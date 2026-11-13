// Public form only: no analytics SDK, no cookies, no source-code upload.
(() => {
  const form = document.querySelector('[data-assurance-intake]');
  if (!form) return;
  const submit = form.querySelector('[data-assurance-submit]');
  const status = form.querySelector('[data-turnstile-status]');
  const setStatus = message => { if (status) status.textContent = message; };
  if (!submit) return;
  const allowed = ['mathgraph.org', 'www.mathgraph.org'];
  if (!allowed.includes(window.location.hostname)) {
    submit.disabled = true;
    setStatus('This preview does not accept submissions. Please use the live MathGraph site or the email fallback.');
    return;
  }
  for (const name of ['utm_source', 'utm_medium', 'utm_campaign']) {
    const value = new URLSearchParams(window.location.search).get(name) || '';
    const input = form.elements.namedItem(name);
    if (input && /^[a-z0-9_. -]{0,80}$/i.test(value)) input.value = value;
  }
  window.mathgraphTurnstileOk = () => { submit.disabled = false; setStatus('Human verification completed. You can submit your enquiry.'); };
  window.mathgraphTurnstileExpired = () => { submit.disabled = true; setStatus('Verification expired. Please complete it again.'); };
  window.mathgraphTurnstileError = () => { submit.disabled = true; setStatus('Human verification could not load. Please use the email fallback.'); };
  submit.disabled = true;
  setStatus('Checking your browser before submission…');
  const script = document.createElement('script');
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
  script.async = true;
  script.defer = true;
  script.onerror = () => window.mathgraphTurnstileError();
  script.onload = () => setStatus('Complete the human-verification check to submit.');
  document.head.appendChild(script);
})();