"""Synthetic parser controls. The real OASC fixture is independently fetched in Actions."""
import unittest
from dataclasses import replace
from sacm_transfer import parse_case, git_blob, bfs_consequences, independent_fixpoint

def fixture(*, cycle=False, missing=False, duplicate=False, wrong_artifact=False, dtd=False,
            changed=False):
    src = '<!DOCTYPE x [<!ENTITY hi SYSTEM "file:///etc/passwd">]>' if dtd else ''
    return (src + """<sacm:AssuranceCasePackage xmlns:sacm="http://www.omg.org/spec/SACM/2.2/Argumentation" id="root">
       <artifactPackage><artifact id="A1" name="Assessment" /></artifactPackage>
       <argumentPackage>
         <claim id="G1" content="Root"/><claim id="G2" content="Leaf"/>
         <claim id="G3" content="Separate"/>
         <artifactReference id="EV1" referencedArtifact="%s"/>
         <assertedEvidence id="e1"><source href="#EV1"/><target href="#G2"/></assertedEvidence>
         <assertedInference id="e2"><source href="#G2"/><target href="#G1"/></assertedInference>
         %s
         %s
       </argumentPackage>
     </sacm:AssuranceCasePackage>""" % (
        "BAD" if wrong_artifact else "A1",
        '<assertedInference id="e3"><source href="#G1"/><target href="#G2"/></assertedInference>' if cycle
        else '<assertedInference id="e3"><source href="#G4"/><target href="#G1"/></assertedInference>' if missing
        else '',
        '<claim id="G1" content="duplicate"/>' if duplicate
        else '<claim id="G4" content="Added"/>' if changed
        else ''
    )).encode()

class SACMTests(unittest.TestCase):
    def parsed(self, data=None):
        data=data or fixture()
        return parse_case(data,pin=git_blob(data))

    def test_good(self):
        c=self.parsed()
        self.assertEqual(bfs_consequences(c,"EV1"),["G1","G2"])
    def test_oracle_agrees(self):
        c=self.parsed()
        self.assertEqual(bfs_consequences(c,"EV1"),independent_fixpoint(c,"EV1"))
    def test_unrelated_preserved(self):
        self.assertNotIn("G3",bfs_consequences(self.parsed(),"EV1"))
    def test_text_never_warrants_evidence(self):
        c=self.parsed()
        self.assertEqual(c.artifacts["A1"],"Assessment")
        self.assertTrue(c.references["EV1"]=="A1")
        self.assertFalse(hasattr(c,"authenticated_artifact"))
    def test_nonexistent_evidence(self):
        with self.assertRaises(ValueError):
            bfs_consequences(self.parsed(),"EV_Not_A_Source")
    def test_tamper_source_pin(self):
        with self.assertRaisesRegex(ValueError,"blob"):
            parse_case(fixture(),pin="0"*40)
    def test_wrong_artifact(self):
        with self.assertRaisesRegex(ValueError,"broken artifact"):
            self.parsed(fixture(wrong_artifact=True))
    def test_cycle(self):
        with self.assertRaisesRegex(ValueError,"cyclic"):
            self.parsed(fixture(cycle=True))
    def test_dangling(self):
        with self.assertRaisesRegex(ValueError,"dangling"):
            self.parsed(fixture(missing=True))
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            self.parsed(fixture(duplicate=True))
    def test_doctype_rejected(self):
        with self.assertRaisesRegex(ValueError,"DOCTYPE"):
            self.parsed(fixture(dtd=True))
    def test_malformed_xml(self):
        with self.assertRaises(Exception):
            self.parsed(b"not XML")
    def test_wrong_root(self):
        d=b'<unknown id="u"><claim id="G1"/></unknown>'
        with self.assertRaisesRegex(ValueError,"unexpected"):
            self.parsed(d)
    def test_nonclaim_endpoint(self):
        d=fixture().replace(b'<target href="#G2"/>',b'<target href="#A1"/>')
        with self.assertRaisesRegex(ValueError,"invalid cited-evidence"):
            self.parsed(d)
    def test_independent_extra_claim_no_effect(self):
        d=fixture(changed=True)
        self.assertEqual(bfs_consequences(self.parsed(d),"EV1"),["G1","G2"])
    def test_rewritten_contents_with_old_pin_refused(self):
        d=fixture(); newer=d.replace(b'content="Root"',b'content="Changed"')
        with self.assertRaisesRegex(ValueError,"blob"):
            parse_case(newer,pin=git_blob(d))

if __name__ == "__main__":unittest.main()
