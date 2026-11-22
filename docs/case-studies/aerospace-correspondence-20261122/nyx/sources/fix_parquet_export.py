"""Apply the minimal fail-closed frame-fidelity correction to a pinned Nyx checkout.

Expected precondition: unmodified upstream nyx-core/src/md/trajectory/traj.rs.
This is used for the bounded RED/GREEN research replay; the upstream PR should
carry the resulting native Rust diff, not depend on this script.
"""

from pathlib import Path
import sys


OLD = "        let frame = self.states[0].frame();"
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
        }"""


def main(root: Path) -> None:
    path = root / "nyx-core/src/md/trajectory/traj.rs"
    source = path.read_text()
    # A distinct RIC-difference export path uses the same frame assignment.
    # Scope the correction to Traj::to_parquet, not every occurrence in the file.
    start = source.index("    pub fn to_parquet<P: AsRef<Path>>(")
    end = source.index("    pub fn resample(", start)
    section = source[start:end]
    count = section.count(OLD)
    if count != 1:
        raise RuntimeError(f"expected one Parquet export frame assignment, found {count}")
    updated = source[:start] + section.replace(OLD, NEW, 1) + source[end:]
    path.write_text(updated)
    print("MG_FRAME_EXPORT_FIX_APPLIED: traj.rs only")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
