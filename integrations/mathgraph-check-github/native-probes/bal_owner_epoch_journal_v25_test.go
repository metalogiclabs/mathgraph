//go:build balexperiment

// V25 RED baseline: copied V24 post-success in-memory epoch advancement.
// A native Engine VALID effect whose acknowledgement/epoch-update is lost
// is followed by a reconstructed gateway with no durable state. Test-only.
package catalyst

import (
	"context"
	"crypto/ed25519"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
)

type balV25Gateway struct {
	h         balV23ImportedHarness
	pub       ed25519.PublicKey
	genesis   common.Hash
	journal   string
	lastEpoch uint64
	mu        sync.Mutex
	dropAfterNative func(uint64) bool
}

func newBALV25Gateway(h balV23ImportedHarness, pub ed25519.PublicKey, genesis common.Hash, journal string, drop func(uint64) bool) (*balV25Gateway, error) {
	// RED: reconstructs an in-memory gate but ignores the journal path.
	return &balV25Gateway{h: h, pub: pub, genesis: genesis, journal: journal, dropAfterNative: drop}, nil
}

func (g *balV25Gateway) forward(client int, p balV24Grant) (engine.ForkChoiceResponse, error) {
	if p.Scope != balV24Scope || p.Genesis != g.genesis || p.Epoch == 0 ||
		p.Head == (common.Hash{}) || p.Final == (common.Hash{}) ||
		!ed25519.Verify(g.pub, balV24Digest(p), p.Signature) {
		return engine.ForkChoiceResponse{}, errors.New("MG_V25_INVALID_GRANT")
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	if p.Epoch <= g.lastEpoch {
		return engine.ForkChoiceResponse{}, fmt.Errorf("MG_V25_STALE epoch=%d last=%d", p.Epoch, g.lastEpoch)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	var response engine.ForkChoiceResponse
	err := g.h.clients[client].CallContext(ctx, &response, "engine_forkchoiceUpdatedV4",
		engine.ForkchoiceStateV1{HeadBlockHash: p.Head, FinalizedBlockHash: p.Final}, nil, nil)
	if err != nil || response.PayloadStatus.Status != engine.VALID {
		return response, err
	}
	if g.dropAfterNative != nil && g.dropAfterNative(p.Epoch) {
		// Inject loss after observing actual native VALID, before epoch commit.
		return response, errors.New("MG_V25_ACK_LOST_AFTER_NATIVE_VALID")
	}
	g.lastEpoch = p.Epoch
	return response, nil
}

func (g *balV25Gateway) reconcileNative() error {
	return errors.New("MG_V25_RECONCILIATION_NOT_IMPLEMENTED")
}
