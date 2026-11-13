"""Judge-facing read-only transfer cockpit; no live API or release controls."""
from __future__ import annotations
import argparse
import base64
from html import escape
import json
from pathlib import Path

EXPECTED_SCHEMA = "mathgraph.upstream-evidence-acquisition.v1"
EXPECTED_MODE = "PINNED_UPSTREAM_WITH_SCRIPTED_MUTATIONS_NOT_LIVE_NEBIUS"
UPSTREAM = "672971d66a2ef9f85151e53283113f33d642dabd"

def render(report: dict) -> str:
    if report.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unknown report schema")
    if report.get("mode") != EXPECTED_MODE:
        raise ValueError("unverified mode/provenance")
    origin=report.get("origin",{})
    if origin.get("commit") != UPSTREAM or origin.get("repository") != "pallets/itsdangerous":
        raise ValueError("source pin mismatch")
    evidence=report.get("experiment",{})
    if evidence.get("minimum_synthetic_cost") != evidence.get("independent_brute_force_cost"):
        raise ValueError("minimum cost not independently checked")
    if evidence.get("minimum_tests_hex") is None:
        raise ValueError("missing separating witnesses")
    comparison=report.get("comparison",{})
    if (comparison.get("baseline_original_tests") != "WARRANTED"
        or comparison.get("with_new_test") != "REJECTED"
        or comparison.get("after_scripted_repair") != "WARRANTED"):
        raise ValueError("unexpected demonstration result")
    timeline=report.get("transitions",[])
    if len(timeline)!=6 or any(e.get("state") not in ("WARRANTED","REJECTED","UNKNOWN") for e in timeline):
        raise ValueError("invalid evidence timeline")
    witnesses=[]
    for hexvalue in evidence["minimum_tests_hex"]:
        if not isinstance(hexvalue,str) or len(hexvalue)>256:
            raise ValueError("invalid candidate input")
        data=bytes.fromhex(hexvalue)
        expected=base64.urlsafe_b64encode(data).rstrip(b"=")
        witnesses.append({"bytes":hexvalue,"output":expected.hex()})
    if len(witnesses)<2:
        raise ValueError("insufficient demonstration")

    data=json.dumps(timeline,ensure_ascii=True).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    def clean(x):
        return escape(str(x),quote=True)
    cases="\n".join(f'''<div class="case"><div class="mono">{i+1:02d} / INPUT HEX <b>{clean(w["bytes"])}</b></div>
    <div class="mono">ORACLE OUTPUT HEX <b>{clean(w["output"])}</b></div></div>'''
    for i,w in enumerate(witnesses))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MathGraph Autopilot — Missing Evidence, Real Project</title>
<style>
:root{{--bg:#0a1221;--surface:#131f34;--line:#344867;--light:#edf3ff;--muted:#aabbd6;--mint:#7ee8ba;--red:#ff9595;--yellow:#ffcd75}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;color:var(--light);background:radial-gradient(circle at 75% -10%,#274769,#0a1221 50%);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1120px;margin:auto;padding:32px 22px 60px}}.eyebrow{{font-weight:800;font-size:12px;letter-spacing:.18em;color:#8bbfff}}
h1{{font-size:clamp(2.3rem,5.5vw,4.2rem);line-height:1.04;letter-spacing:-.045em;margin:16px 0 20px;max-width:900px}}p{{color:var(--muted);line-height:1.6}}.safety{{border:1px solid #806b43;color:#ffdb96;border-radius:10px;padding:12px 16px;font-weight:700;font-size:13px;margin:18px 0 24px;background:#27271f}}
.panel{{background:var(--surface);border:1px solid var(--line);border-radius:17px;padding:24px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}}
.state{{font-weight:850;font-size:30px;letter-spacing:.02em;margin:6px 0}}.WARRANTED{{color:var(--mint)}}.REJECTED{{color:var(--red)}}.UNKNOWN{{color:var(--yellow)}}
h2{{font-size:1.2rem;margin:0 0 12px}}h3{{font-size:1rem;margin:0 0 8px}}.mono{{font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;color:#c8dafa}}
.case{{border-top:1px solid var(--line);padding:13px 0}}.case .mono{{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}}
.stat{{display:flex;align-items:center;gap:14px;margin:12px 0}}.number{{font-size:2.3rem;font-weight:800}}.timeline{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
button{{background:#223b62;color:var(--light);border:1px solid #6288b3;border-radius:8px;cursor:pointer;padding:8px 12px;font-weight:700}}
button:hover,button.selected{{background:#396092}}.large{{font-size:1.4rem;font-weight:700}}.source{{border-top:1px solid var(--line);padding:13px 0}}a{{color:#98cafa}}
footer{{font-size:12px;color:var(--muted);margin-top:25px}}@media(max-width:750px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="eyebrow">MATHGRAPH / AUTOPILOT / REAL SOURCE TRANSFER</div>
<h1>Every existing test passed.<br>Two missing tests changed the verdict.</h1>
<p>Actual upstream package source and test files. Three isolated, deliberately injected coding faults. Independently executed native pytest. MathGraph acquires missing evidence rather than trusting a green suite.</p>
<div class="safety">REAL UPSTREAM SOURCE · SCRIPTED INJECTED MUTATIONS · NOT A LIVE NEBIUS MODEL RUN · NOT AN UPSTREAM BUG REPORT</div>
<div class="grid">
<section class="panel"><div class="eyebrow">CONVENTIONAL FIXED TESTS</div><div class="state WARRANTED">WARRANTED*</div>
<p>Even defective variants passed the unmodified upstream encoding tests. *Authorization is only to say those declared tests passed.</p>
<div class="eyebrow">AFTER THE MISSING OBSERVATIONS</div><div class="state REJECTED">REJECTED</div>
<p>Fresh tests reveal that the candidate cannot fulfill the URL-safe, unpadded Base64 contract.</p>
</section>
<section class="panel"><div class="eyebrow">MINIMUM FINITE TEST BASIS</div>
<div class="stat"><span class="number">{clean(evidence["testcase_domain"])}</span><span>bounded source-native candidate inputs</span></div>
<div class="stat"><span class="number">{len(witnesses)}</span><span>minimum-cost separating tests</span></div>
{cases}
<p>Synthetic total cost <strong>{clean(evidence["minimum_synthetic_cost"])}</strong>. The independent pairwise exact comparator agrees; not a wall-clock performance benchmark.</p>
</section>
</div>
<section class="panel"><h2>Selective authority withdrawal</h2>
<p>Choose each event to inspect precisely what evidence was accepted, missing or revoked.</p>
<div id="timeline" class="timeline"></div>
<div class="grid"><div><div class="eyebrow">EVIDENCE STEP</div><div id="state" class="state"></div><h3 id="step"></h3><p id="reason"></p></div>
<div><div class="eyebrow">RECEIPT FINGERPRINT</div><div id="receipt" class="mono"></div></div></div>
</section>
<div class="grid">
<section class="panel"><h2>Provenance</h2><p>Public repository: <a href="https://github.com/pallets/itsdangerous/tree/{UPSTREAM}" rel="noopener">pallets/itsdangerous</a></p>
<div class="source mono">Source commit: {UPSTREAM}</div>
<div class="source mono">Schema: {clean(report["schema"])}</div>
<div class="source mono">Provider: SCRIPTED — not Nebius</div></section>
<section class="panel"><h2>Qualification boundary</h2><p>A genuine source-native software replay with intentionally injected faults, a finite predeclared input grammar, a separately specified standard-library oracle, and exact-byte test receipts.</p>
<p>No claim of a discovered upstream bug, arbitrary-repository repair, unseen-defect detection, signed CI attestation, general mathematical proof, or qualifying NVIDIA-model inference.</p></section>
</div>
<footer>MathGraph Autopilot · evidence generated by GitHub Actions from an independently pinned public repository and verified finite tests.</footer>
<script>
const events={data};
const $=id=>document.getElementById(id);
let selected=0;
function draw(){{const event=events[selected];const state=$('state');state.textContent=event.state;state.className='state '+event.state;$('step').textContent=event.step.replaceAll('_',' ');
$('reason').textContent=event.reason||({{WARRANTED:'The current exact-byte test receipt satisfies its declared test scope.',REJECTED:'New evidence or changed bytes withdrew authorization.',UNKNOWN:'Missing evidence must be acquired.'}}[event.state]);
const r=event.receipt||{{}};$('receipt').textContent='Candidate snapshot: '+(r.before_snapshot||'none')+'\\nTest stdout SHA256: '+(r.stdout_sha256||'none')+'\\nExit code: '+(r.exit_code??'—');
[...$('timeline').children].forEach((button,n)=>button.className=n===selected?'selected':'');}}
events.forEach((event,i)=>{{const b=document.createElement('button');b.textContent=(i+1)+'. '+event.step.replaceAll('_',' ');b.onclick=()=>{{selected=i;draw()}};$('timeline').appendChild(b)}});draw();
</script></main></body></html>'''

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("report",type=Path)
    p.add_argument("--output",type=Path,default=Path("upstream-transfer-cockpit.html"))
    a=p.parse_args()
    a.output.write_text(render(json.loads(a.report.read_text())),encoding="utf-8")
    print(a.output)

if __name__ == "__main__":
    main()
