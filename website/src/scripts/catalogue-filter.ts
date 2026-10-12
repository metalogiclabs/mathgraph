function normalize(value: string): string {
  return value.normalize('NFKC').toLocaleLowerCase('en-US').trim();
}

function tokens(value: string): string[] {
  return normalize(value).match(/[\p{L}\p{N}]+/gu) ?? [];
}

function orderedSubsequence(query: string[], value: string[]): boolean {
  let index = 0;
  for (const token of value) if (token === query[index]) index += 1;
  return index === query.length;
}

function titleFor(item: HTMLElement): string {
  return item.dataset.catalogueTitle ?? item.querySelector<HTMLElement>('[data-catalogue-entry-title]')?.textContent ?? '';
}

function moduleFor(item: HTMLElement): string {
  return item.dataset.catalogueModule ?? item.querySelector<HTMLElement>('.knowledge-catalogue__meta > span')?.textContent ?? '';
}

function relevance(item: HTMLElement, query: string, metadata: string): number | null {
  const needle = normalize(query);
  if (!needle) return 5;
  const displayTitle = titleFor(item);
  const title = normalize(displayTitle);
  const finalName = normalize(displayTitle.split(/[.:/#]/u).filter(Boolean).at(-1) ?? displayTitle);
  if (title === needle) return 0;
  if (finalName === needle) return 1;
  const queryTokens = tokens(query);
  if (queryTokens.length > 0 && orderedSubsequence(queryTokens, tokens(title))) return 2;
  if (title.includes(needle)) return 3;
  const normalizedMetadata = normalize(metadata);
  if (queryTokens.length > 0 && queryTokens.every(token => normalizedMetadata.includes(token))) return 4;
  return normalizedMetadata.includes(needle) ? 4 : null;
}

async function initializeCatalogue(root: HTMLElement): Promise<void> {
  const controls = root.querySelector<HTMLFieldSetElement>('[data-catalogue-controls]');
  const query = root.querySelector<HTMLInputElement>('[data-catalogue-query]');
  const selects = Array.from(root.querySelectorAll<HTMLSelectElement>('[data-catalogue-select]'));
  const clear = root.querySelector<HTMLButtonElement>('[data-catalogue-clear]');
  const count = root.querySelector<HTMLElement>('[data-catalogue-count]');
  const noMatch = root.querySelector<HTMLElement>('[data-catalogue-no-match]');
  const itemsRoot = root.querySelector<HTMLElement>('[data-catalogue-items]');
  const orderRoot = root.querySelector<HTMLElement>('[data-catalogue-order-root]');
  const items = Array.from(root.querySelectorAll<HTMLElement>('[data-catalogue-item]'));
  if (!controls || !query || !clear || !count || !noMatch || !itemsRoot) return;
  const ranked = root.dataset.catalogueRanked === 'true';
  const urlState = root.dataset.catalogueUrlState === 'true';
  const metadata = new Map(items.map(item => [item, item.dataset.catalogueMetadata ?? item.dataset.catalogueSearch ?? item.textContent ?? '']));

  const searchIndex = root.dataset.catalogueSearchIndex;
  if (searchIndex) {
    try {
      const url = new URL(searchIndex, window.location.origin);
      if (url.origin !== window.location.origin) throw new Error('CROSS_ORIGIN_SEARCH_INDEX');
      const response = await fetch(url);
      if (!response.ok) throw new Error('SEARCH_INDEX_UNAVAILABLE');
      const values: unknown = await response.json();
      const expected = Number(root.dataset.catalogueSearchIndexCount);
      if (!Array.isArray(values) || !Number.isSafeInteger(expected) || values.length !== expected) throw new Error('SEARCH_INDEX_INVALID');
      const sourceItems = items.filter(item => item.hasAttribute('data-catalogue-source'));
      if (sourceItems.length !== expected) throw new Error('SEARCH_INDEX_MISMATCH');
      const seen = new Set<string>();
      for (let index = 0; index < values.length; index += 1) {
        const value = values[index];
        if (!value || typeof value !== 'object') throw new Error('SEARCH_INDEX_INVALID');
        const entry = value as Record<string, unknown>;
        if (![entry.object_id, entry.qualified_name, entry.module, entry.kind, entry.statement].every(field => typeof field === 'string')) throw new Error('SEARCH_INDEX_INVALID');
        const id = entry.object_id as string;
        const item = sourceItems[index];
        if (!item || seen.has(id) || titleFor(item) !== entry.qualified_name || moduleFor(item) !== entry.module) throw new Error('SEARCH_INDEX_MISMATCH');
        seen.add(id);
        item.dataset.catalogueSourceId = id;
        item.dataset.catalogueProject = 'Mathlib';
        item.dataset.catalogueKind = 'SOURCE_DECLARATION';
        item.dataset.catalogueModule = entry.module as string;
        item.dataset.catalogueStatus = 'SOURCE_INDEXED';
        metadata.set(item, `${metadata.get(item)} ${entry.kind} ${entry.statement}`);
      }
      if (seen.size !== expected) throw new Error('SEARCH_INDEX_MISMATCH');
    } catch (error) {
      // The complete static catalogue remains usable by name. Search enrichment grants no authority.
      root.dataset.catalogueSearchIndexState = error instanceof Error ? error.message : 'SEARCH_INDEX_UNAVAILABLE';
    }
  }

  if (urlState) {
    const parameters = new URLSearchParams(window.location.search);
    query.value = (parameters.get('q') ?? '').slice(0, 200);
    for (const select of selects) {
      const field = select.dataset.catalogueField;
      const requested = field ? parameters.get(field) : null;
      if (requested !== null && Array.from(select.options).some(option => option.value === requested)) select.value = requested;
    }
  }

  const render = (): void => {
    const needle = normalize(query.value);
    const visible: Array<{ item: HTMLElement; score: number; id: string }> = [];
    const hidden: HTMLElement[] = [];
    for (const item of items) {
      const itemMetadata = metadata.get(item) ?? '';
      const score = ranked ? relevance(item, query.value, itemMetadata) : (!needle || normalize(itemMetadata).includes(needle) ? 0 : null);
      const axesMatch = selects.every((select) => {
        const field = select.dataset.catalogueField;
        const itemField = field ? `catalogue${field[0].toUpperCase()}${field.slice(1)}` : undefined;
        return !select.value || (itemField !== undefined && item.dataset[itemField] === select.value);
      });
      item.hidden = score === null || !axesMatch;
      if (item.hidden) hidden.push(item);
      else visible.push({ item, score: score ?? 0, id: item.dataset.catalogueSourceId ?? '' });
    }
    if (ranked) visible.sort((left, right) => left.score - right.score || left.id.localeCompare(right.id, 'en-US'));
    const destination = orderRoot ?? itemsRoot;
    for (const { item } of visible) destination.append(item);
    for (const item of hidden) destination.append(item);
    count.textContent = `${visible.length} of ${items.length} displayed.`;
    noMatch.hidden = visible.length !== 0;
  };

  query.addEventListener('input', render);
  for (const select of selects) select.addEventListener('change', render);
  clear.addEventListener('click', () => {
    query.value = '';
    for (const select of selects) select.value = '';
    render();
    query.focus();
  });
  controls.disabled = false;
  query.disabled = false;
  clear.disabled = false;
  for (const select of selects) select.disabled = false;
  render();
}

if (typeof document !== 'undefined') {
  document.querySelectorAll<HTMLElement>('[data-catalogue-filter]').forEach(root => { void initializeCatalogue(root); });
}
