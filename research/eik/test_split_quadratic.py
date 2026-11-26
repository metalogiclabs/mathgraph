"""Check the approximation identity, exact bound and rounding guard falsifiers."""
from fractions import Fraction as F
from split_quadratic import nearest, transformed_rows
import unittest


class EnvelopeTests(unittest.TestCase):
    def test_chebyshev_identity_and_extrema(self):
        for n in (2, 4):
            r = F(1, 4*n)
            for h in [F(k, 4*n) for k in range(-2*n+1, 2*n, 2)]:
                for k in range(65):
                    z = -r+2*r*k/64
                    x = h+z
                    q = 3*h*x*x+(-3*h*h+3*r*r/4)*x+h**3-3*h*r*r/4
                    assert x**3-q == z**3-3*r*r*z/4
                    assert abs(x**3-q) <= r**3/4

    def test_modular_quotient_guard(self):
        for width in (128, 256, 512):
            for E in (7, 15, 31):
                if 2*E+1 >= width:
                    continue
                mask=(width-1) & ~(2*E+1)
                for block in [0, 1, 100, (1<<32)//width-1]:
                    for low in range(width):
                        Q=(block*width+low) & 0xffffffff
                        if Q & mask:
                            for error in range(-E, E+1):
                                V=(Q-E+error) & 0xffffffff
                                self.assertEqual(Q//width, V//width)
                                self.assertNotEqual(V & (width-2), 0)

    def test_rounding_and_strict_source_pin(self):
        for k in range(-100, 101):
            for d in (2, 4, 16):
                x=F(k,d)
                self.assertLessEqual(abs(nearest(x)-x), F(1,2))
        # Removing the uncertainty margin must admit an incorrect quotient.
        self.assertNotEqual((512+1)//512, (512+1-15)//512)


if __name__ == '__main__':
    unittest.main()
