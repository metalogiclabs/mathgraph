#!/usr/bin/env python3
"""Run local advisory Discover; ERROR exits 1, semantic outcomes exit 0."""

import argparse
from pathlib import Path
import sys

# Explicit package root supports the dependency-free `python -I -S` invocation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathgraph_protocol.discover_sources_v1 import request_from_recursive_transfer
from mathgraph_protocol.discover_v1 import discover, encode_result, error_result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", type=Path, help="strict JSON request file")
    source.add_argument("--source-pack", type=Path, help="local recursive transfer pack directory")
    try:
        args = parser.parse_args(argv)
        request = args.request.read_bytes() if args.request else request_from_recursive_transfer(args.source_pack)
        result = discover(request)
    except OSError:
        result = error_result("SOURCE_IO_ERROR")
    except ValueError as error:
        code = str(error).split(":", 1)[0]
        if code not in {"INVALID_ARGUMENTS", "SOURCE_SIZE_MISMATCH", "SOURCE_DIGEST_MISMATCH"}:
            code = "INVALID_SOURCE"
        result = error_result(code)
    sys.stdout.buffer.write(encode_result(result))
    return 1 if result["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
