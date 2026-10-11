"""Deterministic evaluation of a measured QAOA distribution (no repair)."""

import numbers
from collections.abc import Mapping

import numpy as np
from build_qubo import proxy_objective


def decode_bitstring(bitstring, n):
    if not isinstance(bitstring, str):
        raise ValueError("Bitstrings must be strings.")
    bits = bitstring.replace(" ", "")
    if len(bits) != n or set(bits) - {"0", "1"}:
        raise ValueError(f"Expected a {n}-bit binary measurement.")
    return np.array([int(bit) for bit in bits[::-1]], dtype=int)


def summarize_samples(counts, c, Q, k, A, site_ids, exact_proxy_value, expected_shots=None):
    """Select best sampled feasible proxy score; mode is a separate diagnostic.

    Feasible means <=k sites. Ties: higher count, then lexicographically smaller
    Qiskit bitstring. All rate denominators are shots, not unique bitstrings.
    """
    c, Q = np.asarray(c, dtype=float), np.asarray(Q, dtype=float)
    if c.ndim != 1 or not 1 <= len(c) <= 15:
        raise ValueError("Expected one to fifteen site weights.")
    n = len(c)
    if (
        not np.isfinite(c).all()
        or not np.isfinite(Q).all()
        or not np.isfinite([A, exact_proxy_value]).all()
        or A < 0
        or isinstance(k, bool)
        or not isinstance(k, numbers.Integral)
        or not 0 <= k <= n
    ):
        raise ValueError("Objective and budget must be finite and valid.")
    if (
        len(site_ids) != n
        or len(set(site_ids)) != n
        or Q.shape != (n, n)
        or any(
            isinstance(i, (bool, np.bool_)) or not isinstance(i, numbers.Integral) or i < 0
            for i in site_ids
        )
    ):
        raise ValueError("Site IDs and objective dimensions must agree.")
    if not np.allclose(Q, Q.T, atol=1e-12, rtol=0) or not np.allclose(
        np.diag(Q), 0, atol=1e-12, rtol=0
    ):
        raise ValueError("Overlap matrix must be symmetric with zero diagonal.")
    if not isinstance(counts, Mapping):
        raise ValueError("Counts must be a bitstring-to-count mapping.")
    if expected_shots is not None and (
        isinstance(expected_shots, (bool, np.bool_))
        or not isinstance(expected_shots, numbers.Integral)
        or expected_shots <= 0
    ):
        raise ValueError("Expected shots must be a positive integer.")
    normalized = {}
    for bits, count in counts.items():
        decode_bitstring(bits, n)
        if (
            isinstance(count, (bool, np.bool_))
            or not isinstance(count, numbers.Integral)
            or count <= 0
        ):
            raise ValueError("Sample counts must be positive integers.")
        key = bits.replace(" ", "")
        normalized[key] = normalized.get(key, 0) + int(count)
    shots = sum(normalized.values())
    if shots == 0 or (expected_shots is not None and shots != expected_shots):
        raise ValueError("Sample counts must sum to the expected positive shot count.")
    records = []
    for bits, count in normalized.items():
        x = decode_bitstring(bits, n)
        selected = int(x.sum())
        score = float(proxy_objective(x, c, Q, k, A))
        if score > exact_proxy_value + 1e-9:
            raise ValueError("A sampled score exceeds the supplied exact proxy optimum.")
        records.append(
            dict(
                bitstring=bits,
                count=count,
                sites=np.asarray(site_ids)[x == 1].tolist(),
                selected_count=selected,
                feasible=selected <= k,
                exactly_budget=selected == k,
                penalized_proxy_score=score,
                proxy_score_ratio=score / exact_proxy_value if exact_proxy_value > 0 else None,
            )
        )
    mode = min(records, key=lambda r: (-r["count"], r["bitstring"]))
    feasible = [r for r in records if r["feasible"]]
    best = (
        min(feasible, key=lambda r: (-r["penalized_proxy_score"], -r["count"], r["bitstring"]))
        if feasible
        else None
    )
    optimal_shots = sum(
        r["count"]
        for r in records
        if np.isclose(r["penalized_proxy_score"], exact_proxy_value, atol=1e-9, rtol=0)
    )
    feasible_shots = sum(r["count"] for r in feasible)
    exact_budget_shots = sum(r["count"] for r in records if r["exactly_budget"])
    return dict(
        selection_rule="best observed feasible penalized proxy score; ties by count then bitstring",
        feasibility_rule="selected_count <= k; under-budget samples are feasible",
        shots=shots,
        unique_bitstrings=len(records),
        mode=mode,
        best_feasible_sample=best,
        selected_raw=best,
        selection_status="selected" if best else "no feasible sample",
        feasible_shots=feasible_shots,
        feasible_rate=feasible_shots / shots,
        exactly_budget_shots=exact_budget_shots,
        exactly_budget_rate=exact_budget_shots / shots,
        proxy_optimal_shots=optimal_shots,
        proxy_optimal_rate=optimal_shots / shots,
        expected_penalized_proxy_score=sum(r["count"] * r["penalized_proxy_score"] for r in records)
        / shots,
        exact_proxy_value=float(exact_proxy_value),
        counts=normalized,
    )
