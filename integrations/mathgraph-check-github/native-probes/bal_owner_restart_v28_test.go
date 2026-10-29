//go:build balexperiment

// GOETH V28: restart the owner-side OS process after real native Engine VALID
// before its observed-state commit. Gateway is a different OS UID (nobody),
// with no native JWT or owner signing key. Research-only, synthetic grants.
package catalyst

import (
 "bufio"
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "os/exec"
 "path/filepath"
 "strconv"
 "strings"
 "syscall"
 "testing"
 "time"

 "github.com/ethereum/go-ethereum/beacon/engine"
)

type balV28SourceFixture struct {
 h balV23ImportedHarness
 b balV24Grant
 a balV24Grant
 grantKey ed25519.PrivateKey
 ownerPub ed25519.PublicKey
 ownerDir string
 initialOwnerStore []byte
 bin string
}

func balV28Setup(t *testing.T) balV28SourceFixture {
 t.Helper()
 bin:=os.Getenv("MG_V28_OWNER_BIN")
 if bin=="" {t.Fatal("UNKNOWN/setup: MG_V28_OWNER_BIN not provided by pinned CI")}
 if st,e:=os.Stat(bin);e!=nil||st.Mode()&0111==0{t.Fatalf("UNKNOWN/setup: owner helper not executable: %v",e)}
 nobody,e:=exec.Command("sudo","-n","-u","nobody","--","id","-u").CombinedOutput()
 if e!=nil||strings.TrimSpace(string(nobody))!="65534" {
  t.Fatalf("UNKNOWN/setup: lower-privilege nobody UID not reachable: %v %s",e,nobody)
 }
 h,_,a,b,grantKey:=balV24Environment(t,true,nil)
 ctx,cancel:=context.WithTimeout(context.Background(),15*time.Second)
 defer cancel()
 var response engine.ForkChoiceResponse
 e=h.clients[1].CallContext(ctx,&response,"engine_forkchoiceUpdatedV4",h.fcu(1),nil,nil)
 if e!=nil||response.PayloadStatus.Status!=engine.VALID {
  t.Fatalf("UNKNOWN/setup: Geth native Engine B2 not VALID: %+v err=%v",response,e)
 }
 if head,final:=h.current();head!=b.Head||final!=b.Final {
  t.Fatalf("UNKNOWN/setup: B2 not actual canonical")
 }
 pub,priv,e:=ed25519.GenerateKey(rand.Reader)
 if e!=nil{t.Fatal(e)}
 ownerDir:=filepath.Join(t.TempDir(),"owner-private")
 if e=os.Mkdir(ownerDir,0700);e!=nil{t.Fatal(e)}
 if e=os.WriteFile(filepath.Join(ownerDir,"owner.key"),[]byte(hex.EncodeToString(priv)),0600);e!=nil{t.Fatal(e)}
 initial,e:=json.Marshal(struct{
  Version string
  Phase string
  Grant balV24Grant
 }{Version:"MG_V28_OWNER_V1",Phase:"OBSERVED",Grant:b})
 if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(filepath.Join(ownerDir,"owner.state"),initial,0600);e!=nil{t.Fatal(e)}
 return balV28SourceFixture{h:h,b:b,a:a,grantKey:grantKey,ownerPub:pub,ownerDir:ownerDir,initialOwnerStore:initial,bin:bin}
}
func (f balV28SourceFixture) grant(epoch uint64) balV24Grant {
 return balV24Sign(f.grantKey,f.b.Genesis,epoch,f.b.Head,f.b.Final)
}
func (f balV28SourceFixture) state(t *testing.T)(string,uint64){
 t.Helper()
 b,e:=os.ReadFile(filepath.Join(f.ownerDir,"owner.state"));if e!=nil{t.Fatal(e)}
 var rec struct{Version string;Phase string;Grant balV24Grant}
 if e=json.Unmarshal(b,&rec);e!=nil{t.Fatal(e)}
 if rec.Version!="MG_V28_OWNER_V1" {t.Fatalf("UNKNOWN/owner store version %q",rec.Version)}
 return rec.Phase,rec.Grant.Epoch
}

type balV28OwnerProc struct {
 cmd *exec.Cmd
 stderr bytes.Buffer
 events chan string
 url string
 stopped bool
}
func (p *balV28OwnerProc) stop(t *testing.T) {
 t.Helper()
 if p.stopped{return}
 p.stopped=true
 if p.cmd.Process==nil{t.Fatal("UNKNOWN/owner no process")}
 if e:=p.cmd.Process.Kill();e!=nil{t.Fatalf("UNKNOWN/owner SIGKILL: %v",e)}
 e:=p.cmd.Wait()
 var exit *exec.ExitError
 if !errors.As(e,&exit){t.Fatalf("UNKNOWN/owner did not terminate under SIGKILL: %v",e)}
 state,ok:=exit.Sys().(syscall.WaitStatus)
 if !ok||!state.Signaled()||state.Signal()!=syscall.SIGKILL{
  t.Fatalf("UNKNOWN/owner not actual SIGKILL: %+v",exit.Sys())
 }
}
func (p *balV28OwnerProc) observe(t *testing.T,needle string,timeout time.Duration){
 t.Helper()
 deadline:=time.After(timeout)
 for {
  select {
  case v,ok:=<-p.events:
   if !ok{t.Fatalf("UNKNOWN/owner stdout ended before %s, stderr=%s",needle,p.stderr.String())}
   if strings.Contains(v,needle){return}
  case <-deadline:
   t.Fatalf("UNKNOWN/owner timeout waiting for %s, stderr=%s",needle,p.stderr.String())
  }
 }
}
func balV28StartOwner(t *testing.T,f balV28SourceFixture,faultEpoch uint64)*balV28OwnerProc {
 t.Helper()
 args:=[]string{"serve","--root",f.ownerDir,"--engine",f.h.stack.HTTPAuthEndpoint(),
  "--jwt",f.h.stack.Config().JWTSecret,"--grant-pub",hex.EncodeToString(f.grantKey.Public().(ed25519.PublicKey)),
  "--fault-epoch",strconv.FormatUint(faultEpoch,10)}
 p:=&balV28OwnerProc{cmd:exec.Command(f.bin,args...),events:make(chan string,16)}
 output,e:=p.cmd.StdoutPipe()
 if e!=nil{t.Fatal(e)}
 p.cmd.Stderr=&p.stderr
 if e=p.cmd.Start();e!=nil{t.Fatalf("UNKNOWN/owner process start: %v",e)}
 t.Cleanup(func(){if !p.stopped&&p.cmd.Process!=nil{_ =p.cmd.Process.Kill();_ =p.cmd.Wait();p.stopped=true}})
 go func(){
  scanner:=bufio.NewScanner(output)
  scanner.Buffer(make([]byte,4096),1024*1024)
  for scanner.Scan(){p.events<-scanner.Text()}
  close(p.events)
 }()
 deadline:=time.After(15*time.Second)
 for {
  select{
  case line,ok:=<-p.events:
   if !ok{t.Fatalf("UNKNOWN/owner failed startup stderr=%s",p.stderr.String())}
   if strings.HasPrefix(line,"MG_V28_OWNER_LISTEN="){
    p.url=strings.TrimPrefix(line,"MG_V28_OWNER_LISTEN=")
    return p
   }
  case <-deadline:
   t.Fatalf("UNKNOWN/owner startup timeout stderr=%s",p.stderr.String())
  }
 }
}
func (f balV28SourceFixture) gatewayArgs(ownerURL,action string,g balV24Grant)[]string {
 payload,_:=json.Marshal(g)
 return []string{"-n","-u","nobody","--",f.bin,"gateway",
  "--owner",ownerURL,"--owner-pub",hex.EncodeToString(f.ownerPub),
  "--grant",base64.StdEncoding.EncodeToString(payload),"--action",action}
}
func balV28Gateway(t *testing.T,f balV28SourceFixture,ownerURL,action string,g balV24Grant,marker string){
 t.Helper()
 ctx,cancel:=context.WithTimeout(context.Background(),40*time.Second);defer cancel()
 out,e:=exec.CommandContext(ctx,"sudo",f.gatewayArgs(ownerURL,action,g)...).CombinedOutput()
 if e!=nil||!strings.Contains(string(out),marker){
  t.Fatalf("UNKNOWN/gateway action=%s expected %s: %v output=%s",action,marker,e,out)
 }
}
func balV28Canonical(t *testing.T,f balV28SourceFixture,g balV24Grant){
 t.Helper()
 head,final:=f.h.current()
 if head!=g.Head||final!=g.Final{
  t.Fatalf("UNKNOWN/native head/final %s/%s expected %s/%s",head,final,g.Head,g.Final)
 }
}
func TestBALV28OwnerProcessSIGKILLPreCommitAndLowerPrivilegeRecovery(t *testing.T){
 f:=balV28Setup(t)
 p:=balV28StartOwner(t,f,3)
 ownerURL:=p.url
 ctx,cancel:=context.WithTimeout(context.Background(),45*time.Second);defer cancel()
 cmd:=exec.CommandContext(ctx,"sudo",f.gatewayArgs(ownerURL,"apply",f.grant(3))...)
 var out bytes.Buffer
 cmd.Stdout=&out;cmd.Stderr=&out
 if e:=cmd.Start();e!=nil{t.Fatal(e)}
 p.observe(t,"MG_V28_OWNER_NATIVE_VALID_POST_EFFECT_PRE_COMMIT",25*time.Second)
 balV28Canonical(t,f,f.b)
 if phase,epoch:=f.state(t);phase!="PREPARED"||epoch!=3{
  t.Fatalf("UNKNOWN/owner journal not PREPARED after native VALID: %s/%d",phase,epoch)
 }
 p.stop(t)
 if e:=cmd.Wait();e==nil{
  t.Fatalf("UNKNOWN/fault injection gateway unexpectedly received success: %s",out.String())
 }
 t.Log("MG_V28_ACTUAL_OWNER_OS_SIGKILL_AFTER_NATIVE_VALID_BEFORE_OBSERVED")
 p2:=balV28StartOwner(t,f,0)
 balV28Gateway(t,f,p2.url,"status",f.b,"MG_V28_GATEWAY_ABSTAIN_DURING_OWNER_IN_DOUBT")
 balV28Gateway(t,f,p2.url,"apply",f.grant(4),"MG_V28_GATEWAY_ABSTAIN_DURING_OWNER_IN_DOUBT")
 t.Log("MG_V28_RESTARTED_OWNER_READS_PREPARED_AND_QUARANTINES_GATEWAY")
 balV28Gateway(t,f,p2.url,"reconcile",f.grant(3),"MG_V28_GATEWAY_NATIVE_RECONCILED_AFTER_OWNER_RESTART")
 if phase,epoch:=f.state(t);phase!="OBSERVED"||epoch!=3{
  t.Fatalf("UNKNOWN/owner reconciliation journal %s/%d",phase,epoch)
 }
 balV28Gateway(t,f,p2.url,"apply",f.b,"MG_V28_GATEWAY_REJECT_STALE_SIGNED_GRANT")
 balV28Gateway(t,f,p2.url,"apply",f.grant(4),"MG_V28_GATEWAY_NATIVE_VALID_APPLIED_EPOCH_4")
 balV28Canonical(t,f,f.grant(4))
 t.Log("MG_V28_OWNER_RESTART_RECONCILED_STALE_REJECTED_FRESH_EPOCH4_NATIVE_VALID")
}

func TestBALV28UnprivilegedGatewayCannotReadOwnerJWTOrDirectlyExecuteNative(t *testing.T){
 f:=balV28Setup(t)
 p:=balV28StartOwner(t,f,0)
 ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
 out,e:=exec.CommandContext(ctx,"sudo","-n","-u","nobody","--",f.bin,"probe",
  "--root",f.ownerDir,"--jwt",f.h.stack.Config().JWTSecret,"--engine",f.h.stack.HTTPAuthEndpoint()).CombinedOutput()
 if e!=nil||!strings.Contains(string(out),"MG_V28_GATEWAY_OS_PRIVATE_OWNER_AND_JWT_DENIED")||
  !strings.Contains(string(out),"MG_V28_DIRECT_NATIVE_ENGINE_WITHOUT_JWT_UNAUTHORIZED_401"){
  t.Fatalf("UNKNOWN/isolation: lower privilege probe: %v, %s",e,out)
 }
 balV28Gateway(t,f,p.url,"status",f.b,"MG_V28_GATEWAY_OWNER_SIGNED_CURRENT_EPOCH_2")
 balV28Canonical(t,f,f.b)
 t.Log("MG_V28_BOUNDARY_DIFFERENT_UID_OWNER_STORE_AND_NATIVE_JWT_DENIED_DIRECT_ENGINE_401")
}

func TestBALV28PrivilegedOwnerStateRollbackReauthorizesOldValidSignedGrant(t *testing.T){
 f:=balV28Setup(t)
 p:=balV28StartOwner(t,f,0)
 balV28Gateway(t,f,p.url,"apply",f.grant(3),"MG_V28_GATEWAY_NATIVE_VALID_APPLIED_EPOCH_3")
 if phase,epoch:=f.state(t);phase!="OBSERVED"||epoch!=3{t.Fatalf("UNKNOWN/setup owner3 %s %d",phase,epoch)}
 p.stop(t)
 if e:=os.WriteFile(filepath.Join(f.ownerDir,"owner.state"),f.initialOwnerStore,0600);e!=nil{t.Fatal(e)}
 t.Log("MG_V28_OWNER_DOMAIN_ATTACKER_RESTORED_OLD_B2_STORE")
 p2:=balV28StartOwner(t,f,0)
 balV28Gateway(t,f,p2.url,"status",f.b,"MG_V28_GATEWAY_OWNER_SIGNED_CURRENT_EPOCH_2")
 balV28Gateway(t,f,p2.url,"apply",f.grant(3),"MG_V28_GATEWAY_NATIVE_VALID_APPLIED_EPOCH_3")
 balV28Canonical(t,f,f.grant(3))
 t.Log("MG_V28_NEGATIVE_PRIVILEGED_OWNER_STORE_ROLLBACK_REISSUES_SIGNED_EPOCH3")
}

func TestBALV28MalformedOwnerPrivateStoreFailsClosedOnRestart(t *testing.T){
 f:=balV28Setup(t)
 if e:=os.WriteFile(filepath.Join(f.ownerDir,"owner.state"),[]byte("{invalid-owner-state"),0600);e!=nil{t.Fatal(e)}
 ctx,cancel:=context.WithTimeout(context.Background(),15*time.Second);defer cancel()
 cmd:=exec.CommandContext(ctx,f.bin,"serve","--root",f.ownerDir,
  "--engine",f.h.stack.HTTPAuthEndpoint(),"--jwt",f.h.stack.Config().JWTSecret,
  "--grant-pub",hex.EncodeToString(f.grantKey.Public().(ed25519.PublicKey)))
 out,e:=cmd.CombinedOutput()
 if e==nil||!strings.Contains(string(out),"MG_V28_INVALID_OWNER_STATE"){
  t.Fatalf("UNKNOWN/malformed owner store not rejected: %v %s",e,out)
 }
 balV28Canonical(t,f,f.b)
 t.Log("MG_V28_MALFORMED_OWNER_PRIVATE_STATE_FAIL_CLOSED")
}
