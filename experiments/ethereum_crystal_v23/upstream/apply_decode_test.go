package bal

import (
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/rlp"
	"github.com/holiman/uint256"
)

func TestDecodeApplyRLP(t *testing.T) {
	input := BlockAccessList{{
		Address: common.HexToAddress("0x1234"),
		StorageChanges: []encodingSlotChanges{{
			Slot: uint256.NewInt(1),
			SlotChanges: []encodingStorageWrite{
				{BlockAccessIndex: 1, PostValue: uint256.NewInt(10)},
				{BlockAccessIndex: 4, PostValue: uint256.NewInt(40)},
			},
		}},
		StorageReads: []*uint256.Int{uint256.NewInt(2), uint256.NewInt(3)},
		BalanceChanges: []encodingBalanceChange{
			{BlockAccessIndex: 2, PostBalance: uint256.NewInt(100)},
			{BlockAccessIndex: 5, PostBalance: uint256.NewInt(500)},
		},
		NonceChanges: []encodingAccountNonce{
			{BlockAccessIndex: 3, PostNonce: 7},
			{BlockAccessIndex: 6, PostNonce: 9},
		},
		CodeChanges: []encodingCodeChange{
			{BlockAccessIndex: 1, NewCode: []byte{0x60, 0x00}},
			{BlockAccessIndex: 7, NewCode: []byte{0x60, 0x01, 0x56}},
		},
	}}

	raw, err := rlp.EncodeToBytes(input)
	if err != nil {
		t.Fatal(err)
	}
	got, err := DecodeApplyRLP(raw)
	if err != nil {
		t.Fatal(err)
	}
	want := BlockAccessList{{
		Address: common.HexToAddress("0x1234"),
		StorageChanges: []encodingSlotChanges{{
			Slot: uint256.NewInt(1),
			SlotChanges: []encodingStorageWrite{{
				BlockAccessIndex: 4,
				PostValue:        uint256.NewInt(40),
			}},
		}},
		BalanceChanges: []encodingBalanceChange{{
			BlockAccessIndex: 5,
			PostBalance:      uint256.NewInt(500),
		}},
		NonceChanges: []encodingAccountNonce{{
			BlockAccessIndex: 6,
			PostNonce:        9,
		}},
		CodeChanges: []encodingCodeChange{{
			BlockAccessIndex: 7,
			NewCode:          []byte{0x60, 0x01, 0x56},
		}},
	}}
	if !reflect.DeepEqual(*got, want) {
		t.Fatalf("apply decode mismatch\nwant: %#v\n got: %#v", want, *got)
	}
}

func TestDecodeApplyRLPTrailingBytes(t *testing.T) {
	raw, err := rlp.EncodeToBytes(BlockAccessList{})
	if err != nil {
		t.Fatal(err)
	}
	raw = append(raw, 0x80)
	if _, err := DecodeApplyRLP(raw); err == nil {
		t.Fatal("expected trailing-byte rejection")
	}
}
