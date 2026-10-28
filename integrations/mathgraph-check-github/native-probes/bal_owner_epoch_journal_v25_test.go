//go:build balexperiment

// V25 GREEN candidate: durable write-ahead owner-epoch intent for one
// test-only gateway and one live native Geth target. No production mediation.
// No cross-process lock, real owner key, or independently authorized release.
package catalyst

import (
	"context"
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
)

const balV25JournalVersion = "MG_V25_OWNER_EPOCH_JOURNAL_V1"
const balV25Prepared = "PREPARED"
const balV25Observed = "RECONCILED_OBSERVED"

type balV25JournalRecord struct {
	Version string       `json:"version"`
	Phase   string       `json:"phase"`
	Grant   balV24Grant  `json:"grant"`
}

type balV25Gateway struct {
	h               balV23ImportedHarness
	pub             ed25519.PublicKey
	genesis         common.Hash
	journal         string
	lastEpoch       uint64
	record          *balV25JournalRecord
	mu              sync.Mutex
	dropAfterNative func(uint64) bool
}

func newBALV25Gateway(h balV23ImportedHarness, pub ed25519.PublicKey, genesis common.Hash, journal string, drop func(uint64) bool) (*balV25Gateway, error) {
	g := &balV25Gateway{h: h, pub: pub, genesis: genesis, journal: journal, dropAfterNative: drop}
	b, err := os.ReadFile(journal)
	if errors.Is(err, os.ErrNotExist) {
		// Bounded test assumption: no previous journal has been deleted or
		// rolled back. Real anti-rollback requires a separately trusted anchor.
		return g, nil
	}
	if err != nil {
		return nil, fmt.Errorf("MG_V25_INVALID_JOURNAL read: %w", err)
	}
	var rec balV25JournalRecord
	if err := json.Unmarshal(b, &rec); err != nil {
		return nil, fmt.Errorf("MG_V25_INVALID_JOURNAL decode: %w", err)
	}
	if rec.Version != balV25JournalVersion ||
		(rec.Phase != balV25Prepared && rec.Phase != balV25Observed) ||
		rec.Grant.Scope != balV24Scope || rec.Grant.Genesis != genesis ||
		rec.Grant.Epoch == 0 || rec.Grant.Head == (common.Hash{}) ||
		rec.Grant.Final == (common.Hash{}) ||
		!ed25519.Verify(pub, balV24Digest(rec.Grant), rec.Grant.Signature) {
		return nil, errors.New("MG_V25_INVALID_JOURNAL wrong version, phase or source-bound grant")
	}
	g.record = &rec
	g.lastEpoch = rec.Grant.Epoch
	return g, nil
}

// save publishes the entire record before native RPC. This is a local
// fsync+atomic-rename model on one filesystem, not an anti-rollback service
// or a multi-process serialization guarantee.
func (g *balV25Gateway) save(rec balV25JournalRecord) error {
	if rec.Version != balV25JournalVersion {
		return errors.New("MG_V25_INVALID_JOURNAL_VERSION")
	}
	dir := filepath.Dir(g.journal)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}
	payload, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	file, err := os.CreateTemp(dir, ".mg-v25-*.tmp")
	if err != nil {
		return err
	}
	defer os.Remove(file.Name())
	if err := file.Chmod(0600); err != nil {
		_ = file.Close()
		return err
	}
	if _, err := file.Write(append(payload, '
')); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	if err := os.Rename(file.Name(), g.journal); err != nil {
		return err
	}
	d, err := os.Open(dir)
	if err != nil {
		return err
	}
	defer d.Close()
	return d.Sync()
}

func (g *balV25Gateway) forward(client int, p balV24Grant) (engine.ForkChoiceResponse, error) {
	if p.Scope != balV24Scope || p.Genesis != g.genesis || p.Epoch == 0 ||
		p.Head == (common.Hash{}) || p.Final == (common.Hash{}) ||
		!ed25519.Verify(g.pub, balV24Digest(p), p.Signature) {
		return engine.ForkChoiceResponse{}, errors.New("MG_V25_INVALID_GRANT")
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.record != nil && g.record.Phase == balV25Prepared {
		return engine.ForkChoiceResponse{}, errors.New("MG_V25_IN_DOUBT pending native effect requires reconciliation")
	}
	if p.Epoch <= g.lastEpoch {
		return engine.ForkChoiceResponse{}, fmt.Errorf("MG_V25_STALE epoch=%d last=%d", p.Epoch, g.lastEpoch)
	}
	prepared := balV25JournalRecord{Version: balV25JournalVersion, Phase: balV25Prepared, Grant: p}
	// Quarantine this gateway immediately, including if the write fails.
	// No native effect can be issued until the intent is durably published.
	g.record = &prepared
	if err := g.save(prepared); err != nil {
		return engine.ForkChoiceResponse{}, fmt.Errorf("MG_V25_PREPARE_FAILED: %w", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	var response engine.ForkChoiceResponse
	err := g.h.clients[client].CallContext(ctx, &response, "engine_forkchoiceUpdatedV4",
		engine.ForkchoiceStateV1{HeadBlockHash: p.Head, FinalizedBlockHash: p.Final}, nil, nil)
	if err != nil {
		return response, fmt.Errorf("MG_V25_NATIVE_EFFECT_IN_DOUBT: %w", err)
	}
	if response.PayloadStatus.Status != engine.VALID {
		return response, errors.New("MG_V25_NON_VALID_EFFECT_IN_DOUBT")
	}
	head, final := g.h.current()
	if head != p.Head || final != p.Final {
		return response, errors.New("MG_V25_NATIVE_EFFECT_MISMATCH_IN_DOUBT")
	}
	if g.dropAfterNative != nil && g.dropAfterNative(p.Epoch) {
		// Real native VALID already happened; simulate loss before epoch
		// completion. The fsynced PREPARED record remains for reopening.
		return response, errors.New("MG_V25_ACK_LOST_AFTER_NATIVE_VALID")
	}
	observed := prepared
	observed.Phase = balV25Observed
	if err := g.save(observed); err != nil {
		// Leave the earlier PREPARED record in the gate's in-memory state.
		return response, fmt.Errorf("MG_V25_OBSERVATION_JOURNAL_IN_DOUBT: %w", err)
	}
	g.record = &observed
	g.lastEpoch = p.Epoch
	return response, nil
}

func (g *balV25Gateway) reconcileNative() error {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.record == nil || g.record.Phase != balV25Prepared {
		return errors.New("MG_V25_NOT_PREPARED")
	}
	head, final := g.h.current()
	if head != g.record.Grant.Head || final != g.record.Grant.Final {
		// No permission to infer successful completion from a different
		// observed chain state, even when the original RPC returned VALID.
		return fmt.Errorf("MG_V25_NATIVE_MISMATCH head=%s final=%s", head, final)
	}
	observed := *g.record
	observed.Phase = balV25Observed
	if err := g.save(observed); err != nil {
		return fmt.Errorf("MG_V25_RECONCILE_PERSIST_FAILED: %w", err)
	}
	g.record = &observed
	g.lastEpoch = observed.Grant.Epoch
	return nil
}
