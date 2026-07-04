# SorryDB v4.4.0 Exact-Source Candidate Miner

## Purpose

v4.4.0 converts accepted v4.3.8 replay manifests and certificates into v4.3.5-compatible queue entries. It admits a row only when:

- the manifest and certificate both record `PATCH_ACCEPTED` with return code 0;
- certificate identity, file path, source snippet, and patch snippet agree;
- the source snippet occurs exactly once in the target source file;
- that snippet contains exactly one `sorry`; and
- the exact sorry line falls inside a supplied known sorry span.

Invalid, missing, ambiguous, or inconsistent evidence becomes a `NAMED_OBSTRUCTION`. Candidate rows are not accepted mathematical claims.

## Output

The checked-in output is:

`artifacts/sorrydb/mined_queues/sorrydb_v4_4_0_exact_source_candidates.json`

Its `candidates` array is directly consumable by the v4.3.5 JSON queue runner. Extra span and provenance fields are retained for auditability.

## Reproduce

```bash
python experiments/sorrydb/sorrydb_v4_4_0_exact_source_candidate_miner.py \
  --source-file /path/to/recorded-checkout/MetaExamples/Fiddle.lean \
  --known-span 97 \
  --known-span 99
```

The miner reads source text and JSON only. It does not invoke Lean, Lake, Git, or network services.

## Bounded claim

The miner can generate valid queue entries from exact source/patch/certificate rows.

It does not claim:

- new proof discovery;
- general SorryDB mining; or
- upstream automation.
