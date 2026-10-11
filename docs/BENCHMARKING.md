# Metrics and timing — stage 7

`benchmark_pipeline.py` measures the corrected 15-site instance on one machine.
Classical exact GPS coverage, greedy GPS coverage, and exact proxy enumeration
each receive one untimed warm-up followed by ten timed runs. They are deterministic;
repeat variation measures runtime rather than different randomized solutions.
QAOA depths 1/2/3 each run with seeds 42/43/44, three COBYLA restarts per run,
maximum 200 evaluations per restart, and 4096 final shots. The optimizer and
sampler both receive the run seed. Aer uses one CPU simulation thread explicitly.

The estimator computes ideal exact expectation values (default precision zero);
only final measurement sampling is shot-based. These are local CPU simulator
measurements, not quantum hardware timings or IonQ/Qollab results. Three seeds
are descriptive evidence, not a statistically robust performance study.

## Timing boundaries

All durations use `time.perf_counter()` wall clock. Common data loading and
coverage construction are measured separately once. Reference optimum searches,
QUBO-to-Ising validation, and coefficient derivation are outside solver timings.
Classical rows time the solver call; placement-quality reporting follows outside
that call. Hybrid rows time Hamiltonian construction, ansatz construction,
optimization, final sampling, full sample-distribution selection, and repair and
quality evaluation of the selected placement. Substage times are also retained.
Entire-distribution diagnostic repair, artifact writes, imports, extraction,
and shared input preparation are excluded from hybrid solver timings.

Thus these are explicitly scoped solver comparisons, not complete deployment
latencies. Hybrid includes small quality-reporting overhead beyond the classical
solver call. Exact proxy enumeration solves the same objective as QAOA, while
exact/greedy GPS coverage answer the conservation objective. Those objectives
must remain separate. No speed advantage is claimed.

No quantum warm-up is added: circuit setup is part of each timed hybrid run.
Library caches, operating-system scheduling, and other machine activity can
affect wall time. Package versions, OS/CPU description, inputs, seeds, threads,
configuration, and shared-preparation time are recorded in `data/benchmarks/config.json`.

## Convergence and quality metrics

Every optimizer restart saves initial/final parameters, parameter order, final
energy, evaluation count, full energy history, status, success flag, message,
and elapsed time. A nonconverged restart is retained, not discarded. A finite
optimizer result can still yield useful samples; sampling quality and numerical
optimizer success are reported separately.

Every run saves its full sample counts, mode, selected feasible raw output,
sampling rates, selected-placement repair actions, and raw/repaired metrics.
GPS coverage ratios use the exact feasible GPS optimum; penalized proxy scores
use the exact proxy objective separately. No feasible sample is recorded as a
selection failure rather than replaced with a classical answer. Aggregate
quality columns condition on successful selection and show that run count.

`data/benchmark_metrics.csv` reports means and **sample standard deviations**
(ddof=1), not standard errors, across ten classical repeats and three hybrid
seeds. It includes runtime, coverage, coverage ratios, sampling rates, proxy
score, and convergence counts as applicable. `docs/BENCHMARK_RESULTS.md` presents
the resulting comparison table. Benchmark run records are the underlying evidence.

## Reproduction

After extraction and `build_qubo.py`, run:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/benchmark_pipeline.py
.\.venv\Scripts\python.exe -X utf8 scripts/repair_qaoa.py
```

Or use `scripts/run_pipeline.py --benchmark` for the pipeline including repeated
benchmarking. Without that flag the runner performs one seed-42 run per depth.
The benchmark publishes seed-42 results as `data/qaoa_result_p*.json/.txt` with
convergence logs, preserving other seeds under `data/benchmarks/`. Repair outputs
must be regenerated afterward; the repeated benchmark does not silently reuse
old sample artifacts. The later map task still needs its scheduled correction.

To regenerate only the summary from saved benchmark trials, use
`scripts/benchmark_pipeline.py --summarize`; this performs no new optimization.
Sampling is repeatable for fixed versions/configuration on the same platform;
bit-for-bit agreement across architectures or future library versions is not promised.

Run `scripts/validate_benchmarks.py` to check the saved trials without new
optimization: it checks input hashes, shot totals, convergence evidence,
sampling rates, raw/repaired coverage, and aggregate timing means/std.

## Findings and checks

All nine seeded trials selected [0,1,2], attaining the proxy optimum and covering
883 observations (82.14% of the GPS optimum). Mean proxy-optimal sampling rates
at depths 1/2/3 were 5.25%/3.04%/6.60%, with substantial seed variation at the
deeper depths. Every depth-1 run had all restarts converge; no depth-2 or depth-3
run had all restarts converge within 200 evaluations per restart. These finite
runs still produced measured samples, and those results are retained as observed.

Classical exact GPS coverage and greedy each cover 1,075 observations. Their
mean times are approximately 17.8 ms and 4.9 ms; proxy exact enumeration averages
268 ms. These measurements replace the older unsupported microsecond claim.
The classical algorithm is much faster at this instance size. Larger depth
does not establish a reliable quality improvement from these three seeds.

All 32 tests pass, including a two-qubit repeated-seed sampling check and
convergence-history checks. `validate_benchmarks.py` passes for all nine trials;
current seed-42 repair outputs were regenerated. A summary-only path error was
fixed and the final summary regenerated successfully from the raw trial files.
Syntax and whitespace checks pass. No repeated benchmark is inferred from
the older single-run timing values.

## Dedicated stage-7 audit

Fixed incomplete/duplicate seed-set acceptance in summary generation, added
hash checks to summary-only execution, and strengthened current radius/budget
checks before future benchmark runs. New run records also include the raw GPS
hash directly, in addition to the batch configuration's existing raw-data hash.
The generated report now explicitly shows successful-selection denominators.

Replaced removable Python assertions in the artifact validator with explicit
errors. Validation now reconstructs coverage from GPS coordinates, recomputes
both exact references, checks trial selection/rates, classical repeat identities,
all quality means and standard deviations, and convergence counts. The evidence
passes under ordinary and optimized (`-O`) Python. An intentionally corrupted
sampling-rate summary was correctly rejected. All 32 tests pass, including
missing/duplicate-seed regression cases; syntax and whitespace checks pass.

Timings, samples, selected placements, and scientific findings are unchanged.
No expensive optimizer rerun was needed: changes affect input/report validation,
not the measured circuit or solver behavior. Existing timing-boundary asymmetry
is explicitly disclosed above; the results remain scoped solver measurements.
