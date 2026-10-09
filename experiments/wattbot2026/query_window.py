"""Question-centred exact-substring excerpts; no answers or labels as input.

This changes only which contiguous characters fit the existing context budget.
It is a retrieval heuristic, not evidence of semantic entailment.
"""
from __future__ import annotations
from collections import Counter
import math
import re

TOKEN = re.compile(r"[\w]+(?:[.-][\w]+)*", re.UNICODE)
STOP = frozenset(('a an the is was what how much many in of for from to by on '
                 'and or are were which their its according as at during with '
                 'using does did this that per about than').split())


def query_window(question: str, text: str, limit: int = 1100) -> dict:
    if type(limit) is not int or limit < 1:
        raise ValueError('limit must be a positive integer')
    if not isinstance(question, str) or not isinstance(text, str):
        raise TypeError('question and text must be strings')
    last = max(0, len(text) - limit)
    terms = {m.group().casefold() for m in TOKEN.finditer(question)} - STOP
    if not last or not terms:
        end = min(len(text), limit)
        return {'text': text[:end], 'start': 0, 'end': end}
    occurrences = [(m.start(), m.end(), m.group().casefold())
                   for m in TOKEN.finditer(text)
                   if m.group().casefold() in terms]
    frequencies = Counter(t for _, _, t in occurrences)
    weights = {t: 1 / (1 + math.log1p(n)) for t, n in frequencies.items()}
    starts = {0, last}
    for left, right, _ in occurrences:
        # Centre relevant words, preserving neighbours (including numeric values).
        starts.add(max(0, min(last, (left + right) // 2 - limit // 2)))
    def score(start: int) -> tuple:
        found = Counter(t for left, right, t in occurrences
                        if start <= left and right <= start + limit)
        # Cover distinct question terms; repeated boilerplate has diminishing value.
        relevance = sum(weights[t] * (1 + 0.1 * math.log1p(n - 1))
                        for t, n in found.items())
        return relevance, -start  # Exact ties retain the original prefix.
    start = max(sorted(starts), key=score)
    end = min(len(text), start + limit)
    return {'text': text[start:end], 'start': start, 'end': end}


def window_passages(question: str, passages: list[dict], limit: int = 1100) -> list[dict]:
    """Keep source/page/order identical; copy rather than mutate numeric contexts."""
    result = []
    for page in passages:
        window = query_window(question, page['text'], limit)
        result.append(dict(page, text=window['text'],
                           excerpt_start=window['start'], excerpt_end=window['end']))
    return result
