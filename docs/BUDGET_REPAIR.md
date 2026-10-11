# Classical budget repair — stage 6

`scripts/repair_qaoa.py` reads saved measured counts, preserving the original
QAOA artifacts. It repairs the stage-5 selected raw placement, the mode, and
every distinct sampled placement. The original shot frequencies are retained;
this is classical postprocessing, not a newly sampled quantum distribution.

## Rule

For more than k sensors, repeatedly remove the site whose removal loses the
fewest uniquely covered GPS observations. For fewer than k, repeatedly add the
site with greatest positive marginal GPS coverage. Ties use ascending actual
site ID. Stop at k, or when no addition improves coverage. Thus a placement may
remain under budget but feasible. An exactly-budget input is unchanged: this
is budget repair, not arbitrary replacement with an exact classical optimum.

The rule uses genuine all-fix GPS coverage, not proxy weights. Additions improve
coverage; trimming can reduce coverage to restore the budget. There is no claim
that repair optimizes the proxy objective or recovers the true coverage optimum.
Action logs identify each changed site and its signed coverage effect. Applying
repair twice gives the same placement. Stage-5 selection semantics are unchanged;
the repaired distribution is diagnostic and is not searched for a replacement
winner. If stage 5 found no feasible sample, its selected output remains null;
the mode and sampled distribution can still be repaired independently.

## Metrics and original stage-6 results

The distribution figures below are the original stage-6 observations. Stage 7
regenerates canonical samples with an explicit thread configuration and reruns
repair; current JSON/CSV outputs are authoritative for the latest observations.

Both raw and repaired placements report penalized proxy score, score ratio to
exact proxy optimum, actual covered fixes, and coverage ratio to the
candidate-constrained GPS optimum. Infeasible raw placements still report their
coverage count, but have a null coverage ratio and an explicit invalid-comparison
flag; using extra sensors cannot count as a budget-valid improvement. The proxy
objective contains its own penalty and remains separately labeled.

For p=1,2,3, selected raw and repaired sites are both **[0,1,2]**: already three
sensors, requiring no changes. They attain proxy score **2.8542 (100% of proxy
optimum)** and cover **883 fixes (82.14% of GPS-coverage optimum 1,075)**. Repair
does not close the objective-modeling gap for these already-feasible selections.

| Depth | Changed shots / 4096 | Feasible after repair | Mean repaired covered fixes |
|---|---|---|---|
| 1 | 2,619 | 100% | 825.03 |
| 2 | 2,658 | 100% | 817.75 |
| 3 | 2,945 | 100% | 915.55 |

These distribution means reflect shot frequencies after deterministic repair,
not new quantum success rates. Raw means include infeasible outcomes and are
explicitly labeled as unsuitable for a budget-valid benchmark. Repair uses a
different objective from the proxy; some repaired samples can cover more GPS
fixes than the proxy-selected answer without being proxy-optimal. No claim of
quantum advantage or statistically established depth trend follows.

## Artifacts and execution

Run `.venv/Scripts/python.exe -X utf8 scripts/repair_qaoa.py` after baseline
generation and QAOA sampling. The pipeline runner now includes this stage before
the map and checks all new output files for freshness.

- `data/qaoa_repair_p{1,2,3}.json`: raw/repaired selected and modal placements,
  action logs, both reference optima, metrics, distribution summary, backend,
  budget/radius, and input hashes.
- `data/qaoa_repair_samples_p{1,2,3}.csv`: every observed bitstring, original shot
  count, raw/repaired sites, action logs, feasibility, scores, and coverage metrics.

The stage rejects stale baseline/sample input hashes, mismatched site mappings,
and stale/corrupt coverage matrices. It rebuilds coverage from current GPS data,
recomputes both reference optima, and replays the stage-5 selection summary before
repair. All results here are from existing local Aer samples, not IonQ/Qollab.

## Validation

All 27 tests pass. Repair tests cover over-budget redundancy, positive-gain fill,
no-positive-gain stopping, deterministic ID ties, zero budget, exactly-budget
identity, invalid selections, random feasibility/idempotence, and suppression of
invalid over-budget coverage ratios. An independent full-distribution audit
verified every saved action delta, raw/repaired coverage count, proxy score,
shot total, changed-shot count, weighted mean, source hash, and repaired budget.
All repaired observed outcomes are feasible. Syntax/whitespace checks pass.

## Follow-up audit

All 29 project tests pass. Added validation for placement-evaluation indices,
duplicate selections, noninteger/negative site IDs, invalid reference metrics,
and objective dimensions. Repair now accepts iterator inputs consistently and
has an explicit regression test for positive-gain ties using actual site IDs.
The stage also checks current geometry/weights/radius/budget, demand-column
indices, and the saved depth/qubit/penalty configuration before using samples.

The post-repair feasibility rate is calculated from actual observed outcomes
and backed by a hard failure if any repair violates the budget; it is no longer
a hardcoded reported number. Regenerated reports retain the same selected
placements, coverage counts, changed-shot totals, and 100% repaired feasibility.
