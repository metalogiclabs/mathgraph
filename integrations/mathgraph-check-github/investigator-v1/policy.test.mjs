import test from 'node:test';import assert from 'node:assert/strict';import {subjectPolicy} from './policy.mjs';
test('explicit unfamiliar PR is data, not a registered theorem',()=>{const p=subjectPolicy({MATHGRAPH_PR_NUMBER:'17'});assert.equal(p.requested_pr,17);assert.equal(p.source_repository,'Stanford-NavLab/gnss_lib_py');});
test('owned fork source is allowed for controlled qualification',()=>assert.equal(subjectPolicy({MATHGRAPH_SOURCE_REPOSITORY:'metalogiclabs/gnss_lib_py',MATHGRAPH_PR_NUMBER:'1'}).source_repository,'metalogiclabs/gnss_lib_py'));
for(const value of ['../repo','attacker/repo','https://example.com/repo'])test('unreviewed repository is refused: '+value,()=>assert.throws(()=>subjectPolicy({MATHGRAPH_SOURCE_REPOSITORY:value})));
for(const value of ['0','-1','17; echo hi','not-a-number'])test('invalid PR selector refused: '+value,()=>assert.throws(()=>subjectPolicy({MATHGRAPH_PR_NUMBER:value})));
