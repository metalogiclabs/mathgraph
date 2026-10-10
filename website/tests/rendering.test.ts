import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';
import sharp from 'sharp';

import record from '../src/data/l4yaml-record.json';
import resolveRecord from '../src/data/resolve-record.json';
import resolveScenarios from '../src/data/resolve-scenarios.json';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(website, 'dist');

async function page(path: string): Promise<string> {
  return readFile(join(dist, path, 'index.html'), 'utf8');
}

function visibleText(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

describe('primary public evidence experience', () => {
  test('keeps durable evidence links legible on the dark section', async () => {
    const css = await readFile(join(website, 'src/styles/global.css'), 'utf8');
    expect(css).toMatch(/\.section--ink \.source-link__label\s*{[^}]*color:\s*white/s);
    expect(css).toMatch(/\.section--ink \.source-link__meta\s*{[^}]*color:\s*#aeb7c7/s);
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
    expect(html).toContain('<nav aria-label="Primary">');
    expect(html).toContain('<main id="main-content"');
    expect(html).toContain('Evidence you can inspect. Results you can reuse.');
  });

  test('builds Resolve as a complete public surface with the qualified historical default', async () => {
    const html = await page('resolve');
    const text = visibleText(html);

    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toContain('<nav aria-label="Primary">');
    expect(html).toContain('<main id="main-content"');
    expect(text).toContain('Evidence can change without truth becoming false.');
    expect(text).toContain('Support is reclosed locally.');
    expect(text).toContain('Independent support remains.');
    expect(text).toContain('Cycles cannot create evidence.');
    expect(html).toContain('data-static-qualified-default');
    expect(html).toContain('data-default-scenario="published-after"');
    expect(text).toContain('Published after publisher withdrawal');
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
    expect(text).toContain('Historic graph boundary — unchanged by simulations.');
    for (const scenario of resolveScenarios.SYNTHETIC_CONFORMANCE.scenarios) {
      expect(html).toContain(`value="${scenario.id}"`);
      expect(text).toContain(scenario.label);
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
    expect(html).toContain('<nav aria-label="Primary">');
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

  test('links Agents from primary navigation', async () => {
    const html = await page('');
    expect(html).toMatch(/<nav aria-label="Primary">[\s\S]*href="\/agents\/"[\s\S]*>Agents</);
  });

  test('adds Resolve to navigation and introduces the four-part cycle without advertising future routes', async () => {
    const html = await page('');
    const text = visibleText(html);

    expect(html).toMatch(/<nav aria-label="Primary">[\s\S]*href="\/resolve\/"[\s\S]*>Resolve</);
    expect(text).toContain('Discover what matters. Check what holds. Resolve what remains justified. Develop what becomes possible.');
    expect(text).toContain('Inspect real evidence');
    expect(text).toMatch(/Discover.*Advisory/i);
    expect(text).toMatch(/Check.*Implemented/i);
    expect(text).toMatch(/Resolve.*Bounded-qualified/i);
    expect(text).toMatch(/Develop.*Experimental/i);
    expect(html).not.toContain('href="/discover/"');
    expect(html).not.toContain('href="/develop/"');
    expect(html).not.toContain('href="/capabilities/"');
  });

  test('makes evidence boundaries and canned scope matches inspectable without arbitrary input', async () => {
    const html = await page('');
    const text = visibleText(html);

    expect(text).toContain('Receipts for machine claims');
    expect(text).not.toMatch(/record 001/i);
    expect(text).toContain('48/48');
    expect(text).toContain('52/52');
    expect(text).toContain('Whole-language correctness');
    expect(text).toContain('Statement fidelity');
    expect(text).toContain('Generalization');
    expect(text).toContain('EXACT_SCOPE_MATCH');
    expect(text).toContain('SOURCE_PIN_MISMATCH');
    expect(text).toContain('UNSUPPORTED_GOAL');
    expect(html).toContain('href="/agents/"');
    expect(html).not.toMatch(/<(?:input|textarea|form)\b/i);
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

  test('publishes a deterministic large social card for the permanent record', async () => {
    const html = await page(`records/${record.id}/v1`);
    const imagePath = join(dist, 'social', 'records', `${record.id}-v1.png`);
    const sourcePath = join(dist, 'social', 'records', `${record.id}-v1.source.svg`);
    const metadata = await sharp(imagePath).metadata();
    const source = await readFile(sourcePath, 'utf8');

    expect(html).toContain(`<meta property="og:image" content="https://mathgraph.org/social/records/${record.id}-v1.png">`);
    expect(html).toContain('<meta property="og:image:width" content="1200">');
    expect(html).toContain('<meta property="og:image:height" content="630">');
    expect(html).toContain('<meta name="twitter:card" content="summary_large_image">');
    expect(metadata.width).toBe(1200);
    expect(metadata.height).toBe(630);
    expect(metadata.format).toBe('png');
    expect(source).toContain(record.id);
    expect(source).toContain(`${record.content_sha256.slice(0, 16)}…${record.content_sha256.slice(-8)}`);
    expect(source).toContain('WARRANTED · BOUNDED');
    expect(source).toContain('UNKNOWN · whole-language correctness');
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
    for (const route of ['/', '/check/', '/records/', `/records/${record.id}/`, '/protocol/', '/developers/']) {
      expect(sitemap).toContain(`https://mathgraph.org${route}`);
    }
  });
});
