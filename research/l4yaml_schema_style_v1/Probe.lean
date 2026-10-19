-- Source-native red baseline for nasa-jpl/L4YAML issue #6.
-- Source stays unchanged. This is a legacy file to avoid the separate issue #5.
import L4YAML.Schema.Api
import L4YAML.Schema.Deriving
import L4YAML.Output.Dump
open L4YAML

structure Q where
  x : Option String
  deriving Repr, BEq, Schema.FromYaml, Schema.ToYaml

def qNone : Q := { x := none }
def qStringNull : Q := { x := some "null" }

#eval IO.println ("CHECK:quoted_42_string=" ++ toString ((parseAs String "\"42\"\n").toOption == some "42"))
#eval IO.println ("CHECK:quoted_true_string=" ++ toString ((parseAs String "\"true\"\n").toOption == some "true"))
#eval IO.println ("CHECK:quoted_true_not_bool=" ++ toString ((parseAs Bool "\"true\"\n").toOption == none))
#eval IO.println ("CHECK:quoted_null_string_option=" ++ toString ((parseAs (Option String) "\"null\"\n").toOption == some (some "null")))
#eval IO.println ("CHECK:quoted_null_struct=" ++ toString ((parseAs Q "x: \"null\"\n").toOption == some qStringNull))
#eval IO.println ("CHECK:distinct_dump_option_values=" ++ toString (Dump.dump (toYaml qNone) != Dump.dump (toYaml qStringNull)))
#eval IO.println ("CHECK:round_trip_some_null=" ++ toString ((parseAs Q (Dump.dump (toYaml qStringNull))).toOption == some qStringNull))
-- Essential existing passing controls
#eval IO.println ("CHECK:plain_null_option=" ++ toString ((parseAs (Option String) "null\n").toOption == some none))
#eval IO.println ("CHECK:plain_true_bool=" ++ toString ((parseAs Bool "true\n").toOption == some true))
#eval IO.println ("CHECK:plain_42_nat=" ++ toString ((parseAs Nat "42\n").toOption == some 42))
#eval IO.println ("CHECK:ordinary_string=" ++ toString ((parseAs String "hello\n").toOption == some "hello"))
-- Actual dumped YAML passed to independent YAML parsers.
#eval IO.println ("DUMP:true=" ++ (Dump.dump (toYaml true)).replace "\n" "\\n")
#eval IO.println ("DUMP:none=" ++ (Dump.dump (toYaml (none : Option String))).replace "\n" "\\n")
#eval IO.println ("DUMP:qNone=" ++ (Dump.dump (toYaml qNone)).replace "\n" "\\n")
#eval IO.println ("DUMP:qStringNull=" ++ (Dump.dump (toYaml qStringNull)).replace "\n" "\\n")
