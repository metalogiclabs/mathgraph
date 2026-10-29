#!/usr/bin/env node
// V1 ADDITIONAL EXPLORATORY COHORT, frozen AFTER V0's 455/455 result.
// Tests YAML indentation indicators at the one-digit/10+ boundary.
// Not a blinded holdout. Separate from original V0 scoring.
import {createHash} from 'node:crypto'
import {isDeepStrictEqual} from 'node:util'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'

const [root,phase]=process.argv.slice(2)
if(!root||!['BASE','HEAD'].includes(phase))throw Error('USAGE root BASE|HEAD')
const {parse,stringify}=await import(pathToFileURL(resolve(root,'dist/index.js')).href)
const strings=[
 ['issue-exact','  lead\nx\n'],
 ['one-space',' lead\nx'],
 ['three-space','   deep\n shallow\n']
]
const indents=[7,8,9,10,11,12,16]
const styles=['default','folded']
const structures=[
 ['mapping',s=>({k:s})],
 ['nested',s=>({a:{k:s}})],
 ['list-map',s=>({items:[{k:s}]})],
 ['siblings',s=>({before:1,k:s,after:2})]
]
const cases=[]
for(const [textId,s] of strings)for(const indent of indents)
 for(const style of styles)for(const [context,wrap] of structures){
  const options={indent}
  if(style==='folded')options.blockQuote='folded'
  cases.push({id:textId+':'+indent+':'+style+':'+context,
   label:indent<=9?'single-digit-control':'multi-digit-hypothesis',
   input:wrap(s),options})
 }
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex')
const hash=sha(cases)
const observations=[]
for(const c of cases){
 let rendered
 try{
  rendered=stringify(c.input,c.options)
 }catch(e){
  // Explicit rejection of an unsupported option is NOT on its own proof
  // of invalid output. Preserve it as a distinct uncertainty category.
  observations.push({id:c.id,label:c.label,indent:c.options.indent,
   result:'OPTION_REJECTED_OR_STRINGIFY_ERROR',
   error:String(e?.message??e).slice(0,260)})
  continue
 }
 try{
  const got=parse(rendered)
  if(isDeepStrictEqual(got,c.input)){
   observations.push({id:c.id,label:c.label,indent:c.options.indent,result:'PASS'})
  }else{
   observations.push({id:c.id,label:c.label,indent:c.options.indent,
    result:'VALUE_MISMATCH',want:JSON.stringify(c.input),
    got:JSON.stringify(got),yaml:rendered.slice(0,620)})
  }
 }catch(e){
  observations.push({id:c.id,label:c.label,indent:c.options.indent,
   result:'UNPARSEABLE_SUCCESSFUL_STRINGIFY',
   error:String(e?.message??e).slice(0,350),yaml:rendered.slice(0,620)})
 }
}
const invalid=['VALUE_MISMATCH','UNPARSEABLE_SUCCESSFUL_STRINGIFY']
const summary=Object.fromEntries(['single-digit-control','multi-digit-hypothesis'].map(label=>{
 const group=observations.filter(x=>x.label===label)
 return[label,{total:group.length,pass:group.filter(x=>x.result==='PASS').length,
  invalidOutput:group.filter(x=>invalid.includes(x.result)).length,
  optionRejected:group.filter(x=>x.result==='OPTION_REJECTED_OR_STRINGIFY_ERROR').length}]
}))
const findings=observations.filter(x=>x.result!=='PASS')
const out={schema:'mathgraph-check-real-yaml733-v1-posthoc-edge',
 phase,source:'eemeli/yaml#738 issue#733',
 scope:'NUMERIC_INDENT_OPTIONS_7_8_9_10_11_12_16_MAPPING_LEADING_SPACE',
 parentResult:'V0_455_CASES_REMOVED_FROM_EDGE_SCORE',
 cohortBlinding:'NOT_BLINDED_PRESPECIFIED_AFTER_V0',
 permission:'ADVISORY_ONLY',intentVerification:'NOT_ESTABLISHED',
 reference:'YAML 1.2.2 section 8.1.1.1 block indentation indicator is one ASCII digit 1-9',
 casesSha256:hash,total:cases.length,
 pass:observations.filter(x=>x.result==='PASS').length,
 invalidOutput:observations.filter(x=>invalid.includes(x.result)).length,
 optionRejected:observations.filter(x=>x.result==='OPTION_REJECTED_OR_STRINGIFY_ERROR').length,
 byWidth:summary,
 counterexamples:findings}
process.stdout.write(JSON.stringify(out,null,2)+'\n')
