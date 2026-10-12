"""Browser entry functions: verified saved evidence plus one fresh backend job."""

import ast
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
from placement_core import (
    build_hamiltonian,
    decode_bitstring,
    evaluate_placement,
    exact_max_coverage,
    greedy_max_coverage,
    qubo_to_ising,
    repair_budget,
    summarize_samples,
)
from qiskit import transpile
from qiskit.circuit.library import QAOAAnsatz

# Literal paths let Qollab preload every input into its in-memory filesystem.
INPUT_FILES = (
    "data/candidate_sites.csv",
    "data/coverage_sets.npz",
    "data/coverage_baselines.json",
    "data/qubo_c.npy",
    "data/qubo_Q.npy",
    "data/qubo_params.txt",
    "data/qaoa_result_p1.json",
    "data/qaoa_result_p2.json",
    "data/qaoa_result_p3.json",
    "demo/map.html",
    "demo/map_data.json",
)
RESULT_FILES = {
    1: "data/qaoa_result_p1.json",
    2: "data/qaoa_result_p2.json",
    3: "data/qaoa_result_p3.json",
}


def load_inputs():
    manifest = json.loads(Path("bundle_manifest.json").read_text())
    for name in INPUT_FILES:
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != manifest["input_sha256"][name]:
            raise ValueError(f"Package input changed: {name}")
    baseline = json.loads(Path("data/coverage_baselines.json").read_text())
    with np.load("data/coverage_sets.npz") as saved:
        coverage, ids = saved["coverage"], saved["site_ids"].tolist()
    with open("data/candidate_sites.csv", newline="") as stream:
        sites = list(csv.DictReader(stream))
    if ids != [int(row["site_id"]) for row in sites] or coverage.shape != (
        len(ids),
        baseline["demand_fix_count"],
    ):
        raise ValueError("Coverage matrix and candidate mapping disagree.")
    params = dict(
        line.split("=", 1) for line in Path("data/qubo_params.txt").read_text().splitlines()
    )
    if ast.literal_eval(params["site_ids"]) != ids:
        raise ValueError("QUBO and coverage site mapping disagree.")
    return baseline, coverage, ids, sites, params


def prepare():
    baseline, coverage, ids, _, _ = load_inputs()
    exact, exact_count = exact_max_coverage(coverage, baseline["budget"])
    greedy, greedy_count = greedy_max_coverage(coverage, baseline["budget"])
    if [ids[i] for i in exact] != baseline["exact"]["sites"] or exact_count != baseline["exact"][
        "covered_fixes"
    ]:
        raise ValueError("Recomputed classical baseline disagrees with saved evidence.")
    return json.dumps(
        dict(
            map_html=Path("demo/map.html").read_text(),
            exact_sites=[ids[i] for i in exact],
            exact_covered=exact_count,
            greedy_sites=[ids[i] for i in greedy],
            greedy_covered=greedy_count,
            manifest=manifest_summary(),
        ),
        allow_nan=False,
    )


def manifest_summary():
    return json.loads(Path("bundle_manifest.json").read_text())["description"]


def measure(selected_backend, depth=1, shots=4096):
    if (
        isinstance(depth, bool)
        or depth not in (1, 2, 3)
        or isinstance(shots, bool)
        or not isinstance(shots, int)
        or not 128 <= shots <= 8192
    ):
        raise ValueError("Choose depth 1, 2, or 3 and 128–8192 integer shots.")
    baseline, coverage, ids, sites, params = load_inputs()
    reference = json.loads(Path(RESULT_FILES[depth]).read_text())
    c, Q = np.load("data/qubo_c.npy"), np.load("data/qubo_Q.npy")
    penalty, budget = float(params["A"]), int(params["k"])
    h, coupling, constant = qubo_to_ising(c, Q, penalty, budget)
    hamiltonian = build_hamiltonian(h, coupling, constant, len(ids))
    ansatz = QAOAAnsatz(cost_operator=hamiltonian, reps=depth)
    if [str(parameter) for parameter in ansatz.parameters] != reference["convergence"][
        "parameter_order"
    ]:
        raise ValueError("Parameter order differs from the saved optimization.")
    circuit = ansatz.assign_parameters(reference["convergence"]["best_parameters"])
    circuit.measure_all()
    # Respect the backend selected by the judge. Never instantiate Aer here.
    compiled = transpile(circuit, selected_backend, optimization_level=1)
    started = time.perf_counter()
    job = selected_backend.run(compiled, shots=shots)
    counts = job.result().get_counts()
    elapsed = time.perf_counter() - started
    summary = summarize_samples(
        counts, c, Q, budget, penalty, ids, baseline["proxy"]["penalized_objective"], shots
    )
    chosen = summary["selected_raw"]
    raw = repaired = None
    actions = []
    if chosen is not None:
        indices = np.flatnonzero(decode_bitstring(chosen["bitstring"], len(ids))).tolist()
        repaired_indices, actions = repair_budget(indices, coverage, budget, ids)

        def evaluate(indices):
            return evaluate_placement(
                indices,
                coverage,
                c,
                Q,
                budget,
                penalty,
                ids,
                baseline["proxy"]["penalized_objective"],
                baseline["exact"]["covered_fixes"],
            )

        raw, repaired = evaluate(indices), evaluate(repaired_indices)
    backend_name = getattr(selected_backend, "name", type(selected_backend).__name__)
    if callable(backend_name):
        backend_name = backend_name()
    report = dict(
        backend=str(backend_name),
        job_id=str(job.job_id()),
        depth=depth,
        shots=shots,
        execution="Fresh measurement of parameters optimized previously on local Aer; no optimizer rerun",
        parameter_source=RESULT_FILES[depth],
        sampling_seed="backend default; fresh run, not archived seed-42 sampling",
        sampling_wall_time_s=elapsed,
        timing_scope="backend submission and result retrieval; excludes classical setup/transpilation",
        raw=raw,
        repaired=repaired,
        repair_actions=actions,
        distribution=summary,
        exact_gps=baseline["exact"],
        radius_m=baseline["radius_m"],
    )
    map_html = Path("demo/map.html").read_text()
    map_name = re.search(r"var (map_[a-f0-9]+) = L.map", map_html).group(1)
    commands = [f"var liveLayer = L.featureGroup().addTo({map_name});"]
    if repaired:
        selected = set(repaired["sites"])
        for site in sites:
            if int(site["site_id"]) in selected:
                location = [float(site["lat"]), float(site["lon"])]
                label = f"LIVE p={depth} repaired site {site['site_id']}; backend {backend_name}"
                commands.append(
                    f'L.circle({json.dumps(location)}, {{radius:{baseline["radius_m"]},color:"#00806c",weight:4,fillOpacity:0.15}}).bindPopup({json.dumps(label)}).addTo(liveLayer);'
                )
                commands.append(
                    f"L.marker({json.dumps(location)}, {{title:{json.dumps(label)},icon:L.divIcon({{html:'<span style=\"background:#00806c;color:white;padding:4px;border-radius:4px\">L</span>',className:'live-site'}})}}).bindPopup({json.dumps(label)}).addTo(liveLayer);"
                )
    map_html += "<script>" + "\n".join(commands).replace("</", "<\\/") + "</script>"
    print(
        f"Fresh measurement complete: backend={backend_name}, p={depth}, shots={shots}, job={report['job_id']}"
    )
    return json.dumps(dict(report=report, map_html=map_html), allow_nan=False)
