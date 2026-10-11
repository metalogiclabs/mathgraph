// Read-only local browser qualification. Generated evidence belongs outside Git.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, extname, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
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
  for (const route of ['records', 'capabilities']) {
    for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ viewport: { width: 390, height: 844 }, javaScriptEnabled, reducedMotion: 'reduce' });
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      assert.equal((await page.goto(`${origin}/${route}/`, { waitUntil: 'networkidle' })).status(), 200);
      const catalogue = page.locator('[data-catalogue-filter]');
      const items = catalogue.locator('[data-catalogue-item]');
      const visibleItems = () => catalogue.locator('[data-catalogue-item]:visible');
      assert.equal(await items.count(), 2);
      assert.equal(await visibleItems().count(), 2, 'Every committed entry must be visible without filtering');
      assert.equal(await catalogue.locator('[data-catalogue-query]').isEnabled(), javaScriptEnabled);
      assert.equal(await catalogue.locator('[data-catalogue-clear]').isEnabled(), javaScriptEnabled);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
      if (javaScriptEnabled) {
        const query = catalogue.locator('[data-catalogue-query]');
        await query.focus();
        await page.keyboard.type(route === 'records' ? 'resolve' : 'vdn');
        assert.equal(await visibleItems().count(), 1);
        assert.match(await catalogue.locator('[data-catalogue-count]').innerText(), /1 of 2 displayed/i);
        await query.fill('definitely-no-static-entry');
        assert.equal(await visibleItems().count(), 0);
        assert.equal(await catalogue.locator('[data-catalogue-no-match]').isVisible(), true);
        assert.match(await catalogue.locator('[data-catalogue-no-match]').innerText(), /current static catalogue has no matching displayed entries/i);
        await catalogue.locator('[data-catalogue-clear]').focus();
        await page.keyboard.press('Enter');
        assert.equal(await visibleItems().count(), 2);
        assert.equal(await query.inputValue(), '');
        const select = catalogue.locator('[data-catalogue-select]').first();
        await select.selectOption(route === 'records' ? 'SOURCE_CHECK' : 'QUALIFIED_BOUNDED');
        assert.equal(await visibleItems().count(), 1, `${route}: source-derived exact filter token must retain one entry`);
        await catalogue.locator('[data-catalogue-clear]').click();
        assert.equal(await visibleItems().count(), 2);
      }
      if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/${route}-catalogue-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: true });
      await page.close();
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS catalogue browser: records/capabilities; keyboard search; source-derived select; clear/reset; no-match; JS/no-JS complete fallback; 390px; reduced motion; zero overflow/console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
