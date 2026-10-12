import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from 'vitest';
import Ajv from 'ajv';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const repository = join(website, '..');
const read = (path: string) => readFile(join(repository, path));
const built = (path: string) => readFile(join(website, 'dist', path), 'utf8');
const json = async (path: string) => JSON.parse((await read(path)).toString());
const plain = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const sourceCommit = '02a817e8de64c65e4d88d43a6279ee9f16d4364d';

test.each(['discover', 'develop', 'capabilities'])('publishes the static /%s surface with navigation and no execution inputs', async (route) => {
  const html = await built(`${route}/index.html`).catch(() => '');
  expect(html).toContain('<main id="main-content"');
  expect(html).toContain(`<link rel="canonical" href="https://mathgraph.org/${route}/">`);
  expect(html).not.toMatch(/<(?:form|textarea)\b|<input[^>]+type="(?:file|url)"/i);
  if (route === 'capabilities') expect(html).toMatch(/<input[^>]+type="search"[^>]+data-catalogue-query/);
  else expect(html).not.toMatch(/<input\b/i);
  expect(plain(html)).toMatch(/hosted service.*NOT_DEPLOYED/i);
  expect(await built('sitemap.xml')).toContain(`<loc>https://mathgraph.org/${route}/</loc>`);
});

test('Discover exposes the real incomplete advisory result and source identity without truth promotion', async () => {
  const result = await json('conformance/discover_v1/fixtures/result.json');
  const html = await built('discover/index.html').catch(() => '');
  const text = plain(html);
  for (const value of [result.status, result.verification_status, result.attention_interpretation, ...result.reason_codes, ...result.source_diagnostics]) expect(text).toContain(value);
  expect(text).toContain('advisory_only: true');
  expect(text).toContain('can_promote_truth: false');
  expect(text).toMatch(/attention.*allocation.*not.*truth confidence/i);
  expect(text).toMatch(/reported historical metrics.*not.*new verification/i);
  for (const source of result.sources) {
    expect(text).toContain(source.source_id);
    expect(text).toContain(source.sha256);
    if (source.repo_path) expect(html).toContain(`https://github.com/metalogiclabs/mathgraph/blob/${sourceCommit}/${source.repo_path}`);
  }
  for (const candidate of result.ranked_candidates) expect(text).toContain(candidate.candidate_id);
});

test('qualified capability presentation binds exact registry artifacts and keeps candidates separate', async () => {
  const registry = await json('protocol/registries/capabilities-v1.json');
  const html = await built('capabilities/index.html').catch(() => '');
  const qualified = html.split('id="qualified"')[1]?.split('id="candidates"')[0] ?? '';
  expect(registry.qualified_entries).toHaveLength(1);
  expect((qualified.match(/data-qualified-capability=/g) ?? [])).toHaveLength(1);
  for (const entry of registry.qualified_entries) {
    expect(qualified).toContain(entry.id);
    expect(qualified).toContain(entry.profile);
    for (const name of ['contract', 'evaluation', 'qualification_receipt', 'trust_policy']) {
      const pin = entry[name];
      const bytes = await read(pin.locator);
      expect(bytes.byteLength).toBe(pin.size_bytes);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(pin.sha256);
      expect(qualified).toContain(`/artifacts/${pin.locator}`);
      expect(qualified).toContain(pin.sha256);
      expect(await readFile(join(website, 'dist/artifacts', pin.locator))).toEqual(bytes);
    }
    const contract = await json(entry.contract.locator);
    const evaluation = await json(entry.evaluation.locator);
    expect(plain(qualified)).toContain(contract.claim.scope);
    for (const limit of contract.limitations) expect(plain(qualified)).toContain(limit);
    for (const value of ['qualification', 'current_applicability', 'freshness', 'revocation', 'supersession', 'action_authorization']) expect(qualified).toContain(evaluation[value]);
  }
  for (const candidate of registry.experimental_candidates) {
    expect(html.split('id="candidates"')[1]).toContain(candidate.id);
    expect(qualified).not.toContain(candidate.id);
    expect(plain(html)).toContain(candidate.description);
  }
  expect(await readFile(join(website, 'dist/capabilities/index-v1.json'))).toEqual(await read('protocol/registries/capabilities-v1.json'));
});

test('Develop retains the finite qualification scope and distinguishes the unimplemented compiler', async () => {
  const html = await built('develop/index.html').catch(() => '');
  const text = plain(html);
  const contract = await json('conformance/capability_v1/fixtures/capability-contract.json');
  expect(text).toContain(contract.claim.scope);
  expect(text).toContain('QUALIFIED_BOUNDED');
  expect(text).toMatch(/Capability Family Compiler.*NOT_IMPLEMENTED/i);
  expect(text).toMatch(/same-owner implementation-independent qualification/i);
  expect(text).toMatch(/VDN.*Lean.*EXPERIMENTAL/i);
  expect(text).toMatch(/general descriptor evaluator.*UNKNOWN/i);
  expect(text).toMatch(/does not add.*mathematical terminal form/i);
  for (const limit of contract.limitations) expect(text).toContain(limit);
});

test('machine and human entry points agree on static modules and unsigned interoperability', async () => {
  const manifest = JSON.parse(await built('.well-known/mathgraph.json'));
  const schema = JSON.parse(await built('schemas/discovery-v4.schema.json').catch(() => '{}'));
  expect(manifest.schema).toBe('mathgraph.discovery.v4');
  const ajv = new Ajv({ allErrors: true, strict: true });
  expect(ajv.validate(schema, manifest), ajv.errorsText()).toBe(true);
  expect(manifest.interfaces.discover).toMatchObject({ maturity: 'IMPLEMENTED_LOCAL_ADVISORY', mode: 'LOCAL_CLI', public_interface: 'NOT_DEPLOYED', example_status: 'PARTIAL', advisory_only: true, can_promote_truth: false });
  expect(manifest.interfaces.develop).toMatchObject({ maturity: 'QUALIFIED_BOUNDED', mode: 'OFFLINE_FINITE_REPLAY', public_interface: 'NOT_DEPLOYED', compiler: 'NOT_IMPLEMENTED', current_applicability: 'UNKNOWN', freshness: 'NOT_CHECKED', action_authorization: 'NONE' });
  expect(manifest.interfaces.capabilities).toMatchObject({ maturity: 'STATIC_REGISTRY', qualified_entries: 1, experimental_candidates: 1, registry: 'https://mathgraph.org/capabilities/index-v1.json' });
  expect(manifest.interfaces.external_binding).toMatchObject({ mode: 'LOCAL_UNSIGNED_CORRESPONDENCE', signature: 'UNSIGNED', qualification: 'UNKNOWN', action_authorization: 'NONE' });
  expect(manifest.source_catalogue).toMatchObject({
    catalogue_id: 'mathlib-v4.34.1-foundations-v1',
    catalogue_version: 1,
    result: {
      source_status: 'SOURCE_INDEXED', independent_verification: 'NOT_CHECKED', current_applicability: 'NOT_CHECKED',
      freshness: 'PINNED_HISTORICAL_SOURCE', authorization: 'NONE', authority: 'NONE',
    },
    semantics: { logical_implication: false, semantic_equivalence: false },
  });
  expect(manifest.source_catalogue.relation_types).toEqual(['DECLARES', 'IMPORTS_MODULE', 'TYPE_REFERENCES']);
  expect(manifest.capabilities.source_catalogue).toBe('IMPLEMENTED_STATIC_SOURCE_INDEX');
  expect(manifest.capabilities.mcp).toBe('NOT_DEPLOYED');
  const registry = await json('protocol/registries/capabilities-v1.json');
  const result = await json('conformance/discover_v1/fixtures/result.json');
  const evaluation = await json('conformance/capability_v1/evaluation.json');
  expect(manifest.interfaces.capabilities.qualified_entries).toBe(registry.qualified_entries.length);
  expect(manifest.interfaces.capabilities.experimental_candidates).toBe(registry.experimental_candidates.length);
  expect(manifest.interfaces.discover.example_status).toBe(result.status);
  for (const field of ['advisory_only', 'can_promote_truth', 'verification_status', 'attention_interpretation']) expect(manifest.interfaces.discover[field]).toBe(result[field]);
  expect(manifest.interfaces.develop.maturity).toBe(evaluation.qualification);
  expect(manifest.interfaces.develop.profile).toBe(evaluation.contract.profile);
  for (const field of ['current_applicability', 'freshness', 'revocation', 'supersession', 'action_authorization']) expect(manifest.interfaces.develop[field]).toBe(evaluation[field]);
  for (const field of ['contract', 'evaluation', 'qualification_receipt', 'trust_policy']) {
    expect(manifest.interfaces.develop[field]).toBe(`https://mathgraph.org/artifacts/${registry.qualified_entries[0][field].locator}`);
    expect(manifest.interfaces.develop[`${field}_sha256`]).toBe(registry.qualified_entries[0][field].sha256);
  }
  for (const [group, field, path] of [
    ['discover', 'request', 'conformance/discover_v1/fixtures/request.json'],
    ['discover', 'result', 'conformance/discover_v1/fixtures/result.json'],
    ['external_binding', 'statement', 'conformance/interoperability_v1/statement.json'],
    ['capabilities', 'registry', 'protocol/registries/capabilities-v1.json'],
  ]) expect(manifest.interfaces[group][`${field}_sha256`]).toBe(createHash('sha256').update(await read(path)).digest('hex'));
  const llms = await built('llms.txt');
  for (const route of ['discover', 'develop', 'capabilities']) {
    expect(llms).toContain(`https://mathgraph.org/${route}/`);
    for (const page of ['', 'protocol/', 'agents/', 'developers/']) expect(await built(`${page}index.html`)).toContain(`href="/${route}/"`);
  }
  for (const field of ['PARTIAL', 'ALLOCATION_NOT_TRUTH_CONFIDENCE', 'FULL_REPLAY_UNAVAILABLE', 'QUALIFIED_BOUNDED', 'NOT_IMPLEMENTED', 'UNSIGNED', 'SOURCE_INDEXED', 'PINNED_HISTORICAL_SOURCE']) expect(llms).toContain(field);
  for (const route of ['discover/', 'develop/', 'capabilities/', 'protocol/', 'agents/', 'developers/']) {
    const html = await built(`${route}index.html`);
    expect(plain(html)).not.toMatch(/(?:deployed|live) (?:Discover|Develop|capability) (?:API|service)|universally verified|autonomous improvement is (?:qualified|verified)/i);
  }
});

test('all normative schemas remain exact public projections and modular downloads retain source bytes', async () => {
  for (const name of await readdir(join(repository, 'protocol/schemas'))) {
    if (!name.endsWith('.json')) continue;
    expect(await readFile(join(website, 'dist/schemas', name))).toEqual(await read(`protocol/schemas/${name}`));
  }
  for (const path of ['conformance/discover_v1/fixtures/request.json', 'conformance/discover_v1/fixtures/result.json', 'conformance/capability_v1/fixtures/finite-representation-refinement-v1.json', 'conformance/capability_v1/consumer.py', 'conformance/interoperability_v1/statement.json', 'conformance/source_catalogue_v1/consumer.py', 'conformance/source_catalogue_v1/trust-policy.json', 'conformance/source_catalogue_v1/README.md']) {
    expect(await readFile(join(website, 'dist/artifacts', path)).catch(() => Buffer.alloc(0))).toEqual(await read(path));
  }
});
