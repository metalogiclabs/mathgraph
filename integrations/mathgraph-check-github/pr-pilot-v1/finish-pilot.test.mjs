import test from 'node:test';import assert from 'node:assert/strict';import * as reports from './report.mjs';import * as transport from './producer-transport.mjs';import {readFileSync} from 'node:fs';
test('published snapshot carries the authenticated repair link',()=>{
 assert.equal(typeof reports.finalPublicationReport,'function');
 const a={status:'CANDIDATE_ASSERTION_FAILURE',repair_pr:'https://github.com/metalogiclabs/L4YAML/pull/29',repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'}};
 assert.deepEqual(reports.finalPublicationReport(a,{state:'PUBLISHED'}),a);
});
test('stale publication withdraws the downloadable report as well',()=>{
 assert.equal(typeof reports.finalPublicationReport,'function');
 const a={status:'CANDIDATE_ASSERTION_FAILURE',repair_pr:'https://github.com/metalogiclabs/L4YAML/pull/29'};
 const out=reports.finalPublicationReport(a,{state:'STALE'});assert.equal(out.status,'STALE');assert.equal(out.historical_status,a.status);assert.equal(out.repair_pr,undefined);assert.equal(a.status,'CANDIDATE_ASSERTION_FAILURE');
});
test('intake exposes a safe actionable ambiguity diagnostic',()=>{
 assert.equal(typeof transport.producerIntakeDiagnostic,'function');
 const d=transport.producerIntakeDiagnostic(Error('PRODUCER_LOCATOR_REQUIRED'));assert.equal(d.code,'PRODUCER_LOCATOR_REQUIRED');assert.match(d.message,/exactly one producer evidence link/i);
 const unsafe=transport.producerIntakeDiagnostic(Error('token sk-private value'));assert.equal(unsafe.code,'PRODUCER_EVIDENCE_UNAVAILABLE');assert.doesNotMatch(unsafe.message,/sk-private/);
});
test('check-only route skips repair and assesses the native artifact',()=>{
 const s=readFileSync(new URL('../../../.github/workflows/check-pr-pilot.yml',import.meta.url),'utf8'),job=s.split('\n  propose:')[1].split('\n  verify:')[0],assess=s.split('\n  assess:')[1].split('\n  repository-contract-native:')[0];
 assert.match(job,/needs: \[native, intake\]/);assert.match(job,/if: needs.intake.outputs.command == 'fix'/);assert.match(assess,/needs.intake.outputs.command == 'check' && 'pr-pilot-native'/);
});
