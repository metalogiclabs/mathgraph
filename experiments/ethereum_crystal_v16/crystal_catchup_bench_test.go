package snap

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"os"
	"testing"

	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types/bal"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/rlp"
)

func crystalV16Corpus(t testing.TB) [][]byte {
	t.Helper()
	b, err := os.ReadFile(os.Getenv("CRYSTAL_BAL_CORPUS"))
	if err != nil { t.Fatal(err) }
	if len(b) < 8 || string(b[:4]) != "CV10" { t.Fatal("bad corpus") }
	p := 4
	n := int(binary.LittleEndian.Uint32(b[p:p+4])); p += 4
	out := make([][]byte, 0, n)
	for i := 0; i < n; i++ {
		if p+4 > len(b) { t.Fatal("truncated corpus length") }
		q := int(binary.LittleEndian.Uint32(b[p:p+4])); p += 4
		if p+q > len(b) { t.Fatal("truncated corpus record") }
		raw := make([]byte, q); copy(raw, b[p:p+q]); p += q
		out = append(out, raw)
	}
	if p != len(b) { t.Fatal("corpus trailing bytes") }
	return out
}

func crystalApplyCorpus(raws [][]byte, compact bool) (ethdb.Database, error) {
	db := rawdb.NewMemoryDatabase()
	s := newSyncerV2(db, rawdb.HashScheme)
	for i, raw := range raws {
		var list *bal.BlockAccessList
		if compact {
			v, err := bal.DecodeApplyRLP(raw)
			if err != nil { db.Close(); return nil, fmt.Errorf("record %d compact decode: %w", i, err) }
			list = v
		} else {
			var full bal.BlockAccessList
			if err := rlp.DecodeBytes(raw, &full); err != nil {
				db.Close(); return nil, fmt.Errorf("record %d full decode: %w", i, err)
			}
			list = &full
		}
		batch := db.NewBatch()
		if _, err := s.applyAccessList(list, batch, nil); err != nil {
			db.Close(); return nil, fmt.Errorf("record %d apply: %w", i, err)
		}
		if err := batch.Write(); err != nil {
			db.Close(); return nil, fmt.Errorf("record %d commit: %w", i, err)
		}
	}
	return db, nil
}

func crystalDBDigest(t testing.TB, db ethdb.Database) [32]byte {
	t.Helper()
	h := sha256.New()
	it := db.NewIterator(nil, nil)
	defer it.Release()
	var lenbuf [8]byte
	for it.Next() {
		k := append([]byte(nil), it.Key()...)
		v := append([]byte(nil), it.Value()...)
		binary.LittleEndian.PutUint64(lenbuf[:], uint64(len(k)))
		h.Write(lenbuf[:]); h.Write(k)
		binary.LittleEndian.PutUint64(lenbuf[:], uint64(len(v)))
		h.Write(lenbuf[:]); h.Write(v)
	}
	if err := it.Error(); err != nil { t.Fatal(err) }
	var out [32]byte
	copy(out[:], h.Sum(nil))
	return out
}

func TestCrystalCatchupCorpusStateParity(t *testing.T) {
	raws := crystalV16Corpus(t)
	if len(raws) != 1112 { t.Fatalf("records=%d want 1112", len(raws)) }
	full, err := crystalApplyCorpus(raws, false); if err != nil { t.Fatal(err) }
	defer full.Close()
	compact, err := crystalApplyCorpus(raws, true); if err != nil { t.Fatal(err) }
	defer compact.Close()
	a, b := crystalDBDigest(t, full), crystalDBDigest(t, compact)
	if a != b { t.Fatalf("state digest mismatch full=%x compact=%x", a, b) }
	t.Logf("ETHEREUM_CRYSTAL_V16_STATE_PARITY=PASS records=%d digest=%x", len(raws), a)
}

func benchmarkCrystalCatchup(b *testing.B, compact bool) {
	raws := crystalV16Corpus(b)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		db, err := crystalApplyCorpus(raws, compact)
		if err != nil { b.Fatal(err) }
		db.Close()
	}
}

func BenchmarkCrystalCatchupFull(b *testing.B)    { benchmarkCrystalCatchup(b, false) }
func BenchmarkCrystalCatchupCompact(b *testing.B) { benchmarkCrystalCatchup(b, true) }
