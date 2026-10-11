# GPS observation coverage

Demand is all 21,972 visible GPS observations of Salif Keita, including transit, dwell, and unknown movement states. Each observation has unit weight. Repeated coordinates remain separate observations; a row inside multiple selected disks is counted once. Coverage is not detection probability, animal count, or ecological importance.

`scripts/build_qubo.py` uses haversine distance <=400 m to build a boolean site-by-observation matrix. Exact enumeration checks all 455 three-site combinations. Nonnegative monotone coverage means filling the budget yields an optimum for the at-most-three problem. Greedy repeatedly adds the largest marginal coverage gain, with ties by sorted site order.

| Method | Sites | Covered observations | Relative to exact |
|---|---|---|---|
| Exact GPS | 0, 1, 4 | 1,075 | 100% |
| Greedy GPS | 0, 4, 1 | 1,075 | 100% |
| Exact proxy | 0, 1, 2 | 883 | 82.14% |

The optimum covers 4.89% of the full observation universe. All 15 candidate disks contain 2,085 observations. “100% of exact” means best among this shortlist, radius, and budget—not unrestricted placement or all movement.

Proxy weights measure transit support; coverage measures all visible observations. This objective difference explains the observed gap. The current separated sites have zero pairwise proximity penalties. Penalty A=0.5 selects four sites; the sweep chooses A=1, whose exact proxy optimum selects three and scores 2.8542. That score is not a coverage percentage.

Outputs are `data/coverage_baselines.json` (metrics and input hashes), `data/coverage_sets.npz` (matrix/site IDs/demand indices), `data/coverage_demand.csv` (column provenance), and the QUBO arrays/parameters. All downstream artifacts use the corrected geometry.

Tests cover overlapping disks, repeated coordinates, empty demand, budget edge cases, invalid data, and an example where greedy is worse than exact. Independent pairwise distances and exhaustive combinations verified the saved matrix and optimum. See [benchmark results](BENCHMARK_RESULTS.md) for repeated timings.
