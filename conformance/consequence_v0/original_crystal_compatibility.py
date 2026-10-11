"""Exact original Crystal runtime vs candidate MGSO codec, immutable pinned source.

This checks byte-level interoperability, not semantic equivalence or universal warrant.
Original source is fetched by CI from a fixed commit and hash-checked.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import unittest
from test_crystal_transport import encode,decode,samples,Invalid

EXPECTED_SOURCE_SHA256 = os.environ.get("CRYSTAL_SOURCE_SHA256","")
ORIGINAL_PATH = os.environ.get("CRYSTAL_ORIGINAL_PATH","")

class OriginalCrystalCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_PATH or not EXPECTED_SOURCE_SHA256:
            raise RuntimeError("Original pinned Crystal source required; no silent skip")
        p=Path(ORIGINAL_PATH)
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=EXPECTED_SOURCE_SHA256:
            raise AssertionError("Original Crystal source SHA-256 mismatch")
        spec=importlib.util.spec_from_file_location("pinned_original_crystal",p)
        module=importlib.util.module_from_spec(spec)
        import sys
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        cls.SemanticObject=module.SemanticObject
    def test_real_domain_vectors(self):
        for typ,version,interfaces,payload in samples():
            original=self.SemanticObject(typ,version,payload,interfaces)
            candidate=encode(typ,version,interfaces,payload)
            self.assertEqual(original.to_bytes(),candidate)
            self.assertEqual(original.id,"semantic:"+hashlib.sha256(candidate).hexdigest())
            self.assertEqual(decode(original.to_bytes()),(typ,version,interfaces,payload))
    def test_unknown_binary_and_unicode(self):
        for typ,payload in (("future.unknown",b"\x00\xff\x80"),("physics.λ",b"\x01\x00\xfe")):
            x=self.SemanticObject(typ,7,payload,("future.z","future.α"))
            candidate=encode(typ,7,("future.z","future.α"),payload)
            self.assertEqual(x.to_bytes(),candidate)
            self.assertEqual(decode(candidate)[3],payload)
    def test_original_canonicalizes_unsorted_interfaces(self):
        x=self.SemanticObject("x",1,b"raw",("b","a","b"))
        self.assertEqual(x.to_bytes(),encode("x",1,("a","b"),b"raw"))
        with self.assertRaises(Invalid):encode("x",1,("b","a"),b"raw")
    def test_tamper_identity_and_noncanonical_rejection(self):
        x=self.SemanticObject("x",1,b"raw",("a",))
        self.assertNotEqual(x.id,self.SemanticObject("x",1,b"raw2",("a",)).id)
        with self.assertRaises(Invalid):decode(x.to_bytes()+b"extra")

if __name__=="__main__":unittest.main()
