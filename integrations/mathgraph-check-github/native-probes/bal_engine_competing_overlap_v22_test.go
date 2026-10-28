//go:build balexperiment

// Test-only Engine V4 causal-supersession experiment: two actual Geth TCP
// peers serve different forks from one genesis, and two JWT clients propose
// separate internally ancestry-qualified head/finalized pairs. Both heads
// are cold/unknown to the target, so SYNCING is NOT Engine VALID.
package catalyst

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"path/filepath"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/consensus/beacon"
	"github.com/ethereum/go-ethereum/consensus/ethash"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/eth"
	"github.com/ethereum/go-ethereum/node"
	"github.com/ethereum/go-ethereum/rpc"
)

func TestBALV22ConcurrentCompetingAncestryPreservesNewerWitness(t *testing.T) {
	genesis, chainA, _, _ := makeBALEngineV11Corpus(t)
	_, chainB, _ := core.GenerateChainWithGenesis(genesis,
		beacon.New(ethash.NewFaker()), len(chainA), func(_ int, block *core.BlockGen) {
			block.SetExtra([]byte("BAL V22 independent competing fork B"))
		})
	chains := [2][]*types.Block{chainA, chainB}
	heads := [2]*types.Block{chainA[len(chainA)-1], chainB[len(chainB)-1]}
	finals := [2]*types.Block{chainA[len(chainA)-2], chainB[len(chainB)-2]}
	if heads[0].Hash() == heads[1].Hash() || finals[0].Hash() == finals[1].Hash() ||
		chains[0][0].ParentHash() != chains[1][0].ParentHash() ||
		heads[0].ParentHash() != finals[0].Hash() ||
		heads[1].ParentHash() != finals[1].Hash() {
		t.Fatal("UNKNOWN/setup: two distinct head-linked finalized forks are required")
	}
	root := t.TempDir()
	var sources [2]*node.Node
	for i := range sources {
		stack, service, _ := openBALEngineV11Node(t,
			filepath.Join(root, fmt.Sprintf("source-%d", i)), genesis, false, false)
		sources[i] = stack
		defer stack.Close()
		n, err := service.BlockChain().InsertChain(chains[i])
		if err != nil || n != len(chains[i]) {
			t.Fatalf("UNKNOWN/setup: source-%d imported %d/%d: %v", i, n, len(chains[i]), err)
		}
	}
	entered, release := make(chan struct{}), make(chan struct{})
	var enteredOnce, releaseOnce sync.Once
	defer releaseOnce.Do(func() { close(release) })
	var hooks, admissions atomic.Int64
	factory := func(service *eth.Ethereum) rpc.API {
		return rpc.API{Namespace: "engine", Authenticated: true,
			Service: &balV13PendingEngineAPI{
				ConsensusAPI: NewConsensusAPI(service), service: service,
				onAdmit: func() { admissions.Add(1) },
				beforeAdmit: func() {
					if hooks.Add(1) == 1 {
						enteredOnce.Do(func() { close(entered) })
						<-release
					}
				},
			}}
	}
	targetStack, target, secretPath := openBALEngineV11Node(t,
		filepath.Join(root, "target"), genesis, true, true, factory)
	defer targetStack.Close()
	for i := range sources {
		peer := sources[i].Server().Self()
		if !peer.IP().IsLoopback() || peer.TCP() == 0 {
			t.Fatalf("UNKNOWN/setup: source-%d is not a local Geth TCP peer: %v", i, peer)
		}
		targetStack.Server().AddPeer(peer)
	}
	awaitBALEngineV11(t, "two independent TCP source forks", 25*time.Second, func() bool {
		return targetStack.Server().PeerCount() == 2 &&
			sources[0].Server().PeerCount() == 1 &&
			sources[1].Server().PeerCount() == 1
	})
	// Prevent vacuous ancestry rejection caused by absent heads or parents.
	for i := range heads {
		for _, item := range []struct {
			label string
			hash  common.Hash
		}{
			{"head", heads[i].Hash()},
			{"head-parent", heads[i].ParentHash()},
			{"finalized", finals[i].Hash()},
		} {
			label, hash := item.label, item.hash
			awaitBALEngineV11(t, fmt.Sprintf("fork-%d remote %s", i, label), 35*time.Second, func() bool {
				header, err := target.Downloader().GetHeader(hash)
				return err == nil && header != nil && header.Hash() == hash
			})
		}
	}
	if target.BlockChain().CurrentBlock().Number.Uint64() != 0 ||
		target.BlockChain().CurrentFinalBlock() != nil ||
		target.BlockChain().ExperimentalPendingBALFinalityHash() != (common.Hash{}) {
		t.Fatal("UNKNOWN/setup: target not cold before competing FCUs")
	}
	unsigned := bytes.NewBufferString(`{"jsonrpc":"2.0","method":"engine_forkchoiceUpdatedV4","params":[],"id":1}`)
	resp, err := (&http.Client{Timeout: 5 * time.Second}).Post(
		targetStack.HTTPAuthEndpoint(), "application/json", unsigned)
	if err != nil {
		t.Fatal(err)
	}
	_ = resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("UNKNOWN/setup: unsigned Engine call HTTP %d", resp.StatusCode)
	}
	secret, err := node.ObtainJWTSecret(secretPath)
	if err != nil || len(secret) != 32 {
		t.Fatalf("UNKNOWN/setup: JWT unavailable: %v", err)
	}
	var key [32]byte
	copy(key[:], secret)
	dial := func() *rpc.Client {
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		client, err := rpc.DialOptions(ctx, targetStack.HTTPAuthEndpoint(),
			rpc.WithHTTPAuth(node.NewJWTAuth(key)))
		if err != nil {
			t.Fatalf("UNKNOWN/setup: authenticated Engine RPC dial: %v", err)
		}
		return client
	}
	clientA, clientB := dial(), dial()
	defer clientA.Close()
	defer clientB.Close()
	fcu := func(i int) engine.ForkchoiceStateV1 {
		return engine.ForkchoiceStateV1{
			HeadBlockHash: heads[i].Hash(), FinalizedBlockHash: finals[i].Hash(),
		}
	}
	type result struct {
		reply engine.ForkChoiceResponse
		err   error
	}
	firstDone := make(chan result, 1)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		var reply engine.ForkChoiceResponse
		err := clientA.CallContext(ctx, &reply, "engine_forkchoiceUpdatedV4", fcu(0), nil, nil)
		firstDone <- result{reply: reply, err: err}
	}()
	select {
	case <-entered:
		t.Log("MG_BAL_V22_ORDER older_A_verified_paused_before_pending_admission")
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/setup: A never reached ancestry-qualified admission")
	}
	if got := target.BlockChain().ExperimentalPendingBALFinalityHash(); got != (common.Hash{}) || admissions.Load() != 0 {
		t.Fatalf("UNKNOWN/setup: A admitted before barrier release: pending=%s admissions=%d", got.Hex(), admissions.Load())
	}
	second, err := callBALV20(t, clientB, fcu(1))
	if err != nil || second.PayloadStatus.Status != engine.SYNCING {
		t.Fatalf("UNKNOWN/setup: newer B Engine FCU did not complete SYNCING: %+v err=%v", second, err)
	}
	if got := target.BlockChain().ExperimentalPendingBALFinalityHash(); got != finals[1].Hash() || admissions.Load() != 1 {
		t.Fatalf("UNKNOWN/setup: B did not admit its independent exact finalized ancestor: pending=%s want=%s admissions=%d", got.Hex(), finals[1].Hash().Hex(), admissions.Load())
	}
	t.Logf("MG_BAL_V22_ORDER newer_B_admitted_exact_ancestry final=%s peers=%d hooks=%d", finals[1].Hash().Hex(), targetStack.Server().PeerCount(), hooks.Load())
	releaseOnce.Do(func() { close(release) })
	select {
	case first := <-firstDone:
		if first.err != nil || first.reply.PayloadStatus.Status != engine.SYNCING {
			t.Fatalf("UNKNOWN/setup: older A did not complete SYNCING: %+v err=%v", first.reply, first.err)
		}
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/setup: older A did not finish after release")
	}
	got := target.BlockChain().ExperimentalPendingBALFinalityHash()
	if got == finals[0].Hash() && admissions.Load() == 2 {
		t.Logf("MG_BAL_V22_RED_OLDER_A_REPLACED_NEWER_B pending=%s old_final=%s new_final=%s admissions=%d", got.Hex(), finals[0].Hash().Hex(), finals[1].Hash().Hex(), admissions.Load())
		t.Fatal("older ancestry-qualified A replaced newer pending B")
	}
	if got != finals[1].Hash() || admissions.Load() != 1 || hooks.Load() != 2 ||
		target.BlockChain().CurrentFinalBlock() != nil {
		t.Fatalf("UNKNOWN/result: unexpected competing FCU boundary: pending=%s want=%s admissions=%d hooks=%d", got.Hex(), finals[1].Hash().Hex(), admissions.Load(), hooks.Load())
	}
	t.Logf("MG_BAL_V22_COMPETING_ANCESTRY_PASS newer_final=%s pending=%s admissions=%d hooks=%d engine_status=SYNCING", finals[1].Hash().Hex(), got.Hex(), admissions.Load(), hooks.Load())
}
