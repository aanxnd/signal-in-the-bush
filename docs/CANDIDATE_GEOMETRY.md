# Candidate geometry

DBSCAN provides coarse transit clusters, not sensor coordinates: a broad cluster centroid can be far from any observation. Eligible centers are observed transit fixes in non-noise clusters. A haversine BallTree counts all transit observations within 400 m, including nearby noise observations as support.

Greedy extraction selects the highest-support eligible center, breaking ties by chronological order. It excludes centers within 800 m of a selection and stops at 15 sites or fewer than five local supporting observations. The main path rejects zero or more than 15 coarse clusters and validates every saved center, count, weight, radius, and separation.

`n_fixes` counts local transit support. `cluster_n_fixes` and `source_cluster_id` preserve coarse-cluster provenance. `support_radius_m` records the radius; `weight_c_i` is local support divided by the maximum, rounded to four decimals. Site IDs are assigned in selection order and are not persistent landmark identities. Dwell centroids are separate diagnostic context, not candidates or a current map layer.

The current movement classification gives 7,065 transit observations and 15 supported sites, with 18–48 local observations per site and minimum separation about 848 m. All selected candidates come from the dominant coarse cluster. This shortlist favors frequent transit observations and can miss rare, important, or geographically diverse locations. It is not a demonstrated corridor-connectivity or poaching-risk model.

Separation makes the monitoring disks disjoint and the proxy proximity penalty zero. This simplifies the optimization instance substantially. The 400 m radius is an assumed monitoring zone, not camera range; [conservation validation](CONSERVATION_VALIDATION.md) documents assumptions and sensitivity.

Run `scripts/extract_pinch_points.py` to regenerate candidates. Geometry regression tests cover unsupported centroids, over-cap inputs, deterministic selection, invalid counts/coordinates/IDs/radii/weights, and overlapping sites. Downstream results and the map have been regenerated for this geometry.
