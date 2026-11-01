"""p014 verifier tests: valid, invalid and hostile inputs. Run with: python3 tools/run_tests.py"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import itertools
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("fewshots_verify_p014", HERE / "verify.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

N = 29
BASELINE = "623"
BASELINE_MARKS = [0, 3, 28, 33, 41, 95, 156, 158, 193, 207, 233, 252, 267, 338, 339, 355, 394, 403, 421,
                  473, 479, 502, 523, 570, 580, 592, 612, 616, 623]
BASELINE_HASH = "e4ad2bc601c9451ea6e8e0bd3af4abcb23bcc5a3e7d2a2c228a33ebc26f0ed9b"
MAX_MARK = 10**15


def is_golomb(marks) -> bool:
    """Independent reference: every unordered pair, straight from the definition."""
    diffs = [abs(a - b) for a, b in itertools.combinations(marks, 2)]
    return len(set(diffs)) == len(diffs)


def ref_hash(marks) -> str:
    """Canonical hash written from the PROBLEM.md text, without json.dumps."""
    xs = sorted(marks)
    a = [x - xs[0] for x in xs]
    length = a[-1]
    b = sorted(length - x for x in a)
    keep = a if a <= b else b
    text = '{"marks":[' + ",".join(str(x) for x in keep) + "]}"
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def reflect(marks) -> list:
    top = max(marks)
    return sorted(top - x for x in marks)


def random_ruler(rng: random.Random, n: int = N, span: int = 10**6) -> list:
    """A random Golomb ruler with n marks in 0 .. span, built greedily."""
    while True:
        marks, diffs = [], set()
        for _ in range(50 * n):
            x = rng.randint(0, span)
            new = {abs(x - m) for m in marks}
            if x in marks or len(new) < len(marks) or new & diffs:
                continue
            marks.append(x)
            diffs |= new
            if len(marks) == n:
                return sorted(marks)


def singer_modular_ruler(q: int = 29) -> list:
    """Independent rebuild of the 30-element Singer set modulo q^2+q+1 for a prime q (GF(q^3) = GF(q)[x]/(f))."""
    def mul(a, b, f):
        out = [0] * 5
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                out[i + j] = (out[i + j] + x * y) % q
        for k in (4, 3):
            c = out[k]
            for j in range(4):
                out[k - 3 + j] = (out[k - 3 + j] - c * f[j]) % q
        return out[:3]

    order = q ** 3 - 1
    primes = [p for p in range(2, 1000) if order % p == 0 and all(p % d for d in range(2, p))]
    for c0, c1 in itertools.product(range(1, q), range(q)):
        f = [c0, c1, 0, 1]
        if any((r ** 3 + c1 * r + c0) % q == 0 for r in range(q)):
            continue
        ok = True
        for p in primes:
            acc, base, e = [1, 0, 0], [0, 1, 0], order // p
            while e:
                if e & 1:
                    acc = mul(acc, base, f)
                base = mul(base, base, f)
                e >>= 1
            ok = ok and acc != [1, 0, 0]
        if ok:
            break
    modulus = q * q + q + 1
    elem, out = [1, 0, 0], set()
    for i in range(order):
        if elem[2] == 0:
            out.add(i % modulus)
        elem = mul(elem, [0, 1, 0], f)
    return sorted(out)


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = V.load_config(ROOT / "problem.toml")
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_bytes(self, data: bytes) -> dict:
        (self.dir / "certificate.json").write_bytes(data)
        return V.verify_dir(self.dir, self.cfg)

    def run_obj(self, obj) -> dict:
        return self.run_bytes(json.dumps(obj).encode("utf-8"))

    def run_marks(self, marks) -> dict:
        return self.run_obj({"marks": marks})

    def assertInvalid(self, res: dict, fragment: str = ""):
        self.assertFalse(res["valid"], res)
        self.assertIsNone(res["score"])
        self.assertIsNone(res["canonical_hash"])
        self.assertIn(fragment, res["message"])

    def assertValid(self, res: dict, score: int | str | None = None):
        self.assertTrue(res["valid"], res)
        self.assertEqual(res["message"], "ok")
        if score is not None:
            self.assertEqual(res["score"], str(score))

    def with_mark(self, value, i: int = 0) -> list:
        m = BASELINE_MARKS[:]
        m[i] = value
        return m

    # ---------- baseline and problem.toml

    def test_baseline_reproduces_baseline_score(self):
        with open(ROOT / "problem.toml", "rb") as f:
            meta = tomllib.load(f)
        res = V.verify_dir(ROOT / "baseline", self.cfg)
        self.assertValid(res)
        self.assertEqual(res["score"], meta["baseline_score"])
        self.assertEqual(meta["baseline_score"], BASELINE)
        self.assertEqual(res["canonical_hash"], BASELINE_HASH)
        cert = json.loads((ROOT / "baseline" / "certificate.json").read_text(encoding="utf-8"))
        self.assertEqual(cert, {"marks": BASELINE_MARKS})
        self.assertTrue(is_golomb(BASELINE_MARKS))

    def test_baseline_is_cut_from_the_singer_set(self):
        # PROBLEM.md, Baseline: 30 residues mod 871 with distinct differences; some unit multiple has a
        # 29-element cyclic window of length 623 equal to the baseline up to reflection, and none is shorter
        d = singer_modular_ruler(29)
        self.assertEqual(len(d), 30)
        self.assertEqual(len({(a - b) % 871 for a in d for b in d if a != b}), 870)
        best, found = None, False
        for t in range(1, 871):
            if t % 13 == 0 or t % 67 == 0:  # 871 = 13 * 67
                continue
            s = sorted(t * x % 871 for x in d)
            for start in range(30):
                w = [(s[(start + j) % 30] - s[start]) % 871 for j in range(N)]
                best = w[-1] if best is None else min(best, w[-1])
                if w in (BASELINE_MARKS, reflect(BASELINE_MARKS)):
                    found = True
        self.assertEqual(best, 623)
        self.assertTrue(found)

    def test_problem_toml(self):
        with open(ROOT / "problem.toml", "rb") as f:
            meta = tomllib.load(f)
        self.assertEqual(meta["id"], "p014")
        self.assertEqual(meta["slug"], "golomb-ruler-29")
        self.assertEqual(ROOT.name, "p014-golomb-ruler-29")
        self.assertEqual(meta["epsilon"], "1")
        self.assertEqual(meta["epsilon_mode"], "absolute")
        self.assertEqual(meta["direction"], "min")
        self.assertEqual(meta["params"], {"order": N, "max_mark": MAX_MARK})
        self.assertEqual(meta["max_certificate_bytes"], 65536)
        self.assertEqual(meta["proposal"], 49)
        self.assertEqual(meta["proposer"], "pedestrian6")
        self.assertFalse(meta["sandbox"])

    def test_bounds_in_problem_md(self):
        # trivial bound and the derivation from G(28) = 585: max(a, b) >= 2 for the two end gaps
        self.assertEqual(N * (N - 1) // 2, 406)
        self.assertEqual(585 + 2, 587)
        a, b = BASELINE_MARKS[1] - BASELINE_MARKS[0], BASELINE_MARKS[-1] - BASELINE_MARKS[-2]
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(int(BASELINE) - max(a, b), 585)
        # Carter-O'Bryant-Tao: k^2 (1/(1 + c/sqrt k) - c/sqrt k) - 1 with c = 0.945, k = 29, lies in (566, 567).
        # With s = sqrt(29) the value is 841 (1/(1 + c/s) - c/s) - 1 = f(s); f is increasing in s, so bracketing
        # s between two rationals brackets the value.
        c = Fraction(945, 1000)

        def f(s):
            return 841 * (1 / (1 + c / s) - c / s) - 1
        lo, hi = Fraction(538516, 100000), Fraction(538517, 100000)
        self.assertTrue(lo * lo < 29 < hi * hi)
        self.assertTrue(566 < f(lo) < f(hi) < 567)

    def test_config_rejects_other_parameters(self):
        text = (ROOT / "problem.toml").read_text(encoding="utf-8")
        for old, bad in (("order = 29", "order = 28"), ("order = 29", 'order = "29"'),
                         ("order = 29", "order = 29.0"), ("order = 29", "order = 30"),
                         ("max_mark = 1000000000000000", "max_mark = 10"),
                         ("max_mark = 1000000000000000", "max_mark = 1e15")):
            p = self.dir / "problem.toml"
            p.write_text(text.replace(old, bad, 1), encoding="utf-8")
            with self.assertRaises(Exception):
                V.load_config(p)

    # ---------- the rule and the score

    def test_score_is_length_not_largest_mark(self):
        shifted = [x + 1000 for x in BASELINE_MARKS]                        # review A: baseline_shifted_by_1000
        self.assertValid(self.run_marks(shifted), BASELINE)
        top = [x + MAX_MARK - 623 for x in BASELINE_MARKS]                  # largest mark exactly 10^15
        self.assertValid(self.run_marks(top), BASELINE)

    def test_random_rulers_match_the_reference(self):
        rng = random.Random(29)
        for t in range(40):
            marks = random_ruler(rng, span=10 ** rng.randint(4, 15))
            self.assertTrue(is_golomb(marks))
            res = self.run_marks(marks)
            self.assertValid(res, marks[-1] - marks[0])
            self.assertEqual(res["canonical_hash"], ref_hash(marks))

    def test_near_baseline_rulers_match_the_reference(self):
        # perturb one or two marks of the baseline; the verdict must agree with the definition
        rng = random.Random(49)
        valid = invalid = 0
        for t in range(300):
            m = set(BASELINE_MARKS)
            for _ in range(rng.randint(1, 2)):
                m.discard(rng.choice(sorted(m)))
            while len(m) < N:
                x = rng.randint(0, 1500)
                if t % 2 or (x not in m and is_golomb(sorted(m | {x}))):  # odd t: any mark; even t: keep it Golomb
                    m.add(x)
            marks = sorted(m)
            res = self.run_marks(marks)
            if is_golomb(marks):
                valid += 1
                self.assertValid(res, marks[-1] - marks[0])
                self.assertEqual(res["canonical_hash"], ref_hash(marks))
            else:
                invalid += 1
                self.assertInvalid(res, "not a Golomb ruler")
        self.assertGreater(valid, 0)
        self.assertGreater(invalid, 0)

    def test_repeated_differences(self):
        self.assertInvalid(self.run_marks(list(range(N))), "not a Golomb ruler")          # review B: repeated_difference
        self.assertInvalid(self.run_marks(self.with_mark(622, 28)), "not a Golomb ruler")  # review A: repeated_difference
        self.assertFalse(is_golomb(self.with_mark(622, 28)))
        # a repeat that shares a mark (three-term progression) and one between disjoint pairs
        ap = BASELINE_MARKS[:28] + [2 * 616 - 612]
        self.assertFalse(is_golomb(ap))
        self.assertInvalid(self.run_marks(ap), "not a Golomb ruler")
        rng = random.Random(3)
        for _ in range(20):
            marks = random_ruler(rng)
            i, j = sorted(rng.sample(range(N - 1), 2))
            bad = sorted(set(marks[:N - 1]) | {marks[N - 2] + marks[j] - marks[i]})
            if len(bad) == N:
                self.assertFalse(is_golomb(bad))
                self.assertInvalid(self.run_marks(bad), "not a Golomb ruler")

    def test_repeated_difference_message_uses_indices_only(self):
        res = self.run_marks(list(range(N)))
        self.assertEqual(res["message"], "not a Golomb ruler: mark 1 - mark 0 equals mark 2 - mark 1 (marks counted from 0)")
        m = [x * 1000003 for x in range(N)]
        self.assertNotIn("1000003", self.run_marks(m)["message"])
        self.assertEqual(V.find_repeated_difference([0, 1, 4, 9, 11]), None)
        self.assertEqual(V.find_repeated_difference([0, 2, 5, 7]), (0, 2, 1, 3))  # 5 - 0 == 7 - 2

    def test_known_optimal_small_rulers(self):
        # optimal rulers for 5, 6 and 11 marks (Rokicki and Dogon, section 2, for the 11-mark length 72)
        for marks in ([0, 1, 4, 9, 11], [0, 1, 4, 10, 12, 17], [0, 3, 14, 16, 20, 41, 48, 53, 63, 71, 72]):
            self.assertIsNone(V.find_repeated_difference(marks))
            self.assertTrue(is_golomb(marks))

    # ---------- canonical form and hash

    def test_shift_and_reflection_keep_the_hash(self):
        refl = reflect(BASELINE_MARKS)
        self.assertEqual(refl[:3], [0, 7, 11])
        cases = (
            BASELINE_MARKS,
            refl,                                                   # review A: baseline_reflected
            [x + 1000 for x in BASELINE_MARKS],                     # review A: baseline_shifted_by_1000
            [x + 17 for x in refl],                                 # review B: translated_reflection
            [x + MAX_MARK - 623 for x in refl],
        )
        for marks in cases:
            res = self.run_marks(marks)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], BASELINE_HASH)

    def test_canonical_form_is_idempotent_and_matches_the_reference(self):
        rng = random.Random(5)
        for marks in [BASELINE_MARKS] + [random_ruler(rng) for _ in range(10)]:
            c = V.canonical_marks(marks)
            self.assertEqual(c[0], 0)
            self.assertEqual(V.canonical_marks(c), c)
            self.assertEqual(V.canonical_marks(reflect(marks)), c)
            self.assertLessEqual(c, reflect(c))
            res = self.run_marks(c)
            self.assertEqual(res["canonical_hash"], self.run_marks(marks)["canonical_hash"])
            self.assertEqual(res["canonical_hash"], ref_hash(marks))

    def test_worked_examples_in_problem_md(self):
        self.assertEqual(V.canonical_marks([10, 14, 17, 18]), [0, 1, 4, 8])
        blob = b'{"marks":[0,1,4,8]}'
        self.assertEqual(V.canonical_hash({"marks": [0, 1, 4, 8]}), hashlib.sha256(blob).hexdigest())
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         "0b23813710787f97546f927f9dcc3f0c5e93035b0e9e1f9d3209da223d3e95ae")
        self.assertEqual(V.canonical_marks(BASELINE_MARKS), BASELINE_MARKS)
        text = json.dumps({"marks": BASELINE_MARKS}, sort_keys=True, separators=(",", ":"))
        self.assertEqual(text, '{"marks":[0,3,28,33,41,95,156,158,193,207,233,252,267,338,339,355,394,403,421,'
                               '473,479,502,523,570,580,592,612,616,623]}')
        self.assertEqual(len(text), 119)
        self.assertEqual(hashlib.sha256(text.encode("ascii")).hexdigest(), BASELINE_HASH)

    def test_canonical_hash_separates_inequivalent_rulers(self):
        rng = random.Random(8)
        hashes = {self.run_marks(random_ruler(rng))["canonical_hash"] for _ in range(20)}
        self.assertEqual(len(hashes), 20)
        self.assertNotIn(BASELINE_HASH, hashes)

    def test_formatting_and_key_spelling_do_not_matter(self):
        compact = json.dumps({"marks": BASELINE_MARKS}, separators=(",", ":")).encode()
        variants = [
            compact,
            json.dumps({"marks": BASELINE_MARKS}, indent=4).encode(),
            b"\n\t " + compact + b"\r\n",
            compact.replace(b'"marks"', b'"\\u006darks"'),
            compact.replace(b"[0,", b"[-0,", 1),
            (ROOT / "baseline" / "certificate.json").read_bytes(),
        ]
        for data in variants:
            res = self.run_bytes(data)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], BASELINE_HASH)

    def test_deterministic(self):
        marks = random_ruler(random.Random(9))
        first = self.run_marks(marks)
        self.assertEqual(self.run_marks(marks), first)
        self.assertEqual(self.run_marks(marks), first)
        base = V.verify_dir(ROOT / "baseline", self.cfg)
        self.assertEqual(V.verify_dir(ROOT / "baseline", self.cfg), base)

    def test_key_order_does_not_change_the_verdict(self):
        # only one key is allowed, so shuffling keys can only move an extra key before or after "marks"
        body = json.dumps(BASELINE_MARKS)
        before = self.run_bytes(('{"n": 29, "marks": %s}' % body).encode())
        after = self.run_bytes(('{"marks": %s, "n": 29}' % body).encode())
        self.assertInvalid(before, "single key")
        self.assertEqual(before, after)

    # ---------- invalid certificates (every adversarial case of both reviews)

    def test_missing_empty_and_malformed(self):
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "missing")              # review A: missing file
        self.assertInvalid(self.run_bytes(b""), "valid JSON")                        # review B: empty_file
        self.assertInvalid(self.run_bytes(b"{}"), "single key")                      # A, B: empty_object
        self.assertInvalid(self.run_bytes(b"{}\n"), "single key")
        self.assertInvalid(self.run_bytes(b"this is not json"), "valid JSON")        # review A: not_json
        self.assertInvalid(self.run_bytes(b'{"marks":['), "valid JSON")              # review B: malformed_json
        self.assertInvalid(self.run_bytes(b"{marks: 1}"), "valid JSON")
        self.assertInvalid(self.run_bytes(b'__import__("os").system("id")'), "valid JSON")

    def test_wrong_shape(self):
        B = BASELINE_MARKS
        self.assertInvalid(self.run_obj([B]), "single key")                          # review A: top_level_list
        self.assertInvalid(self.run_obj(B), "single key")
        self.assertInvalid(self.run_obj({"marks": B, "n": 29}), "single key")
        self.assertInvalid(self.run_obj({"marks": B, "score": "1"}), "single key")
        self.assertInvalid(self.run_obj({"Marks": B}), "single key")
        extra = b'{"marks":' + json.dumps(B).encode() + b',"extra":' + b"[" * 64 + b"]" * 64 + b"}"
        self.assertInvalid(self.run_bytes(extra), "nested")                          # review B: nested_extra_depth64
        extra = b'{"marks":' + json.dumps(B).encode() + b',"extra":[[[1]]]}'
        self.assertInvalid(self.run_bytes(extra), "single key")
        self.assertInvalid(self.run_obj({"marks": "0,3,28"}), "exactly 29")           # review A: marks_not_list
        for bad in (None, 1, {}, {"0": 0}):
            self.assertInvalid(self.run_obj({"marks": bad}), "exactly 29")
        self.assertInvalid(self.run_marks([]), "exactly 29")                         # review A: empty_marks
        self.assertInvalid(self.run_marks(B[:28]), "exactly 29")                     # review A: 28_marks
        self.assertInvalid(self.run_marks(B + [1000000]), "exactly 29")              # review A: 30_marks
        self.assertInvalid(self.run_marks(B + [624]), "exactly 29")                  # review B: too_many_marks
        self.assertInvalid(self.run_marks([B]), "exactly 29")

    def test_order_and_duplicates(self):
        self.assertInvalid(self.run_marks(BASELINE_MARKS[::-1]), "strictly increasing")      # review A: not_sorted
        self.assertInvalid(self.run_marks(self.with_mark(616, 28)), "strictly increasing")   # review A: duplicate_mark
        swapped = BASELINE_MARKS[:]
        swapped[3], swapped[4] = swapped[4], swapped[3]
        self.assertInvalid(self.run_marks(swapped), "mark 4")
        self.assertInvalid(self.run_marks([5] * N), "strictly increasing")

    def test_bad_marks(self):
        for bad in (True, False, "623", "x", None, [623], {"v": 623}):               # review A/B: bool, string
            self.assertInvalid(self.run_marks(self.with_mark(bad, 28)), "mark 28 must be an integer")
        self.assertInvalid(self.run_marks(self.with_mark(False, 0)), "mark 0 must be an integer")  # bool_mark
        self.assertInvalid(self.run_marks(self.with_mark(-1, 0)), "between 0 and 10^15")    # review A: negative_mark
        self.assertInvalid(self.run_marks([x - 5 for x in BASELINE_MARKS]), "between 0 and 10^15")
        top = [x + MAX_MARK - 622 for x in BASELINE_MARKS]                                    # largest mark 10^15 + 1
        self.assertInvalid(self.run_marks(top), "mark 28 must be between 0 and 10^15")
        self.assertInvalid(self.run_marks(self.with_mark(10**17, 28)), "between 0 and 10^15")

        class Sub(int):
            pass
        with self.assertRaises(V.Invalid):
            V.parse_marks({"marks": self.with_mark(Sub(623), 28)}, N, MAX_MARK)
        with self.assertRaises(V.Invalid):
            V.parse_marks({"marks": self.with_mark(True, 1)}, N, MAX_MARK)

    def test_numbers_must_be_plain_ascii_integers(self):
        data = json.dumps({"marks": self.with_mark(777, 28)}).encode()
        for bad, msg in ((b"623.0", "fractional"), (b"6.23e2", "fractional"), (b"623e0", "fractional"),
                         (b"623E0", "fractional"), (b"NaN", "NaN"), (b"Infinity", "NaN"),
                         (b"-Infinity", "NaN"), (b"+623", "valid JSON"), (b"0x26f", "valid JSON"),
                         (b"0623", "valid JSON"), ("٦٢٣".encode(), "valid JSON"), ("６２３".encode(), "valid JSON"),
                         (b"null", "integer"), (b"true", "integer")):
            self.assertInvalid(self.run_bytes(data.replace(b"777", bad, 1)), msg)
        self.assertInvalid(self.run_marks(self.with_mark(623.0, 28)), "fractional")          # review A: float_mark
        self.assertInvalid(self.run_marks(self.with_mark(0.0, 0)), "fractional")             # review B: float_mark
        nan = b'{"marks": [NaN' + b", 1" * 28 + b"]}"                                        # review A: nan
        self.assertInvalid(self.run_bytes(nan), "NaN")
        huge = b'{"marks": [0, ' + b"9" * 5000 + b"]}"                                       # review A: huge_int
        self.assertInvalid(self.run_bytes(huge), "digits")
        self.assertInvalid(self.run_bytes(data.replace(b"777", b"1" * 19, 1)), "digits")
        self.assertInvalid(self.run_bytes(data.replace(b"777", b"-" + b"1" * 19, 1)), "digits")

    def test_duplicate_keys(self):
        body = json.dumps(BASELINE_MARKS)
        self.assertInvalid(self.run_bytes(('{"marks": %s, "marks": %s}' % (body, body)).encode()), "duplicate keys")
        self.assertInvalid(self.run_bytes(('{"marks":%s,"\\u006darks":%s}' % (body, body)).encode()), "duplicate keys")

    # ---------- hostile input

    def test_oversized_file(self):
        limit = self.cfg["max_certificate_bytes"]
        self.assertEqual(limit, 65536)
        self.assertInvalid(self.run_bytes(b" " * (limit + 1)), "size limit")
        body = json.dumps({"marks": BASELINE_MARKS}).encode()
        self.assertInvalid(self.run_bytes(body + b" " * (1 << 20)), "size limit")         # review B: 1 MiB padding
        self.assertInvalid(self.run_bytes(body + b" " * (5 << 20)), "size limit")         # review A: 5 MB certificate
        self.assertValid(self.run_bytes(body + b" " * (limit - len(body))), BASELINE)     # exactly at the limit
        self.assertInvalid(self.run_bytes(body + b" " * (limit + 1 - len(body))), "size limit")

    def test_deeply_nested_json(self):
        self.assertInvalid(self.run_bytes(b"[[[[[[[[[0]]]]]]]]]"), "nested")
        self.assertInvalid(self.run_bytes(b'{"marks":' + b"[" * 1000 + b"]" * 1000 + b"}"), "nested")
        self.assertInvalid(self.run_bytes(("[" * 30000 + "]" * 30000).encode()), "nested")
        self.assertInvalid(self.run_bytes(("[" * 100000 + "]" * 100000).encode()), "size limit")  # A: deep_nesting
        self.assertInvalid(self.run_bytes(b"[" * 60000), "nested")
        self.assertInvalid(self.run_bytes(b'{"marks":[[[[[[[[1]]]]]]]]}'), "nested")
        self.assertInvalid(self.run_bytes(b'{"marks":[[[[[[[1]]]]]]]}'), "exactly 29")      # 8 levels is allowed

    def test_brackets_inside_strings_do_not_count_as_depth(self):
        self.assertInvalid(self.run_bytes(b'{"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\\\": "[[[[[[[[[[[["}'), "single key")

    def test_not_utf8_and_byte_order_mark(self):
        body = json.dumps({"marks": BASELINE_MARKS}).encode()
        self.assertInvalid(self.run_bytes(b"\xff\xfe{}"), "UTF-8")
        self.assertInvalid(self.run_bytes(body.decode().encode("utf-16")), "UTF-8")
        self.assertInvalid(self.run_bytes(b"\xef\xbb\xbf" + body), "valid JSON")
        self.assertInvalid(self.run_bytes(b'{"marks": "\xc0\xaf"}'), "UTF-8")
        self.assertInvalid(self.run_bytes(b'{"marks": "\xed\xa0\x80"}'), "UTF-8")
        self.assertInvalid(self.run_bytes(b'{"\\ud800": 1}'), "single key")

    def test_symlink_fifo_and_directory(self):
        target = self.dir / "real.json"
        target.write_text(json.dumps({"marks": BASELINE_MARKS}))
        os.symlink(target, self.dir / "certificate.json")
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "symbolic links")
        os.unlink(self.dir / "certificate.json")
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.dir / "certificate.json")
            self.assertInvalid(V.verify_dir(self.dir, self.cfg), "regular file")
            os.unlink(self.dir / "certificate.json")
        os.mkdir(self.dir / "certificate.json")
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "regular file")

    def test_messages_never_echo_input(self):
        for data in (b'{"marks": "<script>alert(1)</script>"}', b'{"<script>alert(1)</script>": 1}',
                     json.dumps({"marks": self.with_mark("<script>", 3)}).encode()):
            self.assertNotIn("script", self.run_bytes(data)["message"])
        res = self.run_marks(self.with_mark(987654321987654321, 28))
        self.assertNotIn("987654321", res["message"])
        res = self.run_bytes(b'{"marks": [' + b"7" * 30 + b"]}")
        self.assertNotIn("7777", res["message"])

    def test_worst_case_input_is_fast(self):
        limit = self.cfg["max_certificate_bytes"]
        rng = random.Random(0)
        cases = []
        for marks in (random_ruler(rng, span=MAX_MARK), BASELINE_MARKS, [x + MAX_MARK - 623 for x in BASELINE_MARKS]):
            body = json.dumps({"marks": marks}, indent=1).encode()
            cases.append(body + b" " * (limit - len(body)))
        cases.append(b"[" * 8 + b"]" * 8 + b" " * (limit - 16))
        cases.append(b'"' + b"\\\\" * ((limit - 2) // 2) + b'"')
        start = time.perf_counter()
        for _ in range(5):
            for data in cases:
                self.run_bytes(data)
        self.assertLess(time.perf_counter() - start, 5)

    # ---------- command-line contract

    def run_cli(self, *args, env=None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(HERE / "verify.py"), *args],
                              capture_output=True, timeout=60, env=env)

    def test_cli_prints_exactly_one_json_line(self):
        proc = self.run_cli(str(ROOT / "baseline"))
        self.assertEqual(proc.returncode, 0)
        lines = proc.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        obj = json.loads(lines[0])
        self.assertEqual(set(obj), {"valid", "score", "canonical_hash", "message"})
        self.assertEqual(obj["score"], BASELINE)
        self.assertEqual(obj["canonical_hash"], BASELINE_HASH)
        self.assertEqual(proc.stderr, b"")
        (self.dir / "certificate.json").write_text("[" * 100000)
        proc = self.run_cli(str(self.dir))
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(json.loads(proc.stdout)["valid"])
        self.assertEqual(proc.stderr, b"")

    def test_cli_is_deterministic_across_hash_seeds(self):
        outs = set()
        for seed in ("0", "1", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            outs.add(self.run_cli(str(ROOT / "baseline"), env=env).stdout)
        self.assertEqual(len(outs), 1)

    def test_cli_usage_error(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(json.loads(proc.stdout)["valid"])

    def test_source_has_no_dangerous_constructs(self):
        tree = ast.parse((HERE / "verify.py").read_text(encoding="utf-8"))
        imported, called = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                f = node.func
                called.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
        self.assertLessEqual(imported, {"__future__", "hashlib", "json", "os", "stat", "sys",
                                        "tomllib", "fractions", "pathlib"})
        self.assertFalse(called & {"eval", "exec", "compile", "__import__", "literal_eval",
                                   "sympify", "system", "popen"})


if __name__ == "__main__":
    unittest.main()
