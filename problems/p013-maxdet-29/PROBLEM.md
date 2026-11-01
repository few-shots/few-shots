# p013 · Maximal determinant of a 29×29 ±1 matrix

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p013` |
| metric | 行列式绝对值 / absolute determinant |
| direction | `max` (higher is better) |
| baseline | `1188957517256767569920` |
| epsilon | `268435456` (`absolute`) |
| verifier | `python3 problems/p013-maxdet-29/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

Which 29×29 matrix with every entry +1 or −1 has the largest determinant in absolute value?

## Problem

Let M be an n × n matrix with every entry in {−1, +1}, where n = 29 (`[params] order` in `problem.toml`). Find such a matrix with |det M| as large as possible. The score is |det M|, an integer.

Permuting rows or columns, negating rows or columns, and transposing do not change |det M|.

Every n × n ±1 determinant is a multiple of 2^(n−1): negating columns so that the first row is all +1 changes only the sign of the determinant, and subtracting the first row from each other row leaves n − 1 rows whose entries are 0 or −2 (see also §1 of [Brent, Orrick, Osborn and Zimmermann, Maximal determinants and saturated D-optimal designs of orders 19 and 37, preprint, 2011](https://members.loria.fr/PZimmermann/papers/rpb244.pdf), which writes d_n = D_n / 2^(n−1) for the maximum D_n). For n = 29 every score is therefore a multiple of 2^28 = 268,435,456, which is ε. The baseline is 4,429,211,904,320 · 2^28, so the next possible score above it is 4,429,211,904,321 · 2^28 = 1,188,957,517,257,036,005,376. Whether that value, or any value above the baseline, is attained is not known.

Upper bounds. For odd n, the Barba bound is |det M| ≤ √(2n − 1) · (n − 1)^((n−1)/2) ([Browne, Egan, Hegarty and Ó Catháin, A survey of the Hadamard maximal determinant problem, Electron. J. Combin. 28(4) (2021) #P4.41, §5, Corollary 10](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf); bound (2) in [Brent et al. 2011](https://members.loria.fr/PZimmermann/papers/rpb244.pdf)). For n = 29 it is √57 · 28^14 ≈ 1.37452 × 10^21, with integer part 1,374,516,212,147,183,939,924. Equality requires 2n − 1 to be a perfect square (Theorem 12 of [the survey](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf)); 57 is not, so the Barba bound is not attained for n = 29. A smaller bound is proved in §7 and Table 1 of [Brent et al. 2011](https://members.loria.fr/PZimmermann/papers/rpb244.pdf): after ruling out 9,587 candidate Gram matrices, d_29 < 329 · 7^12, that is

|det M| < 329 · 7^12 · 2^28 = 1,222,396,947,429,614,157,824,

so every score is at most (329 · 7^12 − 1) · 2^28 = 1,222,396,947,429,345,722,368. The same section notes that if 7^13 divides d_29 then d_29 = 322 · 7^12. The baseline is about 0.86500 of the Barba bound (the archived record page gives the ratio 0.865001, Table 1 of Brent et al. gives 0.865), and the bound 329 · 7^12 · 2^28 is about 0.88933 of it (0.889 in Table 1). Any score above the baseline is less than 329/320 = 1.028125 times the baseline. The largest possible |det M| for n = 29 is not known. The bounds play no part in scoring.

## Why it matters

Hadamard proved |det M| ≤ n^(n/2) for complex matrices with entries of modulus at most 1 and ended his paper by suggesting the study of the largest determinant of ±1 matrices ([J. Hadamard, Résolution d'une question relative aux déterminants, Bull. Sci. Math. 17 (1893) 240–246, scan on Zenodo](https://zenodo.org/records/18674602); [Browne et al. 2021, abstract](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf)). This is the Hadamard maximal determinant problem. In statistics a ±1 matrix of maximal determinant is a saturated D-optimal design ([Brent et al. 2011, abstract](https://members.loria.fr/PZimmermann/papers/rpb244.pdf)).

For n ≡ 1 (mod 4), [the survey (§5)](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v28i4p41/pdf) states that its authors are not aware of work establishing the maximal determinants at orders 29, 33, 45 or 49, and that these are the only open cases with n ≡ 1 (mod 4) and n ≤ 50. Upper bounds for n = 29 were improved by [Orrick, The maximal {−1, 1}-determinant of order 15, arXiv:math/0401179 (2004)](https://arxiv.org/abs/math/0401179) (abstract) and again by [Brent et al. 2011](https://members.loria.fr/PZimmermann/papers/rpb244.pdf) (Table 1). [OEIS A003433](https://oeis.org/A003433) lists the maximal determinant only for n = 1, …, 22.

The value 1,188,957,517,256,767,569,920 = 320 · 7^12 · 2^28 for n = 29 is on the order-29 page of the maximal determinant tables maintained by Orrick and Solomon ([archived d29.html](https://web.archive.org/web/20200219170713/http://www.indiana.edu/~maxdet/d29.html), page created and last modified in 2002), which credits it to Bruce Solomon (reported in 2002, superseding his earlier 45 · 7^13 · 2^28) and notes "This form has not been proved to be optimal". [Orrick, Solomon, Dowdeswell and Smith, New lower bounds for the maximal determinant problem, arXiv:math/0304410 (2003)](https://arxiv.org/abs/math/0304410) list n = 29 in the abstract among the orders where they beat the existing records. The [order-29 page of R. P. Brent](https://maths-people.anu.edu.au/~brent/maxdet/order29/) gives the Gram matrix of this record, with determinant (320 · 7^12 · 2^28)^2, as the conjectured D-optimal Gram matrix due to Solomon (2002), and lists 4,918 known Hadamard equivalence classes of ±1 matrices R with R Rᵀ = Rᵀ R equal to it. Table 1 of [Brent et al. 2011](https://members.loria.fr/PZimmermann/papers/rpb244.pdf) gives 320 · 7^12 as the lower bound for d_29, and §7.1 reports that hill-climbing and constructions based on Hadamard matrices of order 28 did not give |det|/2^28 > 320 · 7^12. A 29×29 ±1 matrix with |det M| ≥ 1,188,957,517,257,036,005,376 has a larger determinant than every order-29 matrix in these sources.

## Certificate

- File name `certificate.json`, shaped like `{"matrix": [[1, -1, …], …]}`, with no other keys.
- `matrix` is a list of exactly 29 rows; each row is a list of exactly 29 entries; each entry is the JSON integer `1` or `-1`. Booleans, strings, `0`, `-0`, fractions, exponents (`1.0`, `1e0`), `NaN` and `Infinity` are rejected.
- Singular matrices are valid and score `0`.
- The verifier computes det M exactly in integer arithmetic (fraction-free Bareiss elimination with row pivoting). The score is |det M| as a decimal integer string, for example `"1188957517256767569920"`.
- The file is UTF-8 JSON without a byte order mark, at most 65,536 bytes, nested at most 8 levels, with integers of at most 18 ASCII digits and no duplicate keys (keys are compared after JSON unescaping).
- Canonical form. Let r_1, …, r_29 be the rows.
  1. Replace every row whose first entry is −1 by its negation, so every row starts with +1.
  2. Sort the 29 rows in increasing lexicographic order: compare two rows entry by entry from the first, with −1 < +1. (This is Python's ordering of lists of integers.)
  3. The canonical object is `{"matrix": C}` with C the sorted list of rows.
  4. `canonical_hash` is the lowercase hex SHA-256 of that object written as JSON with no whitespace at all, entries as `1` and `-1`, ASCII bytes, no trailing newline; in Python, `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.

  So two certificates have the same hash exactly when one is obtained from the other by permuting rows and negating rows. Whitespace and escapes in the key do not enter the hash. Permuting or negating columns and transposing keep the score but are not detected; a tie with the record is not an improvement either way.

  Worked example (order 3, only to show the computation): the rows `[-1,1,1]`, `[1,1,-1]`, `[1,-1,1]` become `[1,-1,-1]`, `[1,1,-1]`, `[1,-1,1]` after step 1 and `[1,-1,-1]`, `[1,-1,1]`, `[1,1,-1]` after step 2; the hashed bytes are `{"matrix":[[1,-1,-1],[1,-1,1],[1,1,-1]]}`, with SHA-256 `46472a7336ecc2317e522d315d86dca3f959157b2efc98d132cc54d408dcde26`. For the baseline, 9 rows are negated in step 1 (rows 1, 3, 7, 15, 18, 19, 22, 23 and 28 in the printed order, counting from 1), the hashed bytes begin `{"matrix":[[1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,-1,-1,1,1,-1,1,-1,-1,-1,-1,-1,-1,-1,1,-1,1,1],` and are 2,138 bytes long, and `canonical_hash` is `b39a583d8ecf8327fbdc8ccac18cb0cf4d607fbab200dd48996ff3f45fd4de94`.

## Baseline

|det R| = 1,188,957,517,256,767,569,920 = 4,429,211,904,320 · 2^28 = 320 · 7^12 · 2^28 = 5 · 7^12 · 2^34, for the matrix R on the order-29 page of the Orrick–Solomon maximal determinant tables ([archived d29.html](https://web.archive.org/web/20200219170713/http://www.indiana.edu/~maxdet/d29.html); the link serves the Wayback Machine snapshot taken in 2019 of http://www.indiana.edu:80/~maxdet/d29.html). The page credits the value to Bruce Solomon (2002); the same order appears among the new records of [arXiv:math/0304410](https://arxiv.org/abs/math/0304410) (Orrick, Solomon, Dowdeswell, Smith, 2003). Whether the two sources report the same matrix is not confirmed here: only the abstract of the paper was checked. The Gram matrix of R is the one on [Brent's order-29 page](https://maths-people.anu.edu.au/~brent/maxdet/order29/).

`baseline/certificate.json` is the 29 × 29 sign pattern printed under "R:" on that page, rows in the printed order, with `+` → `1` and `-` → `-1`. As printed, det R = +1,188,957,517,256,767,569,920. The page also prints the Gram matrix M = R Rᵀ = Rᵀ R (29 on the diagonal, entries 5, 1 and −3 elsewhere); for the certificate both products equal the printed M entry by entry, and det M = (det R)^2. The page states no licence for the matrix; the certificate holds only its 841 entries, cited to the sources above.

To reproduce:

```bash
python3 problems/p013-maxdet-29/verify/verify.py problems/p013-maxdet-29/baseline
```
