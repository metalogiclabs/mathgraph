#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mathgraph.lean_bridge_capability import compile_authority_file


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("authority")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=compile_authority_file(a.authority,out_path=a.out)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
