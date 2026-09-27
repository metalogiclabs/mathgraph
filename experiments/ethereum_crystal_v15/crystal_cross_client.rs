use crate::{test_utils::hashed_factory, AccountCoverage, SnapCatchUpStore, StorageProgress};
use alloy_eip7928::{
    AccountChanges, BalanceChange, BlockAccessIndex, CodeChange, NonceChange, SlotChanges,
    StorageChange,
};
use alloy_primitives::{Address, Bytes, U256};
use alloy_rlp::{Decodable, Error, Header};
use reth_storage_api::DatabaseProviderFactory;
use std::{fs, hint::black_box, time::Instant};

fn take_list<'a>(buf: &mut &'a [u8]) -> Result<&'a [u8], Error> {
    let header = Header::decode(buf)?;
    if !header.list {
        return Err(Error::UnexpectedString)
    }
    if buf.len() < header.payload_length {
        return Err(Error::InputTooShort)
    }
    let (payload, rest) = buf.split_at(header.payload_length);
    *buf = rest;
    Ok(payload)
}

fn final_u256(mut list: &[u8]) -> Result<Option<(BlockAccessIndex, U256)>, Error> {
    let mut last = None;
    while !list.is_empty() {
        let mut pair = take_list(&mut list)?;
        let index = u64::decode(&mut pair)?;
        let value = U256::decode(&mut pair)?;
        if !pair.is_empty() {
            return Err(Error::Custom("indexed change trailing fields"))
        }
        last = Some((BlockAccessIndex::new(index), value));
    }
    Ok(last)
}

fn final_u64(mut list: &[u8]) -> Result<Option<(BlockAccessIndex, u64)>, Error> {
    let mut last = None;
    while !list.is_empty() {
        let mut pair = take_list(&mut list)?;
        let index = u64::decode(&mut pair)?;
        let value = u64::decode(&mut pair)?;
        if !pair.is_empty() {
            return Err(Error::Custom("indexed change trailing fields"))
        }
        last = Some((BlockAccessIndex::new(index), value));
    }
    Ok(last)
}

fn final_bytes(mut list: &[u8]) -> Result<Option<(BlockAccessIndex, Bytes)>, Error> {
    let mut last = None;
    while !list.is_empty() {
        let mut pair = take_list(&mut list)?;
        let index = u64::decode(&mut pair)?;
        let value = Bytes::decode(&mut pair)?;
        if !pair.is_empty() {
            return Err(Error::Custom("indexed change trailing fields"))
        }
        last = Some((BlockAccessIndex::new(index), value));
    }
    Ok(last)
}

fn decode_apply_view(raw: &[u8]) -> Result<Vec<AccountChanges>, Error> {
    let mut top = raw;
    let mut root = take_list(&mut top)?;
    if !top.is_empty() {
        return Err(Error::Custom("BAL trailing bytes"))
    }
    let mut out = Vec::new();
    while !root.is_empty() {
        let mut account = take_list(&mut root)?;
        let address = Address::decode(&mut account)?;

        let mut storage_raw = take_list(&mut account)?;
        let mut storage_changes = Vec::new();
        while !storage_raw.is_empty() {
            let mut slot_entry = take_list(&mut storage_raw)?;
            let slot = U256::decode(&mut slot_entry)?;
            let changes_raw = take_list(&mut slot_entry)?;
            if !slot_entry.is_empty() {
                return Err(Error::Custom("storage slot trailing fields"))
            }
            let Some((index, value)) = final_u256(changes_raw)? else {
                return Err(Error::Custom("storage slot without changes"))
            };
            storage_changes.push(SlotChanges::new(
                slot,
                vec![StorageChange::new(index, value)],
            ));
        }

        // Dependency-only storage reads are syntactically consumed but not materialized.
        let _storage_reads = take_list(&mut account)?;

        let balances_raw = take_list(&mut account)?;
        let balance_changes = final_u256(balances_raw)?
            .map(|(i, v)| vec![BalanceChange::new(i, v)])
            .unwrap_or_default();

        let nonces_raw = take_list(&mut account)?;
        let nonce_changes = final_u64(nonces_raw)?
            .map(|(i, v)| vec![NonceChange::new(i, v)])
            .unwrap_or_default();

        let codes_raw = take_list(&mut account)?;
        let code_changes = final_bytes(codes_raw)?
            .map(|(i, v)| vec![CodeChange::new(i, v)])
            .unwrap_or_default();

        if !account.is_empty() {
            return Err(Error::Custom("account trailing fields"))
        }
        out.push(AccountChanges {
            address,
            storage_changes,
            storage_reads: Vec::new(),
            balance_changes,
            nonce_changes,
            code_changes,
        });
    }
    Ok(out)
}

fn corpus() -> Vec<Vec<u8>> {
    let bytes = fs::read(std::env::var("CRYSTAL_BAL_CORPUS").expect("CRYSTAL_BAL_CORPUS"))
        .expect("read corpus");
    assert!(bytes.len() >= 8 && &bytes[..4] == b"CV10");
    let mut pos = 4usize;
    let count = u32::from_le_bytes(bytes[pos..pos + 4].try_into().unwrap()) as usize;
    pos += 4;
    let mut out = Vec::with_capacity(count);
    for _ in 0..count {
        let n = u32::from_le_bytes(bytes[pos..pos + 4].try_into().unwrap()) as usize;
        pos += 4;
        out.push(bytes[pos..pos + n].to_vec());
        pos += n;
    }
    assert_eq!(pos, bytes.len());
    out
}

fn median(mut values: Vec<f64>) -> f64 {
    values.sort_by(|a, b| a.partial_cmp(b).unwrap());
    values[values.len() / 2]
}

#[test]
fn crystal_cross_client_reth_apply_consequence_and_benchmark() {
    let records = corpus();
    assert_eq!(records.len(), 1112);

    let factory = hashed_factory();
    let provider = factory.database_provider_rw().unwrap();

    for (i, raw) in records.iter().enumerate() {
        let full = alloy_rlp::decode_exact::<Vec<AccountChanges>>(raw)
            .unwrap_or_else(|e| panic!("record {i} full decode: {e:?}"));
        let compact = decode_apply_view(raw)
            .unwrap_or_else(|e| panic!("record {i} compact decode: {e:?}"));

        let full_update = provider
            .block_access_list_update(AccountCoverage::COMPLETE, StorageProgress::START, &full)
            .unwrap();
        let compact_update = provider
            .block_access_list_update(AccountCoverage::COMPLETE, StorageProgress::START, &compact)
            .unwrap();
        assert_eq!(compact_update, full_update, "record {i} BalStateUpdate mismatch");
    }

    let mut full_times = Vec::new();
    let mut compact_times = Vec::new();
    for _ in 0..7 {
        let start = Instant::now();
        let mut n = 0usize;
        for _ in 0..20 {
            for raw in &records {
                let decoded = alloy_rlp::decode_exact::<Vec<AccountChanges>>(raw).unwrap();
                n ^= black_box(decoded.len());
            }
        }
        black_box(n);
        full_times.push(start.elapsed().as_secs_f64());

        let start = Instant::now();
        let mut n = 0usize;
        for _ in 0..20 {
            for raw in &records {
                let decoded = decode_apply_view(raw).unwrap();
                n ^= black_box(decoded.len());
            }
        }
        black_box(n);
        compact_times.push(start.elapsed().as_secs_f64());
    }

    let full = median(full_times);
    let compact = median(compact_times);
    println!("ETHEREUM_CRYSTAL_V15_RETH=PASS");
    println!("records={}", records.len());
    println!("reth_bal_state_update_parity_all=true");
    println!("full_decode_median_s={full:.9}");
    println!("compact_apply_decode_median_s={compact:.9}");
    println!("speedup_vs_full={:.9}", full / compact);
    println!("reth_architecture_duplicate_decode=false");
}
