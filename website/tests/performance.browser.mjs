// Read-only browser performance qualification. Generated evidence belongs outside Git.
import assert from 'node:assert/strict';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, resolve, sep } from 'node:path';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright');
const root = resolve('dist');
const budgets = Object.freeze({
  searchNormalP95Ms: 50,
  searchFourTimesP95Ms: 100,
  searchReadyFourTimesMs: 2000,
  searchFirstUseFourTimesMs: 250,
  searchClearFourTimesMs: 250,
  graphInitialFourTimesMs: 500,
  graphInteractionFourTimesP95Ms: 200,
});
const queryCases = Object.freeze([
  { kind: 'exact-name', query: 'Real.rpow', expectedTitle: 'Real.rpow' },
  { kind: 'token', query: 'Real add natCast', expectedTitle: "Real.rpow_add_natCast'" },
  { kind: 'no-result', query: 'mathgraph-no-result-query-7c60fc86', expectedTitle: null },
]);
const searchRounds = 20;
const interactionRounds = 24;

function percentile95(values) {
  assert(values.length > 0, 'Cannot calculate p95 of an empty sample');
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.ceil(ordered.length * 0.95) - 1];
}

function summary(values) {
  return {
    count: values.length,
    min_ms: Math.min(...values),
    p95_ms: percentile95(values),
    max_ms: Math.max(...values),
  };
}

function contentType(pathname) {
  return ({
    '.css': 'text/css',
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
  })[extname(pathname)] ?? 'application/octet-stream';
}

const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const file = resolve(root, `.${pathname.endsWith('/') ? `${pathname}index.html` : pathname}`);
  if (!file.startsWith(`${root}${sep}`)) return response.writeHead(403).end();
  try {
    const bytes = await readFile(file);
    response.writeHead(200, { 'Content-Type': contentType(file) }).end(bytes);
  } catch {
    response.writeHead(404).end();
  }
});

async function maximumBoundedNeighborhood() {
  const objectsRoot = join(root, 'objects');
  const candidates = [];
  for (const entry of await readdir(objectsRoot, { withFileTypes: true })) {
    if (!entry.isDirectory() || !/^object-[a-f0-9]{64}$/u.test(entry.name)) continue;
    const html = await readFile(join(objectsRoot, entry.name, 'index.html'), 'utf8');
    const match = html.match(/<script type="application\/json" data-neighborhood-data>(.*?)<\/script>/su);
    if (!match) continue;
    const projection = JSON.parse(match[1]);
    candidates.push({
      route: `/objects/${entry.name}/`,
      center_id: projection.center_id,
      title: projection.nodes.find(node => node.id === projection.center_id)?.title ?? null,
      nodes: projection.nodes.length,
      relations: projection.relations.length,
      max_nodes: projection.context.max_nodes,
      max_relations: projection.context.max_edges,
    });
  }
  candidates.sort((left, right) => right.nodes - left.nodes
    || right.relations - left.relations
    || (left.route < right.route ? -1 : left.route > right.route ? 1 : 0));
  assert(candidates.length > 0, 'Built site has no bounded source-neighborhood projections');
  const selected = candidates[0];
  assert.equal(selected.nodes, selected.max_nodes, 'Largest source neighborhood must exercise the node cap');
  assert.equal(selected.relations, selected.max_relations, 'Largest source neighborhood must exercise the relation cap');
  return selected;
}

async function applyCpuThrottle(page, rate) {
  const session = await page.context().newCDPSession(page);
  await session.send('Emulation.setCPUThrottlingRate', { rate });
  return session;
}

async function benchmarkSearch(browser, origin, cpuRate) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const session = await applyCpuThrottle(page, cpuRate);
  try {
    const navigationStarted = performance.now();
    const response = await page.goto(`${origin}/explore/`, { waitUntil: 'domcontentloaded' });
    assert.equal(response.status(), 200);
    await page.waitForFunction(() => {
      const root = document.querySelector('[data-knowledge-catalogue]');
      const query = root?.querySelector('[data-catalogue-query]');
      const filter = root?.querySelector('[data-catalogue-filter]');
      const mounted = root?.querySelectorAll('[data-catalogue-item]').length ?? 0;
      return filter?.getAttribute('data-catalogue-ready') === 'true'
        && query instanceof HTMLInputElement
        && !query.disabled
        && mounted > 0
        && mounted <= 50;
    });
    const readyElapsedMs = performance.now() - navigationStarted;
    const readiness = await page.locator('[data-knowledge-catalogue]').evaluate(rootElement => ({
      index_state: rootElement.dataset.catalogueSearchIndexState ?? 'READY',
      ready: rootElement.querySelector('[data-catalogue-filter]')?.getAttribute('data-catalogue-ready'),
      declared_total: Number(rootElement.querySelector('[data-catalogue-filter]')?.getAttribute('data-catalogue-total')),
      declared_source_total: Number(rootElement.querySelector('[data-catalogue-filter]')?.getAttribute('data-catalogue-search-index-count')),
      item_count: rootElement.querySelectorAll('[data-catalogue-item]').length,
    }));
    assert.equal(readiness.index_state, 'READY');
    assert.equal(readiness.ready, 'true');
    assert.equal(readiness.declared_total, 2372);
    assert.equal(readiness.declared_source_total, 2345);
    assert(readiness.item_count > 0 && readiness.item_count <= 50, 'JavaScript search must begin with a bounded mounted result window');

    const measureSettledInput = value => page.locator('[data-knowledge-catalogue]').evaluate(async (rootElement, nextValue) => {
      const query = rootElement.querySelector('[data-catalogue-query]');
      if (!(query instanceof HTMLInputElement)) throw new Error('MISSING_CATALOGUE_QUERY');
      query.value = nextValue;
      const started = performance.now();
      query.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise(resolveFrame => requestAnimationFrame(() => requestAnimationFrame(resolveFrame)));
      const first = rootElement.querySelector('[data-catalogue-item]:not([hidden]) [data-catalogue-entry-title]');
      return {
        elapsed: performance.now() - started,
        first_title: first?.textContent?.trim() ?? null,
        visible_count: rootElement.querySelectorAll('[data-catalogue-item]:not([hidden])').length,
      };
    }, value);

    // Measure the first transition from the bounded unfiltered window, then
    // restoring that window. Static/no-JavaScript qualification separately
    // proves that all declared entries remain present in the published HTML.
    const firstUse = await measureSettledInput(queryCases[0].query);
    assert.equal(firstUse.first_title, queryCases[0].expectedTitle, 'First-use exact-name ranking changed');
    const clearReset = await measureSettledInput('');
    assert.equal(clearReset.visible_count, readiness.item_count, 'Clear must restore the bounded initial result window');

    // Populate JIT and style caches before recording the fixed workload.
    for (const testCase of queryCases) {
      await page.locator('[data-catalogue-query]').fill(testCase.query);
      const firstTitle = await page.locator('[data-catalogue-item]:visible [data-catalogue-entry-title]').first().textContent().catch(() => null);
      assert.equal(firstTitle?.trim() ?? null, testCase.expectedTitle);
    }

    const samples = Object.fromEntries(queryCases.map(testCase => [testCase.kind, []]));
    for (let round = 0; round < searchRounds; round += 1) {
      for (const testCase of queryCases) {
        const measured = await measureSettledInput(testCase.query);
        assert.equal(measured.first_title, testCase.expectedTitle, `${testCase.kind} ranking changed during performance workload`);
        if (testCase.expectedTitle === null) assert.equal(measured.visible_count, 0, 'No-result query must stay empty');
        else assert(measured.visible_count > 0, `${testCase.kind} query must retain a result`);
        samples[testCase.kind].push(measured.elapsed);
      }
    }
    assert.deepEqual(errors, []);
    const all = Object.values(samples).flat();
    return {
      cpu_rate: cpuRate,
      ready_elapsed_ms: readyElapsedMs,
      rounds_per_kind: searchRounds,
      workload: queryCases.map(({ kind, query }) => ({ kind, query })),
      first_use: { query: queryCases[0].query, ...firstUse },
      clear_reset: clearReset,
      by_kind: Object.fromEntries(Object.entries(samples).map(([kind, values]) => [kind, { ...summary(values), samples_ms: values }])),
      combined: { ...summary(all), samples_ms: all },
    };
  } finally {
    await session.detach();
    await context.close();
  }
}

async function benchmarkGraph(browser, origin, fixture) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const session = await applyCpuThrottle(page, 4);
  try {
    const response = await page.goto(`${origin}${fixture.route}`, { waitUntil: 'domcontentloaded' });
    assert.equal(response.status(), 200);
    await page.waitForFunction(() => {
      const root = document.querySelector('[data-source-neighborhood]');
      const controls = root?.querySelector('[data-neighborhood-controls]');
      return controls instanceof HTMLFieldSetElement
        && !controls.disabled
        && root.querySelector('[data-neighborhood-visual] svg') !== null;
    });
    const initialInteractiveMs = await page.evaluate(() => performance.now());
    const projection = await page.locator('[data-neighborhood-data]').evaluate(element => JSON.parse(element.textContent));
    assert.equal(projection.center_id, fixture.center_id);
    assert.equal(projection.nodes.length, fixture.nodes);
    assert.equal(projection.relations.length, fixture.relations);

    const interaction = await page.locator('[data-source-neighborhood]').evaluate((rootElement, rounds) => {
      const projection = JSON.parse(rootElement.querySelector('[data-neighborhood-data]').textContent);
      const selectionIds = projection.nodes.map(node => node.id).filter(id => id !== projection.center_id);
      if (selectionIds.length === 0) throw new Error('NO_NEIGHBOR_SELECTION_TARGET');
      const selectionSamples = [];
      const traversalSamples = [];
      for (let index = 0; index < rounds; index += 1) {
        const id = selectionIds[index % selectionIds.length];
        const selection = Array.from(rootElement.querySelectorAll('[data-neighborhood-select]'))
          .find(element => element.dataset.neighborhoodSelect === id);
        if (!(selection instanceof HTMLElement)) throw new Error('MISSING_NEIGHBOR_SELECTION_TARGET');
        let started = performance.now();
        selection.click();
        selectionSamples.push(performance.now() - started);
        if (rootElement.querySelector('[data-neighborhood-detail-id]')?.textContent !== id) throw new Error('NEIGHBOR_SELECTION_DID_NOT_RENDER');

        const direction = index % 2 === 0 ? 'incoming' : 'outgoing';
        const traversal = rootElement.querySelector(`[data-neighborhood-traverse="${direction}"]`);
        if (!(traversal instanceof HTMLButtonElement) || traversal.disabled) throw new Error('MISSING_NEIGHBOR_TRAVERSAL');
        started = performance.now();
        traversal.click();
        traversalSamples.push(performance.now() - started);
        if (!rootElement.querySelector('[data-neighborhood-traversal-status]')?.textContent?.includes(`Display-only ${direction} traversal`)) {
          throw new Error('NEIGHBOR_TRAVERSAL_DID_NOT_RENDER');
        }
      }
      return { selectionSamples, traversalSamples };
    }, interactionRounds);
    assert.deepEqual(errors, []);
    return {
      cpu_rate: 4,
      route: fixture.route,
      center_id: fixture.center_id,
      title: fixture.title,
      displayed_nodes: fixture.nodes,
      displayed_relations: fixture.relations,
      initial_interactive_ms: initialInteractiveMs,
      selection: { ...summary(interaction.selectionSamples), samples_ms: interaction.selectionSamples },
      traversal: { ...summary(interaction.traversalSamples), samples_ms: interaction.traversalSamples },
    };
  } finally {
    await session.detach();
    await context.close();
  }
}

await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));
let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const graphFixture = await maximumBoundedNeighborhood();
  const results = {
    schema: 'mathgraph.website-performance-qualification.v1',
    browser: { name: 'chromium', version: browser.version() },
    budgets,
    search: {
      normal: await benchmarkSearch(browser, origin, 1),
      four_times_cpu: await benchmarkSearch(browser, origin, 4),
    },
    graph: await benchmarkGraph(browser, origin, graphFixture),
  };
  const compact = {
    schema: results.schema,
    search_normal_p95_ms: results.search.normal.combined.p95_ms,
    search_four_times_p95_ms: results.search.four_times_cpu.combined.p95_ms,
    search_ready_four_times_ms: results.search.four_times_cpu.ready_elapsed_ms,
    search_first_use_four_times_ms: results.search.four_times_cpu.first_use.elapsed,
    search_clear_four_times_ms: results.search.four_times_cpu.clear_reset.elapsed,
    search_four_times_by_kind_p95_ms: Object.fromEntries(Object.entries(results.search.four_times_cpu.by_kind).map(([kind, value]) => [kind, value.p95_ms])),
    graph_route: results.graph.route,
    graph_center_id: results.graph.center_id,
    graph_initial_four_times_ms: results.graph.initial_interactive_ms,
    graph_selection_four_times_p95_ms: results.graph.selection.p95_ms,
    graph_traversal_four_times_p95_ms: results.graph.traversal.p95_ms,
  };
  console.log(`PERFORMANCE_BROWSER_RESULTS ${JSON.stringify(compact)}`);
  if (process.env.BROWSER_EVIDENCE_DIR) {
    const evidenceRoot = resolve(process.env.BROWSER_EVIDENCE_DIR);
    await mkdir(evidenceRoot, { recursive: true });
    await writeFile(join(evidenceRoot, 'performance-browser.json'), `${JSON.stringify(results, null, 2)}\n`, 'utf8');
  }

  const failures = [];
  if (results.search.normal.combined.p95_ms >= budgets.searchNormalP95Ms) failures.push(`normal combined search p95 ${results.search.normal.combined.p95_ms.toFixed(2)}ms >= ${budgets.searchNormalP95Ms}ms`);
  if (results.search.four_times_cpu.combined.p95_ms >= budgets.searchFourTimesP95Ms) failures.push(`4x combined search p95 ${results.search.four_times_cpu.combined.p95_ms.toFixed(2)}ms >= ${budgets.searchFourTimesP95Ms}ms`);
  if (results.search.four_times_cpu.ready_elapsed_ms >= budgets.searchReadyFourTimesMs) failures.push(`4x navigation-to-search-ready ${results.search.four_times_cpu.ready_elapsed_ms.toFixed(2)}ms >= ${budgets.searchReadyFourTimesMs}ms`);
  if (results.search.four_times_cpu.first_use.elapsed >= budgets.searchFirstUseFourTimesMs) failures.push(`4x first-use search ${results.search.four_times_cpu.first_use.elapsed.toFixed(2)}ms >= ${budgets.searchFirstUseFourTimesMs}ms`);
  if (results.search.four_times_cpu.clear_reset.elapsed >= budgets.searchClearFourTimesMs) failures.push(`4x clear/reset ${results.search.four_times_cpu.clear_reset.elapsed.toFixed(2)}ms >= ${budgets.searchClearFourTimesMs}ms`);
  for (const [kind, value] of Object.entries(results.search.normal.by_kind)) {
    if (value.p95_ms >= budgets.searchNormalP95Ms) failures.push(`normal ${kind} search p95 ${value.p95_ms.toFixed(2)}ms >= ${budgets.searchNormalP95Ms}ms`);
  }
  for (const [kind, value] of Object.entries(results.search.four_times_cpu.by_kind)) {
    if (value.p95_ms >= budgets.searchFourTimesP95Ms) failures.push(`4x ${kind} search p95 ${value.p95_ms.toFixed(2)}ms >= ${budgets.searchFourTimesP95Ms}ms`);
  }
  if (results.graph.initial_interactive_ms >= budgets.graphInitialFourTimesMs) failures.push(`4x graph initial interactive ${results.graph.initial_interactive_ms.toFixed(2)}ms >= ${budgets.graphInitialFourTimesMs}ms`);
  if (results.graph.selection.p95_ms >= budgets.graphInteractionFourTimesP95Ms) failures.push(`4x graph selection p95 ${results.graph.selection.p95_ms.toFixed(2)}ms >= ${budgets.graphInteractionFourTimesP95Ms}ms`);
  if (results.graph.traversal.p95_ms >= budgets.graphInteractionFourTimesP95Ms) failures.push(`4x graph traversal p95 ${results.graph.traversal.p95_ms.toFixed(2)}ms >= ${budgets.graphInteractionFourTimesP95Ms}ms`);
  assert.deepEqual(failures, [], `Performance budgets failed:\n${failures.join('\n')}`);
  console.log('PASS browser performance: search controls ready <2000ms at 4x CPU; settled exact/token/no-result search p95 <50ms normal and <100ms at 4x CPU; first-use and clear/reset <250ms at 4x CPU; maximum bounded source-neighborhood interactive <500ms and selection/traversal p95 <200ms at 4x CPU.');
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
