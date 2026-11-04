//! External, source-pinned Brahe PR #576 research fixture.
//!
//! Injected into a temporary checkout only; this is not a proposed
//! modification to the Brahe repository.
use brahe::ccsds::CCSDSOrbitRelativeFrame;
use brahe::constants::{AngleFormat, WGS84_A};
use brahe::coordinates::position_geodetic_to_ecef;
use brahe::relative_motion::{
    omega_enz, omega_sez, rotation_ecef_to_enz, rotation_ecef_to_sez,
    state_ecef_to_enz, state_ecef_to_sez, state_enz_to_ecef,
};
use brahe::SVector6;
use nalgebra::Vector3;
use serial_test::parallel;

fn near(actual: f64, expected: f64, tolerance: f64, label: &str) {
    assert!(
        (actual - expected).abs() <= tolerance,
        "{label}: observed {actual:.15e}, expected {expected:.15e}, tolerance {tolerance:.3e}"
    );
}

#[test]
#[parallel]
fn test_enz_explicit_equator_axes_and_state() {
    // Independent geometric oracle at longitude=latitude=zero:
    // E=(0,1,0), N=(0,0,1), Z=(1,0,0).
    let site = SVector6::new(WGS84_A, 0.0, 0.0, 0.0, 0.0, 0.0);
    let rotation = rotation_ecef_to_enz(site);
    let expected = [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]];
    for row in 0..3 {
        for col in 0..3 {
            near(rotation[(row, col)], expected[row][col], 1e-12, "equator basis");
        }
    }
    let target = SVector6::new(WGS84_A + 300.0, 100.0, 200.0, 30.0, 10.0, 20.0);
    let relative = state_ecef_to_enz(site, target);
    let expected_relative = [100.0, 200.0, 300.0, 10.0, 20.0, 30.0];
    for i in 0..6 {
        near(relative[i], expected_relative[i], 1e-9, "equator relative state");
    }
    let restored = state_enz_to_ecef(site, relative);
    for i in 0..6 {
        near(restored[i], target[i], 1e-8, "equator inverse state");
    }
}

#[test]
#[parallel]
fn test_enz_numerical_geodetic_basis_and_signed_sez_motion() {
    // No exact poles: longitude has a defined local frame in every case.
    let cases: [(f64, f64, f64); 7] = [
        (30.0, 45.0, 500.0),
        (-170.0, -72.0, 1200.0),
        (0.0, 0.0, 0.0),
        (89.0, 23.0, 35000.0),
        (179.0, 80.0, 10.0),
        (-89.7, -3.5, 0.0),
        (10.0, 89.2, 500.0),
    ];
    for (case_index, (lon_deg, lat_deg, altitude)) in cases.into_iter().enumerate() {
        let position = position_geodetic_to_ecef(
            Vector3::new(lon_deg, lat_deg, altitude),
            AngleFormat::Degrees,
        )
        .unwrap();
        let site = SVector6::new(
            position[0], position[1], position[2],
            13.0 + case_index as f64, -21.0, 8.0,
        );
        let target = SVector6::new(
            site[0] + 1100.0,
            site[1] - 2700.0,
            site[2] + 3300.0,
            site[3] + 4.0,
            site[4] - 6.0,
            site[5] + 11.0,
        );
        let lon = lon_deg.to_radians();
        let lat = lat_deg.to_radians();
        let (slon, clon) = lon.sin_cos();
        let (slat, clat) = lat.sin_cos();
        // Independent ENZ projection from local east/north and WGS84
        // geodetic zenith, avoiding the SEZ implementation as oracle.
        let expected = [
            [-slon, clon, 0.0],
            [-slat * clon, -slat * slon, clat],
            [clat * clon, clat * slon, slat],
        ];
        let enz = rotation_ecef_to_enz(site);
        let sez = rotation_ecef_to_sez(site);
        for row in 0..3 {
            for col in 0..3 {
                near(enz[(row, col)], expected[row][col], 5e-12, "geodetic basis");
                let signed = match row {
                    0 => sez[(1, col)],
                    1 => -sez[(0, col)],
                    _ => sez[(2, col)],
                };
                near(enz[(row, col)], signed, 1e-12, "SEZ axis permutation");
            }
        }
        let omega_en = omega_enz(site);
        let omega_sz = omega_sez(site);
        for (index, signed) in [omega_sz[1], -omega_sz[0], omega_sz[2]]
            .into_iter().enumerate()
        {
            near(omega_en[index], signed, 5e-15, "SEZ angular-rate permutation");
        }
        let rel_en = state_ecef_to_enz(site, target);
        let rel_sz = state_ecef_to_sez(site, target);
        for (index, signed) in [
            rel_sz[1], -rel_sz[0], rel_sz[2],
            rel_sz[4], -rel_sz[3], rel_sz[5],
        ]
        .into_iter().enumerate()
        {
            near(rel_en[index], signed, 1e-8, "SEZ relative-state permutation");
        }
        let round_trip = state_enz_to_ecef(site, rel_en);
        for i in 0..3 {
            near(round_trip[i], target[i], 1e-7, "inverse position");
            near(round_trip[i + 3], target[i + 3], 1e-9, "inverse velocity");
        }
    }
}

#[test]
#[parallel]
fn test_ccsds_enu_aliases_canonicalize_to_enz() {
    let cases = [
        ("ENU_ROTATING", CCSDSOrbitRelativeFrame::ENZRotating, "ENZ_ROTATING"),
        ("enu_rotating", CCSDSOrbitRelativeFrame::ENZRotating, "ENZ_ROTATING"),
        (" ENZ_ROTATING ", CCSDSOrbitRelativeFrame::ENZRotating, "ENZ_ROTATING"),
        ("ENU_INERTIAL", CCSDSOrbitRelativeFrame::ENZInertial, "ENZ_INERTIAL"),
        ("enz_inertial", CCSDSOrbitRelativeFrame::ENZInertial, "ENZ_INERTIAL"),
    ];
    for (source, expected_variant, canonical) in cases {
        let actual = CCSDSOrbitRelativeFrame::parse(source);
        assert_eq!(actual, expected_variant);
        assert_eq!(actual.to_string(), canonical);
    }
    let unknown = CCSDSOrbitRelativeFrame::parse(" MY_CUSTOM_ENU ");
    assert_eq!(unknown, CCSDSOrbitRelativeFrame::Other("MY_CUSTOM_ENU".into()));
    assert_eq!(unknown.to_string(), "MY_CUSTOM_ENU");
}
