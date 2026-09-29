#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mathgraph.lean_import_slice import materialize_slice


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",required=True)
    p.add_argument("--target",action="append",default=[],required=True)
    p.add_argument("--out-root",required=True)
    p.add_argument("--extra",action="append",default=[],help="src=dest")
    args=p.parse_args()

    extras=[]
    for item in args.extra:
        src,sep,dst=item.partition("=")
        if not sep:
            raise SystemExit(f"bad --extra {item!r}; expected src=dest")
        extras.append((src,dst))

    result=materialize_slice(
        args.repo_root,args.target,args.out_root,extra_files=extras
    )
    print(json.dumps({
        "file_count":result["file_count"],
        "source_bytes":result["source_bytes"],
        "target_count":len(result["targets"]),
        "unresolved_local_candidates":result["unresolved_local_candidates"],
        "status":result["status"],
    },sort_keys=True))


if __name__=="__main__":
    main()
