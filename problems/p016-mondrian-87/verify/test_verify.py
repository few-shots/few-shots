"""Regression tests for the p016 certificate contract and review counterexamples."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("mondrian_verify", HERE / "verify.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)
BASELINE = json.loads((ROOT / "baseline/certificate.json").read_text())
# Independently rebuilt from the public grid, transforming all rectangle corners.
BASELINE_HASH = "9e35bae916e1f9877a693fae4d02bc2707ba790fd314b0886efc3ba857f9174b"
BANDS = {"rectangles": [[0, 0, 87, 43], [0, 43, 87, 44]]}


def symmetry_images(rectangles):
    """Independent corner-based transformations, not verifier helper calls."""
    for swap in (False, True):
        for flip_x in (False, True):
            for flip_y in (False, True):
                out = []
                for x, y, w, h in rectangles:
                    points = []
                    for a, b in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
                        if swap:
                            a, b = b, a
                        points.append((87 - a if flip_x else a, 87 - b if flip_y else b))
                    xs, ys = zip(*points)
                    out.append([min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)])
                yield out


class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = V.load_config(ROOT / "problem.toml")
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_bytes(self, raw):
        (self.directory / "certificate.json").write_bytes(raw)
        return V.verify_dir(self.directory, self.cfg)

    def run_object(self, obj):
        return self.run_bytes(json.dumps(obj).encode("utf-8"))

    def assertInvalid(self, result, fragment=""):
        self.assertEqual(set(result), {"valid", "score", "canonical_hash", "message"})
        self.assertIs(result["valid"], False)
        self.assertIsNone(result["score"])
        self.assertIsNone(result["canonical_hash"])
        self.assertIn(fragment, result["message"])

    def test_baseline_reproduces_public_score_and_hash(self):
        result = V.verify_dir(ROOT / "baseline", self.cfg)
        with open(ROOT / "problem.toml", "rb") as handle:
            metadata = tomllib.load(handle)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["score"], metadata["baseline_score"])
        self.assertEqual(result["score"], "22")
        self.assertEqual(result["canonical_hash"], BASELINE_HASH)
        self.assertEqual(self.cfg["n"], 87)
        self.assertEqual(self.cfg["max_rectangles"], 1000)
        self.assertEqual(self.cfg["max_certificate_bytes"], 1048576)

    def test_all_eight_symmetries_and_rectangle_order(self):
        images = list(symmetry_images(BASELINE["rectangles"]))
        self.assertEqual(len({json.dumps(sorted(img)) for img in images}), 8)
        for image in images:
            for rects in (image, list(reversed(image))):
                with self.subTest(rects=rects[0]):
                    result = self.run_object({"rectangles": rects})
                    self.assertTrue(result["valid"], result)
                    self.assertEqual(result["score"], "22")
                    self.assertEqual(result["canonical_hash"], BASELINE_HASH)

    def test_key_spelling_whitespace_and_integer_normalization(self):
        # There is only one allowed key, so key-order permutations are identical.
        raw = json.dumps(BASELINE, indent=3).replace('"rectangles"', '"rect\\u0061ngles"')
        raw = raw.replace("[\n      0,", "[\n      -0,", 1)
        result = self.run_bytes(raw.encode())
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["canonical_hash"], BASELINE_HASH)
        self.assertEqual(result, self.run_bytes(raw.encode()))

    def test_valid_but_worse_two_bands_and_distinct_hash(self):
        first = self.run_object(BANDS)
        self.assertTrue(first["valid"], first)
        self.assertEqual(first["score"], "87")
        self.assertNotEqual(first["canonical_hash"], BASELINE_HASH)
        for image in symmetry_images(BANDS["rectangles"]):
            result = self.run_object({"rectangles": image})
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["score"], "87")
            self.assertEqual(result["canonical_hash"], first["canonical_hash"])

    def test_equal_areas_of_different_shapes_are_allowed(self):
        areas = [w * h for x, y, w, h in BASELINE["rectangles"]]
        self.assertLess(len(set(areas)), len(areas))
        self.assertTrue(self.run_object(BASELINE)["valid"])

    def test_empty_or_single_rectangle(self):
        for rects in ([], [[0, 0, 87, 87]]):
            self.assertInvalid(self.run_object({"rectangles": rects}), "at least two")

    def test_congruent_strips_and_rotated_congruence(self):
        strips = {"rectangles": [[0, 0, 87, 29], [0, 29, 87, 29], [0, 58, 87, 29]]}
        self.assertInvalid(self.run_object(strips), "congruent")
        cert = copy.deepcopy(BASELINE)
        # Both affected shapes have area 572; replace 13x44 by a rotated 22x26.
        index = cert["rectangles"].index([28, 29, 13, 44])
        cert["rectangles"][index] = [28, 29, 26, 22]
        self.assertInvalid(self.run_object(cert), "congruent")

    def test_area_correct_overlap_and_gap_from_both_reviews(self):
        bands = copy.deepcopy(BANDS)
        bands["rectangles"][1][1] = 42
        self.assertInvalid(self.run_object(bands), "overlap")
        cert = copy.deepcopy(BASELINE)
        cert["rectangles"][0][0] = 1
        self.assertInvalid(self.run_object(cert), "overlap")

    def test_incomplete_cover_and_wrong_area(self):
        for height in (42, 44):
            cert = copy.deepcopy(BANDS)
            cert["rectangles"][0][3] = height
            self.assertInvalid(self.run_object(cert), "square area")

    def test_coordinate_and_side_bounds(self):
        for index, value in ((0, -1), (1, -1), (0, 1), (1, 88), (2, 0),
                             (3, 0), (2, -1), (3, -1), (2, 88), (3, 88)):
            with self.subTest(index=index, value=value):
                cert = copy.deepcopy(BANDS)
                cert["rectangles"][0][index] = value
                self.assertInvalid(self.run_object(cert))

    def test_boolean_coordinates_from_both_reviews(self):
        for original in (BANDS, BASELINE):
            cert = copy.deepcopy(original)
            cert["rectangles"][0][0] = False
            self.assertInvalid(self.run_object(cert), "integer")

    def test_invalid_schema_and_wrong_arity(self):
        for obj in ([], None, "rectangles", {}, {"rectangles": None}, {"rectangles": "x"},
                    {"rectangles": BANDS["rectangles"], "n": 87},
                    {"rectangles": [[0, 0, 87], [0, 43, 87, 44]]},
                    {"rectangles": [[0, 0, 87, 43, 1], [0, 43, 87, 44]]},
                    {"rectangles": [{}, [0, 43, 87, 44]]}):
            self.assertInvalid(self.run_object(obj))

    def test_non_integer_tokens_in_every_position(self):
        for index in range(4):
            for value in (True, False, None, "0", [], {}, 1.0):
                cert = copy.deepcopy(BANDS)
                cert["rectangles"][0][index] = value
                self.assertInvalid(self.run_object(cert))
        for token in ("0.0", "0e0", "1e999999", "NaN", "Infinity", "-Infinity"):
            raw = ('{"rectangles":[[' + token + ',0,87,43],[0,43,87,44]]}').encode()
            self.assertInvalid(self.run_bytes(raw))

    def test_duplicate_and_escaped_duplicate_keys(self):
        for key in ('"rectangles"', '"rect\\u0061ngles"'):
            raw = '{"rectangles":[],' + key + ':' + json.dumps(BANDS["rectangles"]) + '}'
            self.assertInvalid(self.run_bytes(raw.encode()), "repeat keys")

    def test_long_integers_rejected_before_conversion(self):
        for digits in (10, 5000):
            for sign in ("", "-"):
                raw = ('{"rectangles":[[' + sign + '9' * digits + ',0,87,43],[0,43,87,44]]}').encode()
                self.assertInvalid(self.run_bytes(raw), "9 digits")
        raw = b'{"rectangles":[[999999999,0,87,43],[0,43,87,44]]}'
        self.assertInvalid(self.run_bytes(raw), "outside")

    def test_rectangle_count_limit(self):
        at_limit = {"rectangles": [[0, 0, 1, 1]] * 1000}
        self.assertInvalid(self.run_object(at_limit), "square area")
        over_limit = {"rectangles": [[0, 0, 1, 1]] * 1001}
        self.assertInvalid(self.run_object(over_limit), "too many")

    def test_size_limit_boundary(self):
        raw = json.dumps(BANDS).encode()
        padded = raw + b" " * (self.cfg["max_certificate_bytes"] - len(raw))
        result = self.run_bytes(padded)
        self.assertTrue(result["valid"], result)
        self.assertInvalid(self.run_bytes(padded + b" "), "size limit")

    def test_depth_limit_and_extreme_nesting(self):
        self.assertEqual(V.strict_json(b"[" * 8 + b"0" + b"]" * 8), [[[[[[[[0]]]]]]]])
        for depth in (9, 50, 30000):
            self.assertInvalid(self.run_bytes(b"[" * depth + b"0" + b"]" * depth), "nesting")
        self.assertInvalid(self.run_bytes(b'{"rectangles":[[[[[[[[[0]]]]]]]]]}'), "nesting")

    def test_quoted_brackets_and_escapes_do_not_count_as_depth(self):
        for text in ('[[[[[[[[[[[[[[[[', '"[[[[[[[[[[\\"'):
            obj = {"rectangles": BANDS["rectangles"], text: 1}
            self.assertInvalid(self.run_object(obj), "exactly one key")

    def test_empty_malformed_and_non_utf8(self):
        for raw in (b"", b'{"rectangles": [', b'{"rectangles": [}',
                    b"{'rectangles': []}", b"{}{}", b"\xef\xbb\xbf{}", b"\0"):
            self.assertInvalid(self.run_bytes(raw), "not valid JSON")
        self.assertInvalid(self.run_bytes(b"\xff\xfe{}"), "UTF-8")

    def test_file_handling(self):
        self.assertInvalid(V.verify_dir(self.directory, self.cfg), "missing")
        real = self.directory / "real.json"
        real.write_text(json.dumps(BANDS))
        path = self.directory / "certificate.json"
        path.symlink_to(real)
        self.assertInvalid(V.verify_dir(self.directory, self.cfg), "symlinks")
        path.unlink()
        path.mkdir()
        self.assertInvalid(V.verify_dir(self.directory, self.cfg))
        path.rmdir()
        os.mkfifo(path)
        self.assertInvalid(V.verify_dir(self.directory, self.cfg), "regular file")

    def test_messages_never_echo_input(self):
        marker = "UNTRUSTED_TEXT_[[[[[[[[[[[[[["
        result = self.run_object({"rectangles": BANDS["rectangles"], marker: marker})
        self.assertInvalid(result)
        self.assertNotIn(marker, json.dumps(result))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(HERE / "verify.py"), *args],
                              capture_output=True, timeout=5)

    def test_cli_one_line_determinism_and_invalid_contract(self):
        outputs = []
        for _ in range(2):
            proc = self.run_cli(str(ROOT / "baseline"))
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stderr, b"")
            self.assertEqual(len(proc.stdout.splitlines()), 1)
            outputs.append(json.loads(proc.stdout))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0]["canonical_hash"], BASELINE_HASH)
        for raw in (b"", b"[" * 30000, b'{"rectangles":[]}'):
            self.run_bytes(raw)
            proc = self.run_cli(str(self.directory))
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stderr, b"")
            self.assertEqual(len(proc.stdout.splitlines()), 1)
            self.assertInvalid(json.loads(proc.stdout))

    def test_cli_usage_is_one_json_line(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stderr, b"")
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        self.assertInvalid(json.loads(proc.stdout), "usage")

    def test_verifier_uses_only_standard_library_and_no_execution(self):
        tree = ast.parse((HERE / "verify.py").read_text())
        imports, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(node.func.id if isinstance(node.func, ast.Name)
                          else getattr(node.func, "attr", ""))
        self.assertLessEqual(imports, {"__future__", "hashlib", "json", "os", "stat", "sys", "tomllib", "pathlib"})
        self.assertFalse(calls & {"eval", "exec", "compile", "__import__", "system", "popen", "literal_eval"})


if __name__ == "__main__":
    unittest.main()
