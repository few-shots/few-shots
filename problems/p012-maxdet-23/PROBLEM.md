# p012 · Maximal determinant of a 23×23 ±1 matrix

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p012` |
| metric | 行列式绝对值 / absolute determinant |
| direction | `max` (higher is better) |
| baseline | `2779447296000000` |
| epsilon | `4194304` (`absolute`) |
| verifier | `python3 problems/p012-maxdet-23/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

Which 23×23 matrix with every entry +1 or −1 has the largest determinant in absolute value?

## Problem

Let M be an n × n matrix with every entry in {−1, +1}, where n = 23 (`[params] order` in `problem.toml`). Find such a matrix with |det M| as large as possible. The score is |det M|, an integer.

Permuting rows or columns, negating rows or columns, and transposing do not change |det M|.

Every n × n ±1 determinant is a multiple of 2^(n−1): negating columns so that the first row is all +1 changes only the sign of the determinant, and subtracting the first row from each other row leaves n − 1 rows whose entries are 0 or −2. The same factor appears in the formula a(n) = 2^(n−1)·A003432(n−1) of [OEIS A003433](https://oeis.org/A003433). For n = 23 every score is therefore a multiple of 2^22 = 4,194,304, which is ε. The baseline is 662,671,875 · 2^22, so the next possible score above it is 662,671,876 · 2^22 = 2,779,447,300,194,304. Whether that value, or any value above the baseline, is attained is not known.

Upper bound. For n ≡ 3 (mod 4) the Ehlich bound applies (H. Ehlich, Math. Z. 83 (1964) 123–132; stated as the formula before Theorem 28 and Theorem 28 in [Browne, Egan, Hegarty and Ó Catháin, A survey of the Hadamard maximal determinant problem, Electron. J. Combin. 28(4) (2021) #P4.41, §7](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf/)). For n = 23 the extremal block partition is 4 + 4 + 4 + 4 + 4 + 3, which gives

det(M Mᵀ) ≤ 20^17 · 36^5 · 32 · (1 − 5·4/36 − 3/32) = (2^22 · 3 · 5^6 · 675)^2 · 505,

so |det M| ≤ 2^22 · 3 · 5^6 · 675 · √505 ≈ 2.98230 × 10^15. The bound is not an integer, and the largest multiple of 2^22 below it is 711,034,613 · 2^22 = 2,982,295,321,444,352. The baseline is about 0.93198 of the Ehlich bound; the archived record page gives the ratio 0.931983. The largest possible |det M| for n = 23 is not known. The bound plays no part in scoring.

## Why it matters

Hadamard proved |det M| ≤ n^(n/2) for complex matrices with entries of modulus at most 1 and ended his paper by suggesting the study of the largest determinant of ±1 matrices ([J. Hadamard, Résolution d'une question relative aux déterminants, Bull. Sci. Math. 17 (1893) 240–246, scan on Zenodo](https://zenodo.org/records/18674602); [Browne et al. 2021, abstract](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf/)). This is the Hadamard maximal determinant problem. In statistics the same matrices are saturated D-optimal designs; for example, order 22 was settled in "The D-optimal saturated designs of order 22" (Chasiotis, Kounias and Farmakis, Discrete Math. 341 (2018) 380–387, reference [13] of [the survey](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf/)).

[OEIS A003433](https://oeis.org/A003433) lists the maximal determinant for n = 1, …, 22; its comment by R. P. Brent (2021) records that n = 22 was proved optimal by Chasiotis et al. Among orders n ≡ 3 (mod 4), [the survey (§7)](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf/) lists the maximum as determined for n = 3, 7 and 11, for n = 15 by Orrick (Metrika 62 (2005)) and for n = 19 by Brent, Osborn, Orrick and Zimmermann. For n = 23 only lower bounds from constructions are known.

The value 2,779,447,296,000,000 for n = 23 is on the order-23 page of the maximal determinant tables maintained by Orrick and Solomon ([archived d23.html](https://web.archive.org/web/20191228141040/http://www.indiana.edu:80/~maxdet/d23.html), page created 26 January 2002, last modified 11 April 2003), which credits the lower bound to Dowdeswell, Neubauer, Solomon and Tumer [DNST] and notes "This form has not been proved to be optimal". [Orrick, Solomon, Dowdeswell and Smith, New lower bounds for the maximal determinant problem, arXiv:math/0304410 (2003)](https://arxiv.org/abs/math/0304410) report in the abstract that they beat the existing records for n = 22, 23, 27, … and present the matrices. Table 1 of [Browne et al. (2021)](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf/) lists for n = 23 the ratio 0.7091 to the Barba bound √45 · 22^11, taken from Orrick's tables; the baseline gives 0.70909. A 23×23 ±1 matrix with |det M| ≥ 2,779,447,300,194,304 has a larger determinant than every order-23 matrix in these sources.

## Certificate

- File name `certificate.json`, shaped like `{"matrix": [[1, -1, …], …]}`, with no other keys.
- `matrix` is a list of exactly 23 rows; each row is a list of exactly 23 entries; each entry is the JSON integer `1` or `-1`. Booleans, strings, `0`, `-0`, fractions, exponents (`1.0`, `1e0`), `NaN` and `Infinity` are rejected.
- Singular matrices are valid and score `0`.
- The verifier computes det M exactly in integer arithmetic (fraction-free Bareiss elimination with row pivoting). The score is |det M| as a decimal integer string, for example `"2779447296000000"`.
- The file is UTF-8 JSON without a byte order mark, at most 65,536 bytes, nested at most 8 levels, with integers of at most 18 digits and no duplicate keys (keys are compared after JSON unescaping).
- Canonical form. Let r_1, …, r_23 be the rows.
  1. Replace every row whose first entry is −1 by its negation, so every row starts with +1.
  2. Sort the 23 rows in increasing lexicographic order: compare two rows entry by entry from the first, with −1 < +1. (This is Python's ordering of lists of integers.)
  3. The canonical object is `{"matrix": C}` with C the sorted list of rows.
  4. `canonical_hash` is the lowercase hex SHA-256 of that object written as JSON with no whitespace at all, entries as `1` and `-1`, ASCII bytes, no trailing newline; in Python, `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.

  So two certificates have the same hash exactly when one is obtained from the other by permuting rows and negating rows. Permuting or negating columns and transposing keep the score but are not detected; a tie with the record is not an improvement either way.

  Worked example (order 3, only to show the computation): the rows `[-1,1,1]`, `[1,1,-1]`, `[1,-1,1]` become `[1,-1,-1]`, `[1,1,-1]`, `[1,-1,1]` after step 1 and `[1,-1,-1]`, `[1,-1,1]`, `[1,1,-1]` after step 2; the hashed bytes are `{"matrix":[[1,-1,-1],[1,-1,1],[1,1,-1]]}`, with SHA-256 `46472a7336ecc2317e522d315d86dca3f959157b2efc98d132cc54d408dcde26`. For the baseline, 9 rows are negated in step 1, the hashed bytes begin `{"matrix":[[1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,1,1,-1,1,1,1,-1,-1,-1,-1,1,1],` and are 1,368 bytes long, and `canonical_hash` is `1ce81e628d6dc36c015673ac9b8dbb911b6f7d6fa4c04d5af35bef38cc942075`.

## Baseline

|det R| = 2,779,447,296,000,000 = 662,671,875 · 2^22 = 3 · 67 · 211 · 5^6 · 2^22, for the matrix R on the order-23 page of the Orrick–Solomon maximal determinant tables ([Wayback Machine snapshot of 28 December 2019](https://web.archive.org/web/20191228141040/http://www.indiana.edu:80/~maxdet/d23.html); the proposal's link [web.archive.org/web/20200219170713/…/d23.html](https://web.archive.org/web/20200219170713/http://www.indiana.edu:80/~maxdet/d23.html) serves this snapshot). The page credits the bound to Dowdeswell, Neubauer, Solomon and Tumer [DNST]; the same order appears among the new records of [arXiv:math/0304410](https://arxiv.org/abs/math/0304410) (Orrick, Solomon, Dowdeswell, Smith, submitted 25 April 2003). Whether the two sources report the same matrix, and who found it first, is not confirmed here: only the abstract of the paper was checked.

`baseline/certificate.json` is the 23 × 23 sign pattern printed under "R:" on that page, rows in the printed order, with `+` → `1` and `-` → `-1`. As printed, det R = −2,779,447,296,000,000. The page also prints the Gram matrix M = R Rᵀ = Rᵀ R; for the certificate both products equal the printed M entry by entry, and det M = (det R)^2. The page states no licence for the matrix; the certificate holds only its 529 entries, cited to the sources above.

To reproduce:

```bash
python3 problems/p012-maxdet-23/verify/verify.py problems/p012-maxdet-23/baseline
```
