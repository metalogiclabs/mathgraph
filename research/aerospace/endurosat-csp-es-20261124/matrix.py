"""Independent elapsed-time and finite-ring oracle; each case starts a fresh process."""
import csv
import io
import json
import subprocess
import sys

rows = []
for version in (1, 2):
    for start in (1000, 2**32 - 50, 2**32 - 10000):
        for elapsed in (0, 1, 30, 49, 50, 55, 99, 100, 101, 10001):
            for others in (0, 14, 15, 16):
                result = subprocess.run(
                    [sys.argv[1], str(version), str(start), str(elapsed), str(others)],
                    check=True, capture_output=True, text=True,
                )
                values = list(map(int, result.stdout.split()))
                assert values[:4] == [version, start, elapsed, others]
                assert values[4:6] == [0, 0], "fresh-packet or distinct-payload control failed"
                expected = int(elapsed <= 100 and others < 16)
                rows.append(values + [expected, int(values[6] != expected)])
out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
out.writerow(["version", "start", "elapsed", "others", "first", "other_errors", "actual", "expected", "mismatch"])
out.writerows(rows)
print(json.dumps({"cases": len(rows), "mismatches": sum(row[-1] for row in rows)}), file=sys.stderr)
