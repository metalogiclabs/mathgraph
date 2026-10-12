"""Portable, network-free source catalogue contracts; no mathematical authority.

V1 canonical bytes are restricted RFC 8785 JCS: null, bool, scalar Unicode,
safe integers, lists, and string-keyed dictionaries. Keys sort by UTF-16 code
units, strings keep their code points, and output is UTF-8 with no newline.
Identity payload keys are exactly the public function argument names (the
relation payload uses ``relation_type``). Hashes bind source occurrences, never
semantic equivalence. JSON Schemas document shape; this standard-library
validator also closes identities, counts, pins, and relation provenance.

Ranges use one-based lines, zero-based UTF-8 byte columns and absolute byte
offsets, with an exclusive end. File-byte bounds and coordinate order are
checked here; matching coordinates to actual source bytes belongs to extraction.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .json_strict import DuplicateKeyError, NonFiniteNumberError, strict_json_loads


MANIFEST_SCHEMA = "mathgraph.source-catalogue-manifest.v1"
SHARD_SCHEMA = "mathgraph.source-catalogue-shard.v1"
MAX_SAFE_INTEGER = 9007199254740991
LIMITS = {"max_declarations": 2500, "max_relations": 25000,
          "max_search_bytes": 2 * 1024 * 1024, "max_shard_bytes": 2 * 1024 * 1024,
          "max_manifest_bytes": 1024 * 1024, "max_projection_nodes": 50,
          "max_projection_edges": 100}
AXES = {"source_status": "SOURCE_INDEXED", "verification_status": "NOT_CHECKED",
        "current_applicability": "NOT_CHECKED", "freshness": "PINNED_HISTORICAL_SOURCE",
        "authorization": "NONE", "authority": "NONE"}
SELECTION_POLICY = {"modules": "EXPLICIT_MODULE_LIST", "declarations": "USER_ORIGIN_SUPPORTED_WITH_RANGE",
                    "ordering": "UTF16_LEXICOGRAPHIC", "type_references": "DIRECT_EXPR_CONST",
                    "imports": "DIRECT_ONLY", "omissions": "NAMED_COUNTED"}
CONSTANT_KINDS = frozenset({"theorem", "definition", "opaque", "axiom", "inductive", "constructor"})
RELATION_KINDS = {"DECLARES": ("SOURCE_MODULE", "SOURCE_DECLARATION"),
                  "IMPORTS_MODULE": ("SOURCE_MODULE", "SOURCE_MODULE"),
                  "TYPE_REFERENCES": ("SOURCE_DECLARATION", "SOURCE_DECLARATION")}
OMISSION_COUNTS = {"omitted_type_references", "omitted_imports", "omitted_declarations"}
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class SourceCatalogueError(ValueError):
    """Deterministic decline with a stable code and bounded explanatory message."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise SourceCatalogueError(code, message)


def _unicode(value: str) -> None:
    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value),
             "UNSUPPORTED_JSON_VALUE", "lone surrogate is not scalar Unicode")


def _key(value: str) -> bytes:
    return value.encode("utf-16-be")


def canonical_bytes(value: object) -> bytes:
    """Encode the restricted JCS domain; reject coercion, floats, and cycles."""
    active: set[int] = set()

    def encode(item: Any) -> str:
        if item is None:
            return "null"
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) is int:
            _require(abs(item) <= MAX_SAFE_INTEGER, "UNSUPPORTED_JSON_VALUE", "integer outside safe range")
            return str(item)
        if type(item) is str:
            _unicode(item)
            return json.dumps(item, ensure_ascii=False)
        _require(type(item) in (dict, list), "UNSUPPORTED_JSON_VALUE", "unsupported canonical value type")
        _require(id(item) not in active, "UNSUPPORTED_JSON_VALUE", "cyclic canonical value")
        active.add(id(item))
        try:
            if type(item) is list:
                return "[" + ",".join(encode(member) for member in item) + "]"
            for name in item:
                _require(type(name) is str, "UNSUPPORTED_JSON_VALUE", "object key must be a string")
                _unicode(name)
            return "{" + ",".join(encode(name) + ":" + encode(item[name]) for name in sorted(item, key=_key)) + "}"
        finally:
            active.remove(id(item))

    try:
        return encode(value).encode("utf-8")
    except RecursionError as error:
        raise SourceCatalogueError("UNSUPPORTED_JSON_VALUE", "canonical nesting limit exceeded") from error


def _identity(prefix: str, payload: dict) -> str:
    return prefix + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def module_id(repository: str, commit: str, module: str, path: str) -> str:
    """Bind repository, commit, module, and path; tree is checked by the source pin."""
    for value in (repository, commit, module, path):
        _text(value)
    return _identity("module-", {"repository": repository, "commit": commit, "module": module, "path": path})


def occurrence_id(repository: str, commit: str, module: str, path: str,
                  qualified_name: str, object_contract_version: int = 1) -> str:
    """Bind a declaration occurrence, without interpreting its mathematical type."""
    for value in (repository, commit, module, path, qualified_name):
        _text(value)
    _integer(object_contract_version, 1)
    return _identity("object-", {"repository": repository, "commit": commit, "module": module, "path": path,
                                "qualified_name": qualified_name, "object_contract_version": object_contract_version})


def relation_id(catalogue_id: str, relation_type: str, source_id: str, target_id: str) -> str:
    """Bind the named source relation and its direction within one catalogue."""
    for value in (catalogue_id, relation_type, source_id, target_id):
        _text(value)
    return _identity("relation-", {"catalogue_id": catalogue_id, "relation_type": relation_type,
                                  "source_id": source_id, "target_id": target_id})


def _load(document: str | bytes | bytearray | dict, maximum: int) -> dict:
    if type(document) is dict:
        raw = canonical_bytes(document)
        _require(len(raw) <= maximum, "INPUT_TOO_LARGE", "document exceeds byte limit")
        return strict_json_loads(raw)
    _require(type(document) in (str, bytes, bytearray), "INVALID_JSON", "expected JSON text, bytes, or object")
    try:
        if type(document) is str:
            raw = document.encode("utf-8")
        else:
            raw = bytes(document)
        _require(len(raw) <= maximum, "INPUT_TOO_LARGE", "document exceeds byte limit")
        text = raw.decode("utf-8")
        _require(not text.startswith("\ufeff"), "INVALID_UTF8", "UTF-8 BOM is not permitted")
    except UnicodeError as error:
        raise SourceCatalogueError("INVALID_UTF8", "expected scalar UTF-8 JSON") from error
    try:
        value = strict_json_loads(text)
    except DuplicateKeyError as error:
        raise SourceCatalogueError("DUPLICATE_JSON_KEY", "duplicate JSON object member") from error
    except NonFiniteNumberError as error:
        raise SourceCatalogueError("NONFINITE_JSON_NUMBER", "non-finite JSON number") from error
    except (ValueError, RecursionError) as error:
        raise SourceCatalogueError("INVALID_JSON", "JSON syntax or parser limit") from error
    # strict_json_loads intentionally preserves ordinary integers; JSON -0
    # needs a lexical check before that distinction disappears.
    numeric_text = _JSON_STRING.sub('""', text)
    _require(re.search(r'(?<![\w.])-0(?![\w.])', numeric_text) is None,
             "UNSUPPORTED_JSON_VALUE", "negative zero is not permitted")
    canonical_bytes(value)
    return value


def _shape(value: Any, fields: set[str]) -> None:
    _require(type(value) is dict, "INVALID_FIELD_TYPE", "expected object")
    _require(fields <= value.keys(), "MISSING_FIELD", "required field is missing")
    _require(value.keys() <= fields, "UNKNOWN_FIELD", "unknown field is not permitted")


def _text(value: Any) -> None:
    _require(type(value) is str and bool(value.strip()), "INVALID_FIELD_TYPE", "expected nonempty string")
    _unicode(value)


def _integer(value: Any, minimum: int = 0, maximum: int = MAX_SAFE_INTEGER) -> None:
    _require(type(value) is int and minimum <= value <= maximum, "INVALID_FIELD_TYPE", "expected bounded integer")


def _digest(value: Any, length: int = 64) -> None:
    _text(value)
    _require(re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value) is not None,
             "INVALID_DIGEST", "expected lowercase hexadecimal digest")


def _path(value: Any) -> None:
    _text(value)
    _require(not value.startswith("/") and "\\" not in value and ":" not in value
             and all(part not in {"", ".", ".."} for part in value.split("/"))
             and not any(ord(c) < 32 or ord(c) == 127 for c in value),
             "INVALID_PATH", "expected safe relative path")


def _array(value: Any) -> None:
    _require(type(value) is list, "INVALID_FIELD_TYPE", "expected array")


def _unique(value: str, seen: set[str], code: str = "DUPLICATE_ID") -> None:
    _text(value)
    _require(value not in seen, code, "duplicate catalogue identity")
    seen.add(value)


def _ordered(values: list[str]) -> None:
    _require(values == sorted(values, key=_key), "INVALID_ORDER", "expected UTF-16 lexicographic order")


def _axes(value: dict) -> None:
    for field, expected in AXES.items():
        _require(type(value[field]) is str and value[field] == expected,
                 "AUTHORITY_ESCALATION", "source catalogue status boundary violated")


def _extensions(value: Any) -> None:
    _array(value)
    seen: set[tuple[str, int]] = set()
    for extension in value:
        _shape(extension, {"id", "version", "critical", "payload"})
        _text(extension["id"])
        _integer(extension["version"], 1)
        _require(type(extension["critical"]) is bool, "INVALID_FIELD_TYPE", "expected critical boolean")
        identity = (extension["id"], extension["version"])
        _require(identity not in seen, "DUPLICATE_EXTENSION", "extension id and version must be unique")
        seen.add(identity)
        _require(not extension["critical"], "UNKNOWN_CRITICAL_EXTENSION", "no critical extensions are recognized by v1")
        canonical_bytes(extension["payload"])


def _file(value: dict, extra: set[str] = frozenset()) -> None:
    _shape(value, {"path", "sha256"} | extra)
    _path(value["path"])
    _digest(value["sha256"])


def validate_manifest(document: str | bytes | bytearray | dict) -> dict:
    """Validate source pins and the closed inventory; return an independent copy."""
    result = _load(document, LIMITS["max_manifest_bytes"])
    _shape(result, {"schema", "catalogue_version", "catalogue_id", "source", "extractor", "selection_policy",
                    "modules", "counts", "limits", "truncation", "reproduce_command", "search", "shards", "extensions"} | AXES.keys())
    _require(result["schema"] == MANIFEST_SCHEMA and type(result["catalogue_version"]) is int
             and result["catalogue_version"] == 1, "UNSUPPORTED_VERSION", "unsupported manifest version")
    _text(result["catalogue_id"])
    _axes(result)
    _extensions(result["extensions"])
    source = result["source"]
    _shape(source, {"repository", "commit", "tree", "tag", "license", "citation", "lean_toolchain",
                    "lake_manifest", "root_module", "dependency_inventory_sha256"})
    _text(source["repository"])
    _text(source["tag"])
    _digest(source["commit"], 40)
    _digest(source["tree"], 40)
    _digest(source["dependency_inventory_sha256"])
    for field in ("license", "citation", "lake_manifest", "root_module"):
        _file(source[field])
    _file(source["lean_toolchain"], {"value"})
    _text(source["lean_toolchain"]["value"])
    extractor = result["extractor"]
    _shape(extractor, {"source_commit", "contract_version", "sources"})
    _digest(extractor["source_commit"], 40)
    _require(type(extractor["contract_version"]) is int and extractor["contract_version"] == 1,
             "UNSUPPORTED_VERSION", "unsupported extractor contract")
    _array(extractor["sources"])
    _require(bool(extractor["sources"]), "MISSING_FIELD", "extractor sources must be pinned")
    source_paths: set[str] = set()
    for entry in extractor["sources"]:
        _file(entry)
        _unique(entry["path"], source_paths)
    _ordered([entry["path"] for entry in extractor["sources"]])
    _shape(result["selection_policy"], set(SELECTION_POLICY))
    _require(result["selection_policy"] == SELECTION_POLICY, "INVALID_POLICY", "unsupported selection or ordering policy")
    _shape(result["limits"], set(LIMITS))
    for name, ceiling in LIMITS.items():
        _integer(result["limits"][name], 1, ceiling)
    _require(len(canonical_bytes(result)) <= result["limits"]["max_manifest_bytes"],
             "INPUT_TOO_LARGE", "manifest exceeds declared byte limit")
    _shape(result["truncation"], {"occurred", "reason"})
    _require(result["truncation"]["occurred"] is False and result["truncation"]["reason"] is None,
             "TRUNCATION_NOT_PERMITTED", "v1 requires complete bounded publication")
    _text(result["reproduce_command"])
    _require("\n" not in result["reproduce_command"] and "\r" not in result["reproduce_command"],
             "INVALID_FIELD_TYPE", "replay command must be a single descriptive command")
    _array(result["modules"])
    _require(bool(result["modules"]), "MISSING_FIELD", "selected modules are required")
    module_ids: set[str] = set()
    paths: set[str] = set()
    names: set[str] = set()
    object_ids: set[str] = set()
    qualified_names: set[str] = set()
    for module in result["modules"]:
        _shape(module, {"module_id", "module", "path", "sha256", "size_bytes", "objects"})
        _text(module["module"])
        _path(module["path"])
        _require(module["path"] == module["module"].replace(".", "/") + ".lean", "SOURCE_MISMATCH", "module path mismatch")
        _digest(module["sha256"])
        _integer(module["size_bytes"], 1)
        expected = module_id(source["repository"], source["commit"], module["module"], module["path"])
        _require(module["module_id"] == expected, "IDENTITY_MISMATCH", "module identity mismatch")
        _unique(module["module_id"], module_ids)
        _unique(module["path"], paths)
        _unique(module["module"], names)
        _array(module["objects"])
        for obj in module["objects"]:
            _shape(obj, {"object_id", "qualified_name"})
            _text(obj["qualified_name"])
            expected = occurrence_id(source["repository"], source["commit"], module["module"], module["path"], obj["qualified_name"])
            _require(obj["object_id"] == expected, "IDENTITY_MISMATCH", "occurrence inventory identity mismatch")
            _unique(obj["object_id"], object_ids)
            _unique(obj["qualified_name"], qualified_names, "DUPLICATE_NAME")
        _ordered([obj["qualified_name"] for obj in module["objects"]])
    _ordered([module["module"] for module in result["modules"]])
    _array(result["shards"])
    for entry in result["shards"]:
        _shape(entry, {"module_id", "path", "sha256", "size_bytes", "object_count", "relation_count"} | OMISSION_COUNTS)
    _require([entry["module_id"] for entry in result["shards"]]
             == [module["module_id"] for module in result["modules"]], "SHARD_INVENTORY_MISMATCH", "one ordered shard per module is required")
    shard_digests: set[str] = set()
    for entry, module in zip(result["shards"], result["modules"]):
        _shape(entry, {"module_id", "path", "sha256", "size_bytes", "object_count", "relation_count"} | OMISSION_COUNTS)
        _digest(entry["sha256"])
        _unique(entry["sha256"], shard_digests)
        _require(entry["path"] == f"shards/{entry['sha256']}.json", "CONTENT_ADDRESS_MISMATCH", "shard filename must equal digest")
        _integer(entry["size_bytes"], 1, result["limits"]["max_shard_bytes"])
        for name in {"object_count", "relation_count"} | OMISSION_COUNTS:
            _integer(entry[name])
        _require(entry["object_count"] == len(module["objects"]), "COUNT_MISMATCH", "shard occurrence count mismatch")
        _require(entry["relation_count"] >= entry["object_count"], "COUNT_MISMATCH", "every occurrence requires DECLARES")
    _shape(result["counts"], {"modules", "objects", "relations"} | OMISSION_COUNTS)
    counts = result["counts"]
    for value in counts.values():
        _integer(value)
    expected_counts = {"modules": len(module_ids), "objects": len(object_ids),
                       "relations": sum(s["relation_count"] for s in result["shards"])}
    expected_counts.update({name: sum(s[name] for s in result["shards"]) for name in OMISSION_COUNTS})
    _require(counts == expected_counts, "COUNT_MISMATCH", "manifest aggregate count mismatch")
    _require(counts["objects"] <= result["limits"]["max_declarations"]
             and counts["relations"] <= result["limits"]["max_relations"], "COUNT_LIMIT_EXCEEDED", "catalogue exceeds declared count limit")
    search = result["search"]
    _file(search, {"size_bytes", "object_count"})
    _require(search["path"] == "search.json", "INVALID_PATH", "search publication must be search.json")
    _integer(search["size_bytes"], 1, result["limits"]["max_search_bytes"])
    _integer(search["object_count"])
    _require(search["object_count"] == counts["objects"], "COUNT_MISMATCH", "search occurrence count mismatch")
    return result


def _range(value: dict, maximum: int) -> None:
    _shape(value, {"start", "end"})
    for position in value.values():
        _shape(position, {"line", "column", "byte"})
        _integer(position["line"], 1)
        _integer(position["column"], 0, maximum)
        _integer(position["byte"], 0, maximum)
        _require(position["column"] <= position["byte"], "INVALID_RANGE", "column exceeds absolute offset")
        _require(position["line"] <= position["byte"] + 1, "INVALID_RANGE", "line exceeds possible preceding newlines")
        _require(position["byte"] >= position["column"] + position["line"] - 1,
                 "INVALID_RANGE", "column leaves insufficient preceding newline bytes")
        if position["line"] == 1:
            _require(position["byte"] == position["column"], "INVALID_RANGE", "first-line byte and column disagree")
    start, end = value["start"], value["end"]
    _require(start["byte"] < end["byte"] and (start["line"], start["column"]) < (end["line"], end["column"]),
             "INVALID_RANGE", "range must be nonempty and ordered")
    _require(end["line"] - start["line"] <= end["byte"] - start["byte"],
             "INVALID_RANGE", "line interval exceeds possible newline bytes")
    if start["line"] == end["line"]:
        _require(end["byte"] - start["byte"] == end["column"] - start["column"],
                 "INVALID_RANGE", "same-line byte coordinates disagree")
    else:
        _require(end["byte"] - start["byte"] >= end["line"] - start["line"] + end["column"],
                 "INVALID_RANGE", "multiline interval cannot contain newlines and final column")


def validate_shard(document: str | bytes | bytearray | dict, manifest: dict) -> dict:
    """Validate one canonical content-addressed shard against a closed manifest."""
    manifest = validate_manifest(manifest)
    result = _load(document, manifest["limits"]["max_shard_bytes"])
    _shape(result, {"schema", "catalogue_version", "catalogue_id", "module", "objects", "relations", "omissions", "extensions"} | AXES.keys())
    _require(result["schema"] == SHARD_SCHEMA and type(result["catalogue_version"]) is int
             and result["catalogue_version"] == 1, "UNSUPPORTED_VERSION", "unsupported shard version")
    _require(result["catalogue_id"] == manifest["catalogue_id"], "SOURCE_MISMATCH", "shard catalogue mismatch")
    _axes(result)
    _extensions(result["extensions"])
    module = result["module"]
    _shape(module, {"module_id", "module", "path", "sha256", "size_bytes", "repository", "commit", "tree"} | AXES.keys())
    _axes(module)
    _integer(module["size_bytes"], 1)
    selected = next((m for m in manifest["modules"] if m["module_id"] == module["module_id"]), None)
    _require(selected is not None, "UNKNOWN_MODULE", "shard module is outside selected inventory")
    for field in ("module_id", "module", "path", "sha256", "size_bytes"):
        _require(module[field] == selected[field], "SOURCE_MISMATCH", "shard module metadata mismatch")
    for field in ("repository", "commit", "tree"):
        _require(module[field] == manifest["source"][field], "SOURCE_MISMATCH", "shard source pin mismatch")
    metadata = next(s for s in manifest["shards"] if s["module_id"] == module["module_id"])
    raw = canonical_bytes(result)
    if type(document) is not dict:
        document_raw = document.encode("utf-8") if type(document) is str else bytes(document)
        _require(document_raw == raw, "NONCANONICAL_SHARD", "published shard bytes must be canonical")
    _require(len(raw) == metadata["size_bytes"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"],
             "SHARD_INTEGRITY_MISMATCH", "shard byte size or digest mismatch")
    _array(result["objects"])
    object_ids: set[str] = set()
    names: set[str] = set()
    for obj in result["objects"]:
        _shape(obj, {"object_id", "object_contract_version", "source", "qualified_name", "kind", "statement", "statement_sha256", "extensions"} | AXES.keys())
        _axes(obj)
        _extensions(obj["extensions"])
        _require(type(obj["object_contract_version"]) is int and obj["object_contract_version"] == 1,
                 "UNSUPPORTED_VERSION", "unsupported occurrence contract")
        _text(obj["kind"])
        _require(obj["kind"] in CONSTANT_KINDS, "UNSUPPORTED_CONSTANT_KIND", "constant kind is not admitted")
        _text(obj["qualified_name"])
        _text(obj["statement"])
        _digest(obj["statement_sha256"])
        _require(hashlib.sha256(obj["statement"].encode("utf-8")).hexdigest() == obj["statement_sha256"],
                 "STATEMENT_INTEGRITY_MISMATCH", "rendered statement digest mismatch")
        _shape(obj["source"], {"repository", "commit", "tree", "module", "path", "range"})
        for field in ("repository", "commit", "tree", "module", "path"):
            _require(obj["source"][field] == module[field], "SOURCE_MISMATCH", "occurrence source pin mismatch")
        _range(obj["source"]["range"], module["size_bytes"])
        _unique(obj["object_id"], object_ids)
        _unique(obj["qualified_name"], names, "DUPLICATE_NAME")
    _ordered([obj["qualified_name"] for obj in result["objects"]])
    _require([{"object_id": o["object_id"], "qualified_name": o["qualified_name"]} for o in result["objects"]]
             == selected["objects"], "OBJECT_INVENTORY_MISMATCH", "shard must exactly match occurrence inventory")
    endpoints = {m["module_id"]: ("SOURCE_MODULE", m["module_id"]) for m in manifest["modules"]}
    endpoints.update({o["object_id"]: ("SOURCE_DECLARATION", m["module_id"])
                      for m in manifest["modules"] for o in m["objects"]})
    _array(result["relations"])
    relation_ids: set[str] = set()
    declares: set[str] = set()
    for relation in result["relations"]:
        _shape(relation, {"relation_id", "type", "source_id", "target_id", "source_kind", "target_kind",
                          "authority", "logical_implication", "semantic_equivalence", "extensions"})
        _text(relation["type"])
        _require(relation["type"] in RELATION_KINDS, "UNSUPPORTED_RELATION", "relation meaning is not admitted")
        _require(relation["authority"] == "NONE" and relation["logical_implication"] is False
                 and relation["semantic_equivalence"] is False, "AUTHORITY_ESCALATION", "relation carries unadmitted meaning")
        _extensions(relation["extensions"])
        _text(relation["source_id"])
        _text(relation["target_id"])
        _require(relation["source_id"] in endpoints and relation["target_id"] in endpoints,
                 "UNKNOWN_ENDPOINT", "relation endpoint is outside inventory")
        source, target = endpoints[relation["source_id"]], endpoints[relation["target_id"]]
        expected_kinds = RELATION_KINDS[relation["type"]]
        _require((relation["source_kind"], relation["target_kind"]) == expected_kinds
                 and (source[0], target[0]) == expected_kinds, "ENDPOINT_KIND_MISMATCH", "relation endpoint kinds mismatch")
        _require(source[1] == module["module_id"], "RELATION_PROVENANCE_MISMATCH", "relation must originate in this shard")
        if relation["type"] == "DECLARES":
            _require(target[1] == module["module_id"], "RELATION_PROVENANCE_MISMATCH", "DECLARES must stay in this module")
            declares.add(relation["target_id"])
        expected = relation_id(result["catalogue_id"], relation["type"], relation["source_id"], relation["target_id"])
        _require(relation["relation_id"] == expected, "IDENTITY_MISMATCH", "relation identity mismatch")
        _unique(relation["relation_id"], relation_ids)
    _ordered([r["relation_id"] for r in result["relations"]])
    _require(declares == object_ids, "MISSING_DECLARES", "every occurrence must be declared by this module")
    _shape(result["omissions"], {"type_references", "imports", "declarations"})
    omissions = result["omissions"]
    for entries in omissions.values():
        _array(entries)
    omitted_refs: set[str] = set()
    for entry in omissions["type_references"]:
        _shape(entry, {"source_id", "target_name"})
        _text(entry["source_id"])
        _text(entry["target_name"])
        _require(entry["source_id"] in object_ids and entry["target_name"] not in {o["qualified_name"] for m in manifest["modules"] for o in m["objects"]},
                 "INVALID_OMISSION", "type omission must name an out-of-slice target")
        _unique(canonical_bytes(entry).decode("utf-8"), omitted_refs)
    _ordered([entry["source_id"] + "\0" + entry["target_name"] for entry in omissions["type_references"]])
    omitted_imports: set[str] = set()
    for entry in omissions["imports"]:
        _text(entry)
        _require(entry not in {m["module"] for m in manifest["modules"]}, "INVALID_OMISSION", "import omission must name an out-of-slice module")
        _unique(entry, omitted_imports)
    _ordered(omissions["imports"])
    omitted_declarations: set[str] = set()
    for entry in omissions["declarations"]:
        _shape(entry, {"qualified_name", "kind", "reason"})
        _text(entry["qualified_name"])
        _text(entry["kind"])
        _text(entry["reason"])
        _require(entry["reason"] in {"GENERATED", "MISSING_RANGE", "UNSUPPORTED_KIND"}, "INVALID_OMISSION", "unknown declaration omission reason")
        _require(entry["qualified_name"] not in {o["qualified_name"] for m in manifest["modules"] for o in m["objects"]},
                 "INVALID_OMISSION", "admitted declaration cannot also be omitted")
        _unique(entry["qualified_name"], omitted_declarations)
    _ordered([entry["qualified_name"] for entry in omissions["declarations"]])
    expected_counts = {"object_count": len(result["objects"]), "relation_count": len(result["relations"]),
                       "omitted_type_references": len(omissions["type_references"]),
                       "omitted_imports": len(omissions["imports"]), "omitted_declarations": len(omissions["declarations"])}
    _require(all(metadata[field] == value for field, value in expected_counts.items()), "COUNT_MISMATCH", "shard counts disagree with manifest")
    return result


__all__ = ["SourceCatalogueError", "canonical_bytes", "module_id", "occurrence_id", "relation_id",
           "validate_manifest", "validate_shard"]
