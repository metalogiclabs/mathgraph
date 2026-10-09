#!/usr/bin/env python3
"""Bounded question-window intervention on the qualified 24-PDF reader.

Only the excerpt start changes. Numeric fallback, source ranking, six-context
budget, model, prompt, verifier and output budget remain unchanged. Historical
score is a comparator, not a same-run paired LLM trial. TRAIN gold enters the
post-run availability audit only; never a window-selection or model input.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import zipfile
from query_window import window_passages

PINS = {
    'Score.py':'e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075',
    'metadata.csv':'b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1',
    'train_QA.csv':'9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca',
}
CORPUS_SHA = 'dd3eefee514b58ea807c6670241ad4bba9111058216f844d8996f20076568e23'
BASE_READER_BLOB = '51e2444d5e07a50203abf0b11659503471604b3c'


def run(path: str) -> None:
    import retrieved_reader_probe as base
    from holdout_probe import is_holdout
    from train_probe import load_csv, parse_refs
    from wattbot import NUM_RE, as_fraction

    raw = Path(base.__file__).read_bytes()
    git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if git_blob != BASE_READER_BLOB:
        raise RuntimeError('Baseline reader changed; re-audit before spending')
    with zipfile.ZipFile(path) as z:
        for name, expected in PINS.items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise RuntimeError('Official snapshot changed; re-audit before spending')
    assert base.K == 6 and base.MAX_EXCERPT == 1100
    assert base.MAX_BUDGET_USD == 0.12 and base.MAX_OUTPUT_TOKENS == 650
    original = base.passages_for
    observations = {}

    def replacement(question, chunks):
        passages, numeric_hits = original(question, chunks)
        windows = window_passages(question, passages, base.MAX_EXCERPT)
        observations[hashlib.sha256(question.encode()).hexdigest()] = (passages, windows)
        return windows, numeric_hits

    base.passages_for = replacement
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            base.run(path)
    finally:
        base.passages_for = original
    marker = 'WATTBOT_RETRIEVED_FLASHLITE_HOLDOUT='
    results = [json.loads(line[len(marker):]) for line in output.getvalue().splitlines()
               if line.startswith(marker)]
    if len(results) != 1:
        raise RuntimeError('Missing unique official-scoring result')
    result = results[0]
    result.update(intervention='query_centred_exact_substring_1100_chars',
                  comparator_run=37892696030, historical_comparator_score=0.34867725,
                  baseline_reader_blob=git_blob,
                  corpus_matches_historical=result.get('source_manifest_sha256') == CORPUS_SHA,
                  same_run_paired_model_comparison=False)
    print('WATTBOT_QUERY_WINDOW_READER=' + json.dumps(result, sort_keys=True), flush=True)

    # Post-inference paired diagnostic: literal value presence is NOT entailment.
    with zipfile.ZipFile(path) as z:
        held = [r for r in load_csv(z, 'train_QA.csv') if is_holdout(r['id'])]
    audit = Counter()
    chars = Counter()
    for row in held:
        key = hashlib.sha256(row['question'].encode()).hexdigest()
        if key not in observations:
            audit['not_observed'] += 1
            continue
        pages, windows = observations[key]
        audit['questions'] += 1
        audit['shifted_questions'] += any(w['excerpt_start'] != 0 for w in windows)
        for page, window in zip(pages, windows):
            chars['prefix'] += len(page['text'][:1100])
            chars['window'] += len(window['text'])
        try:
            gold = as_fraction(row['answer_value'])
        except (ValueError, TypeError, ZeroDivisionError):
            continue
        refs = set(parse_refs(row['ref_id']))
        audit['scalar_questions'] += 1
        def present(candidate_pages, prefix):
            for page in candidate_pages:
                if page['ref_id'] not in refs:
                    continue
                body = page['text'][:1100] if prefix else page['text']
                for match in NUM_RE.finditer(body):
                    try:
                        if as_fraction(match.group()) == gold:
                            return True
                    except ValueError:
                        pass
            return False
        old = present(pages, True)
        new = present(windows, False)
        full = present(pages, False)
        audit['prefix_gold_literal'] += old
        audit['window_gold_literal'] += new
        audit['full_selected_chunk_gold_literal'] += full
        audit['literal_gained'] += new and not old
        audit['literal_lost'] += old and not new
    print('WATTBOT_WINDOW_AVAILABILITY_AUDIT=' + json.dumps({
        'counts':dict(audit), 'context_characters':dict(chars),
        'scope':'Gold scalar literals on gold sources only, post-hoc TRAIN diagnostic; not semantic correctness',
    }, sort_keys=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--official-zip', required=True)
    run(parser.parse_args().official_zip)
