// Public paper-inspired FRETish source -> authentic FRET exporter. No Electron UI.
// [1,7] is a constructed challenger, never an alternative FRET output or authorized repair.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {resolve, join} from 'node:path';
import {mkdirSync, writeFileSync} from 'node:fs';

const require = createRequire(import.meta.url);
const fretRoot=resolve(process.env.ROCKET_FRET_ROOT || 'external/fret');
const output=resolve(process.env.ROCKET_OUTPUT || 'native-rocket-out');
const expected='whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST';
const actual='(BOOST -> (F[0,7] COAST))';
const constructed='(BOOST -> (F[1,7] COAST))';
const fretParser=require(join(fretRoot, 'fret-electron/app/parser/FretSemantics.js'));
const exporter=await import(pathToFileURL(join(fretRoot, 'fret-electron/support/r2u2Export.js')).href);
const result=fretParser.compile(expected);
if(result.parseErrors || !result.collectedSemantics || result.collectedSemantics.R2U2Code!==actual){
  throw Error('FRETISH_EXPORT_NOT_QUALIFIED: '+JSON.stringify(result).slice(0,1000));
}
mkdirSync(output,{recursive:true});
const signals=['BOOST','COAST'];
const inputVariables=signals.map(name=>({name,type:'bool'}));
function contract(formula){return {outputVariables:[],inputVariables,internalVariables:[],r2u2Assignments:[],properties:[{reqid:'ROCKET_RESPONSE',R2U2:formula}]};}
for(const [variant,formula] of [['source',actual],['challenger',constructed]]){
  const c=contract(formula);
  writeFileSync(join(output, variant+'.c2po'), exporter.renderC2POSpec(c));
  writeFileSync(join(output, variant+'.map'), exporter.renderC2POMap(c));
}
const scenarios=[['simultaneous',0,0],['next_tick',0,1],['no_coast',0,-1],['no_boost',-1,-1]];
for(const [name,boost,coast] of scenarios){
  const observations=Array.from({length:8},(_,time)=>({BOOST:Number(time===boost),COAST:Number(time===coast)}));
  const header=exporter.renderC2POCSVHeader(contract(actual));
  const text=header+observations.map(p=>signals.map(s=>p[s]).join(',')).join('\n')+'\n';
  writeFileSync(join(output,name+'.csv'),text);
  writeFileSync(join(output,name+'.json'),JSON.stringify(observations)+'\n');
}
writeFileSync(join(output,'source-declaration.json'),JSON.stringify({fretish:expected,actual_fret_export:actual,constructed_comparison:constructed,semantic_scope:'complete Boolean 8 ticks',operational_owner_authority:'UNKNOWN',repair_permission:'DENIED'},null,2)+'\n');
console.log(JSON.stringify({fretish:expected,actual_fret_export:actual,comparison:constructed,owner:'UNKNOWN'}));
