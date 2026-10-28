//go:build balexperiment

// Synthetic external owner-grant fence around real authenticated native
// Engine FCUs. Research-only: no production code or independently issued grant.
// A direct Engine RPC bypass remains possible and is tested explicitly.
package catalyst

import (
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"fmt"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
)

const balV24Scope = "research:owner-fcu-epoch:v24:NOT-PRODUCTION"

type balV24Grant struct {
	Epoch     uint64
	Scope     string
	Genesis   common.Hash
	Head      common.Hash
	Final     common.Hash
	Signature []byte
}

func balV24Digest(g balV24Grant) []byte {
	h := sha256.New()
	h.Write([]byte("MG-V24-FROZEN-GRANT-V1\x00"))
	h.Write([]byte(g.Scope))
	h.Write([]byte{0})
	h.Write(g.Genesis[:])
	var e [8]byte
	binary.BigEndian.PutUint64(e[:], g.Epoch)
	h.Write(e[:])
	h.Write(g.Head[:])
	h.Write(g.Final[:])
	return h.Sum(nil)
}

type balV24ExternalFence struct {
	h         balV23ImportedHarness
	pub       ed25519.PublicKey
	scope     string
	genesis   common.Hash
	guarded   bool
	before    func(uint64)
	mu        sync.Mutex
	lastEpoch uint64
}

func (g *balV24ExternalFence) forward(client int, p balV24Grant) (engine.ForkChoiceResponse, error) {
	if p.Scope != g.scope || p.Genesis != g.genesis || p.Epoch == 0 ||
		p.Head == (common.Hash{}) || p.Final == (common.Hash{}) ||
		!ed25519.Verify(g.pub, balV24Digest(p), p.Signature) {
		return engine.ForkChoiceResponse{}, errors.New("MG_V24_INVALID_OWNER_GRANT")
	}
	if g.before != nil {
		g.before(p.Epoch)
	} // test-only delay BEFORE the epoch check
	if g.guarded {
		g.mu.Lock()
		defer g.mu.Unlock() // atomically check, execute and advance
		if p.Epoch <= g.lastEpoch {
			return engine.ForkChoiceResponse{}, fmt.Errorf("MG_V24_STALE_OWNER_EPOCH epoch=%d last=%d", p.Epoch, g.lastEpoch)
		}
	}
	var response engine.ForkChoiceResponse
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	err := g.h.clients[client].CallContext(ctx, &response, "engine_forkchoiceUpdatedV4",
		engine.ForkchoiceStateV1{HeadBlockHash: p.Head, FinalizedBlockHash: p.Final}, nil, nil)
	if err == nil && response.PayloadStatus.Status == engine.VALID && g.guarded {
		g.lastEpoch = p.Epoch
	}
	return response, err
}
func balV24Key() ed25519.PrivateKey {
	seed := sha256.Sum256([]byte("MathGraph synthetic-owner V24 test fixture; never real authorization"))
	return ed25519.NewKeyFromSeed(seed[:])
}
func balV24Sign(key ed25519.PrivateKey, genesis common.Hash, epoch uint64, head, final common.Hash) balV24Grant {
	p := balV24Grant{Epoch: epoch, Scope: balV24Scope, Genesis: genesis, Head: head, Final: final}
	p.Signature = ed25519.Sign(key, balV24Digest(p))
	return p
}
func balV24Environment(t *testing.T, guarded bool, before func(uint64)) (balV23ImportedHarness, *balV24ExternalFence, balV24Grant, balV24Grant, ed25519.PrivateKey) {
	t.Helper()
	h := openBALV23ImportedHarness(t, nil)
	key := balV24Key()
	genesis := h.target.BlockChain().GetBlockByNumber(0).Hash()
	gate := &balV24ExternalFence{h: h, pub: key.Public().(ed25519.PublicKey), scope: balV24Scope, genesis: genesis, guarded: guarded, before: before}
	a := balV24Sign(key, genesis, 1, h.heads[0].Hash(), h.finals[0].Hash())
	b := balV24Sign(key, genesis, 2, h.heads[1].Hash(), h.finals[1].Hash())
	return h, gate, a, b, key
}
func balV24Overlap(t *testing.T, guarded bool) {
	t.Helper()
	entered, release := make(chan struct{}), make(chan struct{})
	var once sync.Once
	defer once.Do(func() { close(release) })
	before := func(epoch uint64) {
		if epoch == 1 {
			close(entered)
			<-release
		}
	}
	h, gate, a, b, _ := balV24Environment(t, guarded, before)
	type result struct {
		r   engine.ForkChoiceResponse
		err error
	}
	completed := make(chan result, 1)
	go func() { r, err := gate.forward(0, a); completed <- result{r, err} }()
	select {
	case <-entered:
		t.Log("MG_V24_A_SIGNED_EPOCH1_PAUSED")
	case <-time.After(15 * time.Second):
		t.Fatal("UNKNOWN/setup: A never paused")
	}
	if h.target.BlockChain().CurrentFinalBlock() != nil {
		t.Fatal("UNKNOWN/setup: A executed before release")
	}
	response, err := gate.forward(1, b)
	if err != nil || response.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: B not native Engine VALID: %+v %v", response, err)
	}
	if head, final := h.current(); head != b.Head || final != b.Final {
		t.Fatalf("UNKNOWN/setup: B not canonical: %s %s", head, final)
	}
	t.Log("MG_V24_B_SIGNED_EPOCH2_NATIVE_ENGINE_VALID_CANONICAL")
	once.Do(func() { close(release) })
	var older result
	select {
	case older = <-completed:
	case <-time.After(15 * time.Second):
		t.Fatal("UNKNOWN/result: A did not complete")
	}
	head, final := h.current()
	if guarded {
		if older.err == nil || !strings.Contains(older.err.Error(), "MG_V24_STALE_OWNER_EPOCH") || head != b.Head || final != b.Final {
			t.Fatalf("UNKNOWN/result: guarded A=%+v err=%v head=%s final=%s", older.r, older.err, head, final)
		}
		t.Log("MG_V24_GREEN_SIGNED_EPOCH_FENCE native_B_VALID older_A_ABSTAIN B_canonical")
	} else {
		if older.err != nil || older.r.PayloadStatus.Status != engine.VALID || head != a.Head || final != a.Final {
			t.Fatalf("UNKNOWN/result: unfenced A=%+v err=%v head=%s final=%s", older.r, older.err, head, final)
		}
		t.Log("MG_V24_RED_UNFENCED_SIGNED_GRANTS both_VALID older_A_restored")
	}
}
func TestBALV24UnfencedSignedGrantsDoNotEstablishTemporalAuthority(t *testing.T) {
	balV24Overlap(t, false)
}
func TestBALV24ExternalOwnerEpochFencePreservesNativeValidB(t *testing.T) { balV24Overlap(t, true) }
func TestBALV24ForgeryScopeReplayAndFreshHigherGrant(t *testing.T) {
	h, g, a, b, key := balV24Environment(t, true, nil)
	bad := a
	bad.Signature = append([]byte(nil), a.Signature...)
	bad.Signature[0] ^= 1
	for _, invalid := range []balV24Grant{bad, func() balV24Grant { p := a; p.Scope = "wrong"; return p }(), func() balV24Grant { p := a; p.Head = b.Head; return p }()} {
		if _, err := g.forward(0, invalid); err == nil || !strings.Contains(err.Error(), "MG_V24_INVALID_OWNER_GRANT") {
			t.Fatalf("invalid grant admitted: %v", err)
		}
	}
	if h.target.BlockChain().CurrentFinalBlock() != nil {
		t.Fatal("bad grant created native finality")
	}
	r, err := g.forward(1, b)
	if err != nil || r.PayloadStatus.Status != engine.VALID {
		t.Fatalf("valid B rejected: %+v %v", r, err)
	}
	for _, old := range []balV24Grant{a, b} {
		if _, err := g.forward(0, old); err == nil || !strings.Contains(err.Error(), "MG_V24_STALE_OWNER_EPOCH") {
			t.Fatalf("stale/duplicate admitted: %v", err)
		}
	}
	if head, fin := h.current(); head != b.Head || fin != b.Final {
		t.Fatal("stale grant changed B")
	}
	fresh := balV24Sign(key, b.Genesis, 3, a.Head, a.Final)
	r, err = g.forward(0, fresh)
	if err != nil || r.PayloadStatus.Status != engine.VALID {
		t.Fatalf("fresh higher epoch did not progress: %+v %v", r, err)
	}
	if head, fin := h.current(); head != a.Head || fin != a.Final {
		t.Fatal("fresh higher epoch not canonical")
	}
	t.Log("MG_V24_CONTROLS forged_tampered_scope_stale_duplicate_REJECT fresh_higher_epoch_VALID")
}
func TestBALV24DirectNativeEngineRemainsAnExplicitBypass(t *testing.T) {
	h, g, a, b, _ := balV24Environment(t, true, nil)
	r, err := g.forward(1, b)
	if err != nil || r.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: B not VALID: %+v %v", r, err)
	}
	// This call intentionally does not go through the owner-grant fence.
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	var raw engine.ForkChoiceResponse
	err = h.clients[0].CallContext(ctx, &raw, "engine_forkchoiceUpdatedV4", engine.ForkchoiceStateV1{HeadBlockHash: a.Head, FinalizedBlockHash: a.Final}, nil, nil)
	if err != nil || raw.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: direct native Engine: %+v %v", raw, err)
	}
	if head, fin := h.current(); head != a.Head || fin != a.Final {
		t.Fatalf("UNKNOWN/result: bypass no longer observed %s %s", head, fin)
	}
	t.Log("MG_V24_BYPASS_WITNESS optional_gateway_NOT_a_security_boundary")
}
