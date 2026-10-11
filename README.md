# Signal in the Bush — Technical Report
### Quantum-Optimized Anti-Poaching Sensor Placement
Qollab × IonQ Hackathon — Quantum Impact Track

*This effort is supported by Qollab & IonQ.*

## 0. Status

**Sampling update (stage 5):** local Aer results now use the corrected 15-site
instance and explicitly distinguish mode from best feasible sampled output.
Full distributions and sampling rates are in `data/qaoa_result_p*.json`;
see [`docs/QAOA_SELECTION.md`](docs/QAOA_SELECTION.md). Old eight-site quantum
figures below are superseded. Budget repair and coverage evaluation of quantum
outputs are the next stage.

**Conservation review (stage 4):** single-animal evidence covers 2008–2010.
The 400 m radius is an assumed monitoring zone, not ordinary camera-trap range;
0.5 km/h is a heuristic movement split. Long gaps have unknown movement state.
Lake Banzena proximity does not justify a boost for any current candidate.
See [`docs/CONSERVATION_VALIDATION.md`](docs/CONSERVATION_VALIDATION.md) for source
checks, data quality, and sensitivity results. Older narrative below awaits
the scheduled full documentation reconciliation.

**Geometry update (MASTER_TASKS step 2):** extraction now generates 15 observed
transit locations with verified 400 m support, replacing the old eight centroids.
See [`docs/CANDIDATE_GEOMETRY.md`](docs/CANDIDATE_GEOMETRY.md).
The historical eight-site placements, QUBO/QAOA results, map, and numerical
claims below have not yet been regenerated for this geometry. The old site-7
Lake Banzena association/boost is disabled pending evidence for the new sites.
**Coverage update (step 3):** the GPS-fix baseline is now implemented. At k=3,
exact/greedy cover 1,075 of 21,972 visible fixes; the proxy covers 883 (82.14% of
the candidate-constrained optimum). See [`docs/COVERAGE_BASELINE.md`](docs/COVERAGE_BASELINE.md).
QUBO coefficients have been regenerated; old QAOA samples and map remain superseded.

### Reproduce the local pipeline

Use **CPython 3.11 (64-bit)**. The tested environment uses Python 3.11.4 on Windows;
Python 3.14 is not the supported environment for this project. `requirements.txt`
pins all application dependencies, including transitive dependencies.

From a fresh clone, run these PowerShell commands in the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_pipeline.py
```

On macOS/Linux, create the environment with `python3.11 -m venv .venv` and use
`.venv/bin/python` in place of `.\.venv\Scripts\python.exe` (not yet verified there).
No environment activation is required. Package installation requires internet access;
the four computation stages use the committed CSV data and local Aer without credentials.
The runner executes extraction → QUBO → QAOA → map in order, stops on a failed stage,
uses UTF-8 output on Windows, and rejects missing, empty, or stale stage outputs.
Individual scripts must run from the repository root.

Outputs overwrite `data/candidate_sites.csv`, `data/dwell_sites_context.csv`,
`data/qubo_c.npy`, `data/qubo_Q.npy`, `data/qubo_params.txt`,
`data/qaoa_result_p{1,2,3}.txt`, and `demo/map.html`. Open the HTML in a browser;
its external map tiles and JavaScript/CSS require internet access. QAOA sampling
and timings currently vary between runs; this setup reproduces execution, not
identical samples. Modeling, coverage, repair, and metric corrections remain tracked
in `MASTER_TASKS.md`; successful execution does not validate those scientific claims.

This project was selected through the team's internal decision-matrix process (18.0/20, winner over three other candidates including a job-shop-scheduling proposal) — that ideation process lives in the team's separate planning workspace, not in this repo.

**Submission deadline is today:** Sunday, Oct 11, 7:00 PM ET.

Task breakdown for the team: [`TASKS.md`](TASKS.md). Required judging-criteria summary and disclosures: [`SUBMISSION.md`](SUBMISSION.md). Interactive demo map: [`demo/map.html`](demo/map.html).

**Pipeline status:** Tracks A (data), B (QUBO + true baseline), and C (QAOA) are done and validated end to end on real data — run in order: `scripts/extract_pinch_points.py` → `scripts/build_qubo.py` → `scripts/run_qaoa.py` → `scripts/build_demo_map.py`. Both baselines and the QAOA pipeline agree the right 3 sites are [0, 2, 7] (includes Lake Banzena); QAOA's own approximation ratio plateaus at 65% (Section 8). Still open: publishing to Qollab.xyz itself and running on their IonQ simulator specifically (everything above ran locally, per Section 13's advice to validate off the shared queue first), and the demo video.

## 1. Executive Summary

Anti-poaching teams can only cover a handful of the many corridor pinch-points — river fords, fence gaps, trail junctions — where wildlife repeatedly cross. We extract real high-traffic pinch-points from GPS-collar elephant movement data, formulate camera-trap/ranger placement as a budget-constrained max-coverage problem, solve the compact combinatorial core (8–14 binary site decisions) with QAOA on the IonQ simulator via Qollab, and use a classical solver to validate and repair the result. The deliverable is an honest, working hybrid pipeline on real conservation data with a visually and emotionally strong demo — not a speed claim.

## 2. Why Quantum Here, Stated Honestly

At 8–14 binary variables, the search space is at most $2^{14} = 16{,}384$ states — a classical computer enumerates that exactly in microseconds. No speed advantage exists to chase at this size, and none has ever been empirically demonstrated for QAOA over classical methods on standard combinatorial optimization problems *at any size*. The hackathon's own mandate (bounded to <16 qubits, "to avoid execution timeouts on the simulator queue") confirms this is a methodology demo, not a performance claim.

So the honest pitch is: this is an end-to-end hybrid pipeline — real conservation data → corridor extraction → QUBO → QAOA → classical feasibility repair → validated decision — proven to work, with data showing *where QAOA stands* (approximation ratio vs. depth $p$, vs. the exact classical optimum) rather than an overclaimed "quantum beats classical" result. Lead with the real-data pipeline and the conservation framing; let the benchmark numbers be exactly as good (or modest) as they actually are.

## 3. Dataset — Downloaded and Verified

**Wall, Wittemyer, LeMay, Douglas-Hamilton & Klinkenberg (2014), African elephant GPS tracking (source: Save the Elephants)**
- Data package DOI: `10.5441/001/1.f321pf80` — citable, satisfies hackathon mandate #1 ("must use a recognized public dataset")
- License: **CC0 1.0 Universal** (public domain), citation requested but not required
- Downloaded directly via the Movebank Data Repository's REST API, no account needed: `data/elephant_gps_raw.csv` (23,494 fixes), `data/elephant_reference_data.csv`, `data/README_dataset.txt`
- Methods paper: Wall et al. 2014, *Methods in Ecology and Evolution*, doi:10.1111/2041-210X.12218

**What's actually in the file (checked against real data, not a page summary):** two elephants, **not** one population. "Salif Keita" (21,972 fixes, 2008–2014) is in the **Gourma region of Mali** (lon ≈ -1.8 to -2.6, lat ≈ 14.5–15.6, UTM zone 30N) — part of the population known for the longest documented land migration of any African elephant. "Habiba" (330 fixes) is a completely separate individual in **central Kenya** (lon ≈ 37.6, lat ≈ 0.6), thousands of km away. The source paper used both as independent method-demonstration examples, not as a shared habitat — so **this project uses Salif Keita only** (`INDIVIDUAL_FILTER` in `scripts/extract_pinch_points.py`); mixing two unrelated populations into one sensor-placement budget wouldn't be ecologically meaningful.

Bonus: there's a dedicated paper on exactly this population's movement — Wall, Wittemyer, Klinkenberg, LeMay & Douglas-Hamilton (2013), "Characterizing properties and drivers of long distance movements by elephants (*Loxodonta africana*) in the Gourma, Mali," *Biological Conservation*, doi:10.1016/j.biocon.2012.07.019. Worth skimming for the demo narrative and as a literature cross-check on whether our extracted pinch-points land near known movement drivers (this is the non-GPS corroboration demonnslayer asked for, if there's time).

## 4. Pipeline

```
GPS CSV (Movebank)
   │  DBSCAN clustering (haversine)
   ▼
8–15 candidate pinch-points (centroid + crossing-density weight)
   │  QUBO formulation (Section 6)
   ▼
QAOA on IonQ simulator (Qollab, Qiskit 2.x SamplerV2)  ◄──┐ compare
   │  bitstring candidates                                │
   ▼                                                       │
Classical feasibility repair (trim/fill to budget k)       │
   │                                                       │
   ▼                                                       │
Final sensor placement ───────────────────────────► Exact classical optimum
                                                      + greedy (1-1/e) baseline
```

## 5. Step 1 — Corridor / Pinch-Point Extraction

**Team catch (credit: demonnslayer) — fixed below:** raw GPS-fix density is the wrong signal on its own. A cluster of many fixes in one place usually means the animal *stood there a long time* (a waterhole, shade, grazing) — ecologically real, but not what an ambush sensor wants. A corridor bottleneck is about *path geometry* (many transits funnel through a narrow spot), which can show up even with low dwell time. Conflating the two risks placing sensors at rest sites instead of actual crossing points.

**Fix — split dwell from transit before clustering:**
- Load the CSV; keep `individual-local-identifier`, `timestamp`, `location-lat`, `location-long`.
- Sort each individual's fixes by time. For each consecutive pair, compute step speed $v_t = \text{haversine}(p_t, p_{t+1}) / \Delta t$.
- Classify each fix as **dwell** (speed below a threshold — start with the individual's own median speed, or a fixed ecologically-reasoned cutoff like <0.5 km/h) or **transit** (above it).
- Cluster **transit fixes only** with DBSCAN, **haversine metric**, `eps` in meters-equivalent radians, tuned so cluster count lands at **8–15** (this directly becomes qubit count — see Section 6's qubit-budget constraint).
  - `sklearn.cluster.DBSCAN(metric='haversine')` expects radians; convert lat/long first, and convert `eps` from meters by dividing by Earth's radius (~6,371,000 m).
- Per transit cluster: centroid (mean lat/long of members) = candidate site location; member-fix count (optionally time-decayed or revisit-count weighted) = coverage weight $c_i$. Dwell clusters are computed too (they're good for the demo map as "known rest/water sites" context layer) but are **excluded from the sensor-placement candidate set** — say this distinction out loud in the demo narrative, it's the direct answer if a judge asks the same question demonnslayer asked.
- **Guard explicitly for the qubit cap:** if DBSCAN yields >15 transit clusters, either raise `eps`/`min_samples` or merge the lowest-weight clusters into their nearest neighbor until $n \le 15$. Don't discover this after the QUBO is built.

**Stretch goal, not required (demonnslayer's literal suggestion):** corroborate transit clusters against independently-known landmarks via OpenStreetMap's free, keyless Overpass API — query the study bounding box for `waterway=river`, `natural=water`, `barrier=fence`. Annotate each candidate site with distance to the nearest such feature ("this cluster sits 80m from a mapped river crossing") for demo credibility. This is corroborating evidence for the pitch, not a change to the QUBO itself — skip it under time pressure; the dwell/transit split above is the required fix, this is polish.

**This stretch goal already paid off once, manually:** `data/candidate_sites.csv` site_id=7 (65 fixes, low weight) sits ~8km from Lake Banzena — the documented primary dry-season water source for this entire elephant population, one of only two lakes in the region that don't dry up. The *dominant* cluster, site_id=0 (6,603 fixes), is a different, unidentified location ~50km away. In other words: raw fix-count underrates a site that external sources say is the single most ecologically critical bottleneck in the study area. Track B should weigh a known-landmark boost into $c_i$ rather than trusting `n_fixes` alone — see Section 6.

## 6. Step 2 — QUBO Formulation

**What this QUBO actually solves (credit: van, for asking):** this is **not** literal maximum coverage. True max-coverage needs a coverage-indicator variable per *demand point* (e.g. one per GPS fix within range of some site) so the objective can count each covered point once, not once per covering site — that's an OR, not a sum, and OR-logic over binary variables needs auxiliary variables you don't get for free. With thousands of fixes as potential demand points, that's thousands of extra qubits, wildly over the <16 cap. So instead, this formulation approximates coverage with a **pairwise proximity penalty** ($Q_{ij}$ below): instead of counting exactly which area is double-covered, it penalizes picking two sites close enough that they probably double-cover something. It's a budget-constrained weighted-selection problem with a redundancy penalty — closer to what van called a knapsack-with-proximity-penalty than to textbook max-coverage. This is the right call for staying inside the qubit budget, but it means the classical $1{-}1/e$ **guarantee doesn't transfer to this exact objective** — see Section 7 for how we handle that honestly.

Variables:
- $n$ candidate sites (8–14 target, hard cap 15), $x_i \in \{0,1\}$: sensor/team placed at site $i$.
- $c_i \ge 0$: normalized coverage weight of site $i$. Default: normalized `n_fixes` from `data/candidate_sites.csv`. **Known issue (Section 5):** this underrates Lake Banzena (site_id=7), which external sources confirm is the population's primary dry-season water source despite having a low fix count. If time allows, manually boost $c_i$ for any site confirmed near a known landmark (e.g. $c_i \leftarrow \max(c_i, 0.5)$ for a confirmed match) rather than shipping the raw-frequency version uncorrected — otherwise the final writeup should at least name this as a known limitation.
- $d_{ij}$: haversine distance between centroids $i,j$.
- $r$: assumed sensor/camera-trap effective detection radius (pick a defensible domain value, e.g. 300–500 m, and state the assumption in the writeup).
- $Q_{ij} = w \cdot \max(0,\, 1 - d_{ij}/r)$: redundancy weight between sites within range of each other (tunable scale $w$).
- $k$: sensor/ranger-team budget.

$$\text{maximize} \quad f(x) \;=\; \sum_i c_i x_i \;-\; \sum_{i<j} Q_{ij}\, x_i x_j \;-\; A\left(\sum_i x_i - k\right)^2$$

Qiskit minimizes, so the cost Hamiltonian is $C(x) = -f(x)$, mapped to Pauli-$Z$ via $x_i = (1-z_i)/2$.

**The qubit-budget gotcha (read this before using `qiskit_optimization`'s converters):** the textbook path — model $\sum_i x_i \le k$ as an inequality constraint in a `QuadraticProgram` and let `InequalityToEquality` + `LinearEqualityToPenalty` handle it — adds a binary-encoded **slack variable** (roughly $\lceil\log_2(k+1)\rceil$ extra qubits) to turn $\le$ into $=$. At $n=14$ candidate sites that can push you to ~18 qubits, **over** the mandate's <16 cap.

The formulation above avoids this entirely: $(\sum_i x_i - k)^2$ is a **soft** quadratic penalty centered at $k$, not an exact constraint, so it expands directly into linear and quadratic terms in the existing $x_i$ (using $x_i^2 = x_i$ for binary variables) with **zero new variables**. Qubit count stays exactly equal to candidate-site count — comfortably inside budget with headroom to spare.

Tradeoff to know about: this penalty softly biases toward using *exactly* $k$ sites rather than *up to* $k$. That's fine here because unused budget is (almost) never better left unused when $c_i \ge 0$, and it's fully covered by the repair step below regardless. Tune $A$ empirically — start around $A \approx \max_i c_i$ and sweep (e.g. $0.5\times$ to $5\times$) — and **validate the QUBO against the exact classical solver before spending IonQ simulator queue time on it**: if the exact optimum of your QUBO doesn't match the exact optimum of the real constrained problem, fix $A$ first, don't debug it on the quantum side.

## 7. Step 3 — Classical Baselines

Two different baselines, answering two different questions — don't collapse them into one "classical result":

1. **True max-coverage baseline (van's branch):** build real coverage sets — e.g. each candidate site covers the GPS fixes within radius $r$ of it — and solve genuine max-coverage: exact ILP for ground truth, greedy for the real, provable $1-1/e$-approximation heuristic (the guarantee holds here because this *is* the actual submodular set-cover problem). This answers "how good could sensor placement be if we weren't qubit-constrained at all," with $k$ fixed to whatever the team standardizes on (van used $k=3$ — fine, keep it unless there's a reason to change).
2. **Proxy QUBO baseline:** exact brute-force optimum of the *same* pairwise-penalty objective in Section 6 ($n \le 15$, so $2^{15}=32{,}768$ states, microseconds). This is **not** relabeled as "the real optimum" — it's the ceiling for what QAOA is actually being asked to solve, and it's how you validate/tune the penalty weight $A$ before touching IonQ.

**At submission time, report both comparisons, honestly labeled:** (a) QAOA vs. the proxy's own exact optimum — this is the real "how good is our QAOA" number; (b) the proxy's chosen sites evaluated under the *true* coverage metric vs. the true optimum from (1) — this is the honest "what did we give up by compressing into a QAOA-friendly proxy" number. Showing both is a better, more interesting result than hiding the gap.

**Result (`scripts/build_qubo.py`, $n=8$, $k=3$, $r=400$m):** both baselines agree exactly — true max-coverage exact, true max-coverage greedy, and the proxy QUBO's own exact optimum all select the same 3 sites, **[0, 2, 7]** (site 7 = Lake Banzena), at **100% of true-optimum coverage** (6,923 of 6,923 fixes). Greedy's approximation ratio is 1.000 here (guarantee only required $\ge 0.632$). The proxy formulation cost nothing at this scale — gap (b) above is 0%. Robust across a penalty-weight ($A$) sweep from 0.5 to 5.0.

**Timing methodology (mandate #2 — must be "rigorously timed"):** same machine, same problem instance, wall-clock time, mean ± std over multiple runs/seeds for all classical methods. Report this alongside the QAOA numbers even though at this $n$ classical is trivially faster — say so plainly rather than burying it.

## 8. Step 4 — Quantum Pipeline

- Map $C(x)$ to a `SparsePauliOp` Ising Hamiltonian.
- Run QAOA at depth $p \in \{1, 2, 3\}$ via Qiskit 2.x primitives (`SamplerV2`) on the IonQ simulator through Qollab.
- Record shot count, depth, and wall-clock per run — these are the actual "quantum parameters" metrics called for below, and the thing worth plotting against approximation ratio.

**Implementation note:** the standard `qiskit_optimization` QP→QUBO→Ising converter is not used (that's the slack-variable path Section 6 warns against). Instead `scripts/run_qaoa.py` builds $h_i$, $J_{ij}$ directly from $a_i$, $b_{ij}$ (the cost-direction QUBO coefficients) via the standard $x_i=(1-z_i)/2$ substitution, then **numerically validates** the resulting Ising Hamiltonian against the already brute-force-verified QUBO objective — for every one of the $2^n$ bitstrings, not a spot check — before building any circuit. This caught two real bugs during development: an unzeroed diagonal in the overlap matrix (giving every site a spurious self-penalty) and a broken approximation-ratio formula (blew up near zero because it was computed against the shifted/negated cost instead of the original objective). Both are fixed in the current code; the lesson generalizes — don't trust a QUBO→Ising conversion on algebra alone when you can brute-force-check it in milliseconds at this $n$.

**Results (local Aer simulator; run `python scripts/run_qaoa.py`):**

| $p$ | approx. ratio vs. true optimum | sites found |
|---|---|---|
| 1 | -29% (unconverged) | [1, 2, 4, 5] |
| 2 | 65% | [0, 7] |
| 3 | 65% | [0, 7] |

QAOA improves sharply from $p=1$ to $p=2$, then plateaus — it never finds the true 3-site optimum ([0, 2, 7], Section 7) at any tested depth, landing instead on a strong-but-suboptimal 2-site answer. Reported as-is rather than cherry-picked; this is the honest "where QAOA stands" data Section 2 promised. **Run locally on Aer so far** (per this report's own advice to validate off the shared simulator queue first) — running on Qollab's actual IonQ simulator specifically is still open.

## 9. Step 5 — Classical Feasibility Repair

Extend the proposal's repair step slightly:
- **Over budget** ($\sum x_i > k$): greedily trim the lowest-marginal-coverage site first until feasible (as proposed).
- **Under budget** ($\sum x_i < k$): greedily *add* the highest-marginal-value remaining site until budget is used or no positive-marginal site remains — cheap, strictly improves coverage, and cleans up the soft-penalty's occasional under-shoot.

## 10. Evaluation Metrics

| Category | Metric | Result |
|---|---|---|
| Solution quality | Interception coverage vs. true optimum | True max-coverage & proxy QUBO: 100% (agree exactly). QAOA: 65% at $p\ge2$ |
| Computational | Wall-clock, exact/greedy/proxy (brute force, $n=8$) | Microseconds — trivially fast at this $n$, as expected (Section 7) |
| Computational | Wall-clock, QAOA ($p=1,2,3$, local Aer, 3 restarts, 4096 shots) | 6.0s / 17.8s / 23.1s |
| Quantum parameters | Approximation ratio vs. depth $p$ | -29% → 65% → 65% (Section 8) |

Plateau from $p=2$ to $p=3$ is the actual finding here, not a single final number — more restarts/iterations might close the gap to the true 3-site optimum, but weren't pursued further given the build-window time budget; noted as a follow-up, not hidden as a limitation.

## 11. Demo & Visualization

- **Interactive map — done:** [`demo/map.html`](demo/map.html) (built by `scripts/build_demo_map.py`). Real GPS trail (Salif Keita, 2008–2014), all 8 candidate sites sized/colored by weight, the 3 selected sites highlighted gold (including Lake Banzena, labeled), dwell/rest sites shown as a gray context layer. Open it directly in a browser — no server needed.
- **2-minute video pitch:** script in [`demo/VIDEO_SCRIPT.md`](demo/VIDEO_SCRIPT.md) — not yet recorded. Note before recording: say explicitly whether QAOA ran on Qollab's actual IonQ simulator or only validated locally on Aer (true as of this writing) — judges will ask, and the honest answer is a better look than an implied claim that doesn't hold up.

## 12. Hackathon Compliance Checklist

Full list per the official Participant Plan PDF's submission requirements, not just the original 4-item ideation mandate:

| Requirement | Status |
|---|---|
| Recognized public dataset | ✅ Movebank Data Repository, CC0, DOI-backed (Section 3) |
| Classical baseline rigorously timed vs. hybrid | ✅ Run, both baselines agree (Section 7) |
| Quantum problem **under 16 qubits** (i.e. ≤15) | ✅ 8 qubits, by construction (Section 5's cluster-count guard) |
| Built with the Qiskit framework | ✅ Qiskit 2.x throughout |
| Runs on the quantum simulator available through Qollab | ❌ **Ran on local Aer only so far — not yet on Qollab's own IonQ simulator.** Say this honestly in the video if still true when recorded |
| Published and runnable on Qollab.xyz | ❌ **Not yet published.** No account/credentials available to do this outside the team — needs direct action on qollab.xyz |
| A Qollab project page (what/how/replicate) | ❌ Content drafted in [`SUBMISSION.md`](SUBMISSION.md), needs to actually go on the Qollab page |
| Built during the Oct 9–11 build window | ✅ |
| UI accessibility best practices | ⬜ Not specifically audited — lower priority given time, but a 5-minute pass (color contrast, alt text) on whatever ships on Qollab's page is worth it if time allows |
| Written summary (all 4 judging criteria) | ✅ [`SUBMISSION.md`](SUBMISSION.md) |
| Repo MIT-licensed | ✅ Root [`LICENSE`](LICENSE) |
| Mandatory attribution string | ✅ Top of this file, `SUBMISSION.md`, and root `README.md`'s predecessor |
| Disclosure of libraries / AI tool use | ✅ [`SUBMISSION.md`](SUBMISSION.md) |
| Theme tag | ✅ Quantum Impact (stated in `SUBMISSION.md` — also set it explicitly on the Qollab.xyz submission form) |
| Short demo video | ❌ Script ready ([`demo/VIDEO_SCRIPT.md`](demo/VIDEO_SCRIPT.md)), not recorded |
| Code repository link | ✅ This repo, live on GitHub |

**The two blocking ❌ items both require direct action on qollab.xyz that nobody has access to script/automate — they're the critical path to an actual submission, not the code.**

## 13. Execution Plan (time-budget-resilient)

Phases are relative, not clock-anchored, since I don't know how many hours are actually left — tell me and I'll tighten this. Each phase has a cut line for what to skip if you're short on time.

1. **Data + corridor extraction** — download CSV, verify individual count (Section 3), DBSCAN to 8–15 pinch-points.
   *Cut line: if clustering is fighting you, hardcode a reasonable `eps` from a quick histogram of pairwise distances rather than tuning it perfectly.*
2. **QUBO + classical baselines** — build $Q$, run exact + greedy, sanity-check the QUBO's own optimum matches the real problem's optimum (Section 6).
   *Cut line: this step is not optional — it's your mandate #2 deliverable and your QAOA correctness check. Don't skip to save time; everything downstream depends on it.*
3. **QAOA on IonQ/Qollab** — run $p \in \{1,2,3\}$, log shots/timing.
   *Cut line: if the simulator queue is slow, run $p=1$ only and say so honestly in the writeup rather than waiting on a queue past your deadline.*
4. **Repair + metrics table** — apply Section 9's repair, assemble the metrics table (Section 10).
5. **Demo map** — Folium/Plotly map (compliance items in Section 12 are already done).
   *Cut line: a static before/after map image beats no visual. A live interactive map is the stretch goal, not the floor.*
6. **Video pitch** — record last, from whatever actually works by then.

## 14. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Dataset has fewer individuals than hoped, weak "corridor" narrative | Reframe as single-animal revisitation hotspots (Section 3) — still ecologically valid |
| DBSCAN yields >15 clusters, blows qubit budget | Explicit merge/guard step before QUBO construction (Section 5) |
| Automatic QP→QUBO slack variables push past 16 qubits | Use the hand-rolled soft-penalty formulation (Section 6), not the library's inequality converter |
| IonQ/Qollab simulator queue latency eats the clock on deadline day | Run $p=1$ first and bank a result immediately; add $p=2,3$ only if time remains |
| Judges ask "why quantum for 14 variables" | Section 2's honest framing — have it memorized, don't get caught flat-footed |
| Repo missing LICENSE/attribution at submission time | Fixed — see Section 12 |
| High-density GPS cluster is a rest/water site, not a transit bottleneck (caught by demonnslayer) | Dwell/transit speed split before clustering (Section 5) — candidate sites come from transit clusters only |

## 15. Immediate Next Steps

1. ~~Add root `LICENSE` (MIT) + attribution string~~ — done.
2. ~~Download the primary dataset CSV and confirm individual count~~ — done, see Section 3. Scoped to Salif Keita (Gourma, Mali); Habiba excluded (unrelated population).
3. ~~Scaffold the dwell/transit split + DBSCAN corridor-extraction script~~ — done, `scripts/extract_pinch_points.py`. Converged at eps=3296m to 8 transit clusters (within the 8–15 target); output in `data/candidate_sites.csv`. One cluster (6,603 fixes) heavily dominates the other 7 (3–255 fixes each) — a real, expected long-tail for a single-animal migratory corridor, not a bug, but worth a sanity-check against the Wall et al. 2013 paper's described movement drivers before trusting it blindly.
4. Build the QUBO + classical baselines from `data/candidate_sites.csv`, validate QUBO optimum against real-problem optimum before touching IonQ.

See [`TASKS.md`](TASKS.md) for how this splits across the team.

---

## Sources

- [Movebank Data Repository — Wall et al. 2014 African elephant dataset](https://datarepository.movebank.org/entities/datapackage/38e05433-0a6f-49c4-ab77-0511e716786c) — downloaded and verified this session (doi:10.5441/001/1.f321pf80)
- Wall J, Wittemyer G, LeMay V, Douglas-Hamilton I, Klinkenberg B (2014) Elliptical Time-Density model to estimate wildlife utilization distributions. *Methods in Ecology and Evolution*. doi:10.1111/2041-210X.12218
- Wall J, Wittemyer G, Klinkenberg B, LeMay V, Douglas-Hamilton I (2013) Characterizing properties and drivers of long distance movements by elephants (*Loxodonta africana*) in the Gourma, Mali. *Biological Conservation* 157:60–68. doi:10.1016/j.biocon.2012.07.019
