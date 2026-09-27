package bal

import (
	"bytes"
	"encoding/binary"
	"os"
	"testing"

	"github.com/ethereum/go-ethereum/rlp"
)

type crystalSpan struct{ list bool; s, e, next int }
type crystalDepAccount struct {
	addr []byte
	reads [][]byte
	slots [][]byte
}

func crystalSpanAt(b []byte, p int) crystalSpan {
	x:=b[p]
	switch {
	case x<=0x7f:
		return crystalSpan{false,p,p+1,p+1}
	case x<=0xb7:
		n:=int(x-0x80); s:=p+1; return crystalSpan{false,s,s+n,s+n}
	case x<=0xbf:
		q:=int(x-0xb7); n:=0
		for _,v:=range b[p+1:p+1+q] { n=(n<<8)|int(v) }
		s:=p+1+q; return crystalSpan{false,s,s+n,s+n}
	case x<=0xf7:
		n:=int(x-0xc0); s:=p+1; return crystalSpan{true,s,s+n,s+n}
	default:
		q:=int(x-0xf7); n:=0
		for _,v:=range b[p+1:p+1+q] { n=(n<<8)|int(v) }
		s:=p+1+q; return crystalSpan{true,s,s+n,s+n}
	}
}
func crystalFixed6(b []byte, x crystalSpan) [6]crystalSpan {
	if !x.list { panic("expected list") }
	var out [6]crystalSpan; p:=x.s; i:=0
	for p<x.e { if i>=6 { panic("too many fields") }; q:=crystalSpanAt(b,p); out[i]=q; i++; p=q.next }
	if i!=6 || p!=x.e { panic("field mismatch") }; return out
}
func crystalFixed2(b []byte, x crystalSpan) [2]crystalSpan {
	if !x.list { panic("expected list") }
	var out [2]crystalSpan; p:=x.s; i:=0
	for p<x.e { if i>=2 { panic("too many fields") }; q:=crystalSpanAt(b,p); out[i]=q; i++; p=q.next }
	if i!=2 || p!=x.e { panic("field mismatch") }; return out
}
func crystalCopy(b []byte,x crystalSpan) []byte {
	if x.list { panic("expected string") }
	z:=make([]byte,x.e-x.s); copy(z,b[x.s:x.e]); return z
}
func crystalDependencyView(raw []byte) []crystalDepAccount {
	root:=crystalSpanAt(raw,0)
	if !root.list || root.next!=len(raw) { panic("bad root") }
	out:=make([]crystalDepAccount,0); p:=root.s
	for p<root.e {
		a:=crystalSpanAt(raw,p); f:=crystalFixed6(raw,a)
		d:=crystalDepAccount{addr:crystalCopy(raw,f[0])}
		q:=f[1].s
		for q<f[1].e {
			se:=crystalSpanAt(raw,q); sf:=crystalFixed2(raw,se)
			d.slots=append(d.slots,crystalCopy(raw,sf[0])); q=se.next
		}
		q=f[2].s
		for q<f[2].e {
			v:=crystalSpanAt(raw,q); d.reads=append(d.reads,crystalCopy(raw,v)); q=v.next
		}
		out=append(out,d); p=a.next
	}
	return out
}

func crystalLoadCorpus(t testing.TB) [][]byte {
	t.Helper(); path:=os.Getenv("CRYSTAL_BAL_CORPUS")
	if path=="" { t.Fatal("CRYSTAL_BAL_CORPUS unset") }
	b,err:=os.ReadFile(path); if err!=nil { t.Fatal(err) }
	if len(b)<8 || string(b[:4])!="CV10" { t.Fatal("bad corpus") }
	p:=4; n:=int(binary.LittleEndian.Uint32(b[p:p+4])); p+=4
	out:=make([][]byte,0,n)
	for i:=0;i<n;i++ {
		q:=int(binary.LittleEndian.Uint32(b[p:p+4])); p+=4
		r:=make([]byte,q); copy(r,b[p:p+q]); p+=q; out=append(out,r)
	}
	if p!=len(b) { t.Fatal("trailing corpus bytes") }; return out
}

func TestCrystalDependencyViewCorrectness(t *testing.T) {
	for ri,raw:=range crystalLoadCorpus(t) {
		var full BlockAccessList
		if err:=rlp.DecodeBytes(raw,&full); err!=nil { t.Fatalf("record %d full decode: %v",ri,err) }
		dep:=crystalDependencyView(raw)
		if len(dep)!=len(full) { t.Fatalf("record %d account count",ri) }
		for i:=range full {
			if !bytes.Equal(dep[i].addr,full[i].Address[:]) { t.Fatalf("record %d account %d address",ri,i) }
			if len(dep[i].reads)!=len(full[i].StorageReads) || len(dep[i].slots)!=len(full[i].StorageChanges) {
				t.Fatalf("record %d account %d dependency counts",ri,i)
			}
			for j,v:=range full[i].StorageReads {
				if !bytes.Equal(dep[i].reads[j],v.Bytes()) { t.Fatalf("record %d read %d",ri,j) }
			}
			for j,v:=range full[i].StorageChanges {
				if !bytes.Equal(dep[i].slots[j],v.Slot.Bytes()) { t.Fatalf("record %d slot %d",ri,j) }
			}
		}
	}
}

var crystalSink int
func BenchmarkCrystalFullGeth(b *testing.B) {
	rs:=crystalLoadCorpus(b); b.ReportAllocs(); b.ResetTimer()
	n:=0
	for i:=0;i<b.N;i++ {
		for _,raw:=range rs {
			var full BlockAccessList
			if err:=rlp.DecodeBytes(raw,&full); err!=nil { b.Fatal(err) }
			n+=len(full)
		}
	}
	crystalSink=n
}
func BenchmarkCrystalDependencyView(b *testing.B) {
	rs:=crystalLoadCorpus(b); b.ReportAllocs(); b.ResetTimer()
	n:=0
	for i:=0;i<b.N;i++ {
		for _,raw:=range rs { n+=len(crystalDependencyView(raw)) }
	}
	crystalSink=n
}
