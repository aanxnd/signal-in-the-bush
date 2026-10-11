# Conservation assumptions and data quality — stage 4

## Scope and what the model means

This is retrospective evidence from **one collared elephant, Salif Keita**,
recorded from **22 March 2008 to 30 September 2010**, not 2008–2014. The full
package contains 23,494 observations: 21,972 for Salif Keita and 1,522 for Habiba,
not the earlier documentation's 330. Habiba remains excluded from optimization.
No multi-animal validation, poaching observations, patrol access constraints,
prospective detection study, or deployment trial is available. Selected sites
are supported movement-observation hotspots, not proven corridor bottlenecks or
measured reductions in poaching.

## Radius and movement classification

The default **400 m radius is an assumed circular monitoring/planning zone**,
not a measured camera-trap detection distance or guaranteed ranger coverage.
Ordinary motion-triggered cameras operate at much shorter ranges: an elephant
camera study describes capture up to approximately 25 m, while a Gabon field
study placed cameras about 4 m from elephant paths. Sources:
[camera identification study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10064994/),
[Gabon field study](https://besjournals.onlinelibrary.wiley.com/doi/10.1111/2041-210X.14036).
The monitoring-zone interpretation preserves the demonstration instance without
claiming unsupported hardware capabilities. Deployment would require terrain,
device, viewing-angle, access, and response-time calibration.

The **0.5 km/h transit threshold is a heuristic**, not a validated behavioral
classifier. It distinguishes faster from slower hourly displacement, not observed
walking from feeding/resting. The track median is approximately 0.267 km/h.
Straight-line step speed underestimates actual traveled distance and misses
movement between hourly fixes. Speed at an endpoint describes the preceding
interval, not necessarily its instantaneous activity.

[Wall et al. 2013](https://www.savetheelephants.org/wp-content/uploads/2016/11/Wall-et-al.-2013-Characterizing-properties-and-drivers-of-long-dist.pdf)
describes hourly collars and a 7 km/h upper speed filter for GPS quality control.
We use that upper bound as a review/classification limit. The default maximum
classifiable gap of 3 hours is an explicit modeling choice, tested below.
First observations, nonpositive intervals, longer gaps, and speeds above the
limit have unknown movement state; they cannot enter transit or dwell clustering.
Unknown movement does not by itself invalidate a GPS location for the all-fix
coverage metric. Duplicate times or missing/invalid coordinates fail loading
instead of being silently repaired. This dataset has no such failures.

## Quality findings

`data/data_quality.json` records the raw-data hash and audit:

- No missing/invalid timestamps or coordinates, duplicate individual timestamps,
  duplicate event IDs, or nonpositive step intervals for the selected elephant.
- Maximum step speed 6.468 km/h; none exceeds 7 km/h.
- Four gaps exceed 3 hours; the longest is 110 hours.
- Five fixes have unknown movement state (first fix plus four gap endpoints).
- Default transit count is now 7,065; all-fix coverage demand remains 21,972.

At gap limits of 1/3/6/24 hours the unknown counts are 30/5/5/2 and transit
counts are 7,061/7,065/7,065/7,066. A long-gap mean speed cannot reveal whether
an elephant spent the interval resting or moving. No interpolation was added.

## Sensitivity checks

`data/conservation_sensitivity.csv` contains 15 combinations of thresholds
0.25/0.5/1.0 km/h and radii 25/100/200/400/800 m. Each combination regenerates
candidate centers and recomputes actual coverage. Coarse DBSCAN epsilon is fixed
at 3295.5 m to isolate these two parameters; the qubit cap and five-fix local
support rule remain. Each run chooses up to three sensors, and `budget_used`
explicitly identifies scenarios with fewer than three supported candidates.

At the default threshold, radius 25/100/200/400/800 m yields exact coverage
37/182/529/1,075/2,154 observations. At radius 400 m, threshold 0.25/0.5/1.0 km/h
yields 1,323/1,075/475 observations and proxy-to-exact ratios 88.44%/82.14%/33.05%.
These are different regenerated instances, not a proof of monotonicity in radius
or robustness of the selected placements. Candidate IDs are local to each run.
The proxy comparison uses top transit weights, which exactly solves its constrained
selection objective here because candidate separation makes the overlap penalty zero.

Default extraction and baseline were regenerated after movement-quality fixes:
the default exact/greedy coverage remains 1,075 and proxy coverage remains 883.
Historical QAOA and map artifacts still await their scheduled updates.

## Lake Banzena and boost decision

The source paper identifies **four** lakes that usually retain water, including
Banzena, and notes that they can dry out; earlier claims of only two lakes that
never dry out are unsupported. This supports regional water importance, not a
numerical site weight or guaranteed year-round access.

The [GeoNames wetland entry](https://www.geonames.org/advanced-search.html?country=ML&featureClass=H&q=&startRow=250)
places Oualet Benzena approximately at (15.663, -2.5878). This is a gazetteer
point, not a surveyed shoreline. The historical centroid from commit `b097931`
at (15.592857, -2.594564) is 7.83 km away, broadly corroborating the old ~8 km
distance only. Even that is far beyond a 400 m zone and cannot establish lake
coverage. The nearest current site is site 13, **34.90 km** from the approximate
point. No current candidate gets a Lake Banzena label or boost.

`data/landmark_boost_sensitivity.csv` deliberately tests a hypothetical boost
to the nearest current candidate, not a verified landmark match. Floors of
0/0.25/0.5 leave the proxy result at 883; floors 1/2 force a different placement
with 878 covered observations. That numerical perturbation does not validate
ecological benefit. The actual boost remains disabled until a coordinate match,
field evidence, and defensible weight calibration exist.

## Reproduce and validation

From the root in the pinned Python environment:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/extract_pinch_points.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_qubo.py
.\.venv\Scripts\python.exe -X utf8 scripts/validate_conservation.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The validation script saves quality, radius/threshold sensitivity, gap sensitivity,
landmark checks, and hypothetical boost sensitivity. It does not overwrite
candidate sites for the sensitivity scenarios. All 15 tests pass, including
unknown-state handling and missing/duplicate timestamp rejection. These checks
validate the implementation and expose assumptions; they do not validate a
field-ready anti-poaching system.

## Follow-up audit

All 17 tests pass after fixing unsorted speed inputs, duplicate event-ID handling,
and empty clustering/context inputs. The quality report now records the actual
classification constants and invalid-coordinate count. Landmark output records
the current candidate-file hash. `data/sensitivity_candidates.csv` retains
coordinates and local support for every scenario; the sensitivity summary also
saves proxy selections. This makes the reported scenario IDs independently
reconstructible. An independent sklearn haversine calculation and exhaustive
enumeration reproduced every scenario's optimum, proxy count, and candidate
union, as well as the landmark distance and candidate hash. Scientific conclusions
and default coverage are unchanged. Syntax and whitespace checks pass.
