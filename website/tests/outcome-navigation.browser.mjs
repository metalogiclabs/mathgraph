// Run with PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE when not installed locally.
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
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE });
  const origin = `http://127.0.0.1:${server.address().port}`;
  for (const width of [1440, 768, 390]) {
    for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, javaScriptEnabled });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.goto(origin, { waitUntil: 'networkidle' });
      const nav = page.getByRole('navigation', { name: 'Primary', exact: true });
      const menu = page.getByRole('button', { name: 'Menu', exact: true, includeHidden: true });
      assert.equal(await menu.count(), 1, 'Menu button missing');
      assert.equal(await menu.isVisible(), javaScriptEnabled && width <= 900);
      assert.equal(await nav.isVisible(), !javaScriptEnabled || width > 900);
      assert.equal(await page.locator('h1').innerText(), 'Knowledge you can verify. Capabilities you can build on.');
      const noOverflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${width}px page overflow`);
      await noOverflow();
      if (javaScriptEnabled && width <= 900) {
        await menu.focus();
        await page.keyboard.press('Enter');
        assert.equal(await menu.getAttribute('aria-expanded'), 'true');
        assert.equal(await nav.isVisible(), true);
        await noOverflow();
        await page.keyboard.press('Tab');
        assert.equal(await nav.getByRole('link', { name: 'Explore', exact: true }).evaluate(el => el === document.activeElement), true);
        await page.keyboard.press('Escape');
        assert.equal(await menu.getAttribute('aria-expanded'), 'false');
        assert.equal(await menu.evaluate(el => el === document.activeElement), true);
        await menu.click();
        await menu.click();
        assert.equal(await nav.isVisible(), false);
        await menu.click();
        for (let index = 0; index < 6; index++) await page.keyboard.press('Tab');
        assert.equal(await menu.getAttribute('aria-expanded'), 'false', 'Tab must leave the menu without a focus trap');
        await menu.click();
        await page.locator('h1').click();
        assert.equal(await menu.getAttribute('aria-expanded'), 'false');
        await menu.click();
        await page.locator('[data-import-file]').focus();
        assert.equal(await menu.getAttribute('aria-expanded'), 'false');
        await menu.click();
        await page.setViewportSize({ width: 1440, height: 900 });
        await page.waitForFunction(() => document.querySelector('.nav-toggle')?.getAttribute('aria-expanded') === 'false');
        assert.equal(await nav.isVisible(), true);
        assert.equal(await menu.isVisible(), false);
        assert.equal(await menu.getAttribute('aria-expanded'), 'false');
        await page.setViewportSize({ width, height: 900 });
        await page.waitForFunction(() => !document.querySelector('#primary-navigation')?.checkVisibility());
        assert.equal(await nav.isVisible(), false);
        await menu.click();
        await nav.getByRole('link', { name: 'Explore', exact: true }).click();
        await page.waitForURL('**/explore/');
        assert.equal(await page.locator('#primary-navigation a[aria-current=page]').innerText(), 'Explore');
      }
      if (!javaScriptEnabled || width > 900) {
        for (const label of ['Explore', 'Verify', 'Build', 'Developers', 'GitHub ↗']) {
          assert.equal(await nav.getByRole('link', { name: label, exact: true }).isVisible(), true);
        }
      }
      if (process.env.BROWSER_EVIDENCE_DIR) {
        await page.goto(origin, { waitUntil: 'networkidle' });
        await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/home-${width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: true });
        await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/home-${width}-${javaScriptEnabled ? 'js' : 'nojs'}-viewport.png` });
      }
      assert.equal((await page.goto(`${origin}/contact/`, { waitUntil: 'networkidle' })).status(), 200);
      const contactGrid = page.locator('main .grid');
      const contactCards = contactGrid.locator(':scope > article.callout');
      assert.equal(await contactCards.count(), 2, 'Contact must expose both project channels');
      const [contactGridBox, repositoryCard, issuesCard] = await Promise.all([
        contactGrid.boundingBox(),
        contactCards.nth(0).boundingBox(),
        contactCards.nth(1).boundingBox(),
      ]);
      assert(contactGridBox && repositoryCard && issuesCard, `Contact geometry missing at ${width}px, JS=${javaScriptEnabled}`);
      if (width > 900) {
        assert.ok(repositoryCard.width >= contactGridBox.width * 0.45 && issuesCard.width >= contactGridBox.width * 0.45, `Contact cards collapsed below half-grid width at ${width}px, JS=${javaScriptEnabled}`);
        assert.ok(Math.abs(repositoryCard.y - issuesCard.y) <= 0.5, `Contact desktop cards must share a row at ${width}px, JS=${javaScriptEnabled}`);
      } else {
        assert.ok(repositoryCard.width >= contactGridBox.width * 0.99 && issuesCard.width >= contactGridBox.width * 0.99, `Contact cards must span the mobile/tablet grid at ${width}px, JS=${javaScriptEnabled}`);
        assert.ok(issuesCard.y >= repositoryCard.y + repositoryCard.height, `Contact cards overlap instead of stacking at ${width}px, JS=${javaScriptEnabled}`);
      }
      if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/contact-${width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`, fullPage: true });
      assert.deepEqual(errors, []);
      await page.close();
    }
  }
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const routeErrors = [];
  page.on('pageerror', error => routeErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') routeErrors.push(message.text()); });
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ['explore', 'verify', 'build', 'developers']) {
      const response = await page.goto(`${origin}/${route}/`, { waitUntil: 'networkidle' });
      assert.equal(response.status(), 200);
      assert.equal(await page.locator('#primary-navigation a[aria-current=page]').getAttribute('href'), `/${route}/`);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${route} at ${width}: overflow`);
      if (route === 'explore') {
        const columns = page.locator('.grid > div');
        const first = await columns.nth(0).boundingBox();
        const second = await columns.nth(1).boundingBox();
        const container = await page.locator('.grid').boundingBox();
        const minimumFraction = width <= 900 ? 0.99 : 0.35;
        assert.ok(first.width >= container.width * minimumFraction && second.width >= container.width * minimumFraction, `Explore columns must remain readable at ${width}px`);
        if (width <= 900) assert.ok(second.y >= first.y + first.height, 'Explore columns must stack on mobile');
      }
      if (process.env.BROWSER_EVIDENCE_DIR && ['explore', 'build'].includes(route)) {
        await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/${route}-${width}.png`, fullPage: true });
      }
    }
  }
  for (const [route, label] of [
    ['records', 'Explore'], ['discover', 'Explore'], ['records/mg-l4yaml-source-check-20261010/v1', 'Explore'],
    ['check', 'Verify'], ['resolve', 'Verify'], ['develop', 'Build'], ['capabilities', 'Build'],
    ['agents', 'Developers'], ['protocol', 'Developers'], ['protocol/profiles/lean', 'Developers'],
  ]) {
    const response = await page.goto(`${origin}/${route}/`, { waitUntil: 'networkidle' });
    assert.equal(response.status(), 200, `legacy route ${route} unavailable`);
    await page.getByRole('button', { name: 'Menu', exact: true }).click();
    assert.equal(await page.locator('#primary-navigation a[aria-current=location]').innerText(), label);
    assert.equal(await page.locator('#primary-navigation a[aria-current=page]').count(), 0);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${route}: overflow`);
  }
  assert.deepEqual(routeErrors, []);
  console.log('PASS outcome browser: 1440/768/390, JS/no-JS, Enter/Tab/Escape/focus return, outside pointer/focus, breakpoint reset, navigation, active child groups, legacy routes, zero overflow/console errors');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
