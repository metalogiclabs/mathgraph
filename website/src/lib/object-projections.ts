/** Internal website view models. These are not evidence or admission schemas. */
import catalog from '../data/record-index.json';
import registry from '../../public/capabilities/index-v1.json';
import type contractShape from '../../../conformance/capability_v1/fixtures/capability-contract.json';
import type evaluationShape from '../../../conformance/capability_v1/evaluation.json';
import type policyShape from '../../../conformance/capability_v1/trust-policy.json';
import type receiptShape from '../../../conformance/capability_v1/receipt.json';
import type { PublishedRecordPackage, SourceCheckPackage, ResolutionSnapshotPackage } from './catalog';
import type { ValidatedSourceCatalogueV1 } from './source-catalogue';
import { canonicalJson, sha256Hex } from './integrity';

export interface SourcePin {
  id: string;
  contract: string;
  version: string;
  locator: string;
  content_sha256?: string;
  transport_sha256?: string;
}
export const objectKinds = ['SOURCE_CHECK', 'RESOLUTION_SNAPSHOT', 'RESOLVE_CLAIM', 'RESOLVE_RECEIPT', 'FINITE_CAPABILITY', 'SOURCE_MODULE', 'SOURCE_DECLARATION'] as const;
export type ObjectKind = typeof objectKinds[number];
export interface ProjectionAxes {
  historical_result: string;
  lifecycle: string;
  research_maturity: string;
  current_applicability: string;
  freshness: string;
  action_authorization: string;
  source_status?: string;
  independent_verification?: string;
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
export const relationTypes = ['EVIDENCE_FOR', 'PREMISE_FOR', 'WITHDRAWS', 'DECLARES', 'IMPORTS_MODULE', 'TYPE_REFERENCES'] as const;
export interface RelationProjection {
  id: string;
  type: typeof relationTypes[number];
  from: string;
  to: string;
  source_id: string;
  target_id: string;
  directed: true;
  authority: 'NONE';
  source_relation_id?: string;
  logical_implication?: false;
  semantic_equivalence?: false;
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
export function objectId(source: SourcePin, id: string): string {
  // Display identities are namespaced by source, never an equivalence assertion.
  return `${source.id}@${source.version}#${encodeURIComponent(id)}`;
}

function sourceAxes(): ProjectionAxes {
  return {
    historical_result: 'UNKNOWN', lifecycle: 'UNKNOWN', research_maturity: 'UNKNOWN',
    current_applicability: 'NOT_CHECKED', freshness: 'PINNED_HISTORICAL_SOURCE',
    action_authorization: 'NONE', source_status: 'SOURCE_INDEXED', independent_verification: 'NOT_CHECKED',
  };
}

/** Validated source bytes become presentation objects only; this adapter creates no warrant. */
export function projectSourceCatalogueV1(catalogue: ValidatedSourceCatalogueV1): ProjectionCollection {
  const { manifest } = catalogue;
  requireProjection(catalogue.result.authority === 'NONE'
    && catalogue.result.source_status === 'SOURCE_INDEXED'
    && catalogue.result.independent_verification === 'NOT_CHECKED', 'SOURCE_CATALOGUE_AUTHORITY_ESCALATION');
  const manifestPin: SourcePin = {
    id: manifest.catalogue_id,
    contract: manifest.schema,
    version: String(manifest.catalogue_version),
    locator: 'https://mathgraph.org/catalogues/mathlib/v4.34.1/manifest.json',
    transport_sha256: catalogue.manifest_sha256,
  };
  const objects: ObjectProjection[] = [];
  const relations: RelationProjection[] = [];
  const endpointIds = new Map<string, string>();
  const shardPins = new Map<string, SourcePin>();
  manifest.shards.forEach(metadata => {
    shardPins.set(metadata.module_id, {
      id: metadata.module_id,
      contract: 'mathgraph.source-catalogue-shard.v1',
      version: '1',
      locator: `https://mathgraph.org/catalogues/mathlib/v4.34.1/${metadata.path}`,
      transport_sha256: metadata.sha256,
    });
  });
  catalogue.shards.forEach((shard, shardIndex) => {
    const pin = shardPins.get(shard.module.module_id)!;
    const moduleProjection: ObjectProjection = {
      ...object(pin, shard.module.module_id, 'SOURCE_MODULE'),
      title: shard.module.module,
      supporting_sources: [manifestPin],
      pointer: `/shards/${shardIndex}/module`,
      axes: sourceAxes(),
      replay_boundary: [shard.module.repository, shard.module.commit, shard.module.tree, shard.module.sha256],
      unknowns: ['independent_verification', 'current_applicability', 'semantic_correspondence'],
      unsupported_semantics: ['logical_implication', 'semantic_equivalence', 'proof_verification', 'action_authorization'],
      details: {
        catalogue_id: manifest.catalogue_id,
        module_id: shard.module.module_id,
        module: shard.module.module,
        path: shard.module.path,
        sha256: shard.module.sha256,
        size_bytes: shard.module.size_bytes,
        source: { repository: shard.module.repository, commit: shard.module.commit, tree: shard.module.tree },
      },
    };
    objects.push(moduleProjection);
    endpointIds.set(shard.module.module_id, moduleProjection.id);
    shard.objects.forEach((declaration, objectIndex) => {
      const projection: ObjectProjection = {
        ...object(pin, declaration.object_id, 'SOURCE_DECLARATION'),
        title: declaration.qualified_name,
        supporting_sources: [manifestPin],
        pointer: `/shards/${shardIndex}/objects/${objectIndex}`,
        axes: sourceAxes(),
        replay_boundary: [declaration.source.repository, declaration.source.commit, declaration.source.tree, declaration.statement_sha256],
        unknowns: ['independent_verification', 'current_applicability', 'semantic_correspondence'],
        unsupported_semantics: ['logical_implication', 'semantic_equivalence', 'proof_verification', 'action_authorization'],
        details: {
          catalogue_id: manifest.catalogue_id,
          module_id: shard.module.module_id,
          qualified_name: declaration.qualified_name,
          declaration_kind: declaration.kind,
          statement: declaration.statement,
          statement_sha256: declaration.statement_sha256,
          source: declaration.source,
          extensions: declaration.extensions,
        },
      };
      objects.push(projection);
      endpointIds.set(declaration.object_id, projection.id);
    });
  });
  catalogue.shards.forEach((shard, shardIndex) => {
    const pin = shardPins.get(shard.module.module_id)!;
    shard.relations.forEach((relation, relationIndex) => {
      relations.push({
        id: objectId(manifestPin, relation.relation_id),
        source_relation_id: relation.relation_id,
        type: relation.type,
        from: endpointIds.get(relation.source_id)!,
        to: endpointIds.get(relation.target_id)!,
        source_id: relation.source_id,
        target_id: relation.target_id,
        directed: true,
        authority: 'NONE',
        logical_implication: false,
        semantic_equivalence: false,
        provenance: { source: pin, pointer: `/shards/${shardIndex}/relations/${relationIndex}` },
      });
    });
  });
  return structuredClone({ objects, relations });
}

export function mergeProjectionCollections(
  fragments: ProjectionCollection[],
  options: { slugger?: (id: string) => string } = {},
): ProjectionCollection {
  const objects = fragments.flatMap(fragment => fragment.objects);
  const relations = fragments.flatMap(fragment => fragment.relations);
  const projectionIds = new Set<string>();
  const sourceObjectIds = new Set<string>();
  const canonicalNames = new Set<string>();
  const routeSlugs = new Set<string>();
  const slugger = options.slugger ?? ((id: string) => `object-${sha256Hex(id)}`);
  for (const item of objects) {
    requireProjection(!projectionIds.has(item.id), 'PROJECTION_ID_COLLISION');
    projectionIds.add(item.id);
    requireProjection(!sourceObjectIds.has(item.source_id), 'SOURCE_OBJECT_ID_COLLISION');
    sourceObjectIds.add(item.source_id);
    const qualifiedName = typeof item.details.qualified_name === 'string' ? item.details.qualified_name : item.title;
    requireProjection(!canonicalNames.has(qualifiedName), 'CANONICAL_NAME_COLLISION');
    canonicalNames.add(qualifiedName);
    const slug = slugger(item.id);
    requireProjection(!routeSlugs.has(slug), 'OBJECT_ROUTE_COLLISION');
    routeSlugs.add(slug);
  }
  const relationIds = new Set<string>();
  const sourceRelationIds = new Set<string>();
  for (const relation of relations) {
    requireProjection(!relationIds.has(relation.id), 'RELATION_ID_COLLISION');
    relationIds.add(relation.id);
    if (relation.source_relation_id !== undefined) {
      requireProjection(!sourceRelationIds.has(relation.source_relation_id), 'SOURCE_RELATION_ID_COLLISION');
      sourceRelationIds.add(relation.source_relation_id);
    }
  }
  return structuredClone({ objects, relations });
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
