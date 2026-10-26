"""Constrained real-source coding loop; real Nebius inference ONLY in --provider nebius.

The public CI uses a SCRIPTED provider and cannot qualify Nebius model usage.
Model writes one verified return expression within a pinned upstream file;
any broader patch is refused. The isolation is task-specific, not a general sandbox.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Protocol
from urllib import request

from upstream_encoding_transfer import (
    ENCODING_PATH, EXPANDED_COMMAND, MUTANTS, NATIVE_COMMAND,
    acquired_tests, call_native_code, copy_package, digest, execute,
    experiment, oracle, pinned_source, qualify, snapshot,
)

MODEL_DEFAULT = "nvidia/nemotron-3-super-120b-a12b"
ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
RETURN_PATTERN = re.compile(r"(?m)^    return .+$")

def validate_replacement(line: str) -> None:
    """Allow bounded pure Base64 encoders and byte substitutions, not Python programs."""
    if len(line) > 320 or "\n" in line or "\r" in line or "\x00" in line:
        raise ValueError("DISALLOWED_PATCH_FORMAT")
    if not line.startswith("return "):
        raise ValueError("RETURN_STATEMENT_REQUIRED")
    try:
        parsed=ast.parse("def f(string):\n    " + line + "\n")
    except SyntaxError as exc:
        raise ValueError("INVALID_PYTHON_EXPRESSION") from exc
    expr=parsed.body[0].body[0].value
    if len(list(ast.walk(expr))) > 32:
        raise ValueError("EXPRESSION_TOO_COMPLEX")
    def check(node: ast.AST, depth: int = 0) -> None:
        if depth > 8 or not isinstance(node, ast.Call) or node.keywords:
            raise ValueError("DISALLOWED_OPERATION")
        fun=node.func
        if not isinstance(fun, ast.Attribute):
            raise ValueError("DISALLOWED_CALL")
        if (isinstance(fun.value, ast.Name) and fun.value.id == "base64"
            and fun.attr in ("b64encode", "urlsafe_b64encode")):
            if (len(node.args)!=1 or not isinstance(node.args[0], ast.Name)
                or node.args[0].id!="string"):
                raise ValueError("DISALLOWED_ENCODER_ARGUMENT")
            return
        if fun.attr=="rstrip":
            if (len(node.args)!=1 or not isinstance(node.args[0], ast.Constant)
                or node.args[0].value != b"="):
                raise ValueError("DISALLOWED_STRIP_ARGUMENT")
            check(fun.value,depth+1)
            return
        if fun.attr=="replace":
            if (len(node.args)!=2 or not all(isinstance(x,ast.Constant) for x in node.args)
                or (node.args[0].value,node.args[1].value)
                    not in ((b"+",b"-"),(b"/",b"_"))):
                raise ValueError("DISALLOWED_BYTE_REPLACEMENT")
            check(fun.value,depth+1)
            return
        raise ValueError("DISALLOWED_METHOD")
    check(expr)

def isolated_patch(source: bytes, replacement: str) -> bytes:
    validate_replacement(replacement)
    text=source.decode("utf-8")
    before, sep, after=text.partition("def base64_encode(")
    if not sep:
        raise ValueError("NATIVE_FUNCTION_MISSING")
    block, sep2, rest=after.partition("\ndef base64_decode(")
    if not sep2 or len(RETURN_PATTERN.findall(block))!=1:
        raise ValueError("AMBIGUOUS_PATCH_TARGET")
    newblock=RETURN_PATTERN.sub("    "+replacement,block,count=1)
    result=(before+"def base64_encode("+newblock+"\ndef base64_decode("+rest).encode("utf-8")
    if len(result)>len(source)+512:
        raise ValueError("PATCH_SIZE_LIMIT")
    return result

@dataclass(frozen=True)
class Proposal:
    replacement_return: str
    provider: str
    model: str
    response_sha256: str
    request_id: str | None
    timestamp_utc: str

class RepairProvider(Protocol):
    def propose(self, source: str, observations: list[dict], attempt: int) -> Proposal: ...

class ScriptedRepair:
    """Non-model fixture: first proposal wrong, second correct."""
    def propose(self, source: str, observations: list[dict], attempt: int) -> Proposal:
        content=("return base64.urlsafe_b64encode(string)" if attempt==1
                 else 'return base64.urlsafe_b64encode(string).rstrip(b"=")')
        return Proposal(content,"SCRIPTED_NOT_NEBIUS","none",
                        digest(content.encode()),None,
                        datetime.now(timezone.utc).isoformat())

class NebiusRepair:
    def __init__(self, model: str):
        self.key=os.environ.get("NEBIUS_API_KEY")
        if not self.key:
            raise RuntimeError("NEBIUS_API_KEY not configured privately; no authenticated inference")
        if not model.startswith("nvidia/"):
            raise ValueError("model must be from NVIDIA Nemotron catalog")
        self.model=model

    def propose(self, source: str, observations: list[dict], attempt: int) -> Proposal:
        system=("You are a software repair agent. Return ONLY a JSON object with the one "
                "string key 'replacement_return'. It must be a single Python return "
                "statement for base64_encode(string), restricted to base64.b64encode "
                "or base64.urlsafe_b64encode applied to string, optionally using "
                ".replace(b'+',b'-'), .replace(b'/',b'_') and .rstrip(b'='). "
                "Never emit imports, eval, exec, shell commands, function definitions, "
                "or edits to tests. Contract: URL-safe unpadded Base64 bytes.")
        user=("This is a pinned upstream source copy with a deliberately injected "
              "experimental defect, not an upstream bug report. Repair the return "
              "expression based on independent failing tests.\n"
              + "Attempt "+str(attempt)+"\nSource:\n"+source[:5000]
              +"\nEvidence (input hex, expected output hex, observed output hex):\n"
              +json.dumps(observations,sort_keys=True))
        payload=json.dumps({"model":self.model,
            "messages":[{"role":"system","content":system},{"role":"user","content":user}],
            "temperature":0.1,"max_tokens":400},separators=(",",":")).encode()
        req=request.Request(ENDPOINT,method="POST",data=payload,
            headers={"Authorization":"Bearer "+self.key,
                     "Content-Type":"application/json"})
        try:
            with request.urlopen(req,timeout=60) as response:
                raw=response.read(1_048_576)
                header_id=response.headers.get("x-request-id")
        except Exception as exc:
            raise RuntimeError("NEBIUS_INFERENCE_FAILED:"+type(exc).__name__) from exc
        result=json.loads(raw)
        if result.get("model") and result["model"]!=self.model:
            raise ValueError("MODEL_IDENTITY_MISMATCH")
        content=result["choices"][0]["message"]["content"]
        if not isinstance(content,str):
            raise ValueError("MODEL_DID_NOT_RETURN_TEXT")
        obj=json.loads(content)
        if set(obj)!={"replacement_return"} or not isinstance(obj["replacement_return"],str):
            raise ValueError("MODEL_OUTPUT_SCHEMA_MISMATCH")
        return Proposal(obj["replacement_return"],"nebius-token-factory",self.model,
                        digest(raw),str(header_id or result.get("id") or ""),
                        datetime.now(timezone.utc).isoformat())

def run(checkout: Path, provider: RepairProvider, attempts: int = 3) -> dict:
    """Authentic inference provenance requires NebiusRepair and a returned response."""
    if attempts<1 or attempts>5:
        raise ValueError("attempt budget out of bounds")
    upstream=pinned_source(checkout)
    source=(checkout/ENCODING_PATH).read_bytes()
    qualified_original_sha=digest(source)
    analysis=experiment(checkout)  # authentic upstream source-native comparison
    cases=tuple(bytes.fromhex(x) for x in analysis["experiment"]["minimum_tests_hex"])
    if not cases:
        raise AssertionError("NO_SOURCE_PINNED_SEPARATING_WITNESS")
    timeline=[]
    with TemporaryDirectory(prefix="mathgraph-nebius-guarded-") as tmp:
        root=Path(tmp)
        mutated=__import__("upstream_encoding_transfer").mutate(source,"standard_alphabet")
        copy_package(checkout,root,mutated)
        native=execute(root,qualified_original_sha,NATIVE_COMMAND)
        state,_=qualify(root,native,qualified_original_sha,NATIVE_COMMAND)
        if state!="WARRANTED":
            raise AssertionError("PINNED_NATIVE_CONTROL_NOT_PASSING")
        timeline.append({"step":"native_tests_pass_but_contract_unproven",
                         "state":state,"receipt":asdict(native)})
        (root/"test_mathgraph_acquired.py").write_bytes(acquired_tests(cases))
        invalidated=qualify(root,native,qualified_original_sha,NATIVE_COMMAND)[0]
        if invalidated!="REJECTED":
            raise AssertionError("TEST_BYTES_DID_NOT_WITHDRAW_RECEIPT")
        evidence=execute(root,qualified_original_sha,EXPANDED_COMMAND)
        refusal=qualify(root,evidence,qualified_original_sha,EXPANDED_COMMAND)[0]
        if refusal!="REJECTED":
            raise AssertionError("SEPARATING_TESTS_DID_NOT_FAIL")
        timeline.append({"step":"separating_evidence_exposes_defect",
                         "state":refusal,"receipt":asdict(evidence)})
        final="UNKNOWN"
        for attempt in range(1,attempts+1):
            code=(root/"src"/"itsdangerous"/"encoding.py").read_bytes()
            actual=call_native_code(root,cases)
            differences=[{"input_hex":x.hex(),"expected_hex":oracle(x).hex(),
                          "observed_hex":y.hex()} for x,y in zip(cases,actual)
                         if oracle(x)!=y]
            try:
                proposal=provider.propose(code.decode("utf-8"),differences,attempt)
                altered=isolated_patch(code,proposal.replacement_return)
                if altered==code:
                    timeline.append({"step":"unchanged_model_proposal",
                                     "attempt":attempt,"state":"REJECTED",
                                     "proposal":asdict(proposal)})
                    continue
                (root/"src"/"itsdangerous"/"encoding.py").write_bytes(altered)
                stale=qualify(root,evidence,qualified_original_sha,EXPANDED_COMMAND)[0]
                if stale!="REJECTED":
                    raise AssertionError("MUTATED_SOURCE_RETAINED_STALE_RECEIPT")
                receipt=execute(root,qualified_original_sha,EXPANDED_COMMAND)
                state,reason=qualify(root,receipt,qualified_original_sha,EXPANDED_COMMAND)
                timeline.append({"step":"bounded_model_patch_attempt","attempt":attempt,
                                 "state":state,"reason":reason,
                                 "proposal":asdict(proposal),"receipt":asdict(receipt)})
                evidence=receipt
                if state=="WARRANTED":
                    final="WARRANTED"
                    break
            except (ValueError,RuntimeError,KeyError,IndexError,TypeError) as exc:
                timeline.append({"step":"invalid_or_unavailable_model_proposal",
                                 "attempt":attempt,"state":"UNKNOWN",
                                 "reason":type(exc).__name__})
                # Never authorize from failed model inference or invalid output.
                continue
        return {"schema":"mathgraph.nebius-pinned-repair.v1",
                "mode":("AUTHENTIC_NEBIUS_RESPONSE_RECORDED_NOT_THIRD_PARTY_ATTESTED"
                        if isinstance(provider,NebiusRepair)
                        else "SCRIPTED_OFFLINE_NO_NEBIUS_INFERENCE"),
                "provider_type":type(provider).__name__,
                "origin_commit":analysis["origin"]["commit"],
                "upstream_git_blob_evidence":upstream,
                "comparison":analysis["comparison"],
                "selected_inputs_hex":[x.hex() for x in cases],
                "final_state":final,
                "authority_scope":"exact source/test bytes, upstream native pytest + finite acquired tests",
                "events":timeline}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--provider",choices=("scripted","nebius"),default="scripted")
    p.add_argument("--model",default=MODEL_DEFAULT)
    p.add_argument("--attempts",type=int,default=3)
    p.add_argument("--report",type=Path,default=Path("upstream-live-candidate-report.json"))
    a=p.parse_args()
    provider=ScriptedRepair() if a.provider=="scripted" else NebiusRepair(a.model)
    report=run(a.upstream_checkout.resolve(),provider,a.attempts)
    a.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"mode":report["mode"],"final_state":report["final_state"],
                      "events":[{"step":e["step"],"state":e["state"]}
                                for e in report["events"]]},indent=2))
    if report["final_state"]!="WARRANTED":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
