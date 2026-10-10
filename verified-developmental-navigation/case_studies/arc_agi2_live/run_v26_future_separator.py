#!/usr/bin/env python3
"""V26 retrospective exact separator of the V25 protected-future failures.

This is NOT fresh heldout evaluation. Protected MinimalTasks outputs were already
scored by V25; they may now be used ONLY for diagnosis. We derive the smallest
feature-signature collision and classify whether it is beyond the entire fixed
feature vocabulary, merely beyond the selected policy, or due to unseen mappings
or changing grid dimensions. Never promote a candidate from this diagnostic.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v25_relational_representation as v25

SOURCE="0e67da6af879e4bad3d7cd3c196e8d551b445725"


def dump(data,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")


def sample_per_pixel(t):
    out=[]
    for part in ("train","test"):
        for k,pair in enumerate(t[part]):
            g=v25.norm_grid(pair["input"])
            target=v25.norm_grid(pair["output"])
            same_dims=(len(g)==len(target) and
                       bool(g and target) and len(g[0])==len(target[0]))
            if not same_dims:
                out.append({"phase":part,"case":k,
                            "shape_failure":True,"source_dims":[len(g),len(g[0]) if g else 0],
                            "target_dims":[len(target),len(target[0]) if target else 0]})
                continue
            features=v25.grid_features(g)
            for i in range(len(g)):
                for j in range(len(g[0])):
                    out.append({"phase":part,"case":k,"i":i,"j":j,
                                "features":features[i,j],
                                "input":g[i][j],"required":target[i][j]})
    return out


def collision(rows,selected_features):
    store={}
    for r in rows:
        if r.get("shape_failure"):continue
        key=tuple(r["features"][f] for f in selected_features)
        prior=store.get(key)
        if prior is not None and prior["required"]!=r["required"]:
            different=[f for f in v25.FEATS
                       if prior["features"][f]!=r["features"][f]]
            return {"first":{"phase":prior["phase"],"case":prior["case"],
                             "i":prior["i"],"j":prior["j"],
                             "input":prior["input"],"required":prior["required"]},
                    "second":{"phase":r["phase"],"case":r["case"],
                              "i":r["i"],"j":r["j"],
                              "input":r["input"],"required":r["required"]},
                    "selected_signature":repr(key),
                    "available_full_vocabulary_separators":different,
                    "full_vocabulary_collision":not bool(different)}
        store.setdefault(key,r)
    return None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--v25-result",required=True)
    ap.add_argument("--v25-policy",required=True)
    ap.add_argument("--minimal",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    v=json.loads(Path(a.v25_result).read_text())
    p=json.loads(Path(a.v25_policy).read_text())
    assert v["schema"]=="vdn.conceptarc.minimal-feature-transfer.v25"
    assert p["schema"]=="vdn.minimal-relational-representation.v25"
    assert v["source"]==p["source_pin"]==SOURCE
    assert v["target_tasks"]==16
    r={x["id"]:x for x in v["protected_rows"]["learned_relation"]}
    t=v25.target_tasks(a.minimal)
    assert set(t)==set(r)
    types=collections.Counter()
    residual=[]
    for tid,task in sorted(t.items()):
        row=r[tid]
        pixels=sample_per_pixel(task)
        bad_shapes=[x for x in pixels if x.get("shape_failure")]
        train_bad=[x for x in bad_shapes if x["phase"]=="train"]
        test_bad=[x for x in bad_shapes if x["phase"]=="test"]
        base={"task_id":tid,
              "chosen_program_fits_training":row["fit"],
              "chosen_feature_set":row["features"],
              "training_shape_mismatch_count":len(train_bad),
              "test_shape_mismatch_count":len(test_bad),
              "old_V25_heldout_solved":row["protected_solved"]}
        if train_bad:
            base["primary_obstruction"]="TRAIN_OUTPUT_DIMENSION_CHANGE"
        elif not row["fit"]:
            # Exhaust feature grammar on demos, not on protected answers.
            train=v25.task_data(task)
            fitting=[fs for fs in v25.feature_universe()
                     if v25.fit(train,fs) is not None]
            base["demo_fitting_feature_sets"]=len(fitting)
            base["primary_obstruction"]=("TRAIN_NO_DETERMINISTIC_MAP_IN_FINITE_GRAMMAR"
                                         if not fitting else "TRAIN_POLICY_BUDGET")
        elif test_bad:
            base["primary_obstruction"]="TEST_OUTPUT_DIMENSION_CHANGE"
        else:
            fs=tuple(row["features"])
            train=v25.task_data(task)
            m=v25.fit(train,fs)
            assert m is not None
            collisions=collision(pixels,fs)
            base["selected_feature_collision"]=collisions
            seen=wrong_known=unseen_needed=wrong_total=0
            for k,pair in enumerate(task["test"]):
                raw=v25.norm_grid(pair["input"])
                y=v25.norm_grid(pair["output"])
                features=v25.grid_features(raw)
                for i in range(len(raw)):
                    for j in range(len(raw[0])):
                        key=tuple(features[i,j][f] for f in fs)
                        pred=m.get(key,raw[i][j]); real=y[i][j]
                        if key in m:seen+=1
                        if pred!=real:
                            wrong_total+=1
                            if key in m:wrong_known+=1
                            else:unseen_needed+=1
            base.update({"wrong_test_pixels":wrong_total,
                         "wrong_on_seen_source_signature":wrong_known,
                         "unseen_feature_signature_requires_change":unseen_needed,
                         "known_signature_test_pixels":seen})
            if collisions and collisions["full_vocabulary_collision"]:
                base["primary_obstruction"]="FIXED_FEATURE_VOCABULARY_NOT_FUTURE_SUFFICIENT"
            elif collisions:
                base["primary_obstruction"]="SELECTED_FEATURE_QUOTIENT_NOT_FUTURE_SUFFICIENT"
            elif unseen_needed:
                base["primary_obstruction"]="UNSEEN_SIGNATURE_INFERENCE_MISSING"
            elif wrong_known:
                base["primary_obstruction"]="KNOWN_SIGNATURE_SEMANTICS_DRIFT"
            else:
                base["primary_obstruction"]="NONLOCAL_TRANSFER_RESIDUAL"
        types[base["primary_obstruction"]]+=1
        residual.append(base)
    assert sum(types.values())==16
    full=[x for x in residual if x["primary_obstruction"]=="FIXED_FEATURE_VOCABULARY_NOT_FUTURE_SUFFICIENT"]
    result={"schema":"vdn.v26.retrospective_future_separator",
            "source":SOURCE,
            "authority":"V25 protected tests already seen: retrospective diagnostic, NOT prospective gain",
            "original_v25_claims":v["claims"],
            "tasks":16,
            "obstruction_counts":dict(types),
            "fixed_vocabulary_collision_tasks":[x["task_id"] for x in full],
            "witnesses":[x["selected_feature_collision"] for x in full[:3]],
            "epistemic":{
                "bounded_negative_observation_certificate":
                    "WARRANTED_EXACT_FINITE" if full else "UNKNOWN",
                "generator_solved_new_protected_task":"NO",
                "autonomous_representation_invention":"UNKNOWN",
                "any_collatz_or_universal_AI_claim":"NOT_APPLICABLE"},
            "rows":residual}
    dump(result,Path(a.out))
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))


if __name__=="__main__":main()
