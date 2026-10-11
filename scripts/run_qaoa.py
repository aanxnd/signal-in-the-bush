"""
Track C: QAOA on the proxy QUBO from build_qubo.py.

Converts the QUBO (c, Q, A, k) to an Ising Hamiltonian, runs QAOA via
Qiskit 2.x primitives (EstimatorV2 for the classical optimization loop,
SamplerV2 for final bitstring sampling) on the local Aer simulator first
-- per README Section 13's own advice, validate locally before touching
the shared IonQ/Qollab queue.
"""
import sys
import time
import itertools
import ast
import json
import hashlib
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import QAOAAnsatz
from qiskit_aer.primitives import EstimatorV2 as AerEstimator
from qiskit_aer.primitives import SamplerV2 as AerSampler

sys.path.insert(0, "scripts")
from build_qubo import (proxy_objective, brute_force_proxy, load_sites,
                        distance_matrix, build_overlap_matrix, R_METERS, K_BUDGET)
from qaoa_samples import decode_bitstring, summarize_samples

SHOTS = 4096
REPS_LIST = [1, 2, 3]
RANDOM_RESTARTS = 3
SEED = 42


def qubo_to_ising(c, Q, A, k):
    n = len(c)
    # cost(x) = -f(x) = sum_i a_i x_i + sum_{i<j} b_ij x_i x_j + A*k^2
    a = -(c - A * (1 - 2 * k))
    b = -(-(Q + 2 * A))  # = Q + 2A ; kept explicit for clarity against the derivation in README Section 6
    np.fill_diagonal(b, 0.0)
    const = A * k * k

    h = np.zeros(n)
    J = np.zeros((n, n))
    total_const = 0.5 * a.sum() + 0.25 * np.triu(b, 1).sum() + const
    for i in range(n):
        h[i] = -0.5 * a[i] - 0.25 * (b[i, :].sum())  # sum_{j != i} b_ij, b_ii=0 so full row sum works
    for i in range(n):
        for j in range(i + 1, n):
            J[i, j] = 0.25 * b[i, j]
    return h, J, total_const, a, b


def validate_ising(c, Q, A, k, h, J, const, n):
    """Brute-force check: Ising energy must equal -proxy_objective(x) for every bitstring."""
    max_err = 0.0
    for bits in itertools.product([0, 1], repeat=n):
        x = np.array(bits)
        z = 1 - 2 * x  # x=0 -> z=+1, x=1 -> z=-1
        ising_energy = const + h @ z + sum(J[i, j] * z[i] * z[j] for i in range(n) for j in range(i + 1, n))
        expected = -proxy_objective(bits, c, Q, k, A)
        max_err = max(max_err, abs(ising_energy - expected))
    return max_err


def build_hamiltonian(h, J, const, n):
    terms, coeffs = [], []
    if abs(const) > 0:
        terms.append("I" * n)
        coeffs.append(const)
    for i in range(n):
        if abs(h[i]) > 1e-12:
            label = ["I"] * n
            label[n - 1 - i] = "Z"
            terms.append("".join(label))
            coeffs.append(h[i])
    for i in range(n):
        for j in range(i + 1, n):
            if abs(J[i, j]) > 1e-12:
                label = ["I"] * n
                label[n - 1 - i] = "Z"
                label[n - 1 - j] = "Z"
                terms.append("".join(label))
                coeffs.append(J[i, j])
    return SparsePauliOp(terms, coeffs)


def run_qaoa_depth(hamiltonian, n, reps, shots=SHOTS, seed=SEED):
    ansatz = QAOAAnsatz(cost_operator=hamiltonian, reps=reps).decompose(reps=4)
    estimator = AerEstimator()
    rng = np.random.default_rng(seed)

    def cost_fn(params):
        job = estimator.run([(ansatz, hamiltonian, params)])
        return float(job.result()[0].data.evs)

    best_val, best_params = np.inf, None
    t0 = time.time()
    for r in range(RANDOM_RESTARTS):
        x0 = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)
        res = minimize(cost_fn, x0, method="COBYLA", options={"maxiter": 200})
        if res.fun < best_val:
            best_val, best_params = res.fun, res.x
    opt_time = time.time() - t0

    bound = ansatz.assign_parameters(best_params)
    bound.measure_all()
    sampler = AerSampler(seed=seed)
    job = sampler.run([bound], shots=shots)
    counts = job.result()[0].data.meas.get_counts()
    total_time = time.time() - t0

    return best_val, counts, opt_time, total_time


def main():
    c = np.load("data/qubo_c.npy")
    Q = np.load("data/qubo_Q.npy")
    params = {}
    with open("data/qubo_params.txt") as f:
        for line in f:
            key, val = line.strip().split("=", 1)
            params[key] = val
    k = int(params["k"])
    A = float(params["A"])
    site_ids = ast.literal_eval(params["site_ids"])
    current_sites = load_sites()
    if (site_ids != current_sites["site_id"].tolist()
            or k != K_BUDGET or not np.isclose(float(params["r"]), R_METERS)
            or not np.isfinite(A) or A < 0
            or c.shape != (len(current_sites),)
            or Q.shape != (len(current_sites), len(current_sites))
            or not np.allclose(c, current_sites["weight_c_i"].to_numpy())
            or not np.allclose(Q, build_overlap_matrix(distance_matrix(current_sites)))):
        raise ValueError("Saved QUBO does not match current candidates; rerun build_qubo.py before QAOA.")
    n = len(c)

    print(f"n={n} qubits, k={k}, A={A}")

    h, J, const, a, b = qubo_to_ising(c, Q, A, k)
    max_err = validate_ising(c, Q, A, k, h, J, const, n)
    print(f"Ising validation vs brute-force proxy objective: max error = {max_err:.2e} ({'PASS' if max_err < 1e-8 else 'FAIL -- DO NOT TRUST RESULTS BELOW'})")
    if max_err >= 1e-8:
        raise ValueError("QUBO/Ising validation failed.")

    x_exact, val_exact = brute_force_proxy(c, Q, k, A)  # val_exact = f(x), the thing we actually maximize
    print(f"Exact proxy optimum: sites {np.array(site_ids)[x_exact == 1].tolist()}, f(x)={val_exact:.4f}")

    hamiltonian = build_hamiltonian(h, J, const, n)
    print(f"Hamiltonian: {len(hamiltonian)} Pauli terms, {n} qubits")

    for p in REPS_LIST:
        print(f"Running p={p}, {SHOTS} shots", flush=True)
        best_val, counts, opt_time, total_time = run_qaoa_depth(hamiltonian, n, p)
        summary = summarize_samples(counts, c, Q, k, A, site_ids, val_exact, SHOTS)
        summary.update(p=p, qubits=n, budget=k, penalty_A=A, backend="local qiskit Aer SamplerV2",
            sampling_seed=SEED, optimizer_seed=SEED, random_restarts=RANDOM_RESTARTS,
            optimizer_expected_energy=best_val, opt_time_s=opt_time, total_time_s=total_time,
            input_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                for name in ("data/candidate_sites.csv", "data/qubo_c.npy", "data/qubo_Q.npy", "data/qubo_params.txt")})
        Path(f"data/qaoa_result_p{p}.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        mode = summary["mode"]
        best = summary["best_feasible_sample"]
        print(f"p={p}: mode={mode['sites']}, best feasible={best['sites'] if best else None}; feasible={summary['feasible_rate']:.2%}, optimal={summary['proxy_optimal_rate']:.2%}", flush=True)
        # Retain text outputs for existing consumers, with explicit selection semantics.
        with open(f"data/qaoa_result_p{p}.txt", "w", encoding="utf-8") as f:
            f.write(f"p={p}\nshots={SHOTS}\nselection_rule={summary['selection_rule']}\n")
            f.write(f"mode_bitstring={mode['bitstring']}\nmode_sites={mode['sites']}\n")
            f.write(f"selected_bitstring={best['bitstring'] if best else None}\nsites={best['sites'] if best else None}\n")
            f.write(f"sampled_f={best['penalized_proxy_score'] if best else None}\nexact_f={val_exact}\n")
            f.write(f"feasible_rate={summary['feasible_rate']}\nproxy_optimal_rate={summary['proxy_optimal_rate']}\n")
            f.write(f"opt_time_s={opt_time}\ntotal_time_s={total_time}\ncounts={dict(counts)}\n")


if __name__ == "__main__":
    main()
