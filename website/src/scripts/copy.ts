const buttons = document.querySelectorAll<HTMLButtonElement>('[data-copy-value]');

for (const button of buttons) {
  const initialLabel = button.textContent ?? 'Copy';
  button.addEventListener('click', async () => {
    const value = button.dataset.copyValue;
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      button.textContent = 'Copied';
    } catch {
      button.textContent = 'Select value';
    }
    window.setTimeout(() => {
      button.textContent = initialLabel;
    }, 1800);
  });
}
