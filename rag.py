"""Small, inspectable local RAG index. No vector DB or external embedding service."""
from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def chunk_text(text: str, source: str, size: int = 180, overlap: int = 35) -> list["Chunk"]:
    """Split on word boundaries; overlap helps retain facts across chunk edges."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size must be positive and 0 <= overlap < size")
    words = text.split()
    return [Chunk(source, i // (size - overlap) + 1, " ".join(words[i:i + size]))
            for i in range(0, len(words), size - overlap) if words[i:i + size]]


@dataclass(frozen=True)
class Chunk:
    source: str
    number: int
    text: str

    @property
    def label(self) -> str:
        return f"{self.source} #{self.number}"


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        # Snapshot the corpus so caller edits cannot desynchronize text and scores.
        self.chunks = tuple(chunks)
        self.tfs = [Counter(tokens(c.text)) for c in self.chunks]
        self.avgdl = sum(map(lambda tf: sum(tf.values()), self.tfs)) / len(self.chunks) if self.chunks else 0
        self.df = Counter(term for tf in self.tfs for term in tf)

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        if k <= 0:
            raise ValueError("k must be positive")
        if not self.chunks or not query.strip():
            return []
        n = len(self.chunks)
        scores = []
        for chunk, tf in zip(self.chunks, self.tfs):
            dl = sum(tf.values())
            score = 0.0
            for term in set(tokens(query)):
                freq = tf.get(term, 0)
                if freq:
                    idf = math.log(1 + (n - self.df[term] + .5) / (self.df[term] + .5))
                    score += idf * freq * 2.2 / (freq + 1.2 * (.25 + .75 * dl / self.avgdl))
            if score > 0:
                scores.append((chunk, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)[:k]
