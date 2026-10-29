//go:build balexperiment

// GOETH V27: signed challenge-bound owner high-water observations versus a
// mutable gateway journal. Native Geth is exercised through real JWT Engine V4.
// The owner signer is held only by the parent test process, not child configs.
// RESEARCH-ONLY: owner parent remains alive; same-UID OS isolation is NOT proven.
package catalyst

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
)

const balV27AnchorVersion = "MG_V27_ANCHOR_V1"
const balV27Observed = "OWNER_OBSERVED_NATIVE_STATE"

type balV27Receipt struct {
	Version string
	Nonce string
	State string
	Grant balV24Grant
	Signature []byte
}

func balV27ReceiptDigest(r balV27Receipt) []byte {
	r.Signature = nil
	payload, _ := json.Marshal(r)
	sum := sha256.Sum256(append([]byte("MG_V27_OWNER_ANCHOR_DOMAIN_V1\x00"), payload...))
	return sum[:]
}

type balV27Owner struct {
	mu sync.Mutex
	current balV24Grant
	grantPub ed25519.PublicKey
	pub ed25519.PublicKey
	priv ed25519.PrivateKey
	h balV23ImportedHarness
	server *httptest.Server
}

func balV27NewOwner(t *testing.T, h balV23ImportedHarness, grantKey ed25519.PrivateKey, first balV24Grant) *balV27Owner {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil { t.Fatal(err) }
	o := &balV27Owner{current:first, grantPub:grantKey.Public().(ed25519.PublicKey), pub:pub, priv:priv, h:h}
	if err := o.checkCurrent(first); err != nil { t.Fatal("UNKNOWN/owner initial state:",err) }
	o.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request) {
		if r.Method!="GET" || r.URL.Path!="/observed" { http.Error(w,"invalid path",http.StatusNotFound); return }
		nonce:=r.URL.Query().Get("nonce")
		if len(nonce)!=40 { http.Error(w,"bad nonce",http.StatusBadRequest); return }
		o.mu.Lock()
		reply:=balV27Receipt{Version:balV27AnchorVersion,Nonce:nonce,State:balV27Observed,Grant:o.current}
		reply.Signature=ed25519.Sign(o.priv,balV27ReceiptDigest(reply))
		o.mu.Unlock()
		w.Header().Set("Content-Type","application/json")
		_ = json.NewEncoder(w).Encode(reply)
	}))
	t.Cleanup(o.server.Close)
	return o
}

func (o *balV27Owner) checkCurrent(g balV24Grant) error {
	if g.Scope!=balV24Scope || g.Epoch==0 || g.Head==(common.Hash{}) ||
		g.Final==(common.Hash{}) || !ed25519.Verify(o.grantPub,balV24Digest(g),g.Signature) {
		return errors.New("MG_V27_OWNER_INVALID_GRANT")
	}
	h,f:=o.h.current()
	if h!=g.Head || f!=g.Final {return fmt.Errorf("MG_V27_OWNER_NATIVE_MISMATCH actual=%s/%s expected=%s/%s",h,f,g.Head,g.Final)}
	return nil
}

// Only the parent (synthetic owner) can advance the signed source-of-truth.
// Gateway child processes have read-only access and receive no signing key.
func (o *balV27Owner) advance(g balV24Grant) error {
	o.mu.Lock(); defer o.mu.Unlock()
	if g.Epoch<=o.current.Epoch || g.Genesis!=o.current.Genesis {
		return errors.New("MG_V27_OWNER_NOT_MONOTONIC")
	}
	if err:=o.checkCurrent(g); err!=nil {return err}
	o.current=g
	return nil
}

type balV27Input struct {
	Native balV26ChildInput
	OwnerURL string
	OwnerPub []byte
}

func balV27ReadOwner(cfg balV27Input) (balV27Receipt,error) {
	if len(cfg.OwnerPub)!=ed25519.PublicKeySize {return balV27Receipt{},errors.New("MG_V27_MISSING_PINNED_OWNER_KEY")}
	nonceBytes:=make([]byte,20)
	if _,err:=rand.Read(nonceBytes);err!=nil{return balV27Receipt{},err}
	nonce:=hex.EncodeToString(nonceBytes)
	client:=http.Client{Timeout:15*time.Second}
	resp,err:=client.Get(cfg.OwnerURL+"/observed?nonce="+nonce)
	if err!=nil{return balV27Receipt{},fmt.Errorf("MG_V27_OWNER_SOURCE_UNAVAILABLE: %w",err)}
	defer resp.Body.Close()
	if resp.StatusCode!=200 {return balV27Receipt{},errors.New("MG_V27_OWNER_BAD_STATUS")}
	var signed balV27Receipt
	if err:=json.NewDecoder(io.LimitReader(resp.Body,16384)).Decode(&signed);err!=nil {
		return balV27Receipt{},fmt.Errorf("MG_V27_OWNER_DECODE: %w",err)
	}
	if signed.Version!=balV27AnchorVersion || signed.State!=balV27Observed ||
		signed.Nonce!=nonce || !balV26GrantValid(cfg.Native,signed.Grant) ||
		!ed25519.Verify(ed25519.PublicKey(cfg.OwnerPub),balV27ReceiptDigest(signed),signed.Signature) {
		return balV27Receipt{},errors.New("MG_V27_BAD_OWNER_ANCHOR_SIGNATURE_OR_CHALLENGE")
	}
	return signed,nil
}

func balV27ChildExecute(cfg balV27Input) (string,error) {
	if !balV26GrantValid(cfg.Native,cfg.Native.Grant) {
		return "",errors.New("MG_V27_INVALID_REQUEST_GRANT")
	}
	owner,err:=balV27ReadOwner(cfg)
	if err!=nil{return "",err}
	journal,err:=balV26ReadJournal(cfg.Native)
	if err!=nil{return "",err}
	// Recover is permitted only with current owner-signed grant and an
	// independently read exact native head/final observation. This model
	// does not establish historical effect parity or all-path mediation.
	if cfg.Native.Mode=="recover" {
		if journal!=nil && journal.Grant.Epoch>owner.Grant.Epoch {
			return "",errors.New("MG_V27_OWNER_ANCHOR_LAGS_JOURNAL")
		}
		client,err:=balV26Dial(cfg.Native)
		if err!=nil{return "",err}
		defer client.Close()
		head,final,err:=balV26Observation(client)
		if err!=nil{return "",err}
		if head!=owner.Grant.Head || final!=owner.Grant.Final {
			return "",fmt.Errorf("MG_V27_NATIVE_MISMATCH actual=%s/%s owner=%s/%s",head,final,owner.Grant.Head,owner.Grant.Final)
		}
		rec:=balV25JournalRecord{Version:balV25JournalVersion,Phase:balV25Observed,Grant:owner.Grant}
		if err:=balV26Save(cfg.Native.Journal,rec);err!=nil{return "",err}
		return "MG_V27_RESTORED_JOURNAL_FROM_CHALLENGE_SIGNED_OWNER_OBSERVATION",nil
	}
	if journal==nil {
		return "",errors.New("MG_V27_MISSING_JOURNAL_FAIL_CLOSED")
	}
	if journal.Phase==balV25Prepared {
		return "",errors.New("MG_V27_PREPARED_IN_DOUBT")
	}
	if journal.Grant.Epoch<owner.Grant.Epoch {
		return "",errors.New("MG_V27_JOURNAL_ROLLBACK_FAIL_CLOSED")
	}
	if journal.Grant.Epoch>owner.Grant.Epoch {
		return "",errors.New("MG_V27_OWNER_ANCHOR_LAGS_JOURNAL")
	}
	if journal.Grant.Head!=owner.Grant.Head || journal.Grant.Final!=owner.Grant.Final ||
		journal.Grant.Genesis!=owner.Grant.Genesis {
		return "",errors.New("MG_V27_JOURNAL_OWNER_IDENTITY_MISMATCH")
	}
	if cfg.Native.Grant.Epoch<=owner.Grant.Epoch {
		return "",errors.New("MG_V27_STALE_SIGNED_GRANT_REJECTED")
	}
	if cfg.Native.Mode!="apply" {
		return "",errors.New("MG_V27_HIGHER_GRANT_REQUIRES_APPLY_MODE")
	}
	// Authoritative receipt was fresh and validated, and journal matches
	// the owner's already-observed floor. Persist intent before effect.
	intent:=balV25JournalRecord{Version:balV25JournalVersion,Phase:balV25Prepared,Grant:cfg.Native.Grant}
	if err:=balV26Save(cfg.Native.Journal,intent);err!=nil{return "",fmt.Errorf("MG_V27_PREPARE_FAIL: %w",err)}
	native,err:=balV26Dial(cfg.Native)
	if err!=nil{return "",err}
	defer native.Close()
	ctx,cancel:=context.WithTimeout(context.Background(),20*time.Second)
	defer cancel()
	var reply engine.ForkChoiceResponse
	err=native.CallContext(ctx,&reply,"engine_forkchoiceUpdatedV4",
		engine.ForkchoiceStateV1{HeadBlockHash:cfg.Native.Grant.Head,FinalizedBlockHash:cfg.Native.Grant.Final},nil,nil)
	if err!=nil || reply.PayloadStatus.Status!=engine.VALID {
		return "",fmt.Errorf("MG_V27_NATIVE_NON_VALID_OR_AMBIGUOUS status=%s err=%v",reply.PayloadStatus.Status,err)
	}
	head,final,err:=balV26Observation(native)
	if err!=nil{return "",err}
	if head!=cfg.Native.Grant.Head || final!=cfg.Native.Grant.Final {
		return "",errors.New("MG_V27_NATIVE_OBSERVATION_NOT_EXACT")
	}
	observed:=intent
	observed.Phase=balV25Observed
	if err:=balV26Save(cfg.Native.Journal,observed);err!=nil{return "",err}
	// The parent owner must independently update its latest observation after
	// reviewing actual native state. Until then, child cannot later progress.
	return fmt.Sprintf("MG_V27_OWNER_FLOOR_VERIFIED_NATIVE_VALID_EPOCH_%d",cfg.Native.Grant.Epoch),nil
}

func TestBALV27GatewayChildProcess(t *testing.T) {
	path:=os.Getenv("MG_V27_CHILD_INPUT")
	if path=="" {return}
	data,err:=os.ReadFile(path)
	if err!=nil{t.Fatal(err)}
	var cfg balV27Input
	if err:=json.Unmarshal(data,&cfg);err!=nil{t.Fatal(err)}
	m,err:=balV27ChildExecute(cfg)
	if err!=nil {
		fmt.Fprintln(os.Stdout,"MG_V27_CHILD_ERROR "+err.Error())
		t.Fatal(err)
	}
	fmt.Fprintln(os.Stdout,m)
}

func balV27RunChild(t *testing.T,cfg balV27Input)(string,error) {
	t.Helper()
	exe,err:=os.Executable()
	if err!=nil{t.Fatal(err)}
	path:=filepath.Join(t.TempDir(),"v27-child.json")
	b,err:=json.Marshal(cfg)
	if err!=nil{t.Fatal(err)}
	if err:=os.WriteFile(path,b,0600);err!=nil{t.Fatal(err)}
	ctx,cancel:=context.WithTimeout(context.Background(),50*time.Second)
	defer cancel()
	cmd:=exec.CommandContext(ctx,exe,"-test.run=^TestBALV27GatewayChildProcess$","-test.v")
	cmd.Env=append(os.Environ(),"MG_V27_CHILD_INPUT="+path)
	data,err:=cmd.CombinedOutput()
	return string(data),err
}

func balV27Expect(t *testing.T,cfg balV27Input,marker string,success bool) {
	t.Helper()
	s,err:=balV27RunChild(t,cfg)
	if !strings.Contains(s,marker) || (err==nil)!=success {
		t.Fatalf("UNKNOWN/V27: mode=%s expected %q success=%t; err=%v output=%s",cfg.Native.Mode,marker,success,err,s)
	}
}

type balV27Fixture struct {
	h balV23ImportedHarness
	key ed25519.PrivateKey
	a,b balV24Grant
	owner *balV27Owner
	journal string
}

func balV27NewFixture(t *testing.T) balV27Fixture {
	t.Helper()
	h,_,a,b,key:=balV24Environment(t,true,nil)
	ctx,cancel:=context.WithTimeout(context.Background(),15*time.Second)
	defer cancel()
	var result engine.ForkChoiceResponse
	err:=h.clients[1].CallContext(ctx,&result,"engine_forkchoiceUpdatedV4",h.fcu(1),nil,nil)
	if err!=nil || result.PayloadStatus.Status!=engine.VALID {t.Fatalf("UNKNOWN/setup: B initial Engine VALID: %+v %v",result,err)}
	head,final:=h.current()
	if head!=b.Head || final!=b.Final {t.Fatalf("UNKNOWN/setup: B not native canonical")}
	o:=balV27NewOwner(t,h,key,b)
	p:=filepath.Join(t.TempDir(),"gateway-journal.json")
	record:=balV25JournalRecord{Version:balV25JournalVersion,Phase:balV25Observed,Grant:b}
	if err:=balV26Save(p,record);err!=nil{t.Fatal(err)}
	return balV27Fixture{h:h,key:key,a:a,b:b,owner:o,journal:p}
}
func (f balV27Fixture) config(mode string,grant balV24Grant)balV27Input {
	return balV27Input{
		Native:balV26ChildInput{
			Mode:mode,Endpoint:f.h.stack.HTTPAuthEndpoint(),
			JWTFile:f.h.stack.Config().JWTSecret,Journal:f.journal,
			Public:f.key.Public().(ed25519.PublicKey),
			Genesis:grant.Genesis,Grant:grant,
		},
		OwnerURL:f.owner.server.URL,OwnerPub:f.owner.pub,
	}
}
func (f balV27Fixture) assertCanonical(t *testing.T,grant balV24Grant) {
	t.Helper()
	h,final:=f.h.current()
	if h!=grant.Head || final!=grant.Final {
		t.Fatalf("UNKNOWN/native canonical state %s/%s want %s/%s",h,final,grant.Head,grant.Final)
	}
}

func TestBALV27DeletedJournalRefusesStaleAndRecoversHigherEpoch(t *testing.T) {
	f:=balV27NewFixture(t)
	if err:=os.Remove(f.journal);err!=nil{t.Fatal(err)}
	balV27Expect(t,f.config("apply",f.a),"MG_V27_MISSING_JOURNAL_FAIL_CLOSED",false)
	f.assertCanonical(t,f.b)
	t.Log("MG_V27_JOURNAL_DELETION_NO_STALE_NATIVE_EXECUTION")
	balV27Expect(t,f.config("recover",f.b),"MG_V27_RESTORED_JOURNAL_FROM_CHALLENGE_SIGNED_OWNER_OBSERVATION",true)
	balV27Expect(t,f.config("apply",f.a),"MG_V27_STALE_SIGNED_GRANT_REJECTED",false)
	fresh:=balV24Sign(f.key,f.b.Genesis,3,f.b.Head,f.b.Final)
	balV27Expect(t,f.config("apply",fresh),"MG_V27_OWNER_FLOOR_VERIFIED_NATIVE_VALID_EPOCH_3",true)
	f.assertCanonical(t,fresh)
	if err:=f.owner.advance(fresh);err!=nil{t.Fatal(err)}
	t.Log("MG_V27_DELETED_HISTORY_RECONCILED_AND_FRESH_EPOCH3_NATIVE_VALID")
}

func TestBALV27JournalRollbackRefusesSupersededGrantThenRecovers(t *testing.T) {
	f:=balV27NewFixture(t)
	older,err:=os.ReadFile(f.journal)
	if err!=nil{t.Fatal(err)}
	c:=balV24Sign(f.key,f.b.Genesis,3,f.b.Head,f.b.Final)
	d:=balV24Sign(f.key,f.b.Genesis,4,f.b.Head,f.b.Final)
	if err:=f.owner.advance(c);err!=nil{t.Fatal(err)}
	if err:=f.owner.advance(d);err!=nil{t.Fatal(err)}
	latest:=balV25JournalRecord{Version:balV25JournalVersion,Phase:balV25Observed,Grant:d}
	if err:=balV26Save(f.journal,latest);err!=nil{t.Fatal(err)}
	if err:=os.WriteFile(f.journal,older,0600);err!=nil{t.Fatal(err)}
	balV27Expect(t,f.config("apply",c),"MG_V27_JOURNAL_ROLLBACK_FAIL_CLOSED",false)
	f.assertCanonical(t,f.b)
	t.Log("MG_V27_ROLLED_BACK_JOURNAL_CANNOT_REISSUE_EPOCH3")
	balV27Expect(t,f.config("recover",d),"MG_V27_RESTORED_JOURNAL_FROM_CHALLENGE_SIGNED_OWNER_OBSERVATION",true)
	balV27Expect(t,f.config("apply",c),"MG_V27_STALE_SIGNED_GRANT_REJECTED",false)
	next:=balV24Sign(f.key,f.b.Genesis,5,f.b.Head,f.b.Final)
	balV27Expect(t,f.config("apply",next),"MG_V27_OWNER_FLOOR_VERIFIED_NATIVE_VALID_EPOCH_5",true)
	f.assertCanonical(t,next)
	if err:=f.owner.advance(next);err!=nil{t.Fatal(err)}
	t.Log("MG_V27_ROLLBACK_RECOVERED_FROM_OWNER_AND_EPOCH5_NATIVE_VALID")
}

func TestBALV27ForgedOrReplayedOwnerReceiptFailsClosed(t *testing.T) {
	f:=balV27NewFixture(t)
	// The fake endpoint cannot mint the parent's owner-private Ed25519 key.
	fake:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request) {
		reply:=balV27Receipt{Version:balV27AnchorVersion,Nonce:"0000000000000000000000000000000000000000",
			State:balV27Observed,Grant:f.b}
		reply.Signature=make([]byte,ed25519.SignatureSize)
		_ = json.NewEncoder(w).Encode(reply)
	}))
	defer fake.Close()
	next:=balV24Sign(f.key,f.b.Genesis,3,f.b.Head,f.b.Final)
	cfg:=f.config("apply",next)
	cfg.OwnerURL=fake.URL
	balV27Expect(t,cfg,"MG_V27_BAD_OWNER_ANCHOR_SIGNATURE_OR_CHALLENGE",false)
	f.assertCanonical(t,f.b)
	// Also verify owner-only monotonic source refuses old observed epochs.
	if err:=f.owner.advance(f.a);err==nil || !strings.Contains(err.Error(),"MG_V27_OWNER_NOT_MONOTONIC") {
		t.Fatalf("UNKNOWN/owner allowed high-water rollback: %v",err)
	}
	t.Log("MG_V27_FORGED_OWNER_RECEIPT_AND_OWNER_EPOCH_ROLLBACK_REJECTED")
}

func TestBALV27DirectEngineBypassStillDefeatsOptionalOwnerGateway(t *testing.T) {
	f:=balV27NewFixture(t)
	ctx,cancel:=context.WithTimeout(context.Background(),20*time.Second)
	defer cancel()
	var reply engine.ForkChoiceResponse
	err:=f.h.clients[0].CallContext(ctx,&reply,"engine_forkchoiceUpdatedV4",f.h.fcu(0),nil,nil)
	if err!=nil || reply.PayloadStatus.Status!=engine.VALID {
		t.Fatalf("UNKNOWN/setup: native Engine direct bypass: %+v %v",reply,err)
	}
	f.assertCanonical(t,f.a)
	balV27Expect(t,f.config("recover",f.b),"MG_V27_NATIVE_MISMATCH",false)
	t.Log("MG_V27_RAW_ENGINE_EFFECT_PATH_STILL_BYPASSABLE")
}
