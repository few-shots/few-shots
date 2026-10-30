#!/usr/bin/env python3
"""Verifier for p011: the smallest sorting network on 17 inputs.

Contract (shared by every problem):
    python verify.py <shot_dir>
Reads <shot_dir>/certificate.json and prints exactly one line of JSON to stdout:
    {"valid": bool, "score": "exact rational string" | null,
     "canonical_hash": "sha256 hex of the canonical certificate" | null, "message": str}
Exit code 0 means a verdict was given (valid or not); non-zero means a usage or configuration error.

Safety: parses JSON and integers only; no eval, pickle, yaml or symbolic maths; no network;
never echoes strings from the input. Python 3.12 standard library only.

Rule: a comparator network on the channels 0 .. n-1 (n = 17), written as an ordered list of comparators
[a, b] with 0 <= a < b < n. A comparator puts the minimum of its two channels on channel a and the maximum
on channel b; comparators run in the listed order, whatever the input. The network must sort every input
into non-decreasing order of channel number. Score = number of comparators. Lower is better.

Check: by the zero-one principle (Knuth, TAOCP vol. 3, 5.3.4, Theorem Z) a comparator network sorts every
input if and only if it sorts all 2^n inputs of 0s and 1s. The simulation is exhaustive and exact: each
channel is a 2^n-bit integer whose bit k is the channel's value on the 0-1 input k, where channel i of
input k is bit i of k. Output j must equal the sorted output: 1 exactly on the inputs with at least n - j ones.
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
CHANNELS = 17                 # must match [params] channels in problem.toml
MAX_COMPARATORS = 1000        # must match [params] max_comparators in problem.toml
# LOW[s] = byte whose bit j (0 <= j < 8) is set iff popcount(j) >= s, for s = 0 .. 4
LOW = tuple(sum(1 << j for j in range(8) if j.bit_count() >= s) for s in range(5))


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
    n = data["params"]["channels"]
    max_comparators = data["params"]["max_comparators"]
    limit = data["max_certificate_bytes"]
    if type(n) is not int or n != CHANNELS:
        raise ValueError("params.channels must be 17")
    if type(max_comparators) is not int or max_comparators != MAX_COMPARATORS:
        raise ValueError("params.max_comparators must be 1000")
    if type(limit) is not int or not 1 <= limit <= 16 * 1024 * 1024:
        raise ValueError("max_certificate_bytes out of range")
    return {"n": n, "max_comparators": max_comparators, "max_certificate_bytes": limit}


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

def parse_network(cert, n: int, max_comparators: int) -> list:
    """Returns the comparators as a list of (a, b) tuples with 0 <= a < b < n."""
    if not isinstance(cert, dict) or set(cert) != {"comparators"}:
        raise Invalid('the certificate must be a JSON object with the single key "comparators"')
    raw = cert["comparators"]
    if not isinstance(raw, list) or not raw:
        raise Invalid("comparators must be a non-empty list")
    if len(raw) > max_comparators:
        raise Invalid(f"at most {max_comparators} comparators are accepted")
    out = []
    for c in raw:
        if not isinstance(c, list) or len(c) != 2 or not (is_int(c[0]) and is_int(c[1])):
            raise Invalid("each comparator must be a list of two integers [a, b]")
        a, b = c
        if not 0 <= a < b < n:
            raise Invalid(f"each comparator [a, b] must satisfy 0 <= a < b <= {n - 1}")
        out.append((a, b))
    return out


def input_wires(n: int) -> list:
    """Bit k of entry i is bit i of the 0-1 input k (k = 0 .. 2^n - 1); built byte by byte, little-endian."""
    nbytes = (1 << n) // 8
    wires = []
    for i in range(n):
        if i < 3:
            byte = sum(1 << j for j in range(8) if (j >> i) & 1)
            block = bytes([byte]) * nbytes
        else:
            half = 1 << (i - 3)
            block = (b"\x00" * half + b"\xff" * half) * (nbytes // (2 * half))
        wires.append(int.from_bytes(block, "little"))
    return wires


def sorted_outputs(n: int) -> list:
    """Bit k of entry j is 1 iff the 0-1 input k has at least n - j ones, i.e. output j of a sorter."""
    nbytes = (1 << n) // 8
    high = [b.bit_count() for b in range(nbytes)]  # ones among bits 3 .. n-1 of k = 8 b + low
    out = []
    for j in range(n):
        need = n - j
        row = bytes(LOW[min(4, max(0, need - h))] for h in high)
        out.append(int.from_bytes(row, "little"))
    return out


def simulate(pairs: list, n: int) -> list:
    w = input_wires(n)
    for a, b in pairs:
        x, y = w[a], w[b]
        w[a] = x & y
        w[b] = x | y
    return w


def layers(pairs: list, n: int) -> list:
    """Earliest-layer schedule: a comparator's layer is 1 + the largest layer of an earlier comparator that
    shares a channel with it (0 if there is none). Each layer is sorted. Reordering comparators on disjoint
    channels does not change the result."""
    last = [-1] * n
    out: list = []
    for a, b in pairs:
        level = 1 + max(last[a], last[b])
        if level == len(out):
            out.append([])
        out[level].append([a, b])
        last[a] = last[b] = level
    return [sorted(layer) for layer in out]


def canonical_form(pairs: list, n: int) -> dict:
    """The layers of the network or of its mirror image ([a, b] -> [n-1-b, n-1-a]), whichever is smaller as
    nested lists. The mirror image of a sorting network is a sorting network of the same size."""
    mirror = [(n - 1 - b, n - 1 - a) for a, b in pairs]
    return {"channels": n, "layers": min(layers(pairs, n), layers(mirror, n))}


def check_certificate(cert, cfg: dict) -> tuple[Fraction, dict]:
    """Returns (score, canonical object)."""
    n = cfg["n"]
    pairs = parse_network(cert, n, cfg["max_comparators"])
    got = simulate(pairs, n)
    want = sorted_outputs(n)
    for j in range(n):
        if got[j] != want[j]:
            raise Invalid(f"the network does not sort: output channel {j} is wrong on at least one 0-1 input")
    return Fraction(len(pairs)), canonical_form(pairs, n)


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
