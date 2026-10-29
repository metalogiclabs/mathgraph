//go:build balexperiment

// GOETH V26: ACTUAL OS-process SIGKILL of a test-only gateway after the
// independently executed native Engine VALID effect, before acknowledgement.
// The native Geth node remains alive in the parent Go test process.
// Separate gateway processes use V25's durable journal save implementation.
// This is not a Geth-process restart, complete mediation or owner permission.
package catalyst

import (
	"bufio"
	"bytes"
	"context"
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/node"
	"github.com/ethereum/go-ethereum/rpc"
)

type balV26ChildInput struct {
	Mode     string       `json:"mode"`
	Endpoint string       `json:"endpoint"`
	JWTFile  string       `json:"jwt_file"`
	Journal  string       `json:"journal"`
	Public   []byte       `json:"public"`
	Genesis  common.Hash  `json:"genesis"`
	Grant    balV24Grant  `json:"grant"`
}

func balV26GrantValid(cfg balV26ChildInput, grant balV24Grant) bool {
	return len(cfg.Public) == ed25519.PublicKeySize &&
		grant.Scope == balV24Scope && grant.Genesis == cfg.Genesis &&
		grant.Epoch > 0 && grant.Head != (common.Hash{}) &&
		grant.Final != (common.Hash{}) &&
		ed25519.Verify(ed25519.PublicKey(cfg.Public), balV24Digest(grant), grant.Signature)
}

func balV26ReadJournal(cfg balV26ChildInput) (*balV25JournalRecord, error) {
	data, err := os.ReadFile(cfg.Journal)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("MG_V26_INVALID_JOURNAL read: %w", err)
	}
	var record balV25JournalRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return nil, fmt.Errorf("MG_V26_INVALID_JOURNAL decode: %w", err)
	}
	if record.Version != balV25JournalVersion ||
		(record.Phase != balV25Prepared && record.Phase != balV25Observed) ||
		!balV26GrantValid(cfg, record.Grant) {
		return nil, errors.New("MG_V26_INVALID_JOURNAL unverified source-bound record")
	}
	return &record, nil
}

func balV26Save(path string, record balV25JournalRecord) error {
	// Reuse the exact V25 file-sync, rename and directory-sync journal writer.
	return (&balV25Gateway{journal: path}).save(record)
}

func balV26Dial(cfg balV26ChildInput) (*rpc.Client, error) {
	if _, err := os.Stat(cfg.JWTFile); err != nil {
		return nil, fmt.Errorf("MG_V26_JWT_SOURCE_NOT_FOUND: %w", err)
	}
	secret, err := node.ObtainJWTSecret(cfg.JWTFile)
	if err != nil || len(secret) != 32 {
		return nil, fmt.Errorf("MG_V26_JWT_INVALID: %v", err)
	}
	var key [32]byte
	copy(key[:], secret)
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	return rpc.DialOptions(ctx, cfg.Endpoint, rpc.WithHTTPAuth(node.NewJWTAuth(key)))
}

func balV26Observation(client *rpc.Client) (common.Hash, common.Hash, error) {
	fetch := func(tag string) (common.Hash, error) {
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		var block map[string]json.RawMessage
		if err := client.CallContext(ctx, &block, "eth_getBlockByNumber", tag, false); err != nil {
			return common.Hash{}, fmt.Errorf("MG_V26_OBSERVATION_RPC_%s: %w", tag, err)
		}
		raw := block["hash"]
		var hash common.Hash
		if len(raw) == 0 || string(raw) == "null" {
			return common.Hash{}, fmt.Errorf("MG_V26_OBSERVATION_MISSING_%s", tag)
		}
		if err := json.Unmarshal(raw, &hash); err != nil || hash == (common.Hash{}) {
			return common.Hash{}, fmt.Errorf("MG_V26_OBSERVATION_INVALID_%s: %v", tag, err)
		}
		return hash, nil
	}
	head, err := fetch("latest")
	if err != nil {
		return common.Hash{}, common.Hash{}, err
	}
	final, err := fetch("finalized")
	return head, final, err
}

func balV26ChildExecute(cfg balV26ChildInput) (string, error) {
	if !balV26GrantValid(cfg, cfg.Grant) {
		return "", errors.New("MG_V26_INVALID_SIGNED_GRANT")
	}
	record, err := balV26ReadJournal(cfg)
	if err != nil {
		return "", err
	}
	switch cfg.Mode {
	case "guard":
		if record == nil {
			return "", errors.New("MG_V26_MISSING_HISTORY_UNKNOWN")
		}
		if record.Phase == balV25Prepared {
			return "MG_V26_RESTART_REFUSED_IN_DOUBT", nil
		}
		if cfg.Grant.Epoch <= record.Grant.Epoch {
			return "MG_V26_RESTART_REFUSED_STALE", nil
		}
		return "", errors.New("MG_V26_UNHANDLED_HIGHER_GRANT_USE_APPLY")
	case "reconcile":
		if record == nil || record.Phase != balV25Prepared {
			return "", errors.New("MG_V26_RECONCILE_REQUIRES_PREPARED")
		}
		client, err := balV26Dial(cfg)
		if err != nil {
			return "", err
		}
		defer client.Close()
		head, final, err := balV26Observation(client)
		if err != nil {
			return "", err
		}
		if head != record.Grant.Head || final != record.Grant.Final {
			return "", fmt.Errorf("MG_V26_NATIVE_MISMATCH head=%s final=%s", head, final)
		}
		observed := *record
		observed.Phase = balV25Observed
		if err := balV26Save(cfg.Journal, observed); err != nil {
			return "", fmt.Errorf("MG_V26_RECONCILE_SYNC_FAILED: %w", err)
		}
		return "MG_V26_RESTART_RECONCILED_EXACT_NATIVE_OBSERVATION", nil
	case "kill", "apply":
		if record != nil {
			if record.Phase == balV25Prepared {
				return "", errors.New("MG_V26_IN_DOUBT_BEFORE_NATIVE_EFFECT")
			}
			if cfg.Grant.Epoch <= record.Grant.Epoch {
				return "", errors.New("MG_V26_STALE_OR_DUPLICATE_GRANT")
			}
		}
		intent := balV25JournalRecord{
			Version: balV25JournalVersion,
			Phase: balV25Prepared,
			Grant: cfg.Grant,
		}
		if err := balV26Save(cfg.Journal, intent); err != nil {
			return "", fmt.Errorf("MG_V26_WRITE_AHEAD_FAILED: %w", err)
		}
		client, err := balV26Dial(cfg)
		if err != nil {
			return "", err
		}
		defer client.Close()
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		var response engine.ForkChoiceResponse
		err = client.CallContext(ctx, &response, "engine_forkchoiceUpdatedV4",
			engine.ForkchoiceStateV1{
				HeadBlockHash: cfg.Grant.Head,
				FinalizedBlockHash: cfg.Grant.Final,
			}, nil, nil)
		if err != nil || response.PayloadStatus.Status != engine.VALID {
			return "", fmt.Errorf("MG_V26_NATIVE_NOT_VALID status=%s err=%v", response.PayloadStatus.Status, err)
		}
		head, final, err := balV26Observation(client)
		if err != nil {
			return "", err
		}
		if head != cfg.Grant.Head || final != cfg.Grant.Final {
			return "", fmt.Errorf("MG_V26_NATIVE_EFFECT_OBSERVATION_MISMATCH head=%s final=%s", head, final)
		}
		if cfg.Mode == "kill" {
			// Parent observes this marker then forcibly SIGKILLs this REAL
			// child OS process. No callback, defer or observation commit.
			fmt.Fprintln(os.Stdout, "MG_V26_CHILD_NATIVE_VALID_CRASH_WINDOW")
			for {
				time.Sleep(time.Hour)
			}
		}
		observed := intent
		observed.Phase = balV25Observed
		if err := balV26Save(cfg.Journal, observed); err != nil {
			return "", fmt.Errorf("MG_V26_NATIVE_VALID_OBSERVATION_SYNC_FAILED: %w", err)
		}
		return fmt.Sprintf("MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_%d", cfg.Grant.Epoch), nil
	default:
		return "", errors.New("MG_V26_UNKNOWN_CHILD_MODE")
	}
}

func TestBALV26GatewayChildProcess(t *testing.T) {
	path := os.Getenv("MG_V26_CHILD_INPUT")
	if path == "" {
		return // Do not start a Geth fixture when run as ordinary Go test.
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("MG_V26_CHILD_CONFIG_READ: %v", err)
	}
	var cfg balV26ChildInput
	if err := json.Unmarshal(data, &cfg); err != nil {
		t.Fatalf("MG_V26_CHILD_CONFIG_DECODE: %v", err)
	}
	marker, err := balV26ChildExecute(cfg)
	if err != nil {
		fmt.Fprintln(os.Stdout, "MG_V26_CHILD_ERROR "+err.Error())
		t.Fatal(err)
	}
	fmt.Fprintln(os.Stdout, marker)
}

func balV26Config(t *testing.T, h balV23ImportedHarness, key ed25519.PrivateKey, journal, mode string, grant balV24Grant) balV26ChildInput {
	t.Helper()
	return balV26ChildInput{
		Mode: mode, Endpoint: h.stack.HTTPAuthEndpoint(),
		JWTFile: h.stack.Config().JWTSecret, Journal: journal,
		Public: key.Public().(ed25519.PublicKey),
		Genesis: grant.Genesis, Grant: grant,
	}
}

func balV26StartChild(t *testing.T, cfg balV26ChildInput) (*exec.Cmd, context.CancelFunc) {
	t.Helper()
	exe, err := os.Executable()
	if err != nil {
		t.Fatalf("UNKNOWN/setup: current Go test binary: %v", err)
	}
	path := filepath.Join(t.TempDir(), "child-input.json")
	data, err := json.Marshal(cfg)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	cmd := exec.CommandContext(ctx, exe, "-test.run=^TestBALV26GatewayChildProcess$", "-test.v")
	cmd.Env = append(os.Environ(), "MG_V26_CHILD_INPUT="+path)
	return cmd, cancel
}

func balV26RunChild(t *testing.T, cfg balV26ChildInput) (string, error) {
	t.Helper()
	cmd, cancel := balV26StartChild(t, cfg)
	defer cancel()
	data, err := cmd.CombinedOutput()
	return string(data), err
}

func balV26ExpectChild(t *testing.T, cfg balV26ChildInput, marker string) string {
	t.Helper()
	out, err := balV26RunChild(t, cfg)
	if err != nil || !strings.Contains(out, marker) {
		t.Fatalf("UNKNOWN/child: %s expected %q: %v; output=%s", cfg.Mode, marker, err, out)
	}
	return out
}

func balV26KillChild(t *testing.T, cfg balV26ChildInput) {
	t.Helper()
	cmd, cancel := balV26StartChild(t, cfg)
	defer cancel()
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if cmd.Process != nil {
			_ = cmd.Process.Kill()
		}
	})
	found := make(chan bool, 1)
	go func() {
		scanner := bufio.NewScanner(stdout)
		scanner.Buffer(make([]byte, 4096), 1024*1024)
		for scanner.Scan() {
			if strings.Contains(scanner.Text(), "MG_V26_CHILD_NATIVE_VALID_CRASH_WINDOW") {
				found <- true
				return
			}
		}
		found <- false
	}()
	select {
	case ok := <-found:
		if !ok {
			_ = cmd.Process.Kill()
			_ = cmd.Wait()
			t.Fatalf("UNKNOWN/setup: child exited before native VALID crash window; stderr=%s", stderr.String())
		}
	case <-time.After(25 * time.Second):
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		t.Fatalf("UNKNOWN/setup: native VALID crash marker not reached; stderr=%s", stderr.String())
	}
	if err := cmd.Process.Kill(); err != nil {
		t.Fatalf("UNKNOWN/setup: actual SIGKILL failed: %v", err)
	}
	err = cmd.Wait()
	var exit *exec.ExitError
	if !errors.As(err, &exit) {
		t.Fatalf("UNKNOWN/setup: gateway did not exit by signal: %v", err)
	}
	status, ok := exit.Sys().(syscall.WaitStatus)
	if !ok || !status.Signaled() || status.Signal() != syscall.SIGKILL {
		t.Fatalf("UNKNOWN/setup: gateway not killed by SIGKILL: %#v", exit.Sys())
	}
	t.Log("MG_V26_ACTUAL_GATEWAY_OS_PROCESS_SIGKILL_AFTER_NATIVE_VALID")
}

func balV26ExpectCanonical(t *testing.T, h balV23ImportedHarness, grant balV24Grant) {
	t.Helper()
	head, final := h.current()
	if head != grant.Head || final != grant.Final {
		t.Fatalf("UNKNOWN/native-state: head=%s final=%s want=%s/%s", head, final, grant.Head, grant.Final)
	}
}

func TestBALV26ActualGatewaySIGKILLAndSeparateProcessRecovery(t *testing.T) {
	h, _, a, b, key := balV24Environment(t, true, nil)
	journal := filepath.Join(t.TempDir(), "v26-owner-journal.json")
	balV26KillChild(t, balV26Config(t, h, key, journal, "kill", b))
	balV26ExpectCanonical(t, h, b)
	prepared, err := balV26ReadJournal(balV26Config(t, h, key, journal, "guard", a))
	if err != nil || prepared == nil || prepared.Phase != balV25Prepared ||
		prepared.Grant.Epoch != 2 || prepared.Grant.Head != b.Head || prepared.Grant.Final != b.Final {
		t.Fatalf("UNKNOWN/prepared: %+v err=%v", prepared, err)
	}
	t.Log("MG_V26_DURABLE_PREPARED_SURVIVED_SIGKILL")
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "guard", a), "MG_V26_RESTART_REFUSED_IN_DOUBT")
	fresh := balV24Sign(key, b.Genesis, 3, b.Head, b.Final)
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "guard", fresh), "MG_V26_RESTART_REFUSED_IN_DOUBT")
	balV26ExpectCanonical(t, h, b)
	t.Log("MG_V26_TWO_SEPARATE_GATEWAY_PROCESSES_FAIL_CLOSED_BEFORE_RECONCILE")
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "reconcile", b), "MG_V26_RESTART_RECONCILED_EXACT_NATIVE_OBSERVATION")
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "guard", a), "MG_V26_RESTART_REFUSED_STALE")
	balV26ExpectCanonical(t, h, b)
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "apply", fresh), "MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_3")
	balV26ExpectCanonical(t, h, fresh)
	t.Log("MG_V26_RECOVERED_NATIVE_OBSERVATION_AND_FRESH_EPOCH3_SAME_HEAD_VALID")
}

func TestBALV26DirectNativeBypassForcesReconciliationAbstention(t *testing.T) {
	h, _, a, b, key := balV24Environment(t, true, nil)
	journal := filepath.Join(t.TempDir(), "v26-owner-journal.json")
	balV26KillChild(t, balV26Config(t, h, key, journal, "kill", b))
	balV26ExpectCanonical(t, h, b)
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	var raw engine.ForkChoiceResponse
	err := h.clients[0].CallContext(ctx, &raw, "engine_forkchoiceUpdatedV4", h.fcu(0), nil, nil)
	if err != nil || raw.PayloadStatus.Status != engine.VALID {
		t.Fatalf("UNKNOWN/setup: raw native bypass not VALID: %+v %v", raw, err)
	}
	balV26ExpectCanonical(t, h, a)
	out, err := balV26RunChild(t, balV26Config(t, h, key, journal, "reconcile", b))
	if err == nil || !strings.Contains(out, "MG_V26_NATIVE_MISMATCH") {
		t.Fatalf("UNKNOWN/result: native bypass falsely reconciled: %v, %s", err, out)
	}
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "guard", a), "MG_V26_RESTART_REFUSED_IN_DOUBT")
	t.Log("MG_V26_NEGATIVE_RAW_ENGINE_BYPASS_MISMATCH_FAIL_CLOSED")
}

func TestBALV26DeletingJournalReenablesStaleSignedNativeAction(t *testing.T) {
	h, _, a, b, key := balV24Environment(t, true, nil)
	journal := filepath.Join(t.TempDir(), "v26-owner-journal.json")
	balV26KillChild(t, balV26Config(t, h, key, journal, "kill", b))
	balV26ExpectCanonical(t, h, b)
	if err := os.Remove(journal); err != nil {
		t.Fatal(err)
	}
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "apply", a), "MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_1")
	balV26ExpectCanonical(t, h, a)
	t.Log("MG_V26_NEGATIVE_JOURNAL_DELETION_REENABLES_STALE_SIGNED_GRANT")
}

func TestBALV26RollingBackJournalReissuesSupersededSignedAction(t *testing.T) {
	h, _, a, b, key := balV24Environment(t, true, nil)
	journal := filepath.Join(t.TempDir(), "v26-owner-journal.json")
	balV26KillChild(t, balV26Config(t, h, key, journal, "kill", b))
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "reconcile", b), "MG_V26_RESTART_RECONCILED_EXACT_NATIVE_OBSERVATION")
	olderJournal, err := os.ReadFile(journal)
	if err != nil {
		t.Fatal(err)
	}
	c := balV24Sign(key, b.Genesis, 3, b.Head, b.Final)
	d := balV24Sign(key, b.Genesis, 4, b.Head, b.Final)
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "apply", c), "MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_3")
	balV26ExpectCanonical(t, h, c)
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "apply", d), "MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_4")
	balV26ExpectCanonical(t, h, d)
	// Explicit attacker-controlled rollback of journal to a signed but stale
	// epoch-2 snapshot. The single local journal cannot detect this.
	if err := os.WriteFile(journal, olderJournal, 0600); err != nil {
		t.Fatal(err)
	}
	balV26ExpectChild(t, balV26Config(t, h, key, journal, "apply", c), "MG_V26_CHILD_NEW_NATIVE_VALID_EPOCH_3")
	balV26ExpectCanonical(t, h, c)
	t.Log("MG_V26_NEGATIVE_JOURNAL_ROLLBACK_REISSUES_STALE_EPOCH3_VALID_SAME_HEAD")
}

func TestBALV26MalformedJournalFailsClosedAcrossProcesses(t *testing.T) {
	h, _, a, b, key := balV24Environment(t, true, nil)
	journal := filepath.Join(t.TempDir(), "v26-owner-journal.json")
	balV26KillChild(t, balV26Config(t, h, key, journal, "kill", b))
	if err := os.WriteFile(journal, []byte("{broken journal"), 0600); err != nil {
		t.Fatal(err)
	}
	out, err := balV26RunChild(t, balV26Config(t, h, key, journal, "guard", a))
	if err == nil || !strings.Contains(out, "MG_V26_INVALID_JOURNAL") {
		t.Fatalf("UNKNOWN/result: malformed persisted history reset: %v, %s", err, out)
	}
	balV26ExpectCanonical(t, h, b)
	t.Log("MG_V26_NEGATIVE_MALFORMED_JOURNAL_FAIL_CLOSED_ACROSS_PROCESSES")
}
