"""Create a size-checked Qollab project archive from verified repository artifacts."""

import ast
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "qollab"
FUNCTIONS = {
    "build_qubo.py": [
        "proxy_objective",
        "validate_coverage_sets",
        "coverage_budget",
        "true_coverage",
        "exact_max_coverage",
        "greedy_max_coverage",
    ],
    "repair_qaoa.py": ["validate_selection", "repair_budget", "evaluate_placement"],
    "run_qaoa.py": ["qubo_to_ising", "build_hamiltonian"],
    "qaoa_samples.py": ["decode_bitstring", "summarize_samples"],
}
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


def main():
    from build_demo_map import load_results

    load_results()  # Reject stale source artifacts before packaging their checksums.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    selected = []

    def write(name, content):
        destination = OUTPUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        selected.append(name)

    def copy(path, name=None):
        write(name or path.relative_to(ROOT).as_posix(), path.read_bytes())

    for directory in ("scripts", "tests", "docs", "data", "demo"):
        for path in sorted((ROOT / directory).glob("*")):
            if path.is_file() and path.name != "elephant_gps_raw.csv":
                copy(path)
    for path in sorted((ROOT / "data" / "benchmarks").glob("*.json")):
        copy(path)
    for path in sorted((ROOT / "demo" / "assets").glob("*")):
        if path.is_file():
            copy(path)
    write(
        "data/elephant_gps_raw.csv.gz",
        gzip.compress((ROOT / "data/elephant_gps_raw.csv").read_bytes(), mtime=0),
    )
    for name in ("LICENSE", "SUBMISSION.md", "TASKS.md"):
        copy(ROOT / name)
    copy(ROOT / "README.md", "LOCAL_README.md")
    copy(ROOT / "requirements.txt", "requirements-local.txt")
    for name in ("index.html", "main.js", "main.css", "runner.py"):
        copy(ROOT / "qollab" / name, name)
    write("requirements.txt", b"qiskit==2.5.2\n")
    core = [
        '"""Generated from repository functions by scripts/package_qollab.py; do not edit separately."""',
        "import itertools",
        "import numbers",
        "from collections.abc import Mapping",
        "import numpy as np",
        "from qiskit.quantum_info import SparsePauliOp",
        "K_BUDGET = 3",
        "",
    ]
    for name, requested in FUNCTIONS.items():
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8-sig")
        nodes = {
            node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
        }
        core.extend(
            ast.get_source_segment(source, nodes[function]) + "\n" for function in requested
        )
    write("placement_core.py", ("\n\n".join(core) + "\n").encode())
    manifest = dict(
        description="Verified repository inputs; live run remeasures saved local-Aer optimized parameters on the backend selected in Qollab. No optimizer rerun.",
        input_sha256={
            name: hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() for name in INPUT_FILES
        },
        raw_data_sha256=hashlib.sha256(
            (ROOT / "data/elephant_gps_raw.csv").read_bytes()
        ).hexdigest(),
        core_source_sha256={
            f"scripts/{name}": hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
            for name in FUNCTIONS
        },
    )
    write("bundle_manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
    write(
        "main.py",
        b'"""Optional Python-mode entry; HTML/JS files take priority in Qollab."""\nfrom runner import measure\n\ndef main(depth: int = 1, shots: int = 4096):\n    from js import sendFile\n    import json\n    result = json.loads(measure(globals()["backend"], depth, shots))\n    print(json.dumps(result["report"], indent=2))\n    sendFile("live-result.json", "application/json", json.dumps(result["report"]))\n    sendFile("map.html", "text/html", result["map_html"])\n',
    )
    readme = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    instructions = """\n## Run this Qollab project\n\nClick **Run Project**, select the built-in local simulator, and run. The visual page recomputes classical GPS coverage from the verified saved coverage matrix and displays the archived local-Aer map/results. Choose depth 1, 2, or 3 and 128–8192 measurements, then click **Measure QAOA circuit**. One fresh measurement job is sent to the backend selected in Qollab, using parameters optimized previously on local Aer. The page reports fresh selection/repair, backend/job ID, and downloadable JSON separately from the archived benchmark. Press Stop and Run to reset for another measurement. This is not a fresh optimizer run or a substitute for the deferred full IonQ experiment.\n\nThe map embeds its libraries and approximate Natural Earth country boundaries, with coordinate grid lines; it makes no online tile requests. Scroll the map panel and toggle layers to compare methods. Green markers added after a live job show that job's repaired answer.\n\nThe raw CSV is supplied as `data/elephant_gps_raw.csv.gz` to respect the 2 MB per-file limit. All project files are below that limit. For full local extraction and repeated optimization, use the GitHub repository instructions. Alternatively download these files, use Python 3.11, install `requirements-local.txt`, decompress the CSV, and follow `LOCAL_README.md`. Browser requirements.txt deliberately contains only Qiskit; NumPy is provided by Pyodide. No Aer installation or subprocesses are used by the browser entry.\n\nData/artifacts are verified by bundle_manifest.json; placement_core.py is generated from the same tested functions as the full local pipeline. Original source, tests, reports, and citations are included.\n"""
    write("README.md", (readme + instructions).encode())
    if len(selected) > 100 or any((OUTPUT / name).stat().st_size > 2_000_000 for name in selected):
        raise ValueError("Qollab upload limits exceeded.")
    archive = ROOT / "dist" / "signal-in-the-bush-qollab.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
        for name in sorted(selected):
            stream.write(OUTPUT / name, name)
    print(
        f"Created {archive}: {len(selected)} files, {archive.stat().st_size:,} bytes; largest file {max((OUTPUT / name).stat().st_size for name in selected):,} bytes."
    )


if __name__ == "__main__":
    main()
