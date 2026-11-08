# p023 · Covering design C(15,9,7)

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p023` |
| metric | 区组数 / blocks |
| direction | `min` (lower is better) |
| baseline | `270` |
| epsilon | `1` (`absolute`) |
| verifier | `python3 problems/p023-covering-15-9-7/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

Find the fewest nine-element blocks on a fixed set of fifteen points that cover every seven-element subset.

## Problem

Let V = {0, 1, ..., 14}. A covering is a list of nine-element subsets of V,
called blocks, such that every seven-element subset of V is contained in at
least one block. Minimize the number of blocks. The minimum is denoted
C(15,9,7); this is the covering-design definition used by
[Fadlaoui and Galinier][construction].

The score is the number of entries in the block list, an integer. Repeated
blocks are allowed and each occurrence counts toward the score. Absolute
epsilon is 1. The next integer score below the baseline 270 is 269, so a
first improvement requires 269 blocks or fewer; this does not assert that
269 is attainable. The baseline is the published construction in
[Table 1][construction], not a proved value of C(15,9,7).

The bounds used here are 225 <= C(15,9,7) <= 270. The upper bound is the
[Table 1 construction][construction]. For the lower bound,
[Krug (2026)][lower] proves C(12,6,4) = 41. Counting point-block incidences
gives C(v,k,t) >= ceil(v*C(v-1,k-1,t-1)/k), because the blocks through each
point, with that point removed, cover every (t-1)-subset of the remaining
points. Thus ceil(13*41/7) = 77, ceil(14*77/8) = 135, and
ceil(15*135/9) = 225. These are bounds, not a claim that any particular
improvement is possible.

## Why it matters

Covering designs and tables of constructive upper bounds are studied in
[Gordon, Kuperberg and Patashnik][tables]. The numerical construction for
these parameters is published in [Fadlaoui and Galinier (2010)][construction].
The [La Jolla Coverings Repository][archive] collects constructions and
improvement histories; [Covering Repository][maintained] provides a maintained
entry point for covering-design results. A smaller valid covering improves
the constructive upper bound for these fixed parameters.

There is also a direct complement formulation. Put F = {V \ B : B is a
block}. Every eight-element subset then contains a six-element member of F.
Minimizing the size of such a family is the Turan covering problem
T(15,8,6) = C(15,9,7). If H is the set of all six-element subsets of V with F
removed, H contains no complete six-uniform hypergraph on eight vertices.
Consequently ex(15; K_8^(6)) = binom(15,6) - C(15,9,7)
= 5005 - C(15,9,7). These identities follow by taking complements in the
[covering definition][construction]; the [lower-bound paper][lower] also
uses this type of covering/Turan correspondence. A family of 270 blocks
proves an upper bound on T, not equality with its optimum.

## Certificate

- File name: `certificate.json`. It must be a JSON object with exactly one
  key, `"blocks"`, whose value is a list of 1 through 1000 blocks.
- Each block is a JSON array of exactly 9 distinct integers in the range
  0 through 14. Block order and point order within a block are arbitrary.
  Boolean values, strings, nulls, fractions and exponent notation are not
  integers for this format. An integer token may have at most 18 decimal
  digits, excluding its optional minus sign.
- The file must be UTF-8 JSON without a byte order mark, at most 65,536 bytes
  (64 KiB), with no duplicate object keys, NaN or Infinity. Container nesting
  is limited to 8 levels: the root object is level 1, the block list level 2,
  and each block array level 3. Brackets inside strings do not add levels.
  The certificate must be a regular file, not a symbolic link or special file.
- The verifier enumerates all binom(15,7) = 6435 seven-element subsets and
  marks the binom(9,7) = 36 subsets in each block, following the
  [covering definition][construction]. Every seven-element subset must be
  covered. All computations are exact integer computations.
- The score is the length of the submitted block list, for example `"270"`.
  Multiplicities are retained; repeated blocks cannot reduce the score.

Canonical form:

1. Sort the nine integer labels in each block in increasing numerical order.
2. Sort the resulting block arrays lexicographically, comparing integers
   numerically. Keep every occurrence of a repeated block.
3. Construct the object with keys `"block_size"`, `"blocks"`, `"cover_size"`,
   `"points"` and values `9`, the sorted block list, `7`, `15`, respectively.
   These fixed parameters participate in the hash even though they are not
   permitted as keys in the submitted certificate.
4. Serialize using Python
   `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
   and encode as ASCII, with no trailing newline. Equivalently, the bytes
   begin `{"block_size":9,"blocks":[`, contain the sorted integer arrays
   with comma separators and no whitespace, and end
   `],"cover_size":7,"points":15}`.
5. `canonical_hash` is the lowercase hexadecimal SHA-256 digest of those
   bytes.

This identifies permutations of the blocks and of the points within each
block, as well as changes in JSON whitespace, object-key order or equivalent
JSON key escaping. It does not quotient by permutations of the point labels
0 through 14. Relabeling points preserves validity and score but need not
preserve the hash. Repeating a block changes the score and canonical data.

## Baseline

The baseline is the 270-block construction in
[Fadlaoui and Galinier, EPM-RT-2010-01 (2010), Table 1][construction], entry
(v,k,t,b) = (15,9,7,270), printed page 2 (PDF page 7).
It has 270 distinct blocks and covers all 6435 seven-element subsets.
This is the reproducible published upper bound used for scoring. The
parameter-specific entry in the live record database has not been
independently confirmed from the available source snapshots.

`baseline/certificate.json` was reconstructed from the 270 integer block
indices in that table, using zero-based colex decoding:

`rank(b_0,...,b_8) = sum(i=0..8, binom(b_i,i+1))`,
where `0 <= b_0 < ... < b_8 <= 14`.

The report calls its ordering lexicographic; the explicit formula above is
the decoding convention that reproduces this covering. Decode each rank by
choosing b_8, then b_7, down to b_0, each as large as possible subject to
the remaining rank and strict label ordering, subtracting its binomial
term. Sort the decoded blocks as specified above, then write
`{"blocks": ...}` as compact ASCII JSON with no trailing newline. This
file is 6214 bytes and has SHA-256
`0dec6b959f6bfceddb99b5f35a83bfc97f7ffd94709f68383bde9b70b7eeacad`.
Its canonical hash is
`39be9ce649e502ff86438406c8d31428c9ab3b601a79122b3c4d50d1ab2c2e13`.

Construction attribution: Kamal Fadlaoui and Philippe Galinier. Related
dataset attribution: Daniel Gordon, *La Jolla Coverings Repository*,
version 1.2, [DOI 10.5281/zenodo.19735294][archive], whose record specifies
[CC BY 4.0][license]. The certificate contains numerical data reconstructed
from the paper; the archive's JSON entry was not used or checked for exact
identity. Changes are the explicit colex decoding, zero-based labels and
sorting. Source attribution and licensing are retained in
`baseline/LICENSE-Fadlaoui-Galinier.txt` and `baseline/LICENSE-LJCR.txt`;
the third-party baseline is not relicensed under the shot CC0 terms.
The paper itself reserves rights and allows attributed reproduction for
personal study or research; its PDF is not redistributed here.

To reproduce the score:

```bash
python3 problems/p023-covering-15-9-7/verify/verify.py problems/p023-covering-15-9-7/baseline
```

[construction]: https://publications.polymtl.ca/2650/1/EPM-RT-2010-01_Fadlaoui.pdf
[lower]: https://arxiv.org/abs/2607.23766
[tables]: https://arxiv.org/abs/math/9502238
[archive]: https://zenodo.org/records/19735294
[maintained]: https://coveringrepository.com/
[license]: https://creativecommons.org/licenses/by/4.0/
