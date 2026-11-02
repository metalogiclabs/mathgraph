import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {runGenericSemantEq} from './generic-semanteq-run-v1.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');

// Unregistered Init-only statements; neither belongs to the two live mention adapters.
const reference={path:'TrustedArithmetic.lean',source:'import Init\ntheorem trusted (n : Nat) : n + 0 = n := by simp\n'};
const equivalent={path:'ProposedArithmetic.lean',source:'import Init\ntheorem candidate (n : Nat) : n = n := by rfl\n'};
const altered={path:'ProposedArithmetic.lean',source:'import Init\ntheorem candidate (n : Nat) : n = 0 := by sorry\n'};
const projectDir=process.env.MATHGRAPH_SEMANTEQ_PROJECT;

test('stale reference is rejected before spawning an external tool',async()=>{
 await assert.rejects(runGenericSemantEq({reference,candidate:equivalent,expectedReferenceSha:hash('stale'),projectDir:'/missing'}),/REFERENCE_SHA_MISMATCH/);
});
test('missing native checker preserves environment-unavailable instead of classifying mathematical meaning',async()=>{
 const r=await runGenericSemantEq({reference,candidate:equivalent,expectedReferenceSha:hash(reference.source),projectDir:'/nonexistent-semanteq'});
 assert.equal(r.execution_status,'ENVIRONMENT_UNAVAILABLE');
 assert.equal(r.formal_statement_relation,'UNKNOWN');
 assert.equal(r.intent_fidelity,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('native pinned SemantEq audits an unregistered equivalent pair with exact receipt hashes', {skip:!projectDir},async()=>{
 const r=await runGenericSemantEq({reference,candidate:equivalent,expectedReferenceSha:hash(reference.source),projectDir,timeoutMs:30000});
 assert.equal(r.execution_status,'EXECUTED');
 assert.equal(r.formal_statement_relation,'NATIVE_CERTIFIED_EQUIVALENT');
 assert.match(r.input_sha256,/^[a-f0-9]{64}$/);
 assert.match(r.output_sha256,/^[a-f0-9]{64}$/);
 assert.equal(r.native_exit_code,0);
 assert.equal(r.tool_git,'f92767000e14d11744580946980cf874324f5d19');
 assert.equal(r.lake_manifest_sha256,'cafd720ea1ea51f4c8653d5dca284ebcfc7ca16fdfb1a2a1499c71ad6408a666');
 assert.equal(r.lean_toolchain_sha256,'1098ca8368e0db12138f33b070187e1f6527984ae0451a587b20e3e661f96a76');
 assert.match(r.semanteq_executable_sha256,/^[a-f0-9]{64}$/);
 assert.equal(r.diagnostic_verdict,'DefEq');
 assert.equal(r.intent_fidelity,'UNKNOWN');
 assert.equal(r.candidate_source_build,'NOT_RUN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
test('native pinned SemantEq does not falsely certify an altered Nat equality', {skip:!projectDir},async()=>{
 const r=await runGenericSemantEq({reference,candidate:altered,expectedReferenceSha:hash(reference.source),projectDir,timeoutMs:30000});
 assert.equal(r.execution_status,'EXECUTED');
 assert.equal(r.formal_statement_relation,'UNKNOWN');
 assert.equal(r.intent_fidelity,'UNKNOWN');
 assert.equal(r.evidence_warrant,'UNKNOWN');
});
