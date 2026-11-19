package connectip

// Temporary, read-only external evidence harness. Copied into the pinned upstream
// checkout only for the CI job. This is NOT an upstream patch or published fix.

import (
  "bytes"
  "encoding/json"
  "fmt"
  "net/netip"
  "os"
  "slices"
  "testing"

  "github.com/quic-go/quic-go/http3"
)

type externalRoute struct {
  Version int `json:"version"`
  Start uint8 `json:"start"`
  End uint8 `json:"end"`
  Protocol uint8 `json:"protocol"`
}
type externalCase struct {
  ID string `json:"id"`
  Routes []externalRoute `json:"routes"`
  Oracle string `json:"oracle"`
}
type externalCorpus struct {
  Schema string `json:"schema"`
  UpstreamSHA string `json:"upstream_sha"`
  Cases []externalCase `json:"cases"`
}

func originalRoute(x externalRoute) IPRoute {
  if x.Version == 4 {
    return IPRoute{
      StartIP: netip.AddrFrom4([4]byte{192, 0, 2, x.Start}),
      EndIP: netip.AddrFrom4([4]byte{192, 0, 2, x.End}),
      IPProtocol: x.Protocol,
    }
  }
  if x.Version != 6 { panic(fmt.Sprintf("unexpected family %d", x.Version)) }
  var a, b [16]byte
  a[0],a[1],a[2],a[3],a[15]=0x20,0x01,0x0d,0xb8,x.Start
  b[0],b[1],b[2],b[3],b[15]=0x20,0x01,0x0d,0xb8,x.End
  return IPRoute{StartIP:netip.AddrFrom16(a),EndIP:netip.AddrFrom16(b),IPProtocol:x.Protocol}
}

func TestExternalRFC9484RouteOrder(t *testing.T) {
  path := os.Getenv("RFC9484_ORACLE_CORPUS")
  if path == "" { t.Fatal("RFC9484_ORACLE_CORPUS is required") }
  data, err := os.ReadFile(path)
  if err != nil { t.Fatal(err) }
  var source externalCorpus
  if err := json.Unmarshal(data, &source); err != nil { t.Fatal(err) }
  if source.Schema != "mathgraph.rfc9484.route-order.v0.1" || source.UpstreamSHA != "9ee608a68fbbc6c377d13da4df2a269580b78909" {
    t.Fatal("wrong oracle/source identity")
  }
  if len(source.Cases) != 10337 { t.Fatalf("wrong corpus size: %d", len(source.Cases)) }

  mandatoryRejected := 0
  structuralAccepted := 0
  optionalAccepted, optionalRejected := 0, 0
  extraRejections := 0
  for _, c := range source.Cases {
    routes := make([]IPRoute, 0, len(c.Routes))
    for _, entry := range c.Routes { routes = append(routes, originalRoute(entry)) }

    validateErr := validateRouteAdvertisement(routes)
    encoded := (&routeAdvertisementCapsule{IPAddressRanges:routes}).append(nil)
    typ, cr, err := http3.NewCapsuleParser(bytes.NewReader(encoded)).Next()
    if err != nil { t.Fatalf("%s: capsule frame failed: %v", c.ID, err) }
    if typ != capsuleTypeRouteAdvertisement { t.Fatalf("%s: wrong capsule type: %d", c.ID, typ) }
    parsed, parseErr := parseRouteAdvertisementCapsule(cr)
    if (validateErr == nil) != (parseErr == nil) {
      t.Errorf("%s: native validator/parser disagree: %v / %v", c.ID, validateErr, parseErr)
      continue
    }
    switch c.Oracle {
    case "MUST_ABORT":
      if validateErr == nil || parseErr == nil {
        t.Errorf("%s: mandatory RFC rejection accepted by native code", c.ID)
      } else { mandatoryRejected++ }
    case "NO_MANDATORY_ABORT":
      if validateErr != nil {
        // Extra rejection can reflect local policy: not automatically an RFC bug.
        extraRejections++
      } else { structuralAccepted++ }
    case "OPTIONAL_ABORT":
      if validateErr != nil { optionalRejected++ } else { optionalAccepted++ }
    default:
      t.Fatalf("invalid external oracle label %q", c.Oracle)
    }
    if parseErr == nil && !slices.Equal(parsed.IPAddressRanges, routes) {
      t.Errorf("%s: accepted capsule bytes did not preserve original routes", c.ID)
    }
  }
  t.Logf("RFC9484_FINITE_NATIVE total=%d must_rejected=%d valid_accepted=%d valid_extra_rejected=%d optional_accepted=%d optional_rejected=%d",
    len(source.Cases),mandatoryRejected,structuralAccepted,extraRejections,optionalAccepted,optionalRejected)
  if mandatoryRejected!=8664 {
    t.Errorf("RFC mandatory rejection count mismatch: %d",mandatoryRejected)
  }
  if structuralAccepted+extraRejections!=1387 || optionalAccepted+optionalRejected!=286 {
    t.Errorf("RFC enumerated class accounting mismatch")
  }
}
