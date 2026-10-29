// GOETH V28 test-only owner process. Standard library only.
// A protected owner UID holds its JWT and Ed25519 key; an unprivileged
// gateway must use this source-bound monitor. NOT a production authority.
package main

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/hmac"
 "crypto/rand"
 "crypto/sha256"
 "encoding/base64"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net"
 "net/http"
 "os"
 "path/filepath"
 "strconv"
 "strings"
 "sync"
 "time"
)

const version="MG_V28_OWNER_V1"
const observed="OBSERVED"
const prepared="PREPARED"

type Grant struct {
 Epoch uint64
 Scope string
 Genesis string
 Head string
 Final string
 Signature []byte
}
type Record struct {
 Version string
 Phase string
 Grant Grant
}
type Receipt struct {
 Version string
 Nonce string
 Phase string
 Grant Grant
 Signature []byte
}
type Request struct {
 Nonce string
 Grant Grant
}

func hash32(s string) ([]byte,error) {
 if !strings.HasPrefix(s,"0x") || len(s)!=66 {return nil,errors.New("invalid hash length/prefix")}
 b,e:=hex.DecodeString(s[2:]);if e!=nil||len(b)!=32{return nil,errors.New("invalid hash hex")};return b,nil
}
func grantDigest(g Grant) ([]byte,error) {
 genesis,e:=hash32(g.Genesis);if e!=nil{return nil,e}
 head,e:=hash32(g.Head);if e!=nil{return nil,e}
 final,e:=hash32(g.Final);if e!=nil{return nil,e}
 h:=sha256.New()
 h.Write([]byte("MG-V24-FROZEN-GRANT-V1\x00"))
 h.Write([]byte(g.Scope));h.Write([]byte{0});h.Write(genesis)
 var ep [8]byte;binary.BigEndian.PutUint64(ep[:],g.Epoch);h.Write(ep[:])
 h.Write(head);h.Write(final)
 return h.Sum(nil),nil
}
func validGrant(g Grant,pub ed25519.PublicKey) bool {
 if g.Epoch==0||g.Scope!="research:owner-fcu-epoch:v24:NOT-PRODUCTION"||len(pub)!=ed25519.PublicKeySize{return false}
 digest,e:=grantDigest(g);return e==nil&&ed25519.Verify(pub,digest,g.Signature)
}
func receiptDigest(r Receipt) []byte {
 r.Signature=nil
 b,_:=json.Marshal(r)
 h:=sha256.Sum256(append([]byte("MG-V28-OWNER-RECEIPT\x00"),b...))
 return h[:]
}
func nonceOK(s string)bool {
 if len(s)!=40{return false};_,e:=hex.DecodeString(s);return e==nil
}
func readFile(path string)([]byte,error){return os.ReadFile(path)}
func writeState(path string,r Record)error {
 b,e:=json.Marshal(r);if e!=nil{return e}
 dir:=filepath.Dir(path)
 tmp,e:=os.CreateTemp(dir,".mg-v28-*.tmp");if e!=nil{return e}
 defer os.Remove(tmp.Name())
 if e=tmp.Chmod(0600);e!=nil{tmp.Close();return e}
 if _,e=tmp.Write(append(b,byte(10)));e!=nil{tmp.Close();return e}
 if e=tmp.Sync();e!=nil{tmp.Close();return e}
 if e=tmp.Close();e!=nil{return e}
 if e=os.Rename(tmp.Name(),path);e!=nil{return e}
 d,e:=os.Open(dir);if e!=nil{return e};defer d.Close();return d.Sync()
}
func readState(path string,pub ed25519.PublicKey)(Record,error){
 b,e:=readFile(path);if e!=nil{return Record{},e}
 var r Record
 if e=json.Unmarshal(b,&r);e!=nil{return Record{},fmt.Errorf("MG_V28_INVALID_OWNER_STATE: %w",e)}
 if r.Version!=version||(r.Phase!=observed&&r.Phase!=prepared)||!validGrant(r.Grant,pub) {
  return Record{},errors.New("MG_V28_INVALID_OWNER_STATE")
 }
 return r,nil
}
func readKey(path string)(ed25519.PrivateKey,error) {
 b,e:=os.ReadFile(path);if e!=nil{return nil,e}
 raw,e:=hex.DecodeString(strings.TrimSpace(string(b)));if e!=nil||len(raw)!=ed25519.PrivateKeySize {
  return nil,errors.New("MG_V28_INVALID_OWNER_PRIVATE_KEY")
 }
 return ed25519.PrivateKey(raw),nil
}
func readJWT(path string)([]byte,error) {
 b,e:=os.ReadFile(path);if e!=nil{return nil,e}
 raw,e:=hex.DecodeString(strings.TrimPrefix(strings.TrimSpace(string(b)),"0x"))
 if e!=nil||len(raw)!=32{return nil,errors.New("MG_V28_JWT_INVALID")}
 return raw,nil
}
func token(secret []byte)string {
 h:=base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"HS256","typ":"JWT"}`))
 p:=base64.RawURLEncoding.EncodeToString([]byte(fmt.Sprintf(`{"iat":%d}`,time.Now().Unix())))
 s:=h+"."+p
 mac:=hmac.New(sha256.New,secret);mac.Write([]byte(s))
 return s+"."+base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
}
type Native struct {URL string;JWT []byte}
func (n Native) rpc(method string,params []any)(json.RawMessage,int,error) {
 ctx,cancel:=context.WithTimeout(context.Background(),15*time.Second);defer cancel()
 body,_:=json.Marshal(map[string]any{"jsonrpc":"2.0","id":7,"method":method,"params":params})
 req,e:=http.NewRequestWithContext(ctx,"POST",n.URL,bytes.NewReader(body));if e!=nil{return nil,0,e}
 req.Header.Set("Content-Type","application/json")
 if len(n.JWT)>0{req.Header.Set("Authorization","Bearer "+token(n.JWT))}
 res,e:=http.DefaultClient.Do(req);if e!=nil{return nil,0,e};defer res.Body.Close()
 data,e:=io.ReadAll(io.LimitReader(res.Body,1<<20));if e!=nil{return nil,res.StatusCode,e}
 if res.StatusCode!=200 {return nil,res.StatusCode,fmt.Errorf("MG_V28_ENGINE_HTTP_%d",res.StatusCode)}
 var envelope struct{ Result json.RawMessage;Error *struct{Message string} }
 if e=json.Unmarshal(data,&envelope);e!=nil{return nil,res.StatusCode,e}
 if envelope.Error!=nil{return nil,res.StatusCode,errors.New(envelope.Error.Message)}
 return envelope.Result,res.StatusCode,nil
}
func (n Native) exact(g Grant)error{
 for _,x:=range []struct{tag,want string}{{"latest",g.Head},{"finalized",g.Final}}{
  r,_,e:=n.rpc("eth_getBlockByNumber",[]any{x.tag,false});if e!=nil{return e}
  var o struct{Hash string}
  if e=json.Unmarshal(r,&o);e!=nil{return fmt.Errorf("MG_V28_NATIVE_HASH_DECODE: %w",e)}
  if !strings.EqualFold(o.Hash,x.want){return fmt.Errorf("MG_V28_NATIVE_STATE_MISMATCH tag=%s got=%s want=%s",x.tag,o.Hash,x.want)}
 }
 return nil
}
func (n Native) apply(g Grant)error{
 r,_,e:=n.rpc("engine_forkchoiceUpdatedV4",[]any{map[string]string{"headBlockHash":g.Head,"safeBlockHash":"0x"+strings.Repeat("0",64),"finalizedBlockHash":g.Final},nil,nil})
 if e!=nil{return e}
 var result struct{PayloadStatus struct{Status string}}
 if e=json.Unmarshal(r,&result);e!=nil{return e}
 if result.PayloadStatus.Status!="VALID"{return fmt.Errorf("MG_V28_NATIVE_NOT_VALID_%s",result.PayloadStatus.Status)}
 return n.exact(g)
}
type Owner struct {
 mu sync.Mutex
 state Record
 path string
 key ed25519.PrivateKey
 grantPub ed25519.PublicKey
 native Native
 faultEpoch uint64
}
func (o *Owner) receipt(nonce string)Receipt {
 r:=Receipt{Version:version,Nonce:nonce,Phase:o.state.Phase,Grant:o.state.Grant}
 r.Signature=ed25519.Sign(o.key,receiptDigest(r))
 return r
}
func writeJSON(w http.ResponseWriter,status int,x any){w.Header().Set("Content-Type","application/json");w.WriteHeader(status);_ =json.NewEncoder(w).Encode(x)}
func errJSON(w http.ResponseWriter,status int,s string){writeJSON(w,status,map[string]string{"error":s})}
func parseRequest(r *http.Request)(Request,error) {
 var q Request
 if e:=json.NewDecoder(io.LimitReader(r.Body,32<<10)).Decode(&q);e!=nil{return q,e}
 if !nonceOK(q.Nonce){return q,errors.New("bad nonce")}
 return q,nil
}
func (o *Owner) handler(w http.ResponseWriter,r *http.Request){
 switch {
 case r.Method=="GET"&&r.URL.Path=="/v1/current":
  nonce:=r.URL.Query().Get("nonce")
  if !nonceOK(nonce){errJSON(w,400,"MG_V28_INVALID_NONCE");return}
  o.mu.Lock();receipt:=o.receipt(nonce);o.mu.Unlock()
  writeJSON(w,200,receipt)
 case r.Method=="POST"&&r.URL.Path=="/v1/reconcile":
  q,e:=parseRequest(r);if e!=nil{errJSON(w,400,"MG_V28_INVALID_REQUEST");return}
  o.mu.Lock();defer o.mu.Unlock()
  if o.state.Phase!=prepared {errJSON(w,409,"MG_V28_RECONCILE_NOT_PREPARED");return}
  if e=o.native.exact(o.state.Grant);e!=nil{errJSON(w,409,"MG_V28_RECONCILE_NATIVE_MISMATCH");return}
  next:=o.state;next.Phase=observed
  if e=writeState(o.path,next);e!=nil{errJSON(w,500,"MG_V28_OWNER_PERSIST_FAILED");return}
  o.state=next
  writeJSON(w,200,o.receipt(q.Nonce))
 case r.Method=="POST"&&r.URL.Path=="/v1/apply":
  q,e:=parseRequest(r);if e!=nil{errJSON(w,400,"MG_V28_INVALID_REQUEST");return}
  o.mu.Lock();defer o.mu.Unlock()
  if !validGrant(q.Grant,o.grantPub)||q.Grant.Genesis!=o.state.Grant.Genesis {
   errJSON(w,403,"MG_V28_UNSIGNED_OR_WRONG_SCOPE");return
  }
  if o.state.Phase!=observed{errJSON(w,409,"MG_V28_IN_DOUBT");return}
  if q.Grant.Epoch<=o.state.Grant.Epoch{errJSON(w,409,"MG_V28_STALE_SIGNED_GRANT");return}
  intent:=Record{Version:version,Phase:prepared,Grant:q.Grant}
  if e=writeState(o.path,intent);e!=nil{errJSON(w,500,"MG_V28_PREPARE_PERSIST_FAILED");return}
  o.state=intent
  if e=o.native.apply(q.Grant);e!=nil{errJSON(w,503,"MG_V28_NATIVE_AMBIGUOUS:"+e.Error());return}
  if o.faultEpoch!=0&&q.Grant.Epoch==o.faultEpoch {
   fmt.Fprintln(os.Stdout,"MG_V28_OWNER_NATIVE_VALID_POST_EFFECT_PRE_COMMIT")
   for{time.Sleep(time.Hour)}
  }
  next:=intent;next.Phase=observed
  if e=writeState(o.path,next);e!=nil{errJSON(w,500,"MG_V28_OBSERVED_PERSIST_FAILED");return}
  o.state=next
  writeJSON(w,200,o.receipt(q.Nonce))
 default:
  http.NotFound(w,r)
 }
}
func serve(args []string)error{
 f:=flag.NewFlagSet("serve",flag.ContinueOnError)
 root:=f.String("root","","owner store directory")
 nativeURL:=f.String("engine","","Geth authenticated endpoint")
 jwtPath:=f.String("jwt","","Geth JWT secret file")
 grantPubHex:=f.String("grant-pub","","synthetic grant public key")
 fault:=f.Uint64("fault-epoch",0,"test-only injected post-native crash epoch")
 if e:=f.Parse(args);e!=nil{return e}
 if *root==""||*nativeURL==""||*jwtPath==""{return errors.New("missing source options")}
 pub,e:=hex.DecodeString(*grantPubHex);if e!=nil||len(pub)!=32{return errors.New("bad grant pub")}
 key,e:=readKey(filepath.Join(*root,"owner.key"));if e!=nil{return e}
 st,e:=readState(filepath.Join(*root,"owner.state"),ed25519.PublicKey(pub));if e!=nil{return e}
 secret,e:=readJWT(*jwtPath);if e!=nil{return e}
 o:=&Owner{state:st,path:filepath.Join(*root,"owner.state"),key:key,grantPub:pub,native:Native{URL:*nativeURL,JWT:secret},faultEpoch:*fault}
 listener,e:=net.Listen("tcp","127.0.0.1:0");if e!=nil{return e}
 fmt.Fprintln(os.Stdout,"MG_V28_OWNER_LISTEN=http://"+listener.Addr().String())
 return http.Serve(listener,http.HandlerFunc(o.handler))
}
func getReceipt(owner string,pub ed25519.PublicKey)(Receipt,error){
 nonceBytes:=make([]byte,20);if _,e:=rand.Read(nonceBytes);e!=nil{return Receipt{},e}
 nonce:=hex.EncodeToString(nonceBytes)
 client:=http.Client{Timeout:10*time.Second}
 r,e:=client.Get(owner+"/v1/current?nonce="+nonce);if e!=nil{return Receipt{},e}
 defer r.Body.Close()
 if r.StatusCode!=200{return Receipt{},fmt.Errorf("MG_V28_OWNER_HTTP_%d",r.StatusCode)}
 var receipt Receipt
 if e=json.NewDecoder(io.LimitReader(r.Body,32<<10)).Decode(&receipt);e!=nil{return Receipt{},e}
 if receipt.Nonce!=nonce||receipt.Version!=version||!ed25519.Verify(pub,receiptDigest(receipt),receipt.Signature) {
  return Receipt{},errors.New("MG_V28_OWNER_RECEIPT_INVALID_SIGNATURE_OR_NONCE")
 }
 return receipt,nil
}
func postOwner(owner,method string,pub ed25519.PublicKey,g Grant)(Receipt,int,error){
 n:=make([]byte,20);if _,e:=rand.Read(n);e!=nil{return Receipt{},0,e}
 nonce:=hex.EncodeToString(n)
 b,_:=json.Marshal(Request{Nonce:nonce,Grant:g})
 ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
 req,e:=http.NewRequestWithContext(ctx,"POST",owner+"/v1/"+method,bytes.NewReader(b));if e!=nil{return Receipt{},0,e}
 req.Header.Set("Content-Type","application/json")
 r,e:=http.DefaultClient.Do(req);if e!=nil{return Receipt{},0,e}
 defer r.Body.Close()
 data,e:=io.ReadAll(io.LimitReader(r.Body,32<<10));if e!=nil{return Receipt{},r.StatusCode,e}
 if r.StatusCode!=200{
  var m struct{Error string};_ =json.Unmarshal(data,&m)
  return Receipt{},r.StatusCode,errors.New(m.Error)
 }
 var receipt Receipt
 if e=json.Unmarshal(data,&receipt);e!=nil{return Receipt{},200,e}
 if receipt.Nonce!=nonce||receipt.Version!=version||!ed25519.Verify(pub,receiptDigest(receipt),receipt.Signature) {
  return Receipt{},200,errors.New("MG_V28_OWNER_APPLY_RECEIPT_INVALID")
 }
 return receipt,200,nil
}
func gateway(args []string)error{
 f:=flag.NewFlagSet("gateway",flag.ContinueOnError)
 owner:=f.String("owner","","owner read-only URL")
 pubHex:=f.String("owner-pub","","pinned owner signing public key")
 grantB64:=f.String("grant","","base64 JSON grant")
 action:=f.String("action","status","status, apply, reconcile")
 if e:=f.Parse(args);e!=nil{return e}
 pub,e:=hex.DecodeString(*pubHex);if e!=nil||len(pub)!=32{return errors.New("bad pinned owner key")}
 b,e:=base64.StdEncoding.DecodeString(*grantB64);if e!=nil{return e}
 var g Grant
 if e=json.Unmarshal(b,&g);e!=nil{return e}
 current,e:=getReceipt(*owner,ed25519.PublicKey(pub));if e!=nil{return e}
 if current.Phase==prepared && *action!="reconcile" {
  fmt.Println("MG_V28_GATEWAY_ABSTAIN_DURING_OWNER_IN_DOUBT")
  return nil
 }
 if current.Phase!=observed&&*action!="reconcile"{return errors.New("MG_V28_UNKNOWN_OWNER_PHASE")}
 if *action=="status" {
  fmt.Printf("MG_V28_GATEWAY_OWNER_SIGNED_CURRENT_EPOCH_%d
",current.Grant.Epoch)
  return nil
 }
 if *action=="apply" && g.Epoch<=current.Grant.Epoch {
  fmt.Println("MG_V28_GATEWAY_REJECT_STALE_SIGNED_GRANT")
  return nil
 }
 if *action!="apply"&&*action!="reconcile"{return errors.New("invalid action")}
 receipt,status,e:=postOwner(*owner,*action,ed25519.PublicKey(pub),g)
 if e!=nil {return fmt.Errorf("MG_V28_OWNER_EFFECT_UNCERTAIN status=%d: %w",status,e)}
 if receipt.Phase!=observed{return errors.New("MG_V28_OWNER_DID_NOT_OBSERVE_NATIVE")}
 if *action=="reconcile" {fmt.Println("MG_V28_GATEWAY_NATIVE_RECONCILED_AFTER_OWNER_RESTART");return nil}
 fmt.Printf("MG_V28_GATEWAY_NATIVE_VALID_APPLIED_EPOCH_%d
",receipt.Grant.Epoch)
 return nil
}
func probe(args []string)error{
 f:=flag.NewFlagSet("probe",flag.ContinueOnError)
 root:=f.String("root","","owner private dir")
 jwt:=f.String("jwt","","native JWT path")
 engine:=f.String("engine","","native Engine endpoint")
 if e:=f.Parse(args);e!=nil{return e}
 for _,p:=range []string{filepath.Join(*root,"owner.key"),filepath.Join(*root,"owner.state"),*jwt}{
  if _,e:=os.ReadFile(p);e==nil{return fmt.Errorf("MG_V28_GATEWAY_READ_PROTECTED_SECRET %s",p)}
 }
 fmt.Println("MG_V28_GATEWAY_OS_PRIVATE_OWNER_AND_JWT_DENIED")
 n:=Native{URL:*engine}
 _,status,e:=n.rpc("engine_forkchoiceUpdatedV4",[]any{map[string]string{},nil,nil})
 if status!=401{return fmt.Errorf("MG_V28_UNAUTH_NATIVE_STATUS_%d err=%v",status,e)}
 fmt.Println("MG_V28_DIRECT_NATIVE_ENGINE_WITHOUT_JWT_UNAUTHORIZED_401")
 return nil
}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"missing mode");os.Exit(2)}
 var e error
 switch os.Args[1]{
 case "serve":e=serve(os.Args[2:])
 case "gateway":e=gateway(os.Args[2:])
 case "probe":e=probe(os.Args[2:])
 default:e=errors.New("unknown command "+strconv.Quote(os.Args[1]))
 }
 if e!=nil{fmt.Fprintln(os.Stderr,"MG_V28_ERROR",e);os.Exit(1)}
}
