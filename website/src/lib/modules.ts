import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

import discoverResult from '../../../conformance/discover_v1/fixtures/result.json';
import capabilityContract from '../../../conformance/capability_v1/fixtures/capability-contract.json';
import capabilityEvaluation from '../../../conformance/capability_v1/evaluation.json';
import capabilityReceipt from '../../../conformance/capability_v1/receipt.json';
import registry from '../../../protocol/registries/capabilities-v1.json';

export { discoverResult, capabilityContract, capabilityEvaluation, capabilityReceipt, registry };

// All referenced artifacts exist at this source revision. This is provenance,
// not publisher authentication, profile admission, or current applicability.
export const moduleSourceCommit = '02a817e8de64c65e4d88d43a6279ee9f16d4364d';
export const sourceUrl = (path: string) => `https://github.com/metalogiclabs/mathgraph/blob/${moduleSourceCommit}/${path}`;
export const artifactUrl = (path: string) => `/artifacts/${path}`;
export const moduleArtifactPaths = [
  'conformance/discover_v1/fixtures/request.json',
  'conformance/discover_v1/fixtures/result.json',
  'conformance/capability_v1/fixtures/capability-contract.json',
  'conformance/capability_v1/fixtures/finite-representation-refinement-v1.json',
  'conformance/capability_v1/fixtures/finite-profile.schema.json',
  'conformance/capability_v1/evaluation.json',
  'conformance/capability_v1/receipt.json',
  'conformance/capability_v1/trust-policy.json',
  'conformance/capability_v1/consumer.py',
  'conformance/interoperability_v1/statement.json',
  'conformance/source_catalogue_v1/consumer.py',
  'conformance/source_catalogue_v1/trust-policy.json',
  'conformance/source_catalogue_v1/README.md',
] as const;

// Finite build-time allowlist: no visitor-supplied path or runtime I/O.
export async function artifactBytes(path: string): Promise<Buffer> {
  if (!moduleArtifactPaths.some((allowed) => allowed === path)) throw new Error('UNKNOWN_MODULE_ARTIFACT');
  return readFile(resolve(process.cwd(), '..', path));
}

export async function artifactDigest(path: string): Promise<string> {
  return createHash('sha256').update(await artifactBytes(path)).digest('hex');
}
