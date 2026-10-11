"""Render observed movement and generated classical/QAOA placements."""
import hashlib
import html
import json
from pathlib import Path

import folium
import numpy as np
import pandas as pd

from build_qubo import load_sites
from extract_pinch_points import load_data, INDIVIDUAL_FILTER


def checked_json(path, required_inputs=()):
    report = json.loads(Path(path).read_text(encoding='utf-8'))
    recorded = {name.replace('\\', '/') for name in report.get('input_sha256', {})}
    if not set(required_inputs) <= recorded:
        raise ValueError(f'{path}: missing required input provenance.')
    for name, digest in report.get('input_sha256', {}).items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'{path}: stale input {name}; regenerate results first.')
    return report


def load_results():
    sites = load_sites()
    baseline = checked_json('data/coverage_baselines.json',
                            ('data/candidate_sites.csv', 'data/elephant_gps_raw.csv'))
    if baseline['individual'] != INDIVIDUAL_FILTER or baseline['candidate_count'] != len(sites):
        raise ValueError('Map baseline does not match the selected individual/candidates.')
    with np.load('data/coverage_sets.npz') as saved:
        coverage = saved['coverage']
        if (not np.array_equal(saved['site_ids'], sites.site_id)
                or coverage.shape != (len(sites), baseline['demand_fix_count'])):
            raise ValueError('Map coverage matrix does not match baseline.')
    placements = [dict(label='Classical GPS optimum', symbol='C', color='#005a9c',
                       **baseline['exact'])]
    for p in (1, 2, 3):
        report = checked_json(f'data/qaoa_repair_p{p}.json', (
            'data/candidate_sites.csv', 'data/elephant_gps_raw.csv',
            'data/coverage_sets.npz', 'data/coverage_baselines.json',
            f'data/qaoa_result_p{p}.json'))
        if (report['p'] != p or report['budget'] != baseline['budget']
                or report['radius_m'] != baseline['radius_m']):
            raise ValueError('Map result configurations disagree.')
        pair = report['selected_raw']
        for key, symbol, color in [('raw', 'Q', '#9c3200'), ('repaired', 'R', '#663399')]:
            placements.append(dict(label=f'QAOA p={p} {key}', symbol=symbol,
                color=color, p=p, backend=report['backend'],
                sites=pair[key]['sites'] if pair else [],
                available=pair is not None,
                covered_fixes=pair[key]['covered_fixes'] if pair else None))
    known = set(sites.site_id)
    for placement in placements:
        ids = placement['sites']
        if len(ids) != len(set(ids)) or not set(ids) <= known:
            raise ValueError('Map placement contains unknown or duplicate site IDs.')
        if len(ids) > baseline['budget']:
            raise ValueError('Selected map placement exceeds budget.')
        if placement.get('available', True):
            indices = [sites.site_id.tolist().index(i) for i in ids]
            covered = int(coverage[indices].any(axis=0).sum())
            if placement['covered_fixes'] != covered:
                raise ValueError('Map coverage count does not match selected sites.')
    landmark = checked_json('data/landmark_validation.json')
    if landmark['candidate_input_sha256'] != hashlib.sha256(Path('data/candidate_sites.csv').read_bytes()).hexdigest():
        raise ValueError('Landmark validation is stale.')
    return sites, baseline, placements, landmark


def main():
    sites, baseline, placements, landmark = load_results()
    trail = load_data('data/elephant_gps_raw.csv')
    trail = trail[trail['individual-local-identifier'] == INDIVIDUAL_FILTER].copy()
    trail['timestamp'] = pd.to_datetime(trail['timestamp'])
    trail = trail.sort_values('timestamp')
    dates = f"{trail.timestamp.min():%Y-%m-%d} to {trail.timestamp.max():%Y-%m-%d}"
    m = folium.Map(location=[trail['location-lat'].mean(), trail['location-long'].mean()],
                   zoom_start=8, tiles='OpenStreetMap', control_scale=True)
    movement = folium.FeatureGroup(name='Observed GPS trail (downsampled)', show=True).add_to(m)
    groups = trail.timestamp.diff().dt.total_seconds().gt(3 * 3600).cumsum()
    for _, segment in trail.groupby(groups):
        sampled = segment.iloc[::4]
        if len(segment) > 1:
            sampled = pd.concat([sampled, segment.iloc[[-1]]]).drop_duplicates()
            folium.PolyLine(sampled[['location-lat', 'location-long']].values.tolist(),
                color='#48745c', weight=1.5, opacity=.55,
                tooltip=f'{INDIVIDUAL_FILTER}: {dates}; approximate path between observations').add_to(movement)
    candidates = folium.FeatureGroup(name='Candidate transit sites', show=True).add_to(m)
    for row in sites.itertuples():
        label = f'Site {row.site_id}: {row.n_fixes} local transit observations; weight {row.weight_c_i:.3f}'
        folium.CircleMarker([row.lat, row.lon], radius=5, color='#333333', fill=True,
            fill_opacity=.6, tooltip=label, popup=label).add_to(candidates)
    for placement in placements:
        layer = folium.FeatureGroup(name=f"{placement['symbol']} — {placement['label']}",
            show=placement.get('p', 3) == 3).add_to(m)
        for site_id in placement['sites']:
            row = sites.set_index('site_id').loc[site_id]
            label = f"{placement['label']}, site {site_id}; {baseline['radius_m']:g} m assumed monitoring zone"
            folium.Circle([row.lat, row.lon], radius=baseline['radius_m'],
                color=placement['color'], weight=2, fill=True, fill_opacity=.08,
                dash_array={'C': None, 'Q': '6 4', 'R': '2 4'}[placement['symbol']],
                tooltip=label).add_to(layer)
            # Nested outlines remain at the actual coordinates; toggles reveal coincident placements.
            size = {'C': 40, 'Q': 28, 'R': 16}[placement['symbol']]
            icon = f'<div title="{html.escape(label)}" style="width:{size}px;height:{size}px;border:3px solid {placement["color"]};border-radius:50%;box-sizing:border-box;background:transparent"></div>'
            folium.Marker([row.lat, row.lon], title=label, tooltip=label, popup=label,
                icon=folium.DivIcon(html=icon, icon_size=(size,size), icon_anchor=(size/2,size/2))).add_to(layer)
    landmarks = folium.FeatureGroup(name='Approximate Banzena reference (not a candidate)', show=False).add_to(m)
    label = (f"{landmark['name']}; approximate gazetteer location. Nearest candidate "
             f"{landmark['nearest_current_distance_km']:.1f} km away; no landmark boost applied.")
    folium.Marker([landmark['lat'], landmark['lon']], tooltip=label,
        popup=html.escape(label) + ' <a href="' + html.escape(landmark['source'], quote=True) + '">Gazetteer source</a>').add_to(landmarks)
    folium.LayerControl(collapsed=False).add_to(m)
    rows = ''.join(f'<tr><th scope="row" style="color:{x["color"]}">{x["symbol"]}: {html.escape(x["label"])}</th><td>{", ".join(map(str,x["sites"])) or ("None selected" if x.get("available", True) else "No feasible sample")}</td><td>{x["covered_fixes"] if x["covered_fixes"] is not None else "Unavailable"}</td></tr>' for x in placements)
    backends = html.escape(', '.join(sorted({x['backend'] for x in placements if 'backend' in x})))
    panel = f'''<style>
    .results-panel {{position:fixed;left:12px;bottom:24px;z-index:1000;background:white;color:#222;
      padding:14px;max-width:470px;max-height:45vh;overflow:auto;font:14px/1.45 Arial,sans-serif;
      box-shadow:0 1px 8px #777;border-radius:6px}}
    .results-panel h1 {{font-size:19px;margin:0 0 6px}} .results-panel table {{border-collapse:collapse;width:100%}}
    .results-panel th,.results-panel td {{text-align:left;padding:4px;border-bottom:1px solid #ddd}}
    @media(max-width:600px) {{.results-panel {{left:6px;right:6px;bottom:20px;max-height:32vh;font-size:12px}}}}
    :focus-visible {{outline:3px solid #005a9c;outline-offset:2px}}
    </style><section class="results-panel" tabindex="0" aria-label="Placement results and map legend">
    <h1>Signal in the Bush</h1><p>Salif Keita · Gourma, Mali · {dates}<br>{len(trail):,} visible GPS observations; budget {baseline['budget']} sites.</p>
    <details open><summary>Compare placements and covered observations</summary>
    <table><caption>Saved results · {backends}</caption><thead><tr><th scope="col">Method</th><th scope="col">Site IDs</th><th scope="col">Covered fixes</th></tr></thead><tbody>{rows}</tbody></table></details>
    <p>C = blue solid / outer ring; Q = brown dashed / middle ring; R = purple dotted / inner ring.
    Toggle layers at top right to inspect overlapping sites. Depth 3 is shown initially.
    Raw means the selected feasible measured sample, before repair. Compare each raw/repaired row to see whether repair changed the selection.</p>
    <p>{baseline['radius_m']:g} m circles are assumed monitoring zones, not camera detection specifications.
    Coverage counts GPS observations, not animals. Green lines approximate movement; gaps over 3 hours are disconnected.
    Banzena is an optional approximate reference, not a sensor site. No quantum advantage is demonstrated.</p></section>'''
    m.get_root().header.add_child(folium.Element('<title>Signal in the Bush — sensor placement results</title>'))
    m.get_root().html.add_child(folium.Element(panel))
    Path('demo').mkdir(exist_ok=True)
    m.save('demo/map.html')
    output = Path('demo/map.html')
    output.write_text('\n'.join(line.rstrip() for line in output.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    manifest = dict(individual=INDIVIDUAL_FILTER, dates=dates, observations=len(trail),
        radius_m=baseline['radius_m'], placements=placements,
        candidates=sites[['site_id','lat','lon']].to_dict(orient='records'))
    Path('demo/map_data.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Saved demo/map.html and demo/map_data.json from validated generated results.')


if __name__ == '__main__':
    main()
