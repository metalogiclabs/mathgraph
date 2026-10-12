import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readdir, readFile, stat } from 'node:fs/promises';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const website = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repository = resolve(website, '..');
const workflowPath = resolve(repository, '.github/workflows/mathgraph-org-v1.yml');

function indentation(line) {
  return line.length - line.trimStart().length;
}

function websiteArtifactContract(workflow) {
  const lines = workflow.split(/\r?\n/);
  const websiteStart = lines.findIndex((line) => /^  website:\s*$/.test(line));
  assert.notEqual(websiteStart, -1, 'website job is missing from MathGraph.org workflow');

  const websiteEnd = lines.findIndex(
    (line, index) => index > websiteStart && /^  [a-zA-Z0-9_-]+:\s*$/.test(line),
  );
  const jobLines = lines.slice(websiteStart, websiteEnd === -1 ? undefined : websiteEnd);
  const uploadIndex = jobLines.findIndex(
    (line) => line.trim().replace(/^-\s*/, '') === 'uses: actions/upload-artifact@v4',
  );
  assert.notEqual(uploadIndex, -1, 'website job does not upload a static-site artifact');

  const stepIndent = indentation(jobLines[uploadIndex]);
  const withIndex = jobLines.findIndex(
    (line, index) => index > uploadIndex && indentation(line) === stepIndent + 2 && line.trim() === 'with:',
  );
  assert.notEqual(withIndex, -1, 'website artifact upload has no with contract');

  const withIndent = indentation(jobLines[withIndex]);
  const values = new Map();
  for (const line of jobLines.slice(withIndex + 1)) {
    if (line.trim() && indentation(line) <= withIndent) break;
    const match = line.trim().match(/^([a-zA-Z0-9_-]+):\s*(.*?)\s*$/);
    if (match) values.set(match[1], match[2].replace(/^['"]|['"]$/g, ''));
  }

  return {
    includeHiddenFiles: values.get('include-hidden-files') === 'true',
    name: values.get('name'),
    path: values.get('path'),
  };
}

async function filesBelow(root) {
  const files = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    const absolute = resolve(root, entry.name);
    if (entry.isDirectory()) files.push(...await filesBelow(absolute));
    else if (entry.isFile()) files.push(absolute);
  }
  return files;
}

function isHidden(relativePath) {
  return relativePath.split(sep).some((segment) => segment.startsWith('.'));
}

const workflow = await readFile(workflowPath, 'utf8');
const contract = websiteArtifactContract(workflow);
assert.equal(contract.name, 'mathgraph-org-v1-static-site');
assert.equal(contract.path, 'website/dist/');

const artifactRoot = resolve(repository, contract.path);
assert((await stat(artifactRoot)).isDirectory(), 'build website/dist before checking the artifact contract');

const allFiles = (await filesBelow(artifactRoot)).map((file) => relative(artifactRoot, file));
const selectedFiles = contract.includeHiddenFiles
  ? allFiles
  : allFiles.filter((file) => !isHidden(file));
const discoveryManifest = ['.well-known', 'mathgraph.json'].join(sep);
const historicalDiscoveryManifest = ['.well-known', 'mathgraph-v3.json'].join(sep);
const catalogueRoot = ['catalogues', 'mathlib', 'v4.34.1'].join(sep);
const catalogueManifestPath = [catalogueRoot, 'manifest.json'].join(sep);
const catalogueSearchPath = [catalogueRoot, 'search.json'].join(sep);

assert(
  selectedFiles.includes(discoveryManifest),
  'mathgraph-org-v1-static-site would omit .well-known/mathgraph.json; include hidden files in the upload contract',
);
assert(selectedFiles.includes(historicalDiscoveryManifest), 'static artifact missing frozen discovery V3 manifest');
assert.equal(
  createHash('sha256').update(await readFile(resolve(artifactRoot, historicalDiscoveryManifest))).digest('hex'),
  '3bde9969e635a39153f58b7f237979b954302c48878c2266dffe2ab9afd16540',
  'frozen discovery V3 bytes changed',
);

assert(selectedFiles.includes(catalogueManifestPath), `static artifact missing ${catalogueManifestPath}`);
assert(selectedFiles.includes(catalogueSearchPath), `static artifact missing ${catalogueSearchPath}`);

const manifest = JSON.parse(await readFile(resolve(artifactRoot, catalogueManifestPath), 'utf8'));
assert(Array.isArray(manifest.shards) && manifest.shards.length > 0, 'catalogue manifest has no shard inventory');
const expectedShards = manifest.shards.map(({ path }) => [catalogueRoot, ...path.split('/')].join(sep)).sort();
const selectedShards = selectedFiles
  .filter((path) => path.startsWith(`${catalogueRoot}${sep}shards${sep}`) && path.endsWith('.json'))
  .sort();
assert.deepEqual(selectedShards, expectedShards, 'static artifact catalogue shards differ from the manifest inventory');

for (const relativePath of [catalogueManifestPath, catalogueSearchPath, ...expectedShards]) {
  const publicPath = resolve(website, 'public', relativePath);
  const builtPath = resolve(artifactRoot, relativePath);
  assert.deepEqual(
    await readFile(builtPath),
    await readFile(publicPath),
    `static build changed committed catalogue bytes: ${relativePath}`,
  );
}

for (const [relativePath, expectedDigest] of [
  [['artifacts', 'conformance', 'source_catalogue_v1', 'consumer.py'].join(sep), '583dcfca46854f56469cdda865b5da62b1068e985bdce411dac9c587e556ca5d'],
  [['artifacts', 'conformance', 'source_catalogue_v1', 'trust-policy.json'].join(sep), 'c3cdec2b2c784728621bb8c25a055a1e73d67d3c1c922b7ab62b09003399e1c9'],
  [['artifacts', 'conformance', 'source_catalogue_v1', 'README.md'].join(sep), '787f1dd6cf9c7b24c1adc7f8d2c31bd44d637c77574f091fc19414761ca1f323'],
]) {
  assert(selectedFiles.includes(relativePath), `static artifact missing ${relativePath}`);
  assert.equal(createHash('sha256').update(await readFile(resolve(artifactRoot, relativePath))).digest('hex'), expectedDigest);
}
for (const relativePath of [
  ['artifacts', 'conformance', 'source_catalogue_v1', 'run_isolated.py'].join(sep),
  ['artifacts', 'conformance', 'source_catalogue_v1', 'test_consumer.py'].join(sep),
]) assert(!selectedFiles.includes(relativePath), `static artifact exposed non-allowlisted path ${relativePath}`);

console.log(`PASS static artifact contract: V4 + frozen V3 discovery, ${expectedShards.length} catalogue shards, and 3 independent-consumer files included byte-for-byte among ${selectedFiles.length} files`);
