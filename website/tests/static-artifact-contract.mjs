import assert from 'node:assert/strict';
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

assert(
  selectedFiles.includes(discoveryManifest),
  'mathgraph-org-v1-static-site would omit .well-known/mathgraph.json; include hidden files in the upload contract',
);

console.log(`PASS static artifact contract: ${discoveryManifest} included among ${selectedFiles.length} files`);
