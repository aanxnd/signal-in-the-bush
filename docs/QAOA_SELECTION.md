# QAOA sample selection — stage 5

The decision rule is now **best observed feasible penalized proxy score**.
Only bitstrings present in the measured counts are candidates for selection.
Feasible means selecting at most k=3 sensors; under-budget samples are feasible
and remain unmodified until the repair stage. Ties are resolved by higher shot
count, then lexicographically smaller Qiskit bitstring. If no feasible sample
exists, selection is null and explicitly reports failure; no exact answer is
substituted. This is classical selection from quantum samples, not a claim that
the quantum distribution concentrates on the selected answer.

The most frequent bitstring (mode) is reported separately, with ties resolved
lexicographically. Qiskit's rightmost bit corresponds to site index zero; site
indices map to the saved candidate IDs. The report retains the complete counts.

Every depth reports:

- Mode and best feasible sampled placement, their counts and penalized scores.
- Feasible shots/rate (<=k) and exactly-budget shots/rate (=k).
- Proxy-optimal shots/rate, counting every sampled bitstring attaining the exact
  proxy score within absolute tolerance 1e-9, including tied optima.
- Expected penalized proxy score over the full shot distribution.

Rates divide by all shots, not by unique outcomes or just feasible shots.
Exact enumeration supplies the comparison score only; it does not supply a
placement to the selection rule. Proxy score ratios are objective diagnostics,
not GPS coverage percentages; ratios are null if the reference score is nonpositive.
The best sampled result depends on shot budget and postprocessing and must be
reported alongside sampling rates rather than treated as typical behavior.

## Outputs and reproduction

Run `.venv/Scripts/python.exe -X utf8 scripts/run_qaoa.py` from the root.
It validates the full 15-qubit QUBO-to-Ising mapping and runs local Aer at
p=1,2,3, 4096 shots per depth, three COBYLA restarts and maxiter=200 per restart.
Optimizer initializations and final Aer sampling use seed 42. Repeated-run
benchmarking and full convergence logging are still stage 7; this is one run.

`data/qaoa_result_p{1,2,3}.json` is the structured source for mode, selected raw
placement, all counts, rates, backend, configuration, timing, and input hashes.
Text companions now use `mode_bitstring` and `selected_bitstring`, removing the
ambiguous old `best_bitstring` field. The pipeline verifies both file formats.
Only the corrected 15-site instance is evaluated; historical eight-bit samples
must not be scored against the current coefficients. Backend is local Aer,
not IonQ/Qollab. The map remains scheduled for a later update.

## Validation

The suite covers a mode that is infeasible while a rare sample is optimal,
shot-weighted rates, under-budget and absent-feasible cases, tied optima,
deterministic ties, bit ordering, malformed measurements, and count totals.
All 21 project tests pass. Syntax and whitespace checks pass.

## Current local Aer observations

| Depth | Feasible shots / 4096 | Proxy-optimal shots / 4096 | Proxy-optimal rate |
|---|---|---|---|
| 1 | 2,419 | 214 | 5.22% |
| 2 | 2,620 | 156 | 3.81% |
| 3 | 2,867 | 572 | 13.96% |

Mode and best feasible sample both select [0, 1, 2] at all tested depths.
These are proxy-optimal sites, not the GPS-coverage optimum [0, 1, 4]. Finding
them in a finite shot batch does not make the full distribution optimal. The
depth-2 optimal sampling rate is lower than depth 1; one seeded run does not
establish a depth trend. Full Ising validation across all 32,768 assignments
passed with maximum error 2.13e-14. Raw results have not undergone budget repair.

## Follow-up audit

All 22 project tests pass. Added rejection of invalid shot metadata, noninteger
site IDs, negative penalties, asymmetric/self-overlap matrices, and malformed
objective dimensions; list inputs are normalized before validation. The harness
now checks the saved overlap matrix against current geometry, and checks radius
and sensor budget as well as weights and site IDs. A corrupted overlap matrix
was rejected before circuit execution.

Replayed all three distributions and independently verified mode, selected
sample, optimal counts, expected scores, input hashes, and text/JSON agreement.
Results are unchanged. Reran current-input and exhaustive Ising validation
without repeating sampling, since no circuit or optimizer behavior changed.
Syntax and whitespace checks pass; no stage-5 blocker remains.
