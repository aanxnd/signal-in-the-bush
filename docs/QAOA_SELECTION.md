# QAOA execution and sample selection

`scripts/run_qaoa.py` validates the 15-qubit QUBO-to-Ising mapping over all 32,768 assignments, then runs depths 1/2/3 on local Qiskit Aer. It uses exact expectation values during COBYLA optimization, three restarts, at most 200 evaluations per restart, one Aer simulation thread, and 4,096 final measurement shots. A normal run seeds optimizer initialization and sampling with 42. No IonQ/Qollab execution is implemented or claimed.

The decision rule is **best observed feasible penalized proxy score**, where feasible means at most three sites. Only measured bitstrings can be selected. Ties use higher frequency, then lexicographically smaller Qiskit bitstring. No feasible sample produces null selection; no exact classical answer is substituted. The mode is reported separately, with lexicographic ties. Qiskit's rightmost bit maps to candidate index zero, which maps to the saved site ID.

Reports retain all counts, selected and modal placements, scores, feasible/exact-budget rates, proxy-optimal rate, and expected penalized proxy score. Rates divide by all shots. Proxy-optimal comparisons use absolute score tolerance 1e-9, including tied optima. Score ratios are not GPS coverage percentages and are null for nonpositive reference scores. Best-of-batch selection must not be interpreted as typical quantum behavior.

Canonical `data/qaoa_result_p*.json` and text companions hold seed-42 samples and configuration. `data/benchmarks/` retains all three seeds per depth. Every benchmark trial selected [0,1,2], score 2.8542, covering 883 GPS observations. Mean optimal-shot rates were 5.25%/3.04%/6.60%. See [benchmark methodology](BENCHMARKING.md) for convergence, timing, and limited seed counts.

Tests cover infeasible modes, rare optimal samples, missing feasible samples, under-budget cases, tied optima, bit ordering, malformed counts, and total shots. Input guards check current site IDs, weights, geometry, budget, radius, and objective dimensions. Repair and the map consume these structured results separately.
