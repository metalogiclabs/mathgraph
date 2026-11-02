// Explicit, trusted demonstration adapters. PR contents never select a toolchain,
// arbitrary theorem, executable script, or verification policy.
import {readFileSync} from 'node:fs';
import {brokenSource,repairedSource,nativeDemo,demoPath,originalTarget} from './mention-native-demo-v1.mjs';
import {artinTarget,artinStrongSource,artinRepairSource,nativeArtin} from './mention-artin-control-v1.mjs';
const publishedSource=readFileSync(new URL('./fixtures/proofnet-artin-statement-v1.lean',import.meta.url),'utf8');
const list={id:'list-reversal',path:demoPath,target:originalTarget,brokenSource,needsMathlib:false,accepts:source=>source===brokenSource||['by simp','by simpa','by exact List.length_reverse'].some(p=>source===repairedSource(p)),verify:nativeDemo};
const artin={id:'artin-generators',path:'mathgraph-demo/ArtinGenerators.lean',target:artinTarget,brokenSource:artinStrongSource,repair:artinRepairSource,needsMathlib:true,accepts:source=>[artinStrongSource,artinRepairSource].includes(source),verify:args=>nativeArtin({...args,publishedSource})};
export function selectDemoCase(files){
 if(!Array.isArray(files)||files.length>=100)throw Error('DEMO_CASE_WINDOW_INCOMPLETE');
 const selected=[list,artin].filter(c=>files.some(f=>f.filename===c.path));
 if(selected.length!==1)throw Error('DEMO_CASE_UNSUPPORTED_OR_AMBIGUOUS');return selected[0];
}
