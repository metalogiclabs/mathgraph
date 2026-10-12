// Read-only Resolve browser qualification. Immutable artifacts are compared with origin/main.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, resolve, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const { AxeBuilder } = await import('@axe-core/playwright');
const root = resolve('dist');
const immutable = [
  ['src/data/resolve-record.json', '0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87'],
  ['src/data/resolve-scenarios.json', 'ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181'],
];
for (const [path, digest] of immutable) {
  const bytes = await readFile(path);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), digest, `${path}: immutable digest changed`);
  assert.deepEqual(bytes, execFileSync('git', ['show', `origin/main:website/${path}`], { cwd: resolve('..') }), `${path}: differs from origin/main`);
  const publicName = path.endsWith('resolve-record.json') ? 'record.json' : 'scenarios.json';
  assert.deepEqual(bytes, await readFile(`public/evidence/mg-living-warrant-openai-jpl-20261010/${publicName}`), `${path}: public copy differs`);
}

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

const ids = {
  history: 'published-after',
  modeled: 'modeled-before',
  counterfactual: 'withdraw-openai.original_publication_receipt.1',
  withdrawJpl: 'withdraw-mathgraph.l4yaml.48-case-qualification',
  withdrawReceipt2: 'withdraw-openai.original_publication_receipt.2',
  support: 'openai.original_support.1',
  proposition: 'openai.theorem.1',
  jpl: 'jpl.l4yaml.finite_parser_acceptance',
};
const jplScope = 'nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases';

async function assertCompactOutcome(page, scenario, supportAfter) {
  const panel = page.locator('[data-resolve-comparison]');
  assert.equal(await panel.getAttribute('data-selected-scenario'), scenario);
  const support = panel.locator(`[data-resolve-outcome="${ids.support}"]`);
  const proposition = panel.locator(`[data-resolve-outcome="${ids.proposition}"]`);
  const jpl = panel.locator(`[data-resolve-outcome="${ids.jpl}"]`);
  assert.match(await support.innerText(), new RegExp(`SOURCE_DOCUMENTED[\\s\\S]*${supportAfter}`));
  if (scenario === ids.modeled) {
    assert.match(await support.innerText(), /Unchanged · documentary support[\s\S]*The documentary support path remains SOURCE_DOCUMENTED/i);
    assert.doesNotMatch(await support.innerText(), /becomes stale/i);
  } else {
    assert.match(await support.innerText(), /Changed · documentary support[\s\S]*The documentary support path changes from SOURCE_DOCUMENTED to STALE/i);
  }
  assert.match(await proposition.innerText(), /UNKNOWN[\s\S]*UNKNOWN[\s\S]*not REFUTED/i);
  assert.doesNotMatch(await proposition.locator('.resolve-status').allInnerTexts().then(values => values.join(' ')), /REFUTED/);
  assert.match(await jpl.innerText(), new RegExp(`WARRANTED_BOUNDED[\\s\\S]*WARRANTED_BOUNDED[\\s\\S]*${jplScope.replaceAll('/', '\\/')}`));
}

let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const errors = [];
  for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }, { width: 390, height: 844 }, { width: 375, height: 812 }]) {
    const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(`${viewport.width}px: ${error.message}`));
    page.on('console', message => { if (message.type() === 'error') errors.push(`${viewport.width}px: ${message.text()}`); });
    assert.equal((await page.goto(`${origin}/resolve/`, { waitUntil: 'networkidle' })).status(), 200);
    const quick = page.locator('[data-resolve-select]');
    assert.equal(await quick.count(), 3);
    assert.equal(await page.locator('[data-resolve-select]:not(:disabled)').count(), 3);
    await assertCompactOutcome(page, ids.history, 'STALE');
    assert.equal(await page.locator(`[data-resolve-select="${ids.history}"]`).getAttribute('aria-pressed'), 'true');

    const modeled = page.locator(`[data-resolve-select="${ids.modeled}"]`);
    await modeled.focus();
    await page.keyboard.press('Enter');
    await assertCompactOutcome(page, ids.modeled, 'SOURCE_DOCUMENTED');
    assert.equal(await page.locator(`input[value="${ids.modeled}"]`).isChecked(), true);

    const counterfactual = page.locator(`[data-resolve-select="${ids.counterfactual}"]`);
    await counterfactual.focus();
    await page.keyboard.press('Enter');
    await assertCompactOutcome(page, ids.counterfactual, 'STALE');
    assert.equal(await page.locator(`input[value="${ids.counterfactual}"]`).isChecked(), true);
    assert.match(await page.locator('[data-resolve-description]').innerText(), /Hypothetical single-dependency withdrawal/);
    for (const selector of ['[data-resolve-comparison] .resolve-comparison__selection', '[data-resolve-view]', '[data-resolve-view] .resolve-view__header']) {
      assert.equal(
        await page.locator(selector).evaluate(element => element.scrollWidth <= element.clientWidth),
        true,
        `${viewport.width}px ${selector} internal overflow`,
      );
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${viewport.width}px Resolve overflow`);

    await page.locator(`input[value="${ids.withdrawJpl}"]`).check();
    const panel = page.locator('[data-resolve-comparison]');
    assert.equal(await panel.getAttribute('data-selected-scenario'), ids.withdrawJpl);
    assert.match(await panel.locator(`[data-resolve-outcome="${ids.support}"]`).innerText(), /Unchanged · documentary support[\s\S]*remains SOURCE_DOCUMENTED/i);
    assert.match(await panel.locator(`[data-resolve-outcome="${ids.jpl}"]`).innerText(), /Changed · independently bounded observation[\s\S]*changes from WARRANTED_BOUNDED to STALE/i);
    assert.match(await panel.locator('[data-resolve-comparison-unchanged]').innerText(), /objects remain distinct[\s\S]*does not infer a relation[\s\S]*declared scope/i);

    await page.locator(`input[value="${ids.withdrawReceipt2}"]`).check();
    assert.match(await panel.locator(`[data-resolve-outcome="${ids.support}"]`).innerText(), /Unchanged · documentary support[\s\S]*remains SOURCE_DOCUMENTED/i);
    assert.doesNotMatch(await panel.locator(`[data-resolve-outcome="${ids.support}"]`).innerText(), /becomes stale/i);
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    assert.deepEqual(axe.violations, [], `${viewport.width}px accessibility violations: ${axe.violations.map(item => item.id).join(', ')}`);
    if (process.env.BROWSER_EVIDENCE_DIR) await page.screenshot({ path: `${process.env.BROWSER_EVIDENCE_DIR}/resolve-${viewport.width}.png`, fullPage: false });
    await context.close();
  }

  const noJS = await browser.newPage({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false });
  await noJS.goto(`${origin}/resolve/`);
  await assertCompactOutcome(noJS, ids.history, 'STALE');
  assert.equal(await noJS.locator('[data-resolve-select]:disabled').count(), 3);
  assert.match(await noJS.locator('noscript').innerText(), /qualified static default remains shown/i);
  await noJS.close();

  const tampered = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await tampered.route('**/evidence/**/scenarios.json', async route => {
    const response = await route.fetch();
    await route.fulfill({ response, body: Buffer.concat([await response.body(), Buffer.from('\n')]) });
  });
  await tampered.goto(`${origin}/resolve/`, { waitUntil: 'networkidle' });
  await assertCompactOutcome(tampered, ids.history, 'STALE');
  assert.equal(await tampered.locator('[data-resolve-select]:disabled').count(), 3);
  assert.equal(await tampered.locator('input[data-scenario-classification]:disabled').count(), await tampered.locator('input[data-scenario-classification]').count());
  assert.equal(await tampered.locator('[data-resolve-error]').isVisible(), true);
  assert.match(await tampered.locator('[data-resolve-heading]').innerText(), /Published after publisher withdrawal/);
  await tampered.close();

  assert.deepEqual(errors, []);
  console.log('PASS Resolve explorer: immutable parity; scenario-derived copy; selective changes; keyboard; fail-closed tamper; JS/no-JS; 1440/768/390/375px; WCAG A/AA; no overflow or console errors.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
