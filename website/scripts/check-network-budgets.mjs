import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import { dirname, extname, isAbsolute, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const websiteRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const committedCatalogueRoot = join(websiteRoot, 'public/catalogues/mathlib/v4.34.1');
const distRoot = join(websiteRoot, 'dist');
const builtCatalogueRoot = join(distRoot, 'catalogues/mathlib/v4.34.1');
const manifestRelativePath = 'manifest.json';

const KiB = 1024;
const MiB = 1024 * KiB;
const limits = Object.freeze({
  selectedModules: 13,
  catalogueObjects: 2_500,
  catalogueRelations: 25_000,
  manifestRawBytes: 1 * MiB,
  searchRawBytes: 2 * MiB,
  searchGzipBytes: 256 * KiB,
  shardRawBytes: 2 * MiB,
  shardGzipBytes: 256 * KiB,
  catalogueRawBytes: 12 * MiB,
  catalogueGzipBytes: Math.floor(1.5 * MiB),
  projectionNodes: 50,
  projectionEdges: 100,
  clientBytes: 100_000,
  homeRawBytes: 96 * KiB,
  homeGzipBytes: 24 * KiB,
  occurrenceRawBytes: 96 * KiB,
  resolveRawBytes: 64 * KiB,
  exploreRawBytes: 1 * MiB,
  exploreGzipBytes: 200 * KiB,
  outputBytes: 64 * MiB,
  htmlFiles: 2_400,
});

function requireBudget(condition, message) {
  if (!condition) throw new Error(message);
}

function safeInteger(value, label) {
  requireBudget(Number.isSafeInteger(value) && value >= 0, `${label} must be a non-negative safe integer`);
  return value;
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function deterministicGzipSize(bytes) {
  return gzipSync(bytes, { level: 9, mtime: 0 }).byteLength;
}

function safeCataloguePath(value, label) {
  requireBudget(typeof value === 'string' && value.length > 0, `${label} must be a non-empty string`);
  requireBudget(!isAbsolute(value) && !value.includes('\\'), `${label} must be a relative POSIX path`);
  const normalized = normalize(value);
  requireBudget(
    normalized === value && normalized !== '..' && !normalized.startsWith(`..${sep}`),
    `${label} escapes the catalogue root`,
  );
  return value;
}

async function exactPublishedBytes(relativePath) {
  const safePath = safeCataloguePath(relativePath, 'catalogue artifact path');
  const [committed, built] = await Promise.all([
    readFile(join(committedCatalogueRoot, safePath)),
    readFile(join(builtCatalogueRoot, safePath)),
  ]);
  requireBudget(committed.equals(built), `built catalogue artifact differs from committed bytes: ${safePath}`);
  return committed;
}

async function collectBuiltOutput(directory, result) {
  const entries = await readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name));
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      await collectBuiltOutput(path, result);
      continue;
    }
    requireBudget(entry.isFile(), `unsupported non-file entry in built output: ${path}`);
    const size = (await stat(path)).size;
    result.files += 1;
    result.outputBytes += size;
    const extension = extname(entry.name);
    if (extension === '.html') result.htmlFiles.push(path);
    if (extension === '.js' || extension === '.css') result.clientBytes += size;
  }
}

function graphProjections(html, relativePath) {
  const projections = [];
  const pattern = /<script\b[^>]*\bdata-(?:map|neighborhood)-data\b[^>]*>([\s\S]*?)<\/script>/gu;
  for (const match of html.matchAll(pattern)) {
    let projection;
    try {
      projection = JSON.parse(match[1]);
    } catch {
      throw new Error(`invalid graph projection JSON in ${relativePath}`);
    }
    requireBudget(projection && typeof projection === 'object', `invalid graph projection in ${relativePath}`);
    requireBudget(Array.isArray(projection.nodes), `graph projection nodes missing in ${relativePath}`);
    const edges = projection.edges ?? projection.relations;
    requireBudget(Array.isArray(edges), `graph projection edges missing in ${relativePath}`);
    requireBudget(
      projection.nodes.length <= limits.projectionNodes,
      `graph projection exceeds ${limits.projectionNodes} nodes in ${relativePath}`,
    );
    requireBudget(
      edges.length <= limits.projectionEdges,
      `graph projection exceeds ${limits.projectionEdges} edges in ${relativePath}`,
    );
    projections.push({ nodes: projection.nodes.length, edges: edges.length });
  }
  return projections;
}

async function pageMeasurement(relativePath, rawLimit, gzipLimit = null) {
  const bytes = await readFile(join(distRoot, relativePath));
  const rawBytes = bytes.byteLength;
  const gzipBytes = deterministicGzipSize(bytes);
  requireBudget(rawBytes <= rawLimit, `${relativePath} exceeds raw-byte budget (${rawBytes} > ${rawLimit})`);
  if (gzipLimit !== null) {
    requireBudget(gzipBytes <= gzipLimit, `${relativePath} exceeds gzip budget (${gzipBytes} > ${gzipLimit})`);
  }
  return { path: relativePath, raw_bytes: rawBytes, gzip_bytes: gzipBytes };
}

async function buildReport() {
  const manifestBytes = await exactPublishedBytes(manifestRelativePath);
  requireBudget(manifestBytes.byteLength <= limits.manifestRawBytes, 'catalogue manifest exceeds raw-byte budget');

  let manifest;
  try {
    manifest = JSON.parse(manifestBytes);
  } catch {
    throw new Error('catalogue manifest is not valid JSON');
  }
  requireBudget(
    manifest?.schema === 'mathgraph.source-catalogue-manifest.v1'
      && manifest.catalogue_version === 1
      && manifest.counts && manifest.limits
      && Array.isArray(manifest.modules)
      && Array.isArray(manifest.shards)
      && manifest.search,
    'unsupported or malformed catalogue manifest',
  );

  const counts = manifest.counts;
  for (const field of [
    'modules', 'objects', 'relations', 'omitted_declarations', 'omitted_imports', 'omitted_type_references',
  ]) safeInteger(counts[field], `manifest counts.${field}`);
  requireBudget(counts.modules === limits.selectedModules, `catalogue must contain exactly ${limits.selectedModules} modules`);
  requireBudget(manifest.modules.length === counts.modules, 'manifest module count does not match module entries');
  requireBudget(manifest.shards.length === counts.modules, 'manifest module count does not match shard entries');
  requireBudget(counts.objects <= limits.catalogueObjects, 'catalogue object count exceeds approved limit');
  requireBudget(counts.relations <= limits.catalogueRelations, 'catalogue relation count exceeds approved limit');

  const declaredLimits = {
    max_declarations: limits.catalogueObjects,
    max_relations: limits.catalogueRelations,
    max_manifest_bytes: limits.manifestRawBytes,
    max_search_bytes: limits.searchRawBytes,
    max_shard_bytes: limits.shardRawBytes,
    max_projection_nodes: limits.projectionNodes,
    max_projection_edges: limits.projectionEdges,
  };
  for (const [field, expected] of Object.entries(declaredLimits)) {
    requireBudget(manifest.limits[field] === expected, `manifest ${field} does not match the approved limit`);
  }

  const moduleIds = manifest.modules.map((entry) => entry?.module_id);
  requireBudget(
    moduleIds.every((value) => typeof value === 'string' && value.length > 0)
      && new Set(moduleIds).size === moduleIds.length,
    'manifest module identities must be unique non-empty strings',
  );
  const moduleIdSet = new Set(moduleIds);

  const searchPath = safeCataloguePath(manifest.search.path, 'manifest search.path');
  requireBudget(searchPath === 'search.json', 'unsupported catalogue search path');
  const searchBytes = await exactPublishedBytes(searchPath);
  const searchRawBytes = searchBytes.byteLength;
  const searchGzipBytes = deterministicGzipSize(searchBytes);
  requireBudget(searchRawBytes === manifest.search.size_bytes, 'search bytes do not match the manifest');
  requireBudget(sha256(searchBytes) === manifest.search.sha256, 'search digest does not match the manifest');
  requireBudget(searchRawBytes <= limits.searchRawBytes, 'search data exceeds raw-byte budget');
  requireBudget(searchGzipBytes <= limits.searchGzipBytes, 'search data exceeds deterministic-gzip budget');
  let search;
  try {
    search = JSON.parse(searchBytes);
  } catch {
    throw new Error('catalogue search data is not valid JSON');
  }
  requireBudget(Array.isArray(search) && search.length === counts.objects, 'search entries do not match catalogue objects');
  requireBudget(manifest.search.object_count === counts.objects, 'search object count does not match the manifest');

  let catalogueRawBytes = manifestBytes.byteLength + searchRawBytes;
  let catalogueGzipBytes = deterministicGzipSize(manifestBytes) + searchGzipBytes;
  let largestShardRawBytes = 0;
  let largestShardGzipBytes = 0;
  const shardTotals = {
    objects: 0,
    relations: 0,
    omitted_declarations: 0,
    omitted_imports: 0,
    omitted_type_references: 0,
  };
  const shardModuleIds = new Set();

  for (const descriptor of manifest.shards) {
    requireBudget(descriptor && typeof descriptor === 'object', 'invalid catalogue shard descriptor');
    const path = safeCataloguePath(descriptor.path, 'manifest shard.path');
    requireBudget(/^shards\/[a-f0-9]{64}\.json$/u.test(path), `unsupported shard path: ${path}`);
    requireBudget(
      typeof descriptor.sha256 === 'string'
        && path === `shards/${descriptor.sha256}.json`,
      `shard filename does not match its declared digest: ${path}`,
    );
    requireBudget(
      typeof descriptor.module_id === 'string'
        && moduleIdSet.has(descriptor.module_id)
        && !shardModuleIds.has(descriptor.module_id),
      `invalid or duplicate shard module identity: ${descriptor.module_id}`,
    );
    shardModuleIds.add(descriptor.module_id);
    for (const field of [
      'object_count', 'relation_count', 'omitted_declarations', 'omitted_imports', 'omitted_type_references',
    ]) safeInteger(descriptor[field], `shard ${path} ${field}`);

    const bytes = await exactPublishedBytes(path);
    const rawBytes = bytes.byteLength;
    const gzipBytes = deterministicGzipSize(bytes);
    requireBudget(rawBytes === descriptor.size_bytes, `shard bytes do not match the manifest: ${path}`);
    requireBudget(sha256(bytes) === descriptor.sha256, `shard digest does not match the manifest: ${path}`);
    requireBudget(rawBytes <= limits.shardRawBytes, `shard exceeds raw-byte budget: ${path}`);
    requireBudget(gzipBytes <= limits.shardGzipBytes, `shard exceeds deterministic-gzip budget: ${path}`);

    let shard;
    try {
      shard = JSON.parse(bytes);
    } catch {
      throw new Error(`catalogue shard is not valid JSON: ${path}`);
    }
    requireBudget(
      shard?.schema === 'mathgraph.source-catalogue-shard.v1'
        && shard.module?.module_id === descriptor.module_id
        && Array.isArray(shard.objects)
        && shard.objects.length === descriptor.object_count
        && Array.isArray(shard.relations)
        && shard.relations.length === descriptor.relation_count,
      `catalogue shard contents do not match descriptor: ${path}`,
    );

    catalogueRawBytes += rawBytes;
    catalogueGzipBytes += gzipBytes;
    largestShardRawBytes = Math.max(largestShardRawBytes, rawBytes);
    largestShardGzipBytes = Math.max(largestShardGzipBytes, gzipBytes);
    shardTotals.objects += descriptor.object_count;
    shardTotals.relations += descriptor.relation_count;
    shardTotals.omitted_declarations += descriptor.omitted_declarations;
    shardTotals.omitted_imports += descriptor.omitted_imports;
    shardTotals.omitted_type_references += descriptor.omitted_type_references;
  }
  requireBudget(shardModuleIds.size === counts.modules, 'shards do not cover every selected module exactly once');
  for (const [field, observed] of Object.entries(shardTotals)) {
    requireBudget(observed === counts[field], `summed shard ${field} does not match manifest counts`);
  }
  requireBudget(catalogueRawBytes <= limits.catalogueRawBytes, 'complete catalogue exceeds raw-byte budget');
  requireBudget(catalogueGzipBytes <= limits.catalogueGzipBytes, 'complete catalogue exceeds deterministic-gzip budget');

  const output = { files: 0, outputBytes: 0, clientBytes: 0, htmlFiles: [] };
  await collectBuiltOutput(distRoot, output);
  requireBudget(output.clientBytes < limits.clientBytes, 'built client JavaScript and CSS exceed approved budget');
  requireBudget(output.outputBytes <= limits.outputBytes, 'built static output exceeds approved budget');
  requireBudget(output.htmlFiles.length <= limits.htmlFiles, 'built HTML count exceeds approved budget');

  let projectionCount = 0;
  let projectionMaxNodes = 0;
  let projectionMaxEdges = 0;
  let occurrenceCount = 0;
  let maximumOccurrence = { path: null, raw_bytes: 0, gzip_bytes: 0 };
  for (const htmlPath of output.htmlFiles) {
    const relativePath = htmlPath.slice(distRoot.length + 1).split(sep).join('/');
    const html = await readFile(htmlPath, 'utf8');
    if (/^objects\/object-[0-9a-f]{64}\/index\.html$/u.test(relativePath)) {
      occurrenceCount += 1;
      const bytes = Buffer.from(html, 'utf8');
      const measurement = {
        path: relativePath,
        raw_bytes: bytes.byteLength,
        gzip_bytes: deterministicGzipSize(bytes),
      };
      requireBudget(
        measurement.raw_bytes <= limits.occurrenceRawBytes,
        `${relativePath} exceeds source/object detail raw-byte budget (${measurement.raw_bytes} > ${limits.occurrenceRawBytes})`,
      );
      if (measurement.raw_bytes > maximumOccurrence.raw_bytes) maximumOccurrence = measurement;
    }
    for (const projection of graphProjections(html, relativePath)) {
      projectionCount += 1;
      projectionMaxNodes = Math.max(projectionMaxNodes, projection.nodes);
      projectionMaxEdges = Math.max(projectionMaxEdges, projection.edges);
    }
  }
  requireBudget(projectionCount > 0, 'built site contains no inspectable graph projections');
  requireBudget(occurrenceCount > 0, 'built site contains no source/object detail pages');

  const pages = {
    home: await pageMeasurement('index.html', limits.homeRawBytes, limits.homeGzipBytes),
    explore: await pageMeasurement('explore/index.html', limits.exploreRawBytes, limits.exploreGzipBytes),
    resolve: await pageMeasurement('resolve/index.html', limits.resolveRawBytes),
    maximum_occurrence: maximumOccurrence,
  };

  return {
    schema: 'mathgraph.website-network-budget-report.v1',
    status: 'PASS',
    deterministic_gzip: { implementation: 'node:zlib.gzipSync', level: 9, mtime: 0 },
    limits: {
      catalogue: {
        modules: limits.selectedModules,
        objects: limits.catalogueObjects,
        relations: limits.catalogueRelations,
        raw_bytes: limits.catalogueRawBytes,
        gzip_bytes: limits.catalogueGzipBytes,
        search_raw_bytes: limits.searchRawBytes,
        search_gzip_bytes: limits.searchGzipBytes,
        shard_raw_bytes: limits.shardRawBytes,
        shard_gzip_bytes: limits.shardGzipBytes,
      },
      projection: { nodes: limits.projectionNodes, edges: limits.projectionEdges },
      client_bytes: limits.clientBytes,
      pages: {
        home: { raw_bytes: limits.homeRawBytes, gzip_bytes: limits.homeGzipBytes },
        explore: { raw_bytes: limits.exploreRawBytes, gzip_bytes: limits.exploreGzipBytes },
        resolve: { raw_bytes: limits.resolveRawBytes },
        occurrence: { raw_bytes: limits.occurrenceRawBytes },
      },
      output: { bytes: limits.outputBytes, html_files: limits.htmlFiles },
    },
    observed: {
      catalogue: {
        modules: counts.modules,
        objects: counts.objects,
        relations: counts.relations,
        raw_bytes: catalogueRawBytes,
        gzip_bytes: catalogueGzipBytes,
        manifest: {
          raw_bytes: manifestBytes.byteLength,
          gzip_bytes: deterministicGzipSize(manifestBytes),
        },
        search: { raw_bytes: searchRawBytes, gzip_bytes: searchGzipBytes },
        shards: {
          count: manifest.shards.length,
          largest_raw_bytes: largestShardRawBytes,
          largest_gzip_bytes: largestShardGzipBytes,
        },
      },
      projections: {
        count: projectionCount,
        maximum_nodes: projectionMaxNodes,
        maximum_edges: projectionMaxEdges,
      },
      client_bytes: output.clientBytes,
      pages,
      output: { bytes: output.outputBytes, files: output.files, html_files: output.htmlFiles.length },
    },
  };
}

async function writeEvidence(report) {
  const configured = process.env.BROWSER_EVIDENCE_DIR?.trim();
  if (!configured) return;
  const evidenceDirectory = resolve(configured);
  const reportPath = join(evidenceDirectory, 'network-budgets.json');
  requireBudget(dirname(reportPath) === evidenceDirectory, 'invalid browser evidence report path');
  await mkdir(evidenceDirectory, { recursive: true });
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
}

try {
  const report = await buildReport();
  await writeEvidence(report);
  const { catalogue, projections, pages, output, client_bytes: clientBytes } = report.observed;
  console.log(
    'NETWORK_BUDGETS_GREEN'
      + ` catalogue=${catalogue.raw_bytes}/${catalogue.gzip_bytes}`
      + ` search=${catalogue.search.raw_bytes}/${catalogue.search.gzip_bytes}`
      + ` shard_max=${catalogue.shards.largest_raw_bytes}/${catalogue.shards.largest_gzip_bytes}`
      + ` projections=${projections.count}:${projections.maximum_nodes}/${projections.maximum_edges}`
      + ` client=${clientBytes}`
      + ` home=${pages.home.raw_bytes}/${pages.home.gzip_bytes}`
      + ` explore=${pages.explore.raw_bytes}/${pages.explore.gzip_bytes}`
      + ` occurrence_max=${pages.maximum_occurrence.raw_bytes}/${pages.maximum_occurrence.gzip_bytes}`
      + ` output=${output.bytes}`
      + ` html=${output.html_files}`,
  );
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  const failure = { schema: 'mathgraph.website-network-budget-report.v1', status: 'FAIL', error: message };
  try {
    await writeEvidence(failure);
  } catch (evidenceError) {
    const evidenceMessage = evidenceError instanceof Error ? evidenceError.message : String(evidenceError);
    console.error(`NETWORK_BUDGETS_EVIDENCE_ERROR ${evidenceMessage}`);
  }
  console.error(`NETWORK_BUDGETS_RED ${message}`);
  process.exitCode = 1;
}
