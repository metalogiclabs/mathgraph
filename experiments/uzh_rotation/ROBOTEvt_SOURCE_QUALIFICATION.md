# RobotEvt original-source continuous-spin qualification (2026-10-23)

## Objective and authority boundary

Assess whether original RobotEvt DAVIS240C/UR5 PureRot trajectories can provide
**repeated complete revolutions** for a continuously spinning, single-column
visual compass. The six original ZIP archives are from the dataset authors'
public Google Drive folder linked by the
[RobotEvt repository](https://github.com/liudaqikk/RobotEvt).
Their exact archive and extracted ground-truth SHA256 values and Drive file IDs
are pinned in `robotevt_sources.json`. Do not commit or redistribute the raw
rosbags or original files; the pipeline re-acquires them from the authors.

This is only **ground-truth trajectory admission**. No ROS images/events/IMU
have yet been decoded, camera-to-arm extrinsics have not been qualified, and
there are no visual-compass accuracy or hardware claims from these files.

## The consequential distinction

The previously added `qualify_robotevt.py` integrates 3D path length and
unwrapped Euler yaw. The independent `audit_robotevt_sweep.py` instead uses
relative rotation matrices and integrates planar signed pairwise increments,
checking spatial axis alignment, sample-step aliases, direction reversals and
the *longest uninterrupted directional streak*. The two yaw-excursion methods
agree within 0.0001 turn, conditional on the supplied UR5 ground truth.

For a continuous-spin 2-turn admission, require an observed 720-degree
directional streak, a mostly z-axis path (at least 95%), pairwise angular steps
strictly below 90 degrees, and valid monotonically timestamped SO(3) poses.
The step threshold is **not a physical bound on unseen intermediate motion**;
an independently bounded max angular velocity is still needed to exclude
multi-turn aliasing between observations. Thus even `ADMITTED` would be a
candidate for further acquisition, not full proof of sensor observability.

## Six originals: local source-authenticated exploratory results

| Original | Absolute 3D path (turns) | Yaw range (turns) | Longest streak (turns) | Qualification |
|---|---:|---:|---:|---|
| PureRot_Fast_Off | 6.115 | 0.432 | 0.425 | REJECTED |
| PureRot_Fast_On | 6.191 | 0.432 | 0.426 | REJECTED |
| PureRot_Mid_Off | 4.590 | 0.432 | 0.420 | REJECTED |
| PureRot_Mid_On | 4.314 | 0.354 | 0.349 | REJECTED |
| PureRot_Slow_Off | 3.134 | 0.432 | 0.404 | REJECTED |
| PureRot_Slow_On | 3.058 | 0.432 | 0.404 | REJECTED |

The recordings repeatedly reverse direction through a limited sector;
their accumulated 3D travel is **not** repeated full-revolution panorama
coverage. `0/6` qualify for the intended full-spin benchmark. This is a real
negative result, not a failure of the visual compass itself.

## Reproduction and falsification

`python -m unittest discover -s experiments/uzh_rotation -p 'test_robotevt*.py' -v`

Synthetic positive controls show genuine three-turn admission, plus negative
controls for repeated sub-turn oscillation, one turn, orthogonal-axis rotation,
undersampling, malformed poses, source archive tampering, member tampering and
incorrectly declared admission. The `robotevt-rotation-qualification.yml`
GitHub Action independently downloads all six author archives, verifies both
archive/member SHA256 digests, replays both angle calculations and persists only
compact JSON artifacts. Exact CI run link and status must be added once observed.

## Residual and reuse

- These recordings **can** test real repeated *partial-sector* observations,
  matching ambiguity and blackout recovery once the DAVIS image/event/IMU
  timing and sensor pose alignment are decoded and verified. They cannot test
  a self-built **360-degree first-turn** panorama.
- Find a different genuine multiple-revolution camera+IMU dataset or capture a
  safe mechanical turntable sequence with a one-column sensor.
- Never promote path integral length to directional full-turn coverage without
  a separating angular excursion/streak witness.
