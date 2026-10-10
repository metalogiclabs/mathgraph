import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';

import record from '../src/data/l4yaml-record.json';

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

  test.each(['', 'records', `records/${record.id}`])('builds /%s as a complete document', async (route) => {
    const html = await page(route);

    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toContain('<nav aria-label="Primary">');
    expect(html).toContain('<main id="main-content"');
    expect(html).toContain('Evidence you can inspect. Results you can reuse.');
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
    expect(visibleText(versioned)).toMatch(/Version 1.*Lifecycle current/i);
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
