"""Run all local pipeline stages from the repository root, stopping on failure."""
from pathlib import Path
import subprocess
import sys
import time


def main():
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Use Python 3.11 with the pinned requirements.txt environment.")
    root = Path(__file__).resolve().parents[1]
    (root / "demo").mkdir(exist_ok=True)
    for script, outputs in (
        ("extract_pinch_points.py", ("data/candidate_sites.csv", "data/dwell_sites_context.csv")),
        ("build_qubo.py", ("data/qubo_c.npy", "data/qubo_Q.npy", "data/qubo_params.txt",
                           "data/coverage_baselines.json", "data/coverage_sets.npz", "data/coverage_demand.csv")),
        ("run_qaoa.py", tuple(f"data/qaoa_result_p{p}.{extension}" for p in (1, 2, 3)
                              for extension in ("txt", "json"))),
        ("build_demo_map.py", ("demo/map.html",)),
    ):
        print(f"\nRunning {script}", flush=True)
        started = time.time()
        subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "scripts" / script)],
            cwd=root,
            check=True,
        )
        for output in outputs:
            path = root / output
            if not path.is_file() or path.stat().st_size == 0 or path.stat().st_mtime < started:
                raise SystemExit(f"{script} did not regenerate a nonempty {output}; stopping.")


if __name__ == "__main__":
    main()
