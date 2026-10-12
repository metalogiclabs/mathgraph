"""Source publication contracts: source identity never establishes proof authority."""

from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "tests/fixtures/source_catalogue_v1/canonical-vectors.json"
AXES = {"source_status": "SOURCE_INDEXED", "verification_status": "NOT_CHECKED",
        "current_applicability": "NOT_CHECKED", "freshness": "PINNED_HISTORICAL_SOURCE",
        "authorization": "NONE", "authority": "NONE"}
PIN = {"repository": "https://github.com/leanprover-community/mathlib4",
       "commit": "a" * 40, "tree": "b" * 40}


def test_validator_is_published():
    assert importlib.util.find_spec("mathgraph_protocol.source_catalogue_v1"), "source catalogue validator is missing"


@pytest.fixture
def api():
    assert importlib.util.find_spec("mathgraph_protocol.source_catalogue_v1"), "source catalogue validator is missing"
    return importlib.import_module("mathgraph_protocol.source_catalogue_v1")


def test_complete_catalogue_uses_measured_raw_file_boundaries(api):
    """Keep the exact 13-module publication without weakening transfer limits."""
    assert api.LIMITS["max_search_bytes"] == 2 * 1024 * 1024
    assert api.LIMITS["max_shard_bytes"] == 2 * 1024 * 1024

    schema = json.loads((ROOT / "protocol/schemas/source-catalogue-manifest-v1.schema.json").read_text())
    limits = schema["properties"]["limits"]["properties"]
    assert limits["max_search_bytes"]["maximum"] == api.LIMITS["max_search_bytes"]
    assert limits["max_shard_bytes"]["maximum"] == api.LIMITS["max_shard_bytes"]
    assert schema["properties"]["search"]["properties"]["size_bytes"]["maximum"] == api.LIMITS["max_search_bytes"]
    assert schema["properties"]["shards"]["items"]["properties"]["size_bytes"]["maximum"] == api.LIMITS["max_shard_bytes"]


def test_exact_committed_catalogue_manifest_satisfies_its_public_schema():
    manifest = json.loads((ROOT / "website/public/catalogues/mathlib/v4.34.1/manifest.json").read_text())
    schema = json.loads((ROOT / "protocol/schemas/source-catalogue-manifest-v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)


def fixture(api):
    modules, objects = [], []
    for name, qualified in [("Mathlib.One", "One.first"), ("Mathlib.Two", "Two.second")]:
        path = name.replace(".", "/") + ".lean"
        mid = api.module_id(PIN["repository"], PIN["commit"], name, path)
        oid = api.occurrence_id(PIN["repository"], PIN["commit"], name, path, qualified)
        modules.append({"module_id": mid, "module": name, "path": path, "sha256": "c" * 64,
                        "size_bytes": 100, "objects": [{"object_id": oid, "qualified_name": qualified}]})
        statement = "True"
        objects.append({"object_id": oid, "object_contract_version": 1,
                        "source": {**PIN, "module": name, "path": path,
                                   "range": {"start": {"line": 1, "column": 0, "byte": 0},
                                             "end": {"line": 1, "column": 10, "byte": 10}}},
                        "qualified_name": qualified, "kind": "theorem", "statement": statement,
                        "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                        **AXES, "extensions": []})
    catalogue_id = "mathlib-test-v1"
    relations = []
    for kind, source, target, sk, tk in [
        ("DECLARES", modules[0]["module_id"], objects[0]["object_id"], "SOURCE_MODULE", "SOURCE_DECLARATION"),
        ("IMPORTS_MODULE", modules[0]["module_id"], modules[1]["module_id"], "SOURCE_MODULE", "SOURCE_MODULE"),
        ("TYPE_REFERENCES", objects[0]["object_id"], objects[1]["object_id"], "SOURCE_DECLARATION", "SOURCE_DECLARATION"),
    ]:
        relations.append({"relation_id": api.relation_id(catalogue_id, kind, source, target),
                          "type": kind, "source_id": source, "target_id": target,
                          "source_kind": sk, "target_kind": tk, "authority": "NONE",
                          "logical_implication": False, "semantic_equivalence": False, "extensions": []})
    relations.sort(key=lambda item: item["relation_id"])
    shard = {"schema": "mathgraph.source-catalogue-shard.v1", "catalogue_version": 1,
             "catalogue_id": catalogue_id,
             "module": {**{k: v for k, v in modules[0].items() if k != "objects"}, **PIN, **AXES},
             "objects": objects[:1], "relations": relations,
             "omissions": {"type_references": [{"source_id": objects[0]["object_id"], "target_name": "Outside.name"}],
                           "imports": ["Outside.Module"], "declarations": []}, **AXES, "extensions": []}
    raw = api.canonical_bytes(shard)
    sha = hashlib.sha256(raw).hexdigest()
    manifest = {"schema": "mathgraph.source-catalogue-manifest.v1", "catalogue_version": 1,
                "catalogue_id": catalogue_id,
                "source": {**PIN, "tag": "v4.34.1",
                           "license": {"path": "LICENSE", "sha256": "d" * 64},
                           "citation": {"path": "CITATION.md", "sha256": "d" * 64},
                           "lean_toolchain": {"path": "lean-toolchain", "sha256": "d" * 64, "value": "leanprover/lean4:v4.34.1"},
                           "lake_manifest": {"path": "lake-manifest.json", "sha256": "d" * 64},
                           "root_module": {"path": "Mathlib.lean", "sha256": "d" * 64},
                           "dependency_inventory_sha256": "e" * 64},
                "extractor": {"source_commit": "f" * 40, "contract_version": 1,
                              "sources": [{"path": "tools/mathlib_catalogue/Extract.lean", "sha256": "d" * 64}]},
                "selection_policy": {"modules": "EXPLICIT_MODULE_LIST", "declarations": "USER_ORIGIN_SUPPORTED_WITH_RANGE",
                                     "ordering": "UTF16_LEXICOGRAPHIC", "type_references": "DIRECT_EXPR_CONST",
                                     "imports": "DIRECT_ONLY", "omissions": "NAMED_COUNTED"},
                "modules": modules,
                "counts": {"modules": 2, "objects": 2, "relations": 4, "omitted_type_references": 1,
                           "omitted_imports": 1, "omitted_declarations": 0},
                "limits": {"max_declarations": 2500, "max_relations": 25000, "max_search_bytes": 2097152,
                           "max_shard_bytes": 2097152, "max_manifest_bytes": 1048576,
                           "max_projection_nodes": 50, "max_projection_edges": 100},
                "truncation": {"occurred": False, "reason": None},
                "reproduce_command": "python scripts/publish_mathlib_source_catalogue_v1.py --checkout {CHECKOUT} --output {OUTPUT}",
                "search": {"path": "search.json", "sha256": "d" * 64, "size_bytes": 100, "object_count": 2},
                "shards": [{"module_id": modules[0]["module_id"], "path": f"shards/{sha}.json", "sha256": sha,
                            "size_bytes": len(raw), "object_count": 1, "relation_count": 3,
                            "omitted_type_references": 1, "omitted_imports": 1, "omitted_declarations": 0},
                           {"module_id": modules[1]["module_id"], "path": f"shards/{'e' * 64}.json", "sha256": "e" * 64,
                            "size_bytes": 100, "object_count": 1, "relation_count": 1,
                            "omitted_type_references": 0, "omitted_imports": 0, "omitted_declarations": 0}],
                **AXES, "extensions": []}
    return manifest, shard


def repin(api, manifest, shard):
    """Keep transport valid when testing a semantic mutation."""
    raw = api.canonical_bytes(shard)
    metadata = manifest["shards"][0]
    metadata.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    metadata["path"] = f"shards/{metadata['sha256']}.json"


@pytest.mark.parametrize("start,end", [
    ({"line": 1, "column": 0, "byte": 5}, {"line": 1, "column": 5, "byte": 10}),
    ({"line": 2, "column": 5, "byte": 5}, {"line": 2, "column": 10, "byte": 10}),
    ({"line": 1, "column": 10, "byte": 10}, {"line": 2, "column": 20, "byte": 30}),
])
def test_internally_impossible_byte_coordinates_are_rejected(api, start, end):
    manifest, shard = fixture(api)
    shard["objects"][0]["source"]["range"] = {"start": start, "end": end}
    repin(api, manifest, shard)
    with pytest.raises(api.SourceCatalogueError, match="INVALID_RANGE"):
        api.validate_shard(shard, manifest)


def test_shared_jcs_vectors(api):
    for vector in json.loads(VECTORS.read_text()):
        assert api.canonical_bytes(vector["value"]) == vector["canonical"].encode("utf-8")
    assert api.canonical_bytes({"b": 1, "a": 2}) == api.canonical_bytes({"a": 2, "b": 1})
    assert len({api.canonical_bytes(v) for v in [1, True, "1", None]}) == 4
    assert api.canonical_bytes("é") != api.canonical_bytes("e\u0301")


@pytest.mark.parametrize("value", [1.0, -0.0, float("nan"), float("inf"), 2**53, -(2**53), "\ud800", {1: "x"}, (1,), {"x": object()}])
def test_canonical_rejects_unsupported_values(api, value):
    with pytest.raises(api.SourceCatalogueError):
        api.canonical_bytes(value)


def test_identity_payloads_and_changes(api):
    args = [PIN["repository"], PIN["commit"], "Mathlib.One", "Mathlib/One.lean"]
    raw = ('{"commit":"' + "a" * 40 + '","module":"Mathlib.One","path":"Mathlib/One.lean",'
           '"repository":"https://github.com/leanprover-community/mathlib4"}').encode()
    assert api.module_id(*args) == "module-" + hashlib.sha256(raw).hexdigest()
    original = api.module_id(*args)
    for index in range(4):
        changed = args.copy()
        changed[index] += "x"
        assert api.module_id(*changed) != original
        assert api.occurrence_id(*changed, "One.first") != api.occurrence_id(*args, "One.first")
    assert api.occurrence_id(*args, "One.first") != api.occurrence_id(*args, "One.second")
    assert api.occurrence_id(*args, "One.first", 2) != api.occurrence_id(*args, "One.first")
    baseline = api.relation_id("c", "DECLARES", "s", "t")
    for values in [("d", "DECLARES", "s", "t"), ("c", "TYPE_REFERENCES", "s", "t"),
                   ("c", "DECLARES", "s2", "t"), ("c", "DECLARES", "s", "t2")]:
        assert api.relation_id(*values) != baseline


def test_valid_contract_and_exact_public_mirrors(api):
    manifest, shard = fixture(api)
    assert api.validate_manifest(manifest) == manifest
    assert api.validate_shard(api.canonical_bytes(shard), manifest) == shard
    for name, value in [("manifest", manifest), ("shard", shard)]:
        path = f"source-catalogue-{name}-v1.schema.json"
        canonical = (ROOT / "protocol/schemas" / path).read_bytes()
        assert canonical == (ROOT / "website/public/schemas" / path).read_bytes()
        schema = json.loads(canonical)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)


def test_public_schemas_decline_authority_versions_kinds_and_unknown_fields(api):
    manifest, shard = fixture(api)
    manifest_schema = json.loads((ROOT / "protocol/schemas/source-catalogue-manifest-v1.schema.json").read_text())
    shard_schema = json.loads((ROOT / "protocol/schemas/source-catalogue-shard-v1.schema.json").read_text())
    for field, value in [("authority", "VERIFY"), ("verification_status", "VERIFIED"),
                         ("authorization", "EXECUTE"), ("source_status", "WARRANTED"),
                         ("catalogue_version", 2), ("terminal_form", "VERIFIED_PROOF"),
                         ("generated_at", "2026-10-12")]:
        altered = deepcopy(manifest); altered[field] = value
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(manifest_schema).validate(altered)
    for field, value in [("type", "PROOF_DEPENDS_ON"), ("logical_implication", True),
                         ("semantic_equivalence", True), ("authority", "VERIFY"),
                         ("source_kind", "SOURCE_DECLARATION")]:
        altered = deepcopy(shard)
        next(r for r in altered["relations"] if r["type"] == "DECLARES")[field] = value
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(shard_schema).validate(altered)
    for kind in ["recursor", "quotient", "generated"]:
        altered = deepcopy(shard); altered["objects"][0]["kind"] = kind
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(shard_schema).validate(altered)
    altered = deepcopy(manifest)
    altered["extensions"] = [{"id": "unknown", "version": 1, "critical": True, "payload": None}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(manifest_schema).validate(altered)


def test_manifest_text_bytes_and_bytearray_preserve_canonical_values(api):
    manifest, _ = fixture(api)
    raw = api.canonical_bytes(manifest)
    for value in [raw, bytearray(raw), raw.decode("utf-8")]:
        assert api.validate_manifest(value) == manifest


@pytest.mark.parametrize("raw,code", [(b'{"schema":1,"schema":2}', "DUPLICATE_JSON_KEY"),
    (b'{"n":NaN}', "NONFINITE_JSON_NUMBER"), (b'{"n":1e999}', "NONFINITE_JSON_NUMBER"),
    (b'{"n":1.0}', "UNSUPPORTED_JSON_VALUE"), (b'{"n":-0}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":-0.0}', "UNSUPPORTED_JSON_VALUE"), (b'\xef\xbb\xbf{}', "INVALID_UTF8"),
    (b'\xff{}', "INVALID_UTF8"), (b'{"n":"\\ud800"}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":9007199254740992}', "UNSUPPORTED_JSON_VALUE"),
    (b'{"n":"-0"}', "MISSING_FIELD")])
def test_strict_json_decline_codes(api, raw, code):
    with pytest.raises(api.SourceCatalogueError) as error:
        api.validate_manifest(raw)
    assert error.value.code == code


def test_bounded_input_and_parser_errors(api):
    for raw, code in [(b" " * (1048576 + 1), "INPUT_TOO_LARGE"),
                      ("[" * 10000 + "0" + "]" * 10000, "INVALID_JSON")]:
        with pytest.raises(api.SourceCatalogueError) as error:
            api.validate_manifest(raw)
        assert error.value.code == code
    cyclic = {}; cyclic["cycle"] = cyclic
    with pytest.raises(api.SourceCatalogueError):
        api.canonical_bytes(cyclic)


@pytest.mark.parametrize("field,value", [("schema", "mathgraph.source-catalogue-manifest.v2"),
    ("catalogue_version", 2), ("authority", "VERIFY"), ("authorization", "EXECUTE"),
    ("source_status", "WARRANTED"), ("verification_status", "VERIFIED"),
    ("terminal_form", "VERIFIED_PROOF"), ("generated_at", "2026-10-12")])
def test_manifest_rejects_escalation_and_wall_clock(api, field, value):
    manifest, _ = fixture(api)
    manifest[field] = value
    with pytest.raises(api.SourceCatalogueError):
        api.validate_manifest(manifest)


def test_required_manifest_fields_and_counts(api):
    manifest, _ = fixture(api)
    for field in manifest:
        changed = deepcopy(manifest); del changed[field]
        with pytest.raises(api.SourceCatalogueError):
            api.validate_manifest(changed)
    for field in manifest["counts"]:
        changed = deepcopy(manifest); changed["counts"][field] += 1
        with pytest.raises(api.SourceCatalogueError):
            api.validate_manifest(changed)


def test_pin_inventory_and_content_addressing_mutations(api):
    manifest, _ = fixture(api)
    mutations = [lambda m: m["source"].update(commit="main"),
                 lambda m: m["modules"][0].update(path="../One.lean"),
                 lambda m: m["modules"][0].update(module_id=m["modules"][1]["module_id"]),
                 lambda m: m["modules"][0]["objects"][0].update(object_id=m["modules"][1]["objects"][0]["object_id"]),
                 lambda m: m["modules"][1]["objects"][0].update(qualified_name="One.first"),
                 lambda m: m["shards"][0].update(path="shards/wrong.json"),
                 lambda m: m["shards"][0].update(size_bytes=api.LIMITS["max_shard_bytes"] + 1),
                 lambda m: m["limits"].update(max_declarations=2501),
                 lambda m: m["selection_policy"].update(type_references="TEXT_MENTIONS"),
                 lambda m: m["truncation"].update(occurred=True),
                 lambda m: m["modules"].reverse()]
    for mutate in mutations:
        changed = deepcopy(manifest); mutate(changed)
        with pytest.raises(api.SourceCatalogueError):
            api.validate_manifest(changed)


@pytest.mark.parametrize("field,value", [("kind", "recursor"), ("kind", "quotient"),
    ("verification_status", "VERIFIED"), ("authority", "CHECK"), ("authorization", "EXECUTE"),
    ("terminal_form", "NAMED_OBSTRUCTION"), ("statement_sha256", "e" * 64)])
def test_occurrence_rejects_kind_integrity_and_status_mutations(api, field, value):
    manifest, shard = fixture(api); shard["objects"][0][field] = value; repin(api, manifest, shard)
    with pytest.raises(api.SourceCatalogueError):
        api.validate_shard(shard, manifest)


def test_occurrence_requires_every_field_and_same_pin_and_range(api):
    manifest, shard = fixture(api)
    for field in shard["objects"][0]:
        changed = deepcopy(shard); del changed["objects"][0][field]; repin(api, manifest, changed)
        with pytest.raises(api.SourceCatalogueError): api.validate_shard(changed, manifest)
    for field, value in [("commit", "f" * 40), ("tree", "f" * 40), ("module", "Mathlib.Two"), ("path", "Mathlib/Two.lean")]:
        changed = deepcopy(shard); changed["objects"][0]["source"][field] = value; repin(api, manifest, changed)
        with pytest.raises(api.SourceCatalogueError): api.validate_shard(changed, manifest)
    changed = deepcopy(shard); changed["objects"][0]["source"]["range"]["end"]["byte"] = 101; repin(api, manifest, changed)
    with pytest.raises(api.SourceCatalogueError): api.validate_shard(changed, manifest)


@pytest.mark.parametrize("field,value", [("type", "IMPLIES"), ("type", "EQUIVALENT_TO"),
    ("type", "EVIDENCE_SUPPORTS"), ("type", "PROOF_DEPENDS_ON"),
    ("logical_implication", True), ("semantic_equivalence", True), ("logical_implication", 0),
    ("authority", "VERIFY"), ("source_kind", "SOURCE_DECLARATION"),
    ("target_id", "object-" + "0" * 64)])
def test_relations_decline_unadmitted_meanings_and_endpoints(api, field, value):
    manifest, shard = fixture(api)
    relation = next(r for r in shard["relations"] if r["type"] == "DECLARES")
    relation[field] = value; repin(api, manifest, shard)
    with pytest.raises(api.SourceCatalogueError): api.validate_shard(shard, manifest)


def test_shard_digest_size_counts_duplicates_and_provenance(api):
    manifest, shard = fixture(api)
    altered = deepcopy(shard); altered["objects"][0]["statement"] = "False"
    with pytest.raises(api.SourceCatalogueError): api.validate_shard(altered, manifest)
    for collection in ["objects", "relations"]:
        altered = deepcopy(shard); altered[collection].append(deepcopy(altered[collection][0])); repin(api, manifest, altered)
        with pytest.raises(api.SourceCatalogueError): api.validate_shard(altered, manifest)
    altered = deepcopy(shard)
    relation = next(r for r in altered["relations"] if r["type"] == "TYPE_REFERENCES")
    relation["source_id"], relation["target_id"] = relation["target_id"], relation["source_id"]
    relation["relation_id"] = api.relation_id(altered["catalogue_id"], relation["type"], relation["source_id"], relation["target_id"])
    altered["relations"].sort(key=lambda r: r["relation_id"]); repin(api, manifest, altered)
    with pytest.raises(api.SourceCatalogueError): api.validate_shard(altered, manifest)


def test_extensions_are_unique_opaque_and_never_authoritative(api):
    manifest, shard = fixture(api)
    extension = {"id": "future.example", "version": 1, "critical": False,
                 "payload": {"authority": "EXECUTE", "verification_status": "VERIFIED", "terminal_form": "VERIFIED_PROOF"}}
    manifest["extensions"] = [deepcopy(extension)]
    assert api.validate_manifest(manifest)["extensions"] == [extension]
    shard["objects"][0]["extensions"] = [deepcopy(extension)]; repin(api, manifest, shard)
    result = api.validate_shard(shard, manifest)
    assert result["objects"][0]["extensions"] == [extension]
    assert result["authority"] == result["objects"][0]["authority"] == "NONE"
    for extensions, code in [([dict(extension, critical=True)], "UNKNOWN_CRITICAL_EXTENSION"),
                              ([extension, extension], "DUPLICATE_EXTENSION")]:
        manifest["extensions"] = extensions
        with pytest.raises(api.SourceCatalogueError) as error: api.validate_manifest(manifest)
        assert error.value.code == code


def test_malformed_field_types_always_decline_through_the_public_error(api):
    """Catch unchecked operations and Python bool/integer equality at every field."""
    manifest, shard = fixture(api)

    def paths(value, prefix=()):
        if isinstance(value, dict):
            for key, member in value.items():
                yield prefix + (key,)
                yield from paths(member, prefix + (key,))
        elif isinstance(value, list):
            for key, member in enumerate(value):
                yield prefix + (key,)
                yield from paths(member, prefix + (key,))

    for name, document in [("manifest", manifest), ("shard", shard)]:
        schema = json.loads((ROOT / f"protocol/schemas/source-catalogue-{name}-v1.schema.json").read_text())
        for path in paths(document):
            for value in [None, True, 0, [], {}, "x"]:
                altered = deepcopy(document)
                parent = altered
                for key in path[:-1]: parent = parent[key]
                parent[path[-1]] = value
                try:
                    if name == "manifest":
                        accepted = api.validate_manifest(altered)
                    else:
                        pin = deepcopy(manifest); repin(api, pin, altered)
                        accepted = api.validate_shard(altered, pin)
                except api.SourceCatalogueError:
                    continue
                jsonschema.Draft202012Validator(schema).validate(accepted)


def test_canonical_shard_transport_and_supported_kinds(api):
    manifest, shard = fixture(api)
    for kind in ["theorem", "definition", "opaque", "axiom", "inductive", "constructor"]:
        shard["objects"][0]["kind"] = kind; repin(api, manifest, shard)
        assert api.validate_shard(shard, manifest)["objects"][0]["kind"] == kind
    with pytest.raises(api.SourceCatalogueError) as error:
        api.validate_shard(api.canonical_bytes(shard) + b"\n", manifest)
    assert error.value.code == "NONCANONICAL_SHARD"
    with pytest.raises(api.SourceCatalogueError) as error:
        api.validate_shard(b" " * (api.LIMITS["max_shard_bytes"] + 1), manifest)
    assert error.value.code == "INPUT_TOO_LARGE"
    # Mutable callers must never be able to alter the validator's returned copy.
    validated = api.validate_manifest(manifest)
    validated["source"]["commit"] = "c" * 40
    assert manifest["source"]["commit"] == "a" * 40


def test_range_lines_must_be_possible_within_the_byte_interval(api):
    manifest, shard = fixture(api)
    shard["objects"][0]["source"]["range"]["end"]["line"] = 100
    repin(api, manifest, shard)
    with pytest.raises(api.SourceCatalogueError) as error:
        api.validate_shard(shard, manifest)
    assert error.value.code == "INVALID_RANGE"
