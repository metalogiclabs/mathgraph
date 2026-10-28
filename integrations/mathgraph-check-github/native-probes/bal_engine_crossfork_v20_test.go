//go:build balexperiment

// Test-only overlay for a separately pinned Geth source tree. This source
// deliberately lives outside the Geth repository and changes no production
// Engine code or original research PR. A green result is historical and scoped.
package catalyst

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"path/filepath"
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

type balV20Arm struct {
	Name           string `json:"name"`
	HeadHash       string `json:"head_hash"`
	FinalizedHash  string `json:"finalized_hash"`
	HeadParentHash string `json:"head_parent_hash"`
	PeerCount      int    `json:"peer_count"`
	SourceForks    bool   `json:"distinct_forks"`
	RemoteHead     bool   `json:"remote_head_fetched"`
	RemoteFinal    bool   `json:"remote_final_fetched"`
	RemoteParent   bool   `json:"remote_head_parent_fetched"`
	JWTProtected   bool   `json:"jwt_protected"`
	ColdHead       bool   `json:"cold_head_before_fcu"`
	EngineStatus   string `json:"engine_status"`
	PendingHash    string `json:"pending_hash"`
	Admissions     int64  `json:"pending_admissions"`
	CanonicalEmpty bool   `json:"canonical_finality_empty"`
}

func balV20RunArm(t *testing.T, genesis *core.Genesis,
	chains [2][]*types.Block, headFork, finalFork int, shouldAdmit bool) balV20Arm {
	t.Helper()
	root := t.TempDir()
	var sources [2]*node.Node
	var services [2]*eth.Ethereum
	var targetStack *node.Node
	defer func() {
		if targetStack != nil {
			_ = targetStack.Close()
		}
		for _, stack := range sources {
			if stack != nil {
				_ = stack.Close()
			}
		}
	}()
	for i := range sources {
		sources[i], services[i], _ = openBALEngineV11Node(
			t, filepath.Join(root, fmt.Sprintf("source-%d", i)), genesis, false, false)
		n, err := services[i].BlockChain().InsertChain(chains[i])
		if err != nil || n != len(chains[i]) {
			t.Fatalf("source %d imported %d/%d blocks: %v", i, n, len(chains[i]), err)
		}
	}
	var admissions atomic.Int64
	factory := func(service *eth.Ethereum) rpc.API {
		return rpc.API{Namespace: "engine", Authenticated: true,
			Service: &balV13PendingEngineAPI{
				ConsensusAPI: NewConsensusAPI(service), service: service,
				onAdmit: func() { admissions.Add(1) },
			}}
	}
	var target *eth.Ethereum
	var jwtFile string
	targetStack, target, jwtFile = openBALEngineV11Node(
		t, filepath.Join(root, "target"), genesis, true, true, factory)
	for i := range sources {
		peer := sources[i].Server().Self()
		if !peer.IP().IsLoopback() || peer.TCP() == 0 {
			t.Fatalf("source %d is not a local authenticated TCP peer: %s", i, peer)
		}
		targetStack.Server().AddPeer(peer)
	}
	awaitBALEngineV11(t, "two separate Geth TCP peers", 25*time.Second, func() bool {
		return targetStack.Server().PeerCount() == 2 &&
			sources[0].Server().PeerCount() == 1 &&
			sources[1].Server().PeerCount() == 1
	})
	heads := [2]*types.Block{chains[0][len(chains[0])-1], chains[1][len(chains[1])-1]}
	finals := [2]*types.Block{chains[0][len(chains[0])-2], chains[1][len(chains[1])-2]}
	if heads[0].Hash() == heads[1].Hash() || finals[0].Hash() == finals[1].Hash() ||
		chains[0][0].ParentHash() != chains[1][0].ParentHash() {
		t.Fatal("fork construction did not preserve shared genesis and distinct forks")
	}
	headHash, finalHash := heads[headFork].Hash(), finals[finalFork].Hash()
	actualParent := heads[headFork].ParentHash()
	if headFork != finalFork && actualParent == finalHash {
		t.Fatal("nominal conflicting-finality arm did not differ from actual head parent")
	}
	// A SYNCING reply alone proves nothing. Both exact remote headers must
	// first be served by actual network peers while the target is cold.
	// The head's *actual* parent must also resolve; otherwise the ancestry
	// predicate could reject merely because the valid same-fork path is absent.
	for _, targetHeader := range []struct {
		label string
		hash  common.Hash
	}{
		{"head", headHash}, {"head-parent", actualParent}, {"final", finalHash},
	} {
		label, hash := targetHeader.label, targetHeader.hash
		awaitBALEngineV11(t, "remote "+label+" header", 35*time.Second, func() bool {
			header, err := target.Downloader().GetHeader(hash)
			return err == nil && header != nil && header.Hash() == hash
		})
	}
	if target.BlockChain().CurrentBlock().Number.Uint64() != 0 ||
		target.BlockChain().CurrentFinalBlock() != nil ||
		target.BlockChain().ExperimentalPendingBALFinalityHash() != (common.Hash{}) {
		t.Fatal("target is not cold/unwarranted before native Engine request")
	}
	// Prove actual authenticated routing: reject an unsigned HTTP call,
	// then use the engine JWT from the target Node's generated secret.
	unauthBody := bytes.NewBufferString(`{"jsonrpc":"2.0","method":"engine_forkchoiceUpdatedV4","params":[],"id":1}`)
	resp, err := (&http.Client{Timeout: 5 * time.Second}).Post(
		targetStack.HTTPAuthEndpoint(), "application/json", unauthBody)
	if err != nil {
		t.Fatal(err)
	}
	_ = resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unsigned Engine request was not rejected: HTTP %d", resp.StatusCode)
	}
	secret, err := node.ObtainJWTSecret(jwtFile)
	if err != nil || len(secret) != 32 {
		t.Fatalf("JWT unavailable: %v length %d", err, len(secret))
	}
	var jwtSecret [32]byte
	copy(jwtSecret[:], secret)
	ctx, cancel := context.WithTimeout(context.Background(), 35*time.Second)
	defer cancel()
	client, err := rpc.DialOptions(ctx, targetStack.HTTPAuthEndpoint(),
		rpc.WithHTTPAuth(node.NewJWTAuth(jwtSecret)))
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	fc := engine.ForkchoiceStateV1{HeadBlockHash: headHash, FinalizedBlockHash: finalHash}
	var reply engine.ForkChoiceResponse
	if err := client.CallContext(ctx, &reply, "engine_forkchoiceUpdatedV4", fc, nil, nil); err != nil {
		t.Fatalf("JWT Engine FCU failed: %v", err)
	}
	if reply.PayloadStatus.Status != engine.SYNCING {
		t.Fatalf("cold unknown-head FCU returned %q rather than SYNCING",
			reply.PayloadStatus.Status)
	}
	observed := balV20Arm{
		Name: fmt.Sprintf("head_fork_%d_final_fork_%d", headFork, finalFork),
		HeadHash: headHash.Hex(), FinalizedHash: finalHash.Hex(),
		HeadParentHash: actualParent.Hex(),
		PeerCount: targetStack.Server().PeerCount(),
		SourceForks: true, RemoteHead: true, RemoteFinal: true, RemoteParent: true,
		JWTProtected: true, ColdHead: true,
		EngineStatus: reply.PayloadStatus.Status,
		PendingHash: target.BlockChain().ExperimentalPendingBALFinalityHash().Hex(),
		Admissions: admissions.Load(),
		CanonicalEmpty: target.BlockChain().CurrentFinalBlock() == nil,
	}
	if shouldAdmit {
		if observed.PendingHash != finalHash.Hex() || observed.Admissions != 1 ||
			!observed.CanonicalEmpty {
			t.Fatalf("same-fork native positive did not admit pending witness: %+v", observed)
		}
	} else if observed.PendingHash != (common.Hash{}).Hex() || observed.Admissions != 0 ||
		!observed.CanonicalEmpty {
		t.Fatalf("real remote cross-fork FCU improperly admitted pending witness: %+v", observed)
	}
	return observed
}

func TestBALV20AuthenticatedRemoteCrossFork(t *testing.T) {
	genesis, chainA, _, _ := makeBALEngineV11Corpus(t)
	// A fork authored separately from A, with the same genesis and header
	// heights. Its different Extra data changes every B header/parent hash.
	_, chainB, _ := core.GenerateChainWithGenesis(genesis,
		beacon.New(ethash.NewFaker()), len(chainA), func(_ int, gen *core.BlockGen) {
			gen.SetExtra([]byte("BAL V20 independent fork B"))
		})
	chains := [2][]*types.Block{chainA, chainB}
	cases := []struct {
		name                 string
		headFork, finalFork  int
		shouldAdmit          bool
	}{
		{"A_head_B_final", 0, 1, false},
		{"B_head_A_final", 1, 0, false},
		{"A_head_A_final", 0, 0, true},
	}
	for _, scenario := range cases {
		t.Run(scenario.name, func(t *testing.T) {
			obs := balV20RunArm(t, genesis, chains,
				scenario.headFork, scenario.finalFork, scenario.shouldAdmit)
			out, err := json.Marshal(obs)
			if err != nil {
				t.Fatal(err)
			}
			t.Logf("MG_BAL_V20_NATIVE_ARM %s", out)
		})
	}
	if t.Failed() {
		t.Log("MG_BAL_V20_NATIVE_UNQUALIFIED one or more required arms failed")
		return
	}
	t.Log("MG_BAL_V20_NATIVE_BOUNDARY REMOTE_CROSS_FORK_PENDING_AUTHORITY_QUALIFIED_ONLY;CONCURRENT_FCU=UNKNOWN")
}
