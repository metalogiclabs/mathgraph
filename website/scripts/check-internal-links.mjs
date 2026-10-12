import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { dirname, extname, posix, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const website = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = resolve(website, 'dist');
const origin = 'https://mathgraph.org';
const deploymentRedirects = [
  /^\/v1\/records\/mg-l4yaml-source-check-20261010$/u,
  /^\/v1\/records\/mg-l4yaml-source-check-20261010\/evidence$/u,
  /^\/v1\/badges\/mg-l4yaml-source-check-20261010\.svg$/u,
];

async function collectFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const absolute = resolve(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collectFiles(absolute));
    else if (entry.isFile()) files.push(absolute);
  }
  return files;
}

function publicPath(absolute) {
  return relative(dist, absolute).split(sep).join('/');
}

function pageUrl(relativePath) {
  if (relativePath === 'index.html') return new URL('/', origin);
  if (relativePath.endsWith('/index.html')) {
    return new URL(`/${relativePath.slice(0, -'index.html'.length)}`, origin);
  }
  return new URL(`/${relativePath}`, origin);
}

function attributeValues(html) {
  const values = [];
  const pattern = /\b(?:href|src)\s*=\s*(["'])(.*?)\1/giu;
  for (const match of html.matchAll(pattern)) values.push(match[2]);
  return values;
}

function anchors(html) {
  const values = new Set();
  const pattern = /\b(?:id|name)\s*=\s*(["'])(.*?)\1/giu;
  for (const match of html.matchAll(pattern)) values.add(match[2]);
  return values;
}

function candidatePaths(pathname) {
  const decoded = decodeURIComponent(pathname);
  const normalized = posix.normalize(decoded).replace(/^\/+/, '');
  assert(!normalized.startsWith('../'), `link escapes the static root: ${pathname}`);
  if (decoded.endsWith('/')) {
    const clean = normalized.replace(/\/$/u, '');
    return [`${normalized}index.html`, `${clean}.html`];
  }
  if (extname(normalized)) return [normalized];
  return [normalized, `${normalized}.html`, `${normalized}/index.html`];
}

const files = await collectFiles(dist);
const published = new Set(files.map(publicPath));
const htmlFiles = files.filter((file) => extname(file) === '.html');
const htmlByPath = new Map();
const anchorsByPath = new Map();
for (const file of htmlFiles) {
  const relativePath = publicPath(file);
  const html = await readFile(file, 'utf8');
  htmlByPath.set(relativePath, html);
  anchorsByPath.set(relativePath, anchors(html));
}

const failures = [];
let references = 0;
let internal = 0;
let external = 0;
let redirected = 0;
let fragments = 0;

for (const [sourcePath, html] of htmlByPath) {
  const base = pageUrl(sourcePath);
  for (const raw of attributeValues(html)) {
    references += 1;
    let url;
    try {
      url = new URL(raw, base);
    } catch (error) {
      failures.push(`${sourcePath}: invalid URL ${JSON.stringify(raw)} (${error.message})`);
      continue;
    }
    if (!['http:', 'https:'].includes(url.protocol) || url.origin !== origin) {
      external += 1;
      continue;
    }
    if (deploymentRedirects.some((pattern) => pattern.test(url.pathname))) {
      redirected += 1;
      continue;
    }
    let candidates;
    try {
      candidates = candidatePaths(url.pathname);
    } catch (error) {
      failures.push(`${sourcePath}: ${error.message}`);
      continue;
    }
    const target = candidates.find((candidate) => published.has(candidate));
    if (!target) {
      failures.push(`${sourcePath}: ${raw} -> missing ${candidates.join(' or ')}`);
      continue;
    }
    internal += 1;
    if (url.hash && target.endsWith('.html')) {
      fragments += 1;
      let fragment;
      try {
        fragment = decodeURIComponent(url.hash.slice(1));
      } catch (error) {
        failures.push(`${sourcePath}: invalid fragment ${url.hash} (${error.message})`);
        continue;
      }
      if (fragment && !anchorsByPath.get(target)?.has(fragment)) {
        failures.push(`${sourcePath}: ${raw} -> missing fragment #${fragment} in ${target}`);
      }
    }
  }
}

assert(htmlFiles.length >= 2_395, `unexpectedly small HTML publication (${htmlFiles.length})`);
assert(references > 10_000, `unexpectedly small link surface (${references})`);
if (failures.length) {
  throw new Error(`Detected ${failures.length} broken internal links:\n${failures.slice(0, 100).join('\n')}`);
}
console.log(
  `INTERNAL_LINKS_GREEN pages=${htmlFiles.length} references=${references} internal=${internal} fragments=${fragments} redirects=${redirected} external_skipped=${external}`,
);
