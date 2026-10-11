# Source quality and documentation audit

The source audit removes unused imports and bindings, the unused QAOA dimension argument, unused QUBO conversion return values, redundant path modification, duplicate haversine code, and disabled landmark-boost scaffolding. QAOA conversion uses the equivalent expression `Q + 2*A` directly. Shared distance calculations use the extraction module's clipped haversine implementation. Historical team/README-section references were removed from source comments. Python formatting and import ordering are consistent.

Names such as `c`, `Q`, `A`, `k`, `h`, and `J` follow the documented mathematical model; descriptive function names identify coverage, repair, sampling, and validation. No algorithm or measured benchmark outcome was changed by cleanup. Optional dwell context remains an intentional extraction diagnostic; sensitivity and saved-evidence validators are executable tools, not dead code.

Ruff checks syntax, undefined names, unused imports/bindings, import order, and selected bug-prone patterns. Vulture scans source and tests for dead code at 60% confidence. Their results supplement manual call-site review; static analysis cannot prove the absence of every unused path. The application dependency graph was checked from seven direct libraries; every pinned requirements.txt entry belongs to their required transitive closure on the verified Windows environment. Optional lint tools are separate in requirements-dev.txt and are not runtime dependencies.

Reproduce source checks after installing the optional tools:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check --config ruff.toml scripts tests
.\.venv\Scripts\python.exe -m ruff format --config ruff.toml --check scripts tests
.\.venv\Scripts\python.exe -m vulture scripts tests --min-confidence 60
.\.venv\Scripts\python.exe -m compileall -q scripts tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_benchmarks.py
```

The current regression suite contains 37 tests. Saved benchmark validation checks all nine trials. Qiskit emits deprecation warnings from its pinned QAOAAnsatz dependencies; these do not fail the checks, and a future Qiskit migration should be treated as a separate behavioral change.

After cleanup, extraction, baseline generation, conservation diagnostics, repair, map generation, and saved-benchmark validation were rerun in an isolated copy under `.verification/stage10_validation/`. Candidate bytes, baseline metrics, landmark/quality reports, QUBO coefficients, and all three repair reports matched the existing artifacts. Exhaustive validation of the full 15-qubit Ising conversion passed with maximum error 2.13e-14. The small repeated-seed circuit regression passed; the expensive nine-trial optimizer experiment was not repeated because circuit behavior and objective coefficients were unchanged. All 15 project Markdown documents passed local-link and encoding checks. `git diff --check` passed.

Documentation now states current dates, 15 candidates, coverage versus proxy metrics, local Aer execution, optimization convergence limits, monitoring-radius assumptions, and actual submission status consistently. Original dataset documentation is retained as third-party provenance. Data/library/AI disclosures and required support attribution are preserved in SUBMISSION.md. Code cleanup cannot establish authorship or replace those disclosures.
