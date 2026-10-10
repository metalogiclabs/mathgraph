import Ajv from 'ajv';
import snapshotSchema from '../../public/schemas/living-warrant-snapshot-v1.schema.json';
import scenariosSchema from '../../public/schemas/resolve-scenarios-v1.schema.json';
import type snapshot from '../../public/evidence/mg-living-warrant-openai-jpl-20261010/record.json';
import type scenarios from '../../public/evidence/mg-living-warrant-openai-jpl-20261010/scenarios.json';
import { canonicalContentDigest, canonicalJson, sha256Hex } from './integrity';

export type ResolveSnapshot = typeof snapshot;
export type ResolveScenarios = typeof scenarios;

// Separately reviewed publication authority, not values supplied by the index,
// payload, presentation sidecar, or a recomputed self-hash.
export const RESOLVE_AUTHORITY = Object.freeze({
  id: 'mg-living-warrant-openai-jpl-20261010',
  recordSchema: 'mathgraph.living-warrant-snapshot.v1',
  scenariosSchema: 'mathgraph.resolve-scenarios.v1',
  transport: '0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87',
  snapshot: 'b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41',
  scenarios: 'ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181',
  independentReplayCiRun: '38086245988',
});

const ajv = new Ajv({ allErrors: true, strict: true });
const validateSnapshot = ajv.compile(snapshotSchema);
const validateScenarios = ajv.compile(scenariosSchema);
function requireResolve(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}
function same(left: unknown, right: unknown): boolean {
  return canonicalJson(left) === canonicalJson(right);
}
function sorted(values: unknown[]): unknown[] {
  return [...values].sort((a, b) => canonicalJson(a).localeCompare(canonicalJson(b)));
}

/** Structural/semantic assertions over published data; never a resolution engine.
 * This function alone is not admission: validateResolveArtifacts additionally
 * gates the exact reviewed transports and the canonical payload digest.
 */
export function validateResolveAgreement(recordValue: unknown, scenariosValue: unknown): {
  record: ResolveSnapshot; scenarios: ResolveScenarios;
} {
  requireResolve(validateSnapshot(recordValue), 'RESOLVE_SNAPSHOT_SCHEMA_INVALID');
  requireResolve(validateScenarios(scenariosValue), 'RESOLVE_SCENARIOS_SCHEMA_INVALID');
  const record = recordValue as ResolveSnapshot;
  const scenarios = scenariosValue as ResolveScenarios;
  requireResolve(record.snapshot_sha256 === canonicalContentDigest(record as unknown as Record<string, unknown>, 'snapshot_sha256'), 'RESOLVE_CANONICAL_DIGEST_INVALID');
  requireResolve(scenarios.record_id === record.id && scenarios.snapshot_sha256 === record.snapshot_sha256 && scenarios.transport_sha256 === RESOLVE_AUTHORITY.transport, 'RESOLVE_RECORD_SCENARIO_IDENTITY_MISMATCH');

  const expectedClaims = record.publisher_notice.documents.flatMap((document, index) => [
    { id: `openai.original_support.${index + 1}`, kind: 'documentary', scope: `openai/math:${document.name}:original-withdrawn-edition` },
    { id: `openai.theorem.${index + 1}`, kind: 'formal', scope: `openai/math:${document.name}:original-withdrawn-edition` },
  ]);
  expectedClaims.push({ id: 'jpl.l4yaml.finite_parser_acceptance', kind: 'formal', scope: 'nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases' });
  requireResolve(same(sorted(record.derivation.claims), sorted(expectedClaims)), 'RESOLVE_CLAIM_PROFILE_MISMATCH');
  const expectedResolutions = Object.fromEntries(expectedClaims.map(claim => [claim.id,
    claim.kind === 'documentary' ? { before: 'SOURCE_DOCUMENTED', after: 'STALE', changed: true }
      : claim.id.startsWith('jpl.') ? { before: 'WARRANTED_BOUNDED', after: 'WARRANTED_BOUNDED', changed: false }
        : { before: 'UNKNOWN', after: 'UNKNOWN', changed: false },
  ]));
  requireResolve(same(record.resolutions, expectedResolutions), 'RESOLVE_HISTORICAL_OUTCOME_MISMATCH');
  const graph = scenarios.PUBLISHED_RECORD.graph;
  for (const key of ['claims', 'receipts', 'routes'] as const) {
    requireResolve(same(sorted(graph[key]), sorted(record.derivation[key])), 'RESOLVE_GRAPH_DISAGREEMENT');
  }
  const published = scenarios.PUBLISHED_RECORD.scenarios.find(item => item.id === 'published-after');
  requireResolve(published !== undefined && published.basis === 'PUBLISHED_AFTER', 'RESOLVE_PUBLISHED_SCENARIO_MISSING');
  requireResolve(same(published.resolutions, record.resolutions) && same(published.withdrawn_evidence, record.derivation.withdrawn_evidence), 'RESOLVE_PUBLISHED_SCENARIO_DISAGREEMENT');
  const expectedStates = Object.fromEntries(expectedClaims.map(claim => [claim.id, claim.id.startsWith('jpl.') ? 'WARRANTED_BOUNDED' : 'UNKNOWN']));
  requireResolve(same(published.states, expectedStates), 'RESOLVE_PUBLISHED_STATES_MISMATCH');
  const historicalIds = expectedClaims.map(claim => claim.id).sort();
  for (const scenario of scenarios.PUBLISHED_RECORD.scenarios) {
    requireResolve(same(Object.keys(scenario.states).sort(), historicalIds) && same(Object.keys(scenario.resolutions).sort(), historicalIds), 'RESOLVE_HISTORICAL_SYNTHETIC_MIX');
  }
  const historicalObjectIds = new Set([
    ...historicalIds,
    ...graph.receipts.map(receipt => receipt.id),
    ...graph.routes.flatMap(route => [route.conclusion, ...route.premises, ...route.evidence]),
  ]);
  for (const scenario of scenarios.SYNTHETIC_CONFORMANCE.scenarios) {
    const { claims, receipts, routes } = scenario.graph;
    const claimIds = new Set(claims.map(claim => claim.id));
    const receiptIds = new Set(receipts.map(receipt => receipt.id));
    requireResolve(
      [...claims, ...receipts].every(item => item.scope === 'synthetic-conformance' && !historicalObjectIds.has(item.id)),
      'RESOLVE_HISTORICAL_SYNTHETIC_MIX',
    );
    requireResolve(
      claimIds.size === claims.length && receiptIds.size === receipts.length &&
      [...claimIds].every(id => !receiptIds.has(id)),
      'RESOLVE_SYNTHETIC_DUPLICATE_IDENTITY',
    );
    // V1 routes have no independent IDs: their conclusion/premise/evidence
    // tuple is their identity. Validate references, not dependency closure.
    const internallyReferential = (route: { conclusion: string; premises: string[]; evidence: string[] }): boolean =>
      claimIds.has(route.conclusion) && route.premises.every(id => claimIds.has(id)) &&
      route.evidence.every(id => receiptIds.has(id));
    requireResolve(routes.every(internallyReferential), 'RESOLVE_SYNTHETIC_ROUTE_REFERENCE_INVALID');
    requireResolve(
      scenario.active_routes.every(route => internallyReferential(route) && routes.some(candidate => same(candidate, route))),
      'RESOLVE_SYNTHETIC_ACTIVE_ROUTE_INVALID',
    );
    requireResolve(scenario.withdrawn_evidence.every(id => receiptIds.has(id)), 'RESOLVE_SYNTHETIC_WITHDRAWAL_REFERENCE_INVALID');
    const expectedKeys = [...claimIds].sort();
    requireResolve(
      same(Object.keys(scenario.states).sort(), expectedKeys) && same(Object.keys(scenario.resolutions).sort(), expectedKeys),
      'RESOLVE_SYNTHETIC_STATE_REFERENCE_INVALID',
    );
  }
  return { record, scenarios };
}

export function validateResolveArtifacts(
  entry: { id: string; version: number; record_schema: string; record_transport_sha256: string; record_content_sha256: string; scenarios_schema: string; scenarios_transport_sha256: string },
  artifacts: { recordBytes: Uint8Array; scenariosBytes?: Uint8Array },
): { record: ResolveSnapshot; scenarios: ResolveScenarios } {
  requireResolve(entry.id === RESOLVE_AUTHORITY.id && entry.version === 1 && entry.record_schema === RESOLVE_AUTHORITY.recordSchema && entry.scenarios_schema === RESOLVE_AUTHORITY.scenariosSchema, 'RESOLVE_UNSUPPORTED_IDENTITY');
  requireResolve(entry.record_transport_sha256 === RESOLVE_AUTHORITY.transport && sha256Hex(artifacts.recordBytes) === RESOLVE_AUTHORITY.transport && artifacts.recordBytes.length === 5290, 'RESOLVE_RECORD_TRANSPORT_NOT_AUTHORIZED');
  requireResolve(entry.record_content_sha256 === RESOLVE_AUTHORITY.snapshot, 'RESOLVE_SNAPSHOT_NOT_AUTHORIZED');
  requireResolve(artifacts.scenariosBytes !== undefined && entry.scenarios_transport_sha256 === RESOLVE_AUTHORITY.scenarios && sha256Hex(artifacts.scenariosBytes) === RESOLVE_AUTHORITY.scenarios, 'RESOLVE_SCENARIOS_TRANSPORT_NOT_AUTHORIZED');
  // JSON.parse cannot detect duplicate keys. These public artifacts must pass
  // exact external byte pins before parsing; arbitrary JSON is not admitted.
  const record = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(artifacts.recordBytes));
  const scenarios = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(artifacts.scenariosBytes));
  const result = validateResolveAgreement(record, scenarios);
  requireResolve(result.record.snapshot_sha256 === RESOLVE_AUTHORITY.snapshot, 'RESOLVE_SNAPSHOT_NOT_AUTHORIZED');
  return result;
}
