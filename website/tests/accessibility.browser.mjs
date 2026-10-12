// Read-only accessibility qualification over the exact existing dist/ bytes.
// Optional reports and screenshots are written only beneath BROWSER_EVIDENCE_DIR.
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, resolve, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const { AxeBuilder } = await import('@axe-core/playwright');

const root = resolve('dist');
const evidenceDirectory = process.env.BROWSER_EVIDENCE_DIR
  ? resolve(process.env.BROWSER_EVIDENCE_DIR)
  : undefined;
const viewports = [
  { width: 1440, height: 900 },
  { width: 768, height: 900 },
  { width: 390, height: 844 },
];
const routes = [
  { name: 'home', path: '/', statuses: ['SOURCE_INDEXED', 'WARRANTED_BOUNDED'] },
  { name: 'explore', path: '/explore/', statuses: ['SOURCE_INDEXED', 'NOT_CHECKED'] },
  { name: 'verify', path: '/verify/', statuses: ['UNKNOWN', 'NONE'] },
  { name: 'build', path: '/build/', statuses: ['QUALIFIED_BOUNDED', 'UNKNOWN'] },
  { name: 'developers', path: '/developers/', statuses: ['WARRANTED_BOUNDED', 'UNKNOWN'] },
  { name: 'check', path: '/check/', statuses: ['UNKNOWN'] },
  { name: 'resolve', path: '/resolve/', statuses: ['STALE', 'UNKNOWN', 'WARRANTED_BOUNDED'] },
  { name: 'records', path: '/records/', statuses: ['SCOPED_MIXED'] },
  { name: 'discover', path: '/discover/', statuses: ['ADVISORY', 'INCOMPLETE'] },
  { name: 'develop', path: '/develop/', statuses: ['QUALIFIED_BOUNDED', 'NOT_IMPLEMENTED'] },
  { name: 'capabilities', path: '/capabilities/', statuses: ['QUALIFIED_BOUNDED', 'UNKNOWN'] },
  { name: 'protocol', path: '/protocol/', statuses: ['UNKNOWN', 'NOT_IMPLEMENTED'] },
  { name: 'agents', path: '/agents/', statuses: ['SOURCE_INDEXED', 'NONE'] },
  {
    name: 'record-l4yaml-v1',
    path: '/records/mg-l4yaml-source-check-20261010/v1/',
    statuses: ['UNKNOWN', 'NOT_CHECKED_AFTER_SNAPSHOT'],
  },
  {
    name: 'record-resolve-v1',
    path: '/records/mg-living-warrant-openai-jpl-20261010/v1/',
    statuses: ['STALE', 'UNKNOWN', 'WARRANTED_BOUNDED'],
  },
  {
    name: 'source-real-rpow',
    path: '/objects/object-d4f47a456aef565016039d955ab630e0ea7fe7ebc9497be27b66858572fad84a/',
    statuses: ['SOURCE_INDEXED', 'NOT_CHECKED', 'NONE'],
  },
];

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
};

const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const file = resolve(root, `.${pathname.endsWith('/') ? `${pathname}index.html` : pathname}`);
  if (!file.startsWith(`${root}${sep}`)) return response.writeHead(403).end();
  try {
    const bytes = await readFile(file);
    response.writeHead(200, {
      'Cache-Control': 'no-store',
      'Content-Type': contentTypes[extname(file)] ?? 'application/octet-stream',
    }).end(bytes);
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));

const compactAxeItem = item => ({
  id: item.id,
  impact: item.impact,
  description: item.description,
  help: item.help,
  helpUrl: item.helpUrl,
  nodes: item.nodes.map(node => ({
    target: node.target,
    html: node.html,
    failureSummary: node.failureSummary,
  })),
});

const report = {
  schema: 'mathgraph.website-accessibility-report.v1',
  generated_at: new Date().toISOString(),
  input: 'existing dist/',
  browser: { name: 'chromium', version: null },
  java_script: true,
  reduced_motion: 'reduce',
  axe_tags: ['wcag2a', 'wcag2aa'],
  axe_exclusions: [{
    selector: '[data-neighborhood-visual] svg',
    reason: 'The generated diagram is aria-hidden; its exact nodes, relations, labels and links are tested in the adjacent semantic HTML lists.',
  }],
  violation_policy: 'FAIL_ANY',
  viewports,
  routes: [],
};
const manuallyAdjudicatedIncompleteRules = new Set();
const failures = [];
let browser;

try {
  if (evidenceDirectory) await mkdir(evidenceDirectory, { recursive: true });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
  });
  report.browser.version = browser.version();
  const origin = `http://127.0.0.1:${server.address().port}`;

  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport,
      javaScriptEnabled: true,
      reducedMotion: 'reduce',
    });

    for (const route of routes) {
      const page = await context.newPage();
      const runtimeErrors = [];
      const entry = {
        route: route.path,
        name: route.name,
        viewport,
        expected_status_text: route.statuses,
        status: 'PASS',
        runtime_errors: runtimeErrors,
      };
      report.routes.push(entry);
      page.on('pageerror', error => runtimeErrors.push(`pageerror: ${error.message}`));
      page.on('console', message => {
        if (message.type() === 'error') runtimeErrors.push(`console: ${message.text()}`);
      });

      try {
        const response = await page.goto(`${origin}${route.path}`, { waitUntil: 'networkidle' });
        assert.ok(response, `${route.name} ${viewport.width}px: no navigation response`);
        assert.equal(response.status(), 200, `${route.name} ${viewport.width}px: expected HTTP 200`);

        const catalogueFilters = page.locator('[data-catalogue-filter]');
        if (await catalogueFilters.count() > 0) {
          await page.waitForFunction(() => Array.from(document.querySelectorAll('[data-catalogue-filter]')).every(rootElement => {
            const query = rootElement.querySelector('[data-catalogue-query]');
            return rootElement.getAttribute('data-catalogue-ready') === 'true'
              && query instanceof HTMLInputElement
              && !query.disabled;
          }));
        }
        if (route.name === 'explore') {
          const exploreFilter = page.locator('[data-knowledge-catalogue] [data-catalogue-filter]');
          assert.equal(await exploreFilter.getAttribute('data-catalogue-total'), '2372');
          const mounted = await exploreFilter.locator('[data-catalogue-item]').count();
          assert.ok(mounted > 0 && mounted <= 50, `explore: expected bounded interactive result window, received ${mounted}`);
          assert.match(await exploreFilter.locator('[data-catalogue-count]').innerText(), /2,372 catalogue entries/u);
        }

        assert.equal(await page.locator('title').count(), 1, `${route.name}: expected one title element`);
        assert.ok((await page.title()).trim(), `${route.name}: title must not be empty`);
        assert.equal(await page.locator('main').count(), 1, `${route.name}: expected one main landmark`);
        assert.ok((await page.locator('main').innerText()).trim(), `${route.name}: main landmark must not be empty`);
        assert.equal(await page.locator('h1').count(), 1, `${route.name}: expected one h1`);
        assert.ok((await page.locator('h1').innerText()).trim(), `${route.name}: h1 must not be empty`);

        const mainText = await page.locator('main').innerText();
        for (const status of route.statuses) {
          assert.ok(mainText.includes(status), `${route.name}: missing meaningful status text ${status}`);
        }

        await page.evaluate(() => document.activeElement?.blur());
        await page.keyboard.press('Tab');
        const firstFocus = await page.evaluate(() => ({
          className: document.activeElement?.className,
          href: document.activeElement?.getAttribute('href'),
          text: document.activeElement?.textContent?.trim(),
        }));
        assert.equal(firstFocus.className, 'skip-link', `${route.name}: first Tab must focus the skip link`);
        assert.equal(firstFocus.href, '#main-content', `${route.name}: skip link must target #main-content`);
        assert.equal(firstFocus.text, 'Skip to content', `${route.name}: skip link needs a meaningful label`);
        await page.keyboard.press('Enter');
        await page.waitForFunction(() => location.hash === '#main-content');
        assert.equal(await page.evaluate(() => document.querySelector(':target')?.id), 'main-content', `${route.name}: skip link target did not resolve`);

        const layout = await page.evaluate(() => ({
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: window.innerWidth,
          overflow: Array.from(document.querySelectorAll('body *')).map(element => {
            const bounds = element.getBoundingClientRect();
            return {
              tag: element.tagName,
              className: typeof element.className === 'string' ? element.className : '',
              left: Math.round(bounds.left * 100) / 100,
              right: Math.round(bounds.right * 100) / 100,
              text: element.textContent?.trim().slice(0, 100),
            };
          }).filter(item => item.left < -0.5 || item.right > window.innerWidth + 0.5).slice(0, 10),
        }));
        entry.layout = layout;
        assert.ok(layout.documentWidth <= layout.viewportWidth, `${route.name} ${viewport.width}px: horizontal overflow ${JSON.stringify(layout)}`);
        assert.equal(runtimeErrors.length, 0, `${route.name} ${viewport.width}px: runtime errors ${runtimeErrors.join(' | ')}`);

        const axe = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa'])
          .exclude('[data-neighborhood-visual] svg')
          .analyze();
        entry.axe = {
          violations: axe.violations.map(compactAxeItem),
          incomplete: axe.incomplete.map(compactAxeItem),
          passes: axe.passes.map(item => ({ id: item.id, impact: item.impact, node_count: item.nodes.length })),
          inapplicable: axe.inapplicable.map(item => ({ id: item.id, impact: item.impact })),
        };
        const unadjudicatedIncomplete = axe.incomplete.filter(
          item => !manuallyAdjudicatedIncompleteRules.has(item.id),
        );
        if (evidenceDirectory) {
          await page.screenshot({
            path: resolve(evidenceDirectory, `accessibility-${route.name}-${viewport.width}x${viewport.height}.png`),
            fullPage: false,
          });
        }
        if (axe.violations.length > 0) {
          throw new Error(`${route.name} ${viewport.width}px: axe violations ${axe.violations.map(item => `${item.id}:${item.impact} (${item.nodes.length} nodes)`).join(', ')}`);
        }
        if (unadjudicatedIncomplete.length > 0) {
          throw new Error(`${route.name} ${viewport.width}px: unadjudicated axe incomplete findings ${unadjudicatedIncomplete.map(item => `${item.id}:${item.impact} (${item.nodes.length} nodes)`).join(', ')}`);
        }
      } catch (error) {
        entry.status = 'FAIL';
        entry.error = error instanceof Error ? error.message : String(error);
        failures.push(`${route.name} ${viewport.width}x${viewport.height}: ${entry.error}`);
      } finally {
        await page.close();
      }
    }
    await context.close();
  }

  report.summary = {
    pages_scanned: report.routes.length,
    passed: report.routes.filter(entry => entry.status === 'PASS').length,
    failed: report.routes.filter(entry => entry.status === 'FAIL').length,
    axe_violations: report.routes.reduce((total, entry) => total + (entry.axe?.violations.length ?? 0), 0),
    axe_serious_or_critical: report.routes.reduce((total, entry) => total + (entry.axe?.violations.filter(item => ['serious', 'critical'].includes(item.impact)).length ?? 0), 0),
    axe_incomplete: report.routes.reduce((total, entry) => total + (entry.axe?.incomplete.length ?? 0), 0),
    axe_color_contrast_incomplete: report.routes.reduce((total, entry) => total + (entry.axe?.incomplete.filter(item => item.id === 'color-contrast').length ?? 0), 0),
    axe_unadjudicated_incomplete: report.routes.reduce((total, entry) => total + (entry.axe?.incomplete.filter(item => !manuallyAdjudicatedIncompleteRules.has(item.id)).length ?? 0), 0),
  };
  if (evidenceDirectory) {
    await writeFile(
      resolve(evidenceDirectory, 'accessibility-report.json'),
      `${JSON.stringify(report, null, 2)}\n`,
      'utf8',
    );
  }

  if (failures.length > 0) throw new Error(`Accessibility qualification failures:\n${failures.join('\n')}`);
  console.log(`PASS accessibility browser: ${report.summary.pages_scanned} route/viewport scans; JavaScript on; reduced motion; HTTP/title/main/h1/status/skip-link/overflow/runtime gates; zero axe violations; zero incomplete findings.`);
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
