# EvSLAM real FPV drone original-reference turn admission (retrospective source discovery)

Research objective: identify true consecutive multi-revolution pose trajectories before downloading any event-camera/IMU bag. This is NOT a visual compass estimator test. Original human-visible program aims at one-column self-built map after first 360°, then corrects drift on later turns, with ambiguity/permission handling. Preserve all prior RobotEvt, ECRot and EFRD negative results.

Upstream dataset: [EvSLAM](https://github.com/NAIL-HNU/EvSLAM_Dataset) commit f116a9fe305f3ad8b1a379e1bb52becfc87654dc. Publisher describes dual DVXplorer event cameras (left event topic, left IMU), RGB and stereo frame cameras, and a motion-capture system. Its evaluation GT rows are timestamp tx ty tz qx qy qz qw vx vy vz. The GT is only dataset reference authority, not an independently calibrated original camera-to-body axis, exposure synchronization or flight correction warrant. These GT files were inspected during source discovery, so any qualification is retrospective, NOT blind.

Original source Git blob IDs:
- drone_rot_norm_gt.txt: 809d83df4063376d0ee50f62095131e1d8940c00
- drone_rot_norm_ref_time.txt: 34a8c16d23a4418a0f206fe615898276bc61008d
- drone_rot_fast_gt.txt: 47a1bd5b54c0843d2535af42ebff0529950a5a6f
- drone_rot_fast_ref_time.txt: b6c74a7e9167cf8750bc3f33b277b23a76181f21

Predeclare **ALL x/y/z body axes**. Compute incremental body frame SO(3) log vectors from q_i^-1 * q_i+1; independent manual quaternion product and SciPy rotation agree or fail. Require GT unit norm +/-0.001, strict monotone time, maximum geodesic step less than 90 degrees and max pose timestamp spacing <=0.25 seconds. A finite sample angle below 90 degrees is a necessary sampling test, NOT an independent velocity bound proving no hidden rotations between samples. Record every projected axis's net, absolute path and longest uninterrupted signed streak with 0.2-degree reversal tolerance. A recorded body-Y trajectory qualifies a **candidate** for 2+ turns only if longest streak >=720 degrees and projection accounts for >=90% of total 3D angular travel. This threshold is a declared admissibility filter, not a demonstration of a physical single-propeller drone-axis match. Record all translation and max displacement as scene-change risk.

Ground-truth reference times are independently source-authenticated and should cover nearly all GT poses within 1ms. Counts and actual turn-end pose timestamps are recorded. No visual-map initial panorama, camera events, IMU correction or physical line-camera test is run in this qualification. These next stages require original raw ROS bag authentication; the downloadable author Drive IDs are frozen for norm 1NNUZgkzpyR321AFeI1j5Uv2DKV8E_W3u and fast 1t4viDrRV40_uOS3Tfh9-jMbGKgHorTI1. Do not edit Joshua's external repositories. Any source withdrawal must revoke an inferred result.
