#!/usr/bin/env python3
"""Synthetic only: freeze V2 alias discovery and matched baseline before new source."""
import importlib.util
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
def load(label, path):
    spec=importlib.util.spec_from_file_location(label,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

candidate=load("preflight_v2_candidate",HERE/"propose.py")
expert=load("preflight_v2_expert",HERE/"expert_reference.py")

with tempfile.TemporaryDirectory() as dirname:
    path=Path(dirname)/"__init__.py"
    md={"repository":"example/frozen-toml","description":"portable TOML serializer","source_sha":"a"*40}
    cases=[
        ("alias",
         'from . import encoder\nfrom .decoder import loads\ndumps = encoder.dumps\n__all__ = ["dumps", "loads"]\n',
         ["dumps","loads"],["external-semantics","native-roundtrip"]),
        ("direct_import",
         'from ._writer import dumps\n__all__ = ("dumps",)\n',
         ["dumps"],["external-semantics"]),
        ("unrelated_literal",
         'from . import encoder\ndumps = 42\n__all__ = ["dumps"]\n',
         [],[]),
        ("unbound",
         'dumps = arbitrary.dumps\n__all__ = ["dumps"]\n',
         [],[]),
    ]
    for label,source,names,obligations in cases:
        path.write_text(source)
        left=candidate.propose(md,path)
        right=expert.expert_rules(md,path)
        assert left["api_sha256"]==right["api_sha256"] and left["source_sha"]==right["source_sha"]
        assert left["public_symbols"]==right["public_symbols"]==names,(label,left,right)
        assert [x["id"] for x in left["obligations"]]==obligations,(label,left)
        assert [x["id"] for x in right["obligations"]]==obligations,(label,right)
        assert left["obligations"]==right["obligations"],(label,left,right)
        assert (left["status"]=="UNKNOWN_NO_SUPPORTED_RELATION")==not bool(obligations)
    path.write_text('from .writer import dumps\n')
    md_ambiguous={**md,"description":"TOML and JSON"}
    assert candidate.propose(md_ambiguous,path)["status"]=="UNKNOWN_NO_SUPPORTED_RELATION"
    assert expert.expert_rules(md_ambiguous,path)["status"]=="UNKNOWN_NO_SUPPORTED_RELATION"
    assert len(load("frozen_v1_evaluate",HERE.parent/"semantic_obligation_induction_v1"/"evaluate.py").SAMPLES)==3
print("SEMANTIC_OBLIGATION_ALIAS_V2_PREFLIGHT_PASS: four synthetic classes, matched comparator, ambiguity abstention")
