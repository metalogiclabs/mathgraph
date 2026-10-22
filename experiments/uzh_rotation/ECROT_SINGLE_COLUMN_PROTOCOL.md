# ECRot original-camera one-column experiment (frozen v1)

## Scientific question

Can a fixed 1-pixel-wide geometric column from a real spinning event camera
build a first-revolution angular reference, later revisit it, and determine
when a seemingly high-confidence match is actually ambiguous?

Source: [TU Berlin ECRot](https://github.com/tub-rip/ECRot); original motorized
ROS1 `events.bag` at the Drive IDs and SHA-256 recorded in
[`ecrot_sources.json`](ecrot_sources.json). Dataset descriptions say *single*
360-degree rotations, **not** repeated revolutions. Neither heading truth nor
a genuine physical line-scan camera is supplied.

## Predeclared methods

1. Verify SHA-256 of the entire original bag before processing. Cross-check
   the first ROS1 EventArray decoded with independent `rosbags` deserialization.
2. Use original IMU `angular_velocity.y`, header timestamp and trapezoidal
   integration **without fitting bias to any ground truth**. It is only the
   map-building angular coordinate, never heading ground truth.
3. Keep original events at physical column `x=320` of the 640×480 camera,
   retaining 24 vertical bins and the polarity. Nothing else from any image
   column is used to form the scene descriptor.
4. Bin into 64 angles. Freeze the histogram map exactly when integrated gyro
   first reaches `2*pi`; all subsequent observations are held out from map
   learning. Observations outside IMU timestamp coverage are dropped.
5. Baseline: unrestricted global cosine-similarity matched-filter retrieval.
   The gyro label **never** enters candidate selection or confidence gating.
6. Conservative conventional gate: require at least 50 events in the query,
   at least two populated candidate map sectors, `cosine >= 0.75`, and best
   minus runner-up cosine `>= 0.08`. A non-unique best match is UNKNOWN. This
   baseline has the same event descriptions as any evidence-aware method.
7. No navigation correction is authorized: even a UNIQUE visual candidate
   would lack independent heading truth, a drift bound and replicated
   full-revolution evidence. Store negative results as explicit UNKNOWN.

Settings were frozen after inspecting one **development** scene,
Charlottenburg Palace, and before obtaining the independent
**Brandenburg Gate holdout**. We must not claim a blind development result.

## Development observation: original Charlottenburg Palace recording

- Raw camera events: 97,399,772 in 252 packets; original IMU: 6,629 samples.
- Single center-column events: 159,175 (159,172 within recorded IMU times).
- First-turn map: 157,084 events, all 64 bins covered, min 749/bin.
- Integrated y-axis gyroscope rotation: 1.015515696844135 turns.
- Remaining ~5.6-degree partial revisit: 2,088 events, one angular sector.
- Unrestricted best match: sector 0, cosine `0.9417090`, agreeing with
  gyro-derived sector *as a diagnostic only*.
- Second-best match: cosine `0.9357135`, gap just `0.0059955`;
  seven sectors remain within the fixed ambiguity margin.
- Final decision: **UNKNOWN; withhold heading correction**.

Although the highest-scoring sector agrees with the gyro, the evidence does
not distinguish its nearby rivals, let alone bound true heading error.

## Limitations / deliberate negative controls

- A lone populated first-turn map sector must not manufacture a false score
  margin by comparing against empty sectors.
- Identical environmental pattern signatures remain UNKNOWN.
- Missing observation or timestamps outside IMU coverage cannot authorize a
  heading correction or generate fabricated events.
- The ROS bag has **not** demonstrated two continuous full turns, occlusion
  recovery, bias correction, real physical line-camera operation, motor-control
  integration or autonomous flight.
- The gate is a conventional, equally informed robust baseline. A MathGraph
  superiority claim is **UNKNOWN** pending an actual separating-observation
  policy and independent post-policy acquisitions.

## Reproduction

Install pinned Python packages: `numpy==2.1.3`, `rosbags==0.11.9` and
`gdown==5.2.0`. Acquire the original development file by its pinned Drive
ID; do not substitute compressed or converted event streams. Run:

```sh
python -m unittest discover -s experiments/uzh_rotation -p 'test_ecrot_line_revisit.py' -v
python experiments/uzh_rotation/audit_ecrot_line_revisit.py \
  --bag ECRot_Charlottenburg_events.bag \
  --sha256 e851b34a76b8b566beeeb24d9d3208de81c8a7d81bc19c02c07966914cb2854e \
  --output ecrot_column_report.json
```

GitHub Actions reproduces the source checksum, event counts, negative
controls and ambiguity gate independently; CI artifact retains only compact
statistics, not redistributable sensor bytes.
