#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
rows = [json.loads(Path(p).read_text()) for p in sys.argv[2:]]

assert len(rows) == 14, len(rows)
assert {r["Arm"] for r in rows} == {"full", "compact"}
assert all(r["Protocol"] == "ETHEREUM_CRYSTAL_V20_SNAP2_MSGPIPE" for r in rows)
assert all(r["Records"] == 1112 for r in rows)
assert all(r["SeedRecords"] == 556 for r in rows)
assert all(r["MeasuredRecords"] == 556 for r in rows)
assert all(r["AccessListRequests"] > 0 for r in rows)

by_trial = {}
for r in rows:
    by_trial.setdefault(r["Trial"], {})[r["Arm"]] = r
assert set(by_trial) == set(range(7)), sorted(by_trial)
for trial, pair in by_trial.items():
    assert set(pair) == {"full", "compact"}, (trial, pair.keys())
    assert pair["full"]["Digest"] == pair["compact"]["Digest"], trial
    assert pair["full"]["TargetHash"] == pair["compact"]["TargetHash"], trial
    assert pair["full"]["AccessListRequests"] == pair["compact"]["AccessListRequests"], trial

digests = {r["Digest"] for r in rows}
targets = {r["TargetHash"] for r in rows}
assert len(digests) == 1, digests
assert len(targets) == 1, targets

full = sorted((r for r in rows if r["Arm"] == "full"), key=lambda r: r["Trial"])
compact = sorted((r for r in rows if r["Arm"] == "compact"), key=lambda r: r["Trial"])
median = lambda xs: int(statistics.median(xs))

full_catch = median([r["CatchUpNS"] for r in full])
compact_catch = median([r["CatchUpNS"] for r in compact])
full_durable = median([r["DurableNS"] for r in full])
compact_durable = median([r["DurableNS"] for r in compact])
paired_catch = [
    by_trial[i]["full"]["CatchUpNS"] / by_trial[i]["compact"]["CatchUpNS"]
    for i in range(7)
]
paired_durable = [
    by_trial[i]["full"]["DurableNS"] / by_trial[i]["compact"]["DurableNS"]
    for i in range(7)
]

cert = {
    "protocol": "ETHEREUM_CRYSTAL_V20_SNAP2_MSGPIPE",
    "geth_pin": "920c07774c65ebb3023536f85df642c44478b540",
    "records": 1112,
    "seed_records": 556,
    "measured_records": 556,
    "trials_per_arm": 7,
    "observations": rows,
    "final_digest": next(iter(digests)),
    "target_hash": next(iter(targets)),
    "wire_requests_per_trial": full[0]["AccessListRequests"],
    "full_catchup_median_ns": full_catch,
    "compact_catchup_median_ns": compact_catch,
    "catchup_speedup": full_catch / compact_catch,
    "full_durable_median_ns": full_durable,
    "compact_durable_median_ns": compact_durable,
    "durable_speedup": full_durable / compact_durable,
    "paired_catchup_ratios": paired_catch,
    "paired_durable_ratios": paired_durable,
    "positive_catchup_pairs": sum(x > 1.0 for x in paired_catch),
    "positive_durable_pairs": sum(x > 1.0 for x in paired_durable),
    "claim_boundary": (
        "pinned geth catchUp using real snap.Peer RequestAccessLists, tracker, "
        "p2p.Send/ReadMsg, SNAP/2 AccessLists RLP encode/decode and HandleMessage, "
        "common full BAL authenticity/hash verification, Pebble writes and final durability; "
        "in-memory MsgPipe excludes TCP/RLPx encryption and network latency; phaseDownload "
        "excludes state-trie root replay"
    ),
    "performance_direction_precommitted": False,
}
out_path.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "catchup_speedup": cert["catchup_speedup"],
    "durable_speedup": cert["durable_speedup"],
    "positive_catchup_pairs": cert["positive_catchup_pairs"],
    "positive_durable_pairs": cert["positive_durable_pairs"],
    "wire_requests_per_trial": cert["wire_requests_per_trial"],
    "final_digest": cert["final_digest"],
}, indent=2, sort_keys=True))
