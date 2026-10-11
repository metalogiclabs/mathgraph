// Run with a local Playwright installation or PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, extname, sep } from 'node:path';
import { spawnSync } from 'node:child_process';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const root = resolve('dist');
const fixture = JSON.parse(await readFile('tests/fixtures/import-workflow.json', 'utf8'));
const raw = await readFile(`public/evidence/${fixture.id}/record.json`);
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
  for (const route of ['verify', 'check']) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${origin}/${route}/`, { waitUntil: 'networkidle' });
    const workbench = page.locator('[data-import-workbench]');
    assert.equal(await workbench.count(), 1, `${route}: shared workbench missing`);
    const documentedCommand = await workbench.locator('pre code').textContent();
    const [, ...documentedArgs] = documentedCommand.replaceAll('\\\n', ' ').trim().split(/\s+/);
    const replay = spawnSync(process.env.PYTHON ?? 'python3', documentedArgs, { cwd: resolve('..'), encoding: 'utf8' });
    assert.equal(replay.status, 0, `documented local import command failed: ${replay.stderr}`);
    assert.equal(JSON.parse(replay.stdout).schema, 'mathgraph.import-result.v1');
    const requests = [];
    page.on('request', request => requests.push(request.url()));
    const input = workbench.locator('input[type=file]');
    assert.equal(await input.isEnabled(), true);
    assert.match(await workbench.locator('[data-import-status]').innerText(), /UNKNOWN/);
    await input.setInputFiles({ name: 'record.json', mimeType: 'application/json', buffer: raw });
    await page.waitForFunction(() => document.querySelector('[data-import-workbench]')?.getAttribute('data-stage') === 'import');
    const inspectContext = async () => {
      const context = await workbench.locator('[data-import-context]').innerText();
      for (const value of [fixture.id, fixture.source.commit, fixture.source.external_suite_commit,
        fixture.evidence.receipt_id, fixture.evidence.archive_sha256, '48', '31', '17', '52', 'statement_fidelity', 'UNKNOWN']) {
        assert.ok(context.includes(value), `${route}: context lost ${value}`);
      }
    };
    await inspectContext();
    for (const stage of ['interpret', 'check', 'resolve', 'explore', 'export']) {
      await workbench.locator(`[data-import-step=${stage}]`).focus();
      await page.keyboard.press('Enter');
      assert.equal(await workbench.getAttribute('data-stage'), stage);
      await inspectContext();
    }
    const downloadEvent = page.waitForEvent('download');
    await workbench.getByRole('link', { name: 'Download presentation JSON' }).click();
    const downloaded = await downloadEvent;
    const exported = JSON.parse(await readFile(await downloaded.path(), 'utf8'));
    assert.equal(exported.schema, 'mathgraph.browser-recognition.v1');
    assert.equal(exported.authority, 'NONE');
    assert.equal(exported.record.id, fixture.id);
    assert.deepEqual(exported.record.unknowns, fixture.unknowns);
    assert.equal(exported.handoff.historical_result, 'WARRANTED_BOUNDED');
    assert.equal(exported.freshness, 'UNKNOWN');
    assert.equal(exported.current_applicability, 'UNKNOWN');
    for (const axis of ['proof_replay', 'kernel_replay', 'source_suite_replay']) assert.equal(exported[axis], 'NOT_PERFORMED');
    const imported = spawnSync(process.env.PYTHON ?? 'python3', ['-c', [
      'import pathlib,sys',
      'from conformance.import_v1.consumer import import_record,ImportError',
      'policy=pathlib.Path("conformance/import_v1/fixtures/trust-policy.json").read_bytes()',
      'try:',
      ' import_record(sys.stdin.buffer.read(),policy,"944231afaf9d89e6f7dc77d9efbe80dcbd3fc76f8e8f260b32637a0f261faf65")',
      'except ImportError as error:',
      ' print(error.reason_code);sys.exit(1)',
    ].join('\n')], { cwd: resolve('..'), input: JSON.stringify(exported), encoding: 'utf8' });
    assert.equal(imported.status, 1, imported.stderr);
    assert.equal(imported.stdout.trim(), 'UNEXPECTED_FIELD');
    await workbench.locator('[data-import-goal]').selectOption('whole_language_correctness');
    await workbench.locator('[data-import-step=resolve]').click();
    assert.match(await workbench.locator('[data-import-stage-output]').innerText(), /UNKNOWN.*UNSUPPORTED_ROUTE/);
    assert.doesNotMatch(await workbench.locator('[data-import-stage-output]').innerText(), /WARRANTED/);
    await inspectContext();
    for (const buffer of [Buffer.concat([raw, Buffer.from('\n')]), Buffer.from('{"producer_verdict":"WARRANTED_BOUNDED"}'), Buffer.alloc(65537)]) {
      await input.setInputFiles({ name: 'changed.json', mimeType: 'application/json', buffer });
      await page.waitForFunction(() => document.querySelector('[data-import-workbench]')?.getAttribute('data-stage') === 'unknown');
      assert.equal(await workbench.locator('[data-import-context]').isVisible(), false);
      assert.equal(await workbench.getByRole('link', { name: 'Download presentation JSON' }).count(), 0);
      assert.doesNotMatch(await workbench.innerText(), /WARRANTED/);
    }
    assert.deepEqual(requests, [], 'local interaction made a network request');
    assert.deepEqual(errors, []);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'mobile overflow');
    await page.close();
  }
  const noJS = await browser.newPage({ javaScriptEnabled: false });
  await noJS.goto(`${origin}/verify/`);
  assert.equal(await noJS.locator('input[type=file]').isDisabled(), true);
  assert.match(await noJS.locator('noscript').innerText(), /UNKNOWN/);
  assert.ok(await noJS.getByRole('link', { name: 'Download the exact supported record.json' }).getAttribute('href'));
  console.log('PASS import browser workflow: both routes, keyboard, mobile, no-JS, no network, mutation reset, unsupported handoff, portable export, Python rejection');
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
