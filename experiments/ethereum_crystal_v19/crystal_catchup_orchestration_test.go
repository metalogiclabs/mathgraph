package snap

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"os"
	"path/filepath"
	"runtime"
	"sync"
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

const (
	crystalV19Records     = 1112
	crystalV19SeedRecords = crystalV19Records / 2
	crystalV19BaseBlock   = uint64(1000000)
)

type crystalV19Observation struct {
	Protocol       string
	Arm            string
	Trial          int
	Records        int
	SeedRecords    int
	MeasuredRecords int
	CatchUpNS      int64
	DurableNS      int64
	Digest         string
	TargetHash     string
	AccessListRequests int64
	ClaimBoundary  string
}

func crystalV19Corpus(t testing.TB) [][]byte {
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
		raw := append([]byte(nil), b[p:p+q]...)
		p += q
		out = append(out, raw)
	}
	if p != len(b) {
		t.Fatal("corpus trailing bytes")
	}
	return out
}

func crystalV19OpenPebble(t testing.TB, path, namespace string) ethdb.Database {
	t.Helper()
	kv, err := pebbledb.New(path, 16, 16, namespace, false)
	if err != nil {
		t.Fatal(err)
	}
	return rawdb.NewDatabase(kv)
}

func crystalV19ApplySeed(t testing.TB, db ethdb.Database, raws [][]byte) {
	t.Helper()
	s := newSyncerV2(db, rawdb.HashScheme)
	for i, raw := range raws {
		var full bal.BlockAccessList
		if err := rlp.DecodeBytes(raw, &full); err != nil {
			t.Fatalf("seed record %d full decode: %v", i, err)
		}
		batch := db.NewBatch()
		if _, err := s.applyAccessList(&full, batch, nil); err != nil {
			t.Fatalf("seed record %d apply: %v", i, err)
		}
		if err := batch.Write(); err != nil {
			t.Fatalf("seed record %d commit: %v", i, err)
		}
	}
}

func crystalV19Digest(t testing.TB, db ethdb.Database) string {
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

func crystalV19CopyDir(src, dst string) error {
	if err := os.MkdirAll(dst, 0o755); err != nil {
		return err
	}
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		if rel == "." {
			return nil
		}
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, info.Mode().Perm())
		}
		in, err := os.Open(path)
		if err != nil {
			return err
		}
		defer in.Close()
		out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, info.Mode().Perm())
		if err != nil {
			return err
		}
		_, copyErr := io.Copy(out, in)
		closeErr := out.Close()
		if copyErr != nil {
			return copyErr
		}
		return closeErr
	})
}

func crystalV19BuildChain(t testing.TB, db ethdb.Database, raws [][]byte) (*types.Header, *types.Header, map[common.Hash]rlp.RawValue) {
	t.Helper()
	emptyHash := common.Hash{}
	zero := uint64(0)
	base := &types.Header{
		Number:           new(big.Int).SetUint64(crystalV19BaseBlock),
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
	rawdb.WriteCanonicalHash(db, base.Hash(), base.Number.Uint64())

	parent := base.Hash()
	bals := make(map[common.Hash]rlp.RawValue, len(raws))
	var last *types.Header
	for i, raw := range raws {
		var list bal.BlockAccessList
		if err := rlp.DecodeBytes(raw, &list); err != nil {
			t.Fatalf("measured record %d full decode for header hash: %v", i, err)
		}
		balHash := list.Hash()
		header := &types.Header{
			ParentHash:       parent,
			Root:             emptyHash,
			Number:           new(big.Int).SetUint64(crystalV19BaseBlock + uint64(i) + 1),
			Difficulty:       common.Big0,
			BaseFee:          common.Big0,
			WithdrawalsHash:  &emptyHash,
			BlobGasUsed:      &zero,
			ExcessBlobGas:    &zero,
			ParentBeaconRoot: &emptyHash,
			RequestsHash:     &emptyHash,
			BlockAccessListHash: &balHash,
		}
		rawdb.WriteHeader(db, header)
		rawdb.WriteCanonicalHash(db, header.Hash(), header.Number.Uint64())
		bals[header.Hash()] = append(rlp.RawValue(nil), raw...)
		parent = header.Hash()
		last = header
	}
	if last == nil {
		t.Fatal("empty measured chain")
	}
	return base, last, bals
}

func TestCrystalV19CatchUpOrchestration(t *testing.T) {
	arm := os.Getenv("CRYSTAL_V19_ARM")
	if arm != "full" && arm != "compact" {
		t.Fatalf("CRYSTAL_V19_ARM=%q", arm)
	}
	var trial int
	if _, err := fmt.Sscanf(os.Getenv("CRYSTAL_V19_TRIAL"), "%d", &trial); err != nil {
		t.Fatalf("CRYSTAL_V19_TRIAL: %v", err)
	}
	resultPath := os.Getenv("CRYSTAL_V19_RESULT")
	if resultPath == "" {
		t.Fatal("CRYSTAL_V19_RESULT not set")
	}

	raws := crystalV19Corpus(t)
	if len(raws) != crystalV19Records {
		t.Fatalf("records=%d want=%d", len(raws), crystalV19Records)
	}
	seedRaws := raws[:crystalV19SeedRecords]
	measureRaws := raws[crystalV19SeedRecords:]

	seedDir := filepath.Join(t.TempDir(), "seed")
	seedDB := crystalV19OpenPebble(t, seedDir, "crystal/v19/seed/")
	crystalV19ApplySeed(t, seedDB, seedRaws)
	base, target, bals := crystalV19BuildChain(t, seedDB, measureRaws)
	if err := seedDB.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	if err := seedDB.Close(); err != nil {
		t.Fatal(err)
	}

	runDir := filepath.Join(t.TempDir(), "chaindata")
	if err := crystalV19CopyDir(seedDir, runDir); err != nil {
		t.Fatal(err)
	}
	db := crystalV19OpenPebble(t, runDir, fmt.Sprintf("crystal/v19/%s/%d/", arm, trial))
	defer db.Close()

	var (
		once   sync.Once
		cancel = make(chan struct{})
		term   = func() { once.Do(func() { close(cancel) }) }
	)
	syncer := newSyncerV2(db, rawdb.HashScheme)
	syncer.pivot = base
	syncer.setPhase(phaseDownload)
	peer := newTestPeerV2("crystal-v19-peer", t, term)
	peer.accessLists = bals
	if err := syncer.Register(peer); err != nil {
		t.Fatal(err)
	}
	peer.remote = syncer

	runtime.GC()
	start := time.Now()
	if err := syncer.catchUp(target, cancel); err != nil {
		t.Fatalf("catchUp: %v", err)
	}
	catchUpNS := time.Since(start).Nanoseconds()
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	durableNS := time.Since(start).Nanoseconds()

	loader := newSyncerV2(db, rawdb.HashScheme)
	loader.loadSyncStatus()
	if loader.pivot == nil || loader.pivot.Hash() != target.Hash() {
		t.Fatalf("persisted pivot mismatch: have=%v want=%v", loader.pivot, target.Hash())
	}
	requests := peer.nAccessListRequests.Load()
	if requests <= 0 {
		t.Fatal("catchUp made no BAL peer requests")
	}
	digest := crystalV19Digest(t, db)
	obs := crystalV19Observation{
		Protocol:           "ETHEREUM_CRYSTAL_V19_GETH_CATCHUP_ORCHESTRATION",
		Arm:                arm,
		Trial:              trial,
		Records:            len(raws),
		SeedRecords:        len(seedRaws),
		MeasuredRecords:    len(measureRaws),
		CatchUpNS:          catchUpNS,
		DurableNS:          durableNS,
		Digest:             digest,
		TargetHash:         target.Hash().Hex(),
		AccessListRequests: requests,
		ClaimBoundary:      "pinned geth catchUp with real test-peer RequestAccessLists scheduling, full BAL authenticity/hash verification, production catch-up decode/apply/status persistence, file-backed Pebble batch writes, and final SyncKeyValue; controlled in-process peer delivery, no devp2p socket/network latency, phaseDownload so no state-trie root replay",
	}
	blob, err := json.MarshalIndent(obs, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	blob = append(blob, byte(10))
	if err := os.WriteFile(resultPath, blob, 0o644); err != nil {
		t.Fatal(err)
	}
	t.Logf("CRYSTAL_V19 arm=%s trial=%d records=%d requests=%d catchup_ns=%d durable_ns=%d digest=%s target=%s", arm, trial, len(measureRaws), requests, catchUpNS, durableNS, digest, target.Hash().Hex())
	t.Logf("ETHEREUM_CRYSTAL_V19_CATCHUP_ORCHESTRATION=PASS arm=%s trial=%d", arm, trial)
}
