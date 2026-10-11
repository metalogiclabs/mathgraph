/** Internal website view models. These are not evidence or admission schemas. */
import catalog from '../data/record-index.json';
import registry from '../../public/capabilities/index-v1.json';
import type contractShape from '../../../conformance/capability_v1/fixtures/capability-contract.json';
import type evaluationShape from '../../../conformance/capability_v1/evaluation.json';
import type policyShape from '../../../conformance/capability_v1/trust-policy.json';
import type receiptShape from '../../../conformance/capability_v1/receipt.json';
import type { PublishedRecordPackage, SourceCheckPackage, ResolutionSnapshotPackage } from './catalog';
import { canonicalJson, sha256Hex } from './integrity';

export interface SourcePin {
  id: string;
  contract: string;
  version: string;
  locator: string;
  content_sha256?: string;
  transport_sha256?: string;
}
export const objectKinds = ['SOURCE_CHECK', 'RESOLUTION_SNAPSHOT', 'RESOLVE_CLAIM', 'RESOLVE_RECEIPT', 'FINITE_CAPABILITY'] as const;
export type ObjectKind = typeof objectKinds[number];
export interface ProjectionAxes {
  historical_result: string;
  lifecycle: string;
  research_maturity: string;
  current_applicability: string;
  freshness: string;
  action_authorization: string;
}
export interface ObjectProjection {
  id: string;
  source_id: string;
  kind: ObjectKind;
  title: string;
  authority: 'NONE';
  source: SourcePin;
  supporting_sources: SourcePin[];
  pointer: string;
  axes: ProjectionAxes;
  verifier_authority: string[];
  assumptions: string[];
  replay_boundary: string[];
  unknowns: string[];
  unsupported_semantics: string[];
  details: Record<string, unknown>;
}
export const relationTypes = ['EVIDENCE_FOR', 'PREMISE_FOR', 'WITHDRAWS'] as const;
export interface RelationProjection {
  id: string;
  type: typeof relationTypes[number];
  from: string;
  to: string;
  source_id: string;
  target_id: string;
  directed: true;
  authority: 'NONE';
  provenance: { source: SourcePin; pointer: string };
}
export interface ProjectionCollection { objects: ObjectProjection[]; relations: RelationProjection[] }
export interface FiniteCapabilityArtifacts {
  contractBytes: Uint8Array;
  evaluationBytes: Uint8Array;
  policyBytes: Uint8Array;
  receiptBytes: Uint8Array;
}

const catalogPin: SourcePin = {
  id: 'mathgraph.record-index.v2', contract: catalog.schema, version: '2',
  locator: 'https://mathgraph.org/records/index.json',
  // Canonical content hash, explicitly distinct from a transport-byte digest.
  content_sha256: sha256Hex(canonicalJson(catalog)),
};
function requireProjection(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}
function recordPin(pkg: PublishedRecordPackage): SourcePin {
  return { id: pkg.entry.id, contract: pkg.entry.record_schema, version: String(pkg.entry.version), locator: pkg.entry.record_json_url, content_sha256: pkg.entry.record_content_sha256, transport_sha256: pkg.entry.record_transport_sha256 };
}
function objectId(source: SourcePin, id: string): string {
  // Display identities are namespaced by source, never an equivalence assertion.
  return `${source.id}@${source.version}#${encodeURIComponent(id)}`;
}
function object(source: SourcePin, id: string, kind: ObjectKind): ObjectProjection {
  return { id: objectId(source, id), source_id: id, kind, title: id, authority: 'NONE', source, supporting_sources: [], pointer: '', axes: { historical_result: 'UNKNOWN', lifecycle: 'UNKNOWN', research_maturity: 'UNKNOWN', current_applicability: 'UNKNOWN', freshness: 'NOT_CHECKED', action_authorization: 'NONE' }, verifier_authority: [], assumptions: [], replay_boundary: [], unknowns: [], unsupported_semantics: [], details: {} };
}

/** Input packages come from the existing catalog validator; no new admission occurs. */
export function projectPublishedRecord(pkg: PublishedRecordPackage): ProjectionCollection {
  requireProjection(pkg.record_kind === 'SOURCE_CHECK' || pkg.record_kind === 'RESOLUTION_SNAPSHOT', 'UNSUPPORTED_PROJECTION_KIND');
  requireProjection(pkg.entry.version === 1, 'UNSUPPORTED_PROJECTION_VERSION');
  if (pkg.record_kind === 'SOURCE_CHECK') return projectSourceCheckV1(pkg);
  return projectResolveSnapshotV1(pkg);
}

export function projectSourceCheckV1(pkg: SourceCheckPackage): ProjectionCollection {
  requireProjection(pkg.entry.version === 1 && pkg.record.schema === 'mathgraph.public-consequence-record.v1' && pkg.entry.record_schema === pkg.record.schema, 'UNSUPPORTED_PROJECTION_VERSION');
  const { record, entry } = pkg;
  const projected = object(recordPin(pkg), record.id, 'SOURCE_CHECK');
  projected.title = record.title;
  projected.supporting_sources = [catalogPin];
  projected.axes = { historical_result: entry.historic_status, lifecycle: entry.lifecycle, research_maturity: 'UNKNOWN', current_applicability: 'UNKNOWN', freshness: record.axes.current_requalification.status, action_authorization: 'NONE' };
  projected.verifier_authority = [record.axes.finite_executable.authority, record.axes.formal_verification.authority];
  projected.assumptions = [record.axes.finite_executable.case_scope, record.axes.formal_verification.scope];
  projected.replay_boundary = [record.source.commit, record.source.external_suite_commit, record.source.lean_toolchain];
  projected.unknowns = entry.unknowns;
  projected.unsupported_semantics = entry.unknowns;
  projected.details = { axes: record.axes, admission: record.admission, source: record.source, scope: entry.scope };
  return structuredClone({ objects: [projected], relations: [] });
}

export function projectResolveSnapshotV1(pkg: ResolutionSnapshotPackage): ProjectionCollection {
  requireProjection(pkg.entry.version === 1 && pkg.record.schema === 'mathgraph.living-warrant-snapshot.v1' && pkg.entry.record_schema === pkg.record.schema, 'UNSUPPORTED_PROJECTION_VERSION');
  const { record, entry } = pkg;
  const source = recordPin(pkg);
  const root = object(source, record.id, 'RESOLUTION_SNAPSHOT');
  root.supporting_sources = [catalogPin];
  root.axes = { historical_result: entry.historical_epistemic_result, lifecycle: entry.lifecycle, research_maturity: entry.research_maturity, current_applicability: entry.current_applicability, freshness: entry.freshness, action_authorization: entry.action_policy };
  root.verifier_authority = Object.values(record.derivation.receipt_admission);
  root.assumptions = [record.interpretation.source_contract];
  root.replay_boundary = [record.snapshot_sha256, record.sources.openai.byte_sha256, record.sources.jpl_record_sha256];
  root.unknowns = entry.unknowns;
  root.unsupported_semantics = [record.publisher_notice.does_not_imply, record.interpretation.runtime_status];
  root.details = { interpretation: record.interpretation, sources: record.sources, publisher_notice: record.publisher_notice };
  const objects = [root];
  record.derivation.claims.forEach((claim, index) => {
    const resolution = record.resolutions[claim.id as keyof typeof record.resolutions];
    objects.push({
      ...root, id: objectId(source, claim.id), source_id: claim.id, kind: 'RESOLVE_CLAIM', title: claim.id,
      pointer: `/derivation/claims/${index}`,
      axes: { ...root.axes, historical_result: resolution.after, lifecycle: 'UNKNOWN', research_maturity: 'UNKNOWN' },
      // A resolution is not an independent verifier declaration for this claim.
      verifier_authority: ['UNKNOWN'], details: { ...claim, resolution },
    });
  });
  record.derivation.receipts.forEach((receipt, index) => {
    objects.push({
      ...root, id: objectId(source, receipt.id), source_id: receipt.id, kind: 'RESOLVE_RECEIPT', title: receipt.id,
      pointer: `/derivation/receipts/${index}`,
      axes: { ...root.axes, historical_result: 'UNKNOWN', research_maturity: 'UNKNOWN', lifecycle: record.derivation.withdrawn_evidence.includes(receipt.id) ? 'WITHDRAWN' : 'UNKNOWN' },
      verifier_authority: [record.derivation.receipt_admission[receipt.kind as keyof typeof record.derivation.receipt_admission]],
      details: { ...receipt },
    });
  });
  const relations: RelationProjection[] = [];
  function edge(type: RelationProjection['type'], from: string, to: string, pointer: string) {
    relations.push({ id: `${source.id}@${source.version}:${pointer}`, type, from: objectId(source, from), to: objectId(source, to), source_id: from, target_id: to, directed: true, authority: 'NONE', provenance: { source, pointer } });
  }
  record.derivation.routes.forEach((route, index) => {
    route.evidence.forEach((id, position) => edge('EVIDENCE_FOR', id, route.conclusion, `/derivation/routes/${index}/evidence/${position}`));
    route.premises.forEach((id, position) => edge('PREMISE_FOR', id, route.conclusion, `/derivation/routes/${index}/premises/${position}`));
  });
  record.derivation.withdrawn_evidence.forEach((id, index) => edge('WITHDRAWS', record.id, id, `/derivation/withdrawn_evidence/${index}`));
  return structuredClone({ objects, relations });
}

/** Exact-byte, finite-profile-only display adapter; does not execute a verifier. */
export function projectFiniteCapabilityV1(artifacts: FiniteCapabilityArtifacts): ProjectionCollection {
  const contract = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(artifacts.contractBytes)) as typeof contractShape;
  requireProjection(contract.schema_version === 'mathgraph.capability-contract.v1' && contract.version === '1' && contract.profile === 'mathgraph.finite-representation-refinement.v1', 'UNSUPPORTED_PROJECTION_VERSION');
  requireProjection(Array.isArray(contract.extensions), 'INVALID_CAPABILITY_EXTENSIONS');
  requireProjection(!contract.extensions.some((extension: { critical?: boolean }) => extension.critical), 'UNSUPPORTED_CRITICAL_EXTENSION');
  const entry = registry.qualified_entries[0];
  function pinned<T>(bytes: Uint8Array, reference: { id: string; locator: string; sha256: string; size_bytes: number }, schema: string): { value: T; pin: SourcePin } {
    requireProjection(bytes.byteLength === reference.size_bytes && sha256Hex(bytes) === reference.sha256, 'CAPABILITY_SOURCE_PIN_MISMATCH');
    const value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    requireProjection(value.schema_version === schema, 'UNSUPPORTED_PROJECTION_VERSION');
    return { value, pin: { id: reference.id, locator: reference.locator, transport_sha256: reference.sha256, contract: schema, version: '1' } };
  }
  const primary = pinned<typeof contractShape>(artifacts.contractBytes, entry.contract, 'mathgraph.capability-contract.v1');
  const evaluation = pinned<typeof evaluationShape>(artifacts.evaluationBytes, entry.evaluation, 'mathgraph.capability-evaluation.v1');
  const policy = pinned<typeof policyShape>(artifacts.policyBytes, entry.trust_policy, 'mathgraph.finite-trust-policy.v1');
  const receipt = pinned<typeof receiptShape>(artifacts.receiptBytes, entry.qualification_receipt, 'mathgraph.finite-qualification-receipt.v1');
  const projected = object(primary.pin, contract.id, 'FINITE_CAPABILITY');
  projected.supporting_sources = [evaluation.pin, policy.pin, receipt.pin];
  projected.axes = { historical_result: evaluation.value.qualification, lifecycle: 'UNKNOWN', research_maturity: 'UNKNOWN', current_applicability: evaluation.value.current_applicability, freshness: evaluation.value.freshness, action_authorization: evaluation.value.action_authorization };
  projected.verifier_authority = [policy.value.verifier.id, policy.value.qualification_basis];
  projected.assumptions = contract.assumptions;
  projected.replay_boundary = [contract.boundary.sha256, policy.value.verifier.sha256];
  projected.unknowns = ['current_applicability', 'freshness', 'revocation', 'supersession'];
  projected.unsupported_semantics = contract.limitations;
  projected.details = { claim: contract.claim, preconditions: contract.preconditions, guarantees: contract.guarantees, limitations: contract.limitations, inputs: contract.inputs, outputs: contract.outputs, boundary: contract.boundary, implementation: contract.implementation, evidence: contract.evidence, evaluation: evaluation.value };
  return structuredClone({ objects: [projected], relations: [] });
}
