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
    for (const width of [390, 901, 1024]) {
      for (const javaScriptEnabled of [false, true]) {
        const page = await browser.newPage({ viewport: { width, height: 844 }, javaScriptEnabled, reducedMotion: 'reduce' });
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
        const overflow = await page.evaluate(() => ({
          fits: document.documentElement.scrollWidth <= window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          catalogueAncestors: (() => {
            const start = document.querySelector('[data-catalogue-filter]');
            const result = [];
            for (let element = start; element && result.length < 5; element = element.parentElement) {
              const box = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              result.push({ tag: element.tagName, className: element.className, left: box.left, right: box.right, width: box.width, minWidth: style.minWidth, contain: style.contain, containerType: style.containerType, gridTemplateColumns: style.gridTemplateColumns });
            }
            return result;
          })(),
          offenders: Array.from(document.querySelectorAll('*')).map((element) => {
            const box = element.getBoundingClientRect();
            return { tag: element.tagName, className: element.className, left: box.left, right: box.right, width: box.width };
          }).filter((box) => box.right > window.innerWidth + 0.5 || box.left < -0.5).slice(0, 8),
        }));
        assert.equal(overflow.fits, true, `${route}: page overflow at ${width}px: ${JSON.stringify(overflow)}`);
        const [catalogueBox, controlsBox] = await Promise.all([
          catalogue.boundingBox(),
          catalogue.locator('[data-catalogue-controls]').boundingBox(),
        ]);
        assert(catalogueBox && controlsBox);
        assert(
          controlsBox.x + controlsBox.width <= catalogueBox.x + catalogueBox.width + 0.5,
          `${route} controls overflow their catalogue at ${width}px`,
        );
        const nestedControls = catalogue.locator('[data-catalogue-controls] label, [data-catalogue-controls] input, [data-catalogue-controls] select, [data-catalogue-controls] button');
        for (let index = 0; index < await nestedControls.count(); index += 1) {
          const nested = nestedControls.nth(index);
          const box = await nested.boundingBox();
          assert(box, `${route}: missing nested control box ${index} at ${width}px`);
          assert(
            box.x >= controlsBox.x - 0.5
              && box.y >= controlsBox.y - 0.5
              && box.x + box.width <= controlsBox.x + controlsBox.width + 0.5
              && box.y + box.height <= controlsBox.y + controlsBox.height + 0.5,
            `${route}: ${await nested.evaluate((element) => element.tagName)} ${index} escapes its fieldset at ${width}px: fieldset=${JSON.stringify(controlsBox)} nested=${JSON.stringify(box)}`,
          );
        }
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
        if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/${route}-catalogue-${width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: true });
        await page.close();
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS catalogue browser: records/capabilities; keyboard search; source-derived select; clear/reset; no-match; JS/no-JS complete fallback; 390/901/1024px; reduced motion; zero container/page overflow or console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
