"""p011 verifier tests: valid, invalid and hostile inputs. Run with: python3 tools/run_tests.py"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("fewshots_verify_p011", HERE / "verify.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

N = 17
BASELINE = [tuple(c) for c in json.loads((ROOT / "baseline" / "certificate.json").read_text())["comparators"]]

# Valsalam and Miikkulainen, JMLR 14 (2013) 303-331, Figure 17, as printed (channels 1..17)
VM13_FIG17 = [
    (6, 12), (5, 10), (8, 13), (1, 15), (3, 17), (2, 16), (4, 9), (7, 14), (4, 11), (9, 14), (5, 8), (10, 13),
    (1, 3), (15, 17), (2, 7), (11, 16), (4, 6), (12, 14), (1, 5), (13, 17), (2, 4), (14, 16), (1, 2), (16, 17),
    (3, 10), (8, 15), (6, 11), (7, 12), (6, 8), (7, 9), (9, 11), (3, 4), (9, 15), (10, 12), (13, 14), (5, 7),
    (11, 15), (5, 6), (8, 10), (12, 14), (2, 3), (15, 16), (2, 9), (14, 16), (2, 5), (3, 6), (12, 15), (14, 15),
    (3, 5), (7, 13), (10, 13), (4, 11), (4, 9), (7, 8), (11, 13), (4, 7), (4, 5), (13, 14), (11, 12), (6, 7),
    (12, 13), (5, 6), (8, 9), (9, 10), (7, 9), (10, 12), (6, 8), (7, 8), (10, 11), (9, 10), (8, 9),
]
VM13 = [(a - 1, b - 1) for a, b in VM13_FIG17]

# Dobbelaere's table: the 17-input network with 72 comparators and 11 layers
TABLE_72 = [
    (0, 8), (1, 3), (2, 6), (4, 15), (5, 13), (9, 16), (10, 11), (12, 14), (0, 2), (1, 4), (3, 15), (5, 8),
    (6, 14), (7, 9), (13, 16), (2, 13), (3, 11), (5, 10), (6, 9), (7, 12), (8, 15), (14, 16), (0, 7), (1, 5),
    (3, 6), (4, 10), (8, 14), (9, 11), (12, 13), (15, 16), (0, 1), (2, 6), (4, 12), (5, 7), (9, 14), (10, 13),
    (11, 15), (1, 4), (2, 3), (6, 11), (7, 12), (8, 9), (13, 14), (15, 16), (2, 5), (3, 8), (7, 10), (9, 12),
    (11, 13), (14, 15), (1, 2), (3, 7), (4, 5), (6, 9), (8, 10), (13, 14), (3, 4), (5, 7), (6, 8), (9, 11),
    (10, 12), (2, 4), (5, 6), (7, 8), (9, 10), (11, 12), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11), (12, 13),
]

# Dobbelaere's table: Green's 16-input network with 60 comparators (channels 0..15 only)
GREEN_16 = [
    (0, 13), (1, 12), (2, 15), (3, 14), (4, 8), (5, 6), (7, 11), (9, 10), (0, 5), (1, 7), (2, 9), (3, 4),
    (6, 13), (8, 14), (10, 15), (11, 12), (0, 1), (2, 3), (4, 5), (6, 8), (7, 9), (10, 11), (12, 13), (14, 15),
    (0, 2), (1, 3), (4, 10), (5, 11), (6, 7), (8, 9), (12, 14), (13, 15), (1, 2), (3, 12), (4, 6), (5, 7),
    (8, 10), (9, 11), (13, 14), (1, 4), (2, 6), (5, 8), (7, 10), (9, 13), (11, 14), (2, 4), (3, 6), (9, 12),
    (11, 13), (3, 5), (6, 8), (7, 9), (10, 12), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (6, 7), (8, 9),
]

# Review B's best 70-comparator candidate: delete baseline index 8, then set index 10 to [0, 14]
NEAR_70 = BASELINE[:8] + BASELINE[9:]
NEAR_70[10] = (0, 14)

# Review A's best 70-comparator candidate from simulated annealing
ANNEAL_70 = [
    (5, 11), (4, 9), (7, 12), (0, 14), (2, 16), (1, 15), (3, 8), (6, 13), (3, 10), (8, 13), (4, 7), (9, 12),
    (0, 2), (14, 16), (1, 6), (10, 15), (3, 5), (11, 13), (0, 4), (12, 16), (1, 3), (13, 15), (0, 1), (15, 16),
    (2, 9), (7, 14), (5, 10), (6, 11), (5, 7), (6, 8), (8, 10), (2, 3), (8, 14), (9, 11), (12, 13), (4, 6),
    (10, 14), (4, 5), (7, 9), (11, 13), (1, 2), (14, 15), (13, 15), (1, 4), (2, 5), (11, 14), (13, 14), (2, 4),
    (6, 12), (9, 12), (3, 10), (3, 8), (6, 7), (10, 12), (3, 6), (3, 4), (12, 13), (10, 11), (5, 6), (11, 12),
    (4, 5), (7, 8), (8, 9), (6, 8), (9, 11), (5, 7), (6, 7), (9, 10), (8, 9), (7, 8),
]


def cert(pairs) -> bytes:
    return json.dumps({"comparators": [list(c) for c in pairs]}, separators=(",", ":")).encode()


def mirror(pairs):
    return [(N - 1 - b, N - 1 - a) for a, b in pairs]


def bubble():
    return [(j, j + 1) for i in range(N - 1, 0, -1) for j in range(i)]


def insertion():
    return [(j - 1, j) for i in range(1, N) for j in range(i, 0, -1)]


def odd_even_transposition():
    return [(i, i + 1) for r in range(N) for i in range(r % 2, N - 1, 2)]


def run_scalar(pairs, values):
    """Independent reference: compare-exchange on a plain list."""
    v = list(values)
    for a, b in pairs:
        if v[a] > v[b]:
            v[a], v[b] = v[b], v[a]
    return v


def is_sorted(v) -> bool:
    return all(v[i] <= v[i + 1] for i in range(len(v) - 1))


def failing_inputs(pairs) -> list:
    """The 0-1 inputs k (channel i holds bit i of k) that the network does not sort, from the bit simulation."""
    got, want = V.simulate(pairs, N), V.sorted_outputs(N)
    bad = 0
    for g, w in zip(got, want):
        bad |= g ^ w
    return [k for k in range(1 << N) if bad >> k & 1]


def peel_layers(pairs):
    """Independent reference for the layers: repeatedly remove the comparators that no earlier remaining
    comparator touches on either channel (Foata normal form)."""
    out, remaining = [], list(pairs)
    while remaining:
        seen, layer, rest = set(), [], []
        for a, b in remaining:
            (rest if a in seen or b in seen else layer).append([a, b])
            seen.update((a, b))
        out.append(sorted(layer))
        remaining = rest
    return out


def spec_hash(pairs) -> str:
    """canonical_hash computed from the rule in PROBLEM.md, with the reference layers above."""
    best = min(peel_layers(pairs), peel_layers(mirror(pairs)))
    blob = '{"channels":17,"layers":' + json.dumps(best, separators=(",", ":")) + "}"
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def problem_md_hashes() -> list:
    text = (ROOT / "PROBLEM.md").read_text(encoding="utf-8")
    return re.findall(r"`([0-9a-f]{64})`", text.split("## Certificate", 1)[1].split("## Baseline", 1)[0])


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

    def run_pairs(self, pairs) -> dict:
        return self.run_bytes(cert(pairs))

    def assertValid(self, res: dict, score: int):
        self.assertTrue(res["valid"], res)
        self.assertEqual(res["score"], str(score))
        self.assertEqual(res["message"], "ok")
        self.assertRegex(res["canonical_hash"], r"^[0-9a-f]{64}$")

    def assertInvalid(self, res: dict, fragment: str = ""):
        self.assertFalse(res["valid"], res)
        self.assertIsNone(res["score"])
        self.assertIsNone(res["canonical_hash"])
        self.assertIn(fragment, res["message"])

    # ---------- configuration

    def test_config_matches_problem_toml(self):
        self.assertEqual(self.cfg, {"n": 17, "max_comparators": 1000, "max_certificate_bytes": 65536})
        text = (ROOT / "problem.toml").read_text(encoding="utf-8")
        for old, new in (("channels = 17", "channels = 16"), ("max_comparators = 1000", "max_comparators = 1001")):
            path = self.dir / "problem.toml"
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            with self.assertRaises(ValueError):
                V.load_config(path)

    # ---------- valid input

    def test_baseline_reproduces_baseline_score(self):
        with open(ROOT / "problem.toml", "rb") as f:
            baseline = tomllib.load(f)["baseline_score"]
        res = V.verify_dir(ROOT / "baseline", self.cfg)
        self.assertValid(res, 71)
        self.assertEqual(baseline, "71")
        self.assertEqual(len(BASELINE), 71)
        self.assertEqual(len(V.layers(BASELINE, N)), 12)

    def test_baseline_sorts_real_valued_inputs(self):
        rng = random.Random(1)
        for _ in range(3000):
            vals = [rng.randrange(6) for _ in range(N)] if rng.random() < 0.5 else rng.sample(range(1000), N)
            for net in (BASELINE, VM13):
                out = run_scalar(net, vals)
                self.assertTrue(is_sorted(out))
                self.assertEqual(sorted(out), sorted(vals))

    def test_other_published_networks(self):
        self.assertValid(self.run_pairs(VM13), 71)
        self.assertValid(self.run_pairs(TABLE_72), 72)
        self.assertValid(self.run_pairs(mirror(BASELINE)), 71)
        self.assertValid(self.run_pairs(GREEN_16 + [(j - 1, j) for j in range(16, 0, -1)]), 76)

    def test_classic_networks(self):
        self.assertValid(self.run_pairs(bubble()), 136)
        self.assertValid(self.run_pairs(insertion()), 136)
        self.assertValid(self.run_pairs(odd_even_transposition()), 136)
        self.assertValid(self.run_pairs(BASELINE + BASELINE), 142)

    def test_redundant_comparators_are_counted(self):
        self.assertValid(self.run_pairs(BASELINE + [(0, 1)] * 929), 1000)
        self.assertValid(self.run_pairs([(0, 1)] * 929 + BASELINE), 1000)
        for i in range(0, len(BASELINE), 7):
            self.assertValid(self.run_pairs(BASELINE[:i + 1] + BASELINE[i:]), 72)   # duplicated in place
        self.assertValid(self.run_pairs([(3, 9)] + BASELINE), 72)                   # prepended
        self.assertValid(self.run_pairs(BASELINE + [(3, 9)]), 72)                   # appended

    def test_wires_and_targets_match_definition(self):
        wires, want = V.input_wires(N), V.sorted_outputs(N)
        rng = random.Random(2)
        for k in [0, 1, 23, (1 << N) - 1] + [rng.randrange(1 << N) for _ in range(500)]:
            for i in range(N):
                self.assertEqual(wires[i] >> k & 1, k >> i & 1)
            ones = bin(k).count("1")
            for j in range(N):
                self.assertEqual(want[j] >> k & 1, int(j >= N - ones))

    def test_bit_simulation_matches_scalar_reference(self):
        rng = random.Random(4)
        nets = [BASELINE[:-1], NEAR_70, ANNEAL_70, VM13[1:]]
        nets += [[tuple(sorted(rng.sample(range(N), 2))) for _ in range(40)] for _ in range(5)]
        for net in nets:
            bad = set(failing_inputs(net))
            for k in list(bad)[:20] + [rng.randrange(1 << N) for _ in range(200)]:
                vals = [k >> i & 1 for i in range(N)]
                self.assertEqual(not is_sorted(run_scalar(net, vals)), k in bad)

    # ---------- invalid networks (do not sort)

    def test_every_single_deletion_fails(self):
        for src in (BASELINE, VM13):
            for i in range(len(src)):
                self.assertInvalid(self.run_pairs(src[:i] + src[i + 1:]), "does not sort")

    def test_delete_last_has_424_failing_inputs(self):
        bad = failing_inputs(BASELINE[:-1])
        self.assertEqual((len(bad), bad[0]), (424, 23))
        self.assertFalse(is_sorted(run_scalar(BASELINE[:-1], [23 >> i & 1 for i in range(N)])))

    def test_near_miss_70_candidates_fail(self):
        self.assertEqual(len(NEAR_70), 70)
        self.assertEqual(failing_inputs(NEAR_70), [15621, 23813, 26753])
        self.assertInvalid(self.run_pairs(NEAR_70), "does not sort")
        self.assertEqual(len(ANNEAL_70), 70)
        self.assertEqual(len(failing_inputs(ANNEAL_70)), 7)
        self.assertInvalid(self.run_pairs(ANNEAL_70), "does not sort")

    def test_endpoint_mutations_fail(self):
        for i, (a, b) in enumerate(BASELINE):
            for c in ((a - 1, b), (a + 1, b), (a, b - 1), (a, b + 1)):
                if 0 <= c[0] < c[1] < N:
                    self.assertInvalid(self.run_pairs(BASELINE[:i] + [c] + BASELINE[i + 1:]), "does not sort")
                else:
                    self.assertInvalid(self.run_pairs(BASELINE[:i] + [c] + BASELINE[i + 1:]), "0 <= a < b")
            self.assertInvalid(self.run_pairs(BASELINE[:i] + [(b, a)] + BASELINE[i + 1:]), "0 <= a < b")

    def test_unsorting_networks(self):
        self.assertInvalid(self.run_pairs([(0, 1)]), "does not sort")
        self.assertInvalid(self.run_pairs([(0, 16)] * 1000), "does not sort")
        self.assertInvalid(self.run_pairs(BASELINE[::-1]), "does not sort")
        self.assertInvalid(self.run_pairs(sorted(BASELINE)), "does not sort")
        self.assertInvalid(self.run_pairs(GREEN_16), "does not sort")          # channel 16 is never touched

    # ---------- invalid certificates (format and limits)

    def test_rule_violations(self):
        base = [list(c) for c in BASELINE]
        for bad, fragment in (([[-1, 5]], "0 <= a < b"), ([[0, 17]], "0 <= a < b"), ([[3, 3]], "0 <= a < b"),
                              ([[11, 0]], "0 <= a < b"), ([[0, 17 + 2 ** 64]], "digits"),
                              ([[0, 1, 2]], "two integers"), ([[0]], "two integers"), ([[]], "two integers"),
                              ([["0", 11]], "two integers"), ([[False, True]], "two integers"),
                              ([[None, 1]], "two integers"), ([[[0], 1]], "two integers"), ([None], "two integers"),
                              ([1], "two integers"), (["01"], "two integers"), ([{"0": 1, "1": 2}], "two integers")):
            self.assertInvalid(self.run_bytes(json.dumps({"comparators": bad + base}).encode()), fragment)
        self.assertInvalid(self.run_pairs([(a + 1, b + 1) for a, b in VM13]), "0 <= a < b")  # 1-indexed as printed
        self.assertInvalid(self.run_pairs([(a + 1, b + 1) for a, b in BASELINE]), "0 <= a < b")
        self.assertInvalid(self.run_pairs([(b, a) for a, b in BASELINE]), "0 <= a < b")

    def test_wrong_shape(self):
        body = json.dumps([list(c) for c in BASELINE])
        for data in (b"[]", b"{}", b"null", b"true", b"17", b'"ATTACK_SENTINEL"', body.encode(),
                     ('{"comparators":%s,"note":"x"}' % body).encode(), ('{"note":1,"comparators":%s}' % body).encode(),
                     ('{"comparators":%s,"score":0}' % body).encode(), ('{"comparators":%s,"\\ud800":0}' % body).encode(),
                     ('{"comparatorѕ":%s}' % body).encode(), ('{"comparators ":%s}' % body).encode(),
                     ('{"comparators\\u200b":%s}' % body).encode(), ('{"comparators\\u0000":%s}' % body).encode(),
                     b'{"\\ud800":1}', b'{"' + b"A" * 60000 + b'":1}'):
            self.assertInvalid(self.run_bytes(data), "single key")
        for data in (b'{"comparators":null}', b'{"comparators":1}', b'{"comparators":{}}',
                     b'{"comparators":"ATTACK_SENTINEL"}', b'{"comparators":[]}', b'{"comparators":{"0":[0,1]}}'):
            self.assertInvalid(self.run_bytes(data), "non-empty list")

    def test_too_many_comparators(self):
        self.assertInvalid(self.run_pairs(BASELINE + [(0, 1)] * 930), "at most 1000")
        self.assertInvalid(self.run_pairs([(0, 1)] * 100000), "size limit")

    def test_numbers_are_not_accepted(self):
        for tok in (b"0.0", b"11.0", b"1e1", b"0e0", b"1e99999999", b"1.5"):
            self.assertInvalid(self.run_bytes(b'{"comparators":[[0,' + tok + b"]]}"), "fractional or exponent")
        for tok in (b"NaN", b"Infinity", b"-Infinity"):
            self.assertInvalid(self.run_bytes(b'{"comparators":[[0,' + tok + b"]]}"), "NaN and Infinity")
        for digits in (19, 4300, 5000, 60000):
            self.assertInvalid(self.run_bytes(b'{"comparators":[[0,1' + b"0" * (digits - 1) + b"]]}"), "digits")
        for tok in (b"00", b"011", b"+0", "٠".encode(), "０".encode()):
            self.assertInvalid(self.run_bytes(b'{"comparators":[[' + tok + b",1]]}"), "valid JSON")

    def test_duplicate_keys(self):
        body = json.dumps([list(c) for c in BASELINE]).encode()
        self.assertInvalid(self.run_bytes(b'{"comparators":[[0,1]],"comparators":' + body + b"}"), "duplicate keys")
        self.assertInvalid(self.run_bytes(b'{"comparators":' + body + b',"comparators":[[0,1]]}'), "duplicate keys")
        self.assertInvalid(self.run_bytes(b'{"comparators":[],"comparators":' + body + b"}"), "duplicate keys")
        self.assertInvalid(self.run_bytes(b'{"comparators":' + body + b',"\\u0063omparators":[[0,1]]}'),
                           "duplicate keys")

    def test_not_json_or_not_utf8(self):
        good = cert(BASELINE)
        self.assertInvalid(self.run_bytes(b""), "valid JSON")
        self.assertInvalid(self.run_bytes(b"hello"), "valid JSON")
        self.assertInvalid(self.run_bytes(b'__import__("os").system("id")'), "valid JSON")
        self.assertInvalid(self.run_bytes(b"\xef\xbb\xbf" + good), "valid JSON")          # byte order mark
        self.assertInvalid(self.run_bytes(good + b"x"), "valid JSON")
        self.assertInvalid(self.run_bytes(good + b"{}"), "valid JSON")
        self.assertInvalid(self.run_bytes(good + b" // ok"), "valid JSON")
        self.assertInvalid(self.run_bytes(good + b"\x00"), "valid JSON")
        self.assertInvalid(self.run_bytes(good[:-2] + b",]}"), "valid JSON")              # trailing comma
        self.assertInvalid(self.run_bytes(good[:-1] + b",}"), "valid JSON")
        self.assertInvalid(self.run_bytes(b'{\xc2\xa0"comparators":' + good[15:]), "valid JSON")  # NBSP
        self.assertInvalid(self.run_bytes(good.decode().encode("utf-16")), "UTF-8")
        self.assertInvalid(self.run_bytes(b"\xff"), "UTF-8")
        self.assertInvalid(self.run_bytes(good + b"\xff"), "UTF-8")

    def test_oversized_file(self):
        limit = self.cfg["max_certificate_bytes"]
        good = cert(BASELINE)
        self.assertValid(self.run_bytes(good + b" " * (limit - len(good))), 71)
        self.assertInvalid(self.run_bytes(good + b" " * (limit + 1 - len(good))), "size limit")
        self.assertInvalid(self.run_bytes(b" " * (10 * limit)), "size limit")

    def test_deeply_nested_json(self):
        for depth in (9, 500, 32000):
            self.assertInvalid(self.run_bytes(("[" * depth + "]" * depth).encode()), "nested")
            self.assertInvalid(self.run_bytes(('{"comparators":' + "[" * depth + "]" * depth + "}").encode()),
                               "nested")

    def test_missing_file_and_special_files(self):
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "missing")
        target = self.dir / "real.json"
        target.write_bytes(cert(BASELINE))
        os.symlink(target, self.dir / "certificate.json")
        self.assertInvalid(V.verify_dir(self.dir, self.cfg), "symbolic links")
        with tempfile.TemporaryDirectory() as d:
            Path(d, "certificate.json").mkdir()
            self.assertInvalid(V.verify_dir(d, self.cfg), "not a regular file")
        if hasattr(os, "mkfifo"):
            with tempfile.TemporaryDirectory() as d:
                os.mkfifo(Path(d, "certificate.json"))
                self.assertInvalid(V.verify_dir(d, self.cfg), "not a regular file")  # must not block

    def test_messages_never_echo_input_strings(self):
        for data in (b'{"comparators": "<script>alert(1)</script>"}', b'{"<script>alert(1)</script>": 1}',
                     b'{"comparators": [["<script>", 1]]}', b'"<script>alert(1)</script>"'):
            self.assertNotIn("script", self.run_bytes(data)["message"])

    # ---------- determinism and canonical form

    def test_hash_matches_problem_md(self):
        documented = problem_md_hashes()
        example = [(5, 9), (0, 1), (1, 2), (3, 4)]
        blob = b'{"channels":17,"layers":[[[0,1],[3,4],[5,9]],[[1,2]]]}'
        self.assertEqual(V.canonical_hash(V.canonical_form(example, N)), hashlib.sha256(blob).hexdigest())
        self.assertEqual(spec_hash(example), hashlib.sha256(blob).hexdigest())
        base_hash = V.verify_dir(ROOT / "baseline", self.cfg)["canonical_hash"]
        self.assertEqual(spec_hash(BASELINE), base_hash)
        self.assertEqual(documented, [hashlib.sha256(blob).hexdigest(), base_hash])
        # for the baseline the mirror image gives the smaller layers
        self.assertLess(V.layers(mirror(BASELINE), N), V.layers(BASELINE, N))

    def test_layers_match_reference(self):
        rng = random.Random(5)
        nets = [BASELINE, VM13, TABLE_72, bubble(), BASELINE + BASELINE]
        nets += [[tuple(sorted(rng.sample(range(N), 2))) for _ in range(rng.randrange(1, 120))] for _ in range(200)]
        for net in nets:
            self.assertEqual(V.layers(net, N), peel_layers(net))
            self.assertEqual(V.canonical_hash(V.canonical_form(net, N)), spec_hash(net))

    def test_equivalent_certificates_hash_the_same(self):
        ref = self.run_pairs(BASELINE)
        rng = random.Random(3)
        layered = V.layers(BASELINE, N)
        variants = [mirror(BASELINE), [c for layer in layered for c in layer]]
        for _ in range(20):
            shuffled = []
            for layer in layered:
                layer = list(layer)
                rng.shuffle(layer)
                shuffled += [tuple(c) for c in layer]
            variants.append(shuffled)
            variants.append(mirror(shuffled))
        for _ in range(20):  # swap adjacent comparators on disjoint channels
            net = list(BASELINE)
            for _ in range(30):
                i = rng.randrange(len(net) - 1)
                if not set(net[i]) & set(net[i + 1]):
                    net[i], net[i + 1] = net[i + 1], net[i]
            variants.append(net)
        for net in variants:
            res = self.run_pairs(net)
            self.assertEqual((res["valid"], res["score"], res["canonical_hash"]),
                             (True, "71", ref["canonical_hash"]))
        body = json.dumps({"comparators": [list(c) for c in BASELINE]}, indent=3)
        compact = cert(BASELINE).decode()
        self.assertIn("[0,", compact)
        for text in (body, body.replace("\n", "\r\n") + "\n\n", compact.replace("[0,", "[-0,"),
                     compact.replace('"comparators"', '"\\u0063omparators"', 1)):
            res = self.run_bytes(text.encode())
            self.assertEqual((res["score"], res["canonical_hash"]), ("71", ref["canonical_hash"]))

    def test_distinct_networks_distinct_hashes(self):
        nets = (BASELINE, VM13, TABLE_72, BASELINE + [(0, 1)], [(0, 1)] + BASELINE, BASELINE + BASELINE,
                bubble(), odd_even_transposition())
        hashes = {self.run_pairs(n)["canonical_hash"] for n in nets}
        self.assertEqual(len(hashes), len(nets))
        # bubble sort and insertion sort networks have the same layers, so they are one network here
        self.assertEqual(V.layers(bubble(), N), V.layers(insertion(), N))
        self.assertEqual(self.run_pairs(bubble())["canonical_hash"], self.run_pairs(insertion())["canonical_hash"])

    def test_same_certificate_twice(self):
        for net in (BASELINE, VM13, NEAR_70):
            self.assertEqual(self.run_pairs(net), self.run_pairs(net))

    # ---------- command-line contract

    def run_cli(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(HERE / "verify.py"), *args],
                              capture_output=True, timeout=60)

    def test_cli_prints_exactly_one_json_line(self):
        (self.dir / "certificate.json").write_bytes(cert(BASELINE))
        first = self.run_cli(str(self.dir))
        self.assertEqual(first.returncode, 0)
        lines = first.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        obj = json.loads(lines[0])
        self.assertEqual(set(obj), {"valid", "score", "canonical_hash", "message"})
        self.assertEqual(obj["score"], "71")
        self.assertEqual(self.run_cli(str(self.dir)).stdout, first.stdout)  # deterministic across processes
        (self.dir / "certificate.json").write_text("[" * 100000)
        proc = self.run_cli(str(self.dir))
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(json.loads(proc.stdout)["valid"])
        self.assertEqual(proc.stderr, b"")

    def test_cli_usage_error(self):
        for args in ((), ("a", "b")):
            proc = self.run_cli(*args)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(len(proc.stdout.decode().splitlines()), 1)
            self.assertFalse(json.loads(proc.stdout)["valid"])

    def test_worst_case_time(self):
        limit = self.cfg["max_certificate_bytes"]
        for net in (BASELINE + [(0, 1)] * 929, [(0, 16)] * 1000):
            data = cert(net)
            (self.dir / "certificate.json").write_bytes(data + b" " * (limit - len(data)))
            t = time.perf_counter()
            proc = self.run_cli(str(self.dir))
            self.assertLess(time.perf_counter() - t, 5.0)
            self.assertEqual(proc.returncode, 0)

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
                                   "system", "popen"})


if __name__ == "__main__":
    unittest.main()
