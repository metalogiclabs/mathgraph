/** Small fail-closed parser for Lean's `#print axioms` on a single theorem. */
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';

const ALLOWED=new Set(['propext','Classical.choice','Quot.sound']);
const LINE=/^'Artin_exercise_2_2_9' depends on axioms: \[([^\]\n]*)\]$/gmu;

export function auditArtinAxioms(output){
  if(typeof output!=='string'||output.length>65536)throw Error('INVALID_LEAN_OUTPUT');
  const found=[...output.matchAll(LINE)];
  if(found.length!==1)throw Error('EXACT_AXIOM_REPORT_REQUIRED');
  const list=found[0][1].trim();
  const axioms=list?list.split(',').map(x=>x.trim()):[];
  if(axioms.some(x=>!ALLOWED.has(x))||new Set(axioms).size!==axioms.length)
    throw Error('UNAPPROVED_OR_DUPLICATE_AXIOM');
  return {schema:'mathgraph.artin-axiom-audit.v1',
    theorem:'Artin_exercise_2_2_9',allowed_axioms:[...ALLOWED],observed_axioms:axioms,
    verdict:'AXIOMS_WITHIN_CLASSICAL_LEAN_ALLOWLIST',
    source_review:'UNKNOWN',intent_verification:'NOT_ESTABLISHED',
    permission:'ADVISORY_ONLY'};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  try{process.stdout.write(JSON.stringify(auditArtinAxioms(readFileSync(0,'utf8')),null,2)+'\n');}
  catch(error){process.stderr.write(String(error.message)+'\n');process.exitCode=1;}
}
