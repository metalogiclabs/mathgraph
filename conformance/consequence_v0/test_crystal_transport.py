"""MGSO v1 exact-byte transport tests over existing JPL and capability artifacts.
No transport grants warrant. Unknown semantics remain UNKNOWN.
"""
import hashlib,json,struct,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
J=R/"website/public/evidence/mg-l4yaml-source-check-20261010/record.json"
C=R/"conformance/capability_v1/fixtures/capability-contract.json"
P=R/"conformance/capability_v1/trust-policy.json"
MAGIC=b"MGSO\x00\x01"
class Invalid(ValueError):pass

def encode(t,v,interfaces,payload):
    if not isinstance(t,str) or not t or type(v)!=int or not 0<=v<2**32 or type(payload)!=bytes:raise Invalid("identity")
    if type(interfaces)!=tuple or interfaces!=tuple(sorted(set(interfaces))) or any(type(i)!=str or not i for i in interfaces):raise Invalid("interfaces")
    def string(s):
        b=s.encode("utf8");return struct.pack(">I",len(b))+b
    return MAGIC+string(t)+struct.pack(">II",v,len(interfaces))+b"".join(string(i) for i in interfaces)+struct.pack(">Q",len(payload))+payload

def decode(b):
    if type(b)!=bytes or not b.startswith(MAGIC):raise Invalid("magic")
    pos=6
    def take(n):
        nonlocal pos
        if n>len(b)-pos:raise Invalid("truncated")
        a=b[pos:pos+n];pos+=n;return a
    def num():return struct.unpack(">I",take(4))[0]
    def string():
        try:return take(num()).decode("utf8")
        except UnicodeDecodeError as e:raise Invalid("utf8") from e
    t=string();v=num();n=num()
    if n>len(b)//4:raise Invalid("count")
    interfaces=tuple(string() for _ in range(n))
    payload=take(struct.unpack(">Q",take(8))[0])
    if pos!=len(b) or not t or interfaces!=tuple(sorted(set(interfaces))) or any(not x for x in interfaces):raise Invalid("canonical")
    if encode(t,v,interfaces,payload)!=b:raise Invalid("roundtrip")
    return t,v,interfaces,payload

def resolve(wire):
    t,v,interfaces,payload=decode(wire)
    if t=="mathgraph.jpl.source-check" and v==1:
        x=json.loads(payload)
        if x.get("admission",{}).get("status")=="WARRANTED_ON_PINNED_BOUNDED_CASES" and x.get("axes",{}).get("finite_executable",{}).get("matched_external_labels")==48 and x["admission"]["source_fidelity_certified"] is False:return "BOUNDED_SOURCE_OBSERVATION"
    if t=="mathgraph.capability.contract" and v==1:
        p=json.loads(P.read_bytes())["contract"];x=json.loads(payload)
        if hashlib.sha256(payload).hexdigest()==p["sha256"] and len(payload)==p["size_bytes"] and x.get("profile")=="mathgraph.finite-representation-refinement.v1":return "DESCRIPTOR_PINNED_REPLAY_REQUIRED"
    return "UNKNOWN"

def samples():
    return [("mathgraph.jpl.source-check",1,("source-bound",),J.read_bytes()),
            ("mathgraph.capability.contract",1,("finite-profile",),C.read_bytes()),
            ("mathgraph.negative.unreplayed",1,(),b'{"baseline_tie":"REPORTED","replay":"UNKNOWN"}')]

class Crystal(unittest.TestCase):
    def test_exact_bytes_and_identity(self):
        for x in samples():
            wire=encode(*x)
            self.assertEqual(decode(wire),x)
            self.assertEqual(hashlib.sha256(encode(*decode(wire))).digest(),hashlib.sha256(wire).digest())
        self.assertEqual(len({hashlib.sha256(encode(*x)).digest() for x in samples()}),3)
    def test_jpl_exact_scope(self):
        self.assertEqual(resolve(encode(*samples()[0])),"BOUNDED_SOURCE_OBSERVATION")
        x=list(samples()[0]);d=json.loads(x[3]);d["admission"]["source_fidelity_certified"]=True;x[3]=json.dumps(d).encode()
        self.assertEqual(resolve(encode(*x)),"UNKNOWN")
    def test_capability_not_self_admitted(self):
        self.assertEqual(resolve(encode(*samples()[1])),"DESCRIPTOR_PINNED_REPLAY_REQUIRED")
        x=list(samples()[1]);d=json.loads(x[3]);d["claim"]["scope"]="universal";x[3]=json.dumps(d).encode()
        self.assertEqual(resolve(encode(*x)),"UNKNOWN")
    def test_negative_remains_unknown(self):
        self.assertEqual(resolve(encode(*samples()[2])),"UNKNOWN")
    def test_unknown_type_preserves_opaque_bytes(self):
        x=("future.type",9,("future.interface",),b"\x00\xff\x80")
        self.assertEqual(decode(encode(*x)),x)
        self.assertEqual(resolve(encode(*x)),"UNKNOWN")
    def test_reject_noncanonical_and_truncation(self):
        w=encode("x",1,("a","b"),b"hello")
        for altered in (w[:-1],w+b"x",w[:5]+b"\x02"+w[6:]):
            with self.assertRaises(Invalid):decode(altered)
        with self.assertRaises(Invalid):encode("x",1,("b","a"),b"")
    def test_tamper_changes_identity(self):
        x=samples()[0]
        self.assertNotEqual(hashlib.sha256(encode(*x)).digest(),hashlib.sha256(encode(x[0],x[1],x[2],x[3]+b" ")).digest())

if __name__=="__main__":unittest.main()
