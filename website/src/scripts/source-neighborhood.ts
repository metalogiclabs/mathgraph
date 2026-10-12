import type { SourceNeighborhoodV1 } from '../lib/source-neighborhood';

const svgNs = 'http://www.w3.org/2000/svg';

function initializeNeighborhood(root: HTMLElement) {
  const projection = JSON.parse(root.querySelector('[data-neighborhood-data]')!.textContent!) as SourceNeighborhoodV1;
  const nodes = new Map(projection.nodes.map(node => [node.id, node]));
  const typeInputs = Array.from(root.querySelectorAll<HTMLInputElement>('[data-neighborhood-type]'));
  const nodeElements = Array.from(root.querySelectorAll<HTMLElement>('[data-neighborhood-node]'));
  const edgeElements = Array.from(root.querySelectorAll<HTMLElement>('[data-neighborhood-edge]'));
  let selected = projection.center_id;
  let displayedNodes = projection.nodes;
  let displayedRelations = projection.relations;

  function trace(direction: 'incoming' | 'outgoing') {
    const visited = new Set([selected]);
    const pending = [selected];
    for (let index = 0; index < pending.length; index += 1) {
      for (const edge of displayedRelations) {
        const from = direction === 'outgoing' ? edge.from : edge.to;
        const to = direction === 'outgoing' ? edge.to : edge.from;
        if (from === pending[index] && !visited.has(to)) { visited.add(to); pending.push(to); }
      }
    }
    return displayedNodes.filter(node => node.id !== selected && visited.has(node.id));
  }

  function draw() {
    const visual = root.querySelector<HTMLElement>('[data-neighborhood-visual]')!;
    visual.replaceChildren();
    const svg = document.createElementNS(svgNs, 'svg');
    svg.setAttribute('aria-hidden', 'true');
    const incoming = new Set(displayedRelations.filter(edge => edge.to === projection.center_id).map(edge => edge.from));
    const outgoing = new Set(displayedRelations.filter(edge => edge.from === projection.center_id).map(edge => edge.to));
    const laneCounts = [0, 0, 0];
    const positions = new Map<string, { x: number; y: number }>();
    for (const node of displayedNodes) {
      const lane = node.id === projection.center_id ? 1 : incoming.has(node.id) ? 0 : outgoing.has(node.id) ? 2 : 2;
      positions.set(node.id, { x: 20 + lane * 300, y: 45 + laneCounts[lane]++ * 70 });
    }
    svg.setAttribute('viewBox', `0 0 900 ${Math.max(190, Math.max(...laneCounts) * 70 + 65)}`);
    for (const edge of displayedRelations) {
      const from = positions.get(edge.from); const to = positions.get(edge.to);
      if (!from || !to) continue;
      const line = document.createElementNS(svgNs, 'line');
      line.setAttribute('x1', String(from.x + 240)); line.setAttribute('y1', String(from.y + 22));
      line.setAttribute('x2', String(to.x)); line.setAttribute('y2', String(to.y + 22));
      line.setAttribute('data-relation', edge.type); svg.append(line);
    }
    for (const node of displayedNodes) {
      const position = positions.get(node.id)!;
      const group = document.createElementNS(svgNs, 'g');
      if (node.id === selected) group.setAttribute('data-selected', 'true');
      const rect = document.createElementNS(svgNs, 'rect');
      rect.setAttribute('x', String(position.x)); rect.setAttribute('y', String(position.y));
      rect.setAttribute('width', '240'); rect.setAttribute('height', '45'); rect.setAttribute('rx', '4');
      const text = document.createElementNS(svgNs, 'text');
      text.setAttribute('x', String(position.x + 9)); text.setAttribute('y', String(position.y + 27));
      text.textContent = node.title.length > 30 ? `${node.title.slice(0, 28)}…` : node.title;
      group.append(rect, text); svg.append(group);
    }
    visual.append(svg);
  }

  function render() {
    const allowed = new Set(typeInputs.filter(input => input.checked).map(input => input.value));
    displayedRelations = projection.relations.filter(edge => allowed.has(edge.type));
    const visible = new Set([projection.center_id, ...displayedRelations.flatMap(edge => [edge.from, edge.to])]);
    displayedNodes = projection.nodes.filter(node => visible.has(node.id));
    if (!visible.has(selected)) selected = projection.center_id;
    for (const element of nodeElements) element.hidden = !visible.has(element.dataset.neighborhoodNode!);
    const edgeIds = new Set(displayedRelations.map(edge => edge.id));
    for (const element of edgeElements) element.hidden = !edgeIds.has(element.dataset.neighborhoodEdge!);
    root.querySelectorAll<HTMLElement>('[data-neighborhood-select]').forEach(control => {
      if (control.dataset.neighborhoodSelect === selected) control.setAttribute('aria-current', 'true');
      else control.removeAttribute('aria-current');
    });
    const node = nodes.get(selected)!;
    root.querySelector<HTMLElement>('[data-neighborhood-detail-kind]')!.textContent = node.kind;
    root.querySelector<HTMLElement>('[data-neighborhood-detail-title]')!.textContent = node.title;
    root.querySelector<HTMLElement>('[data-neighborhood-detail-id]')!.textContent = node.id;
    root.querySelector<HTMLAnchorElement>('[data-neighborhood-detail-link]')!.href = node.href;
    root.querySelector<HTMLElement>('[data-neighborhood-count]')!.textContent = `${displayedNodes.length} of ${projection.completeness.total_nodes} objects · ${displayedRelations.length} of ${projection.completeness.total_edges} relations · omitted: ${projection.completeness.total_nodes - displayedNodes.length} objects, ${projection.completeness.total_edges - displayedRelations.length} relations`;
    const exported = {
      ...projection, nodes: displayedNodes, relations: displayedRelations,
      completeness: {
        ...projection.completeness,
        omitted_nodes: projection.completeness.total_nodes - displayedNodes.length,
        omitted_edges: projection.completeness.total_edges - displayedRelations.length,
        truncated: projection.completeness.total_nodes > displayedNodes.length || projection.completeness.total_edges > displayedRelations.length,
      },
    };
    root.querySelector<HTMLAnchorElement>('[data-neighborhood-export]')!.href = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exported))}`;
    root.querySelectorAll<HTMLButtonElement>('[data-neighborhood-traverse]').forEach(button => button.disabled = false);
    root.querySelector<HTMLElement>('[data-neighborhood-traversal-status]')!.textContent = 'No traversal requested.';
    root.querySelector<HTMLElement>('[data-neighborhood-traversal-results]')!.replaceChildren();
    draw();
  }

  root.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const select = event.target.closest<HTMLElement>('[data-neighborhood-select]');
    if (select?.dataset.neighborhoodSelect && nodes.has(select.dataset.neighborhoodSelect)) {
      selected = select.dataset.neighborhoodSelect;
      render();
    }
    const traverse = event.target.closest<HTMLButtonElement>('[data-neighborhood-traverse]');
    if (!traverse) return;
    const direction = traverse.dataset.neighborhoodTraverse as 'incoming' | 'outgoing';
    const reached = trace(direction);
    root.querySelector<HTMLElement>('[data-neighborhood-traversal-status]')!.textContent = `Display-only ${direction} traversal reached ${reached.length} other objects. No verification performed.`;
    const list = root.querySelector<HTMLElement>('[data-neighborhood-traversal-results]')!;
    list.replaceChildren(...reached.map(node => {
      const item = document.createElement('li'); const link = document.createElement('a');
      link.href = node.href; link.textContent = node.title; item.append(link); return item;
    }));
  });
  typeInputs.forEach(input => input.addEventListener('change', render));
  root.querySelector<HTMLFieldSetElement>('[data-neighborhood-controls]')!.disabled = false;
  render();
}

if (typeof document !== 'undefined') document.querySelectorAll<HTMLElement>('[data-source-neighborhood]').forEach(initializeNeighborhood);
