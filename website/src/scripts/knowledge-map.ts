import type { KnowledgeMapProjection } from '../lib/knowledge-map';
import type { ObjectKind } from '../lib/object-projections';

export function displayProjection(map: KnowledgeMapProjection, kinds: ObjectKind[], maxNodes: number, selectedId: string | null): KnowledgeMapProjection {
  const nodes = map.nodes.filter(node => kinds.includes(node.kind)).slice(0, maxNodes);
  const ids = new Set(nodes.map(node => node.id));
  const edges = map.edges.filter(edge => ids.has(edge.from) && ids.has(edge.to));
  const omittedNodes = map.completeness.total_nodes - nodes.length;
  const omittedEdges = map.completeness.total_edges - edges.length;
  return {
    ...map, nodes, edges,
    // Scope stays the original adapter selection; display state is an opaque,
    // non-critical extension, so filtering never erases pre-existing omissions.
    completeness: { ...map.completeness, omitted_nodes: omittedNodes, omitted_edges: omittedEdges, truncated: omittedNodes > 0 || omittedEdges > 0 },
    extensions: [...map.extensions, { id: 'mathgraph.website-display-context.v1', critical: false, payload: { selected_id: selectedId && ids.has(selectedId) ? selectedId : null, kinds, max_nodes: maxNodes, semantics: 'DISPLAY_ONLY', counts_scope: 'ORIGINAL_SELECTED_ADAPTER_OUTPUT' } }],
  };
}

export function traceDisplayed(map: KnowledgeMapProjection, selectedId: string, direction: 'incoming' | 'outgoing'): string[] {
  if (!map.nodes.some(node => node.id === selectedId)) return [];
  const visited = new Set([selectedId]);
  const pending = [selectedId];
  for (let index = 0; index < pending.length; index++) {
    for (const edge of map.edges) {
      const from = direction === 'outgoing' ? edge.from : edge.to;
      const to = direction === 'outgoing' ? edge.to : edge.from;
      if (from === pending[index] && !visited.has(to)) { visited.add(to); pending.push(to); }
    }
  }
  return map.nodes.filter(node => node.id !== selectedId && visited.has(node.id)).map(node => node.id);
}

function initializeMap(root: HTMLElement) {
  const map = JSON.parse(root.querySelector('[data-map-data]')!.textContent!) as KnowledgeMapProjection;
  const kindInputs = Array.from(root.querySelectorAll<HTMLInputElement>('[data-map-kind]'));
  const limit = root.querySelector<HTMLInputElement>('[data-map-limit]')!;
  const articles = Array.from(root.querySelectorAll<HTMLElement>('[data-object-detail]'));
  const controls = Array.from(root.querySelectorAll<HTMLAnchorElement | SVGAElement>('[data-map-select]'));
  const traversalStatus = root.querySelector<HTMLElement>('[data-map-traversal-status]')!;
  const traversalResults = root.querySelector<HTMLElement>('[data-map-traversal-results]')!;
  const fragmentObject = () => articles.find(article => `#${article.id}` === window.location.hash)?.dataset.objectDetail;
  let selected: string | null = fragmentObject() ?? null;
  let displayed = map;
  const detail = (id: string) => articles.find(article => article.dataset.objectDetail === id);
  function render() {
    const kinds = kindInputs.filter(input => input.checked).map(input => input.value as ObjectKind);
    const maxNodes = Number.isSafeInteger(limit.valueAsNumber) ? Math.max(0, Math.min(map.nodes.length, limit.valueAsNumber)) : map.nodes.length;
    displayed = displayProjection(map, kinds, maxNodes, selected);
    if (!displayed.nodes.some(node => node.id === selected)) selected = displayed.nodes[0]?.id ?? null;
    displayed = displayProjection(map, kinds, maxNodes, selected);
    const nodeIds = new Set(displayed.nodes.map(node => node.id));
    const edgeIds = new Set(displayed.edges.map(edge => edge.id));
    root.querySelectorAll<HTMLElement>('[data-map-node]').forEach(node => node.hidden = !nodeIds.has(node.dataset.mapNode!));
    root.querySelectorAll<SVGElement>('[data-map-svg-node]').forEach(node => node.toggleAttribute('hidden', !nodeIds.has(node.dataset.mapSvgNode!)));
    root.querySelectorAll<SVGElement>('[data-map-svg-edge]').forEach(edge => edge.toggleAttribute('hidden', !edgeIds.has(edge.dataset.mapSvgEdge!)));
    root.querySelectorAll<HTMLElement>('[data-relation-id]').forEach(edge => edge.hidden = !edgeIds.has(edge.dataset.relationId!));
    root.querySelectorAll<HTMLElement>('[data-relation-group]').forEach(group => {
      const hasEdges = Array.from(group.querySelectorAll<HTMLElement>('[data-relation-id]')).some(edge => !edge.hidden);
      group.querySelector<HTMLElement>('[data-empty-relations]')!.hidden = hasEdges;
      group.querySelector<HTMLElement>('ol')!.hidden = !hasEdges;
    });
    for (const control of controls) {
      if (control.dataset.mapSelect === selected) control.setAttribute('aria-current', 'true');
      else control.removeAttribute('aria-current');
    }
    for (const article of articles) article.hidden = article.dataset.objectDetail !== selected;
    const c = displayed.completeness;
    root.querySelector('[data-map-count]')!.textContent = `${displayed.nodes.length} of ${c.total_nodes} objects · ${displayed.edges.length} of ${c.total_edges} relations · omitted: ${c.omitted_nodes} objects, ${c.omitted_edges} relations · truncated: ${c.truncated}`;
    root.querySelector('[data-map-selection]')!.textContent = selected ? `Selected object: ${selected}` : 'No objects in this displayed projection.';
    root.querySelectorAll<HTMLButtonElement>('[data-map-traverse]').forEach(button => button.disabled = !selected);
    traversalStatus.textContent = 'No traversal requested.';
    traversalResults.replaceChildren();
    root.querySelector<HTMLAnchorElement>('[data-map-export]')!.href = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(displayed))}`;
  }
  root.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const anchor = event.target.closest('a');
    const article = anchor && articles.find(item => anchor.getAttribute('href') === `#${item.id}`);
    if (article && displayed.nodes.some(node => node.id === article.dataset.objectDetail)) {
      selected = article.dataset.objectDetail!;
      render();
    }
    const button = event.target.closest<HTMLButtonElement>('[data-map-traverse]');
    if (!button || !selected) return;
    const direction = button.dataset.mapTraverse as 'incoming' | 'outgoing';
    const ids = traceDisplayed(displayed, selected, direction);
    traversalStatus.textContent = `Display-only ${direction} traversal: ${ids.length} other objects reached using currently displayed declared arrows. No verification performed.`;
    traversalResults.replaceChildren(...ids.map(id => {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#${detail(id)!.id}`;
      link.textContent = id;
      li.append(link);
      return li;
    }));
  });
  for (const input of [...kindInputs, limit]) input.addEventListener('change', render);
  window.addEventListener('hashchange', () => {
    const id = fragmentObject();
    // Only this component's exact generated detail fragments affect selection.
    // Keep native anchors/history and the current display filters unchanged.
    if (id && id !== selected && displayed.nodes.some(node => node.id === id)) {
      selected = id;
      render();
    }
  });
  root.querySelector<HTMLFieldSetElement>('[data-map-controls]')!.disabled = false;
  render();
}

if (typeof document !== 'undefined') document.querySelectorAll<HTMLElement>('[data-knowledge-map]').forEach(initializeMap);
