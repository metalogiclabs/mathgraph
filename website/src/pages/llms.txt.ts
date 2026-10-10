import type { APIRoute } from 'astro';

import { loadPublishedRecords } from '../lib/catalog';

export const prerender = true;

export const GET: APIRoute = async () => {
  const [{ entry }] = await loadPublishedRecords();
  const body = `# MathGraph

> Evidence you can inspect. Results you can reuse.

Human agent guide: https://mathgraph.org/agents/
Discovery manifest: https://mathgraph.org/.well-known/mathgraph.json
Record index: https://mathgraph.org/records/index.json
Current record schema: https://mathgraph.org/schemas/public-consequence-record-v1.schema.json
Record index schema: https://mathgraph.org/schemas/record-index-v1.schema.json
Presentation metadata schema: https://mathgraph.org/schemas/presentation-metadata-v1.schema.json
Proposed Lean profile: https://mathgraph.org/schemas/lean-evidence-profile-draft-1.schema.json

Qualified immutable record:
- ${entry.record_json_url}
- Permanent page: ${entry.record_page_url}
- Canonical content SHA-256: ${entry.record_content_sha256}

Usage boundary:
- Match the exact record ID, version, source pin, suite pin, and supported goal.
- Any mismatch or unsupported claim is UNKNOWN; never borrow a nearby warrant.
- A digest establishes integrity and byte identity, not host authenticity or semantic truth.
- Treat generated_at as publication time. Set fetched_at when the record index is received and re-fetch before max_age_seconds elapse.
- Qualified record evidence bytes remain immutable; lifecycle and presentation metadata may be updated separately with history.
- The public resolver and MCP endpoint are not deployed.
`;
  return new Response(body, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
};
