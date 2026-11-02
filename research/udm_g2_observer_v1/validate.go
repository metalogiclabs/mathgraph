// Go-ast static admission of the bounded, untrusted test-only source.
// This is NOT a sandbox: native CI must run without model credentials, network
// credentials or privileged permission, under OS resource limits.
package main

import (
 "encoding/json"
 "fmt"
 "go/ast"
 "go/parser"
 "go/token"
 "os"
)

type Report struct {Status string `json:"status"`; Reason string `json:"reason,omitempty"`; Count int `json:"test_functions"`}
func main(){
 out:=Report{Status:"UNKNOWN_UNTRUSTED_GO_TEST"}
 defer func(){_ = json.NewEncoder(os.Stdout).Encode(out)}()
 candidate:=""
 if len(os.Args)==2 {candidate=os.Args[1]} else if len(os.Args)==3 && os.Args[1]=="--" {candidate=os.Args[2]} else {out.Reason="arguments";return}
 stat,err:=os.Stat(candidate);if err!=nil||stat.Size()>12000||stat.Size()==0{out.Reason="size";return}
 f,err:=parser.ParseFile(token.NewFileSet(),candidate,nil,parser.ParseComments|parser.AllErrors)
 if err!=nil {out.Reason="invalid_go_source";return}
 if f.Name.Name!="zerolog" {out.Reason="wrong_package";return}
 safe:=map[string]bool{"testing":true,"bytes":true,"context":true,"strings":true,"encoding/json":true,"errors":true,"fmt":true,"io":true}
 for _,imp:=range f.Imports{
  q:=imp.Path.Value
  if len(q)<2 || q[0]!='"'||q[len(q)-1]!='"'||!safe[q[1:len(q)-1]] {out.Reason="unsafe_import";return}
  if imp.Name!=nil && (imp.Name.Name=="."||imp.Name.Name=="_") {out.Reason="side_effect_import";return}
 }
 for _,decl:=range f.Decls{
  switch d:=decl.(type){
  case *ast.GenDecl:
   if d.Tok!=token.IMPORT {out.Reason="unexpected_global_declaration";return}
  case *ast.FuncDecl:
   if d.Name.Name!="TestMathGraphProposedWitness"||d.Recv!=nil {out.Reason="unexpected_function";return}
   if d.Type.Params==nil||len(d.Type.Params.List)!=1||len(d.Type.Params.List[0].Names)!=1 {out.Reason="test_signature";return}
   star,ok:=d.Type.Params.List[0].Type.(*ast.StarExpr)
   if !ok {out.Reason="test_signature";return}
   sel,ok:=star.X.(*ast.SelectorExpr)
   if !ok||sel.Sel.Name!="T" {out.Reason="test_signature";return}
   pkg,ok:=sel.X.(*ast.Ident)
   if !ok||pkg.Name!="testing" {out.Reason="test_signature";return}
   out.Count++
  default:out.Reason="unrecognized_decl";return
  }
 }
 if out.Count!=1 {out.Reason="missing_exact_test";return}
 forbidden:=false;hasAssert:=false
 ast.Inspect(f,func(n ast.Node)bool{
  if n==nil{return false}
  switch x:=n.(type){
  case *ast.GoStmt: forbidden=true
  case *ast.CallExpr:
   if sel,ok:=x.Fun.(*ast.SelectorExpr);ok {
    if id,ok:=sel.X.(*ast.Ident);ok {
     if id.Name=="t" && (sel.Sel.Name=="Skip"||sel.Sel.Name=="SkipNow"||sel.Sel.Name=="Parallel") {forbidden=true}
     if id.Name=="t" && (sel.Sel.Name=="Fatal"||sel.Sel.Name=="Fatalf"||sel.Sel.Name=="Error"||sel.Sel.Name=="Errorf") {hasAssert=true}
    }
   }
  }
  return true
 })
 if forbidden {out.Reason="forbidden_test_control";return}
 if !hasAssert {out.Reason="no_falsifiable_assertion";return}
 out.Status="ADMITTED_TEST_ONLY_CANDIDATE";out.Reason=""
 fmt.Fprintln(os.Stderr,"Go test AST admission passed")
}
