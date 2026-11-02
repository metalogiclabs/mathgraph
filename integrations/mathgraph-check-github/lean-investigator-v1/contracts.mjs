import {createHash} from 'node:crypto';
// Native guard observations remain advisory; model-selected intent is unverified.
const requireFact=(v,r)=>{if(!v)throw Error(r);};
const text=(s,n)=>typeof s==='string'&&s.trim().length>0&&Buffer.byteLength(s)<=n;
function expressionOK(expression){
 if(!text(expression,6000)||/[\r\n«»]/.test(expression))return false;
 let outside='',quoted=false,escaped=false;const stack=[];
 for(let i=0;i<expression.length;i++){
  const c=expression[i];
  if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;continue;}
  if(c==='"'){if(expression[i-1]==='!')return false;quoted=true;outside+=' ';continue;}
  outside+=c;
  if('([{'.includes(c))stack.push(c);
  if(')]}'.includes(c)&&stack.pop()!=={')':'(',']':'[','}':'{'}[c])return false;
 }
 if(quoted||stack.length||outside.includes('--')||outside.includes('/-'))return false;
 if(/\b(?:unsafe\w*|sorry\w*|axiom|admit|IO|System|import|namespace|theorem|lemma|def|opaque|set_option|by)\b/.test(outside))return false;
 return !/#(?!\[)/.test(outside);
}
export function admitLeanPlan(p){
 requireFact(text(p?.summary,1200)&&Array.isArray(p?.tests)&&p.tests.length>0&&p.tests.length<=3,'INVALID_LEAN_PLAN');const ids=new Set();
 for(const t of p.tests){requireFact(/^[a-z][a-z0-9_]{0,39}$/.test(t?.id??'')&&!t.id.startsWith('control_')&&!ids.has(t.id)&&text(t.hypothesis,1600)&&text(t.contract,2000)&&expressionOK(t.expression),'INVALID_LEAN_PROBE');ids.add(t.id);}
 return structuredClone(p);
}
// Lex active source: nested comments are removed, literals become stable tokens.
// This is a conservative admission filter, not a general Lean elaborator.
function activeSource(source){
 let i=0,code='',docs=[];
 while(i<source.length){
  if(source.startsWith('--',i)){while(i<source.length&&source[i]!='\n')i++;continue;}
  if(source.startsWith('/-',i)){
   const start=i,isDoc=source.startsWith('/--',i);let depth=1;i+=2;
   while(i<source.length&&depth){if(source.startsWith('/-',i)){depth++;i+=2;}else if(source.startsWith('-/',i)){depth--;i+=2;}else i++;}
   requireFact(depth===0,'UNTERMINATED_COMMENT');if(isDoc)docs.push(source.slice(start,i));
   code+=' '+source.slice(start,i).replace(/[^\n]/g,' ');continue;
  }
  if(source[i]==='"'){
   const start=i++;let escaped=false,closed=false;
   while(i<source.length){const c=source[i++];if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"'){closed=true;break;}}
   requireFact(closed,'UNTERMINATED_LITERAL');code+='STRING_'+createHash('sha256').update(source.slice(start,i)).digest('hex');continue;
  }
  const char=source.slice(i).match(/^'(?:\\.|[^'\\])'/);
  if(char){code+='CHAR_'+createHash('sha256').update(char[0]).digest('hex');i+=char[0].length;continue;}
  code+=source[i++];
 }
 return {code,docs};
}
function catalog(source){
 const {code,docs}=activeSource(source),lines=code.split('\n'),guards=[],headers=[];
 for(let i=0;i<lines.length;i++)if(/^#guard\b/.test(lines[i])){let j=i+1;while(j<lines.length&&(!lines[j].trim()||/^\s/.test(lines[j])))j++;guards.push(lines.slice(i,j).join(' ').replace(/\s+/g,' ').trim());i=j-1;}
 for(const m of code.matchAll(/^(?:def|lemma|theorem|abbrev|inductive|structure)\s+/gm)){
  let depth=0,end=code.length;
  for(let j=m.index;j<code.length;j++){
   if('([{'.includes(code[j]))depth++;else if(')]}'.includes(code[j]))depth--;
   if(depth===0&&(code.startsWith(':=',j)||/^where\b/.test(code.slice(j))||code[j]==='\n'&&/^\n\s*\|/.test(code.slice(j)))){end=j;break;}
  }
  headers.push(code.slice(m.index,end).replace(/\s+/g,' ').trim());
 }
 return {code,docs,guards,headers};
}
export function guardBlocks(source){return catalog(source).guards;}
const multiplicity=(xs,x)=>xs.filter(v=>v===x).length;
export function admitLeanPatch(p,source){
 requireFact(text(p?.summary,1200)&&Array.isArray(p?.edits)&&p.edits.length>0&&p.edits.length<=3,'INVALID_LEAN_PATCH');let patched=source;
 for(const e of p.edits){requireFact(text(e?.old,16000)&&text(e?.new,16000)&&patched.split(e.old).length===2,'AMBIGUOUS_LEAN_EDIT');patched=patched.replace(e.old,()=>e.new);}
 const before=catalog(source),after=catalog(patched);
 requireFact(!/\b(?:sorry|admit|axiom|unsafe|syntax|macro|elab|initialize|run_cmd|set_option)\b/.test(after.code),'UNSAFE_LEAN_PATCH');
 for(const block of before.guards)requireFact(multiplicity(after.guards,block)>=multiplicity(before.guards,block),'PROTECTED_GUARD_CHANGED');
 for(const doc of before.docs)requireFact(multiplicity(after.docs,doc)>=multiplicity(before.docs,doc),'ORIGINAL_CONTRACT_CHANGED');
 for(const h of before.headers)requireFact(after.headers.includes(h),'DECLARATION_HEADER_CHANGED');
 return patched;
}
export function assessGuard(r){
 if(r?.exit_code===0&&r.guard_false===false&&r.other_errors===false)return {execution:'GUARD_PASSED',meaning:'UNVERIFIED'};
 if(r?.exit_code===1&&r.guard_false===true&&r.other_errors===false)return {execution:'CANDIDATE_ASSERTION_FAILURE',meaning:'UNVERIFIED'};
 return {execution:'UNKNOWN',meaning:'UNVERIFIED'};
}

export function renderProbe(profile,expression){return 'import '+profile.module+'\nopen '+profile.namespace+'\ndef mathgraphCandidateProbe : Bool := ('+expression+')\n#guard mathgraphCandidateProbe\n';}
export function inspectArm(arm,{profile,plan,source}={}){
 const hash=s=>createHash('sha256').update(s).digest('hex');
 const ids=plan.tests.map(t=>t.id).sort();
 const exact=Array.isArray(arm?.probes)&&JSON.stringify(arm.probes.map(p=>p.id).sort())===JSON.stringify(ids);
 const sourceOK=arm?.source_sha256===hash(source);
 const controlsOK=assessGuard(arm?.controls?.pass).execution==='GUARD_PASSED'&&assessGuard(arm?.controls?.fail).execution==='CANDIDATE_ASSERTION_FAILURE';
 const baselineOK=arm?.build_exit===0&&arm?.repository_gate_exit===0;
 const rows=plan.tests.map(t=>{const p=arm?.probes?.find(p=>p.id===t.id);const byteOK=p?.test_file_sha256===hash(renderProbe(profile,t.expression));return {id:t.id,...(byteOK?assessGuard(p):{execution:'UNKNOWN',meaning:'UNVERIFIED'})};});
 return {complete:exact&&sourceOK&&controlsOK&&baselineOK&&rows.every(r=>r.execution!=='UNKNOWN'),rows,source_ok:sourceOK,baseline_ok:baselineOK,controls_ok:controlsOK};
}
