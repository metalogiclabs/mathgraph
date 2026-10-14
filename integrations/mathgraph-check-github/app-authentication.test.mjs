import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, verify } from "node:crypto";
import {
  normalizePrivateKey, authenticateAndPublish, APP_CLIENT_ID, appHttp
} from "./app-authentication.mjs";

function generated() {
  const keys = generateKeyPairSync("rsa", { modulusLength: 2048 });
  return {
    pkcs1: keys.privateKey.export({ type:"pkcs1", format:"pem" }).toString(),
    pkcs8: keys.privateKey.export({ type:"pkcs8", format:"pem" }).toString(),
    publicKey: keys.publicKey
  };
}
const SHA="a04aa77aaebd81d11274560e8d24d90c6f417589";
function fixture(options = {}) {
  const key = generated();
  const calls = [];
  const jwtIssuer = [];
  const json = (value, status = 200) =>
    new Response(JSON.stringify(value), { status });
  const grant = { checks: "write", pull_requests:"read", actions:"read" };
  let revoked = 0, published = 0;
  const fetcher = async (url, init) => {
    const u = new URL(url);
    assert.equal(u.origin, "https://api.github.com");
    const path = u.pathname;
    calls.push({ path, method:init.method });
    assert.match(init.headers.Authorization, /^Bearer /);
    if (path === "/app") {
      const pieces=init.headers.Authorization.slice(7).split(".");
      const payload=JSON.parse(Buffer.from(pieces[1],"base64url"));
      jwtIssuer.push(payload.iss);
      assert.equal(payload.iss, APP_CLIENT_ID);
      assert.equal(verify("RSA-SHA256", Buffer.from(pieces[0]+"."+pieces[1]),
        key.publicKey,Buffer.from(pieces[2],"base64url")),true);
      return json({id: options.wrongApp ? 15368 : 5308912,
        owner:{login:"metalogiclabs"},permissions:grant});
    }
    if (path === "/repos/metalogiclabs/go-ethereum/installation") {
      if (options.missingInstallation) return json({},404);
      return json({id:42,app_id:5308912,
        account:{login:"metalogiclabs"},
        suspended_at:null,
        permissions:options.badPermissions ?
          {...grant,checks:"read"}:grant});
    }
    if (path === "/app/installations/42/access_tokens") {
      assert.equal(init.method,"POST");
      assert.deepEqual(JSON.parse(init.body), {
        repositories:["go-ethereum"],permissions:grant
      });
      return json({token:"restricted-installation-token",permissions:grant});
    }
    if (path === "/installation/token") {
      assert.equal(init.method,"DELETE");
      revoked++;
      return options.revokeFailed ? json({},403) :
        new Response(null,{status:204});
    }
    throw Error("TEST_UNEXPECTED_GITHUB_ENDPOINT");
  };
  const publish = async ({token}) => {
    assert.equal(token, "restricted-installation-token");
    published++;
    if (options.publisherFailed) throw Error("PUBLISHER_FAILS_CLOSED");
    return { outcome:"CREATED", appID:5308912, checkId:789,
      repository:"metalogiclabs/go-ethereum",pr:19,sha:SHA,
      conclusion:"neutral" };
  };
  return { key, calls, jwtIssuer, fetcher, publish,
    get revoked(){return revoked;},
    get published(){return published;} };
}

test("parses GitHub's PKCS1 and PKCS8 RSA private keys",()=>{
  const {pkcs1,pkcs8}=generated();
  assert.equal(normalizePrivateKey(pkcs1).key.asymmetricKeyType,"rsa");
  assert.equal(normalizePrivateKey(pkcs8).key.asymmetricKeyType,"rsa");
});

test("repairs escaped newlines, Base64 PEM and one-line compacted PEM in memory",()=>{
  const {pkcs1}=generated();
  const escaped=pkcs1.replace(/\n/g,"\\n");
  const b64=Buffer.from(pkcs1).toString("base64");
  const compact=pkcs1.replace(/\n/g, " ");
  for(const encoded of [escaped,b64,compact,JSON.stringify(escaped)]) {
    const result=normalizePrivateKey(encoded);
    assert.equal(result.key.asymmetricKeyType,"rsa");
  }
});

test("incomplete or missing PEM remains a clear nonsecret rejection",()=>{
  assert.throws(()=>normalizePrivateKey(""),/APP_PRIVATE_KEY_MISSING_OR_OVERSIZED/);
  const {pkcs1}=generated();
  assert.throws(()=>normalizePrivateKey(pkcs1.slice(0,80)),
    /APP_PRIVATE_KEY_UNPARSEABLE_OR_INCOMPLETE/);
});

test("valid credentials issue scoped token, publish only registered App, revoke token",async()=>{
  const f=fixture();
  const r=await authenticateAndPublish({
    keyText:f.key.pkcs1,fetcher:f.fetcher,publish:f.publish
  });
  assert.equal(r.appID,5308912);
  assert.equal(r.outcome,"CREATED");
  assert.equal(r.tokenRevoked,true);
  assert.equal(f.revoked,1);
  assert.equal(f.published,1);
  assert.deepEqual(f.jwtIssuer,[APP_CLIENT_ID]);
});

test("wrong App and uninstalled target never mint or publish",async()=>{
  for(const options of [{wrongApp:true},{missingInstallation:true},{badPermissions:true}]) {
    const f=fixture(options);
    await assert.rejects(authenticateAndPublish({
      keyText:f.key.pkcs8,fetcher:f.fetcher,publish:f.publish
    }),/(WRONG_REGISTERED_GITHUB_APP|GITHUB_REPOSITORY_INSTALLATION_HTTP_404|INSTALLATION_MISSING_REQUIRED_PERMISSIONS)/);
    assert.equal(f.published,0);
    assert.equal(f.revoked,0);
  }
});

test("failed publication still revokes the short-lived token",async()=>{
  const f=fixture({publisherFailed:true});
  await assert.rejects(authenticateAndPublish({
    keyText:f.key.pkcs1,fetcher:f.fetcher,publish:f.publish
  }),/PUBLISHER_FAILS_CLOSED/);
  assert.equal(f.revoked,1);
});

test("unverified token revocation cannot be called complete",async()=>{
  const f=fixture({revokeFailed:true});
  await assert.rejects(authenticateAndPublish({
    keyText:f.key.pkcs1,fetcher:f.fetcher,publish:f.publish
  }),/INSTALLATION_TOKEN_REVOCATION_NOT_VERIFIED/);
});

test("does not send credentials to unallowlisted API URLs",async()=>{
  await assert.rejects(appHttp("/user","any",{
    fetcher:async()=>{throw Error("must not run");}
  }),/INVALID_GITHUB_APP_API_PATH/);
});
