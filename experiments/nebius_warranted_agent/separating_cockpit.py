"""Render a read-only, provenance-explicit separating-experiment judge cockpit."""
from __future__ import annotations
import argparse
from html import escape
import json
from pathlib import Path

EXPECTED_SCHEMA="mathgraph.separating-experiment.v1"
EXPECTED_PROVIDER="SCRIPTED_OFFLINE_FIXTURE_NOT_NEBIUS"

def render(report: dict) -> str:
    if report.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unsupported evidence schema")
    if report.get("provider") != EXPECTED_PROVIDER:
        raise ValueError("provenance not admitted for offline demonstration")
    basis = report["basis"]
    comparison = report["comparison"]
    if basis.get("status") != "MINIMUM_BASIS" or not isinstance(basis.get("tests"),list):
        raise ValueError("no qualified finite experiment basis")
    clean=lambda value: escape(str(value),quote=True)
    timeline=[]
    for n,event in enumerate(report["timeline"],start=1):
        state=event["state"]
        if state not in {"WARRANTED","REJECTED","UNKNOWN"}:
            raise ValueError("invalid evidence state")
        label=clean(event["step"].replace("_"," ").title())
        timeline.append(f'<div class="event"><span class="step">{n:02d}</span>'
                        f'<strong>{label}</strong><span class="state {state}">{state}</span></div>')
    tests=[]
    for case in basis["tests"]:
        if not (isinstance(case,list) and len(case)==3 and all(type(x)==int for x in case)):
            raise ValueError("untrusted finite testcase")
        v,low,high=case
        tests.append(f'<div class="case"><code>clamp({v}, {low}, {high})</code>'
                     f'<span>expected {clean(_expected(case))}</span></div>')
    rivals=clean(", ".join(basis.get("rivals",[])))
    domain=clean(basis.get("domain_size","unknown"))
    price=clean(basis.get("total_cost","unknown"))
    case_html="\n".join(tests)
    event_html="\n".join(timeline)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MathGraph Autopilot | The Missing Experiment</title>
<style>
:root{{--bg:#09101e;--surface:#121e32;--line:#30415d;--muted:#a7b7d2;--bright:#eaf2ff;--green:#6edfb7;--yellow:#f7d47a;--red:#fa929c}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(120deg,#09101e 0%,#10213a 100%);
font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--bright)}}
main{{max-width:1100px;margin:auto;padding:40px 22px 70px}}.eyebrow{{font:700 12px system-ui;letter-spacing:.17em;color:#91b8ff}}
h1{{font-size:clamp(2rem,5vw,3.7rem);line-height:1.09;letter-spacing:-.035em;margin:12px 0 20px}}h2{{margin:0 0 18px;font-size:1.2rem}}
p{{color:var(--muted)}}.note{{color:var(--yellow);padding:12px 16px;border:1px solid #977c42;border-radius:9px;margin:22px 0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:26px 0}}.panel{{padding:24px;background:var(--surface);
border:1px solid var(--line);border-radius:16px}}.big{{font-size:2rem;line-height:1.3;font-weight:800}}
.event,.case{{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 0;border-top:1px solid var(--line)}}
.step{{font:700 12px ui-monospace,monospace;color:#91b8ff}}.state{{font:800 12px ui-monospace,monospace}}
.WARRANTED{{color:var(--green)}}.REJECTED{{color:var(--red)}}.UNKNOWN{{color:var(--yellow)}}
code{{color:#c4e4ff;font:14px ui-monospace,monospace}}small{{color:var(--muted)}}.case span{{color:var(--green)}}
.metric{{display:flex;flex-direction:column;gap:3px}}.divider{{border-top:1px solid var(--line);margin:18px 0}}
.mono{{font:12px ui-monospace,monospace;overflow-wrap:anywhere;color:#bdcee8}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="eyebrow">MATHGRAPH / EVIDENCE-SEEKING AUTOPILOT</div>
<h1>It passed the tests.<br>MathGraph found the missing test.</h1>
<div class="note"><b>SCRIPTED OFFLINE EXPERIMENT — NOT A NEBIUS INFERENCE.</b>
 The test runner and receipt checks executed. The candidate defects, reference behavior, domain and cost model were predeclared.</div>
<div class="grid">
 <section class="panel"><div class="eyebrow">FIXED-TEST BASELINE</div><div class="big WARRANTED">WARRANTED*</div>
  <p>All four original tests pass, even for the defective implementation. *This is only qualification against the original declared tests.</p>
  <div class="divider"></div><div class="eyebrow">AFTER ACQUIRING NEW EVIDENCE</div><div class="big REJECTED">REJECTED</div>
  <p>The newly selected tests expose a previously undetected defect and require a repair.</p></section>
 <section class="panel"><div class="eyebrow">THE SMALLEST SEPARATING EXPERIMENT</div>
  <h2>{len(tests)} tests · declared total cost {price}</h2>{case_html}
  <div class="divider"></div><div class="metric"><small>Finite input cases</small><strong>{domain}</strong></div>
  <p>Separates all surviving defective hypotheses: {rivals}. Independent exhaustive comparison agrees with the minimum cost.</p></section>
</div>
<section class="panel"><h2>Authority withdrawal and evidence reacquisition</h2>{event_html}
<p>After a scripted correction, the independent runner acquires fresh evidence for exact source and test bytes.
 Only then does test-scoped qualification return.</p></section>
<div class="grid"><section class="panel"><h2>Measurement</h2>
 <div class="event"><span>Fixed-only</span><span class="state WARRANTED">{clean(comparison.get("fixed_test_only"))}</span></div>
 <div class="event"><span>New separating tests</span><span class="state REJECTED">{clean(comparison.get("after_separating_test"))}</span></div>
 <div class="event"><span>Scripted repair retested</span><span class="state WARRANTED">{clean(comparison.get("after_scripted_repair"))}</span></div>
 <div class="event"><span>Finite agreement</span><strong>{clean(comparison.get("finite_domain_agreement"))}</strong></div>
</section><section class="panel"><h2>Trust boundary</h2>
 <p>Predeclared mutant pool, deterministic finite oracle and synthetic costs. Exact optimality is only within this grammar. No live model inference, general repository claim, independent external attestation or global software proof.</p>
 <small>Schema: {clean(report["schema"])}</small>
 <div class="mono">Provider: {clean(report["provider"])}</div>
</section></div>
<footer><small>Verification and original report: GitHub Actions artifact, MathGraph Autopilot PR #203.</small></footer>
</main></body></html>'''

def _expected(case):
    from separating_experiments import oracle
    return oracle(tuple(case))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("report")
    p.add_argument("--output",default="separating-cockpit.html")
    args=p.parse_args()
    payload=json.loads(Path(args.report).read_text())
    Path(args.output).write_text(render(payload),encoding="utf-8")
    print(args.output)

if __name__=="__main__":
    main()
