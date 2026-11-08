"""Tests for the fixed-instance LOP verifier and its certificate contract."""

import ast
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent
SPEC = importlib.util.spec_from_file_location("lop_verifier", HERE / "verify.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
BASELINE = json.loads((PROBLEM / "baseline/certificate.json").read_text(encoding="utf-8"))
BASELINE_HASH = "6c9cf526e303289cb0305c009fc8cef35e05f385ae98418c2b071ab8c9ebcd48"

# Source: LOP_MA-EDM/BKS.zip, BKS/xLOLIB2/N-be75eec_500_9.
# Lugo, Segura and Miranda; free to use with citation of their Memetic Computing
# paper, https://arxiv.org/abs/2106.02696. Author permission and provenance are
# preserved in baseline/LICENSE-Zenodo.txt. This test data is not relicensed.
HISTORICAL_ORDER = [214, 6, 16, 136, 283, 454, 194, 28, 338, 145, 56, 238, 93, 460, 433, 244, 164, 176, 110, 178, 419, 86, 11, 179, 430, 299, 374, 113, 226, 196, 435, 368, 92, 15, 48, 372, 18, 17, 138, 245, 418, 25, 335, 301, 343, 443, 442, 172, 391, 400, 284, 61, 223, 265, 79, 184, 371, 83, 346, 143, 353, 36, 389, 365, 405, 309, 75, 457, 243, 212, 43, 155, 210, 131, 488, 280, 321, 201, 483, 173, 192, 282, 315, 142, 383, 397, 303, 308, 489, 450, 236, 316, 147, 230, 82, 375, 360, 394, 107, 455, 269, 33, 356, 135, 81, 257, 314, 95, 264, 152, 146, 35, 426, 285, 27, 156, 20, 453, 367, 422, 254, 153, 291, 312, 70, 106, 347, 295, 470, 133, 253, 39, 175, 317, 494, 434, 45, 252, 242, 415, 241, 351, 298, 273, 222, 151, 247, 355, 10, 55, 14, 402, 344, 123, 274, 49, 439, 148, 326, 232, 427, 215, 297, 275, 167, 128, 423, 313, 466, 102, 88, 362, 354, 109, 452, 266, 446, 387, 51, 350, 406, 384, 122, 30, 411, 209, 124, 485, 189, 115, 259, 459, 290, 359, 87, 154, 420, 2, 191, 91, 331, 78, 396, 361, 57, 7, 44, 185, 436, 161, 50, 69, 250, 120, 378, 235, 380, 294, 458, 63, 281, 482, 13, 58, 0, 304, 38, 381, 499, 490, 302, 408, 340, 139, 180, 96, 349, 456, 364, 277, 84, 268, 68, 292, 345, 476, 9, 42, 477, 288, 379, 224, 32, 407, 103, 469, 205, 41, 233, 47, 401, 158, 199, 208, 461, 67, 94, 216, 46, 385, 134, 425, 369, 204, 329, 181, 141, 451, 157, 318, 332, 286, 479, 249, 327, 278, 73, 348, 296, 480, 219, 200, 129, 118, 493, 206, 221, 53, 328, 471, 325, 197, 467, 190, 116, 267, 437, 80, 491, 98, 193, 399, 150, 421, 177, 251, 225, 8, 89, 392, 382, 386, 170, 23, 195, 404, 486, 403, 279, 320, 140, 370, 468, 220, 498, 261, 231, 447, 413, 464, 169, 462, 339, 90, 311, 432, 263, 234, 472, 127, 324, 357, 3, 22, 114, 126, 276, 54, 307, 121, 76, 300, 438, 239, 495, 428, 319, 52, 496, 74, 287, 410, 168, 377, 262, 217, 395, 358, 497, 112, 336, 440, 171, 388, 258, 40, 248, 484, 445, 182, 366, 481, 1, 132, 99, 100, 227, 409, 137, 29, 198, 85, 125, 417, 97, 174, 475, 271, 211, 213, 166, 255, 203, 202, 21, 334, 228, 448, 72, 429, 289, 322, 416, 246, 441, 65, 398, 363, 260, 293, 376, 60, 352, 310, 474, 337, 4, 31, 237, 229, 62, 159, 117, 465, 105, 390, 108, 34, 342, 119, 487, 165, 431, 270, 160, 71, 130, 373, 240, 333, 163, 59, 492, 183, 256, 19, 66, 412, 111, 393, 188, 323, 26, 77, 207, 305, 341, 162, 5, 187, 414, 330, 101, 64, 424, 104, 149, 463, 37, 12, 306, 24, 144, 444, 449, 218, 186, 473, 272, 478]


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = V.load_config()
        cls.matrix = V.load_matrix()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_bytes(self, raw):
        (self.directory / "certificate.json").write_bytes(raw)
        return V.verify_dir(self.directory, self.cfg)

    def run_text(self, text):
        return self.run_bytes(text.encode("utf-8"))

    def run_obj(self, cert):
        return self.run_text(json.dumps(cert, separators=(",", ":")))

    def assert_invalid(self, result, reason=None):
        self.assertEqual(set(result), {"valid", "score", "canonical_hash", "message"})
        self.assertIs(result["valid"], False)
        self.assertIsNone(result["score"])
        self.assertIsNone(result["canonical_hash"])
        if reason:
            self.assertIn(reason, result["message"])

    def test_public_baseline(self):
        result = V.verify_dir(PROBLEM / "baseline", self.cfg)
        self.assertIs(result["valid"], True)
        self.assertEqual(result["score"], "33489269")
        self.assertEqual(result["canonical_hash"], BASELINE_HASH)

    def test_public_historical_record(self):
        result = self.run_obj({"order": HISTORICAL_ORDER})
        self.assertIs(result["valid"], True)
        self.assertEqual(result["score"], "33464804")
        self.assertEqual(result["canonical_hash"],
                         "fcdb2726012d7b63dd49e3c6bff32f65d38eb69896c19b59bb156476b6df2559")

    def test_fixed_matrix_integrity_bounds_and_lattice(self):
        raw = zlib.decompress(base64.b64decode(V.DATA))
        self.assertEqual(len(raw), 1107980)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), V.INSTANCE_SHA256)
        self.assertEqual(len(self.matrix), 500)
        self.assertTrue(all(len(row) == 500 for row in self.matrix))
        self.assertTrue(all(type(x) is int and x >= 0 for row in self.matrix for x in row))
        self.assertEqual(sum(max(self.matrix[i][j], self.matrix[j][i])
                             for i in range(500) for j in range(i + 1, 500)), 43321427)
        self.assertEqual(math.gcd(*(self.matrix[i][j] - self.matrix[j][i]
                                    for i in range(500) for j in range(i + 1, 500))), 1)

    def test_corrupt_matrix_rejected(self):
        V.load_matrix.cache_clear()
        try:
            # A valid compressed payload with incorrect source bytes must fail.
            with mock.patch.object(V, "DATA", base64.b64encode(zlib.compress(b"500\n")).decode()):
                with self.assertRaises(ValueError):
                    V.load_matrix()
        finally:
            V.load_matrix.cache_clear()

    def test_configuration_is_fixed(self):
        original = (PROBLEM / "problem.toml").read_text(encoding="utf-8")
        path = self.directory / "problem.toml"
        changes = (("n = 500", "n = 499"),
                   ("max_certificate_bytes = 16384", "max_certificate_bytes = 16385"),
                   (V.INSTANCE_SHA256, "0" * 64))
        for before, after in changes:
            with self.subTest(before=before):
                self.assertIn(before, original)
                path.write_text(original.replace(before, after), encoding="utf-8")
                with self.assertRaises(ValueError):
                    V.load_config(path)

    def test_score_orientation_and_reversal(self):
        ascending = list(range(500))
        forward = self.run_obj({"order": ascending})
        reverse = self.run_obj({"order": ascending[::-1]})
        expected = sum(self.matrix[i][j] for i in range(500) for j in range(i + 1, 500))
        self.assertEqual(forward["score"], str(expected))
        total = sum(self.matrix[i][j] + self.matrix[j][i]
                    for i in range(500) for j in range(i + 1, 500))
        self.assertEqual(int(forward["score"]) + int(reverse["score"]), total)
        self.assertNotEqual(forward["canonical_hash"], reverse["canonical_hash"])

    def test_adjacent_exchange_changes_only_one_pair(self):
        order = BASELINE["order"][:]
        u, v = order[0:2]
        order[0], order[1] = v, u
        result = self.run_obj({"order": order})
        self.assertEqual(result["score"], str(33489269 + self.matrix[v][u] - self.matrix[u][v]))
        self.assertNotEqual(result["canonical_hash"], BASELINE_HASH)

    def test_canonical_representations_and_single_key_order(self):
        # Only one top-level key is permitted; reversing its key order is trivial.
        reordered = dict(reversed(list(BASELINE.items())))
        compact = json.dumps(reordered, separators=(",", ":"))
        pretty = json.dumps(BASELINE, indent=2)
        escaped_key = compact.replace('"order"', '"\\u006frder"')
        signed_zero = compact.replace(",0,", ",-0,")
        self.assertNotEqual(signed_zero, compact)
        variants = (compact, pretty, " \r\n\t" + compact + "\n", escaped_key, signed_zero)
        for text in variants:
            with self.subTest(text=text[:20]):
                result = self.run_text(text)
                self.assertTrue(result["valid"])
                self.assertEqual(result["score"], "33489269")
                self.assertEqual(result["canonical_hash"], BASELINE_HASH)
        expected = hashlib.sha256(compact.encode("ascii")).hexdigest()
        self.assertEqual(expected, BASELINE_HASH)

    def test_top_level_and_extra_fields(self):
        for cert in (None, True, [], 1, "order", {}, {"order": []},
                     {"order": BASELINE["order"], "x": 0},
                     {"x": 0, "order": BASELINE["order"]}):
            with self.subTest(kind=type(cert).__name__):
                self.assert_invalid(self.run_obj(cert))

    def test_non_permutations(self):
        original = BASELINE["order"]
        bad = (original[:-1], original + [0], [0] * 500,
               [original[0]] + original[:-1])
        for order in bad:
            self.assert_invalid(self.run_obj({"order": order}))

    def test_vertex_type_and_range(self):
        for vertex in (True, False, None, "0", 0.0, -1, 500, 999, {}, []):
            with self.subTest(vertex=vertex):
                order = BASELINE["order"][:]
                order[0] = vertex
                self.assert_invalid(self.run_obj({"order": order}))

    def test_duplicate_keys_including_escaped_spelling(self):
        array = json.dumps(BASELINE["order"])
        for text in ('{"order":[],"order":' + array + '}',
                     '{"order":' + array + ',"order":' + array + '}',
                     '{"order":' + array + ',"\\u006frder":' + array + '}'):
            self.assert_invalid(self.run_text(text), "Duplicate")

    def test_size_boundary_and_review_oversize_cases(self):
        raw = json.dumps(BASELINE, separators=(",", ":")).encode("ascii")
        for size in (16383, 16384, 16385, 2 * 1024 * 1024 + len(raw)):
            with self.subTest(size=size):
                data = b" " * (size - len(raw)) + raw
                result = self.run_bytes(data)
                if size <= 16384:
                    self.assertTrue(result["valid"])
                else:
                    self.assert_invalid(result, "exceeds")

    def test_depth_boundary_and_both_review_examples(self):
        self.assertTrue(self.run_obj(BASELINE)["valid"])
        for levels in (3, 4, 50):
            text = '{"order":' + '[' * (levels - 1) + '0' + ']' * (levels - 1) + '}'
            self.assert_invalid(self.run_text(text), "nesting")

    def test_brackets_and_escapes_in_strings_do_not_count_as_depth(self):
        text = json.dumps({"order": '[{\\"' * 50})
        self.assert_invalid(self.run_text(text), "list of 500")

    def test_malformed_json_encoding_and_numeric_tokens(self):
        for raw in (b"", b"{", b"{}{}", b"[] trailing", b"{]", b"\xff\xfe{}",
                    b"\xef\xbb\xbf{}", b"{}\x00", b"{'order':[]}",
                    b'{"order":NaN}', b'{"order":Infinity}', b'{"order":-Infinity}',
                    b'{"order":1e999999}', b'{"order":' + b"9" * 4000 + b"}"):
            with self.subTest(raw=raw[:20]):
                self.assert_invalid(self.run_bytes(raw))

    def test_review_fixture_shapes(self):
        # All adversarial shapes reported by review-a and review-b are retained.
        for order in ([], [0] * 500, [True] + list(range(1, 500)),
                      [0.0] + list(range(1, 500)), [500] + list(range(1, 500))):
            self.assert_invalid(self.run_obj({"order": order}))

    def test_no_input_echo(self):
        marker = "<script>DO_NOT_ECHO</script>"
        result = self.run_obj({"order": BASELINE["order"], marker: marker})
        self.assert_invalid(result)
        self.assertNotIn(marker, json.dumps(result))

    def test_missing_file_directory_and_symlink(self):
        self.assert_invalid(V.verify_dir(self.directory, self.cfg))
        target = self.directory / "target.json"
        target.write_text(json.dumps(BASELINE), encoding="utf-8")
        path = self.directory / "certificate.json"
        path.symlink_to(target)
        self.assert_invalid(V.verify_dir(self.directory, self.cfg))
        path.unlink()
        path.mkdir()
        self.assert_invalid(V.verify_dir(self.directory, self.cfg))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(HERE / "verify.py"), *args],
                              capture_output=True, timeout=5)

    def test_cli_deterministic_one_line_contract(self):
        (self.directory / "certificate.json").write_text(json.dumps(BASELINE), encoding="utf-8")
        first = self.run_cli(str(self.directory))
        second = self.run_cli(str(self.directory))
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, b"")
        self.assertEqual(second.stderr, b"")
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(len(first.stdout.splitlines()), 1)
        result = json.loads(first.stdout)
        self.assertEqual(set(result), {"valid", "score", "canonical_hash", "message"})
        self.assertEqual(result["score"], "33489269")
        self.assertEqual(result["canonical_hash"], BASELINE_HASH)

    def test_cli_invalid_and_usage(self):
        for args, code in (((), 2), (("one", "two"), 2), ((str(self.directory),), 0)):
            with self.subTest(args=args):
                process = self.run_cli(*args)
                self.assertEqual(process.returncode, code)
                self.assertEqual(process.stderr, b"")
                self.assertEqual(len(process.stdout.splitlines()), 1)
                self.assert_invalid(json.loads(process.stdout))
        self.run_text('{"order":NaN}')
        process = self.run_cli(str(self.directory))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stderr, b"")
        self.assertEqual(len(process.stdout.splitlines()), 1)
        self.assert_invalid(json.loads(process.stdout))

    def test_source_standard_library_only_and_no_execution(self):
        tree = ast.parse((HERE / "verify.py").read_text(encoding="utf-8"))
        imports, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                calls.add(getattr(node.func, "id", getattr(node.func, "attr", "")))
        self.assertLessEqual(imports, {"__future__", "base64", "functools", "hashlib", "json",
                                       "os", "pathlib", "stat", "sys", "tomllib", "zlib"})
        self.assertFalse(calls & {"eval", "exec", "compile", "__import__", "system", "popen"})


if __name__ == "__main__":
    unittest.main()
