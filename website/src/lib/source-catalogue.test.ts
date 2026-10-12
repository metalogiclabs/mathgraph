import { cp, mkdtemp, readFile, rm, unlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterEach, describe, expect, test } from 'vitest';
import { canonicalJson, sha256Hex } from './integrity';
import {
  SOURCE_CATALOGUE_MANIFEST_SHA256,
  loadSourceCatalogueV1,
  parseCanonicalSourceJson,
} from './source-catalogue';

const published = resolve(process.cwd(), 'public/catalogues/mathlib/v4.34.1');
const temporary: string[] = [];

async function copyPublication(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), 'mathgraph-source-catalogue-ts-'));
  temporary.push(root);
  await cp(published, root, { recursive: true });
  return root;
}

async function rewriteManifest(root: string, mutate: (manifest: any) => void): Promise<string> {
  const path = join(root, 'manifest.json');
  const manifest = JSON.parse(await readFile(path, 'utf8'));
  mutate(manifest);
  const bytes = canonicalJson(manifest);
  await writeFile(path, bytes);
  return sha256Hex(bytes);
}

async function rewriteShard(root: string, mutate: (shard: any) => void): Promise<string> {
  const manifestPath = join(root, 'manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const metadata = manifest.shards[0];
  const oldPath = join(root, metadata.path);
  const shard = JSON.parse(await readFile(oldPath, 'utf8'));
  mutate(shard);
  const shardBytes = canonicalJson(shard);
  const shardSha = sha256Hex(shardBytes);
  const relativePath = `shards/${shardSha}.json`;
  await unlink(oldPath);
  await writeFile(join(root, relativePath), shardBytes);
  metadata.path = relativePath;
  metadata.sha256 = shardSha;
  metadata.size_bytes = Buffer.byteLength(shardBytes);
  const manifestBytes = canonicalJson(manifest);
  await writeFile(manifestPath, manifestBytes);
  return sha256Hex(manifestBytes);
}

afterEach(async () => {
  await Promise.all(temporary.splice(0).map(path => rm(path, { recursive: true, force: true })));
});

describe('strict committed source catalogue loader', () => {
  test('validates the exact complete authority-free publication', async () => {
    const catalogue = await loadSourceCatalogueV1();
    expect(catalogue.manifest_sha256).toBe(SOURCE_CATALOGUE_MANIFEST_SHA256);
    expect(catalogue.manifest.counts).toEqual({
      modules: 13,
      objects: 2345,
      relations: 3571,
      omitted_type_references: 19141,
      omitted_imports: 93,
      omitted_declarations: 1201,
    });
    expect(catalogue.shards).toHaveLength(13);
    expect(catalogue.search).toHaveLength(2345);
    expect(catalogue.result).toEqual({
      source_status: 'SOURCE_INDEXED',
      independent_verification: 'NOT_CHECKED',
      current_applicability: 'NOT_CHECKED',
      freshness: 'PINNED_HISTORICAL_SOURCE',
      authorization: 'NONE',
      authority: 'NONE',
    });
    expect(catalogue.manifest.source.commit).toBe('d13f23b723b8a846827a245b89c10fc7d3f11612');
    expect(catalogue.manifest.source.tree).toBe('efa132418a56d0e38c56cc412a06df22178dac5c');
  });

  test('rejects noncanonical JSON, unsafe numbers and scalar-invalid text before interpretation', () => {
    expect(() => parseCanonicalSourceJson(Buffer.from('{"a":1,"a":1}'), 1024)).toThrow('NONCANONICAL_JSON');
    expect(() => parseCanonicalSourceJson(Buffer.from('{"a":-0}'), 1024)).toThrow('UNSUPPORTED_JSON_VALUE');
    expect(() => parseCanonicalSourceJson(Buffer.from('{"a":1.0}'), 1024)).toThrow('NONCANONICAL_JSON');
    expect(() => parseCanonicalSourceJson(Buffer.from('{"a":"\\ud800"}'), 1024)).toThrow('UNSUPPORTED_JSON_VALUE');
    expect(() => parseCanonicalSourceJson(Buffer.from('{ "a": 1 }'), 1024)).toThrow('NONCANONICAL_JSON');
  });

  test('rejects missing, extra and path-escaping publication files', async () => {
    const missing = await copyPublication();
    const missingManifest = JSON.parse(await readFile(join(missing, 'manifest.json'), 'utf8'));
    await unlink(join(missing, missingManifest.shards[0].path));
    await expect(loadSourceCatalogueV1({ root: missing })).rejects.toThrow('MISSING_PUBLICATION_FILE');

    const extra = await copyPublication();
    await writeFile(join(extra, 'shards', `${'f'.repeat(64)}.json`), '{}');
    await expect(loadSourceCatalogueV1({ root: extra })).rejects.toThrow('PUBLICATION_INVENTORY_MISMATCH');

    const escape = await copyPublication();
    const digest = await rewriteManifest(escape, manifest => { manifest.shards[0].path = '../escape.json'; });
    await expect(loadSourceCatalogueV1({ root: escape, expectedManifestSha256: digest })).rejects.toThrow('INVALID_MANIFEST_SCHEMA');
  });

  test('derives search from occurrences and does not trust a rehashed search file', async () => {
    const root = await copyPublication();
    const searchPath = join(root, 'search.json');
    const search = JSON.parse(await readFile(searchPath, 'utf8'));
    search[0].statement = 'False';
    const searchBytes = canonicalJson(search);
    await writeFile(searchPath, searchBytes);
    const digest = await rewriteManifest(root, manifest => {
      manifest.search.sha256 = sha256Hex(searchBytes);
      manifest.search.size_bytes = Buffer.byteLength(searchBytes);
    });
    await expect(loadSourceCatalogueV1({ root, expectedManifestSha256: digest })).rejects.toThrow('SEARCH_DERIVATION_MISMATCH');
  });

  test('rejects rehashed source substitutions, identity collisions, invalid ranges and promoted relations', async () => {
    const source = await copyPublication();
    const sourceDigest = await rewriteManifest(source, manifest => { manifest.source.commit = '0'.repeat(40); });
    await expect(loadSourceCatalogueV1({ root: source, expectedManifestSha256: sourceDigest })).rejects.toThrow('SOURCE_PIN_MISMATCH');

    const identity = await copyPublication();
    const identityDigest = await rewriteManifest(identity, manifest => {
      manifest.modules[0].objects[1] = structuredClone(manifest.modules[0].objects[0]);
    });
    await expect(loadSourceCatalogueV1({ root: identity, expectedManifestSha256: identityDigest })).rejects.toThrow('DUPLICATE_NAME');

    const range = await copyPublication();
    const rangeDigest = await rewriteShard(range, shard => {
      shard.objects[0].source.range.end = structuredClone(shard.objects[0].source.range.start);
    });
    await expect(loadSourceCatalogueV1({ root: range, expectedManifestSha256: rangeDigest })).rejects.toThrow('INVALID_RANGE');

    const relation = await copyPublication();
    const relationDigest = await rewriteShard(relation, shard => { shard.relations[0].logical_implication = true; });
    await expect(loadSourceCatalogueV1({ root: relation, expectedManifestSha256: relationDigest })).rejects.toThrow(/INVALID_SHARD_SCHEMA|AUTHORITY_ESCALATION/);
  });

  test('preserves opaque noncritical extensions and declines unknown critical ones', async () => {
    const noncritical = await copyPublication();
    const extension = { id: 'urn:example:opaque', version: 1, critical: false, payload: { note: 'uninterpreted' } };
    const digest = await rewriteManifest(noncritical, manifest => { manifest.extensions.push(extension); });
    const loaded = await loadSourceCatalogueV1({ root: noncritical, expectedManifestSha256: digest });
    expect(loaded.manifest.extensions).toContainEqual(extension);
    expect(loaded.result.authority).toBe('NONE');

    const critical = await copyPublication();
    const criticalDigest = await rewriteManifest(critical, manifest => {
      manifest.extensions.push({ ...extension, id: 'urn:example:critical', critical: true });
    });
    await expect(loadSourceCatalogueV1({ root: critical, expectedManifestSha256: criticalDigest })).rejects.toThrow('UNKNOWN_CRITICAL_EXTENSION');
  });
});
