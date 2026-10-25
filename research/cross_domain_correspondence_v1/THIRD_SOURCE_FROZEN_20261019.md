# Third-source held-out correspondence protocol — frozen before source inspection or test outcome

Date: 2026-10-19. Status: CANDIDATE. This is a supplemental preregistration: MathGraph common protocol V1 (commit 9c8b427c679398fd80ea56d9a91a1627b2e96b6d) MUST remain unchanged.

## Source and selection
Selected from repository metadata without opening native implementation/test outputs: `pallets/markupsafe@4e111271b1494995708a9e878a10829b5e10c7ba` (published commit dated 2026-10-03). Distinct from PKC proof attribution and YAML typed interchange: HTML escaping and safety labeling.

This source is **held-out relative to this frozen cross-domain detector experiment**, not asserted globally untouched across all earlier research. Semantic obligations below are expert-authored **before inspecting the selected source**. Hence the experiment can at most qualify transfer of the frozen decision protocol to a third new adapter, not autonomous invention of the relation.

## Frozen challenge/requirements
Interpretation authority: independent Python `html.parser.HTMLParser(convert_charrefs=True)` applied to an HTML **attribute context**, plus a direct ordinary-string comparison oracle. This is bounded to double-quoted `data-v` attribute contexts, not full browser safety.

Constructed native MarkupSafe examples with untrusted literal `x\" onmouseover=\"alert(1)`:

- H1 (positive): call `markupsafe.escape(untrusted)` and insert into a double-quoted HTML attribute. Verify the independent parser sees **one attribute** `data-v` with the exact input value, and no `onmouseover` attribute. Expected WARRANTED_BOUNDED for this exact input/context only.
- H2 (negative): call `str(markupsafe.Markup(untrusted))` and insert into the same attribute. Verify parser sees an extra `onmouseover` attribute or otherwise fails the declared one-attribute preservation relation. Expected REJECTED_BOUNDED for this exact input/context; this is **not a MarkupSafe defect** because Markup intentionally designates pretrusted strings.
- H3 (unsupported): arbitrary claim 'HTML safe in all browser contexts' with no independently specified relation. Expected UNKNOWN.
- Baseline: MarkupSafe native package tests (at least a selected actual upstream test file) and independent interpreter; direct escaped/unescaped comparisons; negative/positive guards.
- Withdrawal: changing/removing the trusted-html attribution or adapter evidence invalidates H1/H2 as applicable, while all PKC and L4YAML declarations stay untouched.

Native tests and independent oracle results MUST be archived with pinned source and build SHA. If H1 or H2 prediction fails, preserve genuine counterevidence and do not amend these expected outcomes. Do not claim upstream security vulnerability, general security of MarkupSafe, or autonomous relation discovery.

Success is qualification of **third-adapter evidence protocol reuse** on this predeclared relation, conditional on GREEN native tests, independently observed HTML semantics and correct fail-closed UNKNOWN.
