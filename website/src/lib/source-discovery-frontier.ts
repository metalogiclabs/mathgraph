import type {
  SourceCatalogueAxesV1,
  SourceCatalogueShardV1,
  SourceOccurrenceV1,
  ValidatedSourceCatalogueV1,
} from './source-catalogue';

const manifestSha256 = '5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68';
const repository = 'https://github.com/leanprover-community/mathlib4';
const commit = 'd13f23b723b8a846827a245b89c10fc7d3f11612';
const tree = 'efa132418a56d0e38c56cc412a06df22178dac5c';
const moduleName = 'Mathlib.Analysis.SpecialFunctions.Pow.Real';
const moduleId = 'module-2d8fe50987a31597b7d92dbbb999e73cf6653b18d141100c8d68b3cad5608da8';
const modulePath = 'Mathlib/Analysis/SpecialFunctions/Pow/Real.lean';
const moduleSha256 = '5f4970fe329b14615ca6cfa3e0dcb0cf9d2017c98d2e3501237412aa2474e70b';
const shardSha256 = '6400eba377e910ff2ac4bea415657e6c84b546832d93808c9fcb9dce952d22c0';
const shardPath = `shards/${shardSha256}.json`;
const sourceName = 'Real.log_rpow';
const sourceId = 'object-8d7d18f07e0f6262a3b65bbb71105c16c69ab67a6d96a78c18e97cfa7afc2322';
const statementSha256 = 'cbb5d6bc3ea24d4f3231fdcb221756eba154e15179f5529d3dc2ecad41dc6d88';
const targetName = 'Real.log';

const exactAxes = {
  source_status: 'SOURCE_INDEXED',
  verification_status: 'NOT_CHECKED',
  current_applicability: 'NOT_CHECKED',
  freshness: 'PINNED_HISTORICAL_SOURCE',
  authorization: 'NONE',
  authority: 'NONE',
} as const;

export interface SourceDiscoveryFrontierV1 {
  schema: 'mathgraph.website-source-discovery-frontier.v1';
  frontier_id: 'mathlib-v4.34.1-real-log-source-gap';
  classification: 'ADVISORY';
  completeness: 'INCOMPLETE';
  terminal_form: 'NONE';
  axes: {
    source_status: 'SOURCE_INDEXED';
    independent_verification: 'NOT_CHECKED';
    current_applicability: 'NOT_CHECKED';
    freshness: 'PINNED_HISTORICAL_SOURCE';
    authority: 'NONE';
    authorization: 'NONE';
  };
  source: {
    qualified_name: 'Real.log_rpow';
    object_id: string;
    statement_sha256: string;
    module: string;
    path: string;
    lines: { start: number; end: number };
    object_url: string;
    source_url: string;
  };
  omitted_target: {
    qualified_name: 'Real.log';
    occurrence_present: false;
    selected_pair_present: true;
    unique_omitting_sources: 42;
    relation_status: 'NOT_PUBLISHED';
    logical_implication: false;
    semantic_equivalence: false;
  };
  publication: {
    manifest_url: string;
    manifest_sha256: string;
    shard_url: string;
    shard_sha256: string;
  };
  gates: {
    catalogue_expansion: {
      status: 'NOT_RUN';
      result_if_successful: 'SOURCE_INDEXED';
      obligation: string;
    };
    lean_proof_check: {
      status: 'NOT_RUN';
      result_if_successful: 'SEPARATE_EVIDENCE_RECEIPT_REQUIRED';
      obligation: string;
    };
  };
}

function requireFrontier(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}

function hasExactAxes(value: SourceCatalogueAxesV1): boolean {
  return value.source_status === exactAxes.source_status
    && value.verification_status === exactAxes.verification_status
    && value.current_applicability === exactAxes.current_applicability
    && value.freshness === exactAxes.freshness
    && value.authorization === exactAxes.authorization
    && value.authority === exactAxes.authority;
}

function selectExactShard(catalogue: ValidatedSourceCatalogueV1): SourceCatalogueShardV1 {
  const manifestModule = catalogue.manifest.modules.find(value => value.module === moduleName);
  const shardMetadata = catalogue.manifest.shards.find(value => value.module_id === moduleId);
  requireFrontier(manifestModule !== undefined
    && manifestModule.module_id === moduleId
    && manifestModule.path === modulePath
    && manifestModule.sha256 === moduleSha256
    && manifestModule.size_bytes === 50134
    && shardMetadata !== undefined
    && shardMetadata.path === shardPath
    && shardMetadata.sha256 === shardSha256
    && shardMetadata.size_bytes === 843725
    && shardMetadata.object_count === 216
    && shardMetadata.relation_count === 395
    && shardMetadata.omitted_type_references === 3045
    && shardMetadata.omitted_imports === 4
    && shardMetadata.omitted_declarations === 44,
  'DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');
  const shards = catalogue.shards.filter(value => value.module.module_id === moduleId);
  requireFrontier(shards.length === 1
    && shards[0].module.module === moduleName
    && shards[0].module.path === modulePath
    && shards[0].module.sha256 === moduleSha256,
  'DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');
  return shards[0];
}

function selectExactSource(shard: SourceCatalogueShardV1): SourceOccurrenceV1 {
  const matches = shard.objects.filter(value => value.qualified_name === sourceName);
  requireFrontier(matches.length === 1, 'DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');
  const source = matches[0];
  requireFrontier(source.object_id === sourceId
    && source.kind === 'theorem'
    && source.statement_sha256 === statementSha256
    && source.source.repository === repository
    && source.source.commit === commit
    && source.source.tree === tree
    && source.source.module === moduleName
    && source.source.path === modulePath
    && source.source.range.start.line === 491
    && source.source.range.start.column === 0
    && source.source.range.start.byte === 20408
    && source.source.range.end.line === 496
    && source.source.range.end.column === 100
    && source.source.range.end.byte === 20795,
  'DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');
  return source;
}

/**
 * Derive one advisory frontier from the already validated, immutable catalogue.
 * This is a build-time view of a named omission, not evidence or a verifier.
 */
export function deriveSourceDiscoveryFrontierV1(catalogue: ValidatedSourceCatalogueV1): SourceDiscoveryFrontierV1 {
  requireFrontier(catalogue.manifest_sha256 === manifestSha256
    && catalogue.manifest.schema === 'mathgraph.source-catalogue-manifest.v1'
    && catalogue.manifest.catalogue_version === 1
    && catalogue.manifest.catalogue_id === 'mathlib-v4.34.1-foundations-v1'
    && catalogue.manifest.source.repository === repository
    && catalogue.manifest.source.commit === commit
    && catalogue.manifest.source.tree === tree
    && catalogue.manifest.source.lean_toolchain.value === 'leanprover/lean4:v4.34.1',
  'DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');
  requireFrontier(hasExactAxes(catalogue.manifest)
    && catalogue.result.source_status === 'SOURCE_INDEXED'
    && catalogue.result.independent_verification === 'NOT_CHECKED'
    && catalogue.result.current_applicability === 'NOT_CHECKED'
    && catalogue.result.freshness === 'PINNED_HISTORICAL_SOURCE'
    && catalogue.result.authorization === 'NONE'
    && catalogue.result.authority === 'NONE',
  'DISCOVERY_FRONTIER_STATUS_MISMATCH');

  const shard = selectExactShard(catalogue);
  const source = selectExactSource(shard);
  requireFrontier(hasExactAxes(shard) && hasExactAxes(source), 'DISCOVERY_FRONTIER_STATUS_MISMATCH');

  const targetPresent = catalogue.shards.some(value => value.objects.some(object => object.qualified_name === targetName))
    || catalogue.search.some(value => value.qualified_name === targetName)
    || catalogue.manifest.modules.some(value => value.objects.some(object => object.qualified_name === targetName));
  requireFrontier(!targetPresent, 'DISCOVERY_FRONTIER_TARGET_PRESENT');

  const targetOmissions = catalogue.shards.flatMap(value => value.omissions.type_references
    .filter(omission => omission.target_name === targetName)
    .map(omission => ({ shard: value.module.module_id, source_id: omission.source_id })));
  const selectedPairPresent = targetOmissions.some(omission => omission.shard === moduleId && omission.source_id === sourceId);
  const uniqueSources = new Set(targetOmissions.map(omission => omission.source_id));
  requireFrontier(selectedPairPresent
    && targetOmissions.length === 42
    && uniqueSources.size === 42
    && targetOmissions.every(omission => omission.shard === moduleId),
  'DISCOVERY_FRONTIER_OMISSION_MISMATCH');

  return {
    schema: 'mathgraph.website-source-discovery-frontier.v1',
    frontier_id: 'mathlib-v4.34.1-real-log-source-gap',
    classification: 'ADVISORY',
    completeness: 'INCOMPLETE',
    terminal_form: 'NONE',
    axes: {
      source_status: 'SOURCE_INDEXED', independent_verification: 'NOT_CHECKED',
      current_applicability: 'NOT_CHECKED', freshness: 'PINNED_HISTORICAL_SOURCE',
      authority: 'NONE', authorization: 'NONE',
    },
    source: {
      qualified_name: sourceName,
      object_id: source.object_id,
      statement_sha256: source.statement_sha256,
      module: moduleName,
      path: modulePath,
      lines: { start: source.source.range.start.line, end: source.source.range.end.line },
      object_url: `/objects/${source.object_id}/`,
      source_url: `${repository}/blob/${commit}/${modulePath}#L${source.source.range.start.line}-L${source.source.range.end.line}`,
    },
    omitted_target: {
      qualified_name: targetName,
      occurrence_present: false,
      selected_pair_present: true,
      unique_omitting_sources: 42,
      relation_status: 'NOT_PUBLISHED',
      logical_implication: false,
      semantic_equivalence: false,
    },
    publication: {
      manifest_url: '/catalogues/mathlib/v4.34.1/manifest.json',
      manifest_sha256: manifestSha256,
      shard_url: `/catalogues/mathlib/v4.34.1/${shardPath}`,
      shard_sha256: shardSha256,
    },
    gates: {
      catalogue_expansion: {
        status: 'NOT_RUN',
        result_if_successful: 'SOURCE_INDEXED',
        obligation: 'Locate and index the exact Real.log source occurrence at the same pinned Mathlib revision, publish a new versioned catalogue projection preserving foundations-v1, and pass its independent offline consumer. This establishes source structure only.',
      },
      lean_proof_check: {
        status: 'NOT_RUN',
        result_if_successful: 'SEPARATE_EVIDENCE_RECEIPT_REQUIRED',
        obligation: 'Separately replay Lean under the declared source and toolchain boundary and publish a qualified receipt before assigning a VERIFIED_PROOF terminal form. Catalogue expansion alone cannot establish proof validity.',
      },
    },
  };
}
