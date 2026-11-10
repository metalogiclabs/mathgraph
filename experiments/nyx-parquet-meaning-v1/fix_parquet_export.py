"""Apply the minimal fail-closed frame-fidelity correction to a pinned Nyx checkout.

Expected precondition: unmodified upstream nyx-core/src/md/trajectory/traj.rs.
This is used for the bounded RED/GREEN research replay; the upstream PR should
carry the resulting native Rust diff, not depend on this script.
"""

from pathlib import Path
import sys


OLD = "        let frame = self.states[0].frame();\n        let more_meta ="
NEW = """        // Parquet has one Frame metadata value for the entire exported table.
        // It must describe the states actually selected for export, not an
        // excluded earlier state. Mixed-frame tables cannot be represented.
        let frame = states
            .first()
            .ok_or_else(|| InputOutputError::Inconsistency {
                msg: "Cannot export an empty trajectory to Parquet".to_string(),
            })?
            .frame();

        if let Some(state) = states.iter().find(|state| state.frame() != frame) {
            return Err(InputOutputError::Inconsistency {
                msg: format!(
                    "Cannot export mixed-frame trajectory to Parquet: first frame {frame}, frame {} at {}",
                    state.frame(),
                    state.epoch()
                ),
            }
            .into());
        }\n        let more_meta ="""


def main(root: Path) -> None:
    path = root / "nyx-core/src/md/trajectory/traj.rs"
    source = path.read_text()
    count = source.count(OLD)
    if count != 1:
        raise RuntimeError(f"expected one Parquet export frame assignment, found {count}")
    updated = source.replace(OLD, NEW, 1)
    path.write_text(updated)
    print("MG_FRAME_EXPORT_FIX_APPLIED: traj.rs only")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
