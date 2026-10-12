// Read-only local browser qualification. Generated screenshots belong outside Git.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, resolve, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const { AxeBuilder } = await import('@axe-core/playwright');
const root = resolve('dist');
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const file = resolve(root, `.${pathname.endsWith('/') ? `${pathname}index.html` : pathname}`);
  if (!file.startsWith(`${root}${sep}`)) return response.writeHead(403).end();
  try {
    const bytes = await readFile(file);
    response.writeHead(200, { 'Content-Type': ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' })[extname(file)] ?? 'application/octet-stream' }).end(bytes);
  } catch { response.writeHead(404).end(); }
});
await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));

let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const errors = [];
  const lookup = await browser.newPage({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
  await lookup.goto(`${origin}/explore/`, { waitUntil: 'networkidle' });
  const routeFor = async title => {
    const link = lookup.locator('[data-catalogue-entry-title]').filter({ hasText: title }).filter({ has: lookup.locator(`text="${title}"`) }).first();
    const exact = lookup.locator('[data-catalogue-entry-title]').and(lookup.getByText(title, { exact: true })).first();
    return await exact.getAttribute('href') ?? await link.getAttribute('href');
  };
  const routes = Object.fromEntries(await Promise.all(['Real.rpow', 'neg_involutive', 'Function.Involutive', 'Set.exists_mem_empty', 'Mathlib.Data.Int.Basic']
    .map(async title => [title, await routeFor(title)])));
  await lookup.close();
  for (const [title, route] of Object.entries(routes)) {
    assert.match(route, /^\/objects\/object-[a-f0-9]{64}\/$/);
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: true, reducedMotion: 'reduce' });
    page.on('pageerror', error => errors.push(`${title}: ${error.message}`));
    page.on('console', message => { if (message.type() === 'error') errors.push(`${title}: ${message.text()}`); });
    assert.equal((await page.goto(`${origin}${route}`, { waitUntil: 'networkidle' })).status(), 200);
    assert.equal(await page.locator('h1').innerText(), title);
    assert.match(await page.locator('[data-source-occurrence-detail]').innerText(), /SOURCE_INDEXED/);
    assert.match(await page.locator('[data-source-occurrence-detail]').innerText(), /NOT_CHECKED/);
    assert.match(await page.locator('[data-source-occurrence-detail]').innerText(), /PINNED_HISTORICAL_SOURCE/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${title} overflows desktop`);
    await page.close();
  }
  for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }, { width: 390, height: 844 }]) {
    for (const javaScriptEnabled of [false, true]) {
      const context = await browser.newContext({ viewport, javaScriptEnabled, reducedMotion: 'reduce' });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(`${viewport.width}px: ${error.message}`));
      page.on('console', message => { if (message.type() === 'error') errors.push(`${viewport.width}px: ${message.text()}`); });
      assert.equal((await page.goto(`${origin}${routes['neg_involutive']}`, { waitUntil: 'networkidle' })).status(), 200);
      const network = page.locator('[data-source-neighborhood]');
      const projection = JSON.parse(await network.locator('[data-neighborhood-data]').textContent());
      assert.equal(projection.schema, 'mathgraph.website-source-neighborhood.v1');
      assert.equal(projection.authority, 'NONE');
      assert.equal(projection.status.independent_verification, 'NOT_CHECKED');
      assert.ok(projection.nodes.some(node => node.title === 'Function.Involutive'), 'Cross-module direct type reference must remain navigable');
      assert.ok(projection.relations.some(edge => edge.type === 'TYPE_REFERENCES'));
      assert.ok(projection.relations.every(edge => edge.logical_implication === false && edge.semantic_equivalence === false));
      assert.equal(await network.locator('[data-neighborhood-node]').count(), projection.nodes.length);
      assert.equal(await network.locator('[data-neighborhood-edge]').count(), projection.relations.length);
      assert.equal(await network.locator('[data-neighborhood-type]').first().isEnabled(), javaScriptEnabled);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${viewport.width}px source page overflow`);
      if (javaScriptEnabled) {
        assert.equal(await network.locator('[data-neighborhood-visual] svg').count(), 1);
        const neighbor = projection.nodes.find(node => node.id !== projection.center_id);
        const selection = network.locator(`[data-neighborhood-select="${neighbor.id}"]`).first();
        await selection.focus(); await page.keyboard.press('Enter');
        assert.equal(await network.locator('[data-neighborhood-detail-title]').innerText(), neighbor.title);
        assert.equal(await selection.getAttribute('aria-current'), 'true');
        const permanent = network.locator(`[data-neighborhood-node="${neighbor.id}"] [data-neighborhood-permanent]`);
        assert.equal((await page.request.get(`${origin}${new URL(await permanent.getAttribute('href'), origin).pathname}`)).status(), 200);
        const centre = network.locator(`[data-neighborhood-select="${projection.center_id}"]`).first();
        await centre.click();
        const direction = projection.relations.some(edge => edge.from === projection.center_id) ? 'outgoing' : 'incoming';
        await network.getByRole('button', { name: `Follow ${direction} arrows` }).click();
        assert.ok(await network.locator('[data-neighborhood-traversal-results] li').count() >= 1);
        const [download] = await Promise.all([page.waitForEvent('download'), network.locator('[data-neighborhood-export]').click()]);
        const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
        assert.equal(exported.authority, 'NONE');
        assert.equal(exported.semantics, 'READ_ONLY_SOURCE_STRUCTURE');
        assert.equal(exported.center_id, projection.center_id);
        assert.deepEqual(exported.relations, projection.relations);
        const firstType = network.locator('[data-neighborhood-type]').first();
        await firstType.uncheck();
        assert.ok(await network.locator('[data-neighborhood-edge]:visible').count() < projection.relations.length);
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
        assert.deepEqual(axe.violations, [], `${viewport.width}px accessibility violations: ${axe.violations.map(item => item.id).join(', ')}`);
      } else {
        assert.match(await network.locator('noscript').innerText(), /All bounded objects and declared relations/);
        assert.equal(await network.locator('[data-neighborhood-node]:visible').count(), projection.nodes.length);
      }
      if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/source-object-${viewport.width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: false });
      await context.close();
    }
  }
  const modulePage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await modulePage.goto(`${origin}${routes['Mathlib.Data.Int.Basic']}`, { waitUntil: 'networkidle' });
  assert.match(await modulePage.locator('[data-source-neighborhood]').innerText(), /IMPORTS_MODULE/);
  await modulePage.close();
  assert.deepEqual(errors, []);
  console.log('PASS source objects browser: four source modules/declarations; permanent direct routes; cross-module TYPE_REFERENCES; IMPORTS_MODULE; exact status boundary; keyboard selection; traversal; compact export; JS/no-JS; 1440/768/390px; reduced motion; WCAG A/AA scan; no overflow or console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
