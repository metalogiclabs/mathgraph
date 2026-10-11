export {};

const header = document.querySelector<HTMLElement>('.site-header');
const button = header?.querySelector<HTMLButtonElement>('.nav-toggle');
const navigation = header?.querySelector<HTMLElement>('#primary-navigation');

if (header && button && navigation) {
  const mobile = window.matchMedia('(max-width: 900px)');
  const close = (returnFocus = false) => {
    button.setAttribute('aria-expanded', 'false');
    if (returnFocus) button.focus();
  };
  button.addEventListener('click', () => {
    if (mobile.matches) button.setAttribute('aria-expanded', String(button.getAttribute('aria-expanded') !== 'true'));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') close(true);
  });
  const outside = (event: Event) => {
    if (event.target instanceof Node && !navigation.contains(event.target) && !button.contains(event.target)) close();
  };
  document.addEventListener('pointerdown', outside);
  document.addEventListener('focusin', outside);
  mobile.addEventListener('change', () => {
    const focusInNavigation = navigation.contains(document.activeElement);
    const focusOnButton = document.activeElement === button;
    close(mobile.matches && focusInNavigation);
    if (!mobile.matches && focusOnButton) navigation.querySelector<HTMLAnchorElement>('a')?.focus();
  });
  // Apply the collapsing CSS only once the complete disclosure is operable.
  header.dataset.navEnhanced = '';
}
