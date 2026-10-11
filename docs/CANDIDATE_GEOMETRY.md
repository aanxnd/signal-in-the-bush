# Candidate geometry — step 2

Completed 2026-10-11 using the step-1 Python environment.

## Method

DBSCAN's approximately 3.3 km connectivity can chain many observations across a
large area; its centroid need not lie near a GPS fix. Retain DBSCAN as a coarse
eligibility filter, then subdivide its clusters into supported local detection
areas. Eligible centers are observed transit fixes in non-noise clusters.

For each eligible center, count all transit fixes within the assumed 400 m radius
using a haversine BallTree. Greedily choose the highest-count center, breaking
ties by chronological input order. Exclude other centers within 800 m of each
selection so detection disks do not overlap. Stop at 15 sites or when no center
has at least five local observations. This is an explicit reduction to the qubit
budget, not a claim that every migration corridor is represented.

The main extraction path hard-fails if coarse clustering yields zero or more
than 15 clusters, or if candidate validation fails. It also validates every
candidate's finite coordinates, observed transit location, and local count
before saving the CSV. The target of eight coarse clusters is tuning guidance;
the candidate count is governed by local evidence and the hard maximum of 15.

`n_fixes` now means transit observations within 400 m. `cluster_n_fixes` retains
the parent cluster's total for provenance; `source_cluster_id` records that
cluster, and `support_radius_m` records the radius. Weights are normalized local
counts. Site IDs are newly assigned in selection order and must not be matched
to historical landmarks by ID. Dwell context generation is unchanged.

## Validation

Real extraction completes with 15 sites from 7,066 transit observations. Each
site has 18–48 transit observations within 400 m. An independent calculation
using sklearn's pairwise haversine distances confirms all counts, confirms that
every center matches an observed fix, and finds a minimum center separation of
848.0 m. The union of all 15 candidate disks contains 422 transit observations
(approximately 6% of transit fixes); this is candidate support, not a three-sensor
optimization result or an interception probability.

Three regression tests pass with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

They cover a cluster whose centroid has no local evidence, explicit reduction of
20 supported locations to 15 plus rejection of over-cap input, deterministic
selection, and rejection of insufficient evidence. `git diff --check` passes.

## Limits and downstream work

All 15 strongest separated sites come from the dominant broad cluster. This
frequency-based shortlist can miss rare but important locations; it is not a
geographic fairness or corridor-connectivity model. The 400 m radius, five-fix
minimum, transit-speed classification, single-animal scope, and ecological
meaning still need the conservation-assumptions review in step 4.

The old site-7 Lake Banzena boost is disabled in `build_qubo.py`; assigning the
old label to the new site 7 would be incorrect. Revalidate landmark associations
by coordinates and evidence before restoring any boost.

Only extraction outputs were regenerated. Saved QUBO arrays, QAOA samples, map,
and historical README figures still describe the previous geometry and must not
be used with the new CSV. Step 3 replaces the cluster-demand baseline with actual
GPS-fix coverage; later tasks regenerate optimization results and the map.

## Follow-up audit

Expanded the suite to six passing tests. Fixed validation gaps for duplicate
site IDs, overlapping detection areas, incorrect radius/weights, malformed label
arrays, and invalid coordinates. Tie-breaking now explicitly sorts by timestamp
when present while keeping cluster labels aligned. Optional dwell context can
be empty without preventing extraction. Extraction and optimization now share
one radius constant, and the haversine calculation clips roundoff at its bounds.

The real-data extraction was rerun successfully with the same 15 supported sites.
Added a QAOA input guard that rejects stale QUBO dimensions, site IDs, or weights;
the old eight-site inputs are now rejected before circuit execution. The saved
historical map remains explicitly superseded pending its scheduled update.

The >800 m separation rule deliberately makes detection disks disjoint and
therefore makes the current proximity penalty zero for this shortlist. This is
a simplification of the optimization instance, not evidence that quantum
optimization solves an overlapping-coverage problem. The GPS-fix baseline must
still be implemented and reported honestly in step 3.
