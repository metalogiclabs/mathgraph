import { beforeAll, describe, expect, test } from 'vitest';

import { deriveSourceDiscoveryFrontierV1 } from './source-discovery-frontier';
import { loadSourceCatalogueV1, type ValidatedSourceCatalogueV1 } from './source-catalogue';

let catalogue: ValidatedSourceCatalogueV1;

beforeAll(async () => {
  catalogue = await loadSourceCatalogueV1();
});

describe('source-grounded Discovery frontier', () => {
  test('derives the Real.log_rpow to omitted Real.log frontier without promoting source indexing', () => {
    const frontier = deriveSourceDiscoveryFrontierV1(catalogue);

    expect(frontier).toMatchObject({
      schema: 'mathgraph.website-source-discovery-frontier.v1',
      frontier_id: 'mathlib-v4.34.1-real-log-source-gap',
      classification: 'ADVISORY',
      completeness: 'INCOMPLETE',
      terminal_form: 'NONE',
      axes: {
        source_status: 'SOURCE_INDEXED',
        independent_verification: 'NOT_CHECKED',
        current_applicability: 'NOT_CHECKED',
        freshness: 'PINNED_HISTORICAL_SOURCE',
        authority: 'NONE',
        authorization: 'NONE',
      },
      source: {
        qualified_name: 'Real.log_rpow',
        object_id: 'object-8d7d18f07e0f6262a3b65bbb71105c16c69ab67a6d96a78c18e97cfa7afc2322',
        statement_sha256: 'cbb5d6bc3ea24d4f3231fdcb221756eba154e15179f5529d3dc2ecad41dc6d88',
        module: 'Mathlib.Analysis.SpecialFunctions.Pow.Real',
        path: 'Mathlib/Analysis/SpecialFunctions/Pow/Real.lean',
        lines: { start: 491, end: 496 },
        object_url: '/objects/object-8d7d18f07e0f6262a3b65bbb71105c16c69ab67a6d96a78c18e97cfa7afc2322/',
      },
      omitted_target: {
        qualified_name: 'Real.log',
        occurrence_present: false,
        selected_pair_present: true,
        unique_omitting_sources: 42,
        relation_status: 'NOT_PUBLISHED',
        logical_implication: false,
        semantic_equivalence: false,
      },
      publication: {
        manifest_url: '/catalogues/mathlib/v4.34.1/manifest.json',
        manifest_sha256: '5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68',
        shard_url: '/catalogues/mathlib/v4.34.1/shards/6400eba377e910ff2ac4bea415657e6c84b546832d93808c9fcb9dce952d22c0.json',
        shard_sha256: '6400eba377e910ff2ac4bea415657e6c84b546832d93808c9fcb9dce952d22c0',
      },
      gates: {
        catalogue_expansion: { status: 'NOT_RUN', result_if_successful: 'SOURCE_INDEXED' },
        lean_proof_check: { status: 'NOT_RUN', result_if_successful: 'SEPARATE_EVIDENCE_RECEIPT_REQUIRED' },
      },
    });
    expect(frontier.source.source_url).toBe('https://github.com/leanprover-community/mathlib4/blob/d13f23b723b8a846827a245b89c10fc7d3f11612/Mathlib/Analysis/SpecialFunctions/Pow/Real.lean#L491-L496');
    expect(frontier.gates.catalogue_expansion.obligation).toMatch(/publish a new versioned catalogue projection/i);
    expect(frontier.gates.catalogue_expansion.obligation).toMatch(/preserv(?:e|ing) foundations-v1/i);
  });

  test('fails closed when the exact source occurrence or selected omission changes', () => {
    const changedSource = structuredClone(catalogue);
    const source = changedSource.shards.flatMap(shard => shard.objects)
      .find(object => object.qualified_name === 'Real.log_rpow')!;
    source.statement_sha256 = '0'.repeat(64);
    expect(() => deriveSourceDiscoveryFrontierV1(changedSource)).toThrow('DISCOVERY_FRONTIER_SOURCE_PIN_MISMATCH');

    const missingPair = structuredClone(catalogue);
    const shard = missingPair.shards.find(value => value.module.module === 'Mathlib.Analysis.SpecialFunctions.Pow.Real')!;
    shard.omissions.type_references = shard.omissions.type_references.filter(omission => !(
      omission.source_id === 'object-8d7d18f07e0f6262a3b65bbb71105c16c69ab67a6d96a78c18e97cfa7afc2322'
      && omission.target_name === 'Real.log'
    ));
    expect(() => deriveSourceDiscoveryFrontierV1(missingPair)).toThrow('DISCOVERY_FRONTIER_OMISSION_MISMATCH');
  });

  test('fails closed if the omitted target appears or any status axis gains authority', () => {
    const targetPresent = structuredClone(catalogue);
    const shard = targetPresent.shards.find(value => value.module.module === 'Mathlib.Analysis.SpecialFunctions.Pow.Real')!;
    const source = structuredClone(shard.objects.find(object => object.qualified_name === 'Real.log_rpow')!);
    source.qualified_name = 'Real.log';
    source.object_id = `object-${'1'.repeat(64)}`;
    shard.objects.push(source);
    expect(() => deriveSourceDiscoveryFrontierV1(targetPresent)).toThrow('DISCOVERY_FRONTIER_TARGET_PRESENT');

    const promoted = structuredClone(catalogue);
    (promoted.result as { independent_verification: string }).independent_verification = 'VERIFIED';
    expect(() => deriveSourceDiscoveryFrontierV1(promoted)).toThrow('DISCOVERY_FRONTIER_STATUS_MISMATCH');
  });
});
