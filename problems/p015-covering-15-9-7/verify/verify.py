#!/usr/bin/env python3
"""Verifier for the covering design C(15,9,7): the fewest 9-subsets of a 15-set that cover every 7-subset.

Contract (shared by every problem):
    python verify.py <shot_dir>
Reads <shot_dir>/certificate.json and prints exactly one line of JSON to stdout:
    {"valid": bool, "score": "exact rational string" | null,
     "canonical_hash": "sha256 hex of the canonical certificate" | null, "message": str}
Exit code 0 means a verdict was given (valid or not); non-zero means a usage or configuration error.

Safety: parses JSON and integers only; no eval, pickle, yaml or symbolic maths; no network;
never echoes strings from the input. Python 3.12 standard library only.

Rule: points are 0 .. 14 (15 of them). A block is a set of 9 distinct points, written as a list.
The blocks must cover every 7-subset of the 15 points: every 7 of the 15 points lie together in at
least one block. Score = number of blocks. Lower is better.

Check: the coverage test is exhaustive and exact. All C(15,7) = 6435 seven-subsets are enumerated
once, each block contributes its own C(9,7) = 36 seven-subsets, and every seven-subset must be hit.
No counting argument, no tolerance, no floating point.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import stat
import sys
from fractions import Fraction
from pathlib import Path

CERT_NAME = "certificate.json"
MAX_DEPTH = 8                 # maximum JSON nesting depth
MAX_INT_DIGITS = 18           # maximum digits in a single integer
POINTS = 15                   # must match [params] points in problem.toml
BLOCK_SIZE = 9                # must match [params] block_size in problem.toml
COVER_SIZE = 7                # must match [params] cover_size in problem.toml
MAX_BLOCKS = 1000             # must match [params] max_blocks in problem.toml
MAX_BYTES = 65536             # must match max_certificate_bytes in problem.toml

SUBSETS = list(itertools.combinations(range(POINTS), COVER_SIZE))
INDEX = {s: i for i, s in enumerate(SUBSETS)}


class Invalid(Exception):
    """The certificate is invalid. The message is shown verbatim, so it must not contain input strings."""


# ---------- reading and parsing (shared) ----------

def read_certificate(shot_dir: str | os.PathLike, limit: int = MAX_BYTES) -> bytes:
    path = Path(shot_dir) / CERT_NAME
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise Invalid("certificate.json is missing") from None
    except OSError:
        raise Invalid("cannot read certificate.json (symbolic links are not allowed)") from None
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):  # checked before fdopen, which fails on a directory
        os.close(fd)
        raise Invalid("certificate.json is not a regular file")
    with os.fdopen(fd, "rb") as f:
        if st.st_size > limit:
            raise Invalid(f"certificate.json exceeds the size limit of {limit} bytes")
        data = f.read(limit + 1)
    if len(data) > limit:
        raise Invalid(f"certificate.json exceeds the size limit of {limit} bytes")
    return data


def check_depth(text: str, limit: int = MAX_DEPTH) -> None:
    depth = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth > limit:
                raise Invalid(f"JSON is nested deeper than {limit} levels")
        elif ch in "]}":
            depth -= 1


def _no_float(_s: str):
    raise Invalid("fractional or exponent numbers are not allowed")


def _no_constant(_s: str):
    raise Invalid("NaN and Infinity are not allowed")


def _bounded_int(s: str) -> int:
    if len(s.lstrip("-")) > MAX_INT_DIGITS:
        raise Invalid(f"an integer has more than {MAX_INT_DIGITS} digits")
    return int(s)


def _unique_keys(pairs: list) -> dict:
    out: dict = {}
    for k, v in pairs:
        if k in out:
            raise Invalid("a JSON object has duplicate keys")
        out[k] = v
    return out


def strict_json(data: bytes):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Invalid("certificate.json must be UTF-8 text") from None
    check_depth(text)
    try:
        return json.loads(
            text,
            parse_float=_no_float,
            parse_int=_bounded_int,
            parse_constant=_no_constant,
            object_pairs_hook=_unique_keys,
        )
    except RecursionError:
        raise Invalid("JSON is nested too deeply") from None
    except ValueError:  # includes a leading byte order mark
        raise Invalid("certificate.json is not valid JSON") from None


def is_int(x) -> bool:
    return type(x) is int  # excludes bool


def canonical_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


# ---------- problem rule ----------

def parse_blocks(cert) -> list:
    """Returns the blocks as a list of sorted tuples of points."""
    if not isinstance(cert, dict) or set(cert) != {"blocks"}:
        raise Invalid('the certificate must be a JSON object with the single key "blocks"')
    raw = cert["blocks"]
    if not isinstance(raw, list) or not raw:
        raise Invalid("blocks must be a non-empty list")
    if len(raw) > MAX_BLOCKS:
        raise Invalid(f"at most {MAX_BLOCKS} blocks are accepted")
    out = []
    for block in raw:
        if not isinstance(block, list) or len(block) != BLOCK_SIZE:
            raise Invalid(f"each block must be a list of {BLOCK_SIZE} integers")
        if not all(is_int(p) for p in block):
            raise Invalid("each point must be an integer")
        if any(not 0 <= p < POINTS for p in block):
            raise Invalid(f"each point must satisfy 0 <= point <= {POINTS - 1}")
        if len(set(block)) != BLOCK_SIZE:
            raise Invalid("the points of a block must be distinct")
        out.append(tuple(sorted(block)))
    return out


def check_coverage(blocks: list) -> None:
    """Every 7-subset of the 15 points must lie inside at least one block."""
    covered = bytearray(len(SUBSETS))
    for block in blocks:  # block is a sorted tuple of 9 points, so each pick is a sorted tuple
        for pick in itertools.combinations(block, COVER_SIZE):
            covered[INDEX[pick]] = 1
    missing = covered.count(0)
    if missing:
        raise Invalid(f"the covering is incomplete: {missing} of the {len(SUBSETS)} 7-subsets lie in no block")


def canonical_form(blocks: list) -> dict:
    """Blocks sorted inside and as a list: the order of the blocks and of the points in a block is irrelevant."""
    return {"blocks": [list(b) for b in sorted(blocks)],
            "block_size": BLOCK_SIZE, "cover_size": COVER_SIZE, "points": POINTS}


def check_certificate(cert) -> tuple[Fraction, dict]:
    """Returns (score, canonical object)."""
    blocks = parse_blocks(cert)
    check_coverage(blocks)
    return Fraction(len(blocks)), canonical_form(blocks)


# ---------- entry point ----------

def verify_bytes(data: bytes) -> dict:
    if len(data) > MAX_BYTES:
        raise Invalid(f"certificate.json exceeds the size limit of {MAX_BYTES} bytes")
    cert = strict_json(data)
    score, canon = check_certificate(cert)
    return {
        "valid": True,
        "score": str(score),
        "canonical_hash": canonical_hash(canon),
        "message": "ok",
    }


def invalid(message: str) -> dict:
    return {"valid": False, "score": None, "canonical_hash": None, "message": message}


def verify_dir(shot_dir: str | os.PathLike) -> dict:
    try:
        return verify_bytes(read_certificate(shot_dir))
    except Invalid as e:
        return invalid(str(e))
    except RecursionError:
        return invalid("JSON is nested too deeply")
    except MemoryError:
        return invalid("input is too large")
    except Exception:  # no traceback, to avoid leaking details
        return invalid("internal verifier error")


def emit(result: dict) -> None:
    line = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        emit(invalid("usage: python verify.py <shot_dir>"))
        return 2
    emit(verify_dir(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
