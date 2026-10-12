// Read-only local browser qualification. Generated screenshots belong outside Git.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, resolve, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const root = resolve('dist');
const waitForCatalogueReady = page => page.waitForFunction(() => {
  const rootElement = document.querySelector('[data-knowledge-catalogue] [data-catalogue-filter]');
  const query = rootElement?.querySelector('[data-catalogue-query]');
  const mounted = rootElement?.querySelectorAll('[data-catalogue-item]').length ?? 0;
  return rootElement?.getAttribute('data-catalogue-ready') === 'true'
    && query instanceof HTMLInputElement
    && !query.disabled
    && mounted > 0
    && mounted <= 50;
});
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
  for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }, { width: 390, height: 844 }]) {
    for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ viewport, javaScriptEnabled, reducedMotion: 'reduce' });
      page.on('pageerror', error => errors.push(`${viewport.width}px: ${error.message}`));
      page.on('console', message => { if (message.type() === 'error') errors.push(`${viewport.width}px: ${message.text()}`); });
      const response = await page.goto(`${origin}/explore/?q=Real.rpow`, { waitUntil: 'networkidle' });
      assert.equal(response.status(), 200);
      const catalogue = page.locator('[data-knowledge-catalogue]');
      const items = catalogue.locator('[data-catalogue-item]');
      const visibleItems = () => catalogue.locator('[data-catalogue-item]:visible');
      const layout = () => page.evaluate(() => ({
        fits: document.documentElement.scrollWidth <= window.innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        offenders: Array.from(document.querySelectorAll('*')).map(element => {
          const box = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return { tag: element.tagName, className: element.className, text: element.textContent?.slice(0, 120), left: box.left, right: box.right, width: box.width, display: style.display, overflowWrap: style.overflowWrap, wordBreak: style.wordBreak, parentClass: element.parentElement?.className };
        }).filter(box => box.right > window.innerWidth + .5 || box.left < -.5).slice(0, 8),
      }));
      if (!javaScriptEnabled) {
        assert.equal(await catalogue.locator('[data-catalogue-query]').isEnabled(), false);
        assert.equal(await items.count(), 2372, 'Complete semantic catalogue must be present without JavaScript');
        assert.equal(await visibleItems().count(), 2372, 'No-JavaScript fallback must expose every entry');
        assert.match(await catalogue.locator('noscript').textContent(), /every entry remains available without JavaScript/i);
      } else {
        await catalogue.locator('[data-catalogue-query]').waitFor({ state: 'visible' });
        await waitForCatalogueReady(page);
        assert.equal(await catalogue.locator('[data-catalogue-filter]').getAttribute('data-catalogue-ready'), 'true');
        assert.equal(await catalogue.locator('[data-catalogue-query]').isEnabled(), true);
        assert.equal(await catalogue.locator('[data-catalogue-filter]').getAttribute('data-catalogue-total'), '2372');
        assert.ok(await items.count() > 0 && await items.count() <= 50, 'JavaScript view must mount a bounded result window');
        const query = catalogue.locator('[data-catalogue-query]');
        assert.equal(await query.inputValue(), 'Real.rpow');
        assert.equal(await visibleItems().first().locator('h3').innerText(), 'Real.rpow');
        await query.fill('Real add natCast');
        assert.match(await visibleItems().first().locator('h3').innerText(), /Real\.rpow_add_natCast/);
        await query.fill('rpow');
        assert.equal(await visibleItems().first().locator('h3').innerText(), 'Real.rpow');
        await query.fill('EmptyCollection emptyCollection False');
        assert.equal(await visibleItems().first().locator('h3').innerText(), 'Set.exists_mem_empty', 'Statement text must be searchable from the pinned static index');
        await query.fill('rpow');
        const moduleFilter = catalogue.locator('[data-catalogue-field="module"]');
        const statusFilter = catalogue.locator('[data-catalogue-field="status"]');
        await moduleFilter.selectOption('Mathlib.Analysis.SpecialFunctions.Pow.Real');
        await statusFilter.selectOption('SOURCE_INDEXED');
        assert.ok(await visibleItems().count() > 1);
        for (let index = 0; index < Math.min(5, await visibleItems().count()); index += 1) {
          assert.equal(await visibleItems().nth(index).getAttribute('data-catalogue-module'), 'Mathlib.Analysis.SpecialFunctions.Pow.Real');
          assert.equal(await visibleItems().nth(index).getAttribute('data-catalogue-status'), 'SOURCE_INDEXED');
        }
        await catalogue.locator('[data-catalogue-clear]').click();
        assert.equal(await query.inputValue(), '');
        assert.equal(await query.evaluate(element => element === document.activeElement), true, 'Clear must return focus to search');
        assert.equal(await visibleItems().count(), 50);
        assert.match(await catalogue.locator('[data-catalogue-count]').innerText(), /50 shown · 2,372 matches · 2,372 catalogue entries/i);
        const more = catalogue.locator('[data-catalogue-more]');
        assert.equal(await more.isVisible(), true);
        await more.focus();
        await page.keyboard.press('Enter');
        assert.equal(await visibleItems().count(), 100, 'Show more must expand the same deterministic result set');
        assert.match(await catalogue.locator('[data-catalogue-count]').innerText(), /100 shown · 2,372 matches · 2,372 catalogue entries/i);
        const geometry = await layout();
        assert.equal(geometry.fits, true, `${viewport.width}px Explore page overflow: ${JSON.stringify(geometry)}`);

        await query.fill('mg-l4yaml-source-check-20261010');
        const evidenceLink = visibleItems().first().locator('h3 a');
        assert.match(await evidenceLink.getAttribute('href'), /^\/objects\/object-[a-f0-9]{64}\/$/);
        assert.equal((await page.goto(`${origin}${await evidenceLink.getAttribute('href')}`, { waitUntil: 'networkidle' })).status(), 200, 'Existing permanent evidence-object link must resolve');
      }
      if (!javaScriptEnabled) {
        const geometry = await layout();
        assert.equal(geometry.fits, true, `${viewport.width}px Explore page overflow: ${JSON.stringify(geometry)}`);
      }
      if (process.env.BROWSER_EVIDENCE_DIR) {
        await page.goto(`${origin}/explore/?q=Real.rpow`, { waitUntil: 'networkidle' });
        if (javaScriptEnabled) await waitForCatalogueReady(page);
        await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/explore-${viewport.width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: false });
      }
      await page.close();
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS Explore browser: 2,372 semantic entries; exact/final/token ranking; exact filters; permanent evidence navigation; clear/focus; JS/no-JS; 1440/768/390px; reduced motion; no overflow or console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
