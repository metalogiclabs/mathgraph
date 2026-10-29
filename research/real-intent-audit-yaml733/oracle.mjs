#!/usr/bin/env node
// MathGraph Check: first unfamiliar source-native PR audit (research only).
// Reporter-authored eemeli/yaml issue #733; AI-assisted PR #738.
// Independent finite oracle. Not owner-authenticated or production authority.
import {createHash} from 'node:crypto'
import {isDeepStrictEqual} from 'node:util'
import {resolve} from 'node:path'
import {pathToFileURL} from 'node:url'

const [root,phase]=process.argv.slice(2)
if (!root || !['BASE','HEAD'].includes(phase)) {
  process.stderr.write('Usage: node oracle.mjs <checkout> <BASE|HEAD>\n')
  process.exit(2)
}
const {parse,stringify}=await import(pathToFileURL(resolve(root,'dist/index.js')).href)
const texts=[
  ['s01','  lead\nx\n'],
  ['s02',' lead\nx'],
  ['s03','   x\n y\nz'],
  ['s04','  first\n  second\nthird'],
  ['s05',' lead\n\nend\n'],
  ['s06','    deep\nshallow'],
  ['s07',' lead\nmid\n\nend'],
  ['s08','  a\n b\nc\n']
]
const indents=[1,2,3,4,5,6,8]
const styles=['default','folded']
const contexts=[
  ['map',s=>({k:s})],
  ['nested',s=>({a:{k:s}})],
  ['list-map',s=>({a:[{k:s}]})],
  ['siblings',s=>({before:1,k:s,after:2})]
]
const matrix=[]
for(const [name,value] of texts)
 for(const indent of indents)
  for(const style of styles)
   for(const [shape,wrap] of contexts){
    const options={indent}
    if(style!=='default')options.blockQuote=style
    matrix.push({id:name+':indent'+indent+':'+style+':'+shape,
      group:'pr733-mapping-matrix',input:wrap(value),options})
   }
const issueCases=[
  {id:'issue733:map:indent1',input:{k:'  lead\nx\n'},options:{indent:1}},
  {id:'issue733:map:indent3',input:{k:'  lead\nx\n'},options:{indent:3}},
  {id:'issue733:map:indent4',input:{k:'  lead\nx\n'},options:{indent:4}},
  {id:'issue733:nested:indent4',input:{a:{k:'  lead\nx\n'}},options:{indent:4}},
  {id:'issue733:folded:indent4',input:{k:'  lead\nx'},options:{indent:4,blockQuote:'folded'}}
].map(x=>({...x,group:'reporter-exact'}))
const controls=[
 {id:'control:default-indent-map',input:{k:'  lead\nx\n'},options:{indent:2},group:'positive-control'},
 {id:'control:sequence-indent4',input:['  lead\nx\n'],options:{indent:4},group:'positive-control'}
]
const cases=[...issueCases,...controls,...matrix]
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex')
function check(t){
 let encoded=null
 try{
  encoded=stringify(t.input,t.options)
  const got=parse(encoded)
  if(isDeepStrictEqual(got,t.input))return{id:t.id,group:t.group,result:'PASS'}
  return{id:t.id,group:t.group,result:'FAIL',type:'VALUE_MISMATCH',
   want:JSON.stringify(t.input),got:JSON.stringify(got),yaml:encoded.slice(0,480)}
 }catch(e){
  return{id:t.id,group:t.group,result:'FAIL',type:'EXCEPTION',
   error:String(e?.message??e).slice(0,330),yaml:encoded?.slice(0,480)??null}
 }
}
const observations=cases.map(check)
const failures=observations.filter(x=>x.result==='FAIL')
const perGroup=Object.fromEntries(['reporter-exact','positive-control','pr733-mapping-matrix']
 .map(group=>[group,{total:observations.filter(x=>x.group===group).length,
 pass:observations.filter(x=>x.group===group&&x.result==='PASS').length,
 fail:observations.filter(x=>x.group===group&&x.result==='FAIL').length}]))
const outsideScope=check({id:'outside-scope:issue692-root-leading-space',
 input:'  a\n  b',options:{},group:'separate-root-issue692'})
const out={
 schema:'mathgraph-check-real-source-audit-yaml733-v0',
 phase,sourceRepository:'eemeli/yaml',issue:733,pr:738,
 reporterAuthoredOnly:true,ownerIntentAuthenticated:false,
 requirement:'For scoped multiline mapping strings with leading whitespace, parse(stringify(value,{indent,blockQuote?})) deep-equals value.',
 scope:'ISSUE_733_MAPPING_BLOCK_SCALAR_ROUNDTRIP_ONLY',
 permission:'ADVISORY_ONLY',
 casesSha256:sha(cases),total:cases.length,
 pass:cases.length-failures.length,fail:failures.length,
 perGroup,failures,outsideScopeIssue692:outsideScope
}
process.stdout.write(JSON.stringify(out,null,2)+'\n')
