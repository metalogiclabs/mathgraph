"""An unsigned wrapper can establish exact correspondence, never authority."""

import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
NAME = "conformance/capability_v1/fixtures/capability-contract.json"
PIN = {
    "name": NAME,
    "sha256": "24e639b9181af313100504e0aa525536197d868810e6ffdb5093fd13501577a8",
    "size_bytes": 3533,
    "media_type": "application/json",
    "object_schema": "mathgraph.capability-contract.v1",
}


def api():
    assert (ROOT / "mathgraph_protocol/in_toto_v1.py").is_file(), "unsigned binding implementation missing"
    return importlib.import_module("mathgraph_protocol.in_toto_v1")


def raw():
    return (ROOT / NAME).read_bytes()


def statement():
    return json.loads(api().export_statement(raw(), name=NAME))


def encode(value):
    return json.dumps(value, sort_keys=True).encode()


def check(value, artifact=None, pin=None):
    return api().import_statement(
        encode(value) if isinstance(value, dict) else value,
        raw() if artifact is None else artifact,
        expected_artifact=PIN if pin is None else pin,
    )


def assert_no_authority(result):
    assert result["signature"] == "UNSIGNED"
    for field in ("authenticity", "signer_policy", "transparency", "freshness"):
        assert result[field] == "NOT_CHECKED"
    assert result["qualification"] == "UNKNOWN"
    assert result["current_applicability"] == "UNKNOWN"
    assert result["action_authorization"] == "NONE"
    assert "terminal_form" not in result


def test_deterministic_exact_qualified_contract_round_trip_grants_no_authority():
    exported = api().export_statement(raw(), name=NAME)
    assert type(exported) is bytes
    assert exported == api().export_statement(raw(), name=NAME)
    assert exported == (ROOT / "conformance/interoperability_v1/statement.json").read_bytes()
    value = json.loads(exported)
    assert value["_type"] == "https://in-toto.io/Statement/v1"
    assert value["predicateType"] == "https://mathgraph.org/attestation/external-binding/v1"
    assert value["subject"] == [{"name": NAME, "digest": {"sha256": PIN["sha256"]}}]
    contract = json.loads(raw())
    assert value["predicate"]["artifact"] == PIN
    assert value["predicate"]["claim"] == contract["claim"]
    assert value["predicate"]["assumptions"] == contract["assumptions"]
    assert value["predicate"]["evidence"] == contract["evidence"]
    result = check(exported)
    assert result["correspondence"] == "MATCH"
    assert result["artifact"] == PIN
    assert result["claim"] == contract["claim"]
    assert_no_authority(result)


@pytest.mark.parametrize("field,value", [
    ("name", "other.json"), ("sha256", "0" * 64), ("size_bytes", 3534),
    ("media_type", "text/plain"), ("object_schema", "mathgraph.unknown.v1"),
    ("size_bytes", True), ("size_bytes", 3533.0),
])
def test_changed_artifact_metadata_is_rejected(field, value):
    data = statement()
    data["predicate"]["artifact"][field] = value
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field", ["name", "digest"])
def test_wrong_subject_cannot_hide_behind_correct_predicate(field):
    data = statement()
    data["subject"][0][field] = "other" if field == "name" else {"sha256": "0" * 64}
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field,value", [
    ("_type", "https://in-toto.io/Statement/v0.1"),
    ("predicateType", "https://example.invalid/predicate"),
    ("subject", []), ("subject", [{"name": NAME, "digest": {"sha256": "0" * 64}}] * 2),
    ("qualification", "QUALIFIED_BOUNDED"), ("signatures", []),
])
def test_unsupported_statement_and_producer_authority_fields_fail_closed(field, value):
    data = statement()
    data[field] = value
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "mathgraph.external-binding.v2"), ("signature", "VERIFIED"),
    ("qualification", "QUALIFIED_BOUNDED"), ("terminal_form", "VERIFIED_PROOF"),
    ("assumptions", []), ("evidence", []),
])
def test_stripped_boundary_or_injected_predicate_authority_fails(field, value):
    data = statement()
    data["predicate"][field] = value
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field", ["id", "kind", "scope"])
def test_claim_correspondence_includes_identity_kind_and_scope(field):
    data = statement()
    data["predicate"]["claim"][field] += " altered"
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field", ["id", "locator", "sha256", "size_bytes", "media_type"])
def test_every_evidence_reference_field_is_bound(field):
    data = statement()
    data["predicate"]["evidence"][0][field] = 1 if field == "size_bytes" else "changed"
    with pytest.raises(api().ExternalBindingError):
        check(data)


@pytest.mark.parametrize("field", ["artifact", "claim", "assumptions", "evidence", "signature", "extensions"])
def test_missing_predicate_members_fail_closed(field):
    data = statement()
    del data["predicate"][field]
    with pytest.raises(api().ExternalBindingError):
        check(data)


def test_artifact_bytes_not_normalized_before_digest_comparison():
    with pytest.raises(api().ExternalBindingError):
        check(statement(), artifact=raw() + b"\n")


@pytest.mark.parametrize("field", ["scope", "assumptions", "evidence"])
def test_recomputed_digest_on_changed_contract_cannot_replace_consumer_pin(field):
    contract = json.loads(raw())
    if field == "scope":
        contract["claim"][field] = "All possible carriers"
    else:
        contract[field] = []
    changed = encode(contract)
    new_statement = api().export_statement(changed, name=NAME)
    assert json.loads(new_statement)["subject"][0]["digest"]["sha256"] == hashlib.sha256(changed).hexdigest()
    with pytest.raises(api().ExternalBindingError, match="ARTIFACT_PIN_MISMATCH"):
        check(new_statement, artifact=changed)


def test_changed_contract_with_recomputed_digest_but_original_projection_is_rejected():
    contract = json.loads(raw())
    contract["claim"]["scope"] = "All possible carriers"
    changed = encode(contract)
    data = statement()
    pin = dict(PIN, sha256=hashlib.sha256(changed).hexdigest(), size_bytes=len(changed))
    data["subject"][0]["digest"]["sha256"] = pin["sha256"]
    data["predicate"]["artifact"] = pin
    with pytest.raises(api().ExternalBindingError, match="CLAIM_MISMATCH"):
        check(data, artifact=changed, pin=pin)


@pytest.mark.parametrize("document", [
    b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'{', b'null', b'\xff',
])
def test_strict_json_on_both_byte_boundaries(document):
    with pytest.raises(api().ExternalBindingError):
        check(document)
    with pytest.raises(api().ExternalBindingError):
        api().export_statement(document, name=NAME)


@pytest.mark.parametrize("document", [{}, "{}", bytearray(b"{}")])
def test_boundary_requires_exact_bytes_not_reserialized_python_values(document):
    with pytest.raises(api().ExternalBindingError):
        api().export_statement(document, name=NAME)
    with pytest.raises(api().ExternalBindingError):
        api().import_statement(document, raw(), expected_artifact=PIN)


@pytest.mark.parametrize("critical", [True, "false", 0, None])
def test_unknown_or_malformed_critical_extension_fails_closed(critical):
    data = statement()
    data["predicate"]["extensions"] = [
        {"id": "urn:unknown", "version": "1", "critical": critical, "payload": {}}
    ]
    with pytest.raises(api().ExternalBindingError):
        check(data)


def test_explicitly_noncritical_data_is_opaque_and_has_no_authority():
    data = statement()
    extension = {"id": "urn:unknown", "version": "1", "critical": False,
                 "payload": {"qualification": "QUALIFIED_BOUNDED", "url": "https://example.invalid/never-fetch"}}
    data["predicate"]["extensions"] = [extension]
    before = copy.deepcopy(data)
    result = check(data)
    assert result["external_extensions"] == [extension]
    assert_no_authority(result)
    assert data == before
    data["predicate"]["extensions"].append(copy.deepcopy(extension))
    with pytest.raises(api().ExternalBindingError):
        check(data)


def test_contract_critical_extensions_and_self_qualification_are_rejected():
    contract = json.loads(raw())
    contract["extensions"] = [{"id": "urn:unknown", "version": "1", "critical": True, "payload": {}}]
    with pytest.raises(api().ExternalBindingError):
        api().export_statement(encode(contract), name=NAME)
    contract = json.loads(raw())
    contract["qualification"] = "QUALIFIED_BOUNDED"
    with pytest.raises(api().ExternalBindingError):
        api().export_statement(encode(contract), name=NAME)
    contract = json.loads(raw())
    contract["schema_version"] = "mathgraph.unknown.v1"
    with pytest.raises(api().ExternalBindingError):
        api().export_statement(encode(contract), name=NAME)


def test_schema_public_projection_and_strict_shape():
    path = ROOT / "protocol/schemas/external-binding-v1.schema.json"
    assert path.is_file(), "external binding schema missing"
    assert path.read_bytes() == (ROOT / "website/public/schemas/external-binding-v1.schema.json").read_bytes()
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(path.read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(statement(), schema)
    data = statement()
    data["predicate"]["qualification"] = "QUALIFIED_BOUNDED"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, schema)


def test_adapter_keeps_standard_library_boundary_and_never_fetches_or_executes():
    assert (ROOT / "adapters/in_toto_v1.py").is_file(), "thin adapter missing"
    script = '''
import importlib.abc, pathlib, sys
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'mathgraph', 'numpy', 'pandas', 'requests', 'jsonschema'}:
            raise AssertionError('forbidden dependency: ' + fullname)
sys.meta_path.insert(0, Block())
from adapters.in_toto_v1 import export_statement, import_statement
from mathgraph_protocol.in_toto_v1 import ExternalBindingError
raw = pathlib.Path(sys.argv[1], 'conformance/capability_v1/fixtures/capability-contract.json').read_bytes()
import json
pin = json.loads(sys.argv[2])
def audit(event, args):
    if event in {'open', 'os.system', 'subprocess.Popen', 'socket.connect', 'socket.__new__'}:
        raise AssertionError('forbidden side effect: ' + event)
sys.addaudithook(audit)
statement = export_statement(raw, name=pin['name'])
assert import_statement(statement, raw, expected_artifact=pin)['qualification'] == 'UNKNOWN'
print('stdlib-only correspondence; no runtime I/O')
'''
    result = subprocess.run([sys.executable, "-I", "-S", "-c", script, str(ROOT), json.dumps(PIN)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "no runtime I/O" in result.stdout
