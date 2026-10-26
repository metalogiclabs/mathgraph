"""Evidence-seeking merge planner: genuine Nebius decisions, source-native authority.

The model may select ONLY typed, predeclared observation actions, not write shell
or direct merge commands. A separate exact solver and real pinned native pytest
verify what the proposal warrants. No upstream repository is ever mutated.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib import request

from merge_decision_lab import CASES, _candidate, _select, _truth_table
from upstream_encoding_transfer import ENCODING_PATH, MUTANTS, domain, pinned_source, digest
from upstream_nebius_agent import DEFAULT_MODEL, ENDPOINT

RIVALS = tuple(sorted(MUTANTS))
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["acquire", "obstruction"]},
        "tests_hex": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "unseparable": {
            "type": "array", "items": {"type": "string", "enum": list(RIVALS)}
        },
    },
    "required": ["decision", "tests_hex", "unseparable"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ProposedAction:
    action: dict
    provider: str
    model: str
    response_sha256: str
    request_id: str | None
    choice_id: str | None = None


def menu_from_native(inputs, observations, lengths) -> list[dict]:
    """Smallest-cost real input for every available discrimination pattern."""
    per_pattern = {}
    for i, value in enumerate(inputs):
        if len(value) not in lengths:
            continue
        changed = tuple(n for n in RIVALS
                        if observations[n][i] != observations["reference"][i])
        if not changed:
            continue
        cost = len(value) + 1
        option = {"hex": value.hex(), "cost": cost, "separates": list(changed)}
        old = per_pattern.get(changed)
        if old is None or (cost, option["hex"]) < (old["cost"], old["hex"]):
            per_pattern[changed] = option
    return sorted(per_pattern.values(), key=lambda x: (x["cost"], x["hex"]))


def certify_action(action: object, menu: list[dict], exact: dict) -> dict:
    """Model output is a request, never merge authority."""
    if not isinstance(action, dict) or set(action) != set(ACTION_SCHEMA["required"]):
        raise ValueError("ACTION_SCHEMA_REJECTED")
    decision, probes, claimed = (action[k] for k in
                                 ("decision", "tests_hex", "unseparable"))
    if decision not in ("acquire", "obstruction"):
        raise ValueError("ACTION_KIND_REJECTED")
    if (not isinstance(probes, list) or len(probes) > 4
        or any(type(x) is not str for x in probes) or len(set(probes)) != len(probes)
        or not isinstance(claimed, list) or any(type(x) is not str for x in claimed)
        or len(set(claimed)) != len(claimed)
        or any(x not in RIVALS for x in claimed)):
        raise ValueError("ACTION_SHAPE_REJECTED")
    if exact["status"] == "OBSTRUCTION":
        if decision != "obstruction" or probes or sorted(claimed) != sorted(exact["unsplittable"]):
            raise ValueError("OBSTRUCTION_PROPOSAL_UNSUPPORTED")
        return {"status": "ACCEPTED_OBSTRUCTION", "tests_hex": [],
                "cost": None, "unseparable": sorted(claimed)}
    if exact["status"] != "MINIMUM_BASIS":
        raise ValueError("EXACT_SOLVER_NOT_QUALIFIED")
    if decision != "acquire" or claimed or not probes:
        raise ValueError("EXPERIMENT_PROPOSAL_REQUIRED")
    choices = {v["hex"]: v for v in menu}
    if any(x not in choices for x in probes):
        raise ValueError("UNAUTHORIZED_TEST")
    covered = set()
    cost = 0
    for x in probes:
        covered.update(choices[x]["separates"])
        cost += choices[x]["cost"]
    if covered != set(RIVALS):
        raise ValueError("TESTS_NOT_SEPARATING")
    if cost != exact["synthetic_cost"]:
        raise ValueError("TESTS_NOT_MINIMUM_COST")
    return {"status": "ACCEPTED_MINIMUM_BASIS", "tests_hex": probes,
            "cost": cost, "unseparable": []}


class ScriptedPlanner:
    """Only for deterministic CI; never represents authentic model inference."""
    def propose(self, case, menu, lengths, attempt, feedback="") -> ProposedAction:
        if not menu or not set(RIVALS).issubset(
            set().union(*(set(v["separates"]) for v in menu))):
            missing = sorted(set(RIVALS) - set().union(
                *(set(v["separates"]) for v in menu)))
            action = {"decision": "obstruction", "tests_hex": [],
                      "unseparable": missing}
        else:
            from itertools import combinations
            options = []
            for count in range(1, min(4, len(menu)) + 1):
                for subset in combinations(menu, count):
                    covered = set().union(*(set(v["separates"]) for v in subset))
                    if covered == set(RIVALS):
                        options.append((sum(v["cost"] for v in subset),
                                        tuple(v["hex"] for v in subset)))
            if not options:
                raise AssertionError("SCRIPTED_MENU_INCOMPLETE")
            _, choices = min(options)
            action = {"decision": "acquire", "tests_hex": list(choices),
                      "unseparable": []}
        return ProposedAction(action, "SCRIPTED_OFFLINE_NOT_NEBIUS", "none",
                              digest(json.dumps(action, sort_keys=True).encode()), None)


class NemotronObservationPlanner:
    """Typed Nebius proposal with no model-generated executable code."""
    def __init__(self, model: str = DEFAULT_MODEL):
        key = os.environ.get("NEBIUS_API_KEY")
        if not key:
            raise RuntimeError("NEBIUS_API_KEY_NOT_CONFIGURED")
        if not model.startswith("nvidia/"):
            raise ValueError("NVIDIA_OPEN_MODEL_REQUIRED")
        self._key = key
        self.model = model

    def propose(self, case, menu, lengths, attempt, feedback="") -> ProposedAction:
        system = (
            "You are an evidence-seeking merge reviewer. Choose ONLY a typed "
            "permitted observation action, never a code patch or approval. "
            "Every possible probe is listed below with exact detection "
            "coverage and synthetic cost. Choose the minimum-total-cost "
            "subset covering ALL three rival behaviors. If impossible, "
            "return decision=obstruction and the EXACT named unseparable "
            "rivals; tests_hex empty. Otherwise decision=acquire, "
            "tests_hex from the supplied menu, unseparable empty. "
            "Return one JSON object with exactly those three fields."
        )
        user = {
            "source_repository": "pallets/itsdangerous",
            "source_commit": "672971d66a2ef9f85151e53283113f33d642dabd",
            "review_case": case,
            "permitted_input_byte_lengths": list(lengths),
            "required_rival_coverage": list(RIVALS),
            "native_source_derived_options": menu,
            "previous_verifier_feedback": feedback[:160] if feedback else "none",
            "attempt": attempt,
        }
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(user,sort_keys=True)}],
            "temperature": 0.1,
            "max_tokens": 450,
            "chat_template_kwargs": {"enable_thinking": False},
            "guided_json": ACTION_SCHEMA,
            "response_format": {"type": "json_object"},
        }
        raw_body = json.dumps(body,sort_keys=True).encode()
        req = request.Request(ENDPOINT, data=raw_body, method="POST",
                              headers={"Content-Type": "application/json",
                                       "Authorization": "Bearer " + self._key})
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read(1024*1024)
                req_id = response.headers.get("x-request-id")
        except Exception as exc:
            raise RuntimeError("NEBIUS_INFERENCE_UNVERIFIED:" + type(exc).__name__) from None
        try:
            data = json.loads(raw)
            if data.get("model") and data["model"] != self.model:
                raise ValueError("NEBIUS_MODEL_ID_MISMATCH")
            choice = data["choices"][0]
            content = choice["message"].get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("NEBIUS_EMPTY_ACTION")
            if choice.get("finish_reason") not in ("stop", None):
                raise ValueError("NEBIUS_TRUNCATED_ACTION")
            action = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError):
            raise ValueError("NEBIUS_ACTION_RESPONSE_MALFORMED") from None
        return ProposedAction(action, "nebius-token-factory", self.model,
                              digest(raw), str(req_id or data.get("id") or "") or None)



def finite_plan_options(menu: list[dict], case: str) -> dict[str, dict]:
    """Offer trusted finite choices; an untrusted model only selects an ID.

    This avoids parsing model-authored source code or arbitrary hex arrays.
    Plans and prices are derived solely from the pinned native behavior table.
    The independent exact verifier still owns all admission decisions.
    """
    from itertools import combinations
    items=[]
    for count in range(1,min(3,len(menu))+1):
        for subset in combinations(menu,count):
            covered=set().union(*(set(x["separates"]) for x in subset))
            action={"decision":"acquire",
                    "tests_hex":[x["hex"] for x in subset],"unseparable":[]}
            items.append({"action":action,
                          "cost":sum(x["cost"] for x in subset),
                          "covers":sorted(covered),
                          "complete":covered==set(RIVALS)})
    full=sorted((x for x in items if x["complete"]),
                key=lambda x:(x["cost"],len(x["action"]["tests_hex"]),
                              x["action"]["tests_hex"]))
    partial=sorted((x for x in items if not x["complete"]),
                   key=lambda x:(x["cost"],x["action"]["tests_hex"]))
    covered=set().union(*(set(x["separates"]) for x in menu))
    blocked=sorted(set(RIVALS)-covered)
    correct_obstruction={"action":{"decision":"obstruction","tests_hex":[],
                                    "unseparable":blocked},
                         "cost":None,"covers":sorted(covered),
                         "complete":False}
    false_obstruction={"action":{"decision":"obstruction","tests_hex":[],
                                  "unseparable":[next((r for r in RIVALS
                                                    if r not in blocked),RIVALS[0])]},
                       "cost":None,"covers":sorted(covered),"complete":False}
    options=[]
    if partial:options.append(partial[0])
    if full:
        options.append(full[0])
        more=next((p for p in full[1:] if p["cost"]>full[0]["cost"]),None)
        if more:options.append(more)
        options.append(false_obstruction)
    else:
        options.append(correct_obstruction)
        options.append(false_obstruction)
    # Shuffle without randomness, creating a stable ID that does not always
    # reveal the correct answer by position. Published source fixes the order.
    items_by_digest=sorted(options,key=lambda p:digest(
        (case+"|"+json.dumps(p["action"],sort_keys=True)).encode()))
    ids="ABCDEFGH"
    return {ids[i]:item for i,item in enumerate(items_by_digest)}


class NebiusMenuPlanner:
    """Model selects one constrained option; only trusted code constructs tests."""
    def __init__(self,model: str=DEFAULT_MODEL):
        key=os.environ.get("NEBIUS_API_KEY")
        if not key:raise RuntimeError("NEBIUS_API_KEY_NOT_CONFIGURED")
        if not model.startswith("nvidia/"):raise ValueError("NVIDIA_OPEN_MODEL_REQUIRED")
        self._key=key
        self.model=model

    def propose(self,case,menu,lengths,attempt,feedback="") -> ProposedAction:
        options=finite_plan_options(menu,case)
        schema={"type":"object","properties":{
            "choice_id":{"type":"string","enum":list(options)}},
            "required":["choice_id"],"additionalProperties":False}
        visible=[{"id":k,"decision":v["action"]["decision"],
                  "tests_hex":v["action"]["tests_hex"],
                  "unseparable":v["action"]["unseparable"],
                  "covers":v["covers"],"cost":v["cost"]}
                 for k,v in options.items()]
        messages=[
            {"role":"system","content":(
                "You are an evidence-seeking code review planner, not a merge authority. "
                "Choose exactly one provided OPTION ID. Every required rival must be "
                "distinguished using allowed tests at minimum total synthetic cost. "
                "A plan's 'covers' lists which rival defects its proposed tests expose. "
                "If no listed acquisition covers all required rivals, choose the "
                "obstruction with the exact set of uncovered rivals. "
                "Return only JSON with choice_id. No explanation or source code.")},
            {"role":"user","content":json.dumps({
                "review_case":case,"admitted_lengths":list(lengths),
                "required_rivals":list(RIVALS),"options":visible,
                "independent_verifier_feedback":feedback[:160] or "none",
                "attempt":attempt
            },sort_keys=True)}
        ]
        body={"model":self.model,"messages":messages,
              "temperature":0.0,"max_tokens":120,
              "chat_template_kwargs":{"enable_thinking":False},
              "guided_json":schema,"response_format":{"type":"json_object"}}
        req=request.Request(ENDPOINT,data=json.dumps(body,sort_keys=True).encode(),
                            method="POST",headers={
                            "Content-Type":"application/json",
                            "Authorization":"Bearer "+self._key})
        try:
            with request.urlopen(req,timeout=60) as response:
                raw=response.read(1024*1024)
                header_id=response.headers.get("x-request-id")
        except Exception as exc:
            raise RuntimeError("NEBIUS_PLAN_UNVERIFIED:"+type(exc).__name__) from None
        try:
            response=json.loads(raw)
            if response.get("model") and response["model"]!=self.model:
                raise ValueError("MODEL_ID_MISMATCH")
            choice=response["choices"][0]
            text=choice["message"]["content"]
            if not isinstance(text,str) or not text.strip():
                raise ValueError("MODEL_EMPTY_CHOICE")
            if choice.get("finish_reason") not in ("stop",None):
                raise ValueError("MODEL_INCOMPLETE_CHOICE")
            parsed=json.loads(text)
            if not isinstance(parsed,dict) or set(parsed)!={"choice_id"}:
                raise ValueError("MODEL_WRONG_CHOICE_SCHEMA")
            selected=parsed["choice_id"]
            if not isinstance(selected,str) or selected not in options:
                raise ValueError("MODEL_CHOICE_NOT_IN_MENU")
        except (ValueError,TypeError,KeyError,IndexError):
            raise ValueError("NEBIUS_MENU_RESPONSE_MALFORMED") from None
        return ProposedAction(options[selected]["action"],"nebius-token-factory",
                              self.model,digest(raw),
                              str(header_id or response.get("id") or "") or None,
                              choice_id=selected)


def run_review(checkout: Path, provider, max_attempts: int = 2) -> dict:
    """Execute all three decisions; report every rejected model proposal."""
    if max_attempts not in (1, 2):
        raise ValueError("ATTEMPT_BUDGET_EXCEEDED")
    pinned=pinned_source(checkout)
    source=(checkout / ENCODING_PATH).read_bytes()
    original_sha=digest(source)
    with TemporaryDirectory(prefix="mathgraph-observation-planner-") as scratch:
        root=Path(scratch)
        inputs, observations = _truth_table(checkout, root, source)
        results={}
        for case_id, candidate, permitted in CASES:
            exact = _select(inputs, observations, permitted)
            menu = menu_from_native(inputs, observations, permitted)
            history=[]
            selected=None
            for attempt in range(1,max_attempts+1):
                prev_feedback=history[-1].get("reason","") if history else ""
                proposal = provider.propose(case_id, menu, permitted, attempt, prev_feedback)
                event={"attempt": attempt, "provider": proposal.provider,
                       "model": proposal.model, "request_id": proposal.request_id,
                       "response_sha256": proposal.response_sha256,
                       "choice_id": proposal.choice_id}
                try:
                    chosen=certify_action(proposal.action,menu,exact)
                    event["state"]="ACCEPTED"
                    event["certified_selection"]=chosen
                    history.append(event)
                    selected=chosen
                    break
                except ValueError as exc:
                    event["state"]="REJECTED"
                    event["reason"]=str(exc)
                    history.append(event)
            if selected is None:
                results[case_id]={"proposal_state":"REJECTED_OR_MISSING",
                                  "merge_permission":"NONE", "proposals":history,
                                  "source_native_verdict":"NOT_EXECUTED",
                                  "exact_expected_cost":exact["synthetic_cost"]}
                continue
            if selected["status"]=="ACCEPTED_OBSTRUCTION":
                native = _candidate(checkout,root,source,original_sha,case_id,
                                    candidate,exact)
            else:
                approved = dict(exact)
                approved["tests_hex"]=selected["tests_hex"]
                approved["synthetic_cost"]=selected["cost"]
                native = _candidate(checkout,root,source,original_sha,case_id,
                                    candidate,approved)
            results[case_id]={"proposal_state":"ACCEPTED",
                              "proposals":history,
                              "source_native_verdict":native["final_state"],
                              "merge_permission":native["release_permission"],
                              "review":native,
                              "exact_expected_cost":exact["synthetic_cost"]}
    return {
        "schema":"mathgraph.model-chosen-evidence-merge-v1",
        "source":{"repository":"pallets/itsdangerous",
                  "commit":"672971d66a2ef9f85151e53283113f33d642dabd",
                  "file_evidence":pinned},
        "scope":"three constructed pinned-source cases; model chooses typed probes only; verifier owns all approvals",
        "provider_type":type(provider).__name__,
        "no_upstream_write":True,
        "model_cannot_approve_merge":True,
        "cases":results,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout",type=Path,required=True)
    parser.add_argument("--provider",choices=("scripted","nebius","nebius_menu"),
                        default="scripted")
    parser.add_argument("--max-attempts",type=int,default=2)
    parser.add_argument("--report",type=Path,default=Path("model-observation-review.json"))
    args=parser.parse_args()
    provider=(ScriptedPlanner() if args.provider=="scripted"
              else NebiusMenuPlanner() if args.provider=="nebius_menu"
              else NemotronObservationPlanner())
    report=run_review(args.upstream_checkout.resolve(),provider,args.max_attempts)
    args.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    overview={k:{"proposal":v["proposal_state"],
                 "verdict":v["source_native_verdict"],
                 "merge_permission":v["merge_permission"],
                 "attempts":len(v["proposals"])}
              for k,v in report["cases"].items()}
    print(json.dumps({"provider":report["provider_type"],"cases":overview},indent=2))
    if any(v["proposal_state"]!="ACCEPTED" for v in report["cases"].values()):
        raise SystemExit(1)

if __name__=="__main__":
    main()
