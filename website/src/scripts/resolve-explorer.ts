type JsonObject = Record<string, unknown>;
type Route = { conclusion: string; premises: string[]; evidence: string[] };
type Resolution = { before: string; after: string; changed: boolean };
type Graph = {
  claims: Array<{ id: string; kind: string; scope: string }>;
  receipts: Array<{ id: string; kind: string; scope: string }>;
  routes: Route[];
};
type Scenario = {
  id: string;
  label: string;
  basis: string;
  description: string;
  states: Record<string, string>;
  resolutions: Record<string, Resolution>;
  withdrawn_evidence: string[];
  active_routes: Route[];
  graph?: Graph;
};
type ScenarioGroup = { scenarios: Scenario[]; graph?: Graph; default_scenario?: string };
type Artifact = {
  schema: string;
  record_id: string;
  snapshot_sha256: string;
  transport_sha256: string;
  PUBLISHED_RECORD: ScenarioGroup;
  SYNTHETIC_CONFORMANCE: ScenarioGroup;
};

const statusValues = new Set(['SOURCE_DOCUMENTED', 'STALE', 'UNKNOWN', 'WARRANTED_BOUNDED', 'REFUTED']);

function object(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function route(value: unknown): value is Route {
  return object(value) && typeof value.conclusion === 'string' && stringArray(value.premises) && stringArray(value.evidence);
}

function graph(value: unknown): value is Graph {
  return object(value) && Array.isArray(value.claims) && value.claims.every((claim) => object(claim) && typeof claim.id === 'string' && typeof claim.kind === 'string' && typeof claim.scope === 'string') &&
    Array.isArray(value.receipts) && value.receipts.every((receipt) => object(receipt) && typeof receipt.id === 'string' && typeof receipt.kind === 'string' && typeof receipt.scope === 'string') &&
    Array.isArray(value.routes) && value.routes.every(route);
}

function stringStatusRecord(value: unknown): value is Record<string, string> {
  return object(value) && Object.values(value).every((status) => typeof status === 'string' && statusValues.has(status));
}

function resolutionRecord(value: unknown): value is Record<string, Resolution> {
  return object(value) && Object.values(value).every((item) => object(item) && typeof item.before === 'string' && statusValues.has(item.before) && typeof item.after === 'string' && statusValues.has(item.after) && typeof item.changed === 'boolean');
}

function scenario(value: unknown): value is Scenario {
  return object(value) && typeof value.id === 'string' && typeof value.label === 'string' && typeof value.basis === 'string' && typeof value.description === 'string' &&
    stringStatusRecord(value.states) && resolutionRecord(value.resolutions) && stringArray(value.withdrawn_evidence) &&
    Array.isArray(value.active_routes) && value.active_routes.every(route) && (value.graph === undefined || graph(value.graph));
}

function group(value: unknown, needsGraph: boolean): value is ScenarioGroup {
  return object(value) && Array.isArray(value.scenarios) && value.scenarios.every(scenario) && (!needsGraph || graph(value.graph));
}

function artifact(value: unknown, root: HTMLElement): value is Artifact {
  return object(value) && value.schema === 'mathgraph.resolve-scenarios.v1' && value.record_id === root.dataset.recordId &&
    value.snapshot_sha256 === root.dataset.snapshotSha256 && value.transport_sha256 === root.dataset.recordTransportSha256 &&
    group(value.PUBLISHED_RECORD, true) && group(value.SYNTHETIC_CONFORMANCE, false) &&
    value.PUBLISHED_RECORD.default_scenario === root.dataset.defaultScenario;
}

function hexadecimal(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

function routeKey(value: Route): string {
  return JSON.stringify([value.conclusion, value.premises, value.evidence]);
}

function element<K extends keyof HTMLElementTagNameMap>(name: K, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(name);
  if (text !== undefined) node.textContent = text;
  return node;
}

function statusNode(value: string): HTMLSpanElement {
  const node = element('span', value);
  node.className = 'resolve-status';
  node.dataset.status = value.toLowerCase().replaceAll('_', '-');
  return node;
}

function clear(node: Element): void {
  while (node.firstChild) node.firstChild.remove();
}

function appendCode(parent: Element, value: string): void {
  parent.append(element('code', value));
}

function renderTable(root: HTMLElement, selected: Scenario): void {
  const body = root.querySelector('[data-resolve-results]');
  if (!body) throw new Error('RESOLVE_RESULTS_TARGET_MISSING');
  clear(body);
  for (const [claimId, resolution] of Object.entries(selected.resolutions)) {
    const row = element('tr');
    const claim = element('th');
    claim.scope = 'row';
    appendCode(claim, claimId);
    row.append(claim);
    for (const value of [resolution.before, resolution.after, selected.states[claimId]]) {
      const cell = element('td');
      cell.append(statusNode(value));
      row.append(cell);
    }
    body.append(row);
  }
}

function renderGraph(root: HTMLElement, selected: Scenario, selectedGraph: Graph): void {
  const receipts = root.querySelector('[data-resolve-receipts]');
  const routes = root.querySelector('[data-resolve-routes]');
  const claims = root.querySelector('[data-resolve-claims]');
  if (!receipts || !routes || !claims) throw new Error('RESOLVE_GRAPH_TARGET_MISSING');
  clear(receipts);
  clear(routes);
  clear(claims);
  const withdrawn = new Set(selected.withdrawn_evidence);
  const active = new Set(selected.active_routes.map(routeKey));
  const routeConclusions = new Set(selectedGraph.routes.map((item) => item.conclusion));
  const claimKinds = new Map(selectedGraph.claims.map((item) => [item.id, item.kind]));

  for (const receipt of selectedGraph.receipts) {
    const item = element('li');
    appendCode(item, receipt.id);
    item.append(statusNode(withdrawn.has(receipt.id) ? 'WITHDRAWN / STALE' : 'AVAILABLE'));
    item.append(element('small', `${receipt.kind} · ${receipt.scope}`));
    receipts.append(item);
  }
  for (const qualifiedRoute of selectedGraph.routes) {
    const item = element('li');
    const relationship = element('span');
    qualifiedRoute.evidence.forEach((id) => appendCode(relationship, id));
    if (qualifiedRoute.premises.length > 0) {
      relationship.append(document.createTextNode(' + '));
      qualifiedRoute.premises.forEach((id) => appendCode(relationship, id));
    }
    relationship.append(document.createTextNode(' → '));
    appendCode(relationship, qualifiedRoute.conclusion);
    item.append(relationship, element('small', active.has(routeKey(qualifiedRoute)) ? 'ACTIVE IN THIS VIEW' : 'INACTIVE IN THIS VIEW'));
    routes.append(item);
  }
  for (const [claimId, state] of Object.entries(selected.states)) {
    const item = element('li');
    appendCode(item, claimId);
    item.append(statusNode(state));
    const noRoute = !routeConclusions.has(claimId) && claimKinds.get(claimId) === 'formal';
    item.append(element('small', noRoute ? 'No qualified support route in this scenario' : 'Typed claim declared in this precomputed scenario'));
    claims.append(item);
  }
}

function render(root: HTMLElement, classification: string, selected: Scenario, selectedGraph: Graph): void {
  const heading = root.querySelector('[data-resolve-heading]');
  const basis = root.querySelector('[data-resolve-basis]');
  const description = root.querySelector('[data-resolve-description]');
  const classificationNode = root.querySelector('[data-resolve-classification]');
  const live = root.querySelector('[data-resolve-live]');
  if (!heading || !basis || !description || !classificationNode || !live) throw new Error('RESOLVE_VIEW_TARGET_MISSING');
  heading.textContent = selected.label;
  basis.textContent = selected.basis;
  description.textContent = selected.description;
  classificationNode.textContent = classification === 'SYNTHETIC_CONFORMANCE'
    ? 'Synthetic conformance simulation'
    : selected.basis === 'PUBLISHED_AFTER' ? 'Qualified historic snapshot' : 'Modeled / hypothetical view';
  renderTable(root, selected);
  renderGraph(root, selected, selectedGraph);
  live.textContent = `Showing ${selected.label}.`;
}

function findScenario(data: Artifact, classification: string, id: string): { selected: Scenario; selectedGraph: Graph } | undefined {
  const selectedGroup = classification === 'PUBLISHED_RECORD' ? data.PUBLISHED_RECORD : classification === 'SYNTHETIC_CONFORMANCE' ? data.SYNTHETIC_CONFORMANCE : undefined;
  const selected = selectedGroup?.scenarios.find((candidate) => candidate.id === id);
  const selectedGraph = selected?.graph ?? selectedGroup?.graph;
  return selected && selectedGraph ? { selected, selectedGraph } : undefined;
}

function failClosed(root: HTMLElement, controls: HTMLInputElement[], data?: Artifact): void {
  for (const control of controls) control.disabled = true;
  const defaultControl = controls.find((control) => control.dataset.scenarioClassification === root.dataset.defaultClassification && control.value === root.dataset.defaultScenario);
  if (defaultControl) defaultControl.checked = true;
  if (data && root.dataset.defaultClassification && root.dataset.defaultScenario) {
    const fallback = findScenario(data, root.dataset.defaultClassification, root.dataset.defaultScenario);
    if (fallback) render(root, root.dataset.defaultClassification, fallback.selected, fallback.selectedGraph);
  }
  const error = root.querySelector<HTMLElement>('[data-resolve-error]');
  if (error) error.hidden = false;
}

async function initialise(root: HTMLElement): Promise<void> {
  const controls = [...root.querySelectorAll<HTMLInputElement>('input[type="radio"][data-scenario-classification]')];
  try {
    const url = root.dataset.scenariosUrl;
    const expectedDigest = root.dataset.scenariosSha256;
    if (!url || !expectedDigest || new URL(url, window.location.href).origin !== window.location.origin) throw new Error('RESOLVE_SCENARIO_ORIGIN_INVALID');
    const response = await fetch(url, { credentials: 'same-origin', cache: 'force-cache' });
    if (!response.ok) throw new Error('RESOLVE_SCENARIO_FETCH_FAILED');
    const bytes = await response.arrayBuffer();
    const digest = hexadecimal(await crypto.subtle.digest('SHA-256', bytes));
    if (digest !== expectedDigest) throw new Error('RESOLVE_SCENARIO_DIGEST_INVALID');
    const parsed: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    if (!artifact(parsed, root)) throw new Error('RESOLVE_SCENARIO_IDENTITY_INVALID');

    if (controls.length === 0) throw new Error('RESOLVE_SCENARIO_CONTROLS_MISSING');
    for (const control of controls) {
      const classification = control.dataset.scenarioClassification;
      if (!classification || !findScenario(parsed, classification, control.value)) throw new Error('RESOLVE_SCENARIO_CONTROL_UNKNOWN');
    }
    for (const control of controls) {
      control.disabled = false;
      control.addEventListener('change', () => {
        if (!control.checked) return;
        try {
          const classification = control.dataset.scenarioClassification;
          const found = classification ? findScenario(parsed, classification, control.value) : undefined;
          if (!classification || !found) throw new Error('RESOLVE_SCENARIO_SELECTION_UNKNOWN');
          render(root, classification, found.selected, found.selectedGraph);
        } catch {
          failClosed(root, controls, parsed);
        }
      });
    }
  } catch {
    failClosed(root, controls);
  }
}

for (const explorer of document.querySelectorAll<HTMLElement>('[data-resolve-explorer]')) {
  void initialise(explorer);
}
