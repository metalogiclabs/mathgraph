package snap

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types/bal"
	"github.com/ethereum/go-ethereum/ethdb"
	pebbledb "github.com/ethereum/go-ethereum/ethdb/pebble"
	"github.com/ethereum/go-ethereum/rlp"
)

const (
	crystalV18Records     = 1112
	crystalV18SeedRecords = crystalV18Records / 2
	crystalV18Trials      = 7
)

type crystalV18Observation struct {
	Regime       string
	Arm          string
	Trial        int
	ApplyNS      int64
	DurableNS    int64
	Digest       string
	PrewarmBytes int64
	DBStat       string
}

type crystalV18RegimeSummary struct {
	FullApplyMedianNS      int64
	CompactApplyMedianNS   int64
	ApplySpeedup           float64
	FullDurableMedianNS    int64
	CompactDurableMedianNS int64
	DurableSpeedup         float64
	PairedApplyRatios      []float64
	PairedDurableRatios    []float64
}

type crystalV18Certificate struct {
	Protocol        string
	GethPin         string
	Records         int
	SeedRecords     int
	MeasuredRecords int
	TrialsPerRegime int
	SeedDigest      string
	FinalDigest     string
	Regimes         map[string]crystalV18RegimeSummary
	Observations    []crystalV18Observation
	ClaimBoundary   string
}

func crystalV18Corpus(t testing.TB) [][]byte {
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

func crystalV18OpenPebble(t testing.TB, path, namespace string) (ethdb.Database, *pebbledb.Database) {
	t.Helper()
	kv, err := pebbledb.New(path, 16, 16, namespace, false)
	if err != nil {
		t.Fatal(err)
	}
	return rawdb.NewDatabase(kv), kv
}

func crystalV18Apply(t testing.TB, db ethdb.Database, raws [][]byte, compact bool) {
	t.Helper()
	s := newSyncerV2(db, rawdb.HashScheme)
	for i, raw := range raws {
		var list *bal.BlockAccessList
		if compact {
			v, err := bal.DecodeApplyRLP(raw)
			if err != nil {
				t.Fatalf("record %d compact decode: %v", i, err)
			}
			list = v
		} else {
			var full bal.BlockAccessList
			if err := rlp.DecodeBytes(raw, &full); err != nil {
				t.Fatalf("record %d full decode: %v", i, err)
			}
			list = &full
		}
		batch := db.NewBatch()
		if _, err := s.applyAccessList(list, batch, nil); err != nil {
			t.Fatalf("record %d apply: %v", i, err)
		}
		if err := batch.Write(); err != nil {
			t.Fatalf("record %d commit: %v", i, err)
		}
	}
}

func crystalV18Digest(t testing.TB, db ethdb.Database) string {
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

func crystalV18Prewarm(t testing.TB, db ethdb.Database) int64 {
	t.Helper()
	it := db.NewIterator(nil, nil)
	defer it.Release()
	var n int64
	for it.Next() {
		n += int64(len(it.Key()) + len(it.Value()))
	}
	if err := it.Error(); err != nil {
		t.Fatal(err)
	}
	return n
}

func crystalV18CopyDir(src, dst string) error {
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
		out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, info.Mode().Perm())
		if err != nil {
			in.Close()
			return err
		}
		_, copyErr := io.Copy(out, in)
		inCloseErr := in.Close()
		closeErr := out.Close()
		if copyErr != nil {
			return copyErr
		}
		if inCloseErr != nil {
			return inCloseErr
		}
		return closeErr
	})
}

func crystalV18RunArm(t *testing.T, seedDir string, raws [][]byte, regime, arm string, trial int) crystalV18Observation {
	t.Helper()
	root := t.TempDir()
	dbDir := filepath.Join(root, "chaindata")
	if err := crystalV18CopyDir(seedDir, dbDir); err != nil {
		t.Fatal(err)
	}
	db, _ := crystalV18OpenPebble(t, dbDir, fmt.Sprintf("crystal/v18/%s/%s/%d/", regime, arm, trial))
	defer db.Close()

	var prewarmBytes int64
	if regime == "prewarmed" {
		prewarmBytes = crystalV18Prewarm(t, db)
		if prewarmBytes == 0 {
			t.Fatal("prewarm touched zero bytes")
		}
	}
	runtime.GC()
	compact := arm == "compact"
	start := time.Now()
	crystalV18Apply(t, db, raws, compact)
	applyNS := time.Since(start).Nanoseconds()
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	durableNS := time.Since(start).Nanoseconds()
	digest := crystalV18Digest(t, db)
	stat, err := db.Stat()
	if err != nil {
		t.Fatal(err)
	}
	return crystalV18Observation{
		Regime:       regime,
		Arm:          arm,
		Trial:        trial,
		ApplyNS:      applyNS,
		DurableNS:    durableNS,
		Digest:       digest,
		PrewarmBytes: prewarmBytes,
		DBStat:       stat,
	}
}

func crystalV18Median(xs []int64) int64 {
	y := append([]int64(nil), xs...)
	sort.Slice(y, func(i, j int) bool { return y[i] < y[j] })
	return y[len(y)/2]
}

func crystalV18Summarize(obs []crystalV18Observation, regime string) crystalV18RegimeSummary {
	var fullApply, compactApply, fullDurable, compactDurable []int64
	fullByTrial := make(map[int]crystalV18Observation)
	compactByTrial := make(map[int]crystalV18Observation)
	for _, o := range obs {
		if o.Regime != regime {
			continue
		}
		switch o.Arm {
		case "full":
			fullApply = append(fullApply, o.ApplyNS)
			fullDurable = append(fullDurable, o.DurableNS)
			fullByTrial[o.Trial] = o
		case "compact":
			compactApply = append(compactApply, o.ApplyNS)
			compactDurable = append(compactDurable, o.DurableNS)
			compactByTrial[o.Trial] = o
		}
	}
	fa := crystalV18Median(fullApply)
	ca := crystalV18Median(compactApply)
	fd := crystalV18Median(fullDurable)
	cd := crystalV18Median(compactDurable)
	var applyRatios, durableRatios []float64
	for trial := 0; trial < crystalV18Trials; trial++ {
		f := fullByTrial[trial]
		c := compactByTrial[trial]
		applyRatios = append(applyRatios, float64(f.ApplyNS)/float64(c.ApplyNS))
		durableRatios = append(durableRatios, float64(f.DurableNS)/float64(c.DurableNS))
	}
	return crystalV18RegimeSummary{
		FullApplyMedianNS:      fa,
		CompactApplyMedianNS:   ca,
		ApplySpeedup:           float64(fa) / float64(ca),
		FullDurableMedianNS:    fd,
		CompactDurableMedianNS: cd,
		DurableSpeedup:         float64(fd) / float64(cd),
		PairedApplyRatios:      applyRatios,
		PairedDurableRatios:    durableRatios,
	}
}

func TestCrystalDiskBackedCatchupAB(t *testing.T) {
	raws := crystalV18Corpus(t)
	if len(raws) != crystalV18Records {
		t.Fatalf("records=%d want %d", len(raws), crystalV18Records)
	}
	seedRaws := raws[:crystalV18SeedRecords]
	measureRaws := raws[crystalV18SeedRecords:]

	seedDir := filepath.Join(t.TempDir(), "seed")
	seedDB, _ := crystalV18OpenPebble(t, seedDir, "crystal/v18/seed/")
	crystalV18Apply(t, seedDB, seedRaws, false)
	if err := seedDB.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	seedDigest := crystalV18Digest(t, seedDB)
	if err := seedDB.Close(); err != nil {
		t.Fatal(err)
	}

	var observations []crystalV18Observation
	var finalDigest string
	for _, regime := range []string{"fresh_open", "prewarmed"} {
		for trial := 0; trial < crystalV18Trials; trial++ {
			order := []string{"full", "compact"}
			if trial%2 == 1 {
				order = []string{"compact", "full"}
			}
			pair := make(map[string]crystalV18Observation)
			for _, arm := range order {
				o := crystalV18RunArm(t, seedDir, measureRaws, regime, arm, trial)
				observations = append(observations, o)
				pair[arm] = o
				t.Logf("CRYSTAL_V18 regime=%s trial=%d arm=%s apply_ns=%d durable_ns=%d digest=%s prewarm_bytes=%d", regime, trial, arm, o.ApplyNS, o.DurableNS, o.Digest, o.PrewarmBytes)
			}
			if pair["full"].Digest != pair["compact"].Digest {
				t.Fatalf("digest mismatch regime=%s trial=%d full=%s compact=%s", regime, trial, pair["full"].Digest, pair["compact"].Digest)
			}
			if finalDigest == "" {
				finalDigest = pair["full"].Digest
			} else if pair["full"].Digest != finalDigest {
				t.Fatalf("final digest drift regime=%s trial=%d have=%s want=%s", regime, trial, pair["full"].Digest, finalDigest)
			}
		}
	}

	cert := crystalV18Certificate{
		Protocol:        "ETHEREUM_CRYSTAL_V18_GETH_DISK_BACKED_AB",
		GethPin:         "920c07774c65ebb3023536f85df642c44478b540",
		Records:         len(raws),
		SeedRecords:     len(seedRaws),
		MeasuredRecords: len(measureRaws),
		TrialsPerRegime: crystalV18Trials,
		SeedDigest:      seedDigest,
		FinalDigest:     finalDigest,
		Regimes: map[string]crystalV18RegimeSummary{
			"fresh_open": crystalV18Summarize(observations, "fresh_open"),
			"prewarmed":  crystalV18Summarize(observations, "prewarmed"),
		},
		Observations:  observations,
		ClaimBoundary: "pinned geth Pebble-backed snap applyAccessList + batch-write corpus continuation from identical cloned corpus-derived seed DBs; fresh-open and explicit prewarm regimes; apply timing follows geth async Pebble writes, durable timing adds one final SyncKeyValue; no peer/network latency and not a canonical mainnet chaindata replay",
	}
	blob, err := json.MarshalIndent(cert, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	blob = append(blob, byte(10))
	resultPath := os.Getenv("CRYSTAL_V18_RESULT")
	if resultPath == "" {
		t.Fatal("CRYSTAL_V18_RESULT not set")
	}
	if err := os.WriteFile(resultPath, blob, 0o644); err != nil {
		t.Fatal(err)
	}
	for regime, summary := range cert.Regimes {
		t.Logf("CRYSTAL_V18_SUMMARY regime=%s apply_speedup=%.6f durable_speedup=%.6f full_apply_ns=%d compact_apply_ns=%d full_durable_ns=%d compact_durable_ns=%d", regime, summary.ApplySpeedup, summary.DurableSpeedup, summary.FullApplyMedianNS, summary.CompactApplyMedianNS, summary.FullDurableMedianNS, summary.CompactDurableMedianNS)
	}
	t.Logf("ETHEREUM_CRYSTAL_V18_DISK_BACKED_AB=PASS records=%d seed=%d measured=%d digest=%s", len(raws), len(seedRaws), len(measureRaws), finalDigest)
}
