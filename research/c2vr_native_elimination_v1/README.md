# Native Verus elimination probe

Source: unmodified ZoneOut12/C2VerifiableRust commit
6c8b35b5dd8e94473b713b7edcf4bf4142f214e3.

Run original GCD/Fibonacci Verus programs, append isolated proof functions
demonstrating source-introduction acceptance, and test two explicit
exclusion obligations:
- not is_gcd(2, 0, 1)
- not is_fibo(-1, 0)

The two negative verifier attempts must fail by genuine assertion
diagnostics, not by compilation or infrastructure failures. Every input,
native log, executable SHA, generated proof and output is retained.
The tests do not modify the source repository. The conventional baseline
has the same contracts. Negative solver outcomes are not a universal
proof of nonderivability; the separate finite countermodels from V2
are bounded semantic evidence. No migration runtime defect is asserted.
