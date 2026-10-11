# Signal in the Bush — submission summary

**Theme: Quantum Impact**

*This effort is supported by Qollab & IonQ.*

**Execution status:** verified locally with Qiskit Aer on CPU. The required Qollab/IonQ simulator run is deferred and has not been completed. Public runnable-project verification and a recorded demo video remain open. This summary describes the implemented local prototype and does not certify submission readiness.

## Novelty and creativity

The project applies a hybrid quantum-classical placement experiment to real conservation data: recorded elephant movement in Gourma, Mali. It distinguishes transit-based site selection from all-observation coverage, compares the compact quantum objective with the actual coverage objective, and exposes the consequences on a map. The contribution is the application and reproducible evaluation, not a new quantum algorithm.

## Technical execution

The pipeline validates 21,972 visible observations of Salif Keita from March 2008 through September 2010. It excludes the unrelated Kenya track, classifies movement with explicit quality limits, and selects 15 locally supported observed transit locations. A three-site budget and assumed 400 m monitoring radius define the experiment.

Exact enumeration and greedy solve observation coverage; a 15-qubit QAOA circuit optimizes a transit-weight proxy with a soft count penalty. All 32,768 binary assignments validate the QUBO-to-Ising conversion. Local Aer runs depths 1/2/3 with 4,096 final shots, exact optimizer expectations, three COBYLA restarts, and recorded convergence. Selection uses the best feasible measured proxy answer. Classical budget repair preserves raw outcomes and records changes separately.

All nine benchmark trials, using three seeds per depth, selected sites [0,1,2], matching the proxy optimum. These cover 883 observations, or 82.14% of the candidate-constrained GPS optimum of 1,075 at [0,1,4]. Mean proxy-optimal shot rates were 5.25%/3.04%/6.60%. The selected answers already met the budget and were unchanged by repair. Deeper optimizer runs did not have all restarts converge within their evaluation limit.

Ten classical repeats and three trials per depth retain timings, means/sample standard deviations, input hashes, configuration, counts, and convergence evidence. Classical solvers are faster on this small instance. No quantum advantage is demonstrated. [Benchmark results](docs/BENCHMARK_RESULTS.md) explain outcomes; [methodology](docs/BENCHMARKING.md) defines unequal solver timing boundaries.

## Impact potential and limits

The experiment offers a transparent way to investigate limited monitoring resources. Its current output is not a field-ready recommendation: one animal, an observation-density shortlist, assumed radius, and no poaching-event, terrain, access, or device calibration limit ecological conclusions. The 400 m circles are planning zones, not camera detection specifications. Current candidates are separated, so the proxy's pairwise overlap term is zero. No Banzena candidate association or ecological boost is applied.

## Documentation and reproduction

[README.md](README.md) contains setup, model, results, limitations, and artifact locations. [TASKS.md](TASKS.md) records completion states. [Map guide](docs/DEMO_MAP.md) explains all controls. [Video script](demo/VIDEO_SCRIPT.md) is ready for recording but is not a recorded video. The repository is [aanxnd/signal-in-the-bush](https://github.com/aanxnd/signal-in-the-bush).

## Disclosure

- **Data:** Wall et al. (2014), Movebank Data Repository, doi:10.5441/001/1.f321pf80, CC0 1.0. Full citations and original package terms are linked in the README.
- **Software:** Qiskit, Qiskit Aer, SciPy, NumPy, pandas, scikit-learn, and Folium, with pinned transitive dependencies under their respective licenses. Project code is [MIT](LICENSE).
- **AI assistance:** Claude (Anthropic) assisted earlier development, including code, derivation, debugging, and writing. OpenAI Codex assisted subsequent implementation, audits, tests, and documentation. AI assistance does not constitute independent scientific or field validation; formulas, checks, assumptions, and saved evidence are available for review.
- **Support attribution:** the required Qollab & IonQ acknowledgment above does not imply that IonQ execution has occurred.

## Outstanding submission work

1. Run the corrected experiment on the required Qollab/IonQ simulator and retain backend/job/configuration/results evidence; currently deferred.
2. Update this execution statement and affected results only after that evidence exists.
3. Verify the public Qollab project and runnable instructions from a logged-out session.
4. Record and attach the two-minute video and complete the final submission check.
