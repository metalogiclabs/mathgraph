#!/usr/bin/env python3
"""Stdlib-only replay of a pinned, authority-free source catalogue.

This consumer validates canonical publication bytes, a separately supplied
trust-policy digest, exact source/extractor pins, structural relation meanings,
closed endpoints, counts, and content addresses. It does not fetch source,
run Lean, replay proofs, establish current applicability, or authorize action.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


MAX_SAFE_INTEGER = 9007199254740991
MAX_POLICY_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SHARD_BYTES = 512 * 1024
MAX_SEARCH_BYTES = 750 * 1024
MAX_PUBLICATION_BYTES = 4 * 1024 * 1024
MAX_PUBLICATION_GZIP_BYTES = 1536 * 1024
MANIFEST_SCHEMA = "mathgraph.source-catalogue-manifest.v1"
SHARD_SCHEMA = "mathgraph.source-catalogue-shard.v1"
POLICY_SCHEMA = "mathgraph.source-catalogue-trust-policy.v1"
AXES = {
    "source_status": "SOURCE_INDEXED",
    "verification_status": "NOT_CHECKED",
    "current_applicability": "NOT_CHECKED",
    "freshness": "PINNED_HISTORICAL_SOURCE",
    "authorization": "NONE",
    "authority": "NONE",
}
RESULT = {
    "source_status": "SOURCE_INDEXED",
    "independent_verification": "NOT_CHECKED",
    "current_applicability": "NOT_CHECKED",
    "freshness": "PINNED_HISTORICAL_SOURCE",
    "authorization": "NONE",
    "authority": "NONE",
}
SELECTION_POLICY = {
    "modules": "EXPLICIT_MODULE_LIST",
    "declarations": "USER_ORIGIN_SUPPORTED_WITH_RANGE",
    "ordering": "UTF16_LEXICOGRAPHIC",
    "type_references": "DIRECT_EXPR_CONST",
    "imports": "DIRECT_ONLY",
    "omissions": "NAMED_COUNTED",
}
LIMITS = {
    "max_declarations": 2500,
    "max_relations": 25000,
    "max_search_bytes": 750 * 1024,
    "max_shard_bytes": 512 * 1024,
    "max_manifest_bytes": 1024 * 1024,
    "max_projection_nodes": 50,
    "max_projection_edges": 100,
}
CONSTANT_KINDS = {"theorem", "definition", "opaque", "axiom", "inductive", "constructor"}
RELATIONS = {
    "DECLARES": ("SOURCE_MODULE", "SOURCE_DECLARATION"),
    "IMPORTS_MODULE": ("SOURCE_MODULE", "SOURCE_MODULE"),
    "TYPE_REFERENCES": ("SOURCE_DECLARATION", "SOURCE_DECLARATION"),
}
OMISSION_COUNTS = {"omitted_type_references", "omitted_imports", "omitted_declarations"}
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class CatalogueReplayError(ValueError):
    """Fail-closed replay result with a stable, bounded error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise CatalogueReplayError(code, message)


def _unicode(value: str) -> None:
    require(not any(0xD800 <= ord(char) <= 0xDFFF for char in value),
            "UNSUPPORTED_JSON_VALUE", "lone surrogate is not scalar Unicode")


def _utf16(value: str) -> bytes:
    return value.encode("utf-16-be")


def canonical_bytes(value: object) -> bytes:
    active: set[int] = set()

    def encode(item: object) -> str:
        if item is None:
            return "null"
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) is int:
            require(abs(item) <= MAX_SAFE_INTEGER, "UNSUPPORTED_JSON_VALUE", "integer outside safe range")
            return str(item)
        if type(item) is str:
            _unicode(item)
            return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        require(type(item) in (dict, list), "UNSUPPORTED_JSON_VALUE", "unsupported canonical value")
        require(id(item) not in active, "UNSUPPORTED_JSON_VALUE", "cyclic canonical value")
        active.add(id(item))
        try:
            if type(item) is list:
                return "[" + ",".join(encode(member) for member in item) + "]"
            for key in item:
                require(type(key) is str, "UNSUPPORTED_JSON_VALUE", "object keys must be strings")
                _unicode(key)
            return "{" + ",".join(encode(key) + ":" + encode(item[key]) for key in sorted(item, key=_utf16)) + "}"
        finally:
            active.remove(id(item))

    try:
        return encode(value).encode("utf-8")
    except RecursionError as error:
        raise CatalogueReplayError("UNSUPPORTED_JSON_VALUE", "canonical nesting limit exceeded") from error


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY", "duplicate JSON object member")
        result[key] = value
    return result


def _reject_float(value: str):
    _finite_float(value)
    raise CatalogueReplayError("UNSUPPORTED_JSON_VALUE", "floating-point JSON numbers are not admitted")


def _finite_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise CatalogueReplayError("NONFINITE_JSON_NUMBER", "invalid JSON number") from error
    if parsed in (float("inf"), float("-inf")) or parsed != parsed:
        raise CatalogueReplayError("NONFINITE_JSON_NUMBER", "non-finite JSON number")
    return parsed


def _reject_constant(value: str):
    raise CatalogueReplayError("NONFINITE_JSON_NUMBER", "non-finite JSON number")


def strict_load(raw: str | bytes | bytearray, *, maximum: int, canonical: bool) -> object:
    require(type(raw) in (str, bytes, bytearray), "INVALID_JSON", "expected JSON bytes or text")
    try:
        encoded = raw.encode("utf-8") if type(raw) is str else bytes(raw)
        require(len(encoded) <= maximum, "INPUT_TOO_LARGE", "input exceeds byte limit")
        text = encoded.decode("utf-8")
        require(not text.startswith("\ufeff"), "INVALID_UTF8", "UTF-8 BOM is not permitted")
    except UnicodeError as error:
        raise CatalogueReplayError("INVALID_UTF8", "expected scalar UTF-8 JSON") from error
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_float=_reject_float,
                           parse_constant=_reject_constant)
    except CatalogueReplayError:
        raise
    except (ValueError, RecursionError) as error:
        raise CatalogueReplayError("INVALID_JSON", "JSON syntax or parser limit") from error
    numeric = _JSON_STRING.sub('""', text)
    require(re.search(r'(?<![\w.])-0(?![\w.])', numeric) is None,
            "UNSUPPORTED_JSON_VALUE", "negative zero is not permitted")
    encoded_canonical = canonical_bytes(value)
    if canonical:
        require(encoded == encoded_canonical, "NONCANONICAL_JSON", "published bytes must be canonical")
    return value


def _shape(value: object, fields: set[str]) -> dict:
    require(type(value) is dict, "INVALID_FIELD_TYPE", "expected object")
    require(fields <= value.keys(), "MISSING_FIELD", "required field is missing")
    require(value.keys() <= fields, "UNKNOWN_FIELD", "unknown field is not permitted")
    return value


def _text(value: object) -> str:
    require(type(value) is str and bool(value.strip()), "INVALID_FIELD_TYPE", "expected nonempty string")
    _unicode(value)
    return value


def _integer(value: object, minimum: int = 0, maximum: int = MAX_SAFE_INTEGER) -> int:
    require(type(value) is int and minimum <= value <= maximum, "INVALID_FIELD_TYPE", "expected bounded integer")
    return value


def _digest(value: object, length: int = 64) -> str:
    value = _text(value)
    require(re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value) is not None,
            "INVALID_DIGEST", "expected lowercase hexadecimal digest")
    return value


def _path(value: object) -> str:
    value = _text(value)
    require(not value.startswith("/") and "\\" not in value and ":" not in value
            and all(part not in {"", ".", ".."} for part in value.split("/"))
            and not any(ord(char) < 32 or ord(char) == 127 for char in value),
            "INVALID_PATH", "expected safe relative path")
    return value


def _array(value: object) -> list:
    require(type(value) is list, "INVALID_FIELD_TYPE", "expected array")
    return value


def _ordered(values: list[str]) -> None:
    require(values == sorted(values, key=_utf16), "INVALID_ORDER", "expected UTF-16 lexicographic order")


def _unique(value: str, seen: set[str], code: str = "DUPLICATE_ID") -> None:
    _text(value)
    require(value not in seen, code, "duplicate catalogue identity")
    seen.add(value)


def _axes(value: dict) -> None:
    for field, expected in AXES.items():
        require(value.get(field) == expected and type(value.get(field)) is str,
                "AUTHORITY_ESCALATION", "source catalogue status boundary violated")


def _extensions(value: object) -> list:
    value = _array(value)
    seen = set()
    for extension in value:
        extension = _shape(extension, {"id", "version", "critical", "payload"})
        identity = (_text(extension["id"]), _integer(extension["version"], 1))
        require(type(extension["critical"]) is bool, "INVALID_FIELD_TYPE", "expected critical boolean")
        require(identity not in seen, "DUPLICATE_EXTENSION", "duplicate extension identity")
        seen.add(identity)
        require(not extension["critical"], "UNKNOWN_CRITICAL_EXTENSION", "critical extension is not understood")
        canonical_bytes(extension["payload"])
    return value


def _file(value: object, extra: set[str] = frozenset()) -> dict:
    value = _shape(value, {"path", "sha256"} | extra)
    _path(value["path"])
    _digest(value["sha256"])
    return value


def _identity(prefix: str, payload: dict) -> str:
    return prefix + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def module_id(repository: str, commit: str, module: str, path: str) -> str:
    return _identity("module-", {"repository": repository, "commit": commit, "module": module, "path": path})


def occurrence_id(repository: str, commit: str, module: str, path: str,
                  qualified_name: str, object_contract_version: int = 1) -> str:
    return _identity("object-", {"repository": repository, "commit": commit, "module": module, "path": path,
                                "qualified_name": qualified_name, "object_contract_version": object_contract_version})


def relation_id(catalogue_id: str, relation_type: str, source_id: str, target_id: str) -> str:
    return _identity("relation-", {"catalogue_id": catalogue_id, "relation_type": relation_type,
                                  "source_id": source_id, "target_id": target_id})


def _safe_file(root: Path, relative: str) -> Path:
    _path(relative)
    require(root.is_dir() and not root.is_symlink(), "UNSAFE_INPUT", "regular catalogue root required")
    root = root.resolve()
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
            "MISSING_PUBLICATION_FILE", "publication file missing or unsafe")
    require(not any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root)),
            "UNSAFE_INPUT", "symlink publication parent")
    return path


def _validate_policy(raw: bytes, expected_sha256: str) -> dict:
    _digest(expected_sha256)
    require(hashlib.sha256(raw).hexdigest() == expected_sha256,
            "POLICY_PIN_MISMATCH", "separately supplied policy digest mismatch")
    policy = strict_load(raw, maximum=MAX_POLICY_BYTES, canonical=True)
    policy = _shape(policy, {"schema", "policy_version", "catalogue_id", "manifest", "source_policy", "source",
                             "producer", "qualification_wrapper", "admitted_relations", "result", "extensions"})
    require(policy["schema"] == POLICY_SCHEMA and policy["policy_version"] == 1,
            "UNSUPPORTED_VERSION", "unsupported trust-policy version")
    _text(policy["catalogue_id"])
    _file(policy["manifest"], {"size_bytes"})
    _integer(policy["manifest"]["size_bytes"], 1, MAX_MANIFEST_BYTES)
    _file(policy["source_policy"])
    source = _shape(policy["source"], {"repository", "commit", "tree", "lean_toolchain", "modules"})
    _text(source["repository"]); _digest(source["commit"], 40); _digest(source["tree"], 40)
    toolchain = _shape(source["lean_toolchain"], {"value", "sha256"})
    _text(toolchain["value"]); _digest(toolchain["sha256"])
    names = set()
    for module in _array(source["modules"]):
        module = _shape(module, {"module", "path", "sha256", "size_bytes"})
        _unique(_text(module["module"]), names, "DUPLICATE_NAME")
        _path(module["path"]); _digest(module["sha256"]); _integer(module["size_bytes"], 1)
    _ordered([module["module"] for module in source["modules"]])
    producer = _shape(policy["producer"], {"source_commit", "contract_version", "sources"})
    _digest(producer["source_commit"], 40)
    require(producer["contract_version"] == 1 and type(producer["contract_version"]) is int,
            "UNSUPPORTED_VERSION", "unsupported producer contract")
    for file in _array(producer["sources"]): _file(file)
    _ordered([file["path"] for file in producer["sources"]])
    wrapper = _shape(policy["qualification_wrapper"], {"source_commit", "sources"})
    _digest(wrapper["source_commit"], 40)
    require(bool(_array(wrapper["sources"])), "MISSING_FIELD", "qualification wrapper source is required")
    for file in wrapper["sources"]: _file(file)
    _ordered([file["path"] for file in wrapper["sources"]])
    require(policy["admitted_relations"] == ["DECLARES", "IMPORTS_MODULE", "TYPE_REFERENCES"],
            "INVALID_POLICY", "unrecognized relation policy")
    require(policy["result"] == RESULT, "AUTHORITY_ESCALATION", "policy result boundary changed")
    _extensions(policy["extensions"])
    return policy


def _validate_manifest(raw: bytes, policy: dict) -> dict:
    pin = policy["manifest"]
    require(len(raw) == pin["size_bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
            "MANIFEST_PIN_MISMATCH", "manifest differs from trust policy")
    manifest = strict_load(raw, maximum=MAX_MANIFEST_BYTES, canonical=True)
    fields = {"schema", "catalogue_version", "catalogue_id", "source", "extractor", "selection_policy", "modules",
              "counts", "limits", "truncation", "reproduce_command", "search", "shards", "extensions"} | set(AXES)
    manifest = _shape(manifest, fields)
    require(manifest["schema"] == MANIFEST_SCHEMA and manifest["catalogue_version"] == 1,
            "UNSUPPORTED_VERSION", "unsupported manifest version")
    require(manifest["catalogue_id"] == policy["catalogue_id"], "POLICY_MISMATCH", "catalogue identity changed")
    _axes(manifest); _extensions(manifest["extensions"])
    source = _shape(manifest["source"], {"repository", "commit", "tree", "tag", "license", "citation",
                                                 "lean_toolchain", "lake_manifest", "root_module", "dependency_inventory_sha256"})
    _text(source["repository"]); _digest(source["commit"], 40); _digest(source["tree"], 40); _text(source["tag"])
    for field in ("license", "citation", "lake_manifest", "root_module"): _file(source[field])
    _file(source["lean_toolchain"], {"value"}); _text(source["lean_toolchain"]["value"])
    _digest(source["dependency_inventory_sha256"])
    expected_source = policy["source"]
    require({key: source[key] for key in ("repository", "commit", "tree")} ==
            {key: expected_source[key] for key in ("repository", "commit", "tree")},
            "SOURCE_PIN_MISMATCH", "source repository/commit/tree changed")
    require({key: source["lean_toolchain"][key] for key in ("value", "sha256")} == expected_source["lean_toolchain"],
            "SOURCE_PIN_MISMATCH", "toolchain source pin changed")
    extractor = _shape(manifest["extractor"], {"source_commit", "contract_version", "sources"})
    require(extractor == policy["producer"], "PRODUCER_PIN_MISMATCH", "producer identity changed")
    require(manifest["selection_policy"] == SELECTION_POLICY, "INVALID_POLICY", "selection semantics changed")
    require(manifest["limits"] == LIMITS, "COUNT_LIMIT_EXCEEDED", "declared limits changed")
    require(manifest["truncation"] == {"occurred": False, "reason": None},
            "TRUNCATION_NOT_PERMITTED", "bounded catalogue must be complete")
    _text(manifest["reproduce_command"])
    require("\n" not in manifest["reproduce_command"] and "\r" not in manifest["reproduce_command"],
            "INVALID_FIELD_TYPE", "reproduce command must be one line")
    modules = _array(manifest["modules"])
    require(bool(modules), "MISSING_FIELD", "selected modules required")
    module_ids, object_ids, paths, names, qualified = set(), set(), set(), set(), set()
    policy_modules = []
    for module in modules:
        module = _shape(module, {"module_id", "module", "path", "sha256", "size_bytes", "objects"})
        _text(module["module"]); _path(module["path"]); _digest(module["sha256"]); _integer(module["size_bytes"], 1)
        require(module["path"] == module["module"].replace(".", "/") + ".lean",
                "SOURCE_PIN_MISMATCH", "module path mismatch")
        require(module["module_id"] == module_id(source["repository"], source["commit"], module["module"], module["path"]),
                "IDENTITY_MISMATCH", "module identity mismatch")
        _unique(module["module_id"], module_ids); _unique(module["module"], names, "DUPLICATE_NAME"); _unique(module["path"], paths)
        policy_modules.append({key: module[key] for key in ("module", "path", "sha256", "size_bytes")})
        for obj in _array(module["objects"]):
            obj = _shape(obj, {"object_id", "qualified_name"})
            _text(obj["qualified_name"])
            require(obj["object_id"] == occurrence_id(source["repository"], source["commit"], module["module"], module["path"], obj["qualified_name"]),
                    "IDENTITY_MISMATCH", "occurrence inventory identity mismatch")
            _unique(obj["object_id"], object_ids); _unique(obj["qualified_name"], qualified, "DUPLICATE_NAME")
        _ordered([obj["qualified_name"] for obj in module["objects"]])
    _ordered([module["module"] for module in modules])
    require(policy_modules == expected_source["modules"], "SOURCE_PIN_MISMATCH", "selected module pins changed")
    shards = _array(manifest["shards"])
    require([shard.get("module_id") for shard in shards] == [module["module_id"] for module in modules],
            "SHARD_INVENTORY_MISMATCH", "one ordered shard per module is required")
    shard_digests = set()
    for metadata, module in zip(shards, modules):
        metadata = _shape(metadata, {"module_id", "path", "sha256", "size_bytes", "object_count", "relation_count"} | OMISSION_COUNTS)
        _digest(metadata["sha256"]); _unique(metadata["sha256"], shard_digests)
        require(metadata["path"] == f"shards/{metadata['sha256']}.json", "CONTENT_ADDRESS_MISMATCH", "shard path is not content addressed")
        _integer(metadata["size_bytes"], 1, MAX_SHARD_BYTES)
        for field in {"object_count", "relation_count"} | OMISSION_COUNTS: _integer(metadata[field])
        require(metadata["object_count"] == len(module["objects"]), "COUNT_MISMATCH", "shard object count mismatch")
        require(metadata["relation_count"] >= metadata["object_count"], "COUNT_MISMATCH", "DECLARES edge missing")
    counts = _shape(manifest["counts"], {"modules", "objects", "relations"} | OMISSION_COUNTS)
    for value in counts.values(): _integer(value)
    expected_counts = {"modules": len(modules), "objects": len(object_ids), "relations": sum(item["relation_count"] for item in shards)}
    expected_counts.update({field: sum(item[field] for item in shards) for field in OMISSION_COUNTS})
    require(counts == expected_counts, "COUNT_MISMATCH", "aggregate counts changed")
    require(counts["objects"] <= LIMITS["max_declarations"] and counts["relations"] <= LIMITS["max_relations"],
            "COUNT_LIMIT_EXCEEDED", "catalogue count budget exceeded")
    search = _file(manifest["search"], {"size_bytes", "object_count"})
    require(search["path"] == "search.json", "INVALID_PATH", "search path must be search.json")
    _integer(search["size_bytes"], 1, MAX_SEARCH_BYTES); _integer(search["object_count"])
    require(search["object_count"] == counts["objects"], "COUNT_MISMATCH", "search object count mismatch")
    return manifest


def _range(value: object, maximum: int) -> None:
    value = _shape(value, {"start", "end"})
    for point in value.values():
        point = _shape(point, {"line", "column", "byte"})
        _integer(point["line"], 1); _integer(point["column"], 0, maximum); _integer(point["byte"], 0, maximum)
        require(point["column"] <= point["byte"] and point["byte"] >= point["column"] + point["line"] - 1,
                "INVALID_RANGE", "impossible byte coordinate")
        if point["line"] == 1:
            require(point["byte"] == point["column"], "INVALID_RANGE", "first-line coordinate mismatch")
    start, end = value["start"], value["end"]
    require(start["byte"] < end["byte"] and (start["line"], start["column"]) < (end["line"], end["column"]),
            "INVALID_RANGE", "range must be nonempty and ordered")
    if start["line"] == end["line"]:
        require(end["byte"] - start["byte"] == end["column"] - start["column"],
                "INVALID_RANGE", "same-line coordinates disagree")


def _validate_shard(raw: bytes, manifest: dict, metadata: dict, endpoints: dict) -> dict:
    require(len(raw) == metadata["size_bytes"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"],
            "SHARD_INTEGRITY_MISMATCH", "shard digest or size changed")
    shard = strict_load(raw, maximum=MAX_SHARD_BYTES, canonical=True)
    shard = _shape(shard, {"schema", "catalogue_version", "catalogue_id", "module", "objects", "relations",
                           "omissions", "extensions"} | set(AXES))
    require(shard["schema"] == SHARD_SCHEMA and shard["catalogue_version"] == 1,
            "UNSUPPORTED_VERSION", "unsupported shard version")
    require(shard["catalogue_id"] == manifest["catalogue_id"], "SOURCE_PIN_MISMATCH", "shard catalogue changed")
    _axes(shard); _extensions(shard["extensions"])
    module = _shape(shard["module"], {"module_id", "module", "path", "sha256", "size_bytes", "repository", "commit", "tree"} | set(AXES))
    _axes(module)
    selected = next((entry for entry in manifest["modules"] if entry["module_id"] == module["module_id"]), None)
    require(selected is not None, "UNKNOWN_MODULE", "shard module is outside inventory")
    for field in ("module_id", "module", "path", "sha256", "size_bytes"):
        require(module[field] == selected[field], "SOURCE_PIN_MISMATCH", "shard module metadata changed")
    for field in ("repository", "commit", "tree"):
        require(module[field] == manifest["source"][field], "SOURCE_PIN_MISMATCH", "shard source identity changed")
    object_ids, object_names = set(), set()
    for obj in _array(shard["objects"]):
        obj = _shape(obj, {"object_id", "object_contract_version", "source", "qualified_name", "kind", "statement",
                           "statement_sha256", "extensions"} | set(AXES))
        _axes(obj); _extensions(obj["extensions"])
        require(obj["object_contract_version"] == 1 and type(obj["object_contract_version"]) is int,
                "UNSUPPORTED_VERSION", "unsupported object contract")
        require(obj["kind"] in CONSTANT_KINDS, "UNSUPPORTED_CONSTANT_KIND", "unadmitted constant kind")
        _text(obj["qualified_name"]); _text(obj["statement"]); _digest(obj["statement_sha256"])
        require(hashlib.sha256(obj["statement"].encode("utf-8")).hexdigest() == obj["statement_sha256"],
                "STATEMENT_INTEGRITY_MISMATCH", "statement digest changed")
        source = _shape(obj["source"], {"repository", "commit", "tree", "module", "path", "range"})
        for field in ("repository", "commit", "tree", "module", "path"):
            require(source[field] == module[field], "SOURCE_PIN_MISMATCH", "object source occurrence changed")
        _range(source["range"], module["size_bytes"])
        require(obj["object_id"] == occurrence_id(source["repository"], source["commit"], source["module"], source["path"], obj["qualified_name"]),
                "IDENTITY_MISMATCH", "object identity changed")
        _unique(obj["object_id"], object_ids); _unique(obj["qualified_name"], object_names, "DUPLICATE_NAME")
    _ordered([obj["qualified_name"] for obj in shard["objects"]])
    require([{"object_id": obj["object_id"], "qualified_name": obj["qualified_name"]} for obj in shard["objects"]] == selected["objects"],
            "OBJECT_INVENTORY_MISMATCH", "shard objects differ from manifest")
    relation_ids, declares = set(), set()
    for relation in _array(shard["relations"]):
        relation = _shape(relation, {"relation_id", "type", "source_id", "target_id", "source_kind", "target_kind",
                                     "authority", "logical_implication", "semantic_equivalence", "extensions"})
        require(relation["type"] in RELATIONS, "UNSUPPORTED_RELATION", "unadmitted relation meaning")
        require(relation["authority"] == "NONE" and relation["logical_implication"] is False
                and relation["semantic_equivalence"] is False,
                "AUTHORITY_ESCALATION", "structural relation was promoted")
        _extensions(relation["extensions"])
        require(relation["source_id"] in endpoints and relation["target_id"] in endpoints,
                "UNKNOWN_ENDPOINT", "relation endpoint is outside inventory")
        expected_kinds = RELATIONS[relation["type"]]
        source_endpoint, target_endpoint = endpoints[relation["source_id"]], endpoints[relation["target_id"]]
        require((relation["source_kind"], relation["target_kind"]) == expected_kinds
                and (source_endpoint[0], target_endpoint[0]) == expected_kinds,
                "ENDPOINT_KIND_MISMATCH", "relation endpoint kind mismatch")
        require(source_endpoint[1] == module["module_id"], "RELATION_PROVENANCE_MISMATCH", "relation originates outside shard")
        if relation["type"] == "DECLARES":
            require(target_endpoint[1] == module["module_id"], "RELATION_PROVENANCE_MISMATCH", "DECLARES crosses module")
            declares.add(relation["target_id"])
        require(relation["relation_id"] == relation_id(manifest["catalogue_id"], relation["type"], relation["source_id"], relation["target_id"]),
                "IDENTITY_MISMATCH", "relation identity changed")
        _unique(relation["relation_id"], relation_ids)
    _ordered([relation["relation_id"] for relation in shard["relations"]])
    require(declares == object_ids, "MISSING_DECLARES", "each object needs one DECLARES route")
    omissions = _shape(shard["omissions"], {"type_references", "imports", "declarations"})
    for value in omissions.values(): _array(value)
    all_names = {obj["qualified_name"] for module_entry in manifest["modules"] for obj in module_entry["objects"]}
    seen = set()
    for omission in omissions["type_references"]:
        omission = _shape(omission, {"source_id", "target_name"})
        require(omission["source_id"] in object_ids and _text(omission["target_name"]) not in all_names,
                "INVALID_OMISSION", "type omission is not out of slice")
        _unique(canonical_bytes(omission).decode("utf-8"), seen)
    _ordered([item["source_id"] + "\0" + item["target_name"] for item in omissions["type_references"]])
    seen = set()
    selected_modules = {entry["module"] for entry in manifest["modules"]}
    for name in omissions["imports"]:
        require(_text(name) not in selected_modules, "INVALID_OMISSION", "selected import cannot be omitted")
        _unique(name, seen)
    _ordered(omissions["imports"])
    seen = set()
    for omission in omissions["declarations"]:
        omission = _shape(omission, {"qualified_name", "kind", "reason"})
        require(_text(omission["qualified_name"]) not in all_names and omission["reason"] in {"GENERATED", "MISSING_RANGE", "UNSUPPORTED_KIND"},
                "INVALID_OMISSION", "declaration omission is invalid")
        _text(omission["kind"]); _unique(omission["qualified_name"], seen)
    _ordered([item["qualified_name"] for item in omissions["declarations"]])
    expected_counts = {"object_count": len(shard["objects"]), "relation_count": len(shard["relations"]),
                       "omitted_type_references": len(omissions["type_references"]),
                       "omitted_imports": len(omissions["imports"]),
                       "omitted_declarations": len(omissions["declarations"])}
    require(all(metadata[field] == value for field, value in expected_counts.items()),
            "COUNT_MISMATCH", "shard counts changed")
    return shard


def validate_publication(catalogue_root: Path | str, policy_path: Path | str, policy_sha256: str) -> dict:
    root, policy_path = Path(catalogue_root), Path(policy_path)
    require(policy_path.is_file() and not policy_path.is_symlink(), "UNSAFE_INPUT", "regular policy file required")
    policy = _validate_policy(policy_path.read_bytes(), policy_sha256)
    manifest_raw = _safe_file(root, policy["manifest"]["path"]).read_bytes()
    manifest = _validate_manifest(manifest_raw, policy)
    endpoints = {module["module_id"]: ("SOURCE_MODULE", module["module_id"]) for module in manifest["modules"]}
    endpoints.update({obj["object_id"]: ("SOURCE_DECLARATION", module["module_id"])
                      for module in manifest["modules"] for obj in module["objects"]})
    shards, expected_search = [], []
    for metadata in manifest["shards"]:
        shard = _validate_shard(_safe_file(root, metadata["path"]).read_bytes(), manifest, metadata, endpoints)
        shards.append(shard)
        for obj in shard["objects"]:
            expected_search.append({"object_id": obj["object_id"], "qualified_name": obj["qualified_name"],
                                    "module": obj["source"]["module"], "kind": obj["kind"], "statement": obj["statement"]})
    expected_search.sort(key=lambda item: _utf16(item["qualified_name"]))
    search_raw = _safe_file(root, manifest["search"]["path"]).read_bytes()
    require(len(search_raw) == manifest["search"]["size_bytes"]
            and hashlib.sha256(search_raw).hexdigest() == manifest["search"]["sha256"],
            "SEARCH_INTEGRITY_MISMATCH", "search bytes changed")
    search = strict_load(search_raw, maximum=MAX_SEARCH_BYTES, canonical=True)
    require(search == expected_search, "SEARCH_DERIVATION_MISMATCH", "search is not derived from source occurrences")
    expected_paths = {"manifest.json", "search.json", *(metadata["path"] for metadata in manifest["shards"])}
    actual_paths = set()
    for path in root.rglob("*"):
        require(not path.is_symlink(), "UNSAFE_INPUT", "symlink publication entry")
        if path.is_file(): actual_paths.add(path.relative_to(root).as_posix())
    require(actual_paths == expected_paths, "PUBLICATION_INVENTORY_MISMATCH", "publication has missing or extra bytes")
    raw_files = [_safe_file(root, relative).read_bytes() for relative in sorted(expected_paths)]
    require(sum(map(len, raw_files)) <= MAX_PUBLICATION_BYTES, "INPUT_TOO_LARGE", "publication raw budget exceeded")
    require(sum(len(gzip.compress(raw, mtime=0)) for raw in raw_files) <= MAX_PUBLICATION_GZIP_BYTES,
            "INPUT_TOO_LARGE", "publication gzip budget exceeded")
    return {"policy": policy, "manifest": manifest, "shards": shards, "search": search, "result": dict(RESULT)}


def replay(catalogue_root: Path | str, policy_path: Path | str, policy_sha256: str) -> dict:
    return validate_publication(catalogue_root, policy_path, policy_sha256)["result"]


def _audit() -> dict:
    forbidden = sorted(name for name in sys.modules if name == "mathgraph" or name.startswith("mathgraph.")
                       or name == "mathgraph_protocol" or name.startswith("mathgraph_protocol."))
    return {"isolated": bool(sys.flags.isolated), "no_site": bool(sys.flags.no_site),
            "dont_write_bytecode": bool(sys.dont_write_bytecode), "forbidden_imports": forbidden,
            "network_access": "NOT_USED", "proof_replay": "NOT_PERFORMED", "source_bytes": "NOT_PRESENT"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue-root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--audit-imports", action="store_true")
    args = parser.parse_args()
    try:
        result = replay(args.catalogue_root, args.policy, args.policy_sha256)
    except (CatalogueReplayError, OSError) as error:
        print(f"CATALOGUE_REPLAY_DECLINED: {error}", file=sys.stderr)
        return 2
    if args.audit_imports:
        print(json.dumps(_audit(), sort_keys=True, separators=(",", ":")), file=sys.stderr)
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CatalogueReplayError", "canonical_bytes", "strict_load", "validate_publication", "replay"]
