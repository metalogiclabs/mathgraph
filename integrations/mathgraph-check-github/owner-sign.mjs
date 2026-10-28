// Offline signer for a separately approved pilot-owner contract.
// The private key remains on the owner's machine; only the envelope is output.
import {readFile,writeFile} from "node:fs/promises";
import {createPrivateKey,sign} from "node:crypto";
import {Buffer} from "node:buffer";
import {assessWarrant} from "./warrant.mjs";

function argumentsFrom(argv){
  const opts=new Map();
  if(argv.length!==6) throw Error("REQUIRE_CONTRACT_KEY_OUT");
  for(let i=0;i<argv.length;i+=2){
    if(!["--contract","--key","--out"].includes(argv[i]) ||
       opts.has(argv[i]) || !argv[i+1]) throw Error("REQUIRE_CONTRACT_KEY_OUT");
    opts.set(argv[i],argv[i+1]);
  }
  if(opts.size!==3) throw Error("REQUIRE_CONTRACT_KEY_OUT");
  return opts;
}

async function main(){
  const opts=argumentsFrom(process.argv.slice(2));
  let contract;
  try{contract=JSON.parse(await readFile(opts.get("--contract"),"utf8"));}
  catch{throw Error("INVALID_OWNER_CONTRACT");}
  if(!contract || typeof contract!=="object" || Array.isArray(contract) ||
     contract.schema!=="mathgraph.owner-contract.v1")
    throw Error("INVALID_OWNER_CONTRACT");
  const subject=contract.subject;
  const assessment=assessWarrant({repository:subject?.repository,
    number:subject?.pr,sha:subject?.sha},contract,contract.grant?.issued_at);
  if(assessment.residuals.some(x=>[
    "UNRESOLVED_MODEL_COVERAGE","UNRESOLVED_OWNER_CONTRACT_BINDING"
  ].includes(x.code)))throw Error("INVALID_OWNER_CONTRACT");

  let key;
  try{
    key=createPrivateKey(await readFile(opts.get("--key")));
    if(key.asymmetricKeyType!=="rsa" ||
       (key.asymmetricKeyDetails?.modulusLength||0)<2048)throw Error("WEAK_KEY");
  }catch{throw Error("INVALID_PRIVATE_KEY");}

  const payload_b64=Buffer.from(JSON.stringify(contract)).toString("base64url");
  const message=Buffer.from("MathGraph owner-contract v1\n"+payload_b64);
  const signature_b64=sign("RSA-SHA256",message,key).toString("base64url");
  const envelope={schema:"mathgraph.signed-owner-contract.v1",
    payload_b64,signature_b64};
  try{
    await writeFile(opts.get("--out"),JSON.stringify(envelope)+"\n",{
      flag:"wx",mode:0o600});
  }catch(e){
    if(e.code==="EEXIST")throw Error("OUTPUT_ALREADY_EXISTS");
    throw Error("OUTPUT_WRITE_FAILED");
  }
  console.log("SIGNED_OWNER_ENVELOPE_CREATED");
}

try{await main();}
catch(e){
  // Fixed error codes: never echo key bytes, signed policy or file paths.
  console.error(/^[A-Z_]+$/.test(e.message)?e.message:"SIGNER_FAILED");
  process.exitCode=1;
}
