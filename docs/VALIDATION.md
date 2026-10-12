# Reproduction and validation

Use 64-bit CPython 3.11; Windows Python 3.11.4 is the verified environment. Setup and full pipeline commands are in the [README](../README.md#run-locally). Runtime dependencies are pinned in `requirements.txt`; optional source-check tools are in `requirements-dev.txt`.

## Execution checks

`scripts/run_pipeline.py` runs extraction, coverage/QUBO, QAOA (or repeated benchmarks), repair, and map generation. Each subprocess must succeed and regenerate nonempty expected outputs with fresh modification times, including both map files. Failures stop the pipeline. Saved reports record input hashes; downstream validators reject stale artifacts.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q scripts tests qollab
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_benchmarks.py
```

The regression suite covers movement quality, candidate geometry, coverage, QUBO conversion, sample selection, budget repair, benchmark evidence, the self-contained map, and Qollab packaging. Saved-benchmark validation checks all nine trials, including hashes, counts, convergence histories, selected repairs, and aggregate means/sample standard deviations. Exhaustive Ising validation checks all 32,768 assignments; the recorded maximum error is approximately 2.13e-14.

For complete recomputation, run `scripts/run_pipeline.py --benchmark`, then `scripts/validate_conservation.py`. Rebuilding the map, packaging, and validating saved benchmarks do not rerun optimization. Fixed seeds reproduce sampling on the tested platform/configuration; cross-platform bitwise agreement is not promised.

## Source checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check --config ruff.toml scripts tests qollab
.\.venv\Scripts\python.exe -m ruff format --config ruff.toml --check scripts tests qollab
.\.venv\Scripts\python.exe -m vulture scripts tests qollab --min-confidence 60
```

Ruff checks undefined names, unused imports/bindings, import order, and selected bug-prone patterns. Vulture supplements manual call-site review; static analysis cannot prove that every path is needed. Mathematical names `c`, `Q`, `A`, `k`, `h`, and `J` correspond to the documented objective. Runtime requirements include the transitive dependencies of the seven direct libraries; lint tools are separate.

At 60% confidence, Vulture reports Folium's `default_js`/`default_css` overrides and the test HTML parser's `handle_starttag` callback. These are used by their frameworks; review these findings rather than removing the hooks.

Qiskit emits deprecation warnings from the pinned QAOAAnsatz dependencies. A future Qiskit migration should be checked for behavioral changes. Implementation tests, numerical agreement, and browser checks do not establish ecological effectiveness or complete the outstanding IonQ/publication/video requirements. See the [checklist](../TASKS.md).
