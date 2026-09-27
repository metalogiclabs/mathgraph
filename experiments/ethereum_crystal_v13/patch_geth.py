#!/usr/bin/env python3
from pathlib import Path
p=Path("/tmp/geth/eth/protocols/snap/syncv2.go")
s=p.read_text()
old='''			// Decode the raw RLP into a BAL.
			var (
				b         bal.BlockAccessList
				batch     = s.db.NewBatch()
				nextPivot = headers[hash]
				tries     *stateTrie
			)
			if err := rlp.DecodeBytes(raw, &b); err != nil {
				return fmt.Errorf("failed to decode BAL for block %d: %v", num, err)
			}
'''
new='''			// Decode only the final-state consequences consumed by applyAccessList.
			// The raw BAL has already been fully decoded and hash-verified at the
			// peer-response boundary.
			b, err := bal.DecodeApplyRLP(raw)
			if err != nil {
				return fmt.Errorf("failed to decode BAL apply view for block %d: %v", num, err)
			}
			var (
				batch     = s.db.NewBatch()
				nextPivot = headers[hash]
				tries     *stateTrie
			)
'''
if old not in s:
    raise SystemExit("PATCH_TARGET_NOT_FOUND")
s=s.replace(old,new,1)
s=s.replace('s.applyAccessList(&b, batch, tries)','s.applyAccessList(b, batch, tries)',1)
p.write_text(s)
print("PATCH_APPLIED")
