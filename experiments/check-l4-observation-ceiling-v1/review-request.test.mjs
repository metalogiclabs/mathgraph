import test from 'node:test';
import assert from 'node:assert/strict';
import {checkProjectionClaim,digestProjectionClaim} from '../../integrations/mathgraph-check-github/projection-claim-v1.mjs';
import {hashFiniteUniverse} from '../../integrations/mathgraph-check-github/finite-warrant-quotient-v1.mjs';
import {makeIndependentL4ReviewRequest} from './review-request.mjs';

test('review request keeps normative source, exact inputs, and proof source distinct',()=>{
 const packet=makeIndependentL4ReviewRequest();
 assert.equal(packet.schema,'mathgraph.independent-l4-review-request.v1');
 assert.equal(packet.status,'CANDIDATE');
 assert.equal(packet.terminal_form,null);
 assert.equal(packet.reviewer_decision,'NOT_OBTAINED');
 assert.equal(packet.normative_requirement.review_status,'PENDING_INDEPENDENT_REVIEW');
 assert.equal(packet.normative_requirement.source,'https://yaml.org/spec/1.2.2/');
 assert.equal(packet.source.repository,'metalogiclabs/L4YAML');
 assert.equal(packet.source.frozen_production_sha,'64795a8db28ccfdae85082c93b6453001ae9d3e4');
 assert.equal(packet.proof.repository,'metalogiclabs/L4YAML');
 assert.equal(packet.proof.commit,'b882e5b298b30b094f4154da7108a45e196cfcd3');
 assert.notEqual(packet.proof.commit,packet.source.frozen_production_sha);
 assert.deepEqual(packet.separating_witness.map(w=>w.input_utf8_hex),['2361','2301']);
 assert.deepEqual(packet.separating_witness.map(w=>w.parser_success),[true,true]);
 assert.deepEqual(packet.separating_witness.map(w=>w.no_raw_soh),[true,false]);
 assert.equal(packet.proof.proof_replay,'NOT_PERFORMED');
 assert.equal(packet.proof.artifact_sha256,'f60e48bc7a9df0e618c9ce6398644a9bbc5da4d4022010528f662f0566a536f3');
 assert.equal(packet.live_admission.status,'NOT_AUTHORIZED');
 assert.equal(packet.live_admission.reason,'REVIEWED_SOURCE_NOT_CURRENT_MATHGRAPH_PR_HEAD');
 assert.equal(packet.complete_yaml_grammar,'UNKNOWN');
 assert.deepEqual(packet.review_tasks.map(t=>t.status),Array(4).fill('PENDING'));
});

test('historical L4YAML pair cannot be relabeled as evidence on a MathGraph PR',()=>{
 const packet=makeIndependentL4ReviewRequest();
 const subject={repository:'metalogiclabs/mathgraph',pr:273,
  base_sha:'a'.repeat(40),head_sha:'b'.repeat(40)};
 const claim={id:'L4-NORMATIVE-RUNTIME',statement:packet.claim,
  observation:packet.observation,universe:packet.finite_universe};
 const authority={allowedRepositories:[subject.repository],
  expectedHeadSha:subject.head_sha,
  expectedContractSha256:digestProjectionClaim(subject,claim),
  expectedUniverseSha256:hashFiniteUniverse(claim.universe),
  allowedSourceShas:[subject.head_sha]};
 const result=checkProjectionClaim(subject,claim,authority);
 assert.equal(result.status,'UNKNOWN');
 assert.equal(result.reason,'WITNESS_NOT_BOUND_TO_CURRENT_PR_HEAD');
 assert.equal(result.terminal_form,null);
 assert.equal(result.witness,null);
});

test('review request contains testable questions, not preapproved review or signing material',()=>{
 const packet=makeIndependentL4ReviewRequest();
 assert.deepEqual(packet.review_tasks.map(t=>t.id),[
  'NORMATIVE_REQUIREMENT','FROZEN_RUNTIME_BEHAVIOR',
  'LEAN_THEOREM_AND_CONTROLS','CLAIM_TO_EVIDENCE_FIDELITY']);
 for(const task of packet.review_tasks){
  assert.ok(task.question.length>40);
  assert.ok(task.method.length>40);
 }
 assert.equal(packet.reviewer_signature,'NOT_ISSUED');
 assert.ok(!JSON.stringify(packet).includes('PRIVATE KEY'));
 assert.equal(packet.permission,'ADVISORY_ONLY');
});
