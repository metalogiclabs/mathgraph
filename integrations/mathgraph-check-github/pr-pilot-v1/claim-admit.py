"""Reuse the qualified claim-admission boundary; never execute PR-defined code."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'experiments/check-l4-claim-consumer-v1'))
from rules import admit
value=json.load(sys.stdin)
print(json.dumps(admit(value['receipt'],value['controller'])))
