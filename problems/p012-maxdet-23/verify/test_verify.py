"""p012 verifier tests: valid, invalid and hostile inputs. Run with: python3 tools/run_tests.py"""

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
_spec = importlib.util.spec_from_file_location("fewshots_verify_p012", HERE / "verify.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

N = 23
BASELINE = "2779447296000000"
BASELINE_HASH = "1ce81e628d6dc36c015673ac9b8dbb911b6f7d6fa4c04d5af35bef38cc942075"


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

    def assertValid(self, res: dict, score: int | None = None):
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
        self.assertEqual(int(BASELINE), 662671875 * 2**22)
        self.assertEqual(662671875, 3 * 67 * 211 * 5**6)
        # the matrix printed on the source page has determinant -|det|
        self.assertEqual(V.bareiss_det(self.R), -int(BASELINE))
        self.assertEqual(ref_det(self.R), -int(BASELINE))

    def test_baseline_gram_matrix(self):
        # the source page prints M = R R^T = R^T R: 23 on the diagonal, 3 or -1 elsewhere
        rrt = [[sum(a * b for a, b in zip(r, s)) for s in self.R] for r in self.R]
        cols = [list(c) for c in zip(*self.R)]
        rtr = [[sum(a * b for a, b in zip(r, s)) for s in cols] for r in cols]
        self.assertEqual(rrt, rtr)
        self.assertTrue(all(rrt[i][i] == N for i in range(N)))
        self.assertTrue(all(rrt[i][j] in (3, -1) for i in range(N) for j in range(N) if i != j))
        self.assertEqual(ref_det(rrt), int(BASELINE) ** 2)

    def test_epsilon_is_the_determinant_step(self):
        with open(ROOT / "problem.toml", "rb") as f:
            meta = tomllib.load(f)
        self.assertEqual(meta["epsilon"], str(2 ** (N - 1)))
        self.assertEqual(meta["epsilon_mode"], "absolute")
        self.assertEqual(meta["direction"], "max")
        self.assertEqual(meta["params"]["order"], N)
        self.assertEqual(int(BASELINE) % 2 ** (N - 1), 0)

    def test_baseline_below_ehlich_bound(self):
        # det(MM^T) <= (n-3)^(n-6) * prod(n-3+4r) * (1 - sum r/(n-3+4r)), partition (4,4,4,4,4,3)
        parts = (4, 4, 4, 4, 4, 3)
        e2 = Fraction(N - 3) ** (N - len(parts))
        for r in parts:
            e2 *= N - 3 + 4 * r
        e2 *= 1 - sum(Fraction(r, N - 3 + 4 * r) for r in parts)
        c = 2**22 * 3 * 5**6 * 675
        self.assertEqual(e2, c * c * 505)
        self.assertLess(int(BASELINE) ** 2, e2)
        self.assertLess((711034613 * 2**22) ** 2, e2)
        self.assertGreater((711034614 * 2**22) ** 2, e2)

    def test_config_rejects_other_orders(self):
        text = (ROOT / "problem.toml").read_text(encoding="utf-8")
        for bad in ("order = 22", 'order = "23"', "order = 23.0"):
            p = self.dir / "problem.toml"
            p.write_text(text.replace("order = 23", bad, 1), encoding="utf-8")
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
        self.assertEqual(V.bareiss_det([[0, 0], [0, 1]]), 0)
        self.assertEqual(V.bareiss_det([[1, 1], [1, 1]]), 0)

    def test_score_matches_reference_on_random_matrices(self):
        rng = random.Random(23)
        for _ in range(30):
            m = random_matrix(rng)
            res = self.run_mat(m)
            self.assertValid(res, abs(ref_det(m)))
            self.assertEqual(res["canonical_hash"], ref_hash(m))

    def test_score_on_singular_and_near_singular_matrices(self):
        rng = random.Random(7)
        for _ in range(10):
            m = random_matrix(rng)
            i, j = rng.sample(range(N), 2)
            m[j] = m[i][:] if rng.random() < 0.5 else [-x for x in m[i]]   # equal or opposite rows
            self.assertValid(self.run_mat(m), 0)
            # change one entry of the repeated row: rank N - 1 or N, compare with the reference
            m[j][rng.randrange(N)] *= -1
            self.assertValid(self.run_mat(m), abs(ref_det(m)))
        # review cases: all-ones matrix and the baseline with its first row repeated
        self.assertValid(self.run_mat([[1] * N for _ in range(N)]), 0)
        self.assertValid(self.run_mat([self.R[0]] + self.R[:22]), 0)

    def test_known_small_order_values(self):
        # maximal |det| of +-1 matrices of order 1..8 (OEIS A003433), reached by known matrices
        h2 = [[1, 1], [1, -1]]
        h4 = [[a * b for a in r1 for b in r2] for r1 in h2 for r2 in h2]
        h8 = [[a * b for a in r1 for b in r2] for r1 in h4 for r2 in h2]
        self.assertEqual(abs(V.bareiss_det(h4)), 16)
        self.assertEqual(abs(V.bareiss_det(h8)), 4096)
        self.assertEqual(abs(V.bareiss_det([[1, 1, 1], [1, -1, 1], [1, 1, -1]])), 4)

    def test_determinant_is_a_multiple_of_2_to_the_22(self):
        rng = random.Random(22)
        for _ in range(20):
            self.assertEqual(V.bareiss_det(random_matrix(rng)) % 2 ** (N - 1), 0)

    # ---------- canonical form and hash

    def test_row_permutations_and_negations_keep_the_hash(self):
        ref = self.run_mat(self.R)
        rng = random.Random(3)
        swapped = [self.R[1], self.R[0]] + self.R[2:]                       # review B: row_swap
        negated = [[-x for x in r] if i == 5 else r for i, r in enumerate(self.R)]  # review A: one_row_negated
        everything = [[-x for x in r] for r in self.R]                        # global sign
        shuffled = [[s * x for x in r] for r, s in
                    zip(rng.sample(self.R, N), (rng.choice((-1, 1)) for _ in range(N)))]
        for m in (swapped, negated, everything, shuffled):
            res = self.run_mat(m)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], ref["canonical_hash"])

    def test_column_operations_and_transpose_keep_the_score(self):
        # review A: row_col_permuted and transposed. Same score; the hash follows the stated canonical form,
        # which does not identify column operations or transposition.
        rng = random.Random(1)
        rows, cols = list(range(N)), list(range(N))
        rng.shuffle(rows)
        rng.shuffle(cols)
        permuted = [[self.R[i][j] for j in cols] for i in rows]
        transposed = [list(c) for c in zip(*self.R)]
        colneg = [[-x if j == 4 else x for j, x in enumerate(r)] for r in self.R]
        for m in (permuted, transposed, colneg):
            res = self.run_mat(m)
            self.assertValid(res, BASELINE)
            self.assertEqual(res["canonical_hash"], ref_hash(m))
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

    # ---------- invalid certificates (both reviews' adversarial cases included)

    def test_missing_empty_and_malformed(self):
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "missing")
        self.assertInvalid(self.run_bytes(b""), "valid JSON")                 # empty file
        self.assertInvalid(self.run_bytes(b"{}"), "single key")               # empty object
        self.assertInvalid(self.run_bytes(b"{matrix: 1}"), "valid JSON")      # review A: not_json
        self.assertInvalid(self.run_bytes(b'{"matrix":'), "valid JSON")       # review B: bad_malformed
        self.assertInvalid(self.run_bytes(b'__import__("os").system("id")'), "valid JSON")

    def test_wrong_shape(self):
        R = self.R
        self.assertInvalid(self.run_obj(R), "single key")
        self.assertInvalid(self.run_obj({"matrix": R, "x": 1}), "single key")   # review A: extra_key
        self.assertInvalid(self.run_obj({"Matrix": R}), "single key")
        for bad in (None, 1, "x", {}, {"0": R[0]}):
            self.assertInvalid(self.run_obj({"matrix": bad}), "exactly 23 rows")
        self.assertInvalid(self.run_mat([]), "exactly 23 rows")
        self.assertInvalid(self.run_mat([r[:22] for r in R[:22]]), "exactly 23 rows")  # review A: wrong_order_22
        self.assertInvalid(self.run_mat(R + [R[0]]), "exactly 23 rows")
        self.assertInvalid(self.run_mat(R[:22] + [R[22][:22]]), "row 22")              # review A: ragged
        self.assertInvalid(self.run_mat(R[:22] + [R[22] + [1]]), "row 22")
        self.assertInvalid(self.run_mat(R[:3] + ["+" * N] + R[4:]), "row 3")
        self.assertInvalid(self.run_mat(R[:3] + [None] + R[4:]), "row 3")
        big = [r + [1] for r in R] + [[1] * (N + 1)]
        self.assertInvalid(self.run_mat(big), "exactly 23 rows")

    def test_bad_entries(self):
        for bad in (0, 2, -2, True, False, "1", "+", None, [1], {"v": 1}):     # review A/B: zero, two, bool, string
            self.assertInvalid(self.run_mat(self.with_entry(bad, 4, 7)), "entry (4,7)")
        self.assertInvalid(self.run_mat(self.with_entry(10**17, 22, 22)), "entry (22,22)")
        data = json.dumps({"matrix": self.with_entry(7, 0, 0)}).encode()
        self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[-0,", 1)), "entry (0,0)")
        # int subclasses never come out of the JSON parser, but are rejected all the same
        class Sub(int):
            pass
        with self.assertRaises(V.Invalid):
            V.parse_matrix({"matrix": self.with_entry(Sub(1))}, N)
        with self.assertRaises(V.Invalid):
            V.parse_matrix({"matrix": self.with_entry(True)}, N)

    def test_numbers_must_be_plain_integers(self):
        data = json.dumps({"matrix": self.with_entry(7, 0, 0)}).encode()
        for bad, msg in ((b"1.0", "fractional"), (b"-1.0", "fractional"), (b"1e0", "fractional"),
                         (b"1E0", "fractional"), (b"NaN", "NaN"), (b"Infinity", "NaN"),
                         (b"-Infinity", "NaN"), (b"+1", "valid JSON"), (b"0x1", "valid JSON")):
            self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[" + bad + b",", 1)), msg)
        self.assertInvalid(self.run_bytes(b'{"matrix": NaN}'), "NaN")               # review A: nan
        self.assertInvalid(self.run_bytes(data.replace(b"[[7,", b"[[" + b"1" * 80 + b",", 1)), "digits")  # huge_int

    def test_duplicate_keys(self):
        text = '{"matrix":%s,"matrix":%s}' % (json.dumps(self.R), json.dumps(self.R))   # review A: dup_key
        self.assertInvalid(self.run_bytes(text.encode()), "duplicate keys")
        text = '{"matrix":%s,"\\u006datrix":%s}' % (json.dumps(self.R), json.dumps(self.R))
        self.assertInvalid(self.run_bytes(text.encode()), "duplicate keys")

    # ---------- hostile input

    def test_oversized_file(self):
        limit = self.cfg["max_certificate_bytes"]
        self.assertEqual(limit, 65536)
        self.assertInvalid(self.run_bytes(b" " * (limit + 1)), "size limit")         # review B: bad_size
        padded = b" " * (1024 * 1024 + 10) + json.dumps({"matrix": self.R}).encode()  # review A: too_big
        self.assertInvalid(self.run_bytes(padded), "size limit")
        # exactly at the limit is still read
        body = json.dumps({"matrix": self.R}).encode()
        self.assertValid(self.run_bytes(body + b" " * (limit - len(body))), BASELINE)

    def test_deeply_nested_json(self):
        for depth in (9, 30000):                                                    # review B: bad_depth
            self.assertInvalid(self.run_bytes(("[" * depth + "]" * depth).encode()), "nested")
        # review A: deep (100000 levels, 200000 bytes) is stopped by the size limit first
        self.assertInvalid(self.run_bytes(("[" * 100000 + "]" * 100000).encode()), "size limit")
        self.assertInvalid(self.run_bytes(b'{"matrix":[[[[[[[[1]]]]]]]]}'), "nested")

    def test_brackets_inside_strings_do_not_count_as_depth(self):
        self.assertInvalid(self.run_bytes(b'{"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\"[[[[[[[[[[[[": 1}'), "single key")
        self.assertInvalid(self.run_bytes(b'{"\\\\": "[[[[[[[[[[[["}'), "single key")

    def test_not_utf8_and_byte_order_mark(self):
        body = json.dumps({"matrix": self.R}).encode()
        self.assertInvalid(self.run_bytes(b"\xff\xfe{}"), "UTF-8")
        self.assertInvalid(self.run_bytes(body.decode().encode("utf-16")), "UTF-8")
        self.assertInvalid(self.run_bytes(b"\xef\xbb\xbf" + body), "valid JSON")
        self.assertInvalid(self.run_bytes(b'{"matrix": "\xc0\xaf"}'), "UTF-8")

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
        body = json.dumps({"matrix": random_matrix(rng)}, indent=1).encode()
        data = body + b" " * (self.cfg["max_certificate_bytes"] - len(body))
        start = time.perf_counter()
        for _ in range(5):
            self.assertTrue(self.run_bytes(data)["valid"])
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
