//go:build balexperiment

// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// Test-only successor to the independently observed V20 late-admission race.
// It exercises two genuine JWT Engine V4 RPC clients against the same Geth
// service and requires a later invalidating request to supersede an older
// verified-but-paused speculative witness admission.
package catalyst

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/beacon/engine"
	"github.com/ethereum/go-ethereum/common"
)

func TestBALV21ConcurrentStaleFCUDoesNotReinstatePending(t *testing.T) {
	entered := make(chan struct{})
	release := make(chan struct{})
	var releaseOnce sync.Once
	defer releaseOnce.Do(func() { close(release) })
	var enteredOnce sync.Once
	h := openBALV20Harness(t, func() {
		enteredOnce.Do(func() { close(entered) })
		<-release
	})
	if got := h.target.BlockChain().ExperimentalPendingBALFinalityHash(); got != (common.Hash{}) {
		t.Fatalf("UNKNOWN/setup: pending witness nonempty before both FCUs: %s", got.Hex())
	}
	type response struct {
		reply engine.ForkChoiceResponse
		err   error
	}
	firstDone := make(chan response, 1)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		var reply engine.ForkChoiceResponse
		err := h.first.CallContext(ctx, &reply, "engine_forkchoiceUpdatedV4", h.validFCU(), nil, nil)
		firstDone <- response{reply: reply, err: err}
	}()
	select {
	case <-entered:
		t.Log("MG_BAL_V21_ORDER older_authenticated_fcu_verified_paused_before_admission")
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/setup: older FCU did not reach the native ancestry-qualified admission point")
	}
	if got := h.target.BlockChain().ExperimentalPendingBALFinalityHash(); got != (common.Hash{}) {
		t.Fatalf("UNKNOWN/setup: older FCU admitted while barrier was closed: %s", got.Hex())
	}
	bad, err := callBALV20(t, h.second, h.invalidatingFCU())
	if err != nil || bad.PayloadStatus.Status != engine.INVALID {
		t.Fatalf("UNKNOWN/setup: newer authenticated invalidation control changed: %+v err=%v", bad, err)
	}
	if got := h.target.BlockChain().ExperimentalPendingBALFinalityHash(); got != (common.Hash{}) {
		t.Fatalf("UNKNOWN/setup: newer FCU left pending authority before older resumed: %s", got.Hex())
	}
	t.Log("MG_BAL_V21_ORDER newer_authenticated_invalid_fcu_completed_pending_empty")
	releaseOnce.Do(func() { close(release) })
	select {
	case first := <-firstDone:
		if first.err != nil {
			t.Fatalf("UNKNOWN/setup: older FCU failed to complete: %+v err=%v", first.reply, first.err)
		}
	case <-time.After(20 * time.Second):
		t.Fatal("UNKNOWN/setup: older FCU never completed after release")
	}
	if got := h.target.BlockChain().ExperimentalPendingBALFinalityHash(); got != (common.Hash{}) {
		t.Logf("MG_BAL_V21_RED_STALE_REINSTALL pending=%s older_final=%s admissions=%d", got.Hex(), h.frozen.Hash().Hex(), h.admissions.Load())
		t.Fatalf("stale older FCU restored pending witness after newer FCU completed")
	}
	if got := h.admissions.Load(); got != 0 {
		t.Fatalf("a stale older FCU fired the pending-authority admission callback: %d", got)
	}
	t.Log("MG_BAL_V21_GENERATION_FENCE_PASS pending_empty_admissions_zero_after_stale_fcu")
}
