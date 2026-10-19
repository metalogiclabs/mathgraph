import test from "node:test";
import assert from "node:assert/strict";
import {parseSignedEvent,SCOPE} from "./worker.mjs";
const carrier={repository:{full_name:"metalogiclabs/mathgraph"},
 installation:{id:42},action:"edited",pull_request:{
 number:178,head:{sha:"05a6057e94d899ded94374db4a831963034aea93",
 repo:{full_name:"metalogiclabs/mathgraph"}},base:{repo:{full_name:"metalogiclabs/mathgraph"}}}};
test("production Worker currently does not admit the historical evidence carrier",()=>{
 assert.equal(SCOPE.repository,"metalogiclabs/go-ethereum");
 assert.equal(parseSignedEvent(carrier,"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","pull_request"),null);
});
