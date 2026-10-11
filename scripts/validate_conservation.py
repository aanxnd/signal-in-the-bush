"""Reproducible single-animal quality audit and assumption sensitivity checks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from extract_pinch_points import (load_data, compute_speed, split_dwell_transit,
    run_dbscan, build_local_candidates, haversine_m, INDIVIDUAL_FILTER,
    MAX_SPEED_KMH, MAX_STEP_GAP_HOURS, DWELL_SPEED_THRESHOLD_KMH)
from build_qubo import build_coverage_sets, exact_max_coverage, true_coverage, load_sites


def main():
    path = Path('data/elephant_gps_raw.csv')
    raw = pd.read_csv(path)
    selected = raw[raw['individual-local-identifier'] == INDIVIDUAL_FILTER].copy()
    timestamps = pd.to_datetime(selected.timestamp, errors='coerce')
    df = load_data(path)
    df = df[df['individual-local-identifier'] == INDIVIDUAL_FILTER].reset_index(drop=True)
    if df.empty:
        raise ValueError("Selected elephant has no visible observations.")
    df = compute_speed(df)
    gaps = df.step_gap_hours.dropna()
    quality = {
        'individual': INDIVIDUAL_FILTER, 'raw_rows_all_individuals': len(raw),
        'individual_counts': raw.groupby('individual-local-identifier').size().to_dict(),
        'selected_raw_rows': len(selected), 'selected_visible_rows': len(df),
        'missing_or_invalid_timestamps': int(timestamps.isna().sum()),
        'duplicate_individual_timestamps': int(selected.assign(parsed_time=timestamps).duplicated(['individual-local-identifier', 'parsed_time']).sum()),
        'duplicate_event_ids': int(selected['event-id'].duplicated().sum()),
        'missing_coordinates': int(selected[['location-lat', 'location-long']].isna().any(axis=1).sum()),
        'start': str(df.timestamp.min()), 'end': str(df.timestamp.max()),
        'speed_kmh_median': float(df.speed_kmh.median()),
        'speed_kmh_max': float(df.speed_kmh.max()),
        'steps_over_7_kmh': int(df.speed_kmh.gt(7).sum()),
        'gaps_over_3_hours': int(gaps.gt(3).sum()), 'max_gap_hours': float(gaps.max()),
        'unknown_movement_fixes': int((~df.movement_known).sum()),
        'nonpositive_steps': int(gaps.le(0).sum()),
        'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'classification_config': dict(max_speed_kmh=MAX_SPEED_KMH,
            max_step_gap_hours=MAX_STEP_GAP_HOURS, threshold_kmh=DWELL_SPEED_THRESHOLD_KMH),
        'invalid_coordinate_rows': int((~np.isfinite(selected[['location-lat', 'location-long']].to_numpy(dtype=float)).all(axis=1)
            | selected['location-lat'].abs().gt(90) | selected['location-long'].abs().gt(180)).sum()),
    }
    Path('data/data_quality.json').write_text(json.dumps(quality, indent=2) + '\n', encoding='utf-8')
    rows = []
    candidate_rows = []
    # Fixed coarse scale isolates threshold/radius sensitivity from DBSCAN tuning.
    for threshold in (0.25, 0.5, 1.0):
        tagged = split_dwell_transit(df.copy(), threshold)
        transit = tagged[tagged.is_transit]
        labels, clusters = run_dbscan(transit, 3295.5)
        for radius in (25.0, 100.0, 200.0, 400.0, 800.0):
            try:
                sites = build_local_candidates(transit, labels, radius)
            except ValueError as error:
                rows.append(dict(threshold_kmh=threshold, radius_m=radius, status=str(error)))
                continue
            coverage = build_coverage_sets(sites, df, radius)
            scenario_sites = sites.copy()
            scenario_sites['threshold_kmh'] = threshold
            scenario_sites['radius_m'] = radius
            candidate_rows.append(scenario_sites)
            exact, value = exact_max_coverage(coverage, 3)
            # At >2r separation the proxy constrained optimum is the top weights.
            proxy = np.argsort(-sites.weight_c_i.to_numpy(), kind='stable')[:3]
            proxy_cov, _ = true_coverage(proxy, coverage)
            rows.append(dict(threshold_kmh=threshold, radius_m=radius, status='ok',
                budget_used=min(3, len(sites)),
                transit_fixes=len(transit), coarse_clusters=clusters, candidate_count=len(sites),
                exact_covered_fixes=value, proxy_covered_fixes=proxy_cov,
                proxy_ratio=proxy_cov / value if value else None,
                exact_sites=json.dumps(list(exact)),
                proxy_sites=json.dumps(proxy.tolist()),
                candidate_union_fixes=int(coverage.any(axis=0).sum())))
    pd.DataFrame(rows).to_csv('data/conservation_sensitivity.csv', index=False)
    if candidate_rows:
        pd.concat(candidate_rows, ignore_index=True).to_csv('data/sensitivity_candidates.csv', index=False)
    gap_rows = []
    for gap_limit in (1.0, 3.0, 6.0, 24.0):
        known = df.step_gap_hours.gt(0) & df.step_gap_hours.le(gap_limit) & df.speed_kmh.between(0, 7)
        gap_rows.append(dict(max_gap_hours=gap_limit, unknown_fixes=int((~known).sum()),
            transit_fixes=int((known & df.speed_kmh.gt(0.5)).sum())))
    pd.DataFrame(gap_rows).to_csv('data/gap_sensitivity.csv', index=False)
    # Gazetteer point is approximate, not a shoreline or verified deployment site.
    sites = load_sites()
    distances = haversine_m(sites.lat, sites.lon, 15.663, -2.5878)
    landmark = {
        'name': 'Oualet Benzena / approximate Banzena area',
        'lat': 15.663, 'lon': -2.5878,
        'source': 'https://www.geonames.org/advanced-search.html?country=ML&featureClass=H&q=&startRow=250',
        'historical_site7_lat': 15.592856921538463, 'historical_site7_lon': -2.594564207692308,
        'historical_site7_distance_km': float(haversine_m(15.592856921538463, -2.594564207692308, 15.663, -2.5878) / 1000),
        'nearest_current_site_id': int(sites.iloc[int(np.argmin(distances))].site_id),
        'nearest_current_distance_km': float(distances.min() / 1000),
        'boost_enabled': False,
        'candidate_input_sha256': hashlib.sha256(Path('data/candidate_sites.csv').read_bytes()).hexdigest(),
        'reason': 'Approximate gazetteer proximity does not establish a sensor/shoreline match or calibrated ecological weight.',
    }
    Path('data/landmark_validation.json').write_text(json.dumps(landmark, indent=2) + '\n', encoding='utf-8')
    coverage = build_coverage_sets(sites, df)
    _, optimum = exact_max_coverage(coverage, 3)
    boost_rows = []
    nearest = int(np.argmin(distances))
    for floor in (0.0, 0.25, 0.5, 1.0, 2.0):
        weights = sites.weight_c_i.to_numpy().copy()
        weights[nearest] = max(weights[nearest], floor)
        chosen = np.argsort(-weights, kind='stable')[:3]
        count, _ = true_coverage(chosen, coverage)
        boost_rows.append(dict(hypothetical_floor=floor, target_site_id=int(sites.iloc[nearest].site_id),
            sites=json.dumps(sites.iloc[chosen].site_id.tolist()), covered_fixes=count,
            coverage_ratio=count / optimum))
    pd.DataFrame(boost_rows).to_csv('data/landmark_boost_sensitivity.csv', index=False)
    print(json.dumps(quality, indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
    print(json.dumps(landmark, indent=2))


if __name__ == '__main__':
    main()
