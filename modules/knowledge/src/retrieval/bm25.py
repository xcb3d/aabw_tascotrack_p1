"""Small deterministic BM25 implementation for the AIE2 artifact retrieval slice."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize_vi(text: str) -> tuple[str, ...]:
    """Normalize Vietnamese Unicode and return a stable whitespace/word baseline."""

    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(TOKEN_RE.findall(normalized))


class BM25Index:
    def __init__(self, documents: Sequence[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        if not documents:
            raise ValueError("BM25 requires at least one document")
        self.k1 = k1
        self.b = b
        self.tokens = tuple(tokenize_vi(document) for document in documents)
        self.term_frequencies = tuple(Counter(tokens) for tokens in self.tokens)
        self.lengths = tuple(len(tokens) for tokens in self.tokens)
        self.average_length = sum(self.lengths) / len(self.lengths)
        document_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            document_frequency.update(set(tokens))
        count = len(self.tokens)
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def scores(self, query: str) -> tuple[float, ...]:
        query_terms = tokenize_vi(query)
        result: list[float] = []
        for frequencies, length in zip(self.term_frequencies, self.lengths, strict=True):
            score = 0.0
            length_factor = 1 - self.b + self.b * length / max(self.average_length, 1)
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                numerator = frequency * (self.k1 + 1)
                denominator = frequency + self.k1 * length_factor
                score += self.idf.get(term, 0.0) * numerator / denominator
            result.append(score)
        return tuple(result)
