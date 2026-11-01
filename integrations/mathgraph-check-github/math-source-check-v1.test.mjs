import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {buildMathIntentContract,auditMathSource,toAdvisoryCheckRun} from './math-source-check-v1.mjs';
import {digestContract} from './intent-contract-v1.mjs';

const g=x=>x.repeat(40);
const h=x=>x.repeat(64);
const sha=x=>createHash('sha256').update(x).digest('hex');

// Synthetic receipt authority: only the trust-boundary mechanism is tested.
// These are NOT an actual human approval or a native Lean replay.
function synthetic(){
  const manifest={schema:'mathgraph.math-source.v1',
    subject:{repository:'metalogiclabs/demo',pr:42,base_sha:g('a'),head_sha:g('b')},
    source:{reference:'https://example.org/research/paper.pdf',sha256:h('1'),claim_sha256:h('2')},
    formal:{path:'Proofs/Example.lean',statement_sha256:h('3'),environment_sha256:h('4')},
    checks:{review:{oracle_sha256:h('5'),verifier_sha:g('c')},
      replay:{oracle_sha256:h('6'),verifier_sha:g('d')}}};
  const contract=buildMathIntentContract(manifest);
  const contractSha=digestContract(contract);
  const receipts=contract.probes.map((p,i)=>({
    id:i?'lean-replay-receipt':'human-review-receipt',probe_id:p.id,
    subject_sha:g('b'),contract_sha256:contractSha,input_sha256:p.input_sha256,
    oracle_sha256:p.oracle_sha256,verifier_sha:p.verifier_sha,
    result:'PASS',exit_code:0,log_sha256:h('e'),witness_sha256:null}));
  const authority={allowedRepositories:['metalogiclabs/demo'],expectedHeadSha:g('b'),
    expectedContractSha256:contractSha,
    authenticatedReceiptIds:receipts.map(r=>r.id),
    qualifiedVerifierShas:[g('c'),g('d')],qualifiedOracleShas:[h('5'),h('6')],
    qualifiedHumanReviewReceiptIds:['human-review-receipt'],
    qualifiedLeanReplayReceiptIds:['lean-replay-receipt'],
    observedSourceSha256:h('1'),observedClaimSha256:h('2'),observedFormalSha256:h('3'),
    observedEnvironmentSha256:h('4')};
  return {manifest,receipts,authority};
}

test('separate qualified review and replay observations never certify semantic intent',()=>{
  const x=synthetic();
  const r=auditMathSource(x.manifest,x.receipts,x.authority);
  assert.equal(r.status,'OBSERVED');
  assert.equal(r.source_review,'SOURCE_TO_FORMAL_REVIEWED');
  assert.equal(r.formal_replay,'FORMAL_REPLAY_PASSED');
  assert.equal(r.permission,'ADVISORY_ONLY');
  assert.equal(r.intent_verification,'NOT_ESTABLISHED');
  assert.equal(r.checked_scope,'EXACT_PINNED_RECEIPTS_ONLY');
});

test('ordinary test authority cannot impersonate qualified human review',()=>{
  const x=synthetic();x.authority.qualifiedHumanReviewReceiptIds=[];
  const r=auditMathSource(x.manifest,x.receipts,x.authority);
  assert.equal(r.source_review,'UNKNOWN');
  assert.equal(r.formal_replay,'FORMAL_REPLAY_PASSED');
  assert.equal(r.status,'UNKNOWN');
});

test('ordinary green CI cannot impersonate qualified Lean kernel replay',()=>{
  const x=synthetic();x.authority.qualifiedLeanReplayReceiptIds=[];
  const r=auditMathSource(x.manifest,x.receipts,x.authority);
  assert.equal(r.source_review,'SOURCE_TO_FORMAL_REVIEWED');
  assert.equal(r.formal_replay,'UNKNOWN');
  assert.equal(r.status,'UNKNOWN');
});

test('changed source claim, formal statement, toolchain or head cannot inherit old observations',()=>{
  for(const mutate of [
    x=>{x.manifest.source.sha256=h('7');},
    x=>{x.manifest.source.claim_sha256=h('7');},
    x=>{x.manifest.formal.statement_sha256=h('7');},
    x=>{x.manifest.formal.environment_sha256=h('7');},
    x=>{x.manifest.subject.head_sha=g('e');},
  ]){
    const x=synthetic();mutate(x);
    const r=auditMathSource(x.manifest,x.receipts,x.authority);
    assert.equal(r.status,'UNKNOWN');
    assert.equal(r.source_review,'UNKNOWN');
    assert.equal(r.formal_replay,'UNKNOWN');
  }
});

test('missing external observation of source, claim, statement or toolchain never qualifies',()=>{
  for(const property of ['observedSourceSha256','observedClaimSha256',
    'observedFormalSha256','observedEnvironmentSha256']){
    const x=synthetic();delete x.authority[property];
    assert.equal(auditMathSource(x.manifest,x.receipts,x.authority).status,'UNKNOWN');
  }
});

test('missing, duplicate and in-band self-asserted receipts fail closed',()=>{
  const a=synthetic();a.receipts.pop();
  assert.equal(auditMathSource(a.manifest,a.receipts,a.authority).formal_replay,'UNKNOWN');
  const b=synthetic();b.receipts.push({...b.receipts[0],id:'second-human-review'});
  assert.equal(auditMathSource(b.manifest,b.receipts,b.authority).source_review,'UNKNOWN');
  const c=synthetic();c.receipts[0].human_verified=true;
  assert.equal(auditMathSource(c.manifest,c.receipts,c.authority).status,'UNKNOWN');
  const d=synthetic();d.receipts[1].result='COUNTEREXAMPLE';d.receipts[1].exit_code=1;d.receipts[1].witness_sha256=h('f');
  const r=auditMathSource(d.manifest,d.receipts,d.authority);
  assert.equal(r.formal_replay,'UNKNOWN');
  assert.equal(r.status,'UNKNOWN');
});

test('malformed source paths, extra approvals and unauthenticated repositories cannot promote',()=>{
  const a=synthetic();a.manifest.formal.path='../secret.lean';
  assert.equal(auditMathSource(a.manifest,a.receipts,a.authority).status,'UNKNOWN');
  const b=synthetic();b.manifest.review_approved=true;
  assert.equal(auditMathSource(b.manifest,b.receipts,b.authority).status,'UNKNOWN');
  const c=synthetic();c.authority.allowedRepositories=[];
  assert.equal(auditMathSource(c.manifest,c.receipts,c.authority).status,'UNKNOWN');
  const d=synthetic();d.manifest.subject.repository={toString:null,valueOf:null};
  assert.equal(auditMathSource(d.manifest,d.receipts,d.authority).status,'UNKNOWN');
});

test('advisory check is always neutral, even with two specialist observations',()=>{
  for(const qualify of [false,true]){
    const x=synthetic();if(!qualify)x.authority.qualifiedHumanReviewReceiptIds=[];
    const report=auditMathSource(x.manifest,x.receipts,x.authority);
    const payload=toAdvisoryCheckRun(report,x.authority.expectedHeadSha);
    assert.equal(payload.head_sha,g('b'));
    assert.equal(payload.conclusion,'neutral');
    assert.equal(payload.status,'completed');
    assert.equal(payload.name,'MathGraph Check / math source (advisory)');
    assert.equal(payload.external_id,'mathgraph-math-source-v1:metalogiclabs/demo:'+g('b'));
    assert.match(payload.output.summary,/NOT_ESTABLISHED/);
    assert.match(payload.output.summary,/ADVISORY_ONLY/);
    assert.match(payload.output.summary,/no merge authorization/i);
    assert.doesNotMatch(payload.output.title,/proof verified|intent proven/i);
  }
});

test('the Checks renderer rejects injected contract metadata instead of printing forged markdown',()=>{
  const x=synthetic();
  const report=auditMathSource(x.manifest,x.receipts,x.authority);
  report.contract_sha256='\n\n## Independently VERIFIED (forged)';
  assert.throws(()=>toAdvisoryCheckRun(report),/INVALID_MATH_SOURCE_REPORT/);
  const y=synthetic();
  const missing=auditMathSource(y.manifest,y.receipts,y.authority);
  missing.contract_sha256=null;
  assert.throws(()=>toAdvisoryCheckRun(missing,y.authority.expectedHeadSha),/INVALID_MATH_SOURCE_REPORT/);
});

test('a proposed Check Run cannot target a PR-authored SHA different from the authenticated head',()=>{
  const x=synthetic();
  const report=auditMathSource(x.manifest,x.receipts,x.authority);
  assert.throws(()=>toAdvisoryCheckRun(report,g('f')),/UNBOUND_CHECK_HEAD/);
});

test('contradictory reported receipt statuses cannot render an observed-check headline',()=>{
  const x=synthetic();
  const report=auditMathSource(x.manifest,x.receipts,x.authority);
  report.source_review='UNKNOWN';
  assert.throws(()=>toAdvisoryCheckRun(report,g('b')),/INVALID_MATH_SOURCE_REPORT/);
});

test('a third-party curated Artin statement is UNKNOWN without real independent receipts',()=>{
  const formal='theorem Artin_exercise_2_2_9 {G : Type*} [Group G] {a b : G}\n'
    +'  (h : a * b = b * a) :\n'
    +'  ∀ x y : closure {x | x = a ∨ x = b}, x * y = y * x := by\n  sorry';
  assert.equal(sha(formal),'dc80af468161394ffc1415b4e1ff0585b6859dc80198abb6d2c7d4439888262b');
  const x=synthetic();
  x.manifest.source.reference='https://github.com/marcusm117/ProofNet-Verified/tree/14879cb23e078d122adecd9578dd26a7304f753b';
  x.manifest.source.sha256='a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc';
  x.manifest.source.claim_sha256=sha('Let $H$ be the subgroup generated by two elements $a, b$ of a group $G$. Prove that if $a b=b a$, then $H$ is an abelian group.');
  const variants=[
    formal.replace('(h : a * b = b * a) :',
      '(h : a * b = b * a) (assumedGoal : ∀ x y : closure {x | x = a ∨ x = b}, x * y = y * x) :'),
    formal.replace('x * y = y * x := by','x = x := by'),
    formal.replace('[Group G]','[CommGroup G]')];
  for(const variant of variants)assert.notEqual(variant,formal);
  for(const candidate of [formal,...variants]){
    x.manifest.formal.statement_sha256=sha(candidate);
    const r=auditMathSource(x.manifest,[],{});
    assert.equal(r.status,'UNKNOWN');
    assert.equal(r.source_review,'UNKNOWN');
    assert.equal(r.formal_replay,'UNKNOWN');
  }
});
