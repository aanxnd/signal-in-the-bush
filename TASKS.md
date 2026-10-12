# Project status and completion checklist

Stages 1-8 and 10 are complete for the local prototype. Stage 9 is deferred at the user's request; stages 11-12 remain open. The project is not yet ready to claim a completed competition submission.

1. [x] Reproducible Python 3.11 execution, pinned dependencies, and fail-fast pipeline. Evidence: docs/VALIDATION.md.
2. [x] Observed-location candidate geometry, local support, and 15-site cap. Evidence: docs/METHODS.md#candidate-geometry.
3. [x] Actual GPS observation coverage, exact/greedy references, and separate proxy comparison. Evidence: docs/METHODS.md#gps-observation-coverage.
4. [x] Conservation assumptions, movement quality, radius/threshold/gap sensitivity, and landmark validation. Banzena boost disabled. Evidence: docs/CONSERVATION_VALIDATION.md.
5. [x] Seeded local Aer QAOA, explicit measured-answer selection, complete counts, and sampling metrics. Evidence: docs/METHODS.md#qaoa-execution-and-sample-selection.
6. [x] Classical budget repair, preserved raw results, action logs, and both objective metrics. Evidence: docs/METHODS.md#classical-budget-repair.
7. [x] Ten classical repeats, three seeds per QAOA depth, scoped timings, convergence evidence, and saved-trial validation. Evidence: docs/BENCHMARKING.md and docs/BENCHMARK_RESULTS.md.
8. [x] Generated-results map, distinct placement/range layers, accurate landmark labels, Chrome rendering, and basic accessibility checks. Evidence: docs/DEMO_MAP.md.
9. [ ] Required Qollab/IonQ simulator execution and backend/job/configuration/timing/results evidence. **Deferred; the recorded full benchmark uses local Aer.**
10. [x] Reconcile all project documentation, completion states, data/library/AI disclosures, and video narration with verified results; audit and clean source code. Evidence: README.md, SUBMISSION.md, demo/VIDEO_SCRIPT.md, docs/VALIDATION.md.
11. [ ] Publish or update a runnable public Qollab project with replication instructions, theme, attribution/disclosures, repository link, and accurate backend statement; verify from a logged-out browser. The initial Qollab upload ran but its online map tiles were blocked. A self-contained replacement package is locally tested; corrected on-platform execution and logged-out public verification remain unconfirmed. See [Qollab guide](docs/QOLLAB.md).
12. [ ] Record and attach the two-minute demo video, verify required links/artifacts, and complete the final submission check.

Skipping stage 9 does not satisfy its execution requirement. Before submission, update backend/results statements only from retained evidence and review the current competition requirements.
