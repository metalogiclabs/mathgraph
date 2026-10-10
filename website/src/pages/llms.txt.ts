import type { APIRoute } from 'astro';

import { loadPublishedRecords } from '../lib/catalog';

export const prerender = true;

export const GET: APIRoute = async () => {
  const published = await loadPublishedRecords();
  const sourceCheck = published.find((item) => item.record_kind === 'SOURCE_CHECK');
  const resolve = published.find((item) => item.record_kind === 'RESOLUTION_SNAPSHOT');
  if (!sourceCheck || !resolve) throw new Error('PUBLIC_DISCOVERY_RECORDS_MISSING');
  const sourceEntry = sourceCheck.entry;
  const resolveEntry = resolve.entry;
  const body = `# MathGraph

> Evidence you can inspect. Results you can reuse.

Human agent guide: https://mathgraph.org/agents/
Discovery manifest: https://mathgraph.org/.well-known/mathgraph.json
Record index: https://mathgraph.org/records/index.json
Discovery schema: https://mathgraph.org/schemas/discovery-v2.schema.json
Historical discovery schema: https://mathgraph.org/schemas/discovery-v1.schema.json
Source-check record schema: https://mathgraph.org/schemas/public-consequence-record-v1.schema.json
Record index schema: https://mathgraph.org/schemas/record-index-v2.schema.json
Historical index schema: https://mathgraph.org/schemas/record-index-v1.schema.json
Resolution snapshot schema: https://mathgraph.org/schemas/living-warrant-snapshot-v1.schema.json
Precomputed scenarios schema: https://mathgraph.org/schemas/resolve-scenarios-v1.schema.json
Presentation metadata schema: https://mathgraph.org/schemas/presentation-metadata-v1.schema.json
Proposed Lean profile: https://mathgraph.org/schemas/lean-evidence-profile-draft-1.schema.json

Published immutable records:

1. ${sourceEntry.id} (${sourceEntry.record_kind})
- Record schema: ${sourceEntry.record_schema}
- Permanent page: ${sourceEntry.record_page_url}
- Record JSON: ${sourceEntry.record_json_url}
- Canonical content SHA-256: ${sourceEntry.record_content_sha256}
- Transport SHA-256: ${sourceEntry.record_transport_sha256}

2. ${resolveEntry.id} (${resolveEntry.record_kind})
- Record schema: ${resolveEntry.record_schema}
- Permanent page: ${resolveEntry.record_page_url}
- Record JSON: ${resolveEntry.record_json_url}
- Canonical content SHA-256: ${resolveEntry.record_content_sha256}
- Transport SHA-256: ${resolveEntry.record_transport_sha256}
- Scenarios schema: ${resolveEntry.scenarios_schema}
- Precomputed scenarios: ${resolveEntry.scenarios_json_url}
- Scenarios transport SHA-256: ${resolveEntry.scenarios_transport_sha256}
- Offline Python consumer: https://mathgraph.org/evidence/${resolveEntry.id}/offline/consumer.py
- Offline consumer SHA-256: 27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b
- Offline bundle: https://mathgraph.org/evidence/${resolveEntry.id}/offline/bundle.json
- Offline bundle SHA-256: 957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62
- Separately pinned trust policy: https://mathgraph.org/evidence/${resolveEntry.id}/offline/trust-policy.json
- Trust policy SHA-256: 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
- Deterministic replay output SHA-256: 8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668
- TypeScript HTTP reference consumer: https://mathgraph.org/examples/resolve-consumer-v1.ts
- TypeScript consumer SHA-256: e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e

Usage boundary:
- For record 001, match the exact record ID, version, source pin, suite pin, and supported goal.
- For record 002, replay the pinned bundle against the separately trusted policy; do not accept producer-reported states as resolution authority.
- Any mismatch, unsupported claim, unknown type, or unsupported transport is UNKNOWN or an explicit error; never borrow a nearby warrant.
- A digest establishes integrity and byte identity, not host authenticity or semantic truth.
- Treat generated_at as publication time. Set fetched_at when the record index is received and re-fetch before max_age_seconds elapse.
- Qualified record evidence bytes remain immutable; lifecycle and presentation metadata may be updated separately with history.
- Record 002 current applicability is UNKNOWN and freshness is NOT_CHECKED in the offline replay.
- Public resolver: NOT_DEPLOYED. MCP: PROPOSED. Discover and Develop public protocol interfaces are NOT_DEPLOYED. The Capabilities registry is PROPOSED with no P0 entries.
`;
  return new Response(body, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
};
