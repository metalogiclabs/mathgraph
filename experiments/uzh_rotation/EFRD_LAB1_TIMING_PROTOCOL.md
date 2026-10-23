# EFRD lab1: original mocap vs camera IMU timing (development)

**Scope:** Original source-pinned EFRD lab1.bag SHA256
`2fac73513203739df46fb085a4e67f8f41e7c2aa9ebfdd115d97b34a9929e484`.
The 2.96 GB source and 12,228 independent mocap poses were qualified by
[Actions #39878041321](https://github.com/metalogiclabs/mathgraph/actions/runs/39878041321)
and [Actions #39878546818](https://github.com/metalogiclabs/mathgraph/actions/runs/39878546818).
It failed continuous two-revolution world-Z yaw admission. The whole-bag ROS
time-span was anomalous; use original message header timestamps only.

**Question:** Does one fixed, source-identical IMU-to-mocap temporal calibration
learned in the first chronological half improve rate correlation in the
second half over a fully informed zero-offset baseline?

**Declared before reading this source timing result:** independent quaternion
increments give SO(3) geodesic angular speed, compared with the magnitude of
uncalibrated three-axis angular velocity. Compare BOTH original `/dvs/imu`
(camera IMU) and `/imu/data` (external IMU), and retain failures. Neither
sensor is selected based on the score. No event-camera columns are decoded.
Require monotone nanosecond source-header times, valid unit mocap quaternion,
finite sensor rates, 10 seconds overlap, at least 150 observations in each
split. Subtract shared integer nanosecond epoch before interpolation. Fit
only the first half, lag grid [-0.200, 0.200] seconds at 0.005 steps,
deterministically breaking ties toward zero. Compare the frozen selected
lag with zero lag on the second chronological half. This is **within the
already-exposed lab1 recording**, not unseen-scene or external validation.
The same fitting procedure is a conventional comparator; there is no unique
MathGraph algorithm or advantage claimed.

**Critical authority boundary:** independent mocap measures reference angular
speed only for an offline timing diagnostic. Correlation cannot establish an
absolute heading error bound, sensor clock offset uniqueness, physical camera
alignment, or successful visual relocalization. Original gyro bias and timestamp
inconsistency can survive correlation. Any insufficient or conflicting evidence
is UNKNOWN, and no navigation corrections are permitted. Lab2 source values
remain unopened by this experiment; its separately pinned source-identity
workflow is not a pose/matching qualification.
