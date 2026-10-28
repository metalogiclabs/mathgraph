//go:build balexperiment

// Authenticated native Engine-VALID characterization across two already
// imported forks. Test-only RPC barrier observes arrival order without
// changing the native ConsensusAPI ForkchoiceUpdatedV4 implementation.
package catalyst

import (
	"context"
	"path/filepath"
	"sync"
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

type balV23NativeEngineGate struct {
	*ConsensusAPI
	beforeDelegate func(engine.ForkchoiceStateV1)
}

func (a *balV23NativeEngineGate) ForkchoiceUpdatedV4(ctx context.Context, update engine.ForkchoiceStateV1, attrs *engine.PayloadAttributes, custody *types.CustodyBitmap) (engine.ForkChoiceResponse, error) {
	if a.beforeDelegate != nil {
		a.beforeDelegate(update)
	}
	return a.ConsensusAPI.ForkchoiceUpdatedV4(ctx, update, attrs, custody)
}

type balV23ImportedHarness struct {
	stack   *node.Node
	target  *eth.Ethereum
	heads   [2]*types.Block
	finals  [2]*types.Block
	clients [2]*rpc.Client
}

func openBALV23ImportedHarness(t *testing.T, beforeDelegate func(engine.ForkchoiceStateV1)) balV23ImportedHarness {
	t.Helper()
	genesis, chainA, _, _ := makeBALEngineV11Corpus(t)
	_, chainB, _ := core.GenerateChainWithGenesis(genesis,
		beacon.New(ethash.NewFaker()), len(chainA), func(_ int, b *core.BlockGen) {
			b.SetExtra([]byte("BAL V23 imported fork B"))
		})
	chains := [2][]*types.Block{chainA, chainB}
	heads := [2]*types.Block{chainA[len(chainA)-1], chainB[len(chainB)-1]}
	finals := [2]*types.Block{chainA[len(chainA)-2], chainB[len(chainB)-2]}
	if heads[0].Hash() == heads[1].Hash() || finals[0].Hash() == finals[1].Hash() ||
		heads[0].ParentHash() != finals[0].Hash() || heads[1].ParentHash() != finals[1].Hash() ||
		chainA[0].ParentHash() != chainB[0].ParentHash() {
		t.Fatal("UNKNOWN/setup: missing distinct hash-linked source forks")
	}
	factory := func(service *eth.Ethereum) rpc.API {
		return rpc.API{Namespace: "engine", Authenticated: true,
			Service: &balV23NativeEngineGate{
				ConsensusAPI: NewConsensusAPI(service), beforeDelegate: beforeDelegate,
			}}
	}
	stack, target, jwtFile := openBALEngineV11Node(t, filepath.Join(t.TempDir(), "imported-target"), genesis, false, true, factory)
	t.Cleanup(func() { _ = stack.Close() })
	for i := range chains {
		n, err := target.BlockChain().InsertChain(chains[i])
		if err != nil || n != len(chains[i]) {
			t.Fatalf("UNKNOWN/setup: imported fork-%d %d/%d blocks: %v", i, n, len(chains[i]), err)
		}
		if target.BlockChain().GetBlockByHash(heads[i].Hash()) == nil ||
			target.BlockChain().GetBlockByHash(finals[i].Hash()) == nil ||
			!target.BlockChain().HasState(heads[i].Root()) {
			t.Fatalf("UNKNOWN/setup: fork-%d imported head/final or state missing", i)
		}
	}
	if target.BlockChain().CurrentFinalBlock() != nil ||
		target.BlockChain().ExperimentalPendingBALFinalityHash() != (common.Hash{}) {
		t.Fatal("UNKNOWN/setup: native Engine target begins with unwanted finality")
	}
	secret, err := node.ObtainJWTSecret(jwtFile)
	if err != nil || len(secret) != 32 {
		t.Fatalf("UNKNOWN/setup: JWT key unavailable: %v", err)
	}
	var key [32]byte
	copy(key[:], secret)
	var clients [2]*rpc.Client
	for i := range clients {
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		client, err := rpc.DialOptions(ctx, stack.HTTPAuthEndpoint(), rpc.WithHTTPAuth(node.NewJWTAuth(key)))
		cancel()
		if err != nil {
			t.Fatalf("UNKNOWN/setup: JWT RPC client-%d: %v", i, err)
		}
		clients[i] = client
		t.Cleanup(client.Close)
	}
	return balV23ImportedHarness{stack: stack, target: target, heads: heads, finals: finals, clients: clients}
}

func (h balV23ImportedHarness) fcu(i int) engine.ForkchoiceStateV1 {
	return engine.ForkchoiceStateV1{HeadBlockHash: h.heads[i].Hash(), FinalizedBlockHash: h.finals[i].Hash()}
}

func (h balV23ImportedHarness) current() (common.Hash, common.Hash) {
	head := h.target.BlockChain().CurrentBlock().Hash()
	final := h.target.BlockChain().CurrentFinalBlock()
	if final == nil {
		return head, common.Hash{}
	}
	return head, final.Hash()
}

func TestBALV23SerialTwoImportedForksBothEngineValid(t *testing.T) {
	h := openBALV23ImportedHarness(t, nil)
	for i := 0; i < 2; i++ {
		response, err := callBALV20(t, h.clients[i], h.fcu(i))
		if err != nil || response.PayloadStatus.Status != engine.VALID {
			t.Fatalf("UNKNOWN/setup: imported fork-%d not Engine VALID: %+v err=%v", i, response, err)
		}
		head, final := h.current()
		if head != h.heads[i].Hash() || final != h.finals[i].Hash() {
			t.Fatalf("UNKNOWN/setup: imported fork-%d canonical pointers head=%s final=%s", i, head, final)
		}
		t.Logf("MG_BAL_V23_SERIAL_VALID fork=%d head=%s final=%s", i, head, final)
	}
}

func TestBALV23DelayedOlderImportedFCUDoesNotReplaceNewerValidFinal(t *testing.T) {
	entered, release := make(chan struct{}), make(chan struct{})
	var enteredOnce, releaseOnce sync.Once
	defer releaseOnce.Do(func() { close(release) })
	var oldHead common.Hash
	before := func(update engine.ForkchoiceStateV1) {
		if update.HeadBlockHash == oldHead {
			enteredOnce.Do(func() { close(entered) })
			<-release
		}
	}
	h := openBALV23ImportedHarness(t, before)
	oldHead = h.heads[0].Hash()
	type result struct {
		reply engine.ForkChoiceResponse
		err   error
	}
	firstDone := make(chan result, 1)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		var reply engine.ForkChoiceResponse
		err := h.clients[0].CallContext(ctx, &reply, "engine_forkchoiceUpdatedV4", h.fcu(0), nil, nil)
		firstDone <- result{reply: reply, err: err}
	}()
	select {
	case <-entered:
		t.Log("MG_BAL_V23_ORDER older_A_entered_authenticated_RPC_paused_before_native_handler")
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/setup: A never entered authenticated Engine wrapper")
	}
	if final := h.target.BlockChain().CurrentFinalBlock(); final != nil {
		t.Fatalf("UNKNOWN/setup: A installed finality before release: %s", final.Hash())
	}
	second, err := callBALV20(t, h.clients[1], h.fcu(1))
	if err != nil || second.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: newer B imported-head Engine was not VALID: %+v err=%v", second, err)
	}
	if head, final := h.current(); head != h.heads[1].Hash() || final != h.finals[1].Hash() {
		t.Fatalf("UNKNOWN/setup: B Engine VALID but B head/final not canonical: head=%s final=%s", head, final)
	}
	t.Logf("MG_BAL_V23_ORDER newer_B_engine_VALID_canonical head=%s final=%s", h.heads[1].Hash(), h.finals[1].Hash())
	releaseOnce.Do(func() { close(release) })
	var first result
	select {
	case first = <-firstDone:
		if first.err != nil {
			t.Fatalf("UNKNOWN/result: A Engine RPC failed after release: %v", first.err)
		}
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/result: A never completed after release")
	}
	head, final := h.current()
	if first.reply.PayloadStatus.Status == engine.VALID && head == h.heads[0].Hash() && final == h.finals[0].Hash() {
		t.Logf("MG_BAL_V23_RED_OLDER_A_REPLACED_B_AFTER_ENGINE_VALID old_head=%s old_final=%s newer_head=%s newer_final=%s", head, final, h.heads[1].Hash(), h.finals[1].Hash())
		t.Fatal("external arrival-order authority absent: delayed older A overwrote newer B's validated canonical pair")
	}
	if head != h.heads[1].Hash() || final != h.finals[1].Hash() || first.reply.PayloadStatus.Status == engine.SYNCING {
		t.Fatalf("UNKNOWN/result: unexpected imported Engine boundary; A status=%s head=%s final=%s want B head=%s final=%s", first.reply.PayloadStatus.Status, head, final, h.heads[1].Hash(), h.finals[1].Hash())
	}
	t.Logf("MG_BAL_V23_BOUNDED_PROTECTED newer_B_canonical_preserved old_A_status=%s head=%s final=%s", first.reply.PayloadStatus.Status, head, final)
}
