"""Fixed-capacity direct-mapped table, with mate distance normalisation."""
from dataclasses import dataclass

EXACT, LOWER, UPPER = 0, 1, 2
MATE = 30000


def pack_score(score: int, ply: int) -> int:
    return score + ply if score > 29000 else score - ply if score < -29000 else score


def unpack_score(score: int, ply: int) -> int:
    return score - ply if score > 29000 else score + ply if score < -29000 else score


@dataclass(slots=True)
class Entry:
    key: object
    depth: int
    score: int
    bound: int
    move: object


class Table:
    def __init__(self, size: int = 4096):
        if size < 1 or size & (size - 1):
            raise ValueError('Table size must be a power of two')
        self.entries = [None] * size
        self.mask = size - 1

    def get(self, key):
        entry = self.entries[hash(key) & self.mask]
        return entry if entry is not None and entry.key == key else None

    def put(self, key, depth, score, bound, move):
        self.entries[hash(key) & self.mask] = Entry(key, depth, score, bound, move)
