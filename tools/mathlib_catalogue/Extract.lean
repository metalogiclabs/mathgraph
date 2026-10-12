import Lean

/- Contract 1: environment-derived source occurrences only. No proof bodies,
   status claims, fetching, or directory discovery. The caller supplies an
   explicit source root, one output file, and the exact selected module list.
   UTF-16 lexical order, fully qualified escaped names, pp width 120, no
   Unicode normalization; declaration positions become UTF-8 byte coordinates.
   Generated recursors/internal auxiliaries and missing direct ranges are
   named omissions. The offline harness owns environment-byte trust. -/
open Lean

namespace MathGraphCatalogue

def utf16 (s : String) : List Nat := s.toList.flatMap fun c =>
  let n := c.toNat
  if n < 65536 then [n] else [55296 + (n - 65536) / 1024, 56320 + (n - 65536) % 1024]

def lt (a b : String) : Bool := compare (utf16 a) (utf16 b) == .lt

def sorted (xs : Array String) : Array String := xs.qsort lt

def nameText (n : Name) : String := n.toString (escape := true)

partial def constants (e : Expr) (acc : Array String := #[]) : Array String :=
  match e with
  | .const n _ => if acc.contains (nameText n) then acc else acc.push (nameText n)
  | .app f a => constants a (constants f acc)
  | .lam _ t b _ | .forallE _ t b _ => constants b (constants t acc)
  | .letE _ t v b _ => constants b (constants v (constants t acc))
  | .mdata _ b | .proj _ _ b => constants b acc
  | _ => acc

def kind (c : ConstantInfo) : String :=
  match c with
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "definition"
  | .thmInfo _ => "theorem"
  | .opaqueInfo _ => "opaque"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "constructor"
  | .recInfo _ => "recursor"
  | .quotInfo _ => "quotient"

/-- Lean's module system may independently realize the same on-demand theorem
in sibling modules. `finalizeImport` admits only compatible theorem
types/levels/mutual blocks and assigns one canonical origin. Mirror that narrow
boundary for omission accounting; no user declaration or other generated kind
is transportable across an origin mismatch. -/
def sameGeneratedTheorem (observed canonical : ConstantInfo) : Bool :=
  match observed, canonical with
  | .thmInfo a, .thmInfo b =>
    a.name == b.name && a.type == b.type && a.levelParams == b.levelParams && a.all == b.all
  | _, _ => false

/-- `mkHCongrWithArityForConst?` and `mkCongrSimpForConst?` realize Lean's two
reserved congruence-theorem forms, `hcongr_<Nat>` and exact `congr_simp`, and
record their argument kinds in the congruence declaration extension. Sibling
modules may realize the same theorem before import finalization chooses one
canonical origin. Require the official suffix grammar (including hcongr
arity), the registered reserved-name predicate, no direct source range, an
exact entry in the selected module's private serialized extension state, and
agreement with canonical extension metadata. Looking up only the canonical
extension entry is insufficient: a low-level declaration in a sibling module
could otherwise borrow the canonical module's generated status. User theorems
with exact or near-match suffixes are therefore not classified as generated. -/
def isGeneratedCongruence (env : Environment) (idx : ModuleIdx) (name : Name) : Bool :=
  match name with
  | .str _ suffix =>
    let hcongr := Meta.isHCongrReservedNameSuffix suffix
    let congrSimp := suffix == Meta.congrSimpSuffix
    if !(hcongr || congrSimp) || !isReservedName env name then
      false
    else
      let localKindsEntries := Meta.congrKindsExt.getModuleEntries env idx (level := .private)
        |>.filter (fun entry => entry.1 == name)
      let localRangeEntries := declRangeExt.getModuleEntries env idx (level := .private)
        |>.filter (fun entry => entry.1 == name)
      if localKindsEntries.size != 1 || !localRangeEntries.isEmpty then
        false
      else
        match Meta.congrKindsExt.find? env name (level := .private) with
        | some canonicalKinds =>
          let localKinds := localKindsEntries[0]!.2
          localKinds == canonicalKinds
            && (!hcongr || localKinds.size == (suffix.drop 7).toNat!)
        | none => false
  | _ => false

def position (map : FileMap) (p : Position) : Except String Json := do
  let offset := map.ofPosition p
  unless map.toPosition offset == p do throw "invalid declaration coordinate"
  let lineStart := map.ofPosition { line := p.line, column := 0 }
  return Json.mkObj [("line", toJson p.line), ("column", toJson (offset.byteIdx - lineStart.byteIdx)),
                     ("byte", toJson offset.byteIdx)]

def extract (root : System.FilePath) (names : Array String) : MetaM Json := do
  let env ← getEnv
  let mut modules := #[]
  let mut seen : Array String := #[]
  for moduleName in names do
    let mod := moduleName.toName
    let some idx := env.getModuleIdx? mod | throwError "unknown selected module {moduleName}"
    let source ← IO.FS.readFile (root / (moduleName.replace "." "/" ++ ".lean"))
    let map := FileMap.ofString source
    let mut declarations := #[]
    let mut omissions := #[]
    let cs := (env.header.moduleData[idx]!).constants.qsort fun a b => lt (nameText a.name) (nameText b.name)
    for info in cs do
      let name := info.name
      let some origin := env.getModuleIdxFor? name | throwError "unknown origin for {name}"
      let qualified := nameText name
      let k := kind info
      -- Core lookup deliberately does not inherit an inductive's range for a recursor.
      let range? ← findDeclarationRangesCore? name
      -- The imported equation-extension state may name only one canonical
      -- realization. `declFromEqLikeName` independently validates the reserved
      -- suffix against the underlying safe definition, including exposure and
      -- private-name rules, so a sibling realization is still recognized.
      let equation := (Meta.declFromEqLikeName env name).isSome || (← Meta.isEqnThm name)
      let congruence := isGeneratedCongruence env idx name
      -- A private or underscore-prefixed *user* name with its own direct range
      -- remains a source occurrence. Names alone cannot make it generated.
      let generated := k == "recursor" || isAuxRecursor env name || isNoConfusion env name
        || Meta.isMatcherCore env name || equation || congruence
        || (range?.isNone && name.isInternalDetail)
      if origin != idx then
        let some canonical := env.find? name | throwError "missing canonical declaration for {name}"
        unless (equation || congruence) && sameGeneratedTheorem info canonical do
          let canonicalModule := nameText env.header.moduleNames[origin]!
          throwError "inconsistent non-generated origin name={qualified} selected={moduleName} canonical={canonicalModule}"
      let reason := if generated then
          some "GENERATED"
        else if k == "quotient" then some "UNSUPPORTED_KIND"
        else if range?.isNone then some "MISSING_RANGE"
        else none
      if let some reason := reason then
        omissions := omissions.push (Json.mkObj [("qualified_name", toJson qualified),
          ("kind", toJson k), ("reason", toJson reason)])
      else
        if seen.contains qualified then throwError "duplicate admitted name {qualified}"
        seen := seen.push qualified
        let some ranges := range? | throwError "inconsistent omission accounting"
        let start ← ofExcept (position map ranges.range.pos)
        let finish ← ofExcept (position map ranges.range.endPos)
        let statement := (← Meta.ppExpr info.type).pretty 120
        declarations := declarations.push (Json.mkObj [
          ("qualified_name", toJson qualified), ("kind", toJson k), ("statement", toJson statement),
          ("range", Json.mkObj [("start", start), ("end", finish)]),
          ("type_references", toJson (sorted (constants info.type)))])
    let imports := sorted (((env.header.moduleData[idx]!).imports.map fun i => nameText i.module).toList.eraseDups.toArray)
    modules := modules.push (Json.mkObj [("module", toJson moduleName), ("imports", toJson imports),
      ("declarations", Json.arr declarations), ("omissions", Json.arr omissions)])
  return Json.mkObj [("contract_version", toJson (1 : Nat)), ("modules", Json.arr modules)]

end MathGraphCatalogue

unsafe def main (args : List String) : IO Unit := do
  let root :: output :: modules := args | throw <| IO.userError "expected SOURCE_ROOT OUTPUT MODULE..."
  unless !modules.isEmpty && modules.toArray == MathGraphCatalogue.sorted modules.toArray && modules.eraseDups == modules do
    throw <| IO.userError "module list must be nonempty, unique, and UTF-16 sorted"
  for m in modules do
    unless m.splitOn "." |>.all (fun p => !p.isEmpty && p.toList.all (fun c => c.isAlphanum || c == '_')) do
      throw <| IO.userError "invalid module name"
  -- Running with `lean --run` makes appDir the pinned Lean binary directory.
  -- Do not shell out to `lean`: an elan shim could otherwise acquire a toolchain.
  initSearchPath (← getBuildDir)
  enableInitializersExecution
  let options := ({} : Options).setBool `pp.fullNames true |>.setBool `pp.universes true
    |>.setBool `pp.explicit true |>.setBool `pp.proofs false |>.set `pp.width (120 : Nat)
  let env ← importModules (modules.toArray.map fun m => { module := m.toName }) options
    (loadExts := true) (level := .private)
  let (json, _, _) ← (MathGraphCatalogue.extract root modules.toArray).toIO
    { fileName := "<source-catalogue>", fileMap := default, options := options } { env := env }
  IO.FS.writeFile output json.compress
