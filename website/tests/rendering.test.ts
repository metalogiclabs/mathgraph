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
    const text = visibleText(await page('developers'));
    expect(text).toContain('Quickstart');
    expect(text).toContain('/v1/resolve');
    expect(text).toContain(record.id);
    expect(text).toContain(record.source.commit);
    expect(text).toContain(record.source.external_suite_commit);
    expect(text).toContain('WARRANTED_BOUNDED');
    expect(text).toContain('UNKNOWN');
    expect(text).toMatch(/not.*publicly deployed/i);
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
