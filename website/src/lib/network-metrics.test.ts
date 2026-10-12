import { beforeAll, describe, expect, test } from 'vitest';

import registry from '../../public/capabilities/index-v1.json';
import { loadLivingKnowledgeProjections } from '../data/source-catalogue';
import type { ProjectionCollection } from './object-projections';
import { loadSourceCatalogueV1, type ValidatedSourceCatalogueV1 } from './source-catalogue';
import { deriveNetworkMetrics } from './network-metrics';

let catalogue: ValidatedSourceCatalogueV1;
let projections: ProjectionCollection;

beforeAll(async () => {
  [catalogue, projections] = await Promise.all([loadSourceCatalogueV1(), loadLivingKnowledgeProjections()]);
});

describe('source-derived living-network metrics', () => {
  test('keeps source coverage, qualified results, typed relations, projects and capabilities separate', () => {
    const metrics = deriveNetworkMetrics(catalogue, projections, registry);
    expect(metrics).toEqual({
      indexedObjects: 2345,
      qualifiedResults: 1,
      typedRelations: 3578,
      externalProjects: 4,
      qualifiedCapabilities: 1,
      relationBreakdown: {
        DECLARES: 2345, TYPE_REFERENCES: 1224, IMPORTS_MODULE: 2,
        EVIDENCE_FOR: 4, WITHDRAWS: 3,
      },
      relationSources: { SOURCE_CATALOGUE: 3571, QUALIFIED_EVIDENCE: 7 },
      externalProjectIdentities: [
        'https://github.com/leanprover-community/mathlib4',
        'https://github.com/nasa-jpl/L4YAML',
        'https://github.com/openai/math',
        'https://github.com/yaml/yaml-test-suite',
      ],
    });
    expect('total' in metrics).toBe(false);
    expect('verifiedObjects' in metrics).toBe(false);
  });

  test('does not count Resolve states, source declarations or capabilities as qualified results', () => {
    const metrics = deriveNetworkMetrics(catalogue, projections, registry);
    expect(projections.objects.filter(object => object.kind === 'RESOLVE_CLAIM' && object.axes.historical_result === 'WARRANTED_BOUNDED')).toHaveLength(1);
    expect(projections.objects.filter(object => object.kind === 'SOURCE_DECLARATION')).toHaveLength(2345);
    expect(projections.objects.filter(object => object.kind === 'FINITE_CAPABILITY')).toHaveLength(1);
    expect(metrics.qualifiedResults).toBe(1);
  });

  test('fails instead of displaying stale or authority-promoted counters', () => {
    const badCounts = structuredClone(catalogue);
    badCounts.manifest.counts.objects += 1;
    expect(() => deriveNetworkMetrics(badCounts, projections, registry)).toThrow('NETWORK_METRIC_CATALOGUE_MISMATCH');

    const promoted = structuredClone(projections);
    promoted.objects.find(object => object.kind === 'SOURCE_DECLARATION')!.axes.independent_verification = 'VERIFIED';
    expect(() => deriveNetworkMetrics(catalogue, promoted, registry)).toThrow('NETWORK_METRIC_AUTHORITY_ESCALATION');

    const extraCapability = structuredClone(registry);
    extraCapability.qualified_entries.push(structuredClone(extraCapability.qualified_entries[0]));
    expect(() => deriveNetworkMetrics(catalogue, projections, extraCapability)).toThrow('NETWORK_METRIC_CAPABILITY_MISMATCH');

    const substituted = structuredClone(projections);
    const sourceCheck = substituted.objects.find(object => object.kind === 'SOURCE_CHECK')!;
    (sourceCheck.details.source as { repo: string }).repo = 'untrusted/example';
    expect(() => deriveNetworkMetrics(catalogue, substituted, registry)).toThrow('UNAPPROVED_EXTERNAL_PROJECT');
  });
});
