// First-party operator-only native observation of an *actual* compiled theorem
// reference after removing dead let/have bindings. This is not a relevance,
// proof-necessity, source-intent, or independent-warrant oracle.

const NAME=/^[A-Za-z_][A-Za-z0-9_'.]{0,150}$/;
const MARKER=/^MATHGRAPH_CANDIDATE_REFERENCE_[0-9a-f]{12,40}$/i;
const STANDARD_AXIOMS=new Set(['propext','Classical.choice','Quot.sound']);

export function buildCandidateProofReferenceAudit({candidateName,consumerName,marker}){
 if(!NAME.test(candidateName??'')||!NAME.test(consumerName??''))throw Error('INVALID_DECLARATION_NAME');
 if(!MARKER.test(marker??''))throw Error('INVALID_MARKER');
 return `import Lean
import Consumer
open Lean Elab Command Meta
run_cmd do
  let env ← getEnv
  let some candidateInfo := env.find? \`${candidateName} | throwError "CANDIDATE_DECLARATION_MISSING"
  let some consumerInfo := env.find? \`${consumerName} | throwError "CONSUMER_DECLARATION_MISSING"
  let .thmInfo _candidate := candidateInfo | throwError "DECLARATION_NOT_THEOREM"
  let .thmInfo consumer := consumerInfo | throwError "DECLARATION_NOT_THEOREM"
  let some candidateIdx := env.getModuleIdxFor? \`${candidateName} | throwError "DECLARATION_WRONG_MODULE"
  let some consumerIdx := env.getModuleIdxFor? \`${consumerName} | throwError "DECLARATION_WRONG_MODULE"
  let some candidateMod := env.header.modules[candidateIdx]? | throwError "DECLARATION_WRONG_MODULE"
  let some consumerMod := env.header.modules[consumerIdx]? | throwError "DECLARATION_WRONG_MODULE"
  unless candidateMod.module == \`Candidate && consumerMod.module == \`Consumer do
    throwError "DECLARATION_WRONG_MODULE"
  let reduced ← liftTermElabM do Meta.zetaReduce consumer.value
  let found ← liftIO <| IO.mkRef false
  reduced.forEach fun e => do
    if e.isConstOf \`${candidateName} then found.set true
  let direct ← found.get
  logInfo m!"${marker}={direct}"
#print axioms ${candidateName}
#print axioms ${consumerName}
`;
}

export function parseCandidateProofReferenceMarker(stdout,marker){
 if(typeof stdout!=='string'||!MARKER.test(marker??''))return null;
 const lines=stdout.split(/\r?\n/).map(x=>x.trim()).filter(x=>x.includes('MATHGRAPH_CANDIDATE_REFERENCE_'));
 if(lines.length!==1)return null;
 if(lines[0]===`${marker}=true`)return true;
 if(lines[0]===`${marker}=false`)return false;
 return null;
}

export function classifyCandidateProofReference({compiled,record,candidateAxioms,consumerAxioms}={}){
 if(compiled!==true||record!==true)return 'UNKNOWN';
 const clean=axioms=>Array.isArray(axioms)&&axioms.every(a=>STANDARD_AXIOMS.has(a));
 return clean(candidateAxioms)&&clean(consumerAxioms)?'NATIVE_ZETA_NORMALIZED_DIRECT_REFERENCE':'UNKNOWN';
}
