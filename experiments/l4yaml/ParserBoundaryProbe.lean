import L4YAML.Scanner.Scanner
import L4YAML.Parser.TokenParser
import L4YAML.Proofs.Composition
import L4YAML.Proofs.Production.StructureProduction

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

open L4YAML.Surface
open L4YAML.Scanner
open L4YAML.Proofs.CouplingBridge
open L4YAML.Proofs.ScalarProduction

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

/--
Flow-mapping parser success carries the same separator distinction as flow
sequences: once one pair already exists, any successful loop result that grows
the pair array must have crossed an explicit FLOW-ENTRY token.
-/
lemma parseFlowMappingLoop_growth_requires_separator
    (ps ps' : L4YAML.TokenParser.ParseState)
    (fuel : Nat)
    (pairs result : Array (L4YAML.YamlValue × L4YAML.YamlValue))
    (hpairs : pairs.size > 0)
    (hgrowth : result.size > pairs.size)
    (hok : L4YAML.TokenParser.parseFlowMappingLoop ps (fuel + 1) pairs = .ok (result, ps')) :
    ps.peek? = some .flowEntry := by
  unfold L4YAML.TokenParser.parseFlowMappingLoop at hok
  simp only [bind, Except.bind, pure, Except.pure] at hok
  split at hok
  · simp only [Except.ok.injEq, Prod.mk.injEq] at hok
    obtain ⟨rfl, _⟩ := hok
    exact False.elim (Nat.lt_irrefl _ hgrowth)
  · simp [hpairs] at hok
    split at hok
    · assumption
    · simp only [Except.ok.injEq, Prod.mk.injEq] at hok
      obtain ⟨rfl, _⟩ := hok
      exact False.elim (Nat.lt_irrefl _ hgrowth)

/--
Upgrade the upstream comma coupling from mere position correspondence to the
actual YAML production witness `GLit ','`. This is one of the concrete Fix-A
items in the upstream plan, and it is independent of any scanner-tightening.
-/
lemma scanFlowEntry_full_prod
    (sc : ScannerState) (sp : SurfPos)
    (hcorr : ScannerSurfCorr sc sp)
    (hpeek : sc.peek? = some ',')
    (s' : ScannerState) (hok : scanFlowEntry sc = .ok s') :
    ∃ sp', GLit ',' sp sp' ∧ ScannerSurfCorr s' sp' := by
  obtain ⟨rest, hsp_eq⟩ := peek_some_sp hcorr hpeek
  subst hsp_eq
  refine ⟨⟨rest, sc.col + 1⟩, GLit.mk rest sc.col, ?_⟩
  have hmore := peek_some_has_more hpeek
  unfold scanFlowEntry at hok
  simp only [bind, Except.bind] at hok
  split at hok
  · split at hok
    · simp at hok
    · have h := Except.ok.inj hok
      subst h
      have hcorr_emit : ScannerSurfCorr
          (sc.emit .flowEntry) ⟨',' :: rest, sc.col⟩ :=
        ⟨hcorr.chars_from, hcorr.col_eq, hcorr.end_eq,
          hcorr.input_prefix, hcorr.indent_cols_nonneg⟩
      have hcorr_adv := advance_non_newline_corr
        (sc.emit .flowEntry) ',' rest hcorr_emit hmore (by decide) (by decide)
      exact ⟨hcorr_adv.chars_from, hcorr_adv.col_eq, hcorr_adv.end_eq,
        hcorr_adv.input_prefix, hcorr_adv.indent_cols_nonneg⟩
  · have h := Except.ok.inj hok
    subst h
    have hcorr_emit : ScannerSurfCorr
        (sc.emit .flowEntry) ⟨',' :: rest, sc.col⟩ :=
      ⟨hcorr.chars_from, hcorr.col_eq, hcorr.end_eq,
        hcorr.input_prefix, hcorr.indent_cols_nonneg⟩
    have hcorr_adv := advance_non_newline_corr
      (sc.emit .flowEntry) ',' rest hcorr_emit hmore (by decide) (by decide)
    exact ⟨hcorr_adv.chars_from, hcorr_adv.col_eq, hcorr_adv.end_eq,
      hcorr_adv.input_prefix, hcorr_adv.indent_cols_nonneg⟩



#eval scanAccepts "[[a][b]]"
#eval parseAccepts "[[a][b]]"
#eval scanAccepts "[a,b]"
#eval parseAccepts "[a,b]"

end L4YAMLParserBoundaryProbe
