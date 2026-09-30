package snap

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/types/bal"
	"github.com/ethereum/go-ethereum/ethdb"
	pebbledb "github.com/ethereum/go-ethereum/ethdb/pebble"
	"github.com/ethereum/go-ethereum/rlp"
)

const crystalV20Records = 1112

type crystalV20Result struct {
	Protocol           string
	Arm                string
	Records            int
	ApplyNS            int64
	DurableNS          int64
	ApplyCPUNS         int64
	DurableCPUNS       int64
	FinalDigest        string
	FinalPivotHash     string
	AccessListRequests int64
	GethPin            string
	ClaimBoundary      string
}

func crystalV20Corpus(t testing.TB) [][]byte {
	t.Helper()
	b, err := os.ReadFile(os.Getenv("CRYSTAL_BAL_CORPUS"))
	if err != nil {
		t.Fatal(err)
	}
	if len(b) < 8 || string(b[:4]) != "CV10" {
		t.Fatal("bad corpus")
	}
	p := 4
	n := int(binary.LittleEndian.Uint32(b[p : p+4]))
	p += 4
	out := make([][]byte, 0, n)
	for i := 0; i < n; i++ {
		if p+4 > len(b) {
			t.Fatal("truncated corpus length")
		}
		q := int(binary.LittleEndian.Uint32(b[p : p+4]))
		p += 4
		if p+q > len(b) {
			t.Fatal("truncated corpus record")
		}
		raw := make([]byte, q)
		copy(raw, b[p:p+q])
		p += q
		out = append(out, raw)
	}
	if p != len(b) {
		t.Fatal("corpus trailing bytes")
	}
	return out
}

func crystalV20OpenPebble(t testing.TB) ethdb.Database {
	t.Helper()
	path := filepath.Join(t.TempDir(), "chaindata")
	kv, err := pebbledb.New(path, 16, 16, "crystal/v19/", false)
	if err != nil {
		t.Fatal(err)
	}
	return rawdb.NewDatabase(kv)
}

func crystalV20CPUTimeNS(t testing.TB) int64 {
	t.Helper()
	var usage syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &usage); err != nil {
		t.Fatal(err)
	}
	user := usage.Utime.Sec*1_000_000_000 + usage.Utime.Usec*1_000
	system := usage.Stime.Sec*1_000_000_000 + usage.Stime.Usec*1_000
	return user + system
}

func crystalV20Digest(t testing.TB, db ethdb.Database) string {
	t.Helper()
	h := sha256.New()
	it := db.NewIterator(nil, nil)
	defer it.Release()
	var lenbuf [8]byte
	for it.Next() {
		k := append([]byte(nil), it.Key()...)
		v := append([]byte(nil), it.Value()...)
		binary.LittleEndian.PutUint64(lenbuf[:], uint64(len(k)))
		h.Write(lenbuf[:])
		h.Write(k)
		binary.LittleEndian.PutUint64(lenbuf[:], uint64(len(v)))
		h.Write(lenbuf[:])
		h.Write(v)
	}
	if err := it.Error(); err != nil {
		t.Fatal(err)
	}
	return fmt.Sprintf("%x", h.Sum(nil))
}

func crystalV20Fixture(t *testing.T, db ethdb.Database, raws [][]byte) (*types.Header, *types.Header, map[common.Hash]rlp.RawValue) {
	t.Helper()
	emptyHash := common.Hash{}
	zero := uint64(0)
	const baseNumber = uint64(1000)

	base := &types.Header{
		Number:           new(big.Int).SetUint64(baseNumber),
		Root:             emptyHash,
		Difficulty:       common.Big0,
		BaseFee:          common.Big0,
		WithdrawalsHash:  &emptyHash,
		BlobGasUsed:      &zero,
		ExcessBlobGas:    &zero,
		ParentBeaconRoot: &emptyHash,
		RequestsHash:     &emptyHash,
	}
	rawdb.WriteHeader(db, base)
	rawdb.WriteCanonicalHash(db, base.Hash(), baseNumber)

	parent := base.Hash()
	accessLists := make(map[common.Hash]rlp.RawValue, len(raws))
	var target *types.Header
	for i, raw := range raws {
		var full bal.BlockAccessList
		if err := rlp.DecodeBytes(raw, &full); err != nil {
			t.Fatalf("fixture BAL %d decode: %v", i, err)
		}
		balHash := full.Hash()
		header := &types.Header{
			ParentHash:          parent,
			Root:                emptyHash,
			Number:              new(big.Int).SetUint64(baseNumber + uint64(i) + 1),
			Difficulty:          common.Big0,
			BaseFee:             common.Big0,
			WithdrawalsHash:     &emptyHash,
			BlobGasUsed:         &zero,
			ExcessBlobGas:       &zero,
			ParentBeaconRoot:    &emptyHash,
			RequestsHash:        &emptyHash,
			BlockAccessListHash: &balHash,
		}
		rawdb.WriteHeader(db, header)
		rawdb.WriteCanonicalHash(db, header.Hash(), header.Number.Uint64())
		accessLists[header.Hash()] = append(rlp.RawValue(nil), raw...)
		parent = header.Hash()
		target = header
	}
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	return base, target, accessLists
}

func TestCrystalV20AuthenticatedCatchUp(t *testing.T) {
	raws := crystalV20Corpus(t)
	if len(raws) != crystalV20Records {
		t.Fatalf("records=%d want %d", len(raws), crystalV20Records)
	}
	arm := os.Getenv("CRYSTAL_V20_ARM")
	if arm != "stock" && arm != "crystal" {
		t.Fatalf("CRYSTAL_V20_ARM=%q", arm)
	}
	resultPath := os.Getenv("CRYSTAL_V20_RESULT")
	if resultPath == "" {
		t.Fatal("CRYSTAL_V20_RESULT not set")
	}

	db := crystalV20OpenPebble(t)
	defer db.Close()
	base, target, accessLists := crystalV20Fixture(t, db, raws)

	var once sync.Once
	cancel := make(chan struct{})
	term := func() { once.Do(func() { close(cancel) }) }

	syncer := newSyncerV2(db, rawdb.HashScheme)
	syncer.pivot = base
	syncer.setPhase(phaseDownload)
	peer := newTestPeerV2("crystal-v19-peer", t, term)
	peer.accessLists = accessLists
	if err := syncer.Register(peer); err != nil {
		t.Fatal(err)
	}
	peer.remote = syncer

	cpuStart := crystalV20CPUTimeNS(t)
	start := time.Now()
	if err := syncer.catchUp(target, cancel); err != nil {
		t.Fatalf("authenticated catchUp failed: %v", err)
	}
	applyNS := time.Since(start).Nanoseconds()
	applyCPUNS := crystalV20CPUTimeNS(t) - cpuStart
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	durableNS := time.Since(start).Nanoseconds()
	durableCPUNS := crystalV20CPUTimeNS(t) - cpuStart

	if syncer.pivot == nil || syncer.pivot.Hash() != target.Hash() {
		t.Fatalf("live pivot mismatch: have=%v want=%v", syncer.pivot, target.Hash())
	}
	reloaded := newSyncerV2(db, rawdb.HashScheme)
	if reloaded.pivot == nil || reloaded.pivot.Hash() != target.Hash() {
		t.Fatalf("persisted pivot mismatch: have=%v want=%v", reloaded.pivot, target.Hash())
	}
	requests := peer.nAccessListRequests.Load()
	if requests <= 0 {
		t.Fatal("authenticated peer path issued zero BAL requests")
	}

	result := crystalV20Result{
		Protocol:           "ETHEREUM_CRYSTAL_V20_CPU_REPLICATION",
		Arm:                arm,
		Records:            len(raws),
		ApplyNS:            applyNS,
		DurableNS:          durableNS,
		ApplyCPUNS:         applyCPUNS,
		DurableCPUNS:       durableCPUNS,
		FinalDigest:        crystalV20Digest(t, db),
		FinalPivotHash:     target.Hash().Hex(),
		AccessListRequests: requests,
		GethPin:            "920c07774c65ebb3023536f85df642c44478b540",
		ClaimBoundary:      "unchanged V19 authenticated syncerV2.catchUp + Pebble boundary, adding Linux process CPU-time measurement around the measured catch-up and final durability sync; phaseDownload/no-trie synthetic linked header chain over the frozen 1,112 independent held-out BAL records; no socket transport and not canonical mainnet chaindata",
	}
	blob, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(resultPath, blob, 0o644); err != nil {
		t.Fatal(err)
	}
	t.Logf("ETHEREUM_CRYSTAL_V20_CPU_REPLICATION=PASS arm=%s records=%d apply_ns=%d durable_ns=%d apply_cpu_ns=%d durable_cpu_ns=%d digest=%s requests=%d pivot=%s", arm, len(raws), applyNS, durableNS, applyCPUNS, durableCPUNS, result.FinalDigest, requests, result.FinalPivotHash)
}
