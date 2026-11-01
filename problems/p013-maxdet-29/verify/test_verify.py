"""p013 verifier tests: valid, invalid and hostile inputs. Run with: python3 tools/run_tests.py"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import itertools
import json
import math
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
_spec = importlib.util.spec_from_file_location("fewshots_verify_p013", HERE / "verify.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

N = 29
STEP = 2 ** (N - 1)
BASELINE = "1188957517256767569920"
BASELINE_HASH = "b39a583d8ecf8327fbdc8ccac18cb0cf4d607fbab200dd48996ff3f45fd4de94"
ALL_ONES_HASH = "e0247170ca1577d28a64b4912b7be2f4120a7c592c77f23c2f1fea6d2b5805c0"  # review B: singular_valid


def ref_det(mat) -> int:
    """Independent reference: Gaussian elimination over the rationals."""
    a = [[Fraction(x) for x in row] for row in mat]
    n, d = len(a), Fraction(1)
    for k in range(n):
        p = next((i for i in range(k, n) if a[i][k] != 0), None)
        if p is None:
            return 0
        if p != k:
            a[k], a[p] = a[p], a[k]
            d = -d
        d *= a[k][k]
        for i in range(k + 1, n):
            f = a[i][k] / a[k][k]
            for j in range(k, n):
                a[i][j] -= f * a[k][j]
    assert d.denominator == 1
    return int(d)


def leibniz_det(mat) -> int:
    """Independent reference for small matrices: sum over permutations."""
    n, total = len(mat), 0
    for perm in itertools.permutations(range(n)):
        inv = sum(1 for i in range(n) for j in range(i + 1, n) if perm[i] > perm[j])
        prod = 1
        for i in range(n):
            prod *= mat[i][perm[i]]
        total += -prod if inv % 2 else prod
    return total


def ref_hash(mat) -> str:
    """Canonical hash written from the PROBLEM.md text, without json.dumps."""
    rows = [[x * row[0] for x in row] for row in mat]
    rows.sort(key=lambda r: [0 if x == -1 else 1 for x in r])
    text = '{"matrix":[' + ",".join("[" + ",".join(str(x) for x in r) + "]" for r in rows) + "]}"
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def printed_gram() -> list:
    """The Gram matrix M printed on d29.html: 29 on the diagonal, 5 between rows 1-3 and 4-6,
    -3 between row 7 and rows 8-11, 1 elsewhere (rows counted from 1)."""
    m = [[1] * N for _ in range(N)]
    for i in range(N):
        m[i][i] = N
    for i, j in itertools.product(range(3), range(3, 6)):
        m[i][j] = m[j][i] = 5
    for j in range(7, 11):
        m[6][j] = m[j][6] = -3
    return m


def random_matrix(rng: random.Random, n: int = N) -> list:
    return [[rng.choice((-1, 1)) for _ in range(n)] for _ in range(n)]


def load_baseline() -> list:
    return json.loads((ROOT / "baseline" / "certificate.json").read_text(encoding="utf-8"))["matrix"]


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = V.load_config(ROOT / "problem.toml")
        self.R = load_baseline()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_bytes(self, data: bytes) -> dict:
        (self.dir / "certificate.json").write_bytes(data)
        return V.verify_dir(self.dir, self.cfg)

    def run_obj(self, obj) -> dict:
        return self.run_bytes(json.dumps(obj).encode("utf-8"))

    def run_mat(self, mat) -> dict:
        return self.run_obj({"matrix": mat})

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

    def with_entry(self, value, i: int = 0, j: int = 0) -> list:
        m = [row[:] for row in self.R]
        m[i][j] = value
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
        self.assertEqual(int(BASELINE), 4429211904320 * 2**28)
        self.assertEqual(int(BASELINE), 320 * 7**12 * 2**28)
        self.assertEqual(int(BASELINE), 5 * 7**12 * 2**34)
        self.assertEqual(4429211904320, 2**6 * 5 * 7**12)
        # the matrix printed on the source page has determinant +|det|
        self.assertEqual(V.bareiss_det(self.R), int(BASELINE))
        self.assertEqual(ref_det(self.R), int(BASELINE))

    def test_baseline_gram_matrix(self):
        # the source page prints M = R R^T = R^T R
        rrt = [[sum(a * b for a, b in zip(r, s)) for s in self.R] for r in self.R]
        cols = [list(c) for c in zip(*self.R)]
        rtr = [[sum(a * b for a, b in zip(r, s)) for s in cols] for r in cols]
        self.assertEqual(rrt, printed_gram())
        self.assertEqual(rtr, printed_gram())
        self.assertEqual(ref_det(rrt), int(BASELINE) ** 2)

    def test_epsilon_and_next_score(self):
        with open(ROOT / "problem.toml", "rb") as f:
            meta = tomllib.load(f)
        self.assertEqual(meta["epsilon"], str(STEP))
        self.assertEqual(meta["epsilon"], "268435456")
        self.assertEqual(meta["epsilon_mode"], "absolute")
        self.assertEqual(meta["direction"], "max")
        self.assertEqual(meta["params"]["order"], N)
        self.assertEqual(meta["proposal"], 47)
        self.assertEqual(meta["proposer"], "pedestrian6")
        self.assertFalse(meta["sandbox"])
        self.assertEqual(int(BASELINE) % STEP, 0)
        self.assertEqual(int(BASELINE) + STEP, 4429211904321 * 2**28)
        self.assertEqual(int(BASELINE) + STEP, 1188957517257036005376)

    def test_bounds_in_problem_md(self):
        # Barba bound sqrt(57) * 28^14: irrational, integer part as stated
        b2 = (2 * N - 1) * (N - 1) ** (N - 1)
        self.assertNotEqual(math.isqrt(2 * N - 1) ** 2, 2 * N - 1)
        self.assertEqual(math.isqrt(b2), 1374516212147183939924)
        # Brent-Orrick-Osborn-Zimmermann (2011), Table 1: d29 < 329 * 7^12
        upper = 329 * 7**12 * 2**28
        self.assertEqual(upper, 1222396947429614157824)
        self.assertEqual(upper - STEP, 1222396947429345722368)
        self.assertEqual(322 * 7**12, 46 * 7**13)
        self.assertLess(int(BASELINE), upper)
        self.assertEqual(Fraction(upper, int(BASELINE)), Fraction(329, 320))
        self.assertLess(upper * upper, b2)
        # ratios to the Barba bound: baseline 0.86500..., upper bound 0.88932...
        self.assertTrue(Fraction(86500, 10**5) ** 2 * b2 < int(BASELINE) ** 2 < Fraction(86501, 10**5) ** 2 * b2)
        self.assertTrue(Fraction(88932, 10**5) ** 2 * b2 < upper ** 2 < Fraction(88933, 10**5) ** 2 * b2)
        # the earlier record on the page, 45 * 7^13 * 2^28, is below the baseline
        self.assertLess(45 * 7**13, 320 * 7**12)

    def test_config_rejects_other_orders(self):
        text = (ROOT / "problem.toml").read_text(encoding="utf-8")
        for bad in ("order = 23", 'order = "29"', "order = 29.0", "order = 30"):
            p = self.dir / "problem.toml"
            p.write_text(text.replace("order = 29", bad, 1), encoding="utf-8")
            with self.assertRaises(Exception):
                V.load_config(p)

    # ---------- the determinant

    def test_bareiss_matches_leibniz_on_small_integer_matrices(self):
        rng = random.Random(12)
        for n in range(0, 6):
            for _ in range(40):
                m = [[rng.randint(-3, 3) for _ in range(n)] for _ in range(n)]
                self.assertEqual(V.bareiss_det(m), leibniz_det(m) if n else 1, m)

    def test_bareiss_needs_pivoting(self):
        self.assertEqual(V.bareiss_det([[0, 1], [1, 0]]), -1)
        self.assertEqual(V.bareiss_det([[0, 0, 1], [0, 1, 0], [1, 0, 0]]), -1)
        self.assertEqual(V.bareiss_det([[1, 1, 1], [1, 1, 2], [1, 2, 3]]), -1)  # zero pivot after step 0
        self.assertEqual(V.bareiss_det([[1, 1, 1], [1, 2, 3], [1, 1, 2]]), 1)   # a[i][k] == 0 below the pivot
        self.assertEqual(V.bareiss_det([[0, 0], [0, 1]]), 0)
        self.assertEqual(V.bareiss_det([[1, 1], [1, 1]]), 0)

    def test_zero_pivot_on_order_29(self):
        # rows 0 and 1 agree in the first k columns, so the pivot at step 1 is 0 and a row swap is needed
        rng = random.Random(29)
        for k in (2, 3, 5, 10):
            for _ in range(5):
                m = random_matrix(rng)
                m[1][:k] = m[0][:k]
                m[2][:k] = [-x for x in m[0][:k]]
                self.assertValid(self.run_mat(m), abs(ref_det(m)))
        m = [r[:] for r in self.R]
        m[1][:2] = m[0][:2]
        self.assertValid(self.run_mat(m), abs(ref_det(m)))

    def test_exhaustive_small_orders(self):
        # every 3x3 and 4x4 +-1 matrix: multiples of 2^(n-1), maxima 4 and 16 (OEIS A003433)
        for n, top in ((3, 4), (4, 16)):
            seen = set()
            for bits in range(1 << (n * n)):
                m = [[1 if bits >> (n * i + j) & 1 else -1 for j in range(n)] for i in range(n)]
                d = V.bareiss_det(m)
                self.assertEqual(d % 2 ** (n - 1), 0)
                seen.add(abs(d))
            self.assertEqual(max(seen), top)
        self.assertEqual(seen, {0, 8, 16})

    def test_score_matches_reference_on_random_matrices(self):
        rng = random.Random(23)
        for _ in range(30):
            m = random_matrix(rng)
            res = self.run_mat(m)
            self.assertValid(res, abs(ref_det(m)))
            self.assertEqual(res["canonical_hash"], ref_hash(m))

    def test_review_a_random_and_near_baseline_matrices(self):
        # review A: 200 random or near-baseline matrices, Bareiss against exact fractions
        rng = random.Random(47)
        for t in range(200):
            if t < 100:
                m = random_matrix(rng)
            else:
                m = [r[:] for r in self.R]
                for _ in range(rng.randint(1, 4)):
                    m[rng.randrange(N)][rng.randrange(N)] *= -1
                if t % 10 == 0:
                    m[5] = m[7][:]
            d = V.bareiss_det(m)
            self.assertEqual(d, ref_det(m))
            self.assertEqual(d % STEP, 0)

    def test_score_on_singular_and_near_singular_matrices(self):
        rng = random.Random(7)
        for _ in range(10):
            m = random_matrix(rng)
            i, j = rng.sample(range(N), 2)
            m[j] = m[i][:] if rng.random() < 0.5 else [-x for x in m[i]]   # equal or opposite rows
            self.assertValid(self.run_mat(m), 0)
            m[j][rng.randrange(N)] *= -1
            self.assertValid(self.run_mat(m), abs(ref_det(m)))
        # review B: all-ones matrix; review A: baseline with its first row repeated
        res = self.run_mat([[1] * N for _ in range(N)])
        self.assertValid(res, 0)
        self.assertEqual(res["canonical_hash"], ALL_ONES_HASH)
        self.assertValid(self.run_mat(self.R[:28] + [self.R[0]]), 0)
        # repeated column
        self.assertValid(self.run_mat([r[:28] + [r[0]] for r in self.R]), 0)

    def test_negative_determinant_scores_its_absolute_value(self):
        swapped = [self.R[1], self.R[0]] + self.R[2:]
        self.assertEqual(V.bareiss_det(swapped), -int(BASELINE))
        self.assertValid(self.run_mat(swapped), BASELINE)

    def test_known_small_order_values(self):
        h2 = [[1, 1], [1, -1]]
        h4 = [[a * b for a in r1 for b in r2] for r1 in h2 for r2 in h2]
        h8 = [[a * b for a in r1 for b in r2] for r1 in h4 for r2 in h2]
        self.assertEqual(abs(V.bareiss_det(h4)), 16)
        self.assertEqual(abs(V.bareiss_det(h8)), 4096)

    def test_determinant_is_a_multiple_of_2_to_the_28(self):
        rng = random.Random(28)
        for _ in range(20):
            self.assertEqual(V.bareiss_det(random_matrix(rng)) % STEP, 0)

    # ---------- canonical form and hash

    def test_row_permutations_and_negations_keep_the_hash(self):
        ref = self.run_mat(self.R)
        rng = random.Random(3)
        swapped = [self.R[1], self.R[0]] + self.R[2:]
        negated = [[-x for x in r] if i == 5 else r for i, r in enumerate(self.R)]
        everything = [[-x for x in r] for r in self.R]
        shuffled = [[s * x for x in r] for r, s in
                    zip(rng.sample(self.R, N), (rng.choice((-1, 1)) for _ in range(N)))]
        for m in (swapped, negated, everything, shuffled):
            res = self.run_mat(m)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], ref["canonical_hash"])

    def test_column_operations_and_transpose_keep_the_score(self):
        # review A: transformed (row/column permutations, row/column negations, transpose).
        # Same score; the hash follows the stated canonical form, which does not identify column operations.
        rng = random.Random(47)
        m = [r[:] for r in self.R]
        rng.shuffle(m)
        cols = list(range(N))
        rng.shuffle(cols)
        m = [[r[c] for c in cols] for r in m]
        for i in range(N):
            if rng.random() < 0.5:
                m[i] = [-x for x in m[i]]
        for c in range(N):
            if rng.random() < 0.5:
                for r in m:
                    r[c] = -r[c]
        transformed = [list(x) for x in zip(*m)]
        transposed = [list(c) for c in zip(*self.R)]
        colneg = [[-x if j == 4 else x for j, x in enumerate(r)] for r in self.R]
        for mat in (transformed, transposed, colneg):
            res = self.run_mat(mat)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], ref_hash(mat))
        self.assertNotEqual(ref_hash(colneg), BASELINE_HASH)

    def test_canonical_form_is_idempotent_and_matches_the_reference(self):
        rng = random.Random(5)
        for m in [self.R] + [random_matrix(rng) for _ in range(10)]:
            c = V.canonical_matrix(m)
            self.assertEqual(V.canonical_matrix(c), c)
            self.assertTrue(all(r[0] == 1 for r in c))
            self.assertEqual(c, sorted(c))
            res = self.run_mat(c)
            self.assertEqual(res["canonical_hash"], self.run_mat(m)["canonical_hash"])
            self.assertEqual(res["canonical_hash"], ref_hash(m))

    def test_worked_examples_in_problem_md(self):
        rows = [[-1, 1, 1], [1, 1, -1], [1, -1, 1]]
        self.assertEqual(V.canonical_matrix(rows), [[1, -1, -1], [1, -1, 1], [1, 1, -1]])
        blob = b'{"matrix":[[1,-1,-1],[1,-1,1],[1,1,-1]]}'
        self.assertEqual(V.canonical_hash({"matrix": V.canonical_matrix(rows)}), hashlib.sha256(blob).hexdigest())
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         "46472a7336ecc2317e522d315d86dca3f959157b2efc98d132cc54d408dcde26")
        self.assertEqual([i + 1 for i, r in enumerate(self.R) if r[0] < 0], [1, 3, 7, 15, 18, 19, 22, 23, 28])
        text = json.dumps({"matrix": V.canonical_matrix(self.R)}, sort_keys=True, separators=(",", ":"))
        self.assertTrue(text.startswith('{"matrix":[[1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,-1,-1,1,1,-1,1,-1,-1,'
                                        '-1,-1,-1,-1,-1,1,-1,1,1],'))
        self.assertEqual(len(text), 2138)
        self.assertEqual(hashlib.sha256(text.encode("ascii")).hexdigest(), BASELINE_HASH)

    def test_canonical_hash_separates_inequivalent_matrices(self):
        other = self.with_entry(-self.R[10][10], 10, 10)
        self.assertNotEqual(self.run_mat(other)["canonical_hash"], BASELINE_HASH)

    def test_formatting_and_key_spelling_do_not_matter(self):
        compact = json.dumps({"matrix": self.R}, separators=(",", ":")).encode()
        variants = [
            compact,
            json.dumps({"matrix": self.R}, indent=4).encode(),
            b"\n\t " + compact + b"\r\n",
            compact.replace(b'"matrix"', b'"\\u006datrix"'),
            (ROOT / "baseline" / "certificate.json").read_bytes(),
        ]
        for data in variants:
            res = self.run_bytes(data)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], BASELINE_HASH)

    def test_deterministic(self):
        rng = random.Random(9)
        m = random_matrix(rng)
        first = self.run_mat(m)
        self.assertEqual(self.run_mat(m), first)
        self.assertEqual(self.run_mat(m), first)
        base = V.verify_dir(ROOT / "baseline", self.cfg)
        self.assertEqual(V.verify_dir(ROOT / "baseline", self.cfg), base)

    def test_key_order_does_not_change_the_verdict(self):
        # only one key is allowed, so shuffling keys can only move an extra key before or after "matrix"
        body = json.dumps(self.R)
        before = self.run_bytes(('{"x": 1, "matrix": %s}' % body).encode())
        after = self.run_bytes(('{"matrix": %s, "x": 1}' % body).encode())
        self.assertInvalid(before, "single key")
        self.assertEqual(before, after)

    # ---------- invalid certificates (every adversarial case of both reviews)

    def test_missing_empty_and_malformed(self):
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "missing")                 # review A: missing
        self.assertInvalid(self.run_bytes(b""), "valid JSON")                           # A, B: empty_file
        self.assertInvalid(self.run_bytes(b"{}"), "single key")                         # A, B: empty_object
        self.assertInvalid(self.run_bytes(b'{"matrix": [[1, -1],'), "valid JSON")       # review A: not_json
        self.assertInvalid(self.run_bytes(b'{"matrix":'), "valid JSON")                 # review B: malformed
        self.assertInvalid(self.run_bytes(b"{matrix: 1}"), "valid JSON")
        self.assertInvalid(self.run_bytes(b'__import__("os").system("id")'), "valid JSON")

    def test_wrong_shape(self):
        R = self.R
        self.assertInvalid(self.run_obj(R), "single key")                                # review A: top_level_list
        self.assertInvalid(self.run_obj({"matrix": R, "score": "9" * 40}), "single key")  # review A: extra_key
        self.assertInvalid(self.run_obj({"Matrix": R}), "single key")
        for bad in (None, 1, "x", {}, {"0": R[0]}):
            self.assertInvalid(self.run_obj({"matrix": bad}), "exactly 29 rows")
        self.assertInvalid(self.run_mat([]), "exactly 29 rows")
        self.assertInvalid(self.run_mat([r[:23] for r in R[:23]]), "exactly 29 rows")    # review A: matrix_23x23
        self.assertInvalid(self.run_mat(R[:28]), "exactly 29 rows")                      # A: 28_rows, B: wrong_order
        self.assertInvalid(self.run_mat(R + [R[0]]), "exactly 29 rows")                  # review A: matrix_30_rows
        self.assertInvalid(self.run_mat(R[:28] + [R[28][:28]]), "row 28")                # review A: ragged_row
        self.assertInvalid(self.run_mat(R[:28] + [R[28] + [1]]), "row 28")
        self.assertInvalid(self.run_mat(R[:3] + ["+" * N] + R[4:]), "row 3")
        self.assertInvalid(self.run_mat(R[:3] + [None] + R[4:]), "row 3")
        big = [r + [1] for r in R] + [[1] * (N + 1)]
        self.assertInvalid(self.run_mat(big), "exactly 29 rows")

    def test_bad_entries(self):
        # review A: entry_zero, entry_two, entry_true, entry_string at (3,5)
        for bad in (0, 2, -2, True, False, "1", "+", None, [1], {"v": 1}):
            self.assertInvalid(self.run_mat(self.with_entry(bad, 3, 5)), "entry (3,5)")
        # review B: non_sign_entry and boolean_entry at (0,0)
        self.assertInvalid(self.run_mat(self.with_entry(0, 0, 0)), "entry (0,0)")
        self.assertInvalid(self.run_mat(self.with_entry(True, 0, 0)), "entry (0,0)")
        self.assertInvalid(self.run_mat(self.with_entry(10**17, 28, 28)), "entry (28,28)")
        data = json.dumps({"matrix": self.with_entry(7, 0, 0)}).encode()
        self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[-0,", 1)), "entry (0,0)")
        class Sub(int):
            pass
        with self.assertRaises(V.Invalid):
            V.parse_matrix({"matrix": self.with_entry(Sub(1))}, N)
        with self.assertRaises(V.Invalid):
            V.parse_matrix({"matrix": self.with_entry(True)}, N)

    def test_numbers_must_be_plain_ascii_integers(self):
        data = json.dumps({"matrix": self.with_entry(7, 0, 0)}).encode()
        for bad, msg in ((b"1.0", "fractional"), (b"-1.0", "fractional"), (b"1e0", "fractional"),
                         (b"1E0", "fractional"), (b"NaN", "NaN"), (b"Infinity", "NaN"),
                         (b"-Infinity", "NaN"), (b"+1", "valid JSON"), (b"0x1", "valid JSON"),
                         (b"01", "valid JSON"), ("١".encode(), "valid JSON"), ("１".encode(), "valid JSON"),
                         ("-١".encode(), "valid JSON")):
            self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[" + bad + b",", 1)), msg)
        self.assertInvalid(self.run_mat(self.with_entry(1.0, 3, 5)), "fractional")          # review A: entry_float
        base = json.dumps({"matrix": self.R})
        self.assertInvalid(self.run_bytes(base.replace("1", "1e0", 1).encode()), "fractional")   # A: entry_exp
        self.assertInvalid(self.run_bytes(base.replace("-1", "NaN", 1).encode()), "NaN")        # A: entry_nan
        self.assertInvalid(self.run_bytes(b'{"matrix": NaN}'), "NaN")
        self.assertInvalid(self.run_bytes(base.replace("-1", "1" + "0" * 5000, 1).encode()), "digits")  # huge_int
        self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[" + b"1" * 19 + b",", 1)), "digits")

    def test_duplicate_keys(self):
        text = '{"matrix": %s, "matrix": %s}' % (json.dumps(self.R), json.dumps(self.R))   # review A: dup_key
        self.assertInvalid(self.run_bytes(text.encode()), "duplicate keys")
        text = '{"matrix":%s,"\\u006datrix":%s}' % (json.dumps(self.R), json.dumps(self.R))
        self.assertInvalid(self.run_bytes(text.encode()), "duplicate keys")

    # ---------- hostile input

    def test_oversized_file(self):
        limit = self.cfg["max_certificate_bytes"]
        self.assertEqual(limit, 65536)
        self.assertInvalid(self.run_bytes(b" " * (limit + 1)), "size limit")                # review B: oversize
        padded = b'{"matrix": ' + b" " * 70000 + json.dumps(self.R).encode() + b"}"         # review A: oversize
        self.assertInvalid(self.run_bytes(padded), "size limit")
        body = json.dumps({"matrix": self.R}).encode()
        self.assertValid(self.run_bytes(body + b" " * (limit - len(body))), BASELINE)       # exactly at the limit
        self.assertInvalid(self.run_bytes(body + b" " * (limit + 1 - len(body))), "size limit")

    def test_deeply_nested_json(self):
        self.assertInvalid(self.run_bytes(b"[[[[[[[[[0]]]]]]]]]"), "nested")                 # review B: too_deep
        self.assertInvalid(self.run_bytes(b'{"matrix":' + b"[" * 1000 + b"]" * 1000 + b"}"), "nested")  # A: deep_1000
        self.assertInvalid(self.run_bytes(("[" * 30000 + "]" * 30000).encode()), "nested")
        self.assertInvalid(self.run_bytes(("[" * 100000 + "]" * 100000).encode()), "size limit")  # A: deep_nesting
        self.assertInvalid(self.run_bytes(b'{"matrix":[[[[[[[[1]]]]]]]]}'), "nested")
        self.assertInvalid(self.run_bytes(b"[" * 60000), "nested")

    def test_brackets_inside_strings_do_not_count_as_depth(self):
        self.assertInvalid(self.run_bytes(b'{"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\\\": "[[[[[[[[[[[["}'), "single key")

    def test_not_utf8_and_byte_order_mark(self):
        body = json.dumps({"matrix": self.R}).encode()
        self.assertInvalid(self.run_bytes(b"\xff\xfe{}"), "UTF-8")
        self.assertInvalid(self.run_bytes(body.decode().encode("utf-16")), "UTF-8")
        self.assertInvalid(self.run_bytes(b"\xef\xbb\xbf" + body), "valid JSON")               # review A: bom
        self.assertInvalid(self.run_bytes(b'{"matrix": "\xc0\xaf"}'), "UTF-8")
        self.assertInvalid(self.run_bytes(b'{"matrix": "\xed\xa0\x80"}'), "UTF-8")             # encoded surrogate
        self.assertInvalid(self.run_bytes(b'{"\\ud800": 1}'), "single key")

    def test_symlink_fifo_and_directory(self):
        target = self.dir / "real.json"
        target.write_text(json.dumps({"matrix": self.R}))
        os.symlink(target, self.dir / "certificate.json")
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "symbolic links")
        os.unlink(self.dir / "certificate.json")
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.dir / "certificate.json")
            self.assertInvalid(V.verify_dir(self.dir, self.cfg), "regular file")
            os.unlink(self.dir / "certificate.json")
        os.mkdir(self.dir / "certificate.json")
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "regular file")

    def test_messages_never_echo_input_strings(self):
        for data in (b'{"matrix": "<script>alert(1)</script>"}', b'{"<script>alert(1)</script>": 1}',
                     json.dumps({"matrix": self.with_entry("<script>", 2, 3)}).encode()):
            self.assertNotIn("script", self.run_bytes(data)["message"])

    def test_worst_case_input_is_fast(self):
        rng = random.Random(0)
        cases = []
        for m in (random_matrix(rng), self.R, [[1] * N for _ in range(N)]):
            body = json.dumps({"matrix": m}, indent=1).encode()
            cases.append(body + b" " * (self.cfg["max_certificate_bytes"] - len(body)))
        cases.append(b"[" * 8 + b"]" * 8 + b" " * (self.cfg["max_certificate_bytes"] - 16))
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
