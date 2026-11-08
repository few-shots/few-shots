# p017 · Linear ordering of N-be75eec_500

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p017` |
| metric | 排序得分 / ordering score |
| direction | `max` (higher is better) |
| baseline | `33489269` |
| epsilon | `1` (`absolute`) |
| verifier | `python3 problems/p017-lop-be75eec-500/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

Which permutation of the fixed xLOLIB2 instance `N-be75eec_500` maximises its strict upper-triangle sum?

## Problem

Let M be the fixed 500 × 500 non-negative integer matrix in the member
`xLOLIB2/N-be75eec_500` of the authors' [instance archive][instance], with
zero-based row and column indices. The first integer in the source file is
500; the remaining integers are the matrix entries in row-major order. The
SHA-256 of the original file bytes is
`34e940a0ecd9c0a054dfa87c0ad4d2b9286ba141d98be1dcb7ce463fe3f22437`.
The verifier embeds those bytes and checks this digest when loading M.

For a permutation σ of 0, …, 499, define

S(σ) = Σ_{0 ≤ a < b < 500} M[σ_a][σ_b].

Find a permutation maximising S. The score is this exact integer: all
500 × 499 / 2 = 124,750 ordered contributions are summed, with no diagonal
terms and no transposition of M. The dimensions and weights are fixed by
the [original instance][instance], not supplied in a certificate.

Each unordered vertex pair contributes one of M[i][j] and M[j][i]. Thus

S(σ) ≤ Σ_{i<j} max(M[i][j], M[j][i]) = 43,321,427.

This is a directly computable pairwise upper bound from the [instance][instance],
not a claim about the strongest published bound or the optimum. The
[public baseline permutation][bks] establishes the lower bound 33,489,269.
A strongest published instance-specific upper bound and an optimality proof
are unconfirmed in the cited sources.

All scores are integers. The gcd of M[i][j] − M[j][i] over i < j in the
[fixed instance][instance] is 1. Swapping adjacent vertices changes only that
pair's contribution; every permutation can be reached by adjacent swaps.
There is therefore no common coarser integer lattice for score differences.
With absolute ε = 1, the next integer above the [baseline][bks] is
33,489,270, the minimum score qualifying as an improvement on that baseline.
This does not assert that a permutation of exactly that score exists.

## Why it matters

LOLIB supplies benchmark instances used to evaluate linear ordering solvers
([LOLIB maintained page][lolib]). This instance is distributed in the
authors' [EJOR 2015 companion repository][ejor] for Ceberio, Mendiburu and
Lozano, *The linear ordering problem revisited*. Lugo, Segura and Miranda's
[MA-EDM study, first submitted in 2021][paper-old], and their
[later study, first submitted in 2024][paper-new], evaluate improvements to
best-known solutions on xLOLIB2. The authors publish the permutations as
[reusable benchmark data][zenodo], so a better permutation on this fixed
matrix can be compared under the same objective used in those studies.

## Certificate

- File: `certificate.json`, a UTF-8 JSON object with exactly the key `order`.
  For example, `{"order":[0,1,2,...,499]}` illustrates the shape; the ellipsis
  must be replaced by the intervening integers in an actual JSON file.
- `order` must be an array containing every integer from 0 through 499 exactly
  once, in ranking order. Booleans, strings, null, fractional numbers and
  exponent-form numbers are rejected. Integer tokens have at most 3 decimal
  digits, excluding a leading minus sign; negative vertex values are invalid.
- The file is at most 16 KiB (16,384 bytes), including whitespace. It has no
  duplicate object keys, NaN, Infinity, byte-order mark or trailing non-whitespace
  data. Container nesting is at most 2 levels, counting the outer object as
  level 1 and the `order` array as level 2. These are format limits.
- The score is computed from M in exact integer arithmetic and returned as a
  decimal integer string, such as `"33489269"` for the [baseline][bks].
- **Canonical form:** after parsing and validating the permutation, form the
  object `{"order":order}` with that same array order. Serialize it as ASCII
  JSON with no whitespace or final newline, the literal key `"order"`, and each
  vertex as its ordinary base-10 integer spelling, without a sign or leading
  zeros (zero is `0`). Hash precisely those bytes with SHA-256; output the
  lowercase hexadecimal digest as `canonical_hash`. Equivalently, use
  `json.dumps({"order": order}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.
  Input whitespace, escaped spellings of the key, and JSON `-0` in place of
  `0` have the same canonical form. No reversal, rotation, inversion or
  relabelling is applied: the vertex labels and ranking order are fixed,
  and different permutations are different certificates even if their
  scores coincide.

## Baseline

S = 33,489,269. `baseline/certificate.json` is the zero-based permutation
in `BKS/N-be75eec_500_26h` from the authors' [public BKS archive][bks],
whose `Cost: 33489269` is reproduced exactly by summing the original
[matrix entries][instance]. The [dataset][zenodo] was published in 2025;
the [author's explanation][solution-permission] associates these solutions
with *Future trends in the design of memetic algorithms: the case of the
linear ordering problem* ([paper][paper-new], [journal DOI][journal]).
The baseline is a public best-known construction, not a proved optimum.

The source permutation file has SHA-256
`53830fd93a01b4b262dc39bd779d7c632b26204825648dddfb97026909fe6ec5`.
Conversion removes the `Solution:` and `Cost:` labels and writes the same
500 vertex indices as the JSON `order` array, without changing their order
or numbering. Its canonical hash is
`6c9cf526e303289cb0305c009fc8cef35e05f385ae98418c2b071ab8c9ebcd48`.

The [earlier public archive][old-bks] contains
`BKS/xLOLIB2/N-be75eec_500_9`, with `Costo: 33464804`; its permutation
reproduces 33,464,804 on the same [matrix][instance]. It is a historical
test case, not the improvement threshold.

The matrix is third-party data from Ceberio, Mendiburu and Lozano. Josu
Ceberio's [permission][instance-permission] states: “Feel free to use the
instances. The only condition is not to use them directly or indirectly for
commercial purposes.” His [redistribution confirmation][redistribution]
answers the [specific request][permission-question] to embed and publicly
distribute this matrix in the non-commercial benchmark, including drink
voucher rewards. The original permission excerpts are preserved in
`baseline/LICENSE-xLOLIB2.txt`; the embedded matrix retains these terms.

The baseline dataset credits Carlos Segura, Gara Miranda and Lázaro Lugo and
is licensed under [Creative Commons Attribution 4.0 International][ccby]
by the [Zenodo record][zenodo]. `baseline/LICENSE-Zenodo.txt` preserves the
source attribution, licence notice, author permission, paper citations and
JSON conversion description. The baseline retains CC BY 4.0, and the
embedded matrix retains its separate non-commercial permission; neither
is relicensed under the repository's CC0 data declaration or Apache-2.0
code licence.

To reproduce:

```bash
python3 problems/p017-lop-be75eec-500/verify/verify.py problems/p017-lop-be75eec-500/baseline
```

[instance]: https://raw.githubusercontent.com/sgpceurj/EJOR2015/master/xLOLIB2.zip
[ejor]: https://github.com/sgpceurj/EJOR2015
[bks]: https://zenodo.org/api/records/14720629/files/BKS.zip/content
[zenodo]: https://zenodo.org/records/14720629
[old-bks]: https://raw.githubusercontent.com/carlossegurag/LOP_MA-EDM/main/BKS.zip
[paper-old]: https://arxiv.org/abs/2106.02696
[paper-new]: https://arxiv.org/abs/2405.08285
[journal]: https://doi.org/10.1007/s00521-025-11171-z
[lolib]: https://www.uv.es/rmarti/paper/lop.html
[ccby]: https://creativecommons.org/licenses/by/4.0/
[instance-permission]: https://github.com/sgpceurj/EJOR2015/issues/1#issuecomment-6598375344
[permission-question]: https://github.com/sgpceurj/EJOR2015/issues/1#issuecomment-6602047593
[redistribution]: https://github.com/sgpceurj/EJOR2015/issues/1#issuecomment-6625409953
[solution-permission]: https://github.com/carlossegurag/LOP_MA-EDM/issues/1#issuecomment-6621567958
