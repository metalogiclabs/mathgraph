# MathGraph refute-first demo for PKC / JPL — 60-second read

**One proposition, two claims, identical Lean kernel outcome.**

Real NASA/JPL PKC source:
[`nasa-jpl/PropertyKindCalculus@e0deb453`](https://github.com/nasa-jpl/PropertyKindCalculus/commit/e0deb453e05ffa63297d9704ceb47d0855193824)
(17 October 2026). The SysML DSL allows `@Checked` metadata to carry
both the proof declaration `decl` and an optional asserted `statement`.
The model source says the statement is checked against the environment on
import.

**Independent challenge:** write valid SysML containing:

```sysml
#kind width {
    :>> id default = "width"; :>> scale default = ScaleType::ratio;
    @Checked { decl = "PropertyKindCalculus.Iso80000.Part3.Edge.width_length";
               statement = "False"; }
}
```

The **real** Lean declaration is a constructor of the
`Edge width.kind length.kind` proposition, not `False`.

**Observed outcome:** On exact original PKC, published/checksummed
OpenSysML **v0.9.1** validates the text, converts it into real API-element
JSON *preserving* the `False` assertion, and JPL's native
`scripts/ingest-sysml.sh` admits it. The generated Lean module compiles with
`-- checked: ... — False` as a **comment**, never as a theorem.

**Controlled repair:** one fail-closed rule in
`Harvest.unverifiedCitations` rejects any unchecked optional free-text
`@Checked.statement`. The exact unchanged valid proof citation **without**
optional statement stays admitted; identical original `False` text is
rejected with the explicit unchecked-statement reason. Removing that rule
and rebuilding readmits the same `False` text. The V4 API-JSON native
test also retained three pre-existing negative controls (missing
declaration, data/function, and axiom) across the change.

**Primary independently reproducible evidence:**
[GREEN full-text end-to-end V5 Actions #39177893785](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785)
· [V5 exact frozen sources](https://github.com/metalogiclabs/mathgraph/tree/research/jpl-pkc-opensysml-e2e-v5-20261019/research/jpl_pkc_statement_v5)
· [Raw SysML, JSON, original/strict/withdraw logs and result receipt](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785/artifacts/12155725060)
(archive SHA256 `8546dfc16783f8243329883e12b7a11f49b6d0c7a3634aaa5293e6c32613cbc6`)
· [V4 13-case native negative/withdrawal controls](https://github.com/metalogiclabs/mathgraph/actions/runs/39176658515).

**Precise verdict:** `WARRANTED_BOUNDED` **claim-to-proof metadata mismatch**,
not Lean proving falsehood; not a blanket attack on PKC's other proofs.
This is a concrete case of independent, adversarial testing **above the kernel**.

**Unresolved field contract:** Should
`@Checked.statement` be (A) explicitly untrusted commentary, or
(B) an authoritative proposition whose typed semantics must be matched to
the actual checked Lean declaration? The temporary refusal rule is safe
in the tested examples but would reject legitimate optional explanations
until a typed interface exists.

No JPL source modified, no upstream PR or message sent.
