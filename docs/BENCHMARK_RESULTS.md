# Repeated local benchmark results

All timings are seconds, mean +/- sample standard deviation. See [benchmark methodology](BENCHMARKING.md) for scope and limitations.

| Method | Depth | Runs | Time (s) | Covered fixes | Coverage / exact |
|---|---|---|---|---|---|
| exact_gps_coverage | - | 10 | 0.017834 +/- 0.002821 | 1075.00 | 100.00% |
| greedy_gps_coverage | - | 10 | 0.004901 +/- 0.000532 | 1075.00 | 100.00% |
| exact_proxy | - | 10 | 0.268369 +/- 0.043790 | 883.00 | 82.14% |
| QAOA_selection_repair | 1 | 3 | 14.859704 +/- 7.557083 | 883.00 | 82.14% |
| QAOA_selection_repair | 2 | 3 | 50.947861 +/- 6.387000 | 883.00 | 82.14% |
| QAOA_selection_repair | 3 | 3 | 66.394231 +/- 2.658497 | 883.00 | 82.14% |

GPS coverage and proxy scores are different objectives. Quantum figures include classical sample selection and selected-placement repair. Three seeds are descriptive; no quantum speed advantage is claimed.
Coverage means condition on successful selection. Successful hybrid selections by depth: p=1: 3/3, p=2: 3/3, p=3: 3/3.
