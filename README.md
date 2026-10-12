# Signal in the Bush

A hybrid quantum-classical experiment that uses real elephant GPS observations to compare sensor placements selected by QAOA and classical coverage algorithms.

**Theme: Quantum Impact**

*This effort is supported by Qollab & IonQ.*

The local prototype is implemented and tested. Computation uses **Qiskit Aer on a local CPU**, not IonQ hardware or Qollab's IonQ simulator. The required IonQ simulator run has been deferred; public project verification and the demo video remain submission tasks. See [submission summary](SUBMISSION.md) and [stage checklist](TASKS.md).

## What it does

1. Read and validate the committed GPS observations, selecting Salif Keita in Gourma, Mali.
2. Classify movement using preceding-step speed, excluding unknown intervals from transit/dwell classification.
3. Use DBSCAN as a coarse filter, then select up to 15 observed transit locations with strong local support.
4. Compute exact and greedy GPS coverage baselines for a budget of three sites.
5. Build a 15-variable proxy QUBO, validate its Ising conversion exhaustively, and run seeded QAOA at depths 1, 2, and 3.
6. Select the best feasible measured proxy answer, preserve raw results, and apply classical budget repair separately.
7. Save reproducible metrics and display classical, raw QAOA, and repaired placements on an interactive map.

The output is a set of candidate coordinates for investigation, not a validated anti-poaching deployment plan.

## Run locally

Use **64-bit CPython 3.11**; the verified Windows environment uses Python 3.11.4. From PowerShell in the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_pipeline.py
Start-Process .\demo\map.html
```

If `.venv` is already installed, start with the pipeline command. No activation, credentials, or dataset download is needed. Installation needs internet access; computation uses committed data locally. The map bundles its Leaflet/jQuery libraries and public-domain Natural Earth boundaries; no online map tiles are requested. Run individual scripts from the repository root.

On macOS/Linux, use `python3.11 -m venv .venv` and `.venv/bin/python` instead of the Windows executable path. Those platforms have not been verified.

To inspect existing results without rerunning QAOA:

```powershell
.\.venv\Scripts\python.exe scripts/build_demo_map.py
Start-Process .\demo\map.html
```

The map has toggles for the trail, candidates, classical optimum, raw/repaired selections at each depth, and an approximate Banzena reference. Zoom in to see the 400 m monitoring circles. Coincident selections have nested outlines; the text table lists all methods independently of color. See the [map walkthrough](docs/DEMO_MAP.md).

For repeated benchmarks, conservation checks, and tests:

```powershell
.\.venv\Scripts\python.exe scripts/run_pipeline.py --benchmark
.\.venv\Scripts\python.exe scripts/validate_conservation.py
.\.venv\Scripts\python.exe scripts/validate_benchmarks.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The normal pipeline runs one seed per depth; `--benchmark` runs seeds 42, 43, and 44 at each depth and ten repeats per classical solver. Both regenerate canonical seed-42 results, repairs, and the map. Computation can take several minutes; benchmarking is longer. Rebuilding only the saved benchmark summary uses `scripts/benchmark_pipeline.py --summarize` and does not run the optimizer.

## Qollab upload package

Run `scripts/package_qollab.py` to create `dist/signal-in-the-bush-qollab.zip`, then upload the ZIP through Qollab's Code → Browse → Files. It contains a visual browser entry, archived comparisons, and fresh backend measurement using previously optimized QAOA parameters. It does not repeat optimization in the browser. See [Qollab guide and verification status](docs/QOLLAB.md). The initial Qollab upload ran but its online map tiles were blocked. The replacement package uses a self-contained map and is locally tested; its on-platform run and public verification remain unconfirmed.

## Data and assumptions

The source package contains two elephants in unrelated areas. This experiment uses **21,972 visible observations of Salif Keita from March 22, 2008 through September 30, 2010**. Habiba's 1,522 observations in Kenya are excluded.

Movement faster than 0.5 km/h is classified as transit when the preceding interval is positive, at most three hours, and no faster than 7 km/h. These are displacement-based heuristics, not observed behaviors. There are 7,065 transit observations and five unknown movement states. All valid visible observations, including dwell and unknown movement, remain GPS coverage demand.

Candidate centers are observed transit locations with at least five transit observations within an assumed **400 m monitoring zone**. The strongest eligible centers are selected until the 15-site cap; centers are separated by more than 800 m. Current sites have 18–48 local transit observations each. All 15 come from the dominant coarse cluster, so the shortlist can miss rare or geographically important locations.

The radius is a planning assumption, **not a camera-trap hardware detection range**. Observational coverage counts GPS rows once each, not distinct animals, detection probability, or prevented poaching incidents. Field deployment requires additional ecological, terrain, access, device, and response-time evidence. Radius/threshold/gap sensitivity and literature sources are in [conservation validation](docs/CONSERVATION_VALIDATION.md).

No current candidate matches Lake Banzena: the nearest is approximately 34.90 km from the approximate gazetteer point. No landmark boost is applied.

## Optimization model

Each binary variable `x_i` indicates whether candidate site `i` is selected. The classical GPS objective counts the union of observations within selected monitoring disks, subject to at most three sites. Exact enumeration checks 455 three-site combinations; greedy repeatedly adds the site with largest marginal coverage.

QAOA maximizes a different, compact proxy:

```text
f(x) = sum_i c_i x_i - sum_(i<j) Q_ij x_i x_j - A (sum_i x_i - k)^2
c_i  = local transit support / largest local transit support
Q_ij = max(0, 1 - distance(i,j) / radius), with Q_ii = 0
k = 3, A = 1
```

The penalty favors exactly three selections, while feasibility means at most three. Penalty calibration exhaustively checks all assignments. The current separated candidates make every pairwise proximity penalty zero; this is a simple instance, not evidence of solving a difficult overlapping-coverage problem. The proximity penalty is a heuristic, not exact disk-intersection area.

The quantum circuit uses one qubit per candidate. It optimizes the negative of `f` as an Ising energy using `x_i=(1-z_i)/2`. Every one of the 32,768 assignments is checked for equivalence before QAOA runs. The proxy is an explicit modeling choice; exact maximum coverage can have other encodings, so we do not claim that it inherently requires one qubit per GPS observation.

Local Aer uses exact expectation values during COBYLA optimization, three restarts, at most 200 evaluations per restart, one simulation thread, and 4,096 final measurement shots. The selected answer is the best feasible **observed** penalized proxy score, with ties by frequency and then bitstring. The most frequent answer is reported separately. No feasible sample produces a null selection, not a substituted classical optimum.

Classical repair trims the site with least GPS coverage loss or fills with greatest positive gain, breaking ties by site ID. Exactly-budget placements are unchanged. Repair is not a replacement search for the classical optimum. See the [methods guide](docs/METHODS.md) for candidate geometry, coverage, sample selection, and repair.

## Verified results

| Method | Selected site IDs | Covered GPS observations | Relative to GPS optimum |
|---|---|---|---|
| Exact GPS coverage | 0, 1, 4 | 1,075 | 100% |
| Greedy GPS coverage | 0, 4, 1 | 1,075 | 100% |
| Exact proxy | 0, 1, 2 | 883 | 82.14% |
| Selected QAOA, depths 1/2/3 | 0, 1, 2 | 883 | 82.14% |
| Repaired selected QAOA, depths 1/2/3 | 0, 1, 2 | 883 | 82.14% |

All nine seeded benchmark trials selected the proxy optimum, score 2.8542. That score is not a coverage percentage. Mean proxy-optimal measurement rates at depths 1/2/3 were **5.25%, 3.04%, and 6.60%**; the selected answer is not representative of every measurement. All sampled outcomes are feasible after repair, but selected answers already use three sites and are unchanged.

The GPS optimum covers **4.89% of all observations**, not the entire track. All 15 candidate disks together contain 2,085 observations. The 82.14% figure measures the modeling gap relative to this candidate-constrained optimum; it is not a quantum success rate.

Mean wall times were about 17.8 ms for exact GPS coverage, 4.9 ms for greedy, 268 ms for exact proxy, and 14.86/50.95/66.39 seconds for hybrid depths 1/2/3. Classical timings cover the solver call; hybrid timings include circuit construction, optimization, sampling, selection, and selected-placement repair/evaluation. They are scoped measurements, not equal end-to-end deployment timings. See [full means and sample standard deviations](docs/BENCHMARK_RESULTS.md) and [methodology](docs/BENCHMARKING.md).

All depth-1 benchmark runs had all optimizer restarts converge. No depth-2/3 run had all restarts converge within the limit. Their finite measured results are retained and labeled. Three seeds do not establish a reliable depth trend. **No quantum speed or quality advantage is demonstrated.**

## Repository guide

| Location | Contents |
|---|---|
| `scripts/extract_pinch_points.py` | Data validation, movement classification, candidate extraction |
| `scripts/build_qubo.py` | GPS coverage matrix, exact/greedy references, proxy coefficients |
| `scripts/run_qaoa.py`, `scripts/qaoa_samples.py` | Ising validation, seeded QAOA, sample selection |
| `scripts/repair_qaoa.py` | Raw/repaired placement evaluation and distribution diagnostics |
| `scripts/benchmark_pipeline.py`, `scripts/validate_benchmarks.py` | Repeated trials and saved-evidence validation |
| `scripts/validate_conservation.py` | Data quality, sensitivity scenarios, landmark checks |
| `scripts/build_demo_map.py`, `demo/` | Generated map, coordinate manifest, video script |
| `data/` | Raw data, candidates, coverage, QAOA results, benchmarks |
| `tests/` | Regression tests for geometry, movement, coverage, samples, repair, benchmarks, map |

Generated reports record input hashes. Downstream checks reject mismatched inputs rather than silently presenting stale results. `demo/map_data.json` exposes plotted coordinates and selections. `data/benchmarks/config.json` records versions, platform, seeds, and timing scope. Reproduction across platforms or future package versions is not guaranteed bit-for-bit.

## Documentation

- [Methods](docs/METHODS.md): candidate extraction, coverage, QAOA selection, and repair.
- [Conservation validation](docs/CONSERVATION_VALIDATION.md): data quality, assumptions, sensitivity, and landmark checks.
- [Benchmark methodology](docs/BENCHMARKING.md) and [generated results](docs/BENCHMARK_RESULTS.md): experiment configuration, timing scope, and measured outcomes.
- [Map walkthrough](docs/DEMO_MAP.md) and [Qollab guide](docs/QOLLAB.md): interactive controls and browser submission package.
- [Validation](docs/VALIDATION.md): reproduction and source checks.
- [Submission summary](SUBMISSION.md), [completion checklist](TASKS.md), and [video script](demo/VIDEO_SCRIPT.md): submission material and remaining work.

## Attribution and license

Dataset: Wall J, Wittemyer G, LeMay V, Douglas-Hamilton I, Klinkenberg B (2014), *Data from: Elliptical Time-Density model to estimate wildlife utilization distributions*, Movebank Data Repository, [doi:10.5441/001/1.f321pf80](https://doi.org/10.5441/001/1.f321pf80). CC0 1.0; original package terms and attribute descriptions are retained in [README_dataset.txt](data/README_dataset.txt).

Associated paper: Wall et al. (2014), *Methods in Ecology and Evolution*, [doi:10.1111/2041-210X.12218](https://doi.org/10.1111/2041-210X.12218). Gourma context: Wall et al. (2013), *Biological Conservation* 157, 60–68, [doi:10.1016/j.biocon.2012.07.019](https://doi.org/10.1016/j.biocon.2012.07.019).

Project code: [MIT](LICENSE). Dependencies retain their own licenses. Qiskit/Aer supply simulation, SciPy optimization, NumPy/pandas data processing, scikit-learn clustering/neighborhood queries, and Folium mapping. Requirements include pinned transitive dependencies. AI assistance is disclosed in [SUBMISSION.md](SUBMISSION.md#disclosure).
