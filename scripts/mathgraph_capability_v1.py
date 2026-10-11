#!/usr/bin/env python3
"""Inspect a local portable capability; INVALID exits 1, UNKNOWN exits 0."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathgraph_protocol.capability_v1 import encode_result, error_result, evaluate_contract


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--expected-contract", type=Path, help="consumer-owned exact descriptor snapshot")
    try:
        args = parser.parse_args(argv)
        expected = args.expected_contract.read_bytes() if args.expected_contract else None
        result = evaluate_contract(args.contract.read_bytes(), expected_contract=expected)
    except OSError:
        result = error_result("SOURCE_IO_ERROR")
    except ValueError:
        result = error_result("INVALID_ARGUMENTS")
    sys.stdout.buffer.write(encode_result(result))
    return 1 if result["validation"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
