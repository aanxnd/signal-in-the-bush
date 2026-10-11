"""
Track A: corridor/pinch-point extraction (see README.md Section 5).

Splits GPS fixes into dwell (resting/feeding/watering) vs transit (moving
through) before clustering. Candidates are movement-observation hotspots;
their status as real corridor bottlenecks requires independent field evidence.

Candidate n_fixes counts transit observations within 400 m, not whole-cluster
membership. Broad DBSCAN clusters provide eligible observations, not centers.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree

EARTH_RADIUS_M = 6_371_000
DWELL_SPEED_THRESHOLD_KMH = 0.5
MIN_CLUSTERS = 8
MAX_CLUSTERS = 15
SENSOR_RADIUS_M = 400.0
MIN_LOCAL_TRANSIT_FIXES = 5
MAX_SPEED_KMH = 7.0  # Wall et al. 2013 hourly GPS quality-control threshold
MAX_STEP_GAP_HOURS = 3.0  # modeling choice; longer intervals have unknown movement state

# This data package bundles two elephants from unrelated populations thousands
# of km apart (Salif Keita: Gourma, Mali; Habiba: central Kenya) -- the Wall et
# al. 2014 paper used them as separate method examples, not a shared habitat.
# Mixing them into one sensor-placement problem is not ecologically meaningful,
# so we scope to one coherent population. Salif Keita has ~24x the transit fixes
# (richer corridor signal) and dedicated literature on this exact population's
# movement drivers (Wall et al. 2013, Biological Conservation).
INDIVIDUAL_FILTER = "Salif Keita"


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def load_data(path):
    df = pd.read_csv(path)
    df = df[df["visible"].astype(str).str.lower() == "true"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    coords = df[["location-lat", "location-long"]].to_numpy(dtype=float)
    if (df["timestamp"].isna().any() or df["individual-local-identifier"].isna().any()
            or not np.isfinite(coords).all() or (np.abs(coords[:, 0]) > 90).any()
            or (np.abs(coords[:, 1]) > 180).any()):
        raise ValueError("Visible fixes contain missing/invalid time, individual, or coordinates.")
    if df.duplicated(["individual-local-identifier", "timestamp"]).any():
        raise ValueError("Duplicate individual timestamps require explicit data review.")
    if "event-id" in df and df["event-id"].duplicated().any():
        raise ValueError("Duplicate event IDs require explicit data review.")
    df = df.sort_values(["individual-local-identifier", "timestamp"]).reset_index(drop=True)
    return df


def compute_speed(df):
    df = df.sort_values(["individual-local-identifier", "timestamp"], kind="stable").copy()
    grouped = df.groupby("individual-local-identifier")
    df["prev_lat"] = grouped["location-lat"].shift(1)
    df["prev_lon"] = grouped["location-long"].shift(1)
    df["prev_time"] = grouped["timestamp"].shift(1)
    dist_m = haversine_m(df["prev_lat"], df["prev_lon"], df["location-lat"], df["location-long"])
    dt_h = (df["timestamp"] - df["prev_time"]).dt.total_seconds() / 3600.0
    df["step_gap_hours"] = dt_h
    df["speed_kmh"] = ((dist_m / 1000.0) / dt_h.where(dt_h > 0))
    df["movement_known"] = (dt_h.gt(0) & dt_h.le(MAX_STEP_GAP_HOURS)
                            & df["speed_kmh"].between(0, MAX_SPEED_KMH))
    return df


def split_dwell_transit(df, threshold=DWELL_SPEED_THRESHOLD_KMH):
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("Transit threshold must be finite and positive.")
    df["is_transit"] = df["movement_known"] & df["speed_kmh"].gt(threshold)
    df["is_dwell"] = df["movement_known"] & df["speed_kmh"].le(threshold)
    return df


def run_dbscan(points_df, eps_m, min_samples=5):
    if not np.isfinite(eps_m) or eps_m <= 0:
        raise ValueError("Clustering radius must be finite and positive.")
    if points_df.empty:
        return np.array([], dtype=int), 0
    coords = np.column_stack([
        np.radians(points_df["location-lat"].values),
        np.radians(points_df["location-long"].values),
    ])
    labels = DBSCAN(eps=eps_m / EARTH_RADIUS_M, min_samples=min_samples, metric="haversine").fit(coords).labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    return labels, n_clusters


def tune_eps_for_cluster_count(points_df, min_clusters, max_clusters, start_eps_m=1500.0, min_samples=5, max_attempts=25):
    eps_m = start_eps_m
    labels, n_clusters = run_dbscan(points_df, eps_m, min_samples)
    for _ in range(max_attempts):
        if min_clusters <= n_clusters <= max_clusters:
            return labels, eps_m, n_clusters
        eps_m *= 1.3 if n_clusters > max_clusters else 0.75
        labels, n_clusters = run_dbscan(points_df, eps_m, min_samples)
    return labels, eps_m, n_clusters  # best effort — caller should check the count


def build_candidate_table(points_df, labels, representative=False):
    if representative:
        return build_local_candidates(points_df, labels)
    tagged = points_df.copy()
    tagged["cluster"] = labels
    clustered = tagged[tagged["cluster"] != -1]
    rows = []
    for cluster_id, group in clustered.groupby("cluster"):
        lat, lon = group["location-lat"].mean(), group["location-long"].mean()
        support = group
        rows.append({
            "site_id": int(cluster_id),
            "lat": lat,
            "lon": lon,
            "n_fixes": len(support),
            "n_individuals": support["individual-local-identifier"].nunique(),
            "individuals": ",".join(sorted(support["individual-local-identifier"].unique())),
        })
    if not rows:
        # Dwell context is optional; preserve a readable CSV even with no clusters.
        return pd.DataFrame(columns=["site_id", "lat", "lon", "n_fixes", "n_individuals", "individuals", "weight_c_i"])
    table = pd.DataFrame(rows).sort_values("n_fixes", ascending=False).reset_index(drop=True)
    if len(table):
        table["weight_c_i"] = (table["n_fixes"] / table["n_fixes"].max()).round(4)
    return table


def build_local_candidates(points_df, labels, radius_m=SENSOR_RADIUS_M):
    """Subdivide broad clusters into distinct, locally supported detection areas.

    Greedily choose observed fixes by local support, excluding centers within
    two detection radii of a chosen center. Stop at the qubit cap or when no
    center has enough support. Noise fixes cannot be centers but count as evidence.
    """
    if not np.isfinite(radius_m) or radius_m <= 0:
        raise ValueError("Radius must be finite and positive.")
    labels = np.asarray(labels)
    if labels.ndim != 1 or len(labels) != len(points_df):
        raise ValueError("Cluster labels must have one entry per transit fix.")
    if points_df.empty:
        raise ValueError("No transit fixes available for candidate selection.")
    points = points_df.reset_index(drop=True)
    if "timestamp" in points:
        order = points.sort_values("timestamp", kind="stable").index.to_numpy()
        points = points.iloc[order].reset_index(drop=True)
        labels = labels[order]
    coords = np.radians(points[["location-lat", "location-long"]].to_numpy())
    if not np.isfinite(coords).all() or (np.abs(coords[:, 0]) > np.pi / 2).any() or (np.abs(coords[:, 1]) > np.pi).any():
        raise ValueError("Transit coordinates must be finite valid latitude/longitude.")
    tree = BallTree(coords, metric="haversine")
    neighborhoods = tree.query_radius(coords, r=radius_m / EARTH_RADIUS_M)
    counts = np.array([len(indices) for indices in neighborhoods])
    eligible = np.asarray(labels) != -1
    rows = []
    while eligible.any() and len(rows) < MAX_CLUSTERS:
        best = int(np.argmax(np.where(eligible, counts, -1)))
        if counts[best] < MIN_LOCAL_TRANSIT_FIXES:
            break
        support = points.iloc[neighborhoods[best]]
        center = points.iloc[best]
        cluster = int(labels[best])
        rows.append({
            "site_id": len(rows),
            "source_cluster_id": cluster,
            "lat": center["location-lat"], "lon": center["location-long"],
            "n_fixes": len(support),
            "cluster_n_fixes": int((np.asarray(labels) == cluster).sum()),
            "support_radius_m": radius_m,
            "n_individuals": support["individual-local-identifier"].nunique(),
            "individuals": ",".join(sorted(support["individual-local-identifier"].unique())),
        })
        nearby = tree.query_radius(coords[best:best + 1], r=2 * radius_m / EARTH_RADIUS_M)[0]
        eligible[nearby] = False
    if not rows:
        raise ValueError("No locally supported candidate sites; review radius and clustering.")
    table = pd.DataFrame(rows)
    table["weight_c_i"] = (table["n_fixes"] / table["n_fixes"].max()).round(4)
    return table


def validate_candidates(candidates, transit):
    if not 1 <= len(candidates) <= MAX_CLUSTERS:
        raise ValueError(f"Candidate count {len(candidates)} violates 1..{MAX_CLUSTERS} qubit cap.")
    if candidates["site_id"].duplicated().any():
        raise ValueError("Candidate site IDs must be unique.")
    if not np.allclose(candidates["support_radius_m"], SENSOR_RADIUS_M):
        raise ValueError("Candidate support radius does not match the sensor radius.")
    weights = candidates["n_fixes"] / candidates["n_fixes"].max()
    if not np.allclose(candidates["weight_c_i"], weights.round(4)):
        raise ValueError("Candidate weights do not match normalized local support.")
    for row in candidates.itertuples():
        if not np.isfinite([row.lat, row.lon]).all():
            raise ValueError(f"Site {row.site_id} has nonfinite coordinates.")
        distances = haversine_m(row.lat, row.lon, transit["location-lat"], transit["location-long"])
        if not (distances < 1e-6).any():
            raise ValueError(f"Site {row.site_id} is not an observed transit location.")
        count = int((distances <= SENSOR_RADIUS_M).sum())
        if count != row.n_fixes or count < MIN_LOCAL_TRANSIT_FIXES:
            raise ValueError(f"Site {row.site_id} has invalid local transit support: {count}.")
    for i, row in candidates.iterrows():
        others = candidates.loc[candidates.index != i]
        distances = haversine_m(row.lat, row.lon, others["lat"], others["lon"])
        if (distances <= 2 * SENSOR_RADIUS_M).any():
            raise ValueError("Candidate detection areas must have centers more than two radii apart.")


def main():
    df = load_data("data/elephant_gps_raw.csv")
    if INDIVIDUAL_FILTER:
        df = df[df["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(drop=True)
        print(f"Filtered to individual: {INDIVIDUAL_FILTER}")
    df = compute_speed(df)
    df = split_dwell_transit(df)

    transit = df[df["is_transit"]]
    dwell = df[df["is_dwell"]]
    print(f"Total fixes: {len(df)}")
    print(f"Transit fixes: {len(transit)} ({len(transit) / len(df):.1%})")
    print(f"Unknown movement fixes: {int((~df['movement_known']).sum())}")
    print(f"Dwell fixes:   {len(dwell)} ({len(dwell) / len(df):.1%})")

    labels, eps_m, n_clusters = tune_eps_for_cluster_count(transit, MIN_CLUSTERS, MAX_CLUSTERS)
    if not 1 <= n_clusters <= MAX_CLUSTERS:
        raise ValueError(f"DBSCAN produced {n_clusters} clusters; must be 1..{MAX_CLUSTERS}. Adjust clustering before proceeding.")
    print(f"\nDBSCAN eps={eps_m:.0f}m -> {n_clusters} transit clusters")

    candidates = build_candidate_table(transit, labels, representative=True)
    validate_candidates(candidates, transit)
    print(f"Selected {len(candidates)} local sites with >= {MIN_LOCAL_TRANSIT_FIXES} transit fixes within {SENSOR_RADIUS_M:.0f}m (cap {MAX_CLUSTERS}).")
    candidates.to_csv("data/candidate_sites.csv", index=False)
    print(f"\nCandidate sensor sites (-> data/candidate_sites.csv):\n{candidates.to_string(index=False)}")

    dwell_labels, dwell_n = run_dbscan(dwell, eps_m)  # same spatial scale, no qubit constraint
    dwell_sites = build_candidate_table(dwell, dwell_labels)
    dwell_sites.to_csv("data/dwell_sites_context.csv", index=False)
    print(f"\nDwell/rest sites (demo-map context only, NOT sensor candidates): {len(dwell_sites)} found -> data/dwell_sites_context.csv")


if __name__ == "__main__":
    main()
