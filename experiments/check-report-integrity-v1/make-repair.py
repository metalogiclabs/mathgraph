from pathlib import Path
import json,hashlib
p=Path(__file__).parent
source=(p/'original.lean').read_text()
anchor='/-- A start tag\'s attributes:'
validator='''partial def validXmlEntities : List Char → Bool
  | [] => true
  | '&' :: t =>
    let ent := t.takeWhile (· != ';')
    let e := String.ofList ent
    let num : Option Nat :=
      if e.startsWith "#x" then
        let hs := ent.drop 2
        if hs.isEmpty || !hs.all (fun c => c.isDigit || "abcdefABCDEF".toList.contains c) then none
        else some (hs.foldl (fun n c => n * 16 + (if c.isDigit then c.toNat - '0'.toNat else c.toLower.toNat - 'a'.toNat + 10)) 0)
      else if e.startsWith "#" then (String.ofList (ent.drop 1)).toNat? else none
    let scalar := match num with
      | some n => n == 9 || n == 10 || n == 13 || (n ≥ 32 && n ≤ 0xD7FF) || (n ≥ 0xE000 && n ≤ 0xFFFD) || (n ≥ 0x10000 && n ≤ 0x10FFFF)
      | none => false
    t.length > ent.length && (["amp", "lt", "gt", "quot", "apos"].contains e || scalar) && validXmlEntities (t.drop (ent.length + 1))
  | _ :: t => validXmlEntities t

'''
start=source.index('partial def attrsOf')
end=source.index('\n#guard attrsOf',start)
old_attrs=source[start:end]
new_attrs=old_attrs.replace("    | '=' :: t =>\n", "    | '=' :: t =>\n      if acc.any (fun kv => kv.1 == String.ofList name) then .error s!\"duplicate attribute {String.ofList name}\" else\n")
new_attrs=new_attrs.replace('          else go (v.drop', '          else if !validXmlEntities val || val.contains \'<\' then .error s!"invalid value of attribute {String.ofList name}"\n          else go (v.drop')
start=source.index('partial def tokens')
end=source.index('\n/-- `generate_python_ffi_html`',start)
old_tokens=source[start:end]
new_tokens=old_tokens.replace('  go s.toList []','  go s.toList [] 0').replace('Bool × Bool)) :\n      Except','Bool × Bool)) (depth : Nat) :\n      Except')
new_tokens=new_tokens.replace('"comment") acc','"comment") acc depth').replace('"CDATA section") acc','"CDATA section") acc depth').replace('"declaration") acc','"declaration") acc depth')
new_tokens=new_tokens.replace('      go (← skipTo t [\'>\'] s!"end tag </{String.ofList name}>") ((String.ofList name, [], false, true) :: acc)', '''      let afterName := (t.drop name.length).dropWhile Char.isWhitespace
      match afterName with
      | '>' :: rest => go rest ((String.ofList name, [], false, true) :: acc) (depth - 1)
      | _ => throw s!"invalid end tag </{String.ofList name}>"''')
new_tokens=new_tokens.replace('      go rest ((String.ofList name, attrs, true, selfClose) :: acc)','      go rest ((String.ofList name, attrs, true, selfClose) :: acc) (depth + if selfClose then 0 else 1)')
new_tokens=new_tokens.replace('    | _ :: t => go t acc', '''    | '&' :: t => do
      if depth == 0 then throw "text outside root element"
      let ent := t.takeWhile (· != ';')
      if t.length == ent.length || !validXmlEntities ('&' :: ent ++ [';']) then throw "invalid entity in content"
      go (t.drop (ent.length + 1)) acc depth
    | c :: t => do
      if depth == 0 && !c.isWhitespace then throw "text outside root element"
      go t acc depth''',1)
edits=[{'old':anchor,'new':validator+anchor},{'old':old_attrs,'new':new_attrs},{'old':old_tokens,'new':new_tokens}]
candidate=source
for e in edits:
 assert candidate.count(e['old'])==1
 candidate=candidate.replace(e['old'],e['new'])
(p/'candidate.lean').write_text(candidate)
recipe={'summary':'Reject malformed report envelopes, duplicate attributes and undefined entities while preserving existing guards and report API','edits':edits}
(p/'repair.json').write_text(json.dumps(recipe,indent=2))
print(json.dumps({'original_sha256':hashlib.sha256(source.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest()}))
