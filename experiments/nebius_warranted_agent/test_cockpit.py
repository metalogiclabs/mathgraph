import unittest
from cockpit import render

class CockpitTests(unittest.TestCase):
    def test_visible_provenance(self):
        html = render({"provider":"ScriptedProvider","source_sha256":"abc","events":[]})
        self.assertIn("SCRIPTED OFFLINE FIXTURE", html)
        self.assertIn("not a formal theorem", html)

    def test_no_script_element_injection(self):
        html = render({"provider":"ScriptedProvider", "source_sha256":"</script><script>alert(1)</script>",
                       "events":[{"state":"UNKNOWN","step":"test","reason":"</script><script>alert(1)</script>"}]})
        self.assertNotIn("</script><script>alert(1)</script>",html)
        self.assertIn("\\u003c/script",html)

if __name__=="__main__":
    unittest.main()
