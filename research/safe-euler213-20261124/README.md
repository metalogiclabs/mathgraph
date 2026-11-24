# SAFE Euler213 audit — bounded native countermodel

Source: sedaro/safe at f9ed45abc53b28afb7e287e605173275f7fe92c9.
Terminal form: FINITE_COUNTERMODEL for the standard 2-1-3 interpretation.
Owner-intended frame and intrinsic/extrinsic convention: UNKNOWN.

The function named euler213_to_quaternion(pitch, roll, yaw) returns (x,y,z,w).
The audit compares both standard Y-X-Z orders and their inverse matrices;
identity/single-axis controls, unit norm and quaternion sign aliases are checked.
An independent elementary-matrix oracle is cross-checked against SciPy.
Symbolic coefficient expansion identifies qx(roll) * qy(pitch) * qz(yaw).

Three native arms: original, two-sign intrinsic213 diagnostic candidate, original restored.
Each arm preserves 8/8 author tests and 19 identity/single-axis controls.
The selected 216 mixed cases must disagree with the 213 family in original and
withdrawal, and agree with intrinsic213 in the candidate. Failed regression
logs are retained. The successful audit run means these declared outcomes
were reproduced, not that the original source passed its named contract.

Witness: pitch 23 degrees, roll -31 degrees, yaw 47 degrees. The original result
differs from intrinsic213 by approximately 12.216 degrees of orientation.
Tolerance is 1e-12 maximum matrix-entry error. The original mixed cases match
intrinsic XYZ (1-2-3), with arguments ordered (roll,pitch,yaw).

The diagnostic candidate changes only the signs of the sr*sp*sy term in w
and sr*sp*cy term in z. It is not an owner-approved repair. If 123 is intended,
renaming and documenting the function is a separate possible resolution.
The original production bytes and original CSV are restored byte-for-byte.

Scope: public safe-time helper and native unit tests only, not full SAFE,
deployed autonomy, or mission effects. No issue has been submitted to Sedaro.
The existing nonzero quaternion fixture uses roll 0.07 degrees, xyz tolerance
1e-4, and omits w; both original and candidate pass it.

Replay: Rust 1.94.1; Python numpy==2.3.5 scipy==1.17.0 sympy==1.14.0.
Run audit.py with a clean pinned SAFE checkout and an output directory:
python research/safe-euler213-20261124/audit.py /path/to/safe /path/to/receipts

Primary convention references:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.from_euler.html
https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/eul2m_c.html
SPICE uses passive coordinate rotations; the audit does not silently mix signs.

Reuse candidate: identity/single-axis tests cannot distinguish noncommuting
rotation orders. A mixed-axis observation separates these alternatives.
Prospective detection advantage over conventional review remains untested.
