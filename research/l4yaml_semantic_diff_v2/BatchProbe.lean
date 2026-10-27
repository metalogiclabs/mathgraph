module

public import L4YAML.Output.Json
public import L4YAML.Output.JsonIx
public import Lean.Data.Json
public meta import L4YAML.Output.Json
public meta import L4YAML.Output.JsonIx

@[expose] public section

open L4YAML

def stringResult (result : Except ScanError String) : Lean.Json :=
  match result with
  | .ok value => Lean.Json.mkObj [("status", .str "ok"), ("value", .str value)]
  | .error e => Lean.Json.mkObj [("status", .str "error"), ("error", .str (toString e))]

def main (args : List String) : IO Unit := do
  let some path := args.head?
    | throw (IO.userError "pass a JSONL file of input strings")
  let data ← IO.FS.readFile path
  for line in data.splitOn "\n" do
    if line != "" then
      match Lean.Json.parse line with
      | .ok (.str input) =>
        let row := Lean.Json.mkObj [
          ("input", .str input),
          ("legacy", stringResult (L4YAML.Json.streamToJson input)),
          ("indexed", stringResult (L4YAML.Json.streamToJsonIx input))]
        IO.println row.compress
      | _ => throw (IO.userError "non-string JSONL input")

end
