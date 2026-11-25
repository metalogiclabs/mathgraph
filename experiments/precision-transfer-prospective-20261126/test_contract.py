import unittest
from contract import *


class TestContract(unittest.TestCase):
    def test_rfc_encodings(self):
        for n, raw in [(0, "00"), (23, "17"), (24, "1818"), (255, "18ff"),
                       (256, "190100"), (500, "1901f4"), (-1, "20"),
                       (-500, "3901f3"), (MAXIMUM, "1bffffffffffffffff"),
                       (MINIMUM, "3bffffffffffffffff")]:
            with self.subTest(n=n):
                self.assertEqual(encode(n).hex(), raw)
                self.assertEqual(reference(bytes.fromhex(raw)), n)

    def test_boundaries_and_contexts(self):
        for n in boundary_values():
            for context in range(3):
                value = shaped(n, context)
                self.assertEqual(reference(encode(value)), value)

    def test_precision_loss_is_not_shape_loss(self):
        bad = lambda raw: int(float(reference(raw)))
        row = observe(bad, 2**53 + 1, 0)
        self.assertEqual(row["native_type"], "int")
        self.assertEqual(row["status"], "VALUE_DISCREPANCY")
        self.assertEqual(observe(reference, 2**53 + 1, 0)["status"], "AGREEMENT")

    def test_refusal_is_separate(self):
        def reject(raw):
            raise OverflowError("unsupported range")
        self.assertEqual(observe(reject, MAXIMUM, 0)["status"], "REJECTED_INPUT")

    def test_type_is_separate_from_numeric_value(self):
        self.assertTrue(equal(1.0, 1))
        self.assertFalse(equal(1.0, 1, strict=True))
        self.assertFalse(equal(float(2**53 + 1), 2**53 + 1))

    def test_changed_container_is_not_accepted(self):
        self.assertFalse(equal([1], [1, 1]))
        self.assertFalse(equal({0: 1}, {0: 1, 1: 42}))
        self.assertFalse(equal({False: 1}, {0: 1}, strict=True))

    def test_fixed_budget_and_reproducibility(self):
        self.assertEqual(list(corpus(9)), list(corpus(9)))
        self.assertEqual(len(list(corpus(9))), BUDGET)
        self.assertNotEqual(list(corpus(9)), list(corpus(10)))

    def test_unsupported_grammar_is_not_coerced(self):
        for value in [True, 1.0, "1", MAXIMUM + 1, MINIMUM - 1]:
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                encode(value)

    def test_registry_scope(self):
        from prepare import Registry
        p = Registry()
        p.feed('<h2>Python</h2><p>cbor2 <a href="a">one</a> Flynn <a href="b">two</a> Flunn <a href="c">three</a></p><h2>Ruby</h2><a href="d">other</a>')
        self.assertEqual(p.links, ["a", "b", "c"])
        self.assertNotIn("other", " ".join(p.parts))


if __name__ == "__main__":
    unittest.main()
