# Independent review request — frozen L4YAML parser observation

**State: CANDIDATE for external review.** This is an evidence handoff, not a signed decision, production Check Run, full YAML grammar, or fresh Lean proof replay.

## One question worth reviewing

Can the **success bit alone** from `TokenParser.parseYaml` on frozen
`metalogiclabs/L4YAML@64795a8db28ccfdae85082c93b6453001ae9d3e4`
decide the necessary YAML character-set constraint `NoRawSOH`?

- Authoritative intended obligation: [YAML 1.2.2 §5.1, c-printable](https://yaml.org/spec/1.2.2/).
  The listed printable characters exclude U+0001. Independently check that this
  exclusion covers raw control characters in source comments.
- Exact source inputs (hexadecimal UTF-8, **not** visually rendered escapes):
  `23 61` (`#a`) and `23 01` (`#` then raw U+0001).
- Historical actual observation: parser success for both; `NoRawSOH` true
  only for the first. Consequently, those two states have an identical
  success-bit observation and opposite protected truth values.
- Exact [historical theorem source](https://github.com/metalogiclabs/L4YAML/commit/b882e5b298b30b094f4154da7108a45e196cfcd3):
  `MathGraph.WholeSource.CapstoneCommentBoundary.no_normative_iff_on_frozen_runtime`.
  The proof source commit differs from the frozen production commit. This is
  intentional and must not be silently collapsed.
- Original [Lean qualification run #42420433923](https://github.com/metalogiclabs/L4YAML/actions/runs/42420433923),
  job `128547467405`, artifact ID `13593491176`, expected ZIP SHA-256
  `f60e48bc7a9df0e618c9ce6398644a9bbc5da4d4022010528f662f0566a536f3`.
  Historical bytes and CI logs were previously corroborated; **a fresh native
  Lean kernel replay is not recorded in this packet**.

## Repeat without trusting this report

1. Generate the machine-readable unsigned request:
   `node experiments/check-l4-observation-ceiling-v1/review-request.mjs`.
   Its two exact input byte strings and four open review questions are explicit.
2. Independently inspect the normative standard and frozen implementation.
   Reproduce parser outcomes with the **unchanged** frozen parser and record
   the source SHA, executable/toolchain, and exact input bytes.
3. Download the named original GitHub Actions ZIP from the cited proof run.
   Verify its SHA-256 independently; then execute:

   ```sh
   node experiments/check-l4-observation-ceiling-v1/corroborate-artifact.mjs /path/to/original-artifact.zip
   ```

   `CORROBORATED` means the historical archive and logs match their pinned
   receipt; it is **not** a new Lean check. Read the actual theorem type,
   allowed-axiom log and intentionally rejected negative control. Rerun Lean
   independently if able, and state the precise replay boundary.
4. Decide each of the four tasks in the JSON request separately, recording
   `ACCEPTED`, `REJECTED`, or `UNKNOWN` with native evidence references and
   reviewer identity. The independent reviewer must be free to reject the
   source-to-claim mapping even if the old proof builds successfully.

No private key, endorsement, policy authority or reviewer signature is included.
An eventual signed admission must use independently administered reviewer keys,
an authenticated exact source relationship and a separately trusted proof
receipt. Neither an authored JSON field nor a successful CI badge supplies these.

## Important blocked route

This L4YAML historical source witness cannot currently be attached as an
admitted claim to the *MathGraph repository* PR #273 using the existing
PR-head-only signed-projection consumer. That would require relabeling
`source_sha` from the L4YAML frozen source to the unrelated MathGraph PR head.
The consumer correctly returns `UNKNOWN / WITNESS_NOT_BOUND_TO_CURRENT_PR_HEAD`.
The new regression test proves that fail-closed behavior. Genuine
cross-repository source qualification requires a distinct design and review;
this packet does not bypass the guard.

**Unresolved:** human normative/source review, independent native Lean replay,
an authenticated cross-repository admission route, complete YAML grammar and
new production-parser correctness. The limited observation collision is not
a claim that richer observations or repaired source cannot establish the
requirement.
