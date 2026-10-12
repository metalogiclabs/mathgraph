import { loadSourceCatalogueV1 } from '../lib/source-catalogue';
import { mergeProjectionCollections, projectSourceCatalogueV1, type ProjectionCollection } from '../lib/object-projections';
import { loadObjectProjections } from './object-projections';

export async function loadSourceCatalogueProjections(): Promise<ProjectionCollection> {
  return projectSourceCatalogueV1(await loadSourceCatalogueV1());
}

/** Merge only after each domain-specific adapter has validated its own source contract. */
export async function loadLivingKnowledgeProjections(): Promise<ProjectionCollection> {
  const [existing, sourceCatalogue] = await Promise.all([
    loadObjectProjections(),
    loadSourceCatalogueProjections(),
  ]);
  return mergeProjectionCollections([existing, sourceCatalogue]);
}
