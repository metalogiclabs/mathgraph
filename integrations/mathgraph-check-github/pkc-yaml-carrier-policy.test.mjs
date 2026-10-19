import test from "node:test";
import assert from "node:assert/strict";
import {carrierAdmitted,CARRIER} from "./pkc-yaml-carrier-policy.mjs";
test("integration PR 176 cannot be a historical evidence-only carrier",()=>{
 assert.equal(carrierAdmitted("metalogiclabs/mathgraph",176,"a".repeat(40),
 [{filename:"integrations/mathgraph-check-github/webhook.mjs"}]),false)});
test("only dedicated evidence-only carrier admitted",()=>{
 assert.equal(CARRIER.allowedPR,178);
 assert.equal(carrierAdmitted("metalogiclabs/mathgraph",178,CARRIER.allowedHead,
 [{filename:".mathgraph-check/pkc-yaml/EXTERNAL-RESEARCH-RECEIPT.md"}]),true);
 assert.equal(carrierAdmitted("metalogiclabs/mathgraph",171,"a".repeat(40),
 [{filename:".mathgraph-check/pkc-yaml/receipt.json"}]),false)});
