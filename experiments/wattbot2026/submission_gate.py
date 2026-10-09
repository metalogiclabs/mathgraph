"""Fail-closed CSV transport checks; no answer correction or semantic claim."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
import pandas as pd

COLUMNS = ('id','question','answer','answer_value','answer_unit','ref_id',
           'ref_url','supporting_materials','explanation')

def validate_submission(path: str | Path, expected_ids: list[str]) -> dict:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text, newline=''))
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise ValueError('CSV cannot be decoded or parsed') from exc
    if reader.fieldnames != list(COLUMNS):
        raise ValueError('Wrong submission columns or order')
    if not rows or len(rows) != len(expected_ids):
        raise ValueError('Wrong submission row count')
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError('Duplicate expected IDs')
    if any(None in row for row in rows):
        raise ValueError('CSV contains surplus cells')
    empty = {col:sum(row.get(col) is None or not str(row[col]).strip() for row in rows)
             for col in COLUMNS}
    if any(empty.values()):
        raise ValueError('Empty submission fields by column: '+json.dumps(empty,sort_keys=True))
    ids = [row['id'] for row in rows]
    if ids != [str(x) for x in expected_ids] or len(set(ids)) != len(ids):
        raise ValueError('Submission IDs differ from ordered official questions')
    # Emulate ordinary dataframe ingestion; e.g. "NA" or "null" can be
    # interpreted as missing even when the raw CSV cell is not empty.
    frame = pd.read_csv(io.BytesIO(raw), dtype=str)
    if list(frame.columns) != list(COLUMNS) or len(frame) != len(rows):
        raise ValueError('CSV parser round-trip changed shape')
    nulls = {str(k):int(v) for k,v in frame.isna().sum().items() if v}
    if nulls:
        raise ValueError('CSV null values by column: '+json.dumps(nulls,sort_keys=True))
    return {'rows':len(rows),'null_cells':0,'empty_cells':0,
            'file_sha256':hashlib.sha256(raw).hexdigest(),
            'scope':'CSV transport only; not answer correctness or Kaggle acceptance'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--submission',required=True)
    p.add_argument('--official-zip',required=True)
    args=p.parse_args()
    with zipfile.ZipFile(args.official_zip) as z:
        source=io.StringIO(z.read('test_Q.csv').decode('utf-8-sig'),newline='')
        ids=[row['id'] for row in csv.DictReader(source)]
    print('WATTBOT_CSV_PREFLIGHT='+json.dumps(validate_submission(args.submission,ids),sort_keys=True))

if __name__=='__main__': main()
