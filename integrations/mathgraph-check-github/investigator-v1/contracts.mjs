// Model proposals are untrusted candidates. These contracts never certify intent.
const SHA=/^[a-f0-9]{40}$/,DIGEST=/^[a-f0-9]{64}$/;
const pathOK=p=>typeof p==='string'&&/^[A-Za-z0-9_./-]+\.py$/.test(p)&&!p.split('/').some(x=>['','..','.'].includes(x));
const implementation=p=>pathOK(p)&&!/(^|\/)(tests?|test_[^/]*|conftest\.py|setup\.py)(\/|$)/.test(p)&&!p.startsWith('.');
const requireFact=(b,msg)=>{if(!b)throw Error(msg);};
const text=(x,max)=>typeof x==='string'&&x.trim().length>0&&Buffer.byteLength(x)<=max;
function snapshotOK(s){requireFact(/^metalogiclabs\/[A-Za-z0-9_.-]+$/.test(s?.repository??'')&&SHA.test(s?.head_sha??'')&&SHA.test(s?.base_sha??'')&&Array.isArray(s.files),'INVALID_SUBJECT');}
export function admitPlan(p,s){
 snapshotOK(s);requireFact(text(p?.summary,1000)&&Array.isArray(p?.tests)&&p.tests.length>0&&p.tests.length<=3,'INVALID_PLAN');
 const seen=new Set();
 for(const t of p.tests){requireFact(/^[a-z][a-z0-9_]{0,39}$/.test(t?.id??'')&&!t.id.startsWith('control_')&&!seen.has(t.id),'INVALID_TEST_ID');seen.add(t.id);
 requireFact(implementation(t.source_path)&&s.files.some(f=>f.path===t.source_path)&&text(t.hypothesis,1600)&&text(t.contract,2000)&&text(t.code,20000),'INVALID_PROBE');}
 return structuredClone(p);
}
export function admitPatch(p,s){
 snapshotOK(s);requireFact(text(p?.summary,1000)&&Array.isArray(p?.files)&&p.files.length>0&&p.files.length<=2,'INVALID_PATCH');
 const seen=new Set();for(const f of p.files){requireFact(implementation(f?.path)&&s.files.some(x=>x.path===f.path)&&!seen.has(f.path)&&text(f.content,40000),'PATCH_SCOPE_REFUSED');seen.add(f.path);}
 return structuredClone(p);
}
export function assessProbe(r,{subjectSha,testDigest,testFileDigest,requireAssertions=true}={}){
 const unknown=reason=>({execution:'UNKNOWN',meaning:'UNVERIFIED',reason,permission:'ADVISORY_ONLY'});
 if(!SHA.test(subjectSha??'')||!DIGEST.test(testDigest??'')||r?.subject_sha!==subjectSha||r?.test_digest!==testDigest)return unknown('SOURCE_OR_TEST_MISMATCH');
 if(testFileDigest&&r?.test_file_sha256!==testFileDigest)return unknown('EXECUTED_TEST_BYTES_CHANGED');
 if(r.timeout!==false||![0,1].includes(r.exit_code)||!['tests','failures','errors','skipped'].every(k=>Number.isSafeInteger(r[k])&&r[k]>=0)||r.tests<1||r.errors>0||r.skipped>0||r.failures+r.errors+r.skipped>r.tests)return unknown('NATIVE_EXECUTION_INCOMPLETE');
 if(!Array.isArray(r.cases)||r.cases.length!==r.tests||new Set(r.cases.map(x=>x.id)).size!==r.tests||r.cases.some(x=>!x.id||!['passed','failed'].includes(x.status)||requireAssertions&&(!Number.isSafeInteger(x.assertions_reached)||x.assertions_reached<1)||x.status==='failed'&&x.exception!=='AssertionError'))return unknown('TEST_CASES_OR_ASSERTIONS_INCOMPLETE');
 if(r.cases.filter(x=>x.status==='failed').length!==r.failures)return unknown('CASE_COUNTER_MISMATCH');
 if((r.failures>0)!==(r.exit_code===1))return unknown('INCONSISTENT_NATIVE_RESULT');
 return {execution:r.failures?'CANDIDATE_FAILURE_REPRODUCED':'PROBE_PASSED',meaning:'UNVERIFIED',permission:'ADVISORY_ONLY'};
}
export function assessRepair({original,fixed,protectedBefore,protectedAfter}={},context={}){
 const unknown=reason=>({status:'UNKNOWN',meaning:'UNVERIFIED',reason,permission:'ADVISORY_ONLY'});
 if(assessProbe(original,context).execution!=='CANDIDATE_FAILURE_REPRODUCED'||assessProbe(fixed,context).execution!=='PROBE_PASSED')return unknown('REPAIR_NOT_REPRODUCED');
 if(!protectedBefore||!protectedAfter||protectedBefore.test_digest!==protectedAfter.test_digest)return unknown('PROTECTED_TESTS_CHANGED');
 if(JSON.stringify(original.cases.map(x=>x.id).sort())!==JSON.stringify(fixed.cases.map(x=>x.id).sort())||JSON.stringify(protectedBefore.cases?.map(x=>x.id).sort())!==JSON.stringify(protectedAfter.cases?.map(x=>x.id).sort()))return unknown('COLLECTED_TEST_CASES_CHANGED');
 const c={subjectSha:context.subjectSha,testDigest:protectedBefore.test_digest,requireAssertions:false};
 if(assessProbe(protectedBefore,c).execution==='UNKNOWN'||assessProbe(protectedAfter,c).execution!=='PROBE_PASSED')return unknown('PROTECTED_SUITE_NOT_GREEN');
 return {status:'REPAIR_VERIFIED_FOR_FROZEN_TESTS',meaning:'UNVERIFIED',permission:'ADVISORY_ONLY'};
}
