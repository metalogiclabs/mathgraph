//go:build balexperiment

// Frozen tests for ambiguous native Engine effect acknowledgement and
// source-bound write-ahead recovery. Keep this file byte-identical RED→GREEN.
package catalyst

import (
	"context"
	"crypto/ed25519"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
)

func balV25Fixture(t *testing.T) (balV23ImportedHarness, balV24Grant, balV24Grant, ed25519.PrivateKey, string) {
	t.Helper()
	h, _, a, b, key := balV24Environment(t, true, nil)
	return h, a, b, key, filepath.Join(t.TempDir(), "owner_epoch_v25.json")
}

func balV25MustCreate(t *testing.T, h balV23ImportedHarness, key ed25519.PrivateKey, a balV24Grant, journal string, drop func(uint64) bool) *balV25Gateway {
	t.Helper()
	g, err := newBALV25Gateway(h, key.Public().(ed25519.PublicKey), a.Genesis, journal, drop)
	if err != nil {
		t.Fatalf("UNKNOWN/setup: opening owner journal: %v", err)
	}
	return g
}

func balV25MustDropNativeValidB(t *testing.T, h balV23ImportedHarness, g *balV25Gateway, b balV24Grant) {
	t.Helper()
	r, err := g.forward(1, b)
	if err == nil || !strings.Contains(err.Error(), "MG_V25_ACK_LOST_AFTER_NATIVE_VALID") || r.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: injected lost ack not after actual Engine VALID: %+v err=%v", r, err)
	}
	head, final := h.current()
	if head != b.Head || final != b.Final {
		t.Fatalf("UNKNOWN/setup: native B not canonical after lost acknowledgement: %s %s", head, final)
	}
	t.Log("MG_V25_ORDER_NATIVE_B_ENGINE_VALID_ACK_LOST_BEFORE_EPOCH_COMMIT")
}

func TestBALV25LostAckCannotReenableOlderSignedForkchoice(t *testing.T) {
	h, a, b, key, journal := balV25Fixture(t)
	g := balV25MustCreate(t, h, key, a, journal, func(epoch uint64) bool { return epoch == 2 })
	balV25MustDropNativeValidB(t, h, g, b)
	g = nil // Simulated gateway-object recreation; NOT an OS process crash.
	restarted := balV25MustCreate(t, h, key, a, journal, nil)
	r, err := restarted.forward(0, a)
	head, final := h.current()
	if err == nil && r.PayloadStatus.Status == engine.VALID && head == a.Head && final == a.Final {
		t.Log("MG_V25_RED_STALE_EPOCH1_REAPPLIED_AFTER_B_VALID_ACK_LOSS")
		t.Fatal("stale epoch-1 grant rewrote epoch-2 native finality after ambiguous commit")
	}
	if err == nil || !strings.Contains(err.Error(), "MG_V25_IN_DOUBT") {
		t.Fatalf("UNKNOWN/result: expected durable in-doubt quarantine; resp=%+v err=%v", r, err)
	}
	if head != b.Head || final != b.Final {
		t.Fatalf("UNKNOWN/result: quarantined gateway changed B: %s %s", head, final)
	}
	t.Log("MG_V25_GREEN_DURABLE_PREPARE_REFUSES_OLDER_EPOCH_AFTER_REOPEN")
	if err := restarted.reconcileNative(); err != nil {
		t.Fatalf("UNKNOWN/result: exact local head/final reconciliation: %v", err)
	}
	t.Log("MG_V25_NATIVE_HEAD_FINAL_RECONCILED_AS_OBSERVATION")
	for _, old := range []balV24Grant{a, b} {
		if _, err := restarted.forward(0, old); err == nil || !strings.Contains(err.Error(), "MG_V25_STALE") {
			t.Fatalf("UNKNOWN/result: old or replay grant accepted: %v", err)
		}
	}
	fresh := balV24Sign(key, b.Genesis, 3, a.Head, a.Final)
	got, err := restarted.forward(0, fresh)
	if err != nil || got.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/result: fresh higher grant did not make native progress: %+v %v", got, err)
	}
	head, final = h.current()
	if head != a.Head || final != a.Final {
		t.Fatalf("UNKNOWN/result: higher epoch did not become canonical: %s %s", head, final)
	}
	t.Log("MG_V25_GREEN_RECONCILED_REPLAY_REJECTED_FRESH_EPOCH3_ENGINE_VALID")
}

func TestBALV25NativeMismatchCannotBeMisreportedAsReconciled(t *testing.T) {
	h, a, b, key, journal := balV25Fixture(t)
	g := balV25MustCreate(t, h, key, a, journal, func(epoch uint64) bool { return epoch == 2 })
	balV25MustDropNativeValidB(t, h, g, b)
	// The V24 bypass remains. This is a NEGATIVE control: it is not mediation.
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	var raw engine.ForkChoiceResponse
	err := h.clients[0].CallContext(ctx, &raw, "engine_forkchoiceUpdatedV4", h.fcu(0), nil, nil)
	if err != nil || raw.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: direct native bypass did not return VALID: %+v %v", raw, err)
	}
	if head, final := h.current(); head != a.Head || final != a.Final {
		t.Fatal("UNKNOWN/setup: direct native bypass not canonical")
	}
	restarted := balV25MustCreate(t, h, key, a, journal, nil)
	if err := restarted.reconcileNative(); err == nil || !strings.Contains(err.Error(), "MG_V25_NATIVE_MISMATCH") {
		t.Fatalf("UNKNOWN/result: mismatched native state falsely reconciled: %v", err)
	}
	fresh := balV24Sign(key, b.Genesis, 3, b.Head, b.Final)
	if _, err := restarted.forward(1, fresh); err == nil || !strings.Contains(err.Error(), "MG_V25_IN_DOUBT") {
		t.Fatalf("UNKNOWN/result: unresolved mismatch permitted new gateway action: %v", err)
	}
	t.Log("MG_V25_NEGATIVE_NATIVE_BYPASS_CAUSES_MISMATCH_AND_FAIL_CLOSED")
}

func TestBALV25MalformedJournalFailsClosed(t *testing.T) {
	h, a, b, key, journal := balV25Fixture(t)
	g := balV25MustCreate(t, h, key, a, journal, func(epoch uint64) bool { return epoch == 2 })
	balV25MustDropNativeValidB(t, h, g, b)
	if err := os.WriteFile(journal, []byte("{malformed"), 0600); err != nil {
		t.Fatal("UNKNOWN/setup: journal could not be corrupted for control:", err)
	}
	_, err := newBALV25Gateway(h, key.Public().(ed25519.PublicKey), a.Genesis, journal, nil)
	if err == nil || !strings.Contains(err.Error(), "MG_V25_INVALID_JOURNAL") {
		t.Fatalf("UNKNOWN/result: corrupt journal treated as clean start: %v", err)
	}
	t.Log("MG_V25_NEGATIVE_CORRUPT_OWNER_JOURNAL_FAIL_CLOSED")
}
