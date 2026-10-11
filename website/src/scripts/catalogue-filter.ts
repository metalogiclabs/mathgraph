function normalize(value: string): string {
  return value.normalize('NFKC').toLocaleLowerCase('en-US').trim();
}

function initializeCatalogue(root: HTMLElement): void {
  const controls = root.querySelector<HTMLFieldSetElement>('[data-catalogue-controls]');
  const query = root.querySelector<HTMLInputElement>('[data-catalogue-query]');
  const selects = Array.from(root.querySelectorAll<HTMLSelectElement>('[data-catalogue-select]'));
  const clear = root.querySelector<HTMLButtonElement>('[data-catalogue-clear]');
  const count = root.querySelector<HTMLElement>('[data-catalogue-count]');
  const noMatch = root.querySelector<HTMLElement>('[data-catalogue-no-match]');
  const items = Array.from(root.querySelectorAll<HTMLElement>('[data-catalogue-item]'));
  if (!controls || !query || !clear || !count || !noMatch) return;

  const render = (): void => {
    const needle = normalize(query.value);
    let visible = 0;
    for (const item of items) {
      const textMatches = !needle || normalize(item.dataset.catalogueSearch ?? item.textContent ?? '').includes(needle);
      const axesMatch = selects.every((select) => {
        const field = select.dataset.catalogueField;
        const itemField = field ? `catalogue${field[0].toUpperCase()}${field.slice(1)}` : undefined;
        return !select.value || (itemField !== undefined && item.dataset[itemField] === select.value);
      });
      item.hidden = !(textMatches && axesMatch);
      if (!item.hidden) visible += 1;
    }
    count.textContent = `${visible} of ${items.length} displayed.`;
    noMatch.hidden = visible !== 0;
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
  document.querySelectorAll<HTMLElement>('[data-catalogue-filter]').forEach(initializeCatalogue);
}
