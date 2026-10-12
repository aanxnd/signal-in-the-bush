"""Repeated same-instance local benchmarks with explicit timing boundaries."""

import ast
import hashlib
import importlib.metadata
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from build_qubo import (
    K_BUDGET,
    R_METERS,
    brute_force_proxy,
    build_coverage_sets,
    build_overlap_matrix,
    distance_matrix,
    exact_max_coverage,
    greedy_max_coverage,
    load_sites,
)
from extract_pinch_points import INDIVIDUAL_FILTER, load_data
from qaoa_samples import decode_bitstring, summarize_samples
from repair_qaoa import evaluate_placement, repair_budget
from run_qaoa import (
    AER_THREADS,
    MAX_ITERATIONS,
    RANDOM_RESTARTS,
    SHOTS,
    build_hamiltonian,
    qubo_to_ising,
    run_qaoa_depth,
    validate_ising,
)

SEEDS = (42, 43, 44)
DEPTHS = (1, 2, 3)
CLASSICAL_REPEATS = 10


def mean_std(values):
    values = list(values)
    return dict(
        n=len(values),
        mean=statistics.mean(values),
        std=statistics.stdev(values) if len(values) > 1 else 0.0,
    )


def write_metrics(classical, hybrid):
    for p in DEPTHS:
        seeds = [r["seed"] for r in hybrid if r["p"] == p]
        if len(seeds) != len(SEEDS) or set(seeds) != set(SEEDS):
            raise ValueError(f"Depth {p} requires one trial for each configured seed.")
    if any(r["p"] not in DEPTHS for r in hybrid):
        raise ValueError("Unexpected depth in benchmark trials.")
    rows = []
    for name in ("exact_gps_coverage", "greedy_gps_coverage", "exact_proxy"):
        runs = [r for r in classical if r["method"] == name]
        timing = mean_std(r["wall_time_s"] for r in runs)
        rows.append(
            dict(
                method=name,
                p=None,
                runs=timing["n"],
                mean_wall_time_s=timing["mean"],
                std_wall_time_s=timing["std"],
                mean_covered_fixes=statistics.mean(r["covered_fixes"] for r in runs),
                std_covered_fixes=statistics.stdev(r["covered_fixes"] for r in runs),
                mean_coverage_ratio=statistics.mean(
                    r["coverage_ratio_to_feasible_optimum"] for r in runs
                ),
                std_coverage_ratio=statistics.stdev(
                    r["coverage_ratio_to_feasible_optimum"] for r in runs
                ),
            )
        )
    for p in DEPTHS:
        runs = [r for r in hybrid if r["p"] == p]
        timing = mean_std(r["hybrid_wall_time_s"] for r in runs)
        valid = [r for r in runs if r["repaired_metrics"] is not None]
        rows.append(
            dict(
                method="QAOA_selection_repair",
                p=p,
                runs=timing["n"],
                mean_wall_time_s=timing["mean"],
                std_wall_time_s=timing["std"],
                successful_selection_runs=len(valid),
                mean_covered_fixes=statistics.mean(
                    r["repaired_metrics"]["covered_fixes"] for r in valid
                )
                if valid
                else None,
                std_covered_fixes=statistics.stdev(
                    r["repaired_metrics"]["covered_fixes"] for r in valid
                )
                if len(valid) > 1
                else (0.0 if valid else None),
                mean_coverage_ratio=statistics.mean(
                    r["repaired_metrics"]["coverage_ratio_to_feasible_optimum"] for r in valid
                )
                if valid
                else None,
                std_coverage_ratio=statistics.stdev(
                    r["repaired_metrics"]["coverage_ratio_to_feasible_optimum"] for r in valid
                )
                if len(valid) > 1
                else (0.0 if valid else None),
                mean_proxy_optimal_rate=statistics.mean(r["proxy_optimal_rate"] for r in runs),
                std_proxy_optimal_rate=statistics.stdev(r["proxy_optimal_rate"] for r in runs),
                mean_feasible_rate=statistics.mean(r["feasible_rate"] for r in runs),
                std_feasible_rate=statistics.stdev(r["feasible_rate"] for r in runs),
                mean_repaired_proxy_score=statistics.mean(
                    r["repaired_metrics"]["penalized_proxy_score"] for r in valid
                )
                if valid
                else None,
                std_repaired_proxy_score=statistics.stdev(
                    r["repaired_metrics"]["penalized_proxy_score"] for r in valid
                )
                if len(valid) > 1
                else (0.0 if valid else None),
                all_restarts_converged_runs=sum(
                    r["convergence"]["all_restarts_converged"] for r in runs
                ),
            )
        )
    pd.DataFrame(rows).to_csv("data/benchmark_metrics.csv", index=False)
    report = [
        "# Repeated local benchmark results",
        "",
        "All timings are seconds, mean +/- sample standard deviation. See [benchmark methodology](BENCHMARKING.md) for scope and limitations.",
        "",
        "| Method | Depth | Runs | Time (s) | Covered fixes | Coverage / exact |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        covered = row["mean_covered_fixes"]
        ratio = row["mean_coverage_ratio"]
        report.append(
            f"| {row['method']} | {row['p'] if row['p'] is not None else '-'} | {row['runs']} | {row['mean_wall_time_s']:.6f} +/- {row['std_wall_time_s']:.6f} | {covered:.2f} | {ratio:.2%} |"
            if covered is not None
            else f"| {row['method']} | {row['p']} | {row['runs']} | {row['mean_wall_time_s']:.6f} +/- {row['std_wall_time_s']:.6f} | no feasible sample | n/a |"
        )
    report += [
        "",
        "GPS coverage and proxy scores are different objectives. Quantum figures include classical sample selection and selected-placement repair. Three seeds are descriptive; no quantum speed advantage is claimed.",
        "Coverage means condition on successful selection. Successful hybrid selections by depth: "
        + ", ".join(
            f"p={row['p']}: {row['successful_selection_runs']}/{row['runs']}"
            for row in rows
            if row["method"] == "QAOA_selection_repair"
        )
        + ".",
        "",
    ]
    Path("docs/BENCHMARK_RESULTS.md").write_text("\n".join(report), encoding="utf-8")
    return rows


def main():
    started = time.perf_counter()
    sites = load_sites()
    ids = sites.site_id.tolist()
    c, Q = np.load("data/qubo_c.npy"), np.load("data/qubo_Q.npy")
    params = dict(
        line.split("=", 1) for line in Path("data/qubo_params.txt").read_text().splitlines()
    )
    k, A, radius = int(params["k"]), float(params["A"]), float(params["r"])
    if (
        ast.literal_eval(params["site_ids"]) != ids
        or k != K_BUDGET
        or radius != R_METERS
        or not np.isfinite(A)
        or A < 0
        or c.shape != (len(ids),)
        or Q.shape != (len(ids), len(ids))
        or not np.allclose(c, sites.weight_c_i)
        or not np.allclose(Q, build_overlap_matrix(distance_matrix(sites)))
    ):
        raise ValueError("Stale QUBO; regenerate it before benchmarking.")
    fixes = load_data("data/elephant_gps_raw.csv")
    fixes = fixes[fixes["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(drop=True)
    coverage = build_coverage_sets(sites, fixes, radius)
    common_preprocessing_s = time.perf_counter() - started
    _, proxy_optimum = brute_force_proxy(c, Q, k, A)
    _, coverage_optimum = exact_max_coverage(coverage, k)
    h, J, const = qubo_to_ising(c, Q, A, k)
    error = validate_ising(c, Q, A, k, h, J, const, len(c))
    if error >= 1e-8:
        raise ValueError("Ising validation failed.")
    input_hashes = {
        name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
        for name in (
            "data/candidate_sites.csv",
            "data/elephant_gps_raw.csv",
            "data/qubo_c.npy",
            "data/qubo_Q.npy",
            "data/qubo_params.txt",
        )
    }
    Path("data/benchmarks").mkdir(exist_ok=True)
    metadata = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version,
        platform=platform.platform(),
        processor=platform.processor(),
        libraries={
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "pandas", "scikit-learn", "qiskit", "qiskit-aer")
        },
        backend="local Aer CPU simulation",
        aer_threads=AER_THREADS,
        seeds=list(SEEDS),
        depths=list(DEPTHS),
        shots=SHOTS,
        restarts=RANDOM_RESTARTS,
        maxiter=MAX_ITERATIONS,
        classical_repeats=CLASSICAL_REPEATS,
        common_preprocessing_s=common_preprocessing_s,
        ising_max_error=error,
        proxy_optimum=proxy_optimum,
        gps_coverage_optimum=coverage_optimum,
        input_sha256=input_hashes,
        timing_scope="Solver-only wall clock after common input preparation. Hybrid includes Hamiltonian construction, ansatz, optimizer, sampling, full sample selection, selected-placement repair and evaluation. Reference enumeration and correctness checks excluded from all solver timings. Entire-distribution diagnostic repair and artifact I/O excluded.",
        limitations="Three seeds are descriptive, not statistical evidence of advantage. Single machine and one instance. Classical coverage and quantum proxy have different objectives. Common preprocessing, imports, reference construction, and I/O are not end-to-end deployment timings.",
    )
    Path("data/benchmarks/config.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    classical = []
    methods = {
        "exact_gps_coverage": lambda: exact_max_coverage(coverage, k),
        "greedy_gps_coverage": lambda: greedy_max_coverage(coverage, k),
        "exact_proxy": lambda: brute_force_proxy(c, Q, k, A),
    }
    for name, solver in methods.items():
        solver()  # one untimed warm-up for each deterministic solver
        for repeat in range(CLASSICAL_REPEATS):
            t0 = time.perf_counter()
            chosen, _ = solver()
            elapsed = time.perf_counter() - t0
            indices = np.flatnonzero(chosen).tolist() if name == "exact_proxy" else list(chosen)
            metrics = evaluate_placement(
                indices, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum
            )
            classical.append(dict(method=name, repeat=repeat, wall_time_s=elapsed, **metrics))
    Path("data/benchmarks/classical_runs.json").write_text(
        json.dumps(classical, indent=2) + "\n", encoding="utf-8"
    )
    hybrid = []
    for p in DEPTHS:
        for seed in SEEDS:
            print(f"Benchmark p={p}, seed={seed}", flush=True)
            t0 = time.perf_counter()
            hamiltonian = build_hamiltonian(h, J, const, len(c))
            energy, counts, opt_s, quantum_s, convergence = run_qaoa_depth(
                hamiltonian, p, seed=seed
            )
            selection_start = time.perf_counter()
            summary = summarize_samples(counts, c, Q, k, A, ids, proxy_optimum, SHOTS)
            selection_s = time.perf_counter() - selection_start
            selected = summary["selected_raw"]
            repair_start = time.perf_counter()
            raw_metrics = repaired_metrics = None
            actions = []
            if selected is not None:
                indices = np.flatnonzero(decode_bitstring(selected["bitstring"], len(c))).tolist()
                repaired, actions = repair_budget(indices, coverage, k, ids)
                raw_metrics = evaluate_placement(
                    indices, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum
                )
                repaired_metrics = evaluate_placement(
                    repaired, coverage, c, Q, k, A, ids, proxy_optimum, coverage_optimum
                )
            repair_evaluation_s = time.perf_counter() - repair_start
            hybrid_s = time.perf_counter() - t0
            run = dict(
                p=p,
                seed=seed,
                hybrid_wall_time_s=hybrid_s,
                selection_time_s=selection_s,
                repair_evaluation_time_s=repair_evaluation_s,
                raw_metrics=raw_metrics,
                repaired_metrics=repaired_metrics,
                repair_actions=actions,
                **summary,
            )
            run.update(
                qubits=len(c),
                budget=k,
                penalty_A=A,
                sampling_seed=seed,
                optimizer_seed=seed,
                backend="local qiskit Aer SamplerV2",
                random_restarts=RANDOM_RESTARTS,
                opt_time_s=opt_s,
                total_time_s=quantum_s,
                optimizer_expected_energy=energy,
                convergence=convergence,
                input_sha256=input_hashes,
            )
            Path(f"data/benchmarks/qaoa_p{p}_seed{seed}.json").write_text(
                json.dumps(run, indent=2, allow_nan=False) + "\n", encoding="utf-8"
            )
            hybrid.append(run)
            print(
                f"Finished p={p}, seed={seed}: {hybrid_s:.2f}s; optimal shots={summary['proxy_optimal_shots']}; converged={convergence['all_restarts_converged']}",
                flush=True,
            )
    rows = write_metrics(classical, hybrid)
    # Publish seed-42 representatives with full convergence evidence; other seeds stay separate.
    for run in hybrid:
        if run["seed"] != 42:
            continue
        p = run["p"]
        Path(f"data/qaoa_result_p{p}.json").write_text(
            json.dumps(run, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        mode, chosen = run["mode"], run["selected_raw"]
        text = dict(
            p=p,
            shots=SHOTS,
            selection_rule=run["selection_rule"],
            mode_bitstring=mode["bitstring"],
            mode_sites=mode["sites"],
            selected_bitstring=chosen["bitstring"] if chosen else None,
            sites=chosen["sites"] if chosen else None,
            sampled_f=chosen["penalized_proxy_score"] if chosen else None,
            exact_f=proxy_optimum,
            feasible_rate=run["feasible_rate"],
            proxy_optimal_rate=run["proxy_optimal_rate"],
            opt_time_s=run["opt_time_s"],
            total_time_s=run["total_time_s"],
            counts=run["counts"],
        )
        Path(f"data/qaoa_result_p{p}.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in text.items()), encoding="utf-8"
        )
    print(pd.DataFrame(rows).to_string(index=False), flush=True)


if __name__ == "__main__":
    if "--summarize" in sys.argv:
        config = json.loads(Path("data/benchmarks/config.json").read_text())
        for name, digest in config["input_sha256"].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Stale benchmark inputs: {name}")
        classical = json.loads(Path("data/benchmarks/classical_runs.json").read_text())
        hybrid = [
            json.loads(Path(f"data/benchmarks/qaoa_p{p}_seed{seed}.json").read_text())
            for p in DEPTHS
            for seed in SEEDS
        ]
        for run in hybrid:
            for name, digest in run["input_sha256"].items():
                if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Stale trial input: {name}")
        write_metrics(classical, hybrid)
    else:
        main()
