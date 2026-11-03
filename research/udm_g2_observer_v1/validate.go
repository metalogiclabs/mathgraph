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
 expectedPkg:="zerolog"
 if len(os.Args)==2 {candidate=os.Args[1]} else if len(os.Args)==3 && os.Args[1]=="--" {candidate=os.Args[2]} else if len(os.Args)==5 && os.Args[1]=="--" && os.Args[2]=="--package" {expectedPkg=os.Args[3];candidate=os.Args[4]} else {out.Reason="arguments";return}
 if expectedPkg!="backoff" && expectedPkg!="zerolog" {out.Reason="unsupported_package";return}
 stat,err:=os.Stat(candidate);if err!=nil||stat.Size()>12000||stat.Size()==0{out.Reason="size";return}
 f,err:=parser.ParseFile(token.NewFileSet(),candidate,nil,parser.ParseComments|parser.AllErrors)
 if err!=nil {out.Reason="invalid_go_source";return}
 if f.Name.Name!=expectedPkg {out.Reason="wrong_package";return}
 safe:=map[string]bool{"testing":true,"bytes":true,"context":true,"strings":true,"encoding/json":true,"errors":true,"fmt":true,"io":true,"time":true,"sync":true}
 for _,imp:=range f.Imports{
  q:=imp.Path.Value
  if len(q)<2 || q[0]!='"'||q[len(q)-1]!='"'||!safe[q[1:len(q)-1]] {out.Reason="unsafe_import";return}
  if imp.Name!=nil && (imp.Name.Name=="."||imp.Name.Name=="_") {out.Reason="side_effect_import";return}
 }
 helperName:=""
 for _,decl:=range f.Decls{
  d,ok:=decl.(*ast.GenDecl)
  if !ok || d.Tok!=token.TYPE {continue}
  if helperName!="" || len(d.Specs)!=1 {out.Reason="extra_helper_type";return}
  spec,ok:=d.Specs[0].(*ast.TypeSpec)
  if !ok || spec.Assign.IsValid() {out.Reason="helper_type_alias";return}
  st,ok:=spec.Type.(*ast.StructType)
  if !ok || st.Fields==nil || len(st.Fields.List)>3 {out.Reason="helper_not_small_struct";return}
  for _,field:=range st.Fields.List {
   if len(field.Names)==0 {out.Reason="helper_embedded_field";return}
   switch field.Type.(type){
   case *ast.ArrayType,*ast.Ident,*ast.SelectorExpr:
   default:out.Reason="helper_field_type";return
   }
  }
  helperName=spec.Name.Name
 }
 methodCount:=0
 for _,decl:=range f.Decls{
  switch d:=decl.(type){
  case *ast.GenDecl:
   if d.Tok!=token.IMPORT && d.Tok!=token.TYPE {out.Reason="unexpected_global_declaration";return}
  case *ast.FuncDecl:
   if d.Recv!=nil {
    if helperName==""||len(d.Recv.List)!=1 {out.Reason="unexpected_receiver";return}
    recv:=d.Recv.List[0].Type
    star,ok:=recv.(*ast.StarExpr)
    if !ok {out.Reason="unexpected_receiver_type";return}
    ident,ok:=star.X.(*ast.Ident)
    if !ok || ident.Name!=helperName {out.Reason="unexpected_receiver_type";return}
    if d.Name.Name=="init"||d.Name.Name=="TestMathGraphProposedWitness" {out.Reason="unexpected_method";return}
    methodCount++
    if methodCount>2 {out.Reason="too_many_helper_methods";return}
    continue
   }
   if d.Name.Name!="TestMathGraphProposedWitness" {out.Reason="unexpected_function";return}
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
