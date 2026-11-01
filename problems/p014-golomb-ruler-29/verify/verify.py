#!/usr/bin/env python3
"""Verifier for p014: the shortest Golomb ruler with 29 marks.

Contract (shared by every problem):
    python verify.py <shot_dir>
Reads <shot_dir>/certificate.json and prints exactly one line of JSON to stdout:
    {"valid": bool, "score": "exact rational string" | null,
     "canonical_hash": "sha256 hex of the canonical certificate" | null, "message": str}
Exit code 0 means a verdict was given (valid or not); non-zero means a usage or configuration error.

Safety: parses JSON and integers only; no eval, pickle, yaml or symbolic maths; no network;
never echoes strings or numbers from the input. Python 3.12 standard library only.

Rule: exactly n = 29 integer marks, listed in strictly increasing order, each between 0 and 10^15
inclusive, such that the n(n-1)/2 = 406 differences between pairs of marks are pairwise distinct.
Score = largest mark - smallest mark (the length), an integer. Lower is better.

Canonical form: shift the marks so the smallest is 0, giving A; reflect, giving B = sorted(L - a for a in A);
keep the lexicographically smaller of A and B. Shifted and reflected copies of one ruler hash the same.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tomllib
from fractions import Fraction
from pathlib import Path

CERT_NAME = "certificate.json"
MAX_DEPTH = 8                 # maximum JSON nesting depth
MAX_INT_DIGITS = 18           # maximum digits in a single integer
ORDER = 29                    # number of marks; must match [params] order in problem.toml
MAX_MARK = 10**15             # largest allowed mark; must match [params] max_mark in problem.toml


class Invalid(Exception):
    """The certificate is invalid. The message is shown verbatim, so it must not contain input strings."""


# ---------- configuration ----------

def find_problem_toml() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here / "problem.toml", here.parent / "problem.toml"):
        if cand.is_file():
            return cand
    raise FileNotFoundError("problem.toml not found")


def load_config(path: Path | None = None) -> dict:
    with open(path or find_problem_toml(), "rb") as f:
        data = tomllib.load(f)
    n = data["params"]["order"]
    max_mark = data["params"]["max_mark"]
    limit = data["max_certificate_bytes"]
    if type(n) is not int or n != ORDER:
        raise ValueError("params.order must be 29")
    if type(max_mark) is not int or max_mark != MAX_MARK:
        raise ValueError("params.max_mark must be 10^15")
    if type(limit) is not int or not 1 <= limit <= 16 * 1024 * 1024:
        raise ValueError("max_certificate_bytes out of range")
    return {"n": n, "max_mark": max_mark, "max_certificate_bytes": limit}


# ---------- reading and parsing (shared) ----------

def read_certificate(shot_dir: str | os.PathLike, limit: int) -> bytes:
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
    if not s.lstrip("-").isascii():  # JSON digits are ASCII; int() would also accept other scripts
        raise Invalid("certificate.json is not valid JSON")
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

def parse_marks(cert, n: int, max_mark: int) -> list[int]:
    """Returns the marks as a list of n plain ints, strictly increasing, each in 0 .. max_mark."""
    if not isinstance(cert, dict) or set(cert) != {"marks"}:
        raise Invalid('the certificate must be a JSON object with the single key "marks"')
    raw = cert["marks"]
    if not isinstance(raw, list) or len(raw) != n:
        raise Invalid(f"marks must be a list of exactly {n} integers")
    out: list[int] = []
    for i, m in enumerate(raw):
        if not is_int(m):
            raise Invalid(f"mark {i} must be an integer")
        if not 0 <= m <= max_mark:
            raise Invalid(f"mark {i} must be between 0 and 10^15")
        if out and m <= out[-1]:
            raise Invalid(f"marks must be strictly increasing (mark {i} is not larger than mark {i - 1})")
        out.append(int(m))
    return out


def find_repeated_difference(marks: list[int]) -> tuple[int, int, int, int] | None:
    """Returns index pairs (i, j, k, l) with marks[j] - marks[i] == marks[l] - marks[k], or None."""
    seen: dict[int, tuple[int, int]] = {}
    for j in range(len(marks)):
        for i in range(j):
            d = marks[j] - marks[i]
            if d in seen:
                k, l = seen[d]
                return k, l, i, j
            seen[d] = (i, j)
    return None


def canonical_marks(marks: list[int]) -> list[int]:
    """The ruler shifted to start at 0, or its reflection, whichever is lexicographically smaller."""
    a = [x - marks[0] for x in marks]
    length = a[-1]
    b = [length - x for x in reversed(a)]
    return min(a, b)


def check_certificate(cert, cfg: dict) -> tuple[Fraction, dict]:
    """Returns (score, canonical object)."""
    marks = parse_marks(cert, cfg["n"], cfg["max_mark"])
    rep = find_repeated_difference(marks)
    if rep is not None:
        k, l, i, j = rep
        raise Invalid(f"not a Golomb ruler: mark {l} - mark {k} equals mark {j} - mark {i} (marks counted from 0)")
    return Fraction(marks[-1] - marks[0]), {"marks": canonical_marks(marks)}


# ---------- entry point ----------

def verify_bytes(data: bytes, cfg: dict) -> dict:
    cert = strict_json(data)
    score, canon = check_certificate(cert, cfg)
    return {
        "valid": True,
        "score": str(score),
        "canonical_hash": canonical_hash(canon),
        "message": "ok",
    }


def verify_dir(shot_dir: str | os.PathLike, cfg: dict) -> dict:
    try:
        return verify_bytes(read_certificate(shot_dir, cfg["max_certificate_bytes"]), cfg)
    except Invalid as e:
        return invalid(str(e))
    except RecursionError:
        return invalid("JSON is nested too deeply")
    except MemoryError:
        return invalid("input is too large")
    except Exception:  # no traceback, to avoid leaking details
        return invalid("internal verifier error")


def invalid(message: str) -> dict:
    return {"valid": False, "score": None, "canonical_hash": None, "message": message}


def emit(result: dict) -> None:
    line = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        emit(invalid("usage: python verify.py <shot_dir>"))
        return 2
    try:
        cfg = load_config()
    except Exception:
        emit(invalid("verifier configuration error"))
        return 2
    emit(verify_dir(argv[1], cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
