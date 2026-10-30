# p011 · Smallest sorting network on 17 inputs

<!-- few-shots:header -->
| key | value |
| --- | --- |
| id | `p011` |
| metric | 比较器数 / comparators |
| direction | `min` (lower is better) |
| baseline | `71` |
| epsilon | `1` (`absolute`) |
| verifier | `python3 problems/p011-sorting-network-17/verify/verify.py <shot_dir>` |
<!-- /few-shots:header -->

What is the fewest comparators in a fixed network that sorts every input of 17 values?

## Problem

A comparator network on n = 17 channels (`[params] channels` in `problem.toml`), numbered 0 … 16, is a list of comparators [a, b] with 0 ≤ a < b ≤ 16. A comparator puts the minimum of the values on channels a and b on channel a and the maximum on channel b. The comparators act one after another in the listed order, the same order for every input. The network is a sorting network if, for every input of 17 values from a totally ordered set, the output values are non-decreasing in channel number.

Find a sorting network on 17 channels with as few comparators as possible. The score is the number of comparators. Depth (the number of parallel layers) is not restricted and not scored.

The score is an integer, so the next possible score below the baseline is 70.

The least possible number S(17) is not known. The upper bound 71 is the baseline below. Lower bounds: S(12) = 39 ([Harder, arXiv:2012.04400](https://arxiv.org/abs/2012.04400)) and the bound S(n) ≥ S(n − 1) + ⌈log₂ n⌉ of Van Voorhis, restated as Lemma 17 in [Harder](https://arxiv.org/html/2012.04400v2#S3.SS1), give S(17) ≥ 39 + 4 + 4 + 4 + 4 + 5 = 60. [Dobbelaere's table](https://bertdobbelaere.github.io/sorting_networks.html#N17L71D12) lists the lower bound 63 (update of 2025-04-21), and a preprint ([Tomar, 2026](https://hexagonmath.org/2610.00549)) claims 64; neither proof is checked here. These bounds play no part in scoring.

## Why it matters

The least number of comparators that sorts n inputs is the Bose–Nelson sorting problem ([Bose and Nelson, A sorting problem, JACM 9 (1962) 282–296](https://projects.csail.mit.edu/jacm/References/bosen1962%3A282.html)). Exact values are known only for n ≤ 12 ([OEIS A003075](https://oeis.org/A003075)): n = 9 and 10 by [Codish, Cruz-Filipe, Frank and Schneider-Kamp (2014)](https://arxiv.org/abs/1405.5754), n = 11 and 12 by [Harder (2020)](https://arxiv.org/abs/2012.04400), with a computer-checked certificate. A sorting network performs the same comparisons for every input, so it is used for sorting in hardware and in parallel, and small networks are building blocks for larger ones ([Valsalam and Miikkulainen, 2013, §1](https://jmlr.org/papers/volume14/valsalam13a/valsalam13a.pdf)).

For 17 inputs, [Valsalam and Miikkulainen (JMLR 14, 2013, 303–331)](https://jmlr.org/papers/volume14/valsalam13a/valsalam13a.pdf) list 73 as the previous best size (Table 2) and report a network with 71 comparators (Table 4, Figure 17). [Dobbelaere's table of the smallest known sorting networks](https://bertdobbelaere.github.io/sorting_networks.html#N17L71D12) lists 71 comparators (12 layers) for 17 inputs. A sorting network on 17 inputs with 70 comparators or fewer is smaller than every network in these sources.

## Certificate

- File name `certificate.json`, shaped like `{"comparators": [[0, 11], [1, 15], …]}`, with no other keys.
- `comparators` is a list of 1 … 1000 comparators (`[params] max_comparators`), in execution order.
- Each comparator is a list of exactly two JSON integers `[a, b]` with 0 ≤ a < b ≤ 16. Channels are numbered from 0; Valsalam and Miikkulainen print theirs from 1, so subtract 1. Booleans, strings, fractions, exponents, `NaN` and `Infinity` are rejected; `-0` is the integer 0.
- Repeated comparators and comparators that never exchange anything are allowed, and each one is counted.
- The score is the length of the list, an integer, for example `"71"`.
- The verifier checks all 2^17 = 131,072 inputs of 0s and 1s, which suffices by the zero-one principle (Knuth, *The Art of Computer Programming*, vol. 3, §5.3.4, Theorem Z; also [Harder, §2](https://arxiv.org/html/2012.04400v2#S2)). The check is exhaustive and exact: each channel is held as a 131,072-bit integer, one bit per 0-1 input, and a comparator is a bitwise AND (channel a) and OR (channel b). Output channel j must be 1 on exactly the inputs with at least 17 − j ones.
- The file is UTF-8 JSON without a byte order mark, at most 65,536 bytes, nested at most 8 levels, with integers of at most 18 digits and no duplicate keys (keys are compared after JSON unescaping).
- Canonical form. Let c_1, …, c_m be the comparators as listed.
  1. Layers of a list: start with last[i] = −1 for every channel i. For each comparator [a, b] in list order, let level = 1 + max(last[a], last[b]), append [a, b] to layer number `level` (layers are numbered from 0), and set last[a] = last[b] = level. Then sort the comparators inside each layer in increasing order of a (comparators in one layer share no channel). The result is a list of layers, each a list of pairs [a, b].
  2. Mirror image: the list with every [a, b] replaced by [16 − b, 16 − a], in the same order. It is a sorting network exactly when the original is, with the same number of comparators.
  3. Take the layers of the list and the layers of its mirror image, and keep the smaller of the two in lexicographic order: compare layer by layer from the first; two layers compare pair by pair; two pairs compare by a, then by b; a list that is a proper prefix of another is smaller. (This is Python's ordering of nested lists.)
  4. The canonical object is `{"channels": 17, "layers": L}` with L the kept list of layers.
  5. `canonical_hash` is the lowercase hex SHA-256 of that object written as JSON with the keys in sorted order (`channels`, then `layers`), no whitespace at all, integers in plain decimal, ASCII bytes, no trailing newline; in Python, `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")`.

  So reordering comparators on disjoint channels, without moving a comparator past another that shares a channel with it, does not change the hash, and a network and its mirror image hash the same. Other equivalences between networks are not detected; a tie with the record is not an improvement either way.

  Worked example (not a sorting network; it only shows the computation): the list `[[5,9],[0,1],[1,2],[3,4]]` has layers `[[[0,1],[3,4],[5,9]],[[1,2]]]`; its mirror image `[[7,11],[15,16],[14,15],[12,13]]` has layers `[[[7,11],[12,13],[15,16]],[[14,15]]]`; the first is smaller, so the hashed bytes are `{"channels":17,"layers":[[[0,1],[3,4],[5,9]],[[1,2]]]}`, with SHA-256 `c26d7f99be61e7e5d87924e6370f6b563e4c8146f73497a5dce931f8f3fc6e9e`. For the baseline the mirror image gives the smaller layers, and `canonical_hash` is `7899e5f61628b897666dcaf1d556c99adf37005a6d4692a266ca927fcda6df97`.

## Baseline

71 comparators, the size reported by [Valsalam and Miikkulainen (2013, Table 4 and Figure 17)](https://jmlr.org/papers/volume14/valsalam13a/valsalam13a.pdf). [Dobbelaere's table](https://bertdobbelaere.github.io/sorting_networks.html#N17L71D12) credits the size upper bound to [Baddar (2009)](https://etd.ohiolink.edu/acprod/odb_etd/etd/r/1501/10?clear=10&p10_accession_num=kent1239814529), whose thesis was not checked for a 17-input network; who found 71 first is not confirmed here.

`baseline/certificate.json` is the `nw` list of [`Sort_17_71_12.json`](https://github.com/bertdobbelaere/SorterHunter/blob/8ba90df607cbdc339409e0b173b5a2ffd60fc911/Networks/Sorters/Sort_17_71_12.json) in Bert Dobbelaere's SorterHunter repository at commit `8ba90df607cbdc339409e0b173b5a2ffd60fc911` (71 comparators, 12 layers; SHA-256 of the file `dc139714281074c8fef1ce3cc2835aee8b5e95cc4fe8067cef27454dbd9efbcc`), copied unchanged under the key `comparators`. It is the 71-comparator network shown in Dobbelaere's table, a network of the same size as Figure 17 of Valsalam and Miikkulainen but with 12 layers instead of 17. The data is under the [MIT licence](https://github.com/bertdobbelaere/SorterHunter/blob/8ba90df607cbdc339409e0b173b5a2ffd60fc911/LICENSE) (© 2017 bertdobbelaere); the full notice is in `baseline/LICENSE-SorterHunter.txt` and applies to the baseline certificate, not to submitted shots.

To reproduce:

```bash
python3 problems/p011-sorting-network-17/verify/verify.py problems/p011-sorting-network-17/baseline
```
