package connectip

// This file is injected as an UNTRACKED test into a pinned upstream checkout.
// It is a research observation of actual cancellation error codes, not an upstream fix.
import (
 "context"
 "fmt"
 "net/netip"
 "strings"
 "testing"
 "time"

 "github.com/quic-go/quic-go"
 "github.com/quic-go/quic-go/http3"
 "github.com/quic-go/quic-go/quicvarint"
)

type mathgraphObservedStream struct {
 *mockStream
 readCodes chan quic.StreamErrorCode
 writeCodes chan quic.StreamErrorCode
}
func (m *mathgraphObservedStream) CancelRead(c quic.StreamErrorCode) {
 select { case m.readCodes <- c: default: }
}
func (m *mathgraphObservedStream) CancelWrite(c quic.StreamErrorCode) {
 select { case m.writeCodes <- c: default: }
}
func mathgraphNewStream(data []byte) *mathgraphObservedStream {
 inputFinished:=make(chan []byte)
 close(inputFinished)
 return &mathgraphObservedStream{
  mockStream:&mockStream{reading:data,toRead:inputFinished},
  readCodes:make(chan quic.StreamErrorCode,4),
  writeCodes:make(chan quic.StreamErrorCode,4),
 }
}
func mathgraphRoute(start,end string,p uint8) IPRoute {
 return IPRoute{StartIP:netip.MustParseAddr(start),EndIP:netip.MustParseAddr(end),IPProtocol:p}
}
func mathgraphEncoded(routes ...IPRoute) []byte {
 return (&routeAdvertisementCapsule{IPAddressRanges:routes}).append(nil)
}
func mathgraphInvalidIPVersion() []byte {
 payload:=[]byte{5,192,0,2,1,192,0,2,1,6}
 result:=quicvarint.Append(nil,uint64(capsuleTypeRouteAdvertisement))
 result=quicvarint.Append(result,uint64(len(payload)))
 return append(result,payload...)
}
func mathgraphWaitCode(t *testing.T,ch <-chan quic.StreamErrorCode,label string) quic.StreamErrorCode {
 t.Helper()
 select {
 case got:=<-ch: return got
 case <-time.After(4*time.Second): t.Fatalf("missing %s cancellation",label); return 0
 }
}
func TestMathGraphRFC9484NativeAbortHandoff(t *testing.T) {
 if http3.ErrCodeExcessiveLoad != 0x107 || http3.ErrCodeMessageError != 0x10e {
  t.Fatal("unexpected HTTP/3 code definitions")
 }
 cases:=[]struct{name string; data []byte; errorSubstring string; shouldAbort bool}{
  {"malformed_ip_version",mathgraphInvalidIPVersion(),"invalid IP version: 5",true},
  {"same_protocol_overlap",mathgraphEncoded(
   mathgraphRoute("192.0.2.0","192.0.2.0",6),
   mathgraphRoute("192.0.2.0","192.0.2.0",6)),
   "disjoint",true},
  {"optional_cross_protocol_zero_overlap",mathgraphEncoded(
   mathgraphRoute("192.0.2.0","192.0.2.0",0),
   mathgraphRoute("192.0.2.0","192.0.2.0",6)),
   "route overlaps",true},
  {"different_specific_protocols_same_range",mathgraphEncoded(
   mathgraphRoute("192.0.2.0","192.0.2.0",6),
   mathgraphRoute("192.0.2.0","192.0.2.0",17)),
   "",false},
  {"empty_advertisement",mathgraphEncoded(),"",false},
 }
 for _,test:=range cases {
  t.Run(test.name,func(t *testing.T){
   s:=mathgraphNewStream(test.data)
   conn:=newProxiedConn(s,nil)
   select {
   case <-conn.ctx.Done():
   case <-time.After(4*time.Second): t.Fatal("connection did not resolve")
   }
   cause:=context.Cause(conn.ctx)
   if test.shouldAbort {
    if cause==nil||!strings.Contains(cause.Error(),test.errorSubstring) {
     t.Fatalf("wrong abort cause: %v, expected substring %q",cause,test.errorSubstring)
    }
    readCode:=mathgraphWaitCode(t,s.readCodes,"read")
    writeCode:=mathgraphWaitCode(t,s.writeCodes,"write")
    if readCode!=quic.StreamErrorCode(http3.ErrCodeExcessiveLoad) ||
       writeCode!=quic.StreamErrorCode(http3.ErrCodeExcessiveLoad){
      t.Fatalf("unexpected native error codes read=%#x write=%#x",readCode,writeCode)
    }
    t.Logf("MATHGRAPH_ABORT_OBSERVED case=%s read=%#x write=%#x cause=%q expected_for_malformed_capsule=%#x",
       test.name,readCode,writeCode,cause.Error(),uint64(http3.ErrCodeMessageError))
   } else {
    select {
    case code:=<-s.readCodes: t.Fatalf("unexpected read-cancel on valid capsule: %#x",code)
    default:
    }
    select {
    case code:=<-s.writeCodes: t.Fatalf("unexpected write-cancel on valid capsule: %#x",code)
    default:
    }
    conn.mu.Lock()
    actualRoutes:=len(conn.peerRoutes)
    conn.mu.Unlock()
    if actualRoutes!=len([]IPRoute{}) && test.name=="empty_advertisement" {
      t.Fatalf("empty capsule unexpectedly created routes: %d", actualRoutes)
    }
    t.Logf("MATHGRAPH_VALID_OBSERVED case=%s graceful_no_abort=true route_count=%d",test.name,actualRoutes)
   }
  })
 }
 t.Log(fmt.Sprintf("MATHGRAPH_BOUNDARY_RESULT original_HTTP3_code=%#x normative_candidate=%#x",
   uint64(http3.ErrCodeExcessiveLoad),uint64(http3.ErrCodeMessageError)))
}


// Follow-on control, added only after the original malformed-capsule result.
// Resource saturation is a different reason to cancel: do not globally swap
// H3_EXCESSIVE_LOAD to H3_MESSAGE_ERROR without preserving this distinction.
func TestMathGraphRFC9484QueueLoadControl(t *testing.T) {
 var bytes []byte
 for i:=0;i<maxQueuedCapsules+1;i++ {
  bytes=(&addressAssignCapsule{}).append(bytes)
 }
 stream:=mathgraphNewStream(bytes)
 conn:=newProxiedConn(stream,nil)
 select {
 case <-conn.ctx.Done():
 case <-time.After(4*time.Second): t.Fatal("queue overload never caused connection closure")
 }
 cause:=context.Cause(conn.ctx)
 if cause==nil || !strings.Contains(cause.Error(),"address assignment queue full") {
  t.Fatalf("wrong resource-exhaustion error: %v",cause)
 }
 readCode:=mathgraphWaitCode(t,stream.readCodes,"overload read")
 writeCode:=mathgraphWaitCode(t,stream.writeCodes,"overload write")
 if readCode!=quic.StreamErrorCode(http3.ErrCodeExcessiveLoad) ||
    writeCode!=quic.StreamErrorCode(http3.ErrCodeExcessiveLoad) {
   t.Fatalf("unexpected resource-exhaustion cancellation read=%#x write=%#x",readCode,writeCode)
 }
 t.Logf("MATHGRAPH_OVERLOAD_OBSERVED read=%#x write=%#x cause=%q",readCode,writeCode,cause.Error())
}
