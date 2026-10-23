# EFRD original-source discovery — freeze before reading new recordings

Source-author repository: https://github.com/shicy17/MSA at commit `f8a89a0eb842e5f82b982493e636c200f8bf9dee`; dataset: https://drive.google.com/drive/folders/1tOlC-aOPL0YmYcQKetyEFWWRYONG8kF0.

EFRD publishes 8 real DAVIS346/IMU sequences. Only `mahjong-1` and `mahjong-2` advertise external motion-capture ground truth. The other six reference an IMU-derived `/imu/gt` and are **not** eligible to prove correction of gyroscope drift against independent truth. None is documented as repeated continuously spinning multi-turn yaw. This source-listing experiment **cannot** promote any recording to navigation validation.

Protocol frozen BEFORE inspecting folder listing: list original shared Google Drive object identities and names without downloading; enumerate both possible mocap sequences before selecting a bag. Protect against ambiguous/path-alias/unknown names. The output is a source manifest only; no ground truth has been inspected, and file names are not sufficient evidence of event, IMU, or pose contents. Only once the actual bag is acquired, hashed and raw ROS messages replayed, perform fixed-axis reference angular-excursion and uninterrupted-sweep admission. Avoid selecting direction or axis post hoc to fabricate revolutions. If both reference signals and camera align, use the independent motion-capture pose for evaluation only.

Consequence: 2+ contiguous angular turns and independent ground-truth yaw must be QUALIFIED before any post-revolution relocalization claim. Missing data is UNKNOWN rather than a positive result. Preserve all listed negatives and don't modify Joshua's repos.
