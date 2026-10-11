"""Repair measured placements using actual GPS coverage; preserve raw evidence."""
import ast
import hashlib
import json
import numbers
from pathlib import Path

import numpy as np
import pandas as pd

from build_qubo import (validate_coverage_sets, proxy_objective, load_sites,
    build_coverage_sets, exact_max_coverage, brute_force_proxy, distance_matrix,
    build_overlap_matrix, R_METERS, K_BUDGET)
from extract_pinch_points import load_data, INDIVIDUAL_FILTER
from qaoa_samples import decode_bitstring, summarize_samples


def validate_selection(selected, n, k, site_ids):
    selected = list(selected)
    if (isinstance(k, (bool, np.bool_)) or not isinstance(k, numbers.Integral)
            or not 0 <= k <= n or len(site_ids) != n
            or len(set(site_ids)) != n
            or any(isinstance(i, (bool, np.bool_)) or not isinstance(i, numbers.Integral) or i < 0 for i in site_ids)):
        raise ValueError('Invalid repair budget or site mapping.')
    if len(set(selected)) != len(selected) or any(isinstance(i, (bool, np.bool_))
            or not isinstance(i, numbers.Integral) or not 0 <= i < n for i in selected):
        raise ValueError('Repair input must contain unique valid site indices.')
    return selected


def repair_budget(selected, coverage, k, site_ids):
    """Trim least coverage loss, then fill greatest positive coverage gain.

    Ties use ascending actual site ID. A feasible full-budget input is unchanged.
    """
    coverage = validate_coverage_sets(coverage)
    chosen = set(validate_selection(selected, len(coverage), k, site_ids))

    def count(indices):
        return int(coverage[sorted(indices)].any(axis=0).sum())

    actions = []
    while len(chosen) > k:
        before = count(chosen)
        i = min(chosen, key=lambda j: (before - count(chosen - {j}), site_ids[j]))
        chosen.remove(i)
        actions.append(dict(action='remove', site_id=int(site_ids[i]), coverage_change=count(chosen) - before))
    while len(chosen) < k:
        remaining = set(range(len(coverage))) - chosen
        before = count(chosen)
        i = min(remaining, key=lambda j: (-(count(chosen | {j}) - before), site_ids[j]))
        gain = count(chosen | {i}) - before
        if gain <= 0:
            break
        chosen.add(i)
        actions.append(dict(action='add', site_id=int(site_ids[i]), coverage_change=gain))
    return sorted(chosen), actions


def evaluate_placement(indices, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum):
    coverage = validate_coverage_sets(coverage)
    indices = validate_selection(indices, len(coverage), k, ids)
    c, Q = np.asarray(c, dtype=float), np.asarray(Q, dtype=float)
    if (c.shape != (len(coverage),) or Q.shape != (len(c), len(c))
            or not np.isfinite(c).all() or not np.isfinite(Q).all()
            or not np.isfinite([A, proxy_optimum, coverage_optimum]).all() or A < 0 or coverage_optimum < 0):
        raise ValueError('Invalid evaluation objective or reference optimum.')
    x = np.zeros(len(c), dtype=int)
    x[list(indices)] = 1
    count = int(coverage[list(indices)].any(axis=0).sum())
    score = float(proxy_objective(x, c, Q, k, A))
    feasible = len(indices) <= k
    return dict(sites=[int(ids[i]) for i in indices], selected_count=len(indices), feasible=feasible,
        penalized_proxy_score=score, proxy_score_ratio=score / proxy_optimum if proxy_optimum > 0 else None,
        covered_fixes=count, coverage_ratio_to_feasible_optimum=(count / coverage_optimum if coverage_optimum else None) if feasible else None,
        coverage_comparison_valid=feasible)


def main():
    sites = load_sites()
    ids = sites.site_id.tolist()
    c, Q = np.load('data/qubo_c.npy'), np.load('data/qubo_Q.npy')
    params = dict(line.split('=', 1) for line in Path('data/qubo_params.txt').read_text().splitlines())
    k, A, radius = int(params['k']), float(params['A']), float(params['r'])
    if (ast.literal_eval(params['site_ids']) != ids or k != K_BUDGET or radius != R_METERS
            or c.shape != (len(sites),) or Q.shape != (len(sites), len(sites))
            or not np.allclose(c, sites.weight_c_i)
            or not np.allclose(Q, build_overlap_matrix(distance_matrix(sites)))):
        raise ValueError('Saved QUBO site IDs do not match current candidates.')
    baselines = json.loads(Path('data/coverage_baselines.json').read_text())
    for name, digest in baselines['input_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('Coverage baseline inputs are stale; regenerate baselines.')
    if radius != baselines['radius_m'] or k != baselines['budget']:
        raise ValueError('Baseline budget/radius does not match QUBO.')
    fixes = load_data('data/elephant_gps_raw.csv')
    fixes = fixes[fixes['individual-local-identifier'] == INDIVIDUAL_FILTER].reset_index(drop=True)
    coverage = build_coverage_sets(sites, fixes, radius)
    saved = np.load('data/coverage_sets.npz')
    if (not np.array_equal(saved['site_ids'], ids) or not np.array_equal(saved['coverage'], coverage)
            or not np.array_equal(saved['demand_indices'], np.arange(len(fixes)))):
        raise ValueError('Saved coverage matrix is stale or corrupt.')
    _, coverage_optimum = exact_max_coverage(coverage, k)
    _, proxy_optimum = brute_force_proxy(c, Q, k, A)
    for p in (1, 2, 3):
        source = Path(f'data/qaoa_result_p{p}.json')
        result = json.loads(source.read_text())
        if result['p'] != p or result['budget'] != k or result['qubits'] != len(ids) or result['penalty_A'] != A:
            raise ValueError(f'p={p} sample configuration does not match the current instance.')
        for name, digest in result['input_sha256'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'p={p} samples have stale inputs.')
        replay = summarize_samples(result['counts'], c, Q, k, A, ids, proxy_optimum, result['shots'])
        if any(replay[key] != result[key] for key in replay):
            raise ValueError(f'p={p} sample summary does not replay.')
        inputs = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in
            ('data/candidate_sites.csv', 'data/elephant_gps_raw.csv', 'data/coverage_sets.npz',
             'data/coverage_baselines.json', 'data/qubo_c.npy', 'data/qubo_Q.npy', 'data/qubo_params.txt', str(source))}
        output = dict(p=p, backend=result['backend'], budget=k, radius_m=radius,
            repair_rule='trim least GPS-coverage loss; fill greatest positive GPS-coverage gain; ties by site ID',
            proxy_optimum=proxy_optimum, gps_coverage_optimum=coverage_optimum, input_sha256=inputs)

        def pair(bits):
            indices = np.flatnonzero(decode_bitstring(bits, len(ids))).tolist()
            repaired, actions = repair_budget(indices, coverage, k, ids)
            return dict(raw_bitstring=bits, actions=actions,
                raw=evaluate_placement(indices, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum),
                repaired=evaluate_placement(repaired, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum))

        for key in ('mode', 'selected_raw'):
            output[key] = pair(result[key]['bitstring']) if result[key] else None
        rows = []
        changed_shots = repaired_feasible_shots = 0
        raw_coverage_total = repaired_coverage_total = 0
        for bits, count in sorted(result['counts'].items()):
            report = pair(bits)
            raw, repaired = report['raw'], report['repaired']
            if not repaired['feasible']:
                raise ValueError('Repair produced an infeasible placement.')
            repaired_feasible_shots += count
            changed_shots += count if report['actions'] else 0
            raw_coverage_total += count * raw['covered_fixes']
            repaired_coverage_total += count * repaired['covered_fixes']
            rows.append(dict(bitstring=bits, shots=count, raw_sites=json.dumps(raw['sites']),
                repaired_sites=json.dumps(repaired['sites']), actions=json.dumps(report['actions']),
                raw_feasible=raw['feasible'], repaired_feasible=repaired['feasible'],
                raw_covered_fixes=raw['covered_fixes'], repaired_covered_fixes=repaired['covered_fixes'],
                raw_proxy_score=raw['penalized_proxy_score'], repaired_proxy_score=repaired['penalized_proxy_score'],
                raw_proxy_ratio=raw['proxy_score_ratio'], repaired_proxy_ratio=repaired['proxy_score_ratio'],
                raw_coverage_ratio=raw['coverage_ratio_to_feasible_optimum'],
                repaired_coverage_ratio=repaired['coverage_ratio_to_feasible_optimum']))
        output['distribution'] = dict(shots=result['shots'], changed_shots=changed_shots,
            changed_rate=changed_shots / result['shots'], repaired_feasible_rate=repaired_feasible_shots / result['shots'],
            raw_mean_covered_fixes=raw_coverage_total / result['shots'],
            repaired_mean_covered_fixes=repaired_coverage_total / result['shots'],
            note='Raw mean includes infeasible placements; it is not a budget-valid benchmark.')
        Path(f'data/qaoa_repair_p{p}.json').write_text(json.dumps(output, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        pd.DataFrame(rows).to_csv(f'data/qaoa_repair_samples_p{p}.csv', index=False)
        chosen = output['selected_raw']
        print(f"p={p}: selected raw/repaired={chosen['raw']['sites'] if chosen else None}/{chosen['repaired']['sites'] if chosen else None}; changed shots={changed_shots}/{result['shots']}")


if __name__ == '__main__':
    main()
