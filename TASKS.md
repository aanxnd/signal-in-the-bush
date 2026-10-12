# Project tasks

The implemented local pipeline is complete through stage 8; stage 10 documentation and code cleanup are complete. Stage 9 is deferred at the user's request. This is not a completed submission. [MASTER_TASKS.md](MASTER_TASKS.md) is the stage checklist.

| Area | Status | Evidence |
|---|---|---|
| Python 3.11 environment and fail-fast runner | Complete | requirements.txt, scripts/run_pipeline.py |
| Observed-location candidates and movement quality | Complete | docs/CANDIDATE_GEOMETRY.md, docs/CONSERVATION_VALIDATION.md |
| Exact/greedy GPS coverage and proxy comparison | Complete | data/coverage_baselines.json, docs/COVERAGE_BASELINE.md |
| Seeded local Aer QAOA and explicit sample selection | Complete | data/qaoa_result_p*.json, docs/QAOA_SELECTION.md |
| Classical budget repair and raw/repaired evaluation | Complete | data/qaoa_repair_p*.json, docs/BUDGET_REPAIR.md |
| Repeated timing, convergence, and evidence checks | Complete | data/benchmarks/, docs/BENCHMARK_RESULTS.md |
| Generated interactive map and accessibility checks | Complete | demo/map.html, docs/DEMO_MAP.md |
| Current documentation, attribution, and source cleanup | Complete | README.md, SUBMISSION.md, docs/CODE_QUALITY.md |
| Required Qollab/IonQ simulator execution | Deferred; not run | Local Aer only; stage 9 remains open |
| Public runnable Qollab project and logged-out verification | Package prepared and locally tested; upload/run/public verification pending | Stage 11, docs/QOLLAB.md |
| Recorded/attached video and final submission check | Open | Stage 12; script only |

The sequential local workflow is extraction → coverage/QUBO → QAOA → repair → map. Repeated benchmarks optionally replace the single-seed QAOA step. Conservation sensitivity is a separate diagnostic command. No mock-data harness or pending branch merge is needed for the current pipeline.
