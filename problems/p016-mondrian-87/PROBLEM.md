# p016 · Mondrian dissection of the 87×87 square

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p016` |
| metric | 缺陷 / defect |
| direction | `min` (lower is better) |
| baseline | `22` |
| epsilon | `1` (`absolute`) |
| verifier | `python3 problems/p016-mondrian-87/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

Partition the 87×87 square into non-congruent integer rectangles and minimize the difference between the largest and smallest areas.

## Problem

Partition [0,87] × [0,87] into at least two axis-parallel rectangles whose corners have integer coordinates and whose widths and heights are positive integers. Every unit cell must be covered exactly once. No two rectangles may be congruent: widths and heights are compared without orientation, so w×h and h×w are the same shape. Rectangles with equal areas but different shapes are allowed. The number of rectangles is not fixed.

For rectangle areas A_i = w_i h_i, the defect is D = max_i A_i − min_i A_i. The score is D in unit cells of area, computed using exact integer arithmetic; lower is better. This is the fixed n = 87 instance of the problem in [OEIS A276523](https://oeis.org/A276523).

The score is an integer. With baseline 22 and absolute epsilon 1, the next integer score below the baseline is 21; any valid certificate with D ≤ 21 improves the baseline. This does not assert that a dissection of defect 21 exists.

## Why it matters

[Gordon Hamilton's MathPickle page (2015)](https://mathpickle.com/project/mondrian-art-puzzles/) states the Mondrian art problem. [OEIS A276523](https://oeis.org/A276523/internal) maintains constructions and optimality annotations for individual side lengths. A smaller defect for side length 87 improves that entry's constructive upper bound.

Let M(87) denote the minimum defect. [Hannes Bassen, *Further Insight into the Mondrian Art Problem* (2016), Table II](https://mathpickle.com/wp-content/uploads/2016/12/Bassen-Further-Insight-into-the-Mondrian-Art-Problem.pdf) reports computational exclusions of defect 0 for 3 ≤ n ≤ 419, defect 1 for 3 ≤ n ≤ 700, defect 2 for 4 ≤ n ≤ 897, and defect 3 for 3 ≤ n ≤ 417. Each range contains 87, hence M(87) ≥ 4. Together with [Muessig's construction](https://oeis.org/A276523/a276523_2.txt), this gives 4 ≤ M(87) ≤ 22. The lower bound is cited from that computation; it is not asserted to be the strongest published bound. The construction is marked `a(87)<=22`, without an optimality equality.

## Certificate

- Submit a regular file named `certificate.json`, encoded as UTF-8 JSON, with exactly one top-level key: `{"rectangles":[[x,y,w,h],...]}`. Unknown keys and duplicate keys are rejected.
- `rectangles` is an array containing between 2 and 1000 arrays. Each inner array contains exactly four JSON integers: the lower-left corner (x,y), width w and height h. The origin (0,0) is the square's lower-left corner; x increases rightward and y upward. A rectangle covers cells with x ≤ column < x+w and y ≤ row < y+h.
- Require w,h ≥ 1, x,y ≥ 0, x+w ≤ 87, and y+h ≤ 87. Booleans, strings, null, decimal or exponent numbers, NaN and infinities are rejected. Integer tokens may contain at most 9 decimal digits, excluding a leading minus sign.
- The file is at most 1048576 bytes (1 MiB). JSON container nesting is at most 8 levels, counting the root object as level 1 and each nested object or array as one additional level; scalar values do not add a level. A certificate in the required schema has 3 container levels.
- The verifier checks total area 87² = 7569, distinct unordered side-length pairs, and exact coverage without overlap. It returns the defect as a decimal integer string, for example `"22"`. It accepts valid dissections even when their scores do not improve the record.

### Canonical form

The hash identifies a dissection up to reordering its rectangles and the eight symmetries of the square. All comparisons below are numerical lexicographic comparisons of integer tuples and lists, not comparisons of their JSON text.

For a rectangle q = (x,y,w,h), define a counterclockwise quarter-turn R(q) = (87−y−h,x,h,w) and a reflection F(q) = (87−x−w,y,w,h). For k = 0,1,2,3, apply R^k to every rectangle to obtain one image, and apply F after R^k to every rectangle to obtain another image. Here R^0 is the identity. These are the eight candidates.

In each candidate, sort the quadruples ascending by x, then y, then w, then h. Compare the resulting lists lexicographically, comparing the first differing quadruple numerically, and choose the smallest list L. Serialize exactly the object `{"rectangles":L}` with each quadruple represented as a JSON array and each number as its base-10 integer value. Use no whitespace, no extra keys and no trailing newline. Equivalently, use Python `json.dumps({"rectangles": L}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`.

`canonical_hash` is the lowercase hexadecimal SHA-256 digest of those ASCII bytes. Input whitespace, rectangle order, JSON key escaping and the eight global symmetries do not affect it. Merely sharing the same multiset of rectangle shapes does not identify different placements.

## Baseline

[Mia Muessig's OEIS record annotation (2025)](https://oeis.org/A276523/internal) gives a best-known upper bound of 22 for n = 87. Her [public tiling file](https://oeis.org/A276523/a276523_2.txt) explicitly labels the construction `a(87)<=22`. Its 13 rectangles have areas between 572 and 594 inclusive and total area 7569; their defect is 594−572 = 22. The baseline's rectangle count is not a submission constraint.

`baseline/certificate.json` was reconstructed from that file's 87×87 character grid. Each label was replaced by its integer bounding rectangle, the labels were discarded, and the rectangles were sorted. The first source row becomes y=0, so the Cartesian certificate is a vertical reflection of the printed top-to-bottom grid. The source file is 208711 bytes, with SHA-256 `073c266cd84ab5480a696615b935bf95c23f7ec16a6a1c754dd65347518ec66b`. The canonical hash of the supplied baseline is `9e35bae916e1f9877a693fae4d02bc2707ba790fd314b0886efc3ba857f9174b`.

The baseline is attributed to Mia Muessig / The Online Encyclopedia of Integer Sequences, A276523. It retains [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) under the [OEIS license agreement](https://oeis.org/LICENSE), rather than the CC0 license for new shots. The source links, verbatim license notice and adaptation details are in `baseline/LICENSE-OEIS.txt`. Verifier code follows the repository's Apache-2.0 license.

Reproduce from the repository root:

```sh
python3 problems/p016-mondrian-87/verify/verify.py problems/p016-mondrian-87/baseline
```
