import { cp, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { describe, expect, test } from 'vitest';
import sharp from 'sharp';

import record from '../src/data/l4yaml-record.json';
import resolveRecord from '../src/data/resolve-record.json';
import resolveScenarios from '../src/data/resolve-scenarios.json';
import { loadSourceCatalogueV1 } from '../src/lib/source-catalogue';
import { projectSourceCatalogueV1 } from '../src/lib/object-projections';
import { objectSlug } from '../src/lib/object-locators';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(website, 'dist');
const execFileAsync = promisify(execFile);
const importImplementationCommit = '1204a1d267b6217c45c9b17f093cc3587450cf78';
const importSourceRoot = `https://github.com/metalogiclabs/mathgraph/blob/${importImplementationCommit}`;

async function page(path: string): Promise<string> {
  return readFile(join(dist, path, 'index.html'), 'utf8');
}

function visibleText(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

describe('primary public evidence experience', () => {
  test('renders the complete living knowledge catalogue as progressively enhanced semantic HTML', async () => {
    const html = await page('explore').catch(() => '');
    const text = visibleText(html);
    expect(html).toContain('data-knowledge-catalogue');
    expect(html).toContain('data-catalogue-url-state');
    expect(html).toContain('data-catalogue-ranked');
    expect((html.match(/data-catalogue-item(?=[\s>])/g) ?? [])).toHaveLength(2372);
    expect(text).toContain('Real.rpow');
    expect(text).toContain('SOURCE_INDEXED');
    expect(text).toContain('NOT_CHECKED');
    expect(text).toContain('Source indexing is not independent proof checking.');
    expect(text).toContain('Every entry remains available without JavaScript.');
    expect(html).toContain('<noscript>');
    expect(html).toContain('name="q"');
    expect(html).toContain('data-catalogue-no-match');
    expect(html).toContain('href="/discover/"');
  });

  test('renders a permanent source occurrence with exact pins, unknowns, omissions and a bounded map', async () => {
    const catalogue = await loadSourceCatalogueV1();
    const projection = projectSourceCatalogueV1(catalogue);
    const occurrence = projection.objects.find(object => object.title === 'Real.rpow')!;
    const slug = objectSlug(occurrence);
    const html = await page(`objects/${slug}`).catch(() => '');
    const text = visibleText(html);
    expect(html).toContain('data-source-occurrence-detail');
    expect(text).toContain('Real.rpow');
    expect(text).toContain('Mathlib.Analysis.SpecialFunctions.Pow.Real');
    expect(text).toContain(catalogue.manifest.source.repository);
    expect(text).toContain(catalogue.manifest.source.commit);
    expect(text).toContain(catalogue.manifest.source.tree);
    expect(text).toContain('SOURCE_INDEXED');
    expect(text).toContain('NOT_CHECKED');
    expect(text).toContain('PINNED_HISTORICAL_SOURCE');
    expect(text).toContain('Omitted structural references');
    expect(text).toContain('Independent validation');
    expect(text).toContain('python3 -I -S -B conformance/source_catalogue_v1/consumer.py');
    expect(html).toContain('data-knowledge-map');
    expect(html).toContain('data-map-center');
    expect(text).toContain('Presentation projection · authority NONE · not a certificate, proof, or verifier');
    expect(html).toContain(`/catalogues/mathlib/v4.34.1/`);
  });

  test('exposes bounded projection objects, typed relations and full source-linked details without JavaScript', async () => {
    const html = await page('objects').catch(() => '');
    const text = visibleText(html);
    expect(html).toContain('data-knowledge-map');
    expect(text).toContain('Presentation projection · authority NONE · not a certificate, proof, or verifier');
    expect(html).toMatch(/<input[^>]*type="checkbox"[^>]*data-map-kind/);
    expect(html).toContain('data-object-detail');
    expect(html).toContain('data-map-select');
    expect(html).toContain('data-map-export');
    expect(html).toContain('data-map-limit');
    for (const field of ['Canonical identity', 'Source pins', 'Attribution', 'Evidence', 'Verifier authority', 'Assumptions', 'Scope', 'historical_result', 'lifecycle', 'research_maturity', 'current_applicability', 'freshness', 'action_authorization', 'Incoming relations', 'Outgoing relations', 'Lineage', 'Replay boundary', 'Unknowns', 'Unsupported semantics']) expect(text).toContain(field);
    expect(text).toContain('No declared incoming relations in this displayed projection');
    expect(text).toContain('No declared outgoing relations in this displayed projection');
    expect(text).toContain('No declared alternative support route');
    expect(text).toContain('Display-only traversal');
    expect(text).toMatch(/14 of 14 objects.*7 of 7 relations/);
    expect(html).toMatch(/<svg[^>]*aria-labelledby=/);
    expect(html).toContain('EVIDENCE_FOR');
    expect(html).toContain('WITHDRAWS');
    expect(html).toContain('/developers/#offline-replay');
    expect(html).toContain('<noscript>');
  });

  test('makes the source-derived living network the homepage entry point without authority inflation', async () => {
    const html = await page('');
    const text = visibleText(html);
    expect(text).toContain('Knowledge you can verify. Capabilities you can build on.');
    expect(html).toMatch(/<form[^>]+action="\/explore\/"[^>]+method="get"[^>]+data-home-search/);
    expect(html).toMatch(/<input[^>]+name="q"/);
    expect(html).toMatch(/Content-Security-Policy[^>]+form-action 'self'/);
    expect(html).not.toContain('data-import-workbench');
    for (const [value, label] of [['2,345', 'Indexed declarations'], ['1', 'Qualified bounded result'], ['3,578', 'Typed source-backed relations'], ['4', 'External source projects'], ['1', 'Qualified reusable capability']]) {
      expect(text).toContain(value); expect(text).toContain(label);
    }
    expect(text).not.toContain('Total network');
    expect(text).toContain('DECLARES 2,345');
    expect(text).toContain('TYPE_REFERENCES 1,224');
    expect(text).toContain('IMPORTS_MODULE 2');
    expect(text).toContain('Real.rpow');
    expect(text).toContain('SOURCE_INDEXED');
    expect(text).toContain('Independent verification NOT_CHECKED');
    expect(html).toContain('data-source-neighborhood');
    expect(html).toContain('TYPE_REFERENCES');
    expect(html).toMatch(/href="\/objects\/object-[a-f0-9]{64}\//);
    expect(text).toContain(record.id);
    expect(text).toContain('One finite representation-refinement profile');
    expect(text).toContain('Independent verification');
    expect(html).toContain('data-home-quick-start');
  });

  test('connects canonical objects from exploration, Resolve and historical records', async () => {
    for (const route of ['explore', 'resolve', 'records', `records/${record.id}/v1`]) {
      expect(await page(route)).toContain('href="/objects/');
    }
  });

  test('links repository-relative capability pins to their published artifact mirror', async () => {
    const html = await page('objects');
    for (const path of ['fixtures/capability-contract.json', 'evaluation.json', 'trust-policy.json', 'receipt.json']) {
      expect(html).toContain(`href="/artifacts/conformance/capability_v1/${path}"`);
      expect(html).not.toContain(`href="conformance/capability_v1/${path}"`);
    }
  });

  test.each(['verify', 'check'])('offers the same honest local import workflow on /%s', async (route) => {
    const html = await page(route).catch(() => '');
    const text = visibleText(html);
    expect(html).toContain('data-import-workbench');
    expect(html).toMatch(/<input[^>]+type="file"[^>]+accept="application\/json,.json"[^>]+disabled/);
    expect(html).not.toMatch(/<input[^>]+type="url"/);
    expect(text).toContain('65,536 bytes');
    expect(text).toContain('4,321 bytes');
    expect(text).toContain('UNKNOWN');
    expect(text).toContain('No proof, kernel, or source-suite execution');
    expect(html).toContain(`/evidence/${record.id}/record.json`);
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain('<noscript>');
    for (const stage of ['interpret', 'check', 'resolve', 'explore', 'export']) {
      expect(html).toContain(`data-import-step="${stage}"`);
    }
    for (const region of ['source', 'evidence', 'scope', 'unknowns']) {
      expect(html).toContain(`data-import-${region}`);
    }
    expect(text).toContain('python3 -I -S scripts/mathgraph_import_v1.py');
    expect(text).toContain('--policy-sha256');
    expect(text).toContain('Download presentation JSON');
  });

  test('pins historical importer checkout, consumer, and separately reviewed policy', async () => {
    for (const route of ['', 'verify', 'check', 'developers']) {
      const html = await page(route);
      const text = visibleText(html);
      expect(text).toContain(`git checkout --detach ${importImplementationCommit}`);
      expect(html).toContain(`${importSourceRoot}/conformance/import_v1/consumer.py`);
      expect(html).toContain(`${importSourceRoot}/conformance/import_v1/fixtures/trust-policy.json`);
      expect(html).not.toMatch(/github\.com\/metalogiclabs\/mathgraph\/blob\/main\/(?:conformance\/import_v1|scripts\/mathgraph_import_v1\.py)/);
      if (route) {
        expect(text).toMatch(/importer is available on main/i);
        expect(text).not.toMatch(/importer is not yet available on main/i);
      }
    }
  });

  test('keeps durable evidence links legible on the dark section', async () => {
    const css = await readFile(join(website, 'src/styles/global.css'), 'utf8');
    expect(css).toMatch(/\.section--ink \.source-link__label\s*{[^}]*color:\s*white/s);
    expect(css).toMatch(/\.section--ink \.source-link__meta\s*{[^}]*color:\s*#aeb7c7/s);
    expect(css).toMatch(/\.section--ink \.lede\s*{[^}]*color:\s*#aeb7c7/s);
  });

  test('allows developer content to shrink within a mobile grid track', async () => {
    const css = await readFile(join(website, 'src/styles/global.css'), 'utf8');
    expect(css).toMatch(/\.prose\s*{[^}]*min-width:\s*0/s);
    expect(css).toMatch(/@media \(max-width: 900px\)[\s\S]*\.page-grid\s*{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/);
  });

  test('allows long machine-facing identifiers in headings to wrap on mobile', async () => {
    const css = await readFile(join(website, 'src/styles/global.css'), 'utf8');
    expect(css).toMatch(/h1\s*{[^}]*overflow-wrap:\s*anywhere/s);
  });

  test.each(['', 'records', `records/${record.id}`])('builds /%s as a complete document', async (route) => {
    const html = await page(route);

    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toMatch(/<nav[^>]+aria-label="Primary"/);
    expect(html).toContain('<main id="main-content"');
    expect(html).toContain('Evidence you can inspect. Results you can reuse.');
  });

  test('builds Resolve as a complete public surface with the qualified historical default', async () => {
    const html = await page('resolve');
    const text = visibleText(html);

    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toMatch(/<nav[^>]+aria-label="Primary"/);
    expect(html).toContain('<main id="main-content"');
    expect(text).toContain('Evidence can change without truth becoming false.');
    expect(text).toContain('Support is reclosed locally.');
    expect(text).toContain('Independent support remains.');
    expect(text).toContain('Cycles cannot create evidence.');
    expect(html).toContain('data-static-qualified-default');
    expect(html).toContain('data-default-scenario="published-after"');
    expect(text).toContain('Published after publisher withdrawal');
  });

  test('puts the selective consequence comparison before the secondary Resolve controls', async () => {
    const html = await page('resolve');
    const comparison = html.match(/<section[^>]+data-resolve-comparison[\s\S]+?<\/section>/)?.[0] ?? '';
    const text = visibleText(comparison);

    expect(comparison).not.toBe('');
    expect(html.indexOf('data-resolve-comparison')).toBeLessThan(html.indexOf('class="resolve-controls"'));
    expect(comparison).toContain('data-selected-scenario="published-after"');
    expect(text).toContain('What changed — and what did not');
    expect(text).toContain('openai.original_support.1');
    expect(text).toMatch(/SOURCE_DOCUMENTED.*STALE/i);
    expect(text).toContain('openai.theorem.1');
    expect(text).toMatch(/UNKNOWN.*UNKNOWN/i);
    expect(text).toMatch(/not REFUTED/i);
    expect(text).toContain('jpl.l4yaml.finite_parser_acceptance');
    expect(text).toMatch(/WARRANTED_BOUNDED.*WARRANTED_BOUNDED/i);
    expect(text).toContain('nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases');
    expect(text).toMatch(/browser neither resolves, qualifies, nor mutates/i);
    for (const [id, label] of [
      ['published-after', 'Qualified history'],
      ['modeled-before', 'Modeled baseline'],
      ['withdraw-openai.original_publication_receipt.1', 'Counterfactual'],
    ]) {
      expect(comparison).toMatch(new RegExp(`<button[^>]+data-resolve-select="${id.replaceAll('.', '[.]')}"[^>]+disabled`, 'i'));
      expect(text).toContain(label);
    }
  });

  test('renders all seven historic outcomes at both permanent Resolve record routes', async () => {
    const current = await page(`records/${resolveRecord.id}`);
    const versioned = await page(`records/${resolveRecord.id}/v1`);

    for (const html of [current, versioned]) {
      const text = visibleText(html);
      for (const claimId of Object.keys(resolveRecord.resolutions)) expect(text).toContain(claimId);
      expect((html.match(/data-historical-result-row/g) ?? [])).toHaveLength(7);
      expect(text).toMatch(/openai\.original_support\.1.*SOURCE_DOCUMENTED.*STALE/i);
      expect(text).toMatch(/openai\.theorem\.1.*UNKNOWN.*UNKNOWN/i);
      expect(text).toMatch(/jpl\.l4yaml\.finite_parser_acceptance.*WARRANTED_BOUNDED.*WARRANTED_BOUNDED/i);
      expect(text).toContain('Publication history is a source notice, not a formal theorem verifier.');
      expect(text).toMatch(/modeled as active.*does not prove their correctness/i);
      expect(text).toMatch(/same-owner independent implementation/i);
      expect(text).toMatch(/did not rerun the original JPL Lean proof/i);
      expect(text).not.toMatch(/withdrawn propositions? (?:are|were) (?:false|refuted)/i);
    }
  });

  test('keeps Resolve epistemic, lifecycle, maturity, applicability, freshness, and action axes distinct', async () => {
    const html = await page(`records/${resolveRecord.id}/v1`);
    const text = visibleText(html);

    expect(text).toMatch(/Historical epistemic result.*SCOPED_MIXED/i);
    expect(text).toMatch(/Catalogue lifecycle.*CURRENT/i);
    expect(text).toMatch(/Research maturity.*BOUNDED_QUALIFIED/i);
    expect(text).toMatch(/Current applicability.*UNKNOWN/i);
    expect(text).toMatch(/Freshness.*NOT_CHECKED/i);
    expect(text).toMatch(/Action policy.*READ_ONLY_NO_AUTOMATIC_AUTHORIZATION/i);
    expect(html).toContain('data-status-family="epistemic"');
    expect(html).toContain('data-status-family="lifecycle"');
    expect(html).toContain('data-status-family="maturity"');
    expect(html).toContain('data-status-family="applicability"');
    expect(html).toContain('data-status-family="freshness"');
    expect(html).toContain('data-status-family="action"');
    expect(text).not.toMatch(/universally verified/i);
  });

  test('separates published history from synthetic conformance scenarios', async () => {
    const html = await page('resolve');
    const text = visibleText(html);

    expect(text).toContain('Published record');
    expect(text).toContain('Synthetic conformance simulations');
    expect(text).toContain('Synthetic kernel tests, not historical facts about OpenAI or JPL.');
    expect(text).toMatch(/simulation.*never mutates.*historic snapshot/i);
    expect(text).toContain('Before and after support resolution for the selected precomputed scenario');
    expect(text).toContain('Selected scenario state');
    expect(text).toContain('Historic graph boundary — unchanged by simulations.');
    for (const scenario of resolveScenarios.SYNTHETIC_CONFORMANCE.scenarios) {
      expect(html).toContain(`value="${scenario.id}"`);
      expect(text).toContain(scenario.label);
    }
  });

  test('shows declared graph topology and literal scenario fields without derived authority labels', async () => {
    const html = await page('resolve');
    const text = visibleText(html);
    const detailText = visibleText(await page(`records/${resolveRecord.id}/v1`));

    expect(text).toContain('Declared evidence receipts');
    expect(text).toContain('Exact withdrawn_evidence field');
    expect(text).toContain('Listed in withdrawn_evidence');
    expect(text).toContain('Declared graph routes');
    expect(text).toContain('Exact active_routes field');
    expect(text).toContain('Listed in active_routes');
    expect(text).not.toContain('AVAILABLE');
    expect(text).not.toContain('WITHDRAWN / STALE');
    expect(text).not.toContain('ACTIVE IN THIS VIEW');
    expect(text).not.toContain('INACTIVE IN THIS VIEW');
    expect(text).not.toContain('INACTIVE AFTER WITHDRAWAL');
    expect(detailText).toContain('Exact record withdrawn_evidence field');
    for (const misleadingLabel of ['AVAILABLE', 'WITHDRAWN / STALE', 'ACTIVE IN THIS VIEW', 'INACTIVE IN THIS VIEW', 'INACTIVE AFTER WITHDRAWAL']) {
      expect(detailText).not.toContain(misleadingLabel);
    }
  });

  test('provides keyboard-native controls and a fail-closed static fallback', async () => {
    const html = await page('resolve');

    expect(html).toMatch(/<fieldset[^>]*data-scenario-group="PUBLISHED_RECORD"/);
    expect(html).toMatch(/<fieldset[^>]*data-scenario-group="SYNTHETIC_CONFORMANCE"/);
    expect(html).toMatch(/<input[^>]+type="radio"[^>]+value="published-after"[^>]+checked[^>]+disabled/);
    expect(html).toContain('aria-live="polite"');
    expect(html).toMatch(/role="alert"[^>]+data-resolve-error[^>]+hidden/);
    expect(html).toContain('<noscript>');
    expect(html).toMatch(/qualified static default remains shown/i);
    expect(html).toContain('data-static-qualified-default');
    expect(html).toMatch(/interaction failure.*restored.*server-rendered.*default/i);
  });

  test('uses the transparent black MathGraph mark while preserving the browser icons', async () => {
    const html = await page('');

    expect(html).toMatch(/<img[^>]+class="brand__mark"[^>]+src="\/mathgraph-mark-black\.png"[^>]+alt=""[^>]*>/);
    expect(html).toContain('<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">');
    expect(html).toContain('<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">');

    for (const asset of ['mathgraph-mark-black.png', 'favicon-32.png', 'apple-touch-icon.png']) {
      const bytes = await readFile(join(dist, asset));
      expect(bytes.subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    }
  });

  test('publishes the requested homepage SEO title without changing the MathGraph identity', async () => {
    const html = await page('');

    expect(html).toContain('<title>MathGraph — Open Verification Infrastructure</title>');
    expect(html).toContain('<meta property="og:title" content="MathGraph — Open Verification Infrastructure">');
    expect(html).toContain('<meta property="og:site_name" content="MathGraph">');
    expect(html).toContain('<span class="brand__word">MathGraph');
  });

  test('renders the qualified record from the same machine-readable values', async () => {
    const html = await page(`records/${record.id}`);
    const text = visibleText(html);

    expect(html).toContain(record.id);
    expect(html).toContain(record.content_sha256);
    expect(html).toContain(record.source.commit);
    expect(html).toContain(record.source.external_suite_commit);
    expect(html).toContain('48/48');
    expect(text).toMatch(/31 Expected acceptances/i);
    expect(text).toMatch(/17 Expected rejections/i);
    expect(html).toContain('52/52');
    expect(text).toMatch(/NOT CHECKED/i);
    expect(text).toContain('UNKNOWN');
    expect(html).toContain('&amp;x [*x]');
  });

  test('renders identical substantive evidence at current and permanent versioned routes', async () => {
    const current = await page(`records/${record.id}`);
    const versioned = await page(`records/${record.id}/v1`);

    for (const value of [
      record.id,
      record.content_sha256,
      record.source.commit,
      record.source.external_suite_commit,
      '48/48',
      '52/52',
      'UNKNOWN',
      '&amp;x [*x]',
    ]) {
      expect(current).toContain(value);
      expect(versioned).toContain(value);
    }
    const permanent = `https://mathgraph.org/records/${record.id}/v1/`;
    expect(current).toContain(`<link rel="canonical" href="${permanent}">`);
    expect(versioned).toContain(`<link rel="canonical" href="${permanent}">`);
    expect(current).toContain('/records/index.json');
    expect(versioned).toContain('/records/index.json');
    expect(visibleText(versioned)).toMatch(/Version 1.*Lifecycle.*Current/i);
    expect(visibleText(versioned)).toMatch(/metadata updated.*evidence unchanged/i);
    expect(`${current}${versioned}`).not.toContain('vercel.app');
  });

  test('generates no page for an unknown record identity', async () => {
    await expect(page('records/mg-not-published/v1')).rejects.toMatchObject({ code: 'ENOENT' });
  });

  test('keeps status scoped and avoids universal or endorsement language', async () => {
    const html = `${await page('')}${await page('records')}${await page(`records/${record.id}`)}`;
    const text = visibleText(html);

    expect(text).toMatch(/WARRANTED — BOUNDED/i);
    expect(text).toContain('No affiliation or endorsement implied');
    expect(text).not.toMatch(/verified by (NASA|JPL)/i);
    expect(text).not.toMatch(/NASA[- ]verified/i);
    expect(text).not.toMatch(/universally verified/i);
    expect(text).not.toMatch(/quantum[- ]proof/i);
  });

  test.each(['check', 'protocol', 'developers'])('builds the /%s public surface', async (route) => {
    const html = await page(route);
    expect(html).toMatch(/<nav[^>]+aria-label="Primary"/);
    expect(html).toContain('<main id="main-content"');
  });

  test('onboards agents through exact machine-readable scope', async () => {
    const html = await page('agents');
    const text = visibleText(html);

    expect(text).toContain('Point your agent to mathgraph.org/agents');
    expect(html).toContain('/llms.txt');
    expect(html).toContain('/.well-known/mathgraph.json');
    expect(html).toContain('/records/index.json');
    expect(text).toContain(record.content_sha256);
    expect(text).toContain(record.source.commit);
    expect(text).toContain(record.source.external_suite_commit);
    expect(text).toMatch(/exact.*record ID.*version.*source pin.*suite pin.*goal/i);
    expect(text).toMatch(/unsupported.*UNKNOWN/i);
    expect(text).toMatch(/integrity.*not.*authenticity/i);
    expect(text).toMatch(/MCP.*not deployed/i);
    expect(html).not.toContain('vercel.app');
  });

  test('separates exact source matching from bounded offline Resolve replay for agents', async () => {
    const html = await page('agents');
    const text = visibleText(html);

    expect(text).toMatch(/record 001.*exact source-scope match/i);
    expect(text).toMatch(/record 002.*offline dependency replay/i);
    expect(html).toContain(`/evidence/${resolveRecord.id}/offline/consumer.py`);
    expect(html).toContain(`/evidence/${resolveRecord.id}/offline/bundle.json`);
    expect(html).toContain(`/evidence/${resolveRecord.id}/offline/trust-policy.json`);
    expect(text).toMatch(/same-origin digests?.*trusted pin.*not authenticity/i);
    expect(text).toMatch(/Current applicability.*UNKNOWN/i);
    expect(text).toMatch(/Freshness.*NOT_CHECKED/i);
    expect(text).toMatch(/does not rerun the original JPL Lean proof/i);
    expect(text).toMatch(/same-owner.*not.*outside-organization adoption/i);
  });

  test('gives agents a fail-closed source-catalogue consumption sequence', async () => {
    const html = await page('agents');
    const text = visibleText(html);

    expect(html).toContain('data-agent-source-catalogue');
    expect(html).toContain('data-agent-source-sequence');
    expect((html.match(/data-agent-source-step=/g) ?? [])).toHaveLength(7);
    for (const value of ['SOURCE_INDEXED', 'NOT_CHECKED', 'PINNED_HISTORICAL_SOURCE', 'NONE']) expect(text).toContain(value);
    expect(text).toMatch(/DECLARES.*IMPORTS_MODULE.*TYPE_REFERENCES/i);
    expect(text).toMatch(/structural.*never.*implication.*equivalence/i);
    expect(text).toMatch(/same origin.*detects changed bytes.*does not authenticate.*compromised origin.*mathematical truth/i);
    expect(text).toMatch(/independently chosen channel/i);
    expect(text).toMatch(/unsupported version.*critical extension.*forged status.*missing endpoint.*decline/i);
    expect(html).toContain('/catalogues/mathlib/v4.34.1/manifest.json');
    expect(html).toContain('/artifacts/conformance/source_catalogue_v1/consumer.py');
    expect(html).toContain('/artifacts/conformance/source_catalogue_v1/trust-policy.json');
  });

  test('documents only runnable static consumers and keeps hosted interfaces undeployed', async () => {
    const html = await page('developers');
    const text = visibleText(html);

    expect(text).toContain('python3 -I -S consumer.py');
    expect(text).toContain('python3 -I -S -c');
    expect(text).not.toMatch(/\bpython\s+(?:-I|-m)\b/);
    expect(text).toContain('--bundle bundle.json');
    expect(text).toContain('--policy trust-policy.json');
    expect(text).toContain('--policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a');
    expect(text).toContain('27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b');
    expect(text).toContain('node resolve-consumer-v1.ts https://mathgraph.org');
    expect(text).toContain('e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e');
    expect(html).toContain(`/evidence/${resolveRecord.id}/offline/consumer.py`);
    expect(html).toContain('/examples/resolve-consumer-v1.ts');
    expect(text).toMatch(/TypeScript.*HTTP client.*not.*offline/i);
    expect(text).toMatch(/verify.*independently obtained.*consumer.*policy pins.*before execution/i);
    expect(text).toMatch(/public resolver.*NOT_DEPLOYED/i);
    expect(text).toMatch(/MCP.*NOT_DEPLOYED/i);
    expect(text).not.toMatch(/assert sha256/i);
    expect(text).not.toMatch(/(?:implemented|deployed) hosted (?:resolver|API)/i);
    expect(text).not.toMatch(/hosted (?:resolver|API) (?:is|are) (?:implemented|deployed)/i);
  });

  test('documents the exact independently replayed source-catalogue command and boundary', async () => {
    const html = await page('developers');
    const text = visibleText(html);

    expect(html).toContain('id="source-catalogue"');
    expect(html).toContain('data-source-catalogue-command');
    expect(text).toContain('python3 -I -S -B conformance/source_catalogue_v1/consumer.py');
    expect(text).toContain('--catalogue-root website/public/catalogues/mathlib/v4.34.1');
    expect(text).toContain('--policy conformance/source_catalogue_v1/trust-policy.json');
    expect(text).toContain('--policy-sha256 c3cdec2b2c784728621bb8c25a055a1e73d67d3c1c922b7ab62b09003399e1c9');
    expect(text).toContain('--audit-imports');
    expect(text).toContain('8e8f5f529b44852815627206dc5b45062f0c96d6');
    expect(text).toContain('7519de6a51e524caf70df51d37389ff42d430d43');
    expect(text).toContain('eb3149b70f0cdf39109c775898b19a26574c27e6');
    expect(text).toContain('e6643d8e3d207893713da94041ff3822c1190457');
    expect(text).toMatch(/run-specific policy.*did not.*public trust-policy bytes/i);
    expect(text).toContain('5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68');
    expect(text).toContain('583dcfca46854f56469cdda865b5da62b1068e985bdce411dac9c587e556ca5d');
    expect(text).toContain('SOURCE_INDEXED');
    expect(text).toMatch(/imports neither.*producer implementation.*protocol package/i);
    expect(text).toMatch(/does not fetch.*source.*run Lean.*prove declarations.*check current applicability.*authorize action/i);
  });

  test('defines the minimum independently implementable P0 protocol without application dependencies', async () => {
    const html = await page('protocol');
    const text = visibleText(html);

    expect(text).toMatch(/Applications may depend on the protocol.*protocol does not depend on MathGraph\.org/i);
    for (const objectName of ['Typed claim', 'Evidence receipt', 'Dependency route', 'Resolution', 'Trust policy', 'Immutable snapshot']) {
      expect(text).toContain(objectName);
    }
    expect(text).toMatch(/route is conjunctive/i);
    expect(text).toMatch(/separate routes.*alternatives/i);
    expect(text).toMatch(/least fixed point.*qualified root/i);
    expect(text).toMatch(/cycles.*cannot.*self-justification/i);
    expect(text).toMatch(/unsupported.*transport.*UNKNOWN|unsupported.*transport.*error/i);
    expect(text).toMatch(/historical qualification.*current applicability/i);
    expect(text).toMatch(/Check.*Implemented at the qualified record-001 boundary/i);
    expect(text).toMatch(/Resolve.*Bounded-qualified offline/i);
    expect(text).toMatch(/Discover.*local advisory contract/i);
    expect(text).toMatch(/Develop.*QUALIFIED_BOUNDED.*eight/i);
    expect(text).toMatch(/Capabilities.*one qualified finite entry/i);
    expect(text).toMatch(/in-toto.*unsigned correspondence only/i);
    expect(text).toMatch(/Sigstore.*SCITT.*RATS.*deferred/i);
  });

  test('publishes the Lean evidence profile as an unstable proposal', async () => {
    const html = await page('protocol/profiles/lean');
    const text = visibleText(html);

    for (const value of [
      'formalization.yaml',
      'Declaration names',
      'Permitted axioms',
      'Statement SHA-256',
      'Proof SHA-256',
      'Lean commit',
      'Mathlib commit',
      'Comparator',
      'Policy digest',
      'Independent-kernel receipt',
      'Statement fidelity',
    ]) {
      expect(text).toContain(value);
    }
    expect(text).toContain('PROPOSED');
    expect(text).toContain('mathgraph.lean-evidence-profile.draft-1');
    expect(text).toMatch(/no qualified Lean record/i);
    expect(text).toMatch(/Playground.*future.*receipt/i);
  });

  test('exposes four outcome journeys and a progressively enhanced menu', async () => {
    const html = await page('');
    const nav = html.match(/<nav[^>]+aria-label="Primary"[^>]*>[\s\S]*?<\/nav>/)?.[0] ?? '';
    for (const label of ['Explore', 'Verify', 'Build', 'Developers']) expect(nav).toContain(`>${label}</a>`);
    expect(nav.match(/<a /g)).toHaveLength(5);
    expect(nav).toContain('GitHub');
    expect(html).toMatch(/<button[^>]+aria-expanded="false"[^>]+aria-controls="primary-navigation"[^>]*>Menu<\/button>/);
    expect(nav).not.toContain('hidden');
    expect(nav).not.toContain('aria-current');
  });

  test.each([
    ['explore', 'explore', 'page'], ['records', 'explore', 'location'], ['discover', 'explore', 'location'],
    [`records/${record.id}/v1`, 'explore', 'location'],
    ['verify', 'verify', 'page'], ['check', 'verify', 'location'], ['resolve', 'verify', 'location'],
    ['build', 'build', 'page'], ['develop', 'build', 'location'], ['capabilities', 'build', 'location'],
    ['developers', 'developers', 'page'], ['agents', 'developers', 'location'], ['protocol', 'developers', 'location'],
    ['protocol/profiles/lean', 'developers', 'location'],
  ])('marks /%s in the %s outcome group with aria-current=%s', async (route, group, state) => {
    const html = await page(route).catch(() => '');
    const nav = html.match(/<nav[^>]+aria-label="Primary"[^>]*>[\s\S]*?<\/nav>/)?.[0] ?? '';
    expect(nav).toContain(`href="/${group}/" aria-current="${state}"`);
    expect(nav.match(/aria-current=/g)).toHaveLength(1);
  });

  test('gives visitors a bounded route into exploration and capability reuse', async () => {
    const explore = await page('explore').catch(() => '');
    const build = await page('build').catch(() => '');
    expect(explore).toContain('href="/records/"');
    expect(explore).toContain('href="/discover/"');
    expect(visibleText(explore)).toContain(record.title);
    expect(visibleText(explore)).toMatch(/advisory/i);
    expect(build).toContain('href="/develop/"');
    expect(build).toContain('href="/capabilities/"');
    expect(visibleText(build)).toContain('QUALIFIED_BOUNDED');
    expect(visibleText(build)).toMatch(/compiler.*unimplemented/i);
  });

  test('presents outcome journeys with their actual maturity boundaries', async () => {
    const html = await page('');
    const text = visibleText(html);

    expect(html).toContain('<h1>Knowledge you can verify. Capabilities you can build on.</h1>');
    expect(text).toContain('Bring a claim, proof, repository, or research artifact. Discover what has been established, what remains unknown, how it connects, and what can be reused.');
    for (const route of ['explore', 'verify', 'build']) expect(html).toContain(`data-outcome="${route}"`);
    for (const section of ['source-to-result', 'map-preview', 'capability', 'independent-verification', 'quick-start', 'long-term']) expect(html).toContain(`id="${section}"`);
    expect(text).toMatch(/Discover.*advisory/i);
    expect(text).toMatch(/compiler.*unimplemented/i);
    expect(text).toMatch(/no autonomous loop/i);
    for (const route of ['discover', 'develop', 'capabilities']) expect(html).toContain(`href="/${route}/"`);
  });

  test('shows real source-derived evidence and map relations without implying new verification', async () => {
    const html = await page('');
    const text = visibleText(html);

    expect(text).toContain('48/48');
    expect(text).toContain('52/52');
    expect(text).toContain('Whole-language correctness');
    expect(text).toContain('Statement fidelity');
    expect(text).toContain('Generalization');
    expect(text).toContain('EXACT_SCOPE_MATCH');
    expect(text).toContain('SOURCE_PIN_MISMATCH');
    expect(text).toContain('UNSUPPORTED_GOAL');
    expect(html).toContain('href="/agents/"');
    expect(text).toContain('mathgraph.l4yaml.48-case-qualification');
    expect(text).toContain('jpl.l4yaml.finite_parser_acceptance');
    expect(text).toContain('EVIDENCE_FOR');
    expect(text).toContain('/derivation/routes/3/evidence/0');
    expect(text).toContain('PRESENTATION_PROJECTION');
    expect(text).toMatch(/authority.*NONE/i);
    expect(text).toMatch(/does not rerun the original.*proof/i);
    const quickStart = html.match(/<section id="quick-start"[\s\S]*?<\/section>/)?.[0] ?? '';
    expect(visibleText(quickStart)).toContain('freshness NOT_CHECKED');
  });

  test('separates evidence, lifecycle, and maturity status treatments', async () => {
    const recordHtml = await page(`records/${record.id}/v1`);
    const profileHtml = await page('protocol/profiles/lean');
    const combined = `${recordHtml}${profileHtml}`;

    expect(visibleText(recordHtml)).toMatch(/Evidence result.*Warranted — bounded/i);
    expect(visibleText(recordHtml)).toMatch(/Lifecycle.*Current/i);
    expect(combined).toMatch(/data-status-family="evidence"[^>]*>[\s\S]*aria-hidden="true"/);
    expect(combined).toMatch(/data-status-family="lifecycle"[^>]*>[\s\S]*aria-hidden="true"/);
    expect(combined).toMatch(/data-status-family="maturity"[^>]*>[\s\S]*aria-hidden="true"/);
    expect(visibleText(profileHtml)).toMatch(/PROPOSED.*intended contract.*EXPERIMENTAL.*implemented research artifact/i);
  });

  test('publishes presentation-only 1200 × 630 social cards for both immutable records', async () => {
    const sourceId = record.id;
    const resolveId = resolveRecord.id;
    for (const id of [sourceId, resolveId]) {
      const html = await page(`records/${id}/v1`);
      const imagePath = join(dist, 'social', 'records', `${id}-v1.png`);
      const sourcePath = join(dist, 'social', 'records', `${id}-v1.source.svg`);
      const metadata = await sharp(imagePath).metadata();
      const source = await readFile(sourcePath, 'utf8');
      expect(html).toContain(`<meta property="og:image" content="https://mathgraph.org/social/records/${id}-v1.png">`);
      expect(html).toContain('<meta property="og:image:width" content="1200">');
      expect(html).toContain('<meta property="og:image:height" content="630">');
      expect(html).toContain('<meta name="twitter:card" content="summary_large_image">');
      expect(metadata.width).toBe(1200);
      expect(metadata.height).toBe(630);
      expect(metadata.format).toBe('png');
      expect(source).toContain(id);
    }
    const sourceCard = await readFile(join(dist, 'social', 'records', `${sourceId}-v1.source.svg`), 'utf8');
    expect(sourceCard).toContain(`${record.content_sha256.slice(0, 16)}…${record.content_sha256.slice(-8)}`);
    expect(sourceCard).toContain('WARRANTED · BOUNDED');
    expect(sourceCard).toContain('UNKNOWN · whole-language correctness');
    const resolveCard = await readFile(join(dist, 'social', 'records', `${resolveId}-v1.source.svg`), 'utf8');
    for (const copy of [
      'HISTORIC SNAPSHOT · SCOPED_MIXED',
      '3 stale documentary paths',
      '3 UNKNOWN propositions',
      '1 exactly scoped WARRANTED_BOUNDED observation retained',
      'CURRENT APPLICABILITY · UNKNOWN',
      'Presentation only · authority NONE',
    ]) expect(resolveCard).toContain(copy);
    expect(resolveCard).not.toMatch(/(?:OpenAI|JPL).*(?:verified|refuted)/i);
  });

  test('rejects a Resolve card when source predicates disagree without editing committed evidence', async () => {
    const fixtureRoot = await mkdtemp(join(tmpdir(), 'mathgraph-social-card-mismatch-'));
    try {
      await Promise.all([
        cp(join(website, 'src/data'), join(fixtureRoot, 'src/data'), { recursive: true }),
        cp(join(website, 'public/evidence'), join(fixtureRoot, 'public/evidence'), { recursive: true }),
        cp(join(website, 'public/social/records'), join(fixtureRoot, 'public/social/records'), { recursive: true }),
      ]);
      const fixtureRecordPath = join(fixtureRoot, `public/evidence/${resolveRecord.id}/record.json`);
      const fixtureRecord = JSON.parse(await readFile(fixtureRecordPath, 'utf8'));
      fixtureRecord.resolutions['openai.original_support.1'].after = 'UNKNOWN';
      await writeFile(fixtureRecordPath, `${JSON.stringify(fixtureRecord, null, 2)}\n`);
      await expect(execFileAsync(process.execPath, [join(website, 'scripts/generate-social-card.mjs'), '--check'], {
        cwd: fixtureRoot,
      })).rejects.toMatchObject({ stderr: expect.stringContaining('SOCIAL_CARD_RESOLVE_FACTS_MISMATCH') });
    } finally {
      await rm(fixtureRoot, { recursive: true, force: true });
    }
  });

  test('renders complete progressively enhanced record and capability catalogues', async () => {
    const recordsHtml = await page('records');
    const capabilitiesHtml = await page('capabilities');
    for (const [html, count] of [[recordsHtml, 2], [capabilitiesHtml, 2]] as const) {
      expect(html).toContain('data-catalogue-filter');
      expect(html).toMatch(/<input[^>]*type="search"[^>]*data-catalogue-query[^>]*disabled/);
      expect(html).toMatch(/<button[^>]*data-catalogue-clear[^>]*disabled/);
      expect(html).toContain('data-catalogue-select');
      expect(html).toContain('data-catalogue-count');
      expect(html).toContain('aria-live="polite"');
      expect(html).toContain('data-catalogue-no-match');
      expect(visibleText(html)).toContain('The current static catalogue has no matching displayed entries.');
      expect((html.match(/data-catalogue-item(?:[ >])/g) ?? [])).toHaveLength(count);
      expect(html).toContain('<noscript>');
    }
    for (const entry of ['mg-l4yaml-source-check-20261010', 'mg-living-warrant-openai-jpl-20261010']) {
      expect(recordsHtml).toContain(entry);
    }
    for (const entry of ['urn:mathgraph:capability:finite-developmental-growth', 'urn:mathgraph:capability:vdn-lean']) {
      expect(capabilitiesHtml).toContain(entry);
    }
    expect(recordsHtml).toContain('data-catalogue-record-kind');
    expect(recordsHtml).toContain('data-catalogue-lifecycle');
    expect(capabilitiesHtml).toContain('data-catalogue-qualification');
  });

  test('documents responsibilities and operations without widening module authority', async () => {
    const protocol = visibleText(await page('protocol'));
    for (const responsibility of ['Object responsibility', 'Relation responsibility', 'Evidence responsibility', 'Resolution responsibility', 'Transition responsibility']) {
      expect(protocol).toContain(responsibility);
    }
    expect(protocol).toMatch(/CLOSE.*bounded support closure/i);
    expect(protocol).toMatch(/ACT.*caller policy.*NONE/i);
    expect(protocol).toMatch(/REFINE.*separately qualified.*never rewrites historic bytes/i);
    const discover = visibleText(await page('discover'));
    for (const value of ['PARTIAL', 'advisory_only: true', 'can_promote_truth: false', 'NOT_CHECKED', 'FULL_REPLAY_UNAVAILABLE']) expect(discover).toContain(value);
    const develop = visibleText(await page('develop'));
    for (const value of ['eight-state', 'QUALIFIED_BOUNDED', 'Capability Family Compiler', 'NOT_IMPLEMENTED', 'EXPERIMENTAL', 'Current applicability', 'UNKNOWN', 'Action authorization', 'NONE']) expect(develop).toContain(value);
    const agents = visibleText(await page('agents'));
    expect(agents).toMatch(/record 001.*exact-scope/i);
    expect(agents).toMatch(/record 002.*historical offline replay/i);
    expect(agents).toMatch(/browser.*map.*authority.*NONE/i);
    const developers = visibleText(await page('developers'));
    expect(developers).toMatch(/in-toto.*unsigned correspondence/i);
    for (const boundary of ['authenticity', 'signer policy', 'transparency', 'freshness', 'qualification', 'current applicability', 'action authorization']) expect(developers).toContain(boundary);
    expect(developers).toMatch(/Sigstore.*SCITT.*RATS.*deferred/i);
  });

  test('renders the source-grounded Discovery frontier as an incomplete advisory omission', async () => {
    const html = await page('discover');
    const text = visibleText(html);

    for (const boundary of [
      'Source-grounded frontier', 'Real.log_rpow', 'Real.log', '42 distinct indexed declarations',
      'ADVISORY', 'INCOMPLETE', 'Terminal form NONE', 'NOT_CHECKED',
      'Authority NONE', 'Authorization NONE',
      'Next gate 1 — catalogue expansion', 'Later gate 2 — Lean proof qualification',
    ]) expect(text).toContain(boundary);
    expect(text).toMatch(/omission.*does not create.*TYPE_REFERENCES relation/i);
    expect(text).toMatch(/not a proof, countermodel, or named obstruction/i);
    expect(text).toMatch(/catalogue expansion alone cannot establish proof validity/i);
    expect(html).toContain('href="/objects/object-8d7d18f07e0f6262a3b65bbb71105c16c69ab67a6d96a78c18e97cfa7afc2322/"');
    expect(html).toContain('href="/catalogues/mathlib/v4.34.1/manifest.json"');
    expect(html).toContain('href="/catalogues/mathlib/v4.34.1/shards/6400eba377e910ff2ac4bea415657e6c84b546832d93808c9fcb9dce952d22c0.json"');
    expect(html).toContain('href="https://github.com/leanprover-community/mathlib4/blob/d13f23b723b8a846827a245b89c10fc7d3f11612/Mathlib/Analysis/SpecialFunctions/Pow/Real.lean#L491-L496"');
    expect(text).toContain('PARTIAL');
    expect(text).toContain('FULL_REPLAY_UNAVAILABLE');
  });

  test('documents a scoped badge embed linked to the permanent boundary', async () => {
    const html = await page('developers');
    const text = visibleText(html);

    expect(text).toContain('Scoped badge embed');
    expect(text).toContain('Markdown');
    expect(text).toContain('HTML');
    expect(html).toContain(`/v1/badges/${record.id}.svg`);
    expect(html).toContain(`/records/${record.id}/v1/`);
    expect(text).toMatch(/not a universal truth badge/i);
  });

  test('explains independent verification axes on Check', async () => {
    const text = visibleText(await page('check'));
    expect(text).toContain('Source identity');
    expect(text).toContain('Formal verification');
    expect(text).toContain('Finite executable evaluation');
    expect(text).toContain('Statement fidelity');
    expect(text).toContain('Generalization');
    expect(text).toContain('Requalification and revocation');
    expect(text).toMatch(/Warranted — bounded/i);
  });

  test('labels protocol maturity and separates authenticity from truth', async () => {
    const text = visibleText(await page('protocol'));
    expect(text).toContain('MGSO');
    expect(text).toContain('Implemented');
    expect(text).toContain('Experimental');
    expect(text).toContain('Proposed');
    expect(text).toContain('ML-DSA-65');
    expect(text).toMatch(/signature authenticates.*not.*truth/i);
    expect(text).not.toMatch(/quantum[- ]proof/i);
  });

  test('documents the exact resolver contract without claiming public deployment', async () => {
    const html = await page('developers');
    const text = visibleText(html);
    expect(text).toContain('Quickstart');
    expect(text).toContain('/v1/resolve');
    expect(text).toContain(record.id);
    expect(text).toContain(record.source.commit);
    expect(text).toContain(record.source.external_suite_commit);
    expect(text).toContain('WARRANTED_BOUNDED');
    expect(text).toContain('UNKNOWN');
    expect(html).toContain('finite_parser_acceptance');
    expect(html).not.toContain('pinned_external_case_agreement');
    expect(text).toMatch(/not.*publicly deployed/i);
  });

  test('ships a restrictive CSP with external executable JavaScript', async () => {
    const html = await page('');
    expect(html).toMatch(/http-equiv="Content-Security-Policy"/);
    expect(html).toContain("default-src 'self'");
    expect(html).toContain("object-src 'none'");
    expect(html).toMatch(/<script type="module" src="\/_assets\/[^"]+\.js"><\/script>/);
    expect(html).not.toMatch(/<script type="module">/);
  });

  test('builds an honest missing state and complete sitemap', async () => {
    const notFound = await readFile(join(dist, '404.html'), 'utf8');
    const sitemap = await readFile(join(dist, 'sitemap.xml'), 'utf8');
    expect(visibleText(notFound)).toContain('Evidence not found');
    for (const route of ['/', '/explore/', '/verify/', '/build/', '/check/', '/resolve/', '/records/', `/records/${record.id}/`, '/protocol/', '/developers/', '/about/', '/contact/']) {
      expect(sitemap).toContain(`https://mathgraph.org${route}`);
    }
    for (const route of ['about', 'contact']) {
      const html = await page(route);
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain('MathGraph');
    }
    const about = visibleText(await page('about'));
    expect(about).toMatch(/open verification and trust infrastructure.*Metalogic Labs/i);
    const contact = await page('contact');
    expect(contact).toContain('https://github.com/metalogiclabs/mathgraph');
    expect(contact).toContain('https://github.com/metalogiclabs/mathgraph/issues');
    expect(contact).not.toMatch(/mailto:|@[a-z0-9.-]+\.[a-z]{2,}/i);
    const home = await page('');
    expect(home).toContain('href="/about/"');
    expect(home).toContain('href="/contact/"');
  });
});
