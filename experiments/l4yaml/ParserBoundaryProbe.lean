import L4YAML.Scanner.Scanner
import L4YAML.Parser.TokenParser
import L4YAML.Proofs.Composition

/-!
# L4YAML parser-boundary probe

Pinned against nasa-jpl/L4YAML main at commit
16562a74421f94cc0f8216eecf21f1ff58166fa7.

Purpose: test the grammar-completeness architecture, not prove the final
capstone yet.

The current exactness proof throws away parseStream success and derives
InYamlLanguage from scan success alone. This probe verifies the decisive
separator on the real executable implementation:

* several adjacency-invalid flow inputs are accepted by the scanner;
* the parser rejects those same inputs;
* a valid comma-separated flow sequence is accepted by both; and
* every parseYaml success retains an explicit scanFiltered + parseStream
  witness through the existing parseYamlRaw_ok_decompose theorem.

If this file stays green, scanner success is strictly too weak a boundary
for exact YAML grammar membership. The exact forward theorem should consume
parser success rather than strengthen the scanner until it duplicates parser
syntax.
-/

namespace L4YAMLParserBoundaryProbe

def scanAccepts (s : String) : Bool :=
  match L4YAML.Scanner.scan s with
  | .ok _ => true
  | .error _ => false

def parseAccepts (s : String) : Bool :=
  match L4YAML.TokenParser.parseYaml s with
  | .ok _ => true
  | .error _ => false

-- Positive control: real flow syntax.
example : scanAccepts "[a,b]" = true := by native_decide
example : parseAccepts "[a,b]" = true := by native_decide

-- The exact separators already identified in the upstream completeness plan:
-- scanner accepts/tokenizes them, parser supplies the missing syntax rejection.
example : scanAccepts "[[a][b]]" = true := by native_decide
example : parseAccepts "[[a][b]]" = false := by native_decide

example : scanAccepts "[[a]b]" = true := by native_decide
example : parseAccepts "[[a]b]" = false := by native_decide

example : scanAccepts "[\"a\"\"b\"]" = true := by native_decide
example : parseAccepts "[\"a\"\"b\"]" = false := by native_decide

example : scanAccepts "{a: b: c}" = true := by native_decide
example : parseAccepts "{a: b: c}" = false := by native_decide

/--
A successful full parse already contains the stronger witness that the current
parse_strict_proof discards: the exact filtered token stream and a successful
parseStream run on it.
-/
theorem parse_success_has_parser_witness
    (input : String)
    (docs : Array L4YAML.YamlDocument)
    (h : L4YAML.TokenParser.parseYaml input = .ok docs) :
    ∃ rawDocs tokens,
      L4YAML.TokenParser.parseYamlRaw input = .ok rawDocs ∧
      L4YAML.Scanner.scanFiltered input = .ok tokens ∧
      L4YAML.TokenParser.parseStream tokens = .ok rawDocs := by
  unfold L4YAML.TokenParser.parseYaml at h
  split at h
  · rename_i rawDocs h_raw
    obtain ⟨tokens, h_scan, h_parse⟩ :=
      L4YAML.Proofs.Composition.parseYamlRaw_ok_decompose input rawDocs h_raw
    exact ⟨rawDocs, tokens, h_raw, h_scan, h_parse⟩
  · contradiction

/--
Parser success contains the exact missing adjacency distinction. Once a flow
sequence already contains at least one parsed item, a successful loop result
that grows the item array can only have crossed an explicit FLOW-ENTRY token.
This is the token-level fact that `scannerDrop` currently hides at the
character/surface layer.
-/
lemma parseFlowSequenceLoop_growth_requires_separator
    (ps ps' : L4YAML.TokenParser.ParseState)
    (fuel : Nat)
    (items result : Array L4YAML.YamlValue)
    (hitems : items.size > 0)
    (hgrowth : result.size > items.size)
    (hok : L4YAML.TokenParser.parseFlowSequenceLoop ps (fuel + 1) items = .ok (result, ps')) :
    ps.peek? = some .flowEntry := by
  unfold L4YAML.TokenParser.parseFlowSequenceLoop at hok
  simp only [bind, Except.bind, pure, Except.pure] at hok
  split at hok
  · simp only [Except.ok.injEq, Prod.mk.injEq] at hok
    obtain ⟨rfl, _⟩ := hok
    exact False.elim (Nat.lt_irrefl _ hgrowth)
  · simp [hitems] at hok
    split at hok
    · assumption
    · simp only [Except.ok.injEq, Prod.mk.injEq] at hok
      obtain ⟨rfl, _⟩ := hok
      exact False.elim (Nat.lt_irrefl _ hgrowth)

#eval scanAccepts "[[a][b]]"
#eval parseAccepts "[[a][b]]"
#eval scanAccepts "[a,b]"
#eval parseAccepts "[a,b]"

end L4YAMLParserBoundaryProbe
