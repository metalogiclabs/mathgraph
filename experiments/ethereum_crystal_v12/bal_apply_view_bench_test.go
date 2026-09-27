package bal

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/rlp"
	"github.com/holiman/uint256"
)

type crystalApplyStorage struct {
	Slot common.Hash
	Value uint256.Int
}
type crystalApplyAccount struct {
	Address common.Address
	Storage []crystalApplyStorage
	HasBalance bool
	Balance uint256.Int
	HasNonce bool
	Nonce uint64
	HasCode bool
	Code []byte // aliases the input RLP
}

func crystalSkipOne(b []byte) ([]byte,error) {
	_,_,rest,err:=rlp.Split(b); return rest,err
}
func crystalU64(b []byte)(uint64,error) {
	if len(b)>8 { return 0,fmt.Errorf("uint64 overflow") }
	var x uint64
	for _,v:=range b { x=(x<<8)|uint64(v) }
	return x,nil
}
func crystalLastPair(list []byte)(index,value []byte,ok bool,err error) {
	for len(list)>0 {
		var pair,rest []byte
		pair,rest,err=rlp.SplitList(list); if err!=nil{return}
		list=rest
		index,pair,err=rlp.SplitString(pair); if err!=nil{return}
		value,pair,err=rlp.SplitString(pair); if err!=nil{return}
		if len(pair)!=0 { err=fmt.Errorf("pair trailing bytes"); return }
		ok=true
	}
	return
}
func crystalDecodeApplyView(raw []byte)([]crystalApplyAccount,error) {
	root,rest,err:=rlp.SplitList(raw); if err!=nil{return nil,err}
	if len(rest)!=0{return nil,fmt.Errorf("root trailing bytes")}
	out:=make([]crystalApplyAccount,0)
	for len(root)>0 {
		acct,rem,err:=rlp.SplitList(root); if err!=nil{return nil,err}; root=rem
		addr,acct,err:=rlp.SplitString(acct); if err!=nil{return nil,err}
		if len(addr)!=20{return nil,fmt.Errorf("bad address length")}
		var a crystalApplyAccount; copy(a.Address[:],addr)

		storage,acct,err:=rlp.SplitList(acct); if err!=nil{return nil,err}
		for len(storage)>0 {
			slotEntry,rem,err:=rlp.SplitList(storage); if err!=nil{return nil,err}; storage=rem
			slot,slotEntry,err:=rlp.SplitString(slotEntry); if err!=nil{return nil,err}
			changes,slotEntry,err:=rlp.SplitList(slotEntry); if err!=nil{return nil,err}
			if len(slotEntry)!=0{return nil,fmt.Errorf("slot trailing bytes")}
			_,val,ok,err:=crystalLastPair(changes); if err!=nil{return nil,err}
			if !ok{return nil,fmt.Errorf("empty storage changes")}
			var u uint256.Int; u.SetBytes(val)
			a.Storage=append(a.Storage,crystalApplyStorage{Slot:common.BytesToHash(slot),Value:u})
		}
		// storage reads have no consequence for applyAccessList
		acct,err=crystalSkipOne(acct); if err!=nil{return nil,err}

		bals,acct,err:=rlp.SplitList(acct); if err!=nil{return nil,err}
		_,val,ok,err:=crystalLastPair(bals); if err!=nil{return nil,err}
		if ok { a.HasBalance=true; a.Balance.SetBytes(val) }

		nonces,acct,err:=rlp.SplitList(acct); if err!=nil{return nil,err}
		_,val,ok,err=crystalLastPair(nonces); if err!=nil{return nil,err}
		if ok { a.HasNonce=true; a.Nonce,err=crystalU64(val); if err!=nil{return nil,err} }

		codes,acct,err:=rlp.SplitList(acct); if err!=nil{return nil,err}
		_,val,ok,err=crystalLastPair(codes); if err!=nil{return nil,err}
		if ok { a.HasCode=true; a.Code=val }

		if len(acct)!=0{return nil,fmt.Errorf("account trailing bytes")}
		out=append(out,a)
	}
	return out,nil
}

func crystalApplyLoadCorpus(t testing.TB) [][]byte {
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
	return out
}

func TestCrystalApplyViewCorrectness(t *testing.T) {
	for ri,raw:=range crystalApplyLoadCorpus(t) {
		var full BlockAccessList
		if err:=rlp.DecodeBytes(raw,&full); err!=nil { t.Fatalf("record %d full decode: %v",ri,err) }
		view,err:=crystalDecodeApplyView(raw); if err!=nil { t.Fatalf("record %d view: %v",ri,err) }
		if len(view)!=len(full){t.Fatalf("record %d account count",ri)}
		for i:=range full {
			f,v:=full[i],view[i]
			if f.Address!=v.Address || len(f.StorageChanges)!=len(v.Storage){t.Fatalf("record %d account %d shape",ri,i)}
			for j,s:=range f.StorageChanges {
				if s.Slot.Bytes32()!=v.Storage[j].Slot {t.Fatalf("record %d slot",ri)}
				last:=s.SlotChanges[len(s.SlotChanges)-1].PostValue
				if last.Cmp(&v.Storage[j].Value)!=0 {t.Fatalf("record %d storage value",ri)}
			}
			if len(f.BalanceChanges)>0 {
				if !v.HasBalance || f.BalanceChanges[len(f.BalanceChanges)-1].PostBalance.Cmp(&v.Balance)!=0 {t.Fatalf("record %d balance",ri)}
			} else if v.HasBalance {t.Fatalf("record %d spurious balance",ri)}
			if len(f.NonceChanges)>0 {
				if !v.HasNonce || f.NonceChanges[len(f.NonceChanges)-1].PostNonce!=v.Nonce {t.Fatalf("record %d nonce",ri)}
			} else if v.HasNonce {t.Fatalf("record %d spurious nonce",ri)}
			if len(f.CodeChanges)>0 {
				if !v.HasCode || !bytes.Equal(f.CodeChanges[len(f.CodeChanges)-1].NewCode,v.Code){t.Fatalf("record %d code",ri)}
			} else if v.HasCode {t.Fatalf("record %d spurious code",ri)}
		}
	}
}

var crystalApplySink int
func BenchmarkCrystalApplyFullGeth(b *testing.B) {
	rs:=crystalApplyLoadCorpus(b); b.ReportAllocs(); b.ResetTimer(); n:=0
	for i:=0;i<b.N;i++ { for _,raw:=range rs { var full BlockAccessList; if err:=rlp.DecodeBytes(raw,&full);err!=nil{b.Fatal(err)}; n+=len(full) } }
	crystalApplySink=n
}
func BenchmarkCrystalApplyView(b *testing.B) {
	rs:=crystalApplyLoadCorpus(b); b.ReportAllocs(); b.ResetTimer(); n:=0
	for i:=0;i<b.N;i++ { for _,raw:=range rs { v,err:=crystalDecodeApplyView(raw);if err!=nil{b.Fatal(err)}; n+=len(v) } }
	crystalApplySink=n
}
