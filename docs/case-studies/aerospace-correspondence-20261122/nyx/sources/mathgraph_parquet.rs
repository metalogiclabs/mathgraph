//! MathGraph distinction-preservation probe for a pinned Nyx source tree.
//! The production code under test is unmodified.  The test is copied into
//! nyx-core/tests/mathgraph_parquet.rs in the CI workspace.

use anise::constants::frames::{EARTH_J2000, IAU_EARTH_FRAME};
use anise::prelude::{Frame, Orbit};
use anise::prelude::Almanac;
use nyx_space::dynamics::{OrbitalDynamics, SpacecraftDynamics};
use nyx_space::io::ExportCfg;
use nyx_space::md::prelude::Traj;
use nyx_space::propagators::{IntegratorOptions, Propagator};
use nyx_space::time::{Epoch, TimeUnits};
use nyx_space::Spacecraft;
use std::path::PathBuf;
use std::sync::Arc;

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

fn real_almanac() -> Arc<Almanac> {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../data/01_planetary");
    Arc::new(
        Almanac::new(&dir.join("pck08.pca").to_string_lossy())
            .unwrap()
            .load(&dir.join("earth_longterm_000101_251211_250915.bpc").to_string_lossy())
            .unwrap()
            .load(&dir.join("earth_latest_high_prec.bpc").to_string_lossy())
            .unwrap()
            .load(&dir.join("de440s.bsp").to_string_lossy())
            .unwrap(),
    )
}

fn run_nyx_propagation(almanac: Arc<Almanac>, start_fixed: bool) -> Traj<Spacecraft> {
    let epoch = Epoch::from_gregorian_utc_at_noon(2025, 1, 1);
    let inertial = almanac.frame_info(EARTH_J2000).unwrap();
    let inertial_start = Orbit::new(7000.0, 400.0, 100.0, 0.0, 7.6, 0.1, epoch, inertial);
    let start_orbit = if start_fixed {
        almanac.transform_to(inertial_start, IAU_EARTH_FRAME, None).unwrap()
    } else {
        inertial_start
    };

    let mut options = IntegratorOptions::with_fixed_step_s(15.0);
    options.integration_frame = Some(inertial);
    let setup = Propagator::rk89(
        SpacecraftDynamics::new(OrbitalDynamics::two_body()),
        options,
    );
    let (_end, traj) = setup
        .with(Spacecraft::from(start_orbit), almanac)
        .for_duration_with_traj(90.seconds())
        .unwrap();
    traj
}

#[test]
fn mathgraph_parquet_real_inertial_propagation_control() {
    let almanac = real_almanac();
    let source = run_nyx_propagation(almanac.clone(), false);
    assert!(source.states.len() >= 3);
    assert!(source.states.iter().all(|state| state.orbit.frame.orientation_id == 1));
    let recovered = round_trip(&source, "propagation-inertial")
        .expect("homogeneous real propagation must export/import");
    assert_eq!(source.states.len(), recovered.states.len());
    let idx = 1;
    let common = almanac.frame_info(EARTH_J2000).unwrap();
    let src = almanac.transform_to(source.states[idx].orbit, common, None).unwrap();
    let got = almanac.transform_to(recovered.states[idx].orbit, common, None).unwrap();
    let distance_km = (src.radius_km - got.radius_km).norm();
    let velocity_km_s = (src.velocity_km_s - got.velocity_km_s).norm();
    println!("MG_REAL_UNIFORM_RESIDUAL_KM={distance_km:.12} MG_REAL_UNIFORM_RESIDUAL_KMS={velocity_km_s:.12}");
    assert!(distance_km < 1.0e-6, "real homogeneous trajectory position changed");
    assert!(velocity_km_s < 1.0e-9, "real homogeneous trajectory velocity changed");
    println!("MG_REAL_PROPAGATION_CONTROL_PASSED");
}

#[test]
fn mathgraph_parquet_real_mixed_propagation_preserves_physics_or_rejects() {
    let almanac = real_almanac();
    let source = run_nyx_propagation(almanac.clone(), true);
    assert!(source.states.len() >= 3);
    assert_eq!(source.states[0].orbit.frame.orientation_id, 399);
    assert_eq!(source.states[1].orbit.frame.orientation_id, 1);

    let recovered = match round_trip(&source, "propagation-mixed") {
        Ok(traj) => traj,
        Err(error) => {
            println!("MG_PHYSICAL_EXPORT_REJECTED_SAFELY: {error}");
            return;
        }
    };
    let idx = 1;
    assert_eq!(source.states.len(), recovered.states.len());
    let common = almanac.frame_info(EARTH_J2000).unwrap();
    let src = almanac.transform_to(source.states[idx].orbit, common, None).unwrap();
    let got = almanac.transform_to(recovered.states[idx].orbit, common, None).unwrap();
    let distance_km = (src.radius_km - got.radius_km).norm();
    let velocity_km_s = (src.velocity_km_s - got.velocity_km_s).norm();
    println!("MG_REAL_MIXED_RESIDUAL_KM={distance_km:.12} MG_REAL_MIXED_RESIDUAL_KMS={velocity_km_s:.12}");
    assert!(
        distance_km < 1.0e-6 && velocity_km_s < 1.0e-9,
        "MG_PHYSICAL_WRONG_FRAME: Parquet reinterpreted a propagated state in the wrong orientation"
    );
    println!("MG_PHYSICAL_FRAME_FIDELITY_PRESERVED");
}

#[test]
fn mathgraph_parquet_filtered_rows_have_their_own_frame() {
    // This is a homogeneous output selection from a heterogeneous input.
    // The original first row must not dictate the exported rows' frame.
    let source = trajectory(IAU_EARTH_FRAME);
    let selected_epoch = source.states[1].orbit.epoch;
    let cfg = ExportCfg::builder()
        .start_epoch(selected_epoch)
        .end_epoch(selected_epoch)
        .step(30.seconds())
        .build();
    let path = temp_parquet("filtered-second-frame");
    let exported = source.to_parquet(&path, cfg).unwrap();
    let recovered = Traj::<Spacecraft>::from_parquet(&exported).unwrap();
    let _ = std::fs::remove_file(&exported);
    assert_eq!(recovered.states.len(), 1);
    assert_eq!(
        recovered.states[0].orbit.frame,
        source.states[1].orbit.frame,
        "MG_FILTERED_FRAME_WRONG: metadata describes a row not in the export"
    );
    println!("MG_FILTERED_FRAME_CONTROL_PASSED");
}
