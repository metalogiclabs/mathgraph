"""Non-premium build shim for Nyx's unrelated sequence configuration module.

Only the ephemeral CI checkout is modified. The audited trajectory read/write
production files must remain byte-identical to their pinned source revisions.
The shim is not an upstream fix and is included in the evidence boundary.
"""

from pathlib import Path
import sys


def once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"nonpremium shim pattern expected once, observed {count}: {old!r}")
    return source.replace(old, new, 1)


def main(root: Path) -> None:
    path = root / "nyx-core/src/dynamics/sequence/config.rs"
    source = path.read_text()
    source = once(
        source,
        "use crate::dynamics::{SolidTides, SpacecraftDynamics};",
        "use crate::dynamics::SpacecraftDynamics;\n"
        "#[cfg(feature = \"premium\")]\n"
        "use crate::dynamics::SolidTides;",
    )
    source = once(
        source,
        "        if let Some(solid_tides) = &self.accel_models.solid_tides {",
        "        #[cfg(feature = \"premium\")]\n"
        "        if let Some(solid_tides) = &self.accel_models.solid_tides {",
    )
    source = once(
        source,
        "    pub solid_tides: Option<SolidTides>,",
        "    #[cfg(feature = \"premium\")]\n"
        "    pub solid_tides: Option<SolidTides>,",
    )
    source = once(
        source,
        "        fields.insert(\n            \"solid_tides\".to_string(),",
        "        #[cfg(feature = \"premium\")]\n"
        "        fields.insert(\n            \"solid_tides\".to_string(),",
    )
    path.write_text(source)
    print("MG_NONPREMIUM_SHIM_APPLIED: config.rs only")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
