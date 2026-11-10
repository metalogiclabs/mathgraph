//! MathGraph distinction-preservation probe for a pinned Nyx source tree.
//! The production code under test is unmodified.  The test is copied into
//! nyx-core/tests/mathgraph_parquet.rs in the CI workspace.

use anise::constants::frames::{EARTH_J2000, IAU_EARTH_FRAME};
use anise::prelude::{Frame, Orbit};
use nyx_space::io::ExportCfg;
use nyx_space::md::prelude::Traj;
use nyx_space::time::{Epoch, TimeUnits};
use nyx_space::Spacecraft;
use std::path::PathBuf;

fn spacecraft(epoch: Epoch, frame: Frame) -> Spacecraft {
    Spacecraft::from(Orbit::new(
        7000.0, 400.0, 100.0, 0.0, 7.6, 0.1, epoch, frame,
    ))
}

fn trajectory(second_frame: Frame) -> Traj<Spacecraft> {
    let epoch = Epoch::from_gregorian_utc_at_noon(2026, 11, 11);
    Traj {
        name: Some("mathgraph-frame-distinction".to_owned()),
        states: vec![
            spacecraft(epoch, EARTH_J2000),
            spacecraft(epoch + 30.seconds(), second_frame),
        ],
    }
}

fn temp_parquet(suffix: &str) -> PathBuf {
    std::env::temp_dir().join(format!(
        "mathgraph-nyx-parquet-{}-{suffix}.parquet",
        std::process::id()
    ))
}

fn round_trip(source: &Traj<Spacecraft>, suffix: &str) -> Result<Traj<Spacecraft>, String> {
    let requested = temp_parquet(suffix);
    let exported = source
        .to_parquet(&requested, ExportCfg::default())
        .map_err(|error| format!("export rejected: {error}"))?;
    let recovered = Traj::<Spacecraft>::from_parquet(&exported)
        .map_err(|error| format!("import rejected: {error}"));
    let _ = std::fs::remove_file(&exported);
    recovered
}

#[test]
fn mathgraph_parquet_uniform_frame_control() {
    let source = trajectory(EARTH_J2000);
    let recovered = round_trip(&source, "uniform").expect("valid homogeneous round-trip");
    assert_eq!(recovered.states.len(), 2);
    for (before, after) in source.states.iter().zip(recovered.states.iter()) {
        assert_eq!(before.orbit.frame, after.orbit.frame);
        assert_eq!(before.orbit.radius_km, after.orbit.radius_km);
        assert_eq!(before.orbit.velocity_km_s, after.orbit.velocity_km_s);
    }
    println!("MG_UNIFORM_CONTROL_PASSED");
}

#[test]
fn mathgraph_parquet_distinct_frame_inputs_remain_distinct_or_reject() {
    // Same epochs and Cartesian numbers, but the second state's declared frame
    // differs. They are not interchangeable physical states.
    let uniform = trajectory(EARTH_J2000);
    let mixed = trajectory(IAU_EARTH_FRAME);
    assert_ne!(uniform.states[1].orbit.frame, mixed.states[1].orbit.frame);

    // Explicit rejection is safe. Silent acceptance must preserve the frame.
    let recovered_uniform = match round_trip(&uniform, "comparison-uniform") {
        Ok(result) => result,
        Err(error) => panic!("homogeneous positive control rejected: {error}"),
    };
    let recovered_mixed = match round_trip(&mixed, "comparison-mixed") {
        Ok(result) => result,
        Err(error) => {
            println!("MG_MIXED_FRAME_REJECTED_SAFELY: {error}");
            return;
        }
    };
    assert_eq!(recovered_uniform.states.len(), 2);
    assert_eq!(recovered_mixed.states.len(), 2);

    let uniform_frame = recovered_uniform.states[1].orbit.frame;
    let mixed_frame = recovered_mixed.states[1].orbit.frame;
    println!(
        "MG_OBSERVATION source_uniform={:?} source_mixed={:?} recovered_uniform={:?} recovered_mixed={:?}",
        uniform.states[1].orbit.frame,
        mixed.states[1].orbit.frame,
        uniform_frame,
        mixed_frame,
    );
    assert_ne!(
        uniform_frame,
        mixed_frame,
        "MG_DISTINCTION_COLLAPSE: distinct source frames silently became the same imported frame"
    );
    assert_eq!(mixed_frame, mixed.states[1].orbit.frame);
    println!("MG_MIXED_FRAME_DISTINCTION_PRESERVED");
}
