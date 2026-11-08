#!/usr/bin/env python3
"""Verify integer Mondrian dissections and print one JSON verdict.

Geometry follows proposal #57: bounds, area sum, non-congruence and exact cover.
File handling follows p000; D4 canonicalization is specified in PROBLEM.md.
Python 3.12 standard library only. Repository code license: Apache-2.0.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tomllib
from pathlib import Path

CERT_NAME = "certificate.json"
MAX_DEPTH = 8
MAX_INT_DIGITS = 9


class Invalid(Exception):
    """Messages are fixed strings and must never echo certificate text."""


def find_problem_toml() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here / "problem.toml", here.parent / "problem.toml"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("problem.toml not found")


def load_config(path: Path | None = None) -> dict:
    with open(path or find_problem_toml(), "rb") as handle:
        data = tomllib.load(handle)
    n = data["params"]["n"]
    count = data["params"]["max_rectangles"]
    limit = data["max_certificate_bytes"]
    if type(n) is not int or n != 87:
        raise ValueError("params.n must be 87")
    if type(count) is not int or count != 1000:
        raise ValueError("params.max_rectangles must be 1000")
    if type(limit) is not int or not 1 <= limit <= 16 * 1024 * 1024:
        raise ValueError("max_certificate_bytes out of range")
    return {"n": n, "max_rectangles": count, "max_certificate_bytes": limit}


def read_certificate(shot_dir: str | os.PathLike, limit: int) -> bytes:
    path = Path(shot_dir) / CERT_NAME
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise Invalid("certificate.json is missing") from None
    except OSError:
        raise Invalid("certificate.json cannot be read; symlinks are not allowed") from None
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise Invalid("certificate.json must be a regular file")
        if info.st_size > limit:
            raise Invalid("certificate.json exceeds the size limit")
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise Invalid("certificate.json exceeds the size limit")
    return raw


def check_depth(text: str) -> None:
    depth = 0
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise Invalid("JSON nesting exceeds 8 levels")
        elif char in "]}":
            depth -= 1


def _no_float(_token: str):
    raise Invalid("decimal and exponent numbers are not allowed")


def _no_constant(_token: str):
    raise Invalid("NaN and Infinity are not allowed")


def _bounded_int(token: str) -> int:
    if len(token.lstrip("-")) > MAX_INT_DIGITS:
        raise Invalid("integer tokens exceed 9 digits")
    return int(token)


def _unique_keys(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("JSON objects must not repeat keys")
        result[key] = value
    return result


def strict_json(raw: bytes):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Invalid("certificate.json must be UTF-8") from None
    check_depth(text)
    try:
        return json.loads(text, parse_float=_no_float, parse_constant=_no_constant,
                          parse_int=_bounded_int, object_pairs_hook=_unique_keys)
    except RecursionError:
        raise Invalid("JSON nesting is too deep") from None
    except ValueError:
        raise Invalid("certificate.json is not valid JSON") from None


def parse_rectangles(cert, cfg: dict) -> list:
    if not isinstance(cert, dict):
        raise Invalid("the certificate must be a JSON object")
    if set(cert) != {"rectangles"}:
        raise Invalid('the certificate must have exactly one key, "rectangles"')
    items = cert["rectangles"]
    if not isinstance(items, list):
        raise Invalid('"rectangles" must be a list')
    if len(items) < 2:
        raise Invalid("at least two rectangles are required")
    if len(items) > cfg["max_rectangles"]:
        raise Invalid("too many rectangles")
    n = cfg["n"]
    rects = []
    for item in items:
        if not isinstance(item, list) or len(item) != 4:
            raise Invalid("each rectangle must be a list of four integers [x,y,w,h]")
        if any(type(value) is not int for value in item):
            raise Invalid("every coordinate and side length must be an integer")
        x, y, w, h = item
        if w < 1 or h < 1:
            raise Invalid("rectangle side lengths must be positive")
        if x < 0 or y < 0 or x + w > n or y + h > n:
            raise Invalid("a rectangle is outside the square")
        rects.append((x, y, w, h))
    return rects


def check(rects: list, n: int) -> int:
    areas = [w * h for _, _, w, h in rects]
    if sum(areas) != n * n:
        raise Invalid("rectangle areas do not add up to the square area")
    shapes = set()
    for _, _, w, h in rects:
        shape = (min(w, h), max(w, h))
        if shape in shapes:
            raise Invalid("two rectangles are congruent")
        shapes.add(shape)
    # The area precheck bounds all row scans and writes by n*n cells.
    cover = bytearray(n * n)
    for x, y, w, h in rects:
        for row in range(y, y + h):
            start = row * n + x
            if cover.count(0, start, start + w) != w:
                raise Invalid("two rectangles overlap")
            cover[start:start + w] = b"\x01" * w
    if 0 in cover:
        raise Invalid("rectangles do not cover the square")
    return max(areas) - min(areas)


def canonical_hash(rects: list, n: int) -> str:
    images = []
    current = rects
    for _ in range(4):
        images.append(sorted(current))
        images.append(sorted((n - x - w, y, w, h) for x, y, w, h in current))
        current = [(n - y - h, x, h, w) for x, y, w, h in current]
    canonical = {"rectangles": min(images)}
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def verify_bytes(raw: bytes, cfg: dict) -> dict:
    if len(raw) > cfg["max_certificate_bytes"]:
        raise Invalid("certificate.json exceeds the size limit")
    rects = parse_rectangles(strict_json(raw), cfg)
    score = check(rects, cfg["n"])
    return {"valid": True, "score": str(score),
            "canonical_hash": canonical_hash(rects, cfg["n"]), "message": "ok"}


def invalid(message: str) -> dict:
    return {"valid": False, "score": None, "canonical_hash": None, "message": message}


def verify_dir(shot_dir: str | os.PathLike, cfg: dict) -> dict:
    try:
        return verify_bytes(read_certificate(shot_dir, cfg["max_certificate_bytes"]), cfg)
    except Invalid as exc:
        return invalid(str(exc))
    except RecursionError:
        return invalid("JSON nesting is too deep")
    except MemoryError:
        return invalid("input is too large")
    except Exception:
        return invalid("the certificate could not be checked")


def emit(result: dict) -> None:
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n")
    sys.stdout.buffer.flush()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        emit(invalid("usage: python3 verify.py <shot_dir>"))
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
