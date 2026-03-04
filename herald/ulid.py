"""Minimal ULID generator — stdlib only, no external deps."""
from __future__ import annotations

import os
import time

_ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_ulid() -> str:
    """Generate a ULID (Universally Unique Lexicographically Sortable Identifier)."""
    t = int(time.time() * 1000)
    # 10 chars for timestamp (48 bits)
    ts_part = []
    for _ in range(10):
        ts_part.append(_ENCODING[t & 0x1F])
        t >>= 5
    ts_part.reverse()
    # 16 chars for randomness (80 bits)
    rand_bytes = os.urandom(10)
    rand_int = int.from_bytes(rand_bytes, "big")
    rnd_part = []
    for _ in range(16):
        rnd_part.append(_ENCODING[rand_int & 0x1F])
        rand_int >>= 5
    rnd_part.reverse()
    return "".join(ts_part) + "".join(rnd_part)
