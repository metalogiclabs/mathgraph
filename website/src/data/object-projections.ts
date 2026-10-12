import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { loadPublishedRecords } from '../lib/catalog';
import { mergeProjectionCollections, projectPublishedRecord, projectFiniteCapabilityV1, type FiniteCapabilityArtifacts, type ProjectionCollection } from '../lib/object-projections';

export async function loadFiniteCapabilityArtifacts(): Promise<FiniteCapabilityArtifacts> {
  // Build-time local reads only. No registry-provided path is executed or fetched.
  const root = resolve(process.cwd(), '../conformance/capability_v1');
  const [contractBytes, evaluationBytes, policyBytes, receiptBytes] = await Promise.all([
    readFile(resolve(root, 'fixtures/capability-contract.json')),
    readFile(resolve(root, 'evaluation.json')),
    readFile(resolve(root, 'trust-policy.json')),
    readFile(resolve(root, 'receipt.json')),
  ]);
  return { contractBytes, evaluationBytes, policyBytes, receiptBytes };
}

export async function loadObjectProjections(options: { includeCapability?: boolean } = {}): Promise<ProjectionCollection> {
  const fragments = (await loadPublishedRecords()).map(projectPublishedRecord);
  if (options.includeCapability !== false) fragments.push(projectFiniteCapabilityV1(await loadFiniteCapabilityArtifacts()));
  return mergeProjectionCollections(fragments);
}
