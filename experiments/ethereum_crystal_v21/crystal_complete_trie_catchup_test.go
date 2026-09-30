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

const crystalV21Records = 1112

type crystalV21Result struct {
	Protocol           string
	Arm                string
	Records            int
	ApplyNS            int64
	DurableNS          int64
	ApplyCPUNS         int64
	DurableCPUNS       int64
	FinalDigest        string
	FinalPivotHash     string
	FinalStateRoot     string
	RootChainDigest    string
	AccessListRequests int64
	GethPin            string
	ClaimBoundary      string
}

func crystalV21Corpus(t testing.TB) [][]byte {
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

func crystalV21CPUTimeNS(t testing.TB) int64 {
	t.Helper()
	var usage syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &usage); err != nil {
		t.Fatal(err)
	}
	return usage.Utime.Sec*1_000_000_000 + usage.Utime.Usec*1_000 +
		usage.Stime.Sec*1_000_000_000 + usage.Stime.Usec*1_000
}

func crystalV21OpenPebble(t testing.TB) ethdb.Database {
	t.Helper()
	path := filepath.Join(t.TempDir(), "chaindata")
	kv, err := pebbledb.New(path, 32, 32, "crystal/v21/", false)
	if err != nil {
		t.Fatal(err)
	}
	return rawdb.NewDatabase(kv)
}

func crystalV21Digest(t testing.TB, db ethdb.Database) string {
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

func crystalV21BuildSequentialChain(t *testing.T, raws [][]byte) (*types.Header, []*types.Header, map[common.Hash]rlp.RawValue, string) {
	t.Helper()
	builderDB := rawdb.NewMemoryDatabase()
	builder := newSyncerV2(builderDB, rawdb.HashScheme)

	emptyHash := common.Hash{}
	zero := uint64(0)
	const baseNumber = uint64(1000)
	base := &types.Header{
		Number:           new(big.Int).SetUint64(baseNumber),
		Root:             types.EmptyRootHash,
		Difficulty:       common.Big0,
		BaseFee:          common.Big0,
		WithdrawalsHash:  &emptyHash,
		BlobGasUsed:      &zero,
		ExcessBlobGas:    &zero,
		ParentBeaconRoot: &emptyHash,
		RequestsHash:     &emptyHash,
	}

	parentHash := base.Hash()
	parentRoot := base.Root
	headers := make([]*types.Header, 0, len(raws))
	accessLists := make(map[common.Hash]rlp.RawValue, len(raws))
	rootDigest := sha256.New()

	for i, raw := range raws {
		var full bal.BlockAccessList
		if err := rlp.DecodeBytes(raw, &full); err != nil {
			t.Fatalf("builder BAL %d decode: %v", i, err)
		}
		batch := builderDB.NewBatch()
		tr, err := builder.openStateTrie(parentRoot, batch)
		if err != nil {
			t.Fatalf("builder block %d open parent root %x: %v", i, parentRoot, err)
		}
		root, err := builder.applyAccessList(&full, batch, tr)
		if err != nil {
			t.Fatalf("builder block %d apply: %v", i, err)
		}
		if err := batch.Write(); err != nil {
			t.Fatalf("builder block %d commit: %v", i, err)
		}
		balHash := full.Hash()
		header := &types.Header{
			ParentHash:          parentHash,
			Root:                root,
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
		headers = append(headers, header)
		accessLists[header.Hash()] = append(rlp.RawValue(nil), raw...)
		rootDigest.Write(root[:])
		parentHash = header.Hash()
		parentRoot = root
	}
	return base, headers, accessLists, fmt.Sprintf("%x", rootDigest.Sum(nil))
}

func crystalV21InstallChain(t *testing.T, db ethdb.Database, base *types.Header, headers []*types.Header) {
	t.Helper()
	rawdb.WriteHeader(db, base)
	rawdb.WriteCanonicalHash(db, base.Hash(), base.Number.Uint64())
	for _, header := range headers {
		rawdb.WriteHeader(db, header)
		rawdb.WriteCanonicalHash(db, header.Hash(), header.Number.Uint64())
	}
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
}

func TestCrystalV21CompleteTrieCatchUp(t *testing.T) {
	raws := crystalV21Corpus(t)
	if len(raws) != crystalV21Records {
		t.Fatalf("records=%d want %d", len(raws), crystalV21Records)
	}
	arm := os.Getenv("CRYSTAL_V21_ARM")
	if arm != "stock" && arm != "crystal" {
		t.Fatalf("CRYSTAL_V21_ARM=%q", arm)
	}
	resultPath := os.Getenv("CRYSTAL_V21_RESULT")
	if resultPath == "" {
		t.Fatal("CRYSTAL_V21_RESULT not set")
	}

	base, headers, accessLists, rootChainDigest := crystalV21BuildSequentialChain(t, raws)
	target := headers[len(headers)-1]

	db := crystalV21OpenPebble(t)
	defer db.Close()
	crystalV21InstallChain(t, db, base, headers)

	var once sync.Once
	cancel := make(chan struct{})
	term := func() { once.Do(func() { close(cancel) }) }

	syncer := newSyncerV2(db, rawdb.HashScheme)
	syncer.pivot = base
	syncer.setPhase(phaseComplete)
	peer := newTestPeerV2("crystal-v21-peer", t, term)
	peer.accessLists = accessLists
	if err := syncer.Register(peer); err != nil {
		t.Fatal(err)
	}
	peer.remote = syncer

	cpuStart := crystalV21CPUTimeNS(t)
	start := time.Now()
	if err := syncer.catchUp(target, cancel); err != nil {
		t.Fatalf("complete-trie authenticated catchUp failed: %v", err)
	}
	applyNS := time.Since(start).Nanoseconds()
	applyCPUNS := crystalV21CPUTimeNS(t) - cpuStart
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	durableNS := time.Since(start).Nanoseconds()
	durableCPUNS := crystalV21CPUTimeNS(t) - cpuStart

	if syncer.pivot == nil || syncer.pivot.Hash() != target.Hash() {
		t.Fatalf("live pivot mismatch: have=%v want=%v", syncer.pivot, target.Hash())
	}
	reloaded := newSyncerV2(db, rawdb.HashScheme)
	if reloaded.pivot == nil || reloaded.pivot.Hash() != target.Hash() {
		t.Fatalf("persisted pivot mismatch: have=%v want=%v", reloaded.pivot, target.Hash())
	}
	if reloaded.pivot.Root != target.Root {
		t.Fatalf("persisted state root mismatch: have=%s want=%s", reloaded.pivot.Root, target.Root)
	}
	requests := peer.nAccessListRequests.Load()
	if requests <= 0 {
		t.Fatal("authenticated peer path issued zero BAL requests")
	}

	result := crystalV21Result{
		Protocol:           "ETHEREUM_CRYSTAL_V21_COMPLETE_TRIE_CATCHUP",
		Arm:                arm,
		Records:            len(raws),
		ApplyNS:            applyNS,
		DurableNS:          durableNS,
		ApplyCPUNS:         applyCPUNS,
		DurableCPUNS:       durableCPUNS,
		FinalDigest:        crystalV21Digest(t, db),
		FinalPivotHash:     target.Hash().Hex(),
		FinalStateRoot:     target.Root.Hex(),
		RootChainDigest:    rootChainDigest,
		AccessListRequests: requests,
		GethPin:            "920c07774c65ebb3023536f85df642c44478b540",
		ClaimBoundary:      "pinned geth real authenticated syncerV2.catchUp in phaseComplete with full trie maintenance and per-block header-root verification, Pebble batch writes and pivot persistence, over a deterministic sequential chain whose 1,112 post-state roots were generated off-timer by the full production decoder from the frozen independent EELS BAL corpus; no socket transport and not a canonical historical blockchain",
	}
	blob, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(resultPath, blob, 0o644); err != nil {
		t.Fatal(err)
	}
	t.Logf("ETHEREUM_CRYSTAL_V21_COMPLETE_TRIE_CATCHUP=PASS arm=%s records=%d apply_ns=%d durable_ns=%d apply_cpu_ns=%d durable_cpu_ns=%d digest=%s root=%s root_chain=%s requests=%d pivot=%s", arm, len(raws), applyNS, durableNS, applyCPUNS, durableCPUNS, result.FinalDigest, result.FinalStateRoot, rootChainDigest, requests, result.FinalPivotHash)
}
