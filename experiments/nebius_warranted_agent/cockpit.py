"""Generate an offline interactive audit cockpit from a retained JSON run report."""
import argparse
from html import escape
import json
from pathlib import Path


def render(report: dict) -> str:
    # Serialize with JS-embedding escape to prevent user-controlled report text
    # from escaping the script element.
    payload = json.dumps(report, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    source = escape(report.get("source_sha256", "unknown"))
    is_live = report.get("provider") == "NebiusProvider" and all(
        event.get("proposal", {}).get("provider") in (None, "nebius-token-factory")
        for event in report.get("events", []))
    kind = "NEBIUS RUN (UNVERIFIED EXTERNAL PROVENANCE)" if is_live else "SCRIPTED OFFLINE FIXTURE — NOT NEBIUS"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MathGraph Autopilot · Evidence Cockpit</title>
<style>
:root{{--bg:#0b1020;--panel:#151d31;--line:#34405a;--text:#e7edfb;--sub:#a4b2cf;--green:#64e5b1;--red:#ff8585;--amber:#e9c16b}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top right,#203459,#0b1020 50%);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}}main{{max-width:1080px;margin:auto;padding:28px 20px}}h1{{font-size:clamp(2rem,5vw,3.3rem);margin:6px 0}}h2{{font-size:1.1rem}}p{{color:var(--sub);line-height:1.55}}.eyebrow{{color:#91b8ff;letter-spacing:.14em;font-weight:750;font-size:12px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.panel{{border:1px solid var(--line);background:var(--panel);border-radius:16px;padding:20px}}.banner{{border:1px solid #8b733d;background:#2a251a;color:#f8d98b;padding:11px 16px;border-radius:8px;display:inline-block;font-size:12px;font-weight:bold}}.tag{{font-weight:750;letter-spacing:.08em}}.WARRANTED{{color:var(--green)}}.REJECTED{{color:var(--red)}}.UNKNOWN{{color:var(--amber)}}.heroState{{font-size:30px;margin:10px 0}}button{{cursor:pointer;border:1px solid #6888c2;color:white;background:#263a65;border-radius:8px;padding:10px 14px;font-weight:700}}button:hover{{background:#31538a}}button:disabled{{opacity:.4;cursor:default}}.steps{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}}.steps button{{font-size:13px;padding:9px 12px}}.steps button.selected{{outline:2px solid #90c5ff}}.mono{{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;color:#b7c9e9}}.kv{{display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid var(--line);padding:9px 0}}.kv span:first-child{{color:var(--sub)}}footer{{color:var(--sub);font-size:12px;padding:24px 0}}@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}</style>
</head><body><main>
<div class="eyebrow">MATHGRAPH / AUTOPILOT / EVIDENCE COCKPIT</div>
<h1>The agent that proves it's finished.</h1>
<div class="banner">{escape(kind)}</div>
<p>When code changes, yesterday's green test is no longer permission to release. Follow this retained experiment from initial failure to repair and evidence withdrawal.</p>
<div class="panel"><div class="eyebrow">VERIFICATION TIMELINE</div><div id="steps" class="steps"></div><button id="previous">← Previous</button> <button id="next">Next →</button></div>
<div class="grid" style="margin-top:18px">
<section class="panel"><div class="eyebrow">DECISION</div><div id="state" class="heroState"></div><h2 id="step"></h2><p id="reason"></p><div id="attempt"></div></section>
<section class="panel"><div class="eyebrow">AUDIT EVIDENCE</div><div id="receipt"></div></section>
</div><div class="panel" style="margin-top:18px"><div class="eyebrow">AUTHORITY BOUNDARY</div>
<p>This qualifies only a pinned, local, trusted two-file Python fixture against its declared unittest suite. This is not a formal theorem, a secure sandbox, a general-purpose coding agent, or proof of live model inference.</p>
<div class="kv"><span>Starting workspace SHA-256</span><span class="mono">{source}</span></div>
<div class="kv"><span>Provider</span><span class="mono">{escape(str(report.get('provider','unknown')))}</span></div>
</div><footer>Never promote a scripted demonstration into a live model claim. Source revisions, test receipts, and execution boundaries must be reconciled before release.</footer></main>
<script>const report={payload};const evs=report.events||[];let i=0;
const $=id=>document.getElementById(id);
function setText(id,value){{$ (id).textContent=String(value??'—');}}
function line(parent,name,value){{const el=document.createElement('div');el.className='kv';const l=document.createElement('span');l.textContent=name;const r=document.createElement('span');r.className='mono';r.textContent=String(value??'—');el.append(l,r);parent.append(el)}}
function draw(){{if(!evs.length)return;const e=evs[i];const s=$('state');s.className='heroState tag '+e.state;s.textContent=e.state;setText('step',e.step.replaceAll('_',' ').toUpperCase());setText('reason',e.reason||({{WARRANTED:'Declared tests passed for the exact candidate bytes.',REJECTED:'Evidence failed the declared verification gate.',UNKNOWN:'Evidence is not yet sufficient.'}}[e.state]));setText('attempt',e.attempt?'Attempt '+e.attempt:'');const r=$('receipt');r.replaceChildren();if(e.receipt){{for(const key of ['candidate_sha256','source_sha256','after_sha256','exit_code','outcome','output_sha256','acquired_at'])line(r,key,e.receipt[key])}}else line(r,'qualification','No accepted receipt for this state');if(e.proposal){{line(r,'model',e.proposal.model);line(r,'provider',e.proposal.provider);line(r,'response_sha256',e.proposal.response_sha256)}}$('previous').disabled=i===0;$('next').disabled=i===evs.length-1;for(const [j,b] of [...$('steps').children].entries())b.className=j===i?'selected':''}}
for(let j=0;j<evs.length;j++){{const b=document.createElement('button');b.textContent=(j+1)+'. '+evs[j].step.replaceAll('_',' ');b.onclick=()=>{{i=j;draw()}};$('steps').append(b)}}$('previous').onclick=()=>{{i=Math.max(0,i-1);draw()}};$('next').onclick=()=>{{i=Math.min(evs.length-1,i+1);draw()}};draw();
</script></body></html>'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument("report")
    p.add_argument("--output", default="cockpit.html")
    a = p.parse_args()
    data = json.loads(Path(a.report).read_text())
    Path(a.output).write_text(render(data), encoding="utf-8")
    print(a.output)


if __name__ == "__main__":
    main()
