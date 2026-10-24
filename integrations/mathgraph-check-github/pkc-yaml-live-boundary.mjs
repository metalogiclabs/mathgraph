// Exact-byte ZIP-to-report binding, advisory only; no Check API writes.
import {createHash} from "node:crypto";
import {inflateRawSync} from "node:zlib";
import {gatePKCYamlPublication} from "./pkc-yaml-publisher-gate.mjs";
export const PIN=Object.freeze({repo:"metalogiclabs/mathgraph",
 artifact:12171240289,run:39218904172,
 digest:"2bbd575f1d93759a734fa459f4f48be599411a44b91d0627b397d02d4f8b98f9"});
export function checkArtifactBytes(bytes,meta) {
 if(!(bytes instanceof Uint8Array))return false;
 return createHash("sha256").update(bytes).digest("hex")===PIN.digest &&
 meta?.id===PIN.artifact && meta?.digest==="sha256:"+PIN.digest &&
 meta?.expired===false && meta?.workflow_run?.id===PIN.run;
}
export function extractBoundReport(bytes) {
 const b=Buffer.from(bytes); if(b.length>2_000_000)throw Error("ZIP_OVERSIZE");
 const end=b.lastIndexOf(Buffer.from([0x50,0x4b,0x05,0x06]));
 if(end<0 || end+22>b.length)throw Error("ZIP_DIRECTORY_MISSING");
 const count=b.readUInt16LE(end+10),size=b.readUInt32LE(end+12),off=b.readUInt32LE(end+16);
 if(count!==2 || size>8192 || off+size>end)throw Error("ZIP_DIRECTORY_SCOPE");
 let pos=off,report=null,seen=new Set();
 for(let i=0;i<count;i++){
  if(b.readUInt32LE(pos)!==0x02014b50)throw Error("ZIP_ENTRY");
  const method=b.readUInt16LE(pos+10),packed=b.readUInt32LE(pos+20);
  const unpacked=b.readUInt32LE(pos+24),nameLen=b.readUInt16LE(pos+28);
  const extra=b.readUInt16LE(pos+30),comment=b.readUInt16LE(pos+32);
  const local=b.readUInt32LE(pos+42);
  const name=b.subarray(pos+46,pos+46+nameLen).toString("utf8");
  if(seen.has(name)||!["shadow-report.json","check-payload.json"].includes(name) ||
     packed>100000 || unpacked>100000)throw Error("ZIP_FILE_SCOPE");
  seen.add(name);
  if(b.readUInt32LE(local)!==0x04034b50)throw Error("ZIP_LOCAL");
  const localNameLen=b.readUInt16LE(local+26),localExtra=b.readUInt16LE(local+28);
  const localName=b.subarray(local+30,local+30+localNameLen).toString("utf8");
  if(localName!==name)throw Error("ZIP_NAME_MISMATCH");
  const start=local+30+localNameLen+localExtra;
  const raw=b.subarray(start,start+packed);
  const decoded=method===0?raw:method===8?inflateRawSync(raw,{maxOutputLength:100001}):null;
  if(!decoded || decoded.length!==unpacked)throw Error("ZIP_DECOMPRESSION");
  if(name==="shadow-report.json")report=JSON.parse(decoded.toString("utf8"));
  pos+=46+nameLen+extra+comment;
 }
 if(pos!==off+size || !report)throw Error("ZIP_COMPLETENESS");
 return report;
}
export function qualifyLiveCheck({zipBytes,artifactMetadata,repo,pr,head,liveHead,
 appId,installed,existingChecks}={}) {
 let authenticated=false,report;
 try{
  authenticated=checkArtifactBytes(zipBytes,artifactMetadata);
  if(authenticated)report=extractBoundReport(zipBytes);
 }catch{authenticated=false}
 return gatePKCYamlPublication({report,repo,pr,head,liveHead,
  appId,installed,existingChecks,artifactAuthenticated:authenticated});
}
