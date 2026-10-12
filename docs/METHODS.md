# Placement methods

Implementation details for the pipeline introduced in the [README](../README.md). For scientific assumptions and sensitivity, see [conservation validation](CONSERVATION_VALIDATION.md).

## Candidate geometry

DBSCAN provides coarse transit clusters, not sensor coordinates: a broad cluster centroid can be far from any observation. Eligible centers are observed transit fixes in non-noise clusters. A haversine BallTree counts all transit observations within 400 m, including nearby noise observations as support.

Greedy extraction selects the highest-support eligible center, breaking ties by chronological order. It excludes centers within 800 m of a selection and stops at 15 sites or fewer than five local supporting observations. The main path rejects zero or more than 15 coarse clusters and validates every saved center, count, weight, radius, and separation.

`n_fixes` counts local transit support. `cluster_n_fixes` and `source_cluster_id` preserve coarse-cluster provenance. `support_radius_m` records the radius; `weight_c_i` is local support divided by the maximum, rounded to four decimals. Site IDs are assigned in selection order and are not persistent landmark identities. Dwell centroids are separate diagnostic context, not candidates or a current map layer.

The current movement classification gives 7,065 transit observations and 15 supported sites, with 18–48 local observations per site and minimum separation about 848 m. All selected candidates come from the dominant coarse cluster. This shortlist favors frequent transit observations and can miss rare, important, or geographically diverse locations. It is not a demonstrated corridor-connectivity or poaching-risk model.

Separation makes the monitoring disks disjoint and the proxy proximity penalty zero. This simplifies the optimization instance substantially. The 400 m radius is an assumed monitoring zone, not camera range; [conservation validation](CONSERVATION_VALIDATION.md) documents assumptions and sensitivity.

Run `scripts/extract_pinch_points.py` to regenerate candidates. Geometry regression tests cover unsupported centroids, over-cap inputs, deterministic selection, invalid counts/coordinates/IDs/radii/weights, and overlapping sites. Downstream results and the map have been regenerated for this geometry.

## GPS observation coverage

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

## QAOA execution and sample selection

`scripts/run_qaoa.py` validates the 15-qubit QUBO-to-Ising mapping over all 32,768 assignments, then runs depths 1/2/3 on local Qiskit Aer. It uses exact expectation values during COBYLA optimization, three restarts, at most 200 evaluations per restart, one Aer simulation thread, and 4,096 final measurement shots. A normal run seeds optimizer initialization and sampling with 42. The full optimization benchmark uses local Aer. The separate [Qollab runner](QOLLAB.md) can submit fresh measurements using saved optimized parameters; no IonQ execution is recorded.

The decision rule is **best observed feasible penalized proxy score**, where feasible means at most three sites. Only measured bitstrings can be selected. Ties use higher frequency, then lexicographically smaller Qiskit bitstring. No feasible sample produces null selection; no exact classical answer is substituted. The mode is reported separately, with lexicographic ties. Qiskit's rightmost bit maps to candidate index zero, which maps to the saved site ID.

Reports retain all counts, selected and modal placements, scores, feasible/exact-budget rates, proxy-optimal rate, and expected penalized proxy score. Rates divide by all shots. Proxy-optimal comparisons use absolute score tolerance 1e-9, including tied optima. Score ratios are not GPS coverage percentages and are null for nonpositive reference scores. Best-of-batch selection must not be interpreted as typical quantum behavior.

Canonical `data/qaoa_result_p*.json` and text companions hold seed-42 samples and configuration. `data/benchmarks/` retains all three seeds per depth. Every benchmark trial selected [0,1,2], score 2.8542, covering 883 GPS observations. Mean optimal-shot rates were 5.25%/3.04%/6.60%. See [benchmark methodology](BENCHMARKING.md) for convergence, timing, and limited seed counts.

Tests cover infeasible modes, rare optimal samples, missing feasible samples, under-budget cases, tied optima, bit ordering, malformed counts, and total shots. Input guards check current site IDs, weights, geometry, budget, radius, and objective dimensions. Repair and the map consume these structured results separately.

## Classical budget repair

`scripts/repair_qaoa.py` preserves saved QAOA counts and evaluates the selected raw answer, mode, and every measured outcome before and after deterministic classical repair. Frequencies are unchanged: this is postprocessing, not new quantum sampling.

For more than three sites, remove the site with least unique GPS coverage loss until feasible. For fewer than three, add the site with greatest positive marginal GPS coverage until full or no improvement remains. Ties use ascending actual site ID. Exactly-budget selections are unchanged. Repair is idempotent and is not a swap search or replacement by an exact solution.

The repair objective is all-observation coverage, different from the proxy. Additions improve coverage; trimming can lower coverage to restore the budget. Raw infeasible results retain their coverage count but have null coverage ratios and an invalid-comparison flag. No benefit from extra sensors is counted as a budget-valid improvement.

At every depth, current selected raw and repaired sites are [0,1,2], with no actions. They score 2.8542 (the proxy optimum) and cover 883 observations (82.14% of GPS optimum 1,075). Repair does not close this modeling gap. All observed outcomes become feasible after repair, but this is a deterministic property, not a 100% quantum success rate. Shot-weighted repaired means describe the postprocessed distribution; raw means include infeasible samples and are not budget-valid benchmark comparisons.

Run `scripts/repair_qaoa.py` after QAOA and baseline generation. Outputs `data/qaoa_repair_p*.json` retain selected/modal raw/repaired metrics, action logs, distribution summaries, backend, and hashes. `data/qaoa_repair_samples_p*.csv` retain each observed bitstring, frequency, selections, actions, and metrics. Current artifacts, regenerated from canonical seed-42 benchmark samples, are authoritative.

The stage rebuilds GPS coverage, checks saved matrices and input hashes, recomputes references, and replays selection summaries. Tests cover trimming, positive-gain filling, no-gain stopping, actual-ID ties, zero budget, unchanged full-budget inputs, invalid selections, feasibility/idempotence, and infeasible coverage comparisons. Saved benchmark validation independently checks selected repairs and metrics.
