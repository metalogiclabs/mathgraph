import type { ProjectionCollection, RelationProjection } from './object-projections';
import type { ValidatedSourceCatalogueV1 } from './source-catalogue';

const externalProjectAllowlist = new Set([
  'https://github.com/leanprover-community/mathlib4',
  'https://github.com/nasa-jpl/L4YAML',
  'https://github.com/openai/math',
  'https://github.com/yaml/yaml-test-suite',
]);
const structuralRelations = new Set<RelationProjection['type']>(['DECLARES', 'IMPORTS_MODULE', 'TYPE_REFERENCES']);

export interface NetworkMetrics {
  indexedObjects: number;
  qualifiedResults: number;
  typedRelations: number;
  externalProjects: number;
  qualifiedCapabilities: number;
  relationBreakdown: Partial<Record<RelationProjection['type'], number>>;
  relationSources: { SOURCE_CATALOGUE: number; QUALIFIED_EVIDENCE: number };
  externalProjectIdentities: string[];
}

interface CapabilityRegistryLike {
  schema_version: string;
  qualified_entries: Array<{ id: string }>;
}

function requireMetric(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}

function githubProject(value: string): string | null {
  const trimmed = value.replace(/\.git$/, '');
  if (/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(trimmed)) return `https://github.com/${trimmed}`;
  try {
    const url = new URL(trimmed);
    if (url.hostname !== 'github.com') return null;
    const [owner, repository] = url.pathname.split('/').filter(Boolean);
    return owner && repository ? `https://github.com/${owner}/${repository.replace(/\.git$/, '')}` : null;
  } catch {
    return null;
  }
}

/** Derive display metrics only from already validated source projections and registries. */
export function deriveNetworkMetrics(
  catalogue: ValidatedSourceCatalogueV1,
  projections: ProjectionCollection,
  capabilityRegistry: CapabilityRegistryLike,
): NetworkMetrics {
  const declarations = projections.objects.filter(object => object.kind === 'SOURCE_DECLARATION');
  const modules = projections.objects.filter(object => object.kind === 'SOURCE_MODULE');
  const sourceObjects = [...modules, ...declarations];
  requireMetric(catalogue.manifest.counts.objects === declarations.length
    && catalogue.manifest.counts.modules === modules.length, 'NETWORK_METRIC_CATALOGUE_MISMATCH');
  requireMetric(sourceObjects.every(object => object.authority === 'NONE'
    && object.axes.source_status === 'SOURCE_INDEXED'
    && object.axes.independent_verification === 'NOT_CHECKED'
    && object.axes.current_applicability === 'NOT_CHECKED'
    && object.axes.action_authorization === 'NONE'), 'NETWORK_METRIC_AUTHORITY_ESCALATION');

  const sourceRelations = projections.relations.filter(relation => structuralRelations.has(relation.type));
  requireMetric(sourceRelations.length === catalogue.manifest.counts.relations
    && sourceRelations.every(relation => relation.authority === 'NONE'
      && relation.logical_implication === false && relation.semantic_equivalence === false), 'NETWORK_METRIC_CATALOGUE_MISMATCH');
  requireMetric(projections.relations.every(relation => relation.authority === 'NONE'), 'NETWORK_METRIC_AUTHORITY_ESCALATION');

  const qualifiedResultIds = new Set(projections.objects
    .filter(object => object.kind === 'SOURCE_CHECK' && object.axes.historical_result === 'WARRANTED_BOUNDED')
    .map(object => object.source_id));

  requireMetric(capabilityRegistry.schema_version === 'mathgraph.capability-registry.v1', 'NETWORK_METRIC_CAPABILITY_MISMATCH');
  const registryCapabilityIds = capabilityRegistry.qualified_entries.map(entry => entry.id);
  const projectedCapabilityIds = projections.objects.filter(object => object.kind === 'FINITE_CAPABILITY').map(object => object.source_id);
  requireMetric(new Set(registryCapabilityIds).size === registryCapabilityIds.length
    && registryCapabilityIds.length === projectedCapabilityIds.length
    && registryCapabilityIds.every(id => projectedCapabilityIds.includes(id)), 'NETWORK_METRIC_CAPABILITY_MISMATCH');

  const projects = new Set<string>();
  const admitProject = (value: unknown) => {
    if (typeof value !== 'string') return;
    const identity = githubProject(value);
    if (!identity) return;
    requireMetric(externalProjectAllowlist.has(identity), 'UNAPPROVED_EXTERNAL_PROJECT');
    projects.add(identity);
  };
  admitProject(catalogue.manifest.source.repository);
  for (const object of projections.objects) {
    if (object.kind === 'SOURCE_CHECK') {
      const source = object.details.source as { repo?: unknown; external_suite_repo?: unknown } | undefined;
      admitProject(source?.repo); admitProject(source?.external_suite_repo);
    }
    if (object.kind === 'RESOLUTION_SNAPSHOT') {
      const sources = object.details.sources as { openai?: { url?: unknown } } | undefined;
      admitProject(sources?.openai?.url);
    }
  }
  requireMetric(projects.size === externalProjectAllowlist.size
    && [...externalProjectAllowlist].every(project => projects.has(project)), 'NETWORK_METRIC_PROJECT_MISMATCH');

  const relationBreakdown: NetworkMetrics['relationBreakdown'] = {};
  for (const relation of projections.relations) relationBreakdown[relation.type] = (relationBreakdown[relation.type] ?? 0) + 1;
  const sortedBreakdown = Object.fromEntries(Object.entries(relationBreakdown).sort(([left], [right]) => left.localeCompare(right))) as NetworkMetrics['relationBreakdown'];
  return {
    indexedObjects: declarations.length,
    qualifiedResults: qualifiedResultIds.size,
    typedRelations: projections.relations.length,
    externalProjects: projects.size,
    qualifiedCapabilities: registryCapabilityIds.length,
    relationBreakdown: sortedBreakdown,
    relationSources: { SOURCE_CATALOGUE: sourceRelations.length, QUALIFIED_EVIDENCE: projections.relations.length - sourceRelations.length },
    externalProjectIdentities: [...projects].sort(),
  };
}
