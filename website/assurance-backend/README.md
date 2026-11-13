# MathGraph Open Challenge — operational intake

The public `/assurance/` page offers a selectively reviewed **free first independently confirmed assurance finding**. No finding is promised. The separate Cloudflare Worker receives only standard HTML form fields.

## Deployed infrastructure

- Worker: `mathgraph-assurance-intake`, URL `https://mathgraph-assurance-intake.metalogiclabs-check.workers.dev/submit`.
- Cloudflare D1 database: `mathgraph_assurance_leads` (OC location hint), bound in Worker as `LEADS`.
- Turnstile widget: `MathGraph Open Challenge — production`, authorized for `mathgraph.org` and `www.mathgraph.org`.
- Secret `TURNSTILE_SECRET` is stored as a Cloudflare Worker secret, **never** in the repository.
- Cron: `0 3 * * *` UTC, deletes enquiries after the 180-day retention horizon. The Worker `scheduled` handler must remain enabled.
- Public `GET /health` returns readiness without any lead data. Other GET paths return 404.
- Live form is gated to production domain: JavaScript and the Turnstile widget remain disabled on previews and localhost.
- The UI displays receipt only after Cloudflare Turnstile verification and a successful D1 INSERT. No local storage, email attachment, browser cookies, customer login or source upload is implemented by MathGraph.

## Daily review and response

The current implementation **stores leads privately but does not yet send automatic notification or acknowledgement email**. Existing Vercel and Cloudflare connections contained no configured transactional-email provider, and MathGraph's domain is not present among the connected Cloudflare DNS zones. A notification solution will require a verified email sender/provider and a corresponding secret/binding. Do not launch a paid LinkedIn campaign assuming automatic email alerts until that is configured and a complete delivery test is run.

Review the database in the authenticated Cloudflare dashboard; do not create public records or copy private applicant details to GitHub.

```sql
SELECT id, created_at, repository_url, claim, decision, consequence, email, relationship, status,
       campaign_source, campaign_medium, campaign_name
FROM submissions
ORDER BY created_at DESC LIMIT 25;
```

Update status only after a human decision. The database does not assert that any intake is an accepted customer, paid engagement, or verified finding. Do not publicly share submissions without explicit applicant consent.

## Validation and release boundary

- Run the new `assurance-intake.test.mjs` regression: approved-origin validation; fabricated input; Turnstile fail-closed; D1 fail-closed; no personal-data reflection.
- Test `GET /health` once Worker DNS propagates. A successful health response verifies bindings exist; it does **not** test an actual Turnstile token or end-to-end submission.
- Browser-check the form at the production origin, complete Turnstile, submit a clearly marked **test record**, independently verify it arrived in D1, verify receipt redirect and delete the test record.
- Confirm owner notification and privacy requests are receivable before purchasing LinkedIn ads.
- The earlier PR #275 is an overlapping draft; PR #272 is the consolidation path. Neither CI-green previews nor an uploaded Worker alone imply the live MathGraph site was deployed.

The public privacy notice is at `/assurance/privacy/`. Requests for data deletion go to `heath@mathgraph.org`. Do not promise delivery/review SLAs until separately established.
