# GPS-fix coverage baseline — step 3

The demand universe is all 21,972 visible GPS observations for Salif Keita,
including transit and dwell observations. Each row has unit weight. Multiple
observations at the same coordinates remain separate observations; a single
observation inside multiple selected disks is counted only once. This is an
observational coverage metric, not a detection probability, unique-animal count,
or ecological importance score. Data-quality review remains step 4.

`build_qubo.py` builds a boolean site-by-observation coverage matrix using
haversine distance <=400 m. Exact enumeration checks all 455 three-site
combinations among the 15 candidates. Because coverage is nonnegative and
monotone, filling the budget yields an optimum for the up-to-three problem too.
Greedy selects the largest marginal gain each step, breaking ties by sorted
site order. Both solvers operate on the same matrix, as does proxy evaluation.

| Method | Sites | Covered observations | Relative to exact |
|---|---|---|---|
| Exact | [0, 1, 4] | 1,075 | 100% |
| Greedy | [0, 4, 1] | 1,075 | 100% |
| Proxy exact optimum | [0, 1, 2] | 883 | 82.14% |

The exact solution covers 4.89% of the full observation universe. The union of
all 15 candidate disks covers 2,085 observations. “100% of exact” refers only to
the best possible placement among these candidates under this radius and budget,
not all elephant observations or unrestricted geographic placement.

The proxy weights still measure normalized transit support; true coverage here
measures all visible observations. That difference explains the observed
placement gap. It is a modeling tradeoff, not a measured QAOA performance gap.
For the separated shortlist the proximity penalty is zero. The penalty sweep
now rejects A=0.5 (four sensors) and selects A=1.0 (three sensors). The proxy
objective value 2.8542 is not a coverage percentage.

## Artifacts and reproduction

Run `.venv/Scripts/python.exe -X utf8 scripts/build_qubo.py` from the root.
The script saves:

- `data/coverage_baselines.json`: metrics, demand definition, and SHA-256 hashes of inputs.
- `data/coverage_sets.npz`: boolean coverage matrix, row site IDs, and column demand indices.
- `data/coverage_demand.csv`: demand indices, individual, timestamp, and coordinates for each column.
- Regenerated `data/qubo_c.npy`, `data/qubo_Q.npy`, and `data/qubo_params.txt` for the 15-site instance.

The pipeline runner also verifies that all three new coverage artifacts are
regenerated before proceeding. Existing QAOA samples and map are still historical
and must be regenerated in their scheduled tasks. Repeated timing/seed benchmarks
remain step 7; no new benchmark claims are made here.

## Validation

All ten tests pass with `.venv/Scripts/python.exe -m unittest discover -s tests -v`.
Coverage tests include overlapping disks, repeated-location observations,
uncovered observations, empty demand, budget edge cases, invalid coordinates,
and an instance where greedy is strictly worse than exact. An independent
sklearn pairwise haversine calculation matches the entire saved coverage matrix;
independent enumeration of all 455 three-site combinations confirms 1,075 as
the optimum and 883 for the proxy placement. Syntax and whitespace checks pass.

## Follow-up audit

All 13 tests pass. Fixed silent coercion of invalid coverage values, list-input
handling, boolean indices/budgets, invalid or duplicate site IDs, nonfinite or
negative proxy weights, and mismatched candidate/optimization radii. The penalty
sweep now prints actual site IDs rather than row offsets. Randomized overlapping
instances were checked against all subsets up to each budget, confirming exact
solver behavior even when filling the budget is unnecessary.

Reran baseline generation; results remain 1,075 exact/greedy and 883 proxy.
An independent artifact audit matched the demand table back to the visible,
single-animal raw observations, verified timestamps/coordinates, every matrix
entry, site and demand ID mappings, input hashes, the exhaustive optimum, all
reported placements, and regenerated QUBO weights. No step-3 blocker remains.
