"""Check recorded benchmark evidence without rerunning optimization."""

import hashlib
import json
import statistics
from pathlib import Path

import numpy as np
import pandas as pd
from build_qubo import brute_force_proxy, build_coverage_sets, exact_max_coverage
from extract_pinch_points import INDIVIDUAL_FILTER, load_data
from qaoa_samples import summarize_samples


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    metadata = json.loads(Path("data/benchmarks/config.json").read_text())
    for name, digest in metadata["input_sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Stale benchmark input: {name}")
    c, Q = np.load("data/qubo_c.npy"), np.load("data/qubo_Q.npy")
    saved = np.load("data/coverage_sets.npz")
    coverage, ids = saved["coverage"], saved["site_ids"].tolist()
    sites = pd.read_csv("data/candidate_sites.csv").sort_values("site_id")
    fixes = load_data("data/elephant_gps_raw.csv")
    fixes = fixes[fixes["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(drop=True)
    params = dict(
        line.split("=", 1) for line in Path("data/qubo_params.txt").read_text().splitlines()
    )
    k, A, radius = int(params["k"]), float(params["A"]), float(params["r"])
    require(
        np.array_equal(coverage, build_coverage_sets(sites, fixes, radius)), "Stale coverage matrix"
    )
    require(ids == sites.site_id.tolist(), "Incorrect coverage site mapping")
    require(
        exact_max_coverage(coverage, k)[1] == metadata["gps_coverage_optimum"],
        "Incorrect reference coverage",
    )
    require(
        np.isclose(brute_force_proxy(c, Q, k, A)[1], metadata["proxy_optimum"]),
        "Incorrect proxy optimum",
    )
    classical = json.loads(Path("data/benchmarks/classical_runs.json").read_text())
    metrics = pd.read_csv("data/benchmark_metrics.csv")
    require(
        len(metrics) == 6 and not metrics[["method", "p"]].duplicated().any(),
        "Missing or duplicate summary rows",
    )
    for method in ("exact_gps_coverage", "greedy_gps_coverage", "exact_proxy"):
        records = [r for r in classical if r["method"] == method]
        require(len(records) == metadata["classical_repeats"], "Missing classical repeats")
        require(
            sorted(r["repeat"] for r in records) == list(range(metadata["classical_repeats"])),
            "Duplicate classical repeats",
        )
        for record in records:
            chosen = [ids.index(i) for i in record["sites"]]
            require(
                int(coverage[chosen].any(axis=0).sum()) == record["covered_fixes"],
                "Incorrect classical coverage",
            )
            x = np.zeros(len(c))
            x[chosen] = 1
            score = float(c @ x - x @ Q @ x / 2 - A * (x.sum() - k) ** 2)
            require(
                np.isclose(score, record["penalized_proxy_score"]),
                "Incorrect classical proxy score",
            )
    hybrid = []
    for p in metadata["depths"]:
        for seed in metadata["seeds"]:
            run = json.loads(Path(f"data/benchmarks/qaoa_p{p}_seed{seed}.json").read_text())
            for name, digest in run["input_sha256"].items():
                require(
                    hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest,
                    "Stale trial input",
                )
            replay = summarize_samples(
                run["counts"], c, Q, k, A, ids, metadata["proxy_optimum"], metadata["shots"]
            )
            require(
                all(run[key] == replay[key] for key in replay),
                "Incorrect sample selection or rates",
            )
            require(
                run["p"] == p and run["seed"] == seed,
                "Invalid benchmark evidence: run['p'] == p and run['seed'] == seed",
            )
            require(
                sum(run["counts"].values()) == metadata["shots"],
                "Invalid benchmark evidence: sum(run['counts'].values()) == metadata['shots']",
            )
            require(
                run["hybrid_wall_time_s"] >= run["total_time_s"] >= run["opt_time_s"] > 0,
                "Invalid benchmark evidence: run['hybrid_wall_time_s'] >= run['total_time_s'] >= run['opt_time_s'] > 0",
            )
            for restart in run["convergence"]["restarts"]:
                require(
                    restart["evaluations"] == len(restart["energy_history"]),
                    "Invalid benchmark evidence: restart['evaluations'] == len(restart['energy_history'])",
                )
                require(
                    restart["final_energy"] in restart["energy_history"],
                    "Invalid benchmark evidence: restart['final_energy'] in restart['energy_history']",
                )
                require(
                    len(restart["initial_parameters"]) == len(restart["final_parameters"]) == 2 * p,
                    "Invalid benchmark evidence: len(restart['initial_parameters']) == len(restart['final_parameters']) == 2 * p",
                )
            require(
                run["convergence"]["all_restarts_converged"]
                == all(r["success"] for r in run["convergence"]["restarts"]),
                "Invalid benchmark evidence: run['convergence']['all_restarts_converged'] == all(r['success'] for r in run['convergence']['restarts'])",
            )
            optimal = feasible = 0
            for bits, count in run["counts"].items():
                x = np.array([int(bit) for bit in bits[::-1]])
                score = float(
                    c @ x - x @ Q @ x / 2 - run["penalty_A"] * (sum(x) - run["budget"]) ** 2
                )
                optimal += count if abs(score - run["exact_proxy_value"]) <= 1e-9 else 0
                feasible += count if sum(x) <= run["budget"] else 0
            require(
                optimal == run["proxy_optimal_shots"] and feasible == run["feasible_shots"],
                "Invalid benchmark evidence: optimal == run['proxy_optimal_shots'] and feasible == run['feasible_shots']",
            )
            for key in ("raw_metrics", "repaired_metrics"):
                report = run[key]
                if report is not None:
                    indices = [ids.index(site) for site in report["sites"]]
                    count = int(coverage[indices].any(axis=0).sum())
                    x = np.zeros(len(c))
                    x[indices] = 1
                    score = float(c @ x - x @ Q @ x / 2 - A * (x.sum() - k) ** 2)
                    require(
                        np.isclose(score, report["penalized_proxy_score"]),
                        "Incorrect hybrid proxy score",
                    )
                    require(
                        count == report["covered_fixes"],
                        "Invalid benchmark evidence: count == report['covered_fixes']",
                    )
                    require(
                        np.isclose(
                            count / metadata["gps_coverage_optimum"],
                            report["coverage_ratio_to_feasible_optimum"],
                        ),
                        "Invalid benchmark evidence: np.isclose(count / metadata['gps_coverage_optimum'], report['coverage_ratio_to_feasible_optimum'])",
                    )
            hybrid.append(run)
    for row in metrics.itertuples():
        values = (
            [r["hybrid_wall_time_s"] for r in hybrid if r["p"] == row.p]
            if row.method == "QAOA_selection_repair"
            else [r["wall_time_s"] for r in classical if r["method"] == row.method]
        )
        require(len(values) == row.runs, "Invalid benchmark evidence: len(values) == row.runs")
        require(
            np.isclose(statistics.mean(values), row.mean_wall_time_s, rtol=1e-10),
            "Invalid benchmark evidence: np.isclose(statistics.mean(values), row.mean_wall_time_s, rtol=1e-10)",
        )
        require(
            np.isclose(statistics.stdev(values), row.std_wall_time_s, rtol=1e-10),
            "Invalid benchmark evidence: np.isclose(statistics.stdev(values), row.std_wall_time_s, rtol=1e-10)",
        )
    for row in metrics.itertuples():
        if row.method == "QAOA_selection_repair":
            runs = [r for r in hybrid if r["p"] == row.p]
            valid = [r for r in runs if r["repaired_metrics"] is not None]
            require(
                len(valid) == row.successful_selection_runs, "Incorrect successful selection count"
            )
            sources = {
                "proxy_optimal_rate": [r["proxy_optimal_rate"] for r in runs],
                "feasible_rate": [r["feasible_rate"] for r in runs],
                "repaired_proxy_score": [
                    r["repaired_metrics"]["penalized_proxy_score"] for r in valid
                ],
            }
            quality = [r["repaired_metrics"] for r in valid]
            require(
                sum(r["convergence"]["all_restarts_converged"] for r in runs)
                == row.all_restarts_converged_runs,
                "Incorrect convergence count",
            )
        else:
            quality = [r for r in classical if r["method"] == row.method]
            sources = {}
        sources.update(
            covered_fixes=[r["covered_fixes"] for r in quality],
            coverage_ratio=[r["coverage_ratio_to_feasible_optimum"] for r in quality],
        )
        for metric, values in sources.items():
            if values:
                require(
                    np.isclose(statistics.mean(values), getattr(row, "mean_" + metric)),
                    "Incorrect quality mean: " + metric,
                )
                expected_std = statistics.stdev(values) if len(values) > 1 else 0.0
                require(
                    np.isclose(expected_std, getattr(row, "std_" + metric)),
                    "Incorrect quality standard deviation: " + metric,
                )
    print(
        "PASS: all nine benchmark trials, convergence histories, sampling/coverage metrics, input hashes, and aggregate timing statistics"
    )


if __name__ == "__main__":
    main()
