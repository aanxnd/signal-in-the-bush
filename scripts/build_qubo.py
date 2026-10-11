"""Proxy QUBO and genuine maximum coverage over observed GPS fixes.

The proxy uses transit-support weights; coverage counts each visible Salif Keita
GPS observation within any selected detection disk once, including dwell fixes.
"""
import itertools
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from extract_pinch_points import SENSOR_RADIUS_M, INDIVIDUAL_FILTER, load_data

R_METERS = SENSOR_RADIUS_M  # shared extraction/optimization detection radius
K_BUDGET = 3               # matches van's existing max-coverage branch
PENALTY_SWEEP = [0.5, 1.0, 2.0, 3.0, 5.0]
EARTH_RADIUS_M = 6_371_000

LAKE_BANZENA_SITE_ID = None  # New geometry invalidates the old site-7 association; revalidate before boosting.
LANDMARK_BOOST_MIN_CI = 0.5


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def load_sites(path="data/candidate_sites.csv"):
    df = pd.read_csv(path).sort_values("site_id").reset_index(drop=True)
    ids = df["site_id"].to_numpy(dtype=float)
    weights = df["weight_c_i"].to_numpy(dtype=float)
    if (not np.isfinite(ids).all() or (ids < 0).any()
            or (ids != np.floor(ids)).any() or df["site_id"].duplicated().any()):
        raise ValueError("Site IDs must be unique nonnegative integers.")
    df["site_id"] = ids.astype(int)
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Proxy weights must be finite and nonnegative.")
    if "support_radius_m" in df and not np.allclose(df["support_radius_m"], R_METERS):
        raise ValueError("Candidate support radius differs from optimization radius.")
    df.loc[df["site_id"] == LAKE_BANZENA_SITE_ID, "weight_c_i"] = df.loc[
        df["site_id"] == LAKE_BANZENA_SITE_ID, "weight_c_i"
    ].clip(lower=LANDMARK_BOOST_MIN_CI)
    return df


def distance_matrix(df):
    n = len(df)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            d[i, j] = haversine_m(df["lat"][i], df["lon"][i], df["lat"][j], df["lon"][j])
    return d


def build_overlap_matrix(d, r=R_METERS, w=1.0):
    Q = w * np.maximum(0.0, 1.0 - d / r)
    np.fill_diagonal(Q, 0.0)  # a site doesn't overlap-penalize itself
    return Q


def proxy_objective(x, c, Q, k, A):
    x = np.asarray(x, dtype=float)
    coverage = float(c @ x)
    overlap = float(x @ Q @ x) / 2.0  # Q is symmetric; sum_{i<j} = half of x^T Q x (diag is 0)
    penalty = A * (x.sum() - k) ** 2
    return coverage - overlap - penalty


def brute_force_proxy(c, Q, k, A):
    n = len(c)
    best_x, best_val = None, -np.inf
    for bits in itertools.product([0, 1], repeat=n):
        val = proxy_objective(bits, c, Q, k, A)
        if val > best_val:
            best_val, best_x = val, bits
    return np.array(best_x), best_val


def build_coverage_sets(sites, fixes, r=R_METERS):
    """Boolean site-by-observation matrix; repeated coordinates remain distinct fixes."""
    if not np.isfinite(r) or r <= 0:
        raise ValueError("Detection radius must be finite and positive.")
    site_coords = sites[["lat", "lon"]].to_numpy(dtype=float)
    fix_coords = fixes[["location-lat", "location-long"]].to_numpy(dtype=float)
    for coords in (site_coords, fix_coords):
        if (not np.isfinite(coords).all() or (np.abs(coords[:, 0]) > 90).any()
                or (np.abs(coords[:, 1]) > 180).any()):
            raise ValueError("Coverage coordinates must be finite valid latitude/longitude.")
    return haversine_m(site_coords[:, 0, None], site_coords[:, 1, None],
                       fix_coords[None, :, 0], fix_coords[None, :, 1]) <= r


def validate_coverage_sets(coverage_sets):
    matrix = np.asarray(coverage_sets)
    if matrix.ndim != 2 or not np.isin(matrix, [0, 1]).all():
        raise ValueError("Coverage must be a two-dimensional boolean or binary matrix.")
    return matrix.astype(bool, copy=False)


def true_coverage(chosen_idx, coverage_sets):
    """Return the unique observation count and union mask for selected site indices."""
    coverage_sets = validate_coverage_sets(coverage_sets)
    chosen = list(chosen_idx)
    if any(isinstance(i, (bool, np.bool_)) or not isinstance(i, (int, np.integer)) or i < 0 or i >= len(coverage_sets) for i in chosen):
        raise ValueError("Selected site index outside the coverage matrix.")
    covered = (coverage_sets[chosen].any(axis=0) if chosen
               else np.zeros(coverage_sets.shape[1], dtype=bool))
    return int(covered.sum()), covered


def coverage_budget(coverage_sets, k):
    if np.asarray(coverage_sets).ndim != 2:
        raise ValueError("Coverage sets must be a site-by-fix matrix.")
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or k < 0:
        raise ValueError("Sensor budget must be a nonnegative integer.")
    return min(k, len(coverage_sets))


def exact_max_coverage(coverage_sets, k=K_BUDGET):
    """Exhaustive ground truth over candidate sites (not unrestricted geography).

    Nonnegative unit observation weights permit filling the budget without loss.
    """
    coverage_sets = validate_coverage_sets(coverage_sets)
    budget = coverage_budget(coverage_sets, k)
    best_set, best_cov = (), -1
    for combo in itertools.combinations(range(len(coverage_sets)), budget):
        cov = int(coverage_sets[list(combo)].any(axis=0).sum())
        if cov > best_cov:
            best_cov, best_set = cov, combo
    return best_set, best_cov


def greedy_max_coverage(coverage_sets, k=K_BUDGET):
    coverage_sets = validate_coverage_sets(coverage_sets)
    budget = coverage_budget(coverage_sets, k)
    chosen = []
    covered = np.zeros(coverage_sets.shape[1], dtype=bool)
    for _ in range(budget):
        remaining = [i for i in range(len(coverage_sets)) if i not in chosen]
        best_i = max(remaining, key=lambda i: int((coverage_sets[i] & ~covered).sum()))
        chosen.append(best_i)
        covered |= coverage_sets[best_i]
    return chosen, int(covered.sum())


def main():
    df = load_sites()
    n = len(df)
    c = df["weight_c_i"].to_numpy()
    if not K_BUDGET <= n <= 15:
        raise ValueError("Candidate count must support the sensor budget and stay <=15.")
    fixes = load_data("data/elephant_gps_raw.csv")
    fixes = fixes[fixes["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(drop=True)
    if fixes.empty:
        raise ValueError("No visible observations for the selected individual.")
    coverage_sets = build_coverage_sets(df, fixes)
    d = distance_matrix(df)
    Q = build_overlap_matrix(d)

    print(f"n={n} candidate sites, k={K_BUDGET}, r={R_METERS}m")
    print(df[["site_id", "lat", "lon", "n_fixes", "weight_c_i"]].to_string(index=False))

    print(f"\n--- Proxy QUBO: penalty sweep (target: exactly {K_BUDGET} sites selected) ---")
    chosen_A = None
    for A in PENALTY_SWEEP:
        x, val = brute_force_proxy(c, Q, K_BUDGET, A)
        n_selected = int(x.sum())
        status = "OK" if n_selected == K_BUDGET else f"got {n_selected}, want {K_BUDGET}"
        print(f"A={A}: objective={val:.4f}, sites={df['site_id'].to_numpy()[x==1].tolist()}, selected={n_selected} [{status}]")
        if n_selected == K_BUDGET and chosen_A is None:
            chosen_A = A

    if chosen_A is None:
        raise ValueError("No penalty value produced the required budget; widen PENALTY_SWEEP.")

    x_proxy, val_proxy = brute_force_proxy(c, Q, K_BUDGET, chosen_A)
    proxy_sites = df["site_id"].to_numpy()[x_proxy == 1]
    print(f"\nProxy QUBO exact optimum (A={chosen_A}): sites {proxy_sites.tolist()}, objective={val_proxy:.4f}")
    print("^ this is the ceiling QAOA is being asked to approach -- Track C target.")

    print(f"\n--- True max-coverage baseline (actual visible GPS observations, r={R_METERS}m) ---")
    exact_idx, exact_cov = exact_max_coverage(coverage_sets, K_BUDGET)
    exact_sites = df["site_id"].to_numpy()[list(exact_idx)]
    print(f"Exact optimum: sites {exact_sites.tolist()}, covered weight={exact_cov:.0f} fixes")

    greedy_idx, greedy_cov = greedy_max_coverage(coverage_sets, K_BUDGET)
    greedy_sites = df["site_id"].to_numpy()[greedy_idx]
    ratio = greedy_cov / exact_cov if exact_cov else 1.0
    print(f"Greedy (1-1/e guarantee): sites {greedy_sites.tolist()}, covered weight={greedy_cov:.0f} fixes, ratio={ratio:.3f} (guarantee: >= {1-1/np.e:.3f})")

    # Cross-check: how does the proxy QUBO's chosen set perform under the TRUE coverage metric?
    proxy_idx = list(np.where(x_proxy == 1)[0])
    proxy_true_cov, _ = true_coverage(proxy_idx, coverage_sets)
    gap = proxy_true_cov / exact_cov if exact_cov else 1.0
    print(f"\nProxy QUBO's chosen sites, evaluated under TRUE coverage: {proxy_true_cov:.0f} fixes ({gap:.1%} of true optimum)")
    print("^ this is the 'what did we give up for the qubit budget' number -- README Section 7.")

    result = {
        "individual": INDIVIDUAL_FILTER,
        "demand_definition": "all visible GPS observations for selected individual; unit weight per row",
        "radius_m": R_METERS, "budget": K_BUDGET, "candidate_count": n,
        "demand_fix_count": len(fixes),
        "candidate_union_fix_count": int(coverage_sets.any(axis=0).sum()),
        "exact": {"sites": exact_sites.tolist(), "covered_fixes": exact_cov},
        "greedy": {"sites": greedy_sites.tolist(), "covered_fixes": greedy_cov, "ratio_to_exact": ratio},
        "proxy": {"sites": proxy_sites.tolist(), "penalty_A": chosen_A,
                  "penalized_objective": val_proxy, "covered_fixes": proxy_true_cov,
                  "coverage_ratio_to_exact": gap},
        "coverage_fraction_of_all_fixes": exact_cov / len(fixes),
        "input_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                         for name in ("data/candidate_sites.csv", "data/elephant_gps_raw.csv")},
    }
    Path("data/coverage_baselines.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    np.savez_compressed("data/coverage_sets.npz", coverage=coverage_sets,
                        site_ids=df["site_id"].to_numpy(), demand_indices=np.arange(len(fixes)))
    fixes[["individual-local-identifier", "timestamp", "location-lat", "location-long"]].to_csv(
        "data/coverage_demand.csv", index_label="demand_index")
    print(f"Coverage demand: {len(fixes)} visible fixes; all candidate disks cover {result['candidate_union_fix_count']}; optimal budget covers {exact_cov / len(fixes):.2%} of all fixes.")

    np.save("data/qubo_c.npy", c)
    np.save("data/qubo_Q.npy", Q)
    with open("data/qubo_params.txt", "w") as f:
        f.write(f"k={K_BUDGET}\nr={R_METERS}\nA={chosen_A}\nsite_ids={df['site_id'].tolist()}\n")
    print("\nSaved c, Q, and params to data/ for Track C (QAOA).")


if __name__ == "__main__":
    main()
