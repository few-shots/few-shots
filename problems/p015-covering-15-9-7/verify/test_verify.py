"""Covering-design regression, format, resource-limit and verifier-contract tests."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import tomllib
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC = importlib.util.spec_from_file_location("covering_verify", HERE / "verify.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
BASELINE_BYTES = (ROOT / "baseline/certificate.json").read_bytes()
BASELINE = json.loads(BASELINE_BYTES)["blocks"]
BASELINE_HASH = "39be9ce649e502ff86438406c8d31428c9ab3b601a79122b3c4d50d1ab2c2e13"


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_bytes(self, data):
        (self.directory / "certificate.json").write_bytes(data)
        return V.verify_dir(self.directory)

    def run_text(self, text):
        return self.run_bytes(text.encode("utf-8"))

    def run_blocks(self, blocks):
        return self.run_text(json.dumps({"blocks": blocks}, separators=(",", ":")))

    def assertInvalid(self, result, fragment=""):
        self.assertEqual(set(result), {"valid", "score", "canonical_hash", "message"})
        self.assertIs(result["valid"], False, result)
        self.assertIsNone(result["score"])
        self.assertIsNone(result["canonical_hash"])
        self.assertIn(fragment, result["message"])

    def assertValid(self, result, score, expected_hash=None):
        self.assertEqual(set(result), {"valid", "score", "canonical_hash", "message"})
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["score"], str(score))
        self.assertEqual(result["message"], "ok")
        self.assertRegex(result["canonical_hash"], r"^[0-9a-f]{64}$")
        if expected_hash is not None:
            self.assertEqual(result["canonical_hash"], expected_hash)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(HERE / "verify.py"), *args],
                              capture_output=True, timeout=5)

    def test_baseline_matches_metadata_and_published_hash(self):
        with (ROOT / "problem.toml").open("rb") as stream:
            config = tomllib.load(stream)
        self.assertEqual(config["baseline_score"], "270")
        self.assertEqual(config["epsilon"], "1")
        self.assertEqual(config["epsilon_mode"], "absolute")
        self.assertValid(V.verify_dir(ROOT / "baseline"), config["baseline_score"], BASELINE_HASH)
        self.assertEqual(len(BASELINE_BYTES), 6214)
        self.assertEqual(hashlib.sha256(BASELINE_BYTES).hexdigest(),
                         "0dec6b959f6bfceddb99b5f35a83bfc97f7ffd94709f68383bde9b70b7eeacad")

    def test_verifier_limits_match_metadata(self):
        with (ROOT / "problem.toml").open("rb") as stream:
            config = tomllib.load(stream)
        self.assertEqual(config["max_certificate_bytes"], V.MAX_BYTES)
        for key, constant in (("points", V.POINTS), ("block_size", V.BLOCK_SIZE),
                              ("cover_size", V.COVER_SIZE), ("max_blocks", V.MAX_BLOCKS),
                              ("max_depth", V.MAX_DEPTH), ("max_int_digits", V.MAX_INT_DIGITS)):
            self.assertEqual(config["params"][key], constant, key)

    def test_equivalent_orders_whitespace_and_escaped_key(self):
        blocks = [list(reversed(b)) for b in reversed(BASELINE)]
        self.assertValid(self.run_blocks(blocks), 270, BASELINE_HASH)
        rng = random.Random(23056)
        rng.shuffle(blocks)
        for block in blocks:
            rng.shuffle(block)
        text = json.dumps({"blocks": blocks}, indent=2)
        self.assertValid(self.run_text(text), 270, BASELINE_HASH)
        self.assertValid(self.run_bytes(BASELINE_BYTES.replace(b'"blocks"', b'"bl\\u006fcks"')),
                         270, BASELINE_HASH)

    def test_canonical_bytes_follow_the_documented_contract(self):
        # Specify the bytes independently, including the fixed key order and parameters.
        sorted_blocks = sorted(sorted(b) for b in BASELINE)
        block_bytes = json.dumps(sorted_blocks, separators=(",", ":")).encode("ascii")
        canonical = (b'{"block_size":9,"blocks":' + block_bytes
                     + b',"cover_size":7,"points":15}')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), BASELINE_HASH)
        obj = {"points": 15, "cover_size": 7, "blocks": sorted_blocks, "block_size": 9}
        # The input has only one key; key-order invariance applies to this canonical object.
        for order in itertools.permutations(obj):
            self.assertEqual(V.canonical_hash({key: obj[key] for key in order}), BASELINE_HASH)

    def test_point_relabeling_is_not_quotiented(self):
        blocks = [[(p + 1) % 15 for p in b] for b in BASELINE]
        result = self.run_blocks(blocks)
        self.assertValid(result, 270)
        self.assertNotEqual(result["canonical_hash"], BASELINE_HASH)

    def test_repeated_block_is_counted_and_retained(self):
        blocks = BASELINE + [BASELINE[0]]
        result = self.run_blocks(blocks)
        self.assertValid(result, 271)
        self.assertNotEqual(result["canonical_hash"], BASELINE_HASH)
        self.assertValid(self.run_blocks([list(reversed(b)) for b in reversed(blocks)]),
                         271, result["canonical_hash"])

    def test_delete_first_block_loses_coverage(self):
        self.assertInvalid(self.run_blocks(BASELINE[1:]), "13 of the 6435")

    def test_many_blocks_do_not_replace_actual_coverage(self):
        self.assertInvalid(self.run_blocks([BASELINE[0]] * V.MAX_BLOCKS), "incomplete")

    def test_maximum_block_count_is_accepted_and_next_is_rejected(self):
        blocks = BASELINE + [BASELINE[0]] * (V.MAX_BLOCKS - len(BASELINE))
        self.assertValid(self.run_blocks(blocks), V.MAX_BLOCKS)
        self.assertInvalid(self.run_blocks(blocks + [BASELINE[0]]), "at most 1000")

    def test_exact_size_limit_and_one_byte_over(self):
        padded = BASELINE_BYTES + b" " * (V.MAX_BYTES - len(BASELINE_BYTES))
        self.assertEqual(len(padded), V.MAX_BYTES)
        self.assertValid(self.run_bytes(padded), 270, BASELINE_HASH)
        self.assertInvalid(self.run_bytes(padded + b" "), "size limit")
        self.assertInvalid(self.run_bytes(b" " * (V.MAX_BYTES + 1)), "size limit")

    def test_empty_or_non_array_blocks(self):
        for raw in ([], {}, "", None, 0, True):
            with self.subTest(raw=raw):
                self.assertInvalid(self.run_text(json.dumps({"blocks": raw})), "non-empty list")

    def test_wrong_top_level_and_unknown_keys(self):
        for obj in ([], None, True, "blocks", 7, {},
                    {"blocks": BASELINE, "points": 15}, {"blocks": BASELINE, "note": "x"}):
            with self.subTest(kind=type(obj).__name__):
                self.assertInvalid(self.run_text(json.dumps(obj)), "single key")

    def test_wrong_block_shape(self):
        for bad in (BASELINE[0][:-1], BASELINE[0] + [14], None, {}, "012345678", 9):
            with self.subTest(bad=bad):
                self.assertInvalid(self.run_blocks([bad] + BASELINE[1:]), "list of 9")

    def test_repeated_point_within_block(self):
        block = BASELINE[0][1:] + [BASELINE[0][1]]
        self.assertInvalid(self.run_blocks([block] + BASELINE[1:]), "distinct")

    def test_out_of_range_points(self):
        for bad in (-1, 15, 999999999999999999, -999999999999999999):
            with self.subTest(bad=bad):
                self.assertInvalid(self.run_blocks([[bad] + BASELINE[0][1:]] + BASELINE[1:]),
                                   "0 <= point <= 14")

    def test_non_integer_points_including_boolean_review_case(self):
        for bad in (False, True, "0", None, [], {}):
            with self.subTest(bad=bad):
                self.assertInvalid(self.run_blocks([[bad] + BASELINE[0][1:]] + BASELINE[1:]),
                                   "must be an integer")

    def test_fraction_exponent_nan_and_infinity(self):
        for bad in ("0.0", "1.5", "0e0", "1e999999", "-0.0", "NaN", "Infinity", "-Infinity"):
            with self.subTest(bad=bad):
                self.assertInvalid(self.run_text('{"blocks":[[' + bad + ',1,2,3,4,5,6,7,8]]}'))

    def test_integer_token_digit_limit(self):
        for bad in ("9" * 19, "-" + "9" * 19, "9" * 5000):
            with self.subTest(length=len(bad)):
                self.assertInvalid(self.run_text('{"blocks":[[' + bad + ',1,2,3,4,5,6,7,8]]}'),
                                   "more than 18 digits")

    def test_duplicate_keys_including_escaped_alias(self):
        for key in ('"blocks"', '"bl\\u006fcks"'):
            self.assertInvalid(self.run_text('{"blocks":[],' + key + ':'
                                            + json.dumps(BASELINE) + '}'), "duplicate keys")

    def test_depth_limit_and_brackets_inside_strings(self):
        V.strict_json(b"[" * 8 + b"]" * 8)
        for depth in (9, 50, 30000):
            with self.subTest(depth=depth):
                self.assertInvalid(self.run_bytes(b"[" * depth + b"]" * depth), "deeper than 8")
        result = self.run_text(json.dumps({"blocks": BASELINE, "extra": '[{\\"' * 100}))
        self.assertInvalid(result, "single key")

    def test_empty_truncated_or_invalid_json(self):
        for text in ("", "{", '{"blocks":[', "{'blocks':[]}", "{}{}", "{} trailing", "\x00",
                     '__import__("os").system("id")'):
            with self.subTest(text=text):
                self.assertInvalid(self.run_text(text), "not valid JSON")

    def test_utf8_and_byte_order_mark(self):
        self.assertInvalid(self.run_bytes(b"\xff\xfe{}"), "UTF-8")
        self.assertInvalid(self.run_bytes(b"\xef\xbb\xbf" + BASELINE_BYTES), "not valid JSON")

    def test_missing_certificate(self):
        self.assertInvalid(V.verify_dir(self.directory), "missing")
        self.assertInvalid(V.verify_dir(self.directory / "absent"), "missing")

    def test_symlink_directory_and_fifo_are_rejected(self):
        target = self.directory / "real.json"
        target.write_bytes(BASELINE_BYTES)
        cert = self.directory / "certificate.json"
        cert.symlink_to(target)
        self.assertInvalid(V.verify_dir(self.directory), "symbolic links")
        cert.unlink()
        cert.mkdir()
        self.assertInvalid(V.verify_dir(self.directory), "not a regular file")
        cert.rmdir()
        os.mkfifo(cert)
        process = self.cli(str(self.directory))
        self.assertEqual(process.returncode, 0)
        self.assertInvalid(json.loads(process.stdout), "not a regular file")
        self.assertEqual(process.stderr, b"")

    def test_errors_do_not_echo_input(self):
        marker = "<script>untrusted-payload</script>"
        for obj in ({"blocks": BASELINE, marker: 1}, {"blocks": [[marker] * 9]}):
            result = self.run_text(json.dumps(obj))
            self.assertInvalid(result)
            self.assertNotIn(marker, json.dumps(result))

    def test_cli_one_line_contract_and_determinism(self):
        self.run_bytes(BASELINE_BYTES)
        a, b = self.cli(str(self.directory)), self.cli(str(self.directory))
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(a.returncode, 0)
        self.assertEqual(b.returncode, 0)
        self.assertEqual(a.stderr + b.stderr, b"")
        self.assertEqual(len(a.stdout.splitlines()), 1)
        self.assertValid(json.loads(a.stdout), 270, BASELINE_HASH)
        self.run_text('{"blocks":[')
        bad = self.cli(str(self.directory))
        self.assertEqual(bad.returncode, 0)
        self.assertEqual(len(bad.stdout.splitlines()), 1)
        self.assertEqual(bad.stderr, b"")
        self.assertInvalid(json.loads(bad.stdout))

    def test_cli_usage(self):
        for args in ((), (str(self.directory), "extra")):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, b"")
            self.assertEqual(len(result.stdout.splitlines()), 1)
            self.assertInvalid(json.loads(result.stdout), "usage")

    def test_verifier_uses_only_allowed_standard_library_and_no_execution(self):
        tree = ast.parse((HERE / "verify.py").read_text())
        imported, called = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                called.add(node.func.id if isinstance(node.func, ast.Name)
                           else getattr(node.func, "attr", ""))
        self.assertLessEqual(imported, {"__future__", "hashlib", "itertools", "json", "os",
                                        "stat", "sys", "fractions", "pathlib"})
        self.assertFalse(called & {"eval", "exec", "compile", "__import__", "literal_eval",
                                   "system", "popen"})


if __name__ == "__main__":
    unittest.main()
