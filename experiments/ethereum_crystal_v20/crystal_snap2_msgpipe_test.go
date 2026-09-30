package snap

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sync/atomic"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/p2p"
	"github.com/ethereum/go-ethereum/p2p/enode"
	"github.com/ethereum/go-ethereum/rlp"
)

type crystalV20Observation struct {
	Protocol           string
	Arm                string
	Trial              int
	Records            int
	SeedRecords        int
	MeasuredRecords    int
	CatchUpNS          int64
	DurableNS          int64
	Digest             string
	TargetHash         string
	AccessListRequests int64
	ClaimBoundary      string
}

type crystalV20Backend struct {
	syncer *syncerV2
}

func (b *crystalV20Backend) Chain() *core.BlockChain {
	return nil
}

func (b *crystalV20Backend) RunPeer(peer *Peer, handler Handler) error {
	return handler(peer)
}

func (b *crystalV20Backend) PeerInfo(id enode.ID) interface{} {
	return nil
}

func (b *crystalV20Backend) Handle(peer *Peer, packet Packet) error {
	switch res := packet.(type) {
	case *AccessListsPacket:
		return b.syncer.OnAccessLists(peer, res.ID, res.AccessLists)
	default:
		return fmt.Errorf("unexpected V20 packet %T", packet)
	}
}

type crystalV20WireServer struct {
	rw       p2p.MsgReadWriter
	bals     map[common.Hash]rlp.RawValue
	requests atomic.Int64
}

func (w *crystalV20WireServer) serve(errc chan<- error) {
	for {
		msg, err := w.rw.ReadMsg()
		if err != nil {
			errc <- err
			return
		}
		if msg.Code != GetAccessListsMsg {
			msg.Discard()
			errc <- fmt.Errorf("unexpected V20 request code %#x", msg.Code)
			return
		}
		var req GetAccessListsPacket
		if err := msg.Decode(&req); err != nil {
			msg.Discard()
			errc <- err
			return
		}
		msg.Discard()
		w.requests.Add(1)

		list := rlp.RawList[rlp.RawValue]{}
		for _, hash := range req.Hashes {
			raw, ok := w.bals[hash]
			if !ok {
				raw = rlp.EmptyString
			}
			if err := list.AppendRaw(raw); err != nil {
				errc <- err
				return
			}
		}
		if err := p2p.Send(w.rw, AccessListsMsg, &AccessListsPacket{
			ID:          req.ID,
			AccessLists: list,
		}); err != nil {
			errc <- err
			return
		}
	}
}

func TestCrystalV20Snap2MsgPipeCatchUp(t *testing.T) {
	arm := os.Getenv("CRYSTAL_V20_ARM")
	if arm != "full" && arm != "compact" {
		t.Fatalf("CRYSTAL_V20_ARM=%q", arm)
	}
	var trial int
	if _, err := fmt.Sscanf(os.Getenv("CRYSTAL_V20_TRIAL"), "%d", &trial); err != nil {
		t.Fatalf("CRYSTAL_V20_TRIAL: %v", err)
	}
	resultPath := os.Getenv("CRYSTAL_V20_RESULT")
	if resultPath == "" {
		t.Fatal("CRYSTAL_V20_RESULT not set")
	}

	raws := crystalV19Corpus(t)
	if len(raws) != crystalV19Records {
		t.Fatalf("records=%d want=%d", len(raws), crystalV19Records)
	}
	seedRaws := raws[:crystalV19SeedRecords]
	measureRaws := raws[crystalV19SeedRecords:]

	seedDir := filepath.Join(t.TempDir(), "seed")
	seedDB := crystalV19OpenPebble(t, seedDir, "crystal/v20/seed/")
	crystalV19ApplySeed(t, seedDB, seedRaws)
	base, target, bals := crystalV19BuildChain(t, seedDB, measureRaws)
	if err := seedDB.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	if err := seedDB.Close(); err != nil {
		t.Fatal(err)
	}

	runDir := filepath.Join(t.TempDir(), "chaindata")
	if err := crystalV19CopyDir(seedDir, runDir); err != nil {
		t.Fatal(err)
	}
	db := crystalV19OpenPebble(t, runDir, fmt.Sprintf("crystal/v20/%s/%d/", arm, trial))
	defer db.Close()

	syncer := newSyncerV2(db, rawdb.HashScheme)
	syncer.pivot = base
	syncer.setPhase(phaseDownload)

	app, net := p2p.MsgPipe()
	defer app.Close()
	defer net.Close()

	peer := NewFakePeer(SNAP2, "crystal-v20-peer", app)
	defer peer.Close()

	backend := &crystalV20Backend{syncer: syncer}
	handlerErr := make(chan error, 1)
	go func() {
		for {
			if err := HandleMessage(backend, peer); err != nil {
				handlerErr <- err
				return
			}
		}
	}()

	server := &crystalV20WireServer{rw: net, bals: bals}
	serverErr := make(chan error, 1)
	go server.serve(serverErr)

	if err := syncer.Register(peer); err != nil {
		t.Fatal(err)
	}

	cancel := make(chan struct{})
	runtime.GC()
	start := time.Now()
	if err := syncer.catchUp(target, cancel); err != nil {
		t.Fatalf("catchUp: %v", err)
	}
	catchUpNS := time.Since(start).Nanoseconds()
	if err := db.SyncKeyValue(); err != nil {
		t.Fatal(err)
	}
	durableNS := time.Since(start).Nanoseconds()

	loader := newSyncerV2(db, rawdb.HashScheme)
	loader.loadSyncStatus()
	if loader.pivot == nil || loader.pivot.Hash() != target.Hash() {
		t.Fatalf("persisted pivot mismatch: have=%v want=%v", loader.pivot, target.Hash())
	}
	requests := server.requests.Load()
	if requests <= 0 {
		t.Fatal("SNAP/2 wire server saw no BAL requests")
	}

	select {
	case err := <-serverErr:
		t.Fatalf("wire server failed before completion: %v", err)
	default:
	}
	select {
	case err := <-handlerErr:
		t.Fatalf("wire handler failed before completion: %v", err)
	default:
	}

	digest := crystalV19Digest(t, db)
	obs := crystalV20Observation{
		Protocol:           "ETHEREUM_CRYSTAL_V20_SNAP2_MSGPIPE",
		Arm:                arm,
		Trial:              trial,
		Records:            len(raws),
		SeedRecords:        len(seedRaws),
		MeasuredRecords:    len(measureRaws),
		CatchUpNS:          catchUpNS,
		DurableNS:          durableNS,
		Digest:             digest,
		TargetHash:         target.Hash().Hex(),
		AccessListRequests: requests,
		ClaimBoundary:      "pinned geth catchUp using real snap.Peer RequestAccessLists, tracker, p2p.Send/ReadMsg, SNAP/2 AccessLists packet RLP encode/decode and HandleMessage dispatch, full BAL authenticity/hash verification in both arms, production catch-up apply/status persistence, Pebble writes and final durability sync; p2p.MsgPipe is in-memory and excludes TCP/RLPx encryption and real network latency; phaseDownload excludes state-trie root replay",
	}
	blob, err := json.MarshalIndent(obs, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	blob = append(blob, byte(10))
	if err := os.WriteFile(resultPath, blob, 0o644); err != nil {
		t.Fatal(err)
	}
	t.Logf("CRYSTAL_V20 arm=%s trial=%d records=%d wire_requests=%d catchup_ns=%d durable_ns=%d digest=%s target=%s", arm, trial, len(measureRaws), requests, catchUpNS, durableNS, digest, target.Hash().Hex())
	t.Logf("ETHEREUM_CRYSTAL_V20_SNAP2_MSGPIPE=PASS arm=%s trial=%d", arm, trial)
}
