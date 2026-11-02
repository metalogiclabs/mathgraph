// Native qualification of a published exercise, not an upstream defect report.
// Target: ProofNet-Verified 14879cb23e078d122adecd9578dd26a7304f753b,
// data/archive/proofnet-verified-4.28/proofnet-1.lean, Artin exercise 2.2.9.
// The reference/gold proof is not read. The repair uses Mathlib's independently
// documented closureCommGroupOfComm lemma under the original Group hypothesis.
import {createHash} from 'node:crypto';
import {writeFile,mkdir,readFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const prefix='import Mathlib.GroupTheory.Subgroup.Centralizer\n\nopen Subgroup\n\n';
export const artinTarget=`theorem Artin_exercise_2_2_9 {G : Type*} [Group G] {a b : G}
  (h : a * b = b * a) :
  ∀ x y : closure {x | x = a ∨ x = b}, x * y = y * x`;
export const artinStrongSource=prefix+artinTarget.replace('[Group G]','[CommGroup G]')+' := by\n  intro x y\n  exact mul_comm x y\n';
export const artinRepairSource=prefix+artinTarget+` := by
  letI : CommGroup (closure {x : G | x = a ∨ x = b}) :=
    closureCommGroupOfComm (by
      intro x hx y hy
      rcases hx with rfl | rfl <;> rcases hy with rfl | rfl
      · rfl
      · exact h
      · exact h.symm
      · rfl)
  intro x y
  exact mul_comm x y
`;
export const artinConsumer='import Candidate\n\nopen Subgroup\n\n'+artinTarget.replace('theorem Artin_exercise_2_2_9','example')+' := Artin_exercise_2_2_9 h\n#print axioms Artin_exercise_2_2_9\n';
export function bindPublishedArtin(source,{target=artinTarget}={}){
 const hash=createHash('sha256').update(source).digest('hex');
 if(hash!=='a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc')throw Error('PUBLISHED_SOURCE_CHANGED');
 const start=source.indexOf('theorem Artin_exercise_2_2_9');
 const declaration=source.slice(start).match(/^([\s\S]*?) := by\s+sorry\s*$/);
 const normalize=x=>x.trim().replace(/\s+/g,' ');
 if(start<0||!declaration||normalize(declaration[1])!==normalize(target))throw Error('PUBLISHED_TARGET_MISMATCH');
 return {repository:'marcusm117/ProofNet-Verified',commit:'14879cb23e078d122adecd9578dd26a7304f753b',path:'data/archive/proofnet-verified-4.28/proofnet-1.lean',source_sha256:hash,formal_statement_sha256:createHash('sha256').update(normalize(target)).digest('hex'),informal_equivalence:'NOT_CERTIFIED'};
}
export async function nativeArtin({source,run,publishedSource}){
 const published=bindPublishedArtin(publishedSource);
 if(![artinStrongSource,artinRepairSource].includes(source))throw Error('UNSUPPORTED_ARTIN_SOURCE');
 const binding={published,source_sha256:createHash('sha256').update(source).digest('hex'),target_sha256:createHash('sha256').update(artinTarget).digest('hex')};
 const candidate=await run('Candidate',source);
 if(candidate.code!==0)return {...binding,status:'UNKNOWN',source_compiles:false,original_claim_satisfied:false,axioms:null};
 const consumer=await run('Consumer',artinConsumer);
 const audit=consumer.output.match(/^'Artin_exercise_2_2_9' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$/m);
 const axioms=audit?(audit[1]?audit[1].split(',').map(x=>x.trim()):[]):null;
 const clean=consumer.code===0&&axioms!==null&&axioms.every(x=>['propext','Classical.choice','Quot.sound'].includes(x))&&new Set(axioms).size===axioms.length;
 return {...binding,status:clean?'ORIGINAL_TARGET_VERIFIED':consumer.code===1&&/(?:failed to synthesize[\s\S]*CommGroup|type mismatch)/i.test(consumer.output)?'CLAIM_NOT_ESTABLISHED':'UNKNOWN',source_compiles:true,original_claim_satisfied:clean,axioms:clean?axioms:null};
}
export async function qualifyArtin({run,publishedSource}){
 const published=bindPublishedArtin(publishedSource);const trace=[];
 const invoke=async(name,source)=>{const r=await run(name,source);trace.push({unit:name,code:r.code,output:r.output.slice(0,12000)});return r;};
 const strong=await invoke('StrongCandidate',artinStrongSource);
 if(strong.code!==0)return {status:'UNKNOWN',published,trace};
 const rejected=await invoke('StrongConsumer',artinConsumer);
 if(rejected.code!==1||!/(?:failed to synthesize[\s\S]*CommGroup|type mismatch)/i.test(rejected.output))return {status:'UNKNOWN',published,trace};
 const repair=await invoke('RepairCandidate',artinRepairSource);
 if(repair.code!==0)return {status:'UNKNOWN',published,trace};
 const accepted=await invoke('RepairConsumer',artinConsumer);
 const audit=accepted.output.match(/^'Artin_exercise_2_2_9' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*$/m);
 const axioms=audit?(audit[1]?audit[1].split(',').map(x=>x.trim()):[]):null;
 const clean=accepted.code===0&&axioms!==null&&axioms.every(x=>['propext','Classical.choice','Quot.sound'].includes(x))&&new Set(axioms).size===axioms.length;
 return {status:clean?'ARTIN_CONTROLS_VERIFIED':'UNKNOWN',published,axioms:clean?axioms:null,target_sha256:createHash('sha256').update(artinTarget).digest('hex'),repair_sha256:createHash('sha256').update(artinRepairSource).digest('hex'),scope:'PUBLISHED_ARTIN_EXERCISE_WITH_INJECTED_STRONG_HYPOTHESIS_CONTROL',trace};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const directory=resolve(process.argv[2]);const exec=promisify(execFile);await mkdir(join(directory,'.lake/build/lib/lean'),{recursive:true});
 const run=async(name,source)=>{
  const candidate=name.endsWith('Candidate');const file=candidate?'Candidate.lean':'Consumer.lean';await writeFile(join(directory,file),source);
  const args=['env','lean',...(candidate?['-o','.lake/build/lib/lean/Candidate.olean']:[]),file];
  try{const r=await exec('lake',args,{cwd:directory,timeout:120000,maxBuffer:262144,env:{PATH:process.env.PATH,HOME:process.env.HOME,LEAN_NUM_THREADS:'1'}});return {code:0,output:r.stdout+r.stderr};}
  catch(e){if(e.code===1)return {code:1,output:String(e.stdout??'')+String(e.stderr??'')};throw Error('ARTIN_NATIVE_EXECUTION_INCOMPLETE');}
 };
 const publishedSource=await readFile(join(directory,'published-exercise.lean.txt'),'utf8');
 const result=await qualifyArtin({run,publishedSource});await writeFile(join(directory,'artin-mention-native-receipt.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));if(result.status!=='ARTIN_CONTROLS_VERIFIED')process.exitCode=1;
}
