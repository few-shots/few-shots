#!/usr/bin/env python3
"""Verifier for p012: the maximal determinant of a 23x23 matrix with entries +1 and -1.

Contract (shared by every problem):
    python verify.py <shot_dir>
Reads <shot_dir>/certificate.json and prints exactly one line of JSON to stdout:
    {"valid": bool, "score": "exact rational string" | null,
     "canonical_hash": "sha256 hex of the canonical certificate" | null, "message": str}
Exit code 0 means a verdict was given (valid or not); non-zero means a usage or configuration error.

Safety: parses JSON and integers only; no eval, pickle, yaml or symbolic maths; no network;
never echoes strings from the input. Python 3.12 standard library only.

Rule: an n x n matrix (n = 23) with every entry the integer +1 or -1. Score = |det|, the absolute value
of its determinant, computed exactly with the fraction-free Bareiss elimination in integers. Larger is
better. Singular matrices are valid and score 0.

Canonical form: negate every row whose first entry is -1, then sort the rows lexicographically (-1 before
+1). It is invariant under row permutations and row negations, and under nothing else.
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
MAX_INT_DIGITS = 18           # maximum digits in a single integer (valid entries have one)
ORDER = 23                    # matrix order n; must match [params] order in problem.toml


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
    limit = data["max_certificate_bytes"]
    if type(n) is not int or n != ORDER:
        raise ValueError("params.order must be 23")
    if type(limit) is not int or not 1 <= limit <= 16 * 1024 * 1024:
        raise ValueError("max_certificate_bytes out of range")
    return {"n": n, "max_certificate_bytes": limit}


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

def parse_matrix(cert, n: int) -> list[list[int]]:
    if not isinstance(cert, dict) or set(cert) != {"matrix"}:
        raise Invalid('the certificate must be a JSON object with the single key "matrix"')
    rows = cert["matrix"]
    if not isinstance(rows, list) or len(rows) != n:
        raise Invalid(f"matrix must be a list of exactly {n} rows")
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != n:
            raise Invalid(f"row {i} must be a list of exactly {n} entries")
        for j, v in enumerate(row):
            if not is_int(v) or v not in (-1, 1):
                raise Invalid(f"entry ({i},{j}) must be the integer -1 or 1")
        out.append(list(row))
    return out


def bareiss_det(mat: list[list[int]]) -> int:
    """Exact determinant of a square integer matrix (fraction-free Bareiss elimination).

    After step k, a[i][j] (i, j > k) is the (k+2)-order leading minor bordered by row i and column j,
    so every division by the previous pivot is exact.
    """
    n = len(mat)
    if n == 0:
        return 1
    a = [list(row) for row in mat]
    sign = 1
    prev = 1
    for k in range(n - 1):
        if a[k][k] == 0:
            for p in range(k + 1, n):
                if a[p][k] != 0:
                    a[k], a[p] = a[p], a[k]
                    sign = -sign
                    break
            else:
                return 0
        akk = a[k][k]
        rowk = a[k]
        for i in range(k + 1, n):
            rowi = a[i]
            aik = rowi[k]
            for j in range(k + 1, n):
                q, r = divmod(akk * rowi[j] - aik * rowk[j], prev)
                if r:
                    raise ArithmeticError("inexact Bareiss division")
                rowi[j] = q
        prev = akk
    return sign * a[n - 1][n - 1]


def canonical_matrix(mat: list[list[int]]) -> list[list[int]]:
    """Negate each row that starts with -1, then sort the rows (Python list order, -1 < 1)."""
    return sorted([[-x for x in row] if row[0] < 0 else list(row) for row in mat])


def check_certificate(cert, cfg: dict) -> tuple[Fraction, dict]:
    """Returns (score, canonical object)."""
    n = cfg["n"]
    mat = parse_matrix(cert, n)
    det = abs(bareiss_det(mat))
    # every n x n +-1 determinant is a multiple of 2^(n-1); anything else is a verifier bug
    if det % (1 << (n - 1)):
        raise ArithmeticError("determinant is not a multiple of 2^(n-1)")
    return Fraction(det), {"matrix": canonical_matrix(mat)}


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
