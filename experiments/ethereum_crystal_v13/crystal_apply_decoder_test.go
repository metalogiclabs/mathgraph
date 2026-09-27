package bal

import (
	"bytes"
	"encoding/binary"
	"os"
	"testing"

	"github.com/ethereum/go-ethereum/rlp"
)

func loadCrystalApplyCorpus(t testing.TB) [][]byte {
	t.Helper()
	b, err := os.ReadFile(os.Getenv("CRYSTAL_BAL_CORPUS"))
	if err != nil { t.Fatal(err) }
	if len(b)<8 || string(b[:4])!="CV10" { t.Fatal("bad corpus") }
	p:=4; n:=int(binary.LittleEndian.Uint32(b[p:p+4])); p+=4
	out:=make([][]byte,0,n)
	for i:=0;i<n;i++ {
		q:=int(binary.LittleEndian.Uint32(b[p:p+4])); p+=4
		raw:=make([]byte,q); copy(raw,b[p:p+q]); p+=q; out=append(out,raw)
	}
	return out
}

func TestDecodeApplyRLPMatchesProductionConsequences(t *testing.T) {
	for ri, raw := range loadCrystalApplyCorpus(t) {
		var full BlockAccessList
		if err:=rlp.DecodeBytes(raw,&full); err!=nil {t.Fatalf("record %d full: %v",ri,err)}
		view,err:=DecodeApplyRLP(raw); if err!=nil {t.Fatalf("record %d view: %v",ri,err)}
		if len(*view)!=len(full){t.Fatalf("record %d accounts",ri)}
		for i:=range full {
			f,v:=full[i],(*view)[i]
			if f.Address!=v.Address || len(f.StorageChanges)!=len(v.StorageChanges){t.Fatalf("record %d account %d",ri,i)}
			if len(v.StorageReads)!=0 {t.Fatalf("record %d reads retained",ri)}
			for j,s:=range f.StorageChanges {
				got:=v.StorageChanges[j]
				if s.Slot.Cmp(got.Slot)!=0 || len(got.SlotChanges)!=1 {t.Fatalf("record %d storage shape",ri)}
				want:=s.SlotChanges[len(s.SlotChanges)-1]
				if want.PostValue.Cmp(got.SlotChanges[0].PostValue)!=0 {t.Fatalf("record %d storage value",ri)}
			}
			check := func(name string, fullN, viewN int) {
				if (fullN==0)!=(viewN==0) {t.Fatalf("record %d %s presence",ri,name)}
				if fullN>0 && viewN!=1 {t.Fatalf("record %d %s count",ri,name)}
			}
			check("balance",len(f.BalanceChanges),len(v.BalanceChanges))
			if len(f.BalanceChanges)>0 && f.BalanceChanges[len(f.BalanceChanges)-1].PostBalance.Cmp(v.BalanceChanges[0].PostBalance)!=0 {t.Fatalf("record %d balance",ri)}
			check("nonce",len(f.NonceChanges),len(v.NonceChanges))
			if len(f.NonceChanges)>0 && f.NonceChanges[len(f.NonceChanges)-1].PostNonce!=v.NonceChanges[0].PostNonce {t.Fatalf("record %d nonce",ri)}
			check("code",len(f.CodeChanges),len(v.CodeChanges))
			if len(f.CodeChanges)>0 && !bytes.Equal(f.CodeChanges[len(f.CodeChanges)-1].NewCode,v.CodeChanges[0].NewCode){t.Fatalf("record %d code",ri)}
		}
	}
}

var crystalDecodeSink int
func BenchmarkDecodeApplyRLPFull(b *testing.B) {
	rs:=loadCrystalApplyCorpus(b); b.ReportAllocs(); b.ResetTimer(); n:=0
	for i:=0;i<b.N;i++ { for _,raw:=range rs { var full BlockAccessList; if err:=rlp.DecodeBytes(raw,&full);err!=nil{b.Fatal(err)}; n+=len(full) } }
	crystalDecodeSink=n
}
func BenchmarkDecodeApplyRLPCompact(b *testing.B) {
	rs:=loadCrystalApplyCorpus(b); b.ReportAllocs(); b.ResetTimer(); n:=0
	for i:=0;i<b.N;i++ { for _,raw:=range rs { v,err:=DecodeApplyRLP(raw);if err!=nil{b.Fatal(err)}; n+=len(*v) } }
	crystalDecodeSink=n
}
