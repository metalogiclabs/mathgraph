// Trust root: the public key configured independently in the Worker environment.
// A signature authenticates packet bytes under that key. It does NOT prove
// the owner's intended policy, the truth of evidence, or normative authority.
import {createPublicKey,verify} from "node:crypto";
import {Buffer} from "node:buffer";

const B64URL=/^[A-Za-z0-9_-]+$/;
const PREFIX="MathGraph owner-contract v1\n";
const bad=code=>({verified:false,code});

export function verifyConfiguredOwnerContract(raw,publicKeyPEM) {
  if (raw===undefined) return bad("UNRESOLVED_OWNER_CONTRACT");
  if (typeof publicKeyPEM!=="string" || publicKeyPEM.length===0)
    return bad("UNRESOLVED_OWNER_TRUST_ROOT");
  if (typeof raw!=="string" || raw.length>100000)
    return bad("UNRESOLVED_OWNER_SIGNATURE");
  try {
    const envelope=JSON.parse(raw);
    if (!envelope || envelope.schema!=="mathgraph.signed-owner-contract.v1" ||
        typeof envelope.payload_b64!=="string" ||
        typeof envelope.signature_b64!=="string" ||
        envelope.payload_b64.length>87384 || envelope.payload_b64.length===0 ||
        envelope.signature_b64.length>1500 ||
        !B64URL.test(envelope.payload_b64) || !B64URL.test(envelope.signature_b64))
      return bad("UNRESOLVED_OWNER_SIGNATURE");
    const bytes=Buffer.from(envelope.payload_b64,"base64url");
    const sig=Buffer.from(envelope.signature_b64,"base64url");
    if (bytes.toString("base64url")!==envelope.payload_b64 ||
        sig.toString("base64url")!==envelope.signature_b64 || bytes.length>65536)
      return bad("UNRESOLVED_OWNER_SIGNATURE");
    const key=createPublicKey(publicKeyPEM);
    if (key.asymmetricKeyType!=="rsa" ||
        (key.asymmetricKeyDetails?.modulusLength||0)<2048 ||
        !verify("RSA-SHA256",Buffer.from(PREFIX+envelope.payload_b64),key,sig))
      return bad("UNRESOLVED_OWNER_SIGNATURE");
    // Reject invalid UTF-8 and decode only after the signature is qualified.
    const payload=bytes.toString("utf8");
    if (!Buffer.from(payload,"utf8").equals(bytes))
      return bad("UNRESOLVED_OWNER_SIGNATURE");
    const contract=JSON.parse(payload);
    // A signed JSON text with duplicate keys can mean different things to
    // different parsers. Require one unambiguous JSON.stringify round-trip.
    if (JSON.stringify(contract)!==payload)
      return bad("UNRESOLVED_OWNER_SIGNATURE");
    return {verified:true,contract};
  }catch{
    return bad("UNRESOLVED_OWNER_SIGNATURE");
  }
}
