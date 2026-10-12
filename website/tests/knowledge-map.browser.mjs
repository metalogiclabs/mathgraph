// Read-only local browser qualification. Generated evidence belongs outside Git.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, extname, sep } from 'node:path';
import { createServer as createViteServer } from 'vite';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const vite = await createViteServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' });
const { readKnowledgeMap } = await vite.ssrLoadModule('/src/lib/knowledge-map.ts');
const { validatePublicRecordSchema } = await vite.ssrLoadModule('/src/lib/catalog.ts');
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
  const errors = [];
  for (const width of [1440, 768, 390]) {
    for (const javaScriptEnabled of [false, true]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, javaScriptEnabled, reducedMotion: 'reduce' });
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      assert.equal((await page.goto(`${origin}/objects/`, { waitUntil: 'networkidle' })).status(), 200);
      const map = page.locator('[data-knowledge-map]');
      const base = JSON.parse(await map.locator('[data-map-data]').textContent());
      assert.equal(base.nodes.length, 14);
      assert.equal(base.edges.length, 7);
      const claim = base.nodes.find(node => node.source_id === 'jpl.l4yaml.finite_parser_acceptance');
      const receipt = base.nodes.find(node => node.source_id === 'mathgraph.l4yaml.48-case-qualification');
      const semanticNode = id => map.locator(`[data-map-node] [data-map-select="${id}"]`);
      const selectedDetail = id => map.locator(`[data-object-detail="${id}"]`);
      const noOverflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `overflow at ${width}, JS=${javaScriptEnabled}`);
      await noOverflow();
      assert.equal(await map.locator('[data-map-kind]').first().isEnabled(), javaScriptEnabled);
      assert.equal(await map.locator('[data-object-detail]:visible').count(), javaScriptEnabled ? 1 : 14);
      if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/objects-${width}-${javaScriptEnabled ? 'js' : 'nojs'}.png` });
      if (javaScriptEnabled) {
        const receiptFragment = await semanticNode(receipt.id).getAttribute('href');
        const claimFragment = await semanticNode(claim.id).getAttribute('href');
        await page.goto('about:blank');
        await page.goto(`${origin}/objects/${receiptFragment}`, { waitUntil: 'networkidle' });
        assert.equal(await semanticNode(receipt.id).getAttribute('aria-current'), 'true', 'Direct object fragment must select its matching detail');
        assert.equal(await selectedDetail(receipt.id).isVisible(), true);
        await page.reload({ waitUntil: 'networkidle' });
        assert.equal(await semanticNode(receipt.id).getAttribute('aria-current'), 'true', 'Reload must retain fragment selection');
        assert.equal(await selectedDetail(receipt.id).isVisible(), true);
        await semanticNode(claim.id).click();
        await page.waitForURL(`${origin}/objects/${claimFragment}`);
        await page.goBack();
        await page.waitForFunction(id => document.querySelector(`[data-object-detail="${id}"]`)?.hidden === false, receipt.id, { timeout: 3000 });
        assert.equal(new URL(page.url()).hash, receiptFragment);
        assert.equal(await semanticNode(receipt.id).getAttribute('aria-current'), 'true');
        await page.goForward();
        await page.waitForFunction(id => document.querySelector(`[data-object-detail="${id}"]`)?.hidden === false, claim.id, { timeout: 3000 });
        assert.equal(new URL(page.url()).hash, claimFragment);
        assert.equal(await semanticNode(claim.id).getAttribute('aria-current'), 'true');
        await page.goto(`${origin}/objects/#main-content`);
        assert.equal(await semanticNode(claim.id).getAttribute('aria-current'), 'true', 'Unrelated fragment must not reset map selection');
        assert.equal(await selectedDetail(claim.id).isVisible(), true);
        assert.equal(new URL(page.url()).hash, '#main-content', 'Keep native unrelated fragment navigation');
        await semanticNode(receipt.id).focus();
        await page.keyboard.press('Enter');
        assert.equal(await semanticNode(receipt.id).getAttribute('aria-current'), 'true');
        assert.equal(await selectedDetail(receipt.id).isVisible(), true);
        assert.match(await map.locator('[data-map-selection]').innerText(), /mathgraph\.l4yaml\.48-case-qualification/);
        await map.getByRole('button', { name: 'Follow outgoing arrows' }).click();
        assert.equal(await map.locator('[data-map-traversal-results] li').count(), 1);
        assert.equal(await map.locator('[data-map-traversal-results]').innerText(), claim.id);
        await map.locator('[data-map-traversal-results] a').click();
        assert.equal(await selectedDetail(claim.id).isVisible(), true);
        await map.getByRole('button', { name: 'Follow incoming arrows' }).click();
        assert.equal(await map.locator('[data-map-traversal-results]').innerText(), receipt.id);
        const svgNode = map.locator(`[data-map-svg-node="${receipt.id}"]`);
        await svgNode.focus();
        await page.keyboard.press('Enter');
        assert.equal(await svgNode.getAttribute('aria-current'), 'true');
        assert.equal(await selectedDetail(receipt.id).isVisible(), true);
        await svgNode.focus();
        await page.keyboard.press('Tab');
        assert.equal(await svgNode.evaluate(element => element === document.activeElement), false, 'Native Tab must leave the selected node');
        await semanticNode(claim.id).click();
        await map.locator('[data-map-kind][value=RESOLVE_RECEIPT]').uncheck();
        assert.equal(await map.locator('[data-map-node]:visible').count(), 10);
        assert.equal(await map.locator('[data-map-svg-edge]:visible').count(), 0);
        assert.equal(await map.locator('[data-map-edge]:visible').count(), 0);
        assert.equal(await selectedDetail(claim.id).getByText('No declared incoming relations in this displayed projection.', { exact: true }).isVisible(), true);
        await map.getByRole('button', { name: 'Follow incoming arrows' }).click();
        assert.equal(await map.locator('[data-map-traversal-results] li').count(), 0);
        const [download] = await Promise.all([page.waitForEvent('download'), map.locator('[data-map-export]').click()]);
        const exported = readKnowledgeMap(await readFile(await download.path(), 'utf8')).projection;
        assert.equal(exported.authority, 'NONE');
        assert.equal(exported.kind, 'PRESENTATION_PROJECTION');
        assert.equal(exported.nodes.length, 10);
        assert.equal(exported.edges.length, 0);
        assert.deepEqual(exported.source_pins, base.source_pins);
        assert.equal(exported.extensions.at(-1).payload.selected_id, claim.id);
        assert.equal(exported.completeness.omitted_nodes, 4);
        assert.equal(exported.completeness.omitted_edges, 7);
        assert.equal(exported.completeness.truncated, true);
        assert.throws(() => validatePublicRecordSchema(exported), /PUBLIC_RECORD_SCHEMA_INVALID/);
        await map.locator('[data-map-kind][value=RESOLVE_RECEIPT]').check();
        const [fullDownload] = await Promise.all([page.waitForEvent('download'), map.locator('[data-map-export]').click()]);
        const fullExport = readKnowledgeMap(await readFile(await fullDownload.path(), 'utf8')).projection;
        assert.deepEqual(fullExport.edges, base.edges, 'Export must preserve every exact directed occurrence and provenance');
        await map.locator('[data-map-limit]').fill('2');
        await map.locator('[data-map-limit]').press('Tab');
        assert.match(await map.locator('[data-map-count]').innerText(), /2 of 14 objects.*omitted: 12 objects.*truncated: true/);
        assert.equal(await map.locator('[data-map-node]:visible').count(), 2);
        if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/objects-${width}-bounded.png` });
        for (const input of await map.locator('[data-map-kind]').all()) await input.uncheck();
        assert.equal(await map.locator('[data-map-node]:visible').count(), 0);
        assert.equal(await map.locator('[data-object-detail]:visible').count(), 0);
        assert.equal(await map.getByRole('button', { name: 'Follow incoming arrows' }).isDisabled(), true);
        for (const input of await map.locator('[data-map-kind]').all()) await input.check();
        await map.locator('[data-map-limit]').fill('14');
        await map.locator('[data-map-limit]').press('Tab');
        await semanticNode(claim.id).click();
        if (process.env.BROWSER_EVIDENCE_DIR) {
          await map.locator('.map-visual').screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/objects-${width}-diagram.png` });
          await selectedDetail(claim.id).screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/objects-${width}-detail.png` });
        }
        await noOverflow();
      } else {
        const [download] = await Promise.all([page.waitForEvent('download'), map.locator('[data-map-export]').click()]);
        assert.deepEqual(readKnowledgeMap(await readFile(await download.path(), 'utf8')).projection.edges, base.edges);
        await semanticNode(claim.id).click();
        assert.equal(await selectedDetail(claim.id).isVisible(), true);
      }
      for (const object of base.nodes) {
        const permanent = selectedDetail(object.id).getByRole('link', { name: 'Permanent object view', includeHidden: true });
        const response = await page.request.get(`${origin}${await permanent.getAttribute('href')}`);
        assert.equal(response.status(), 200);
        assert.ok((await response.text()).includes(object.id));
      }
      await page.goto(origin, { waitUntil: 'networkidle' });
      const home = page.locator('[data-source-neighborhood]');
      const homeProjection = JSON.parse(await home.locator('[data-neighborhood-data]').textContent());
      assert.equal(homeProjection.nodes.length, 3);
      assert.equal(homeProjection.relations.length, 3);
      assert.equal(await home.locator('[data-neighborhood-node]').count(), 3);
      assert.equal(await home.locator('[data-neighborhood-edge]').count(), 3);
      if (javaScriptEnabled) {
        const target = homeProjection.nodes.find(node => node.id !== homeProjection.center_id);
        const targetControl = home.locator(`[data-neighborhood-node="${target.id}"] [data-neighborhood-select]`).first();
        await targetControl.focus();
        await page.keyboard.press('Enter');
        assert.equal(await targetControl.getAttribute('aria-current'), 'true');
        assert.equal(await home.locator('[data-neighborhood-detail-id]').innerText(), target.id);
        await home.locator('[data-neighborhood-type][value=TYPE_REFERENCES]').uncheck();
        assert.equal(await home.locator('[data-neighborhood-edge]:visible').count(), 2);
        assert.equal(await home.locator('[data-neighborhood-visual] line[data-relation=TYPE_REFERENCES]').count(), 0);
      } else {
        assert.equal(await home.locator('[data-neighborhood-node]:visible').count(), 3);
        assert.equal(await home.locator('[data-neighborhood-edge]:visible').count(), 3);
      }
      await noOverflow();
      await page.close();
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS knowledge map browser: 1440/768/390; direct-fragment/reload and Back/Forward selection; unrelated fragments preserved; keyboard semantic/SVG selection; filters; directed display-only traversal; actual download + read-only reader + evidence rejection; limits/omissions; all 14 detail routes; JS/no-JS; reduced motion; homepage 3-object/3-relation source projection; zero overflow/console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
  await vite.close();
}
