# Local execution and verification

The supported environment is 64-bit CPython 3.11; Windows Python 3.11.4 is verified. requirements.txt pins direct and transitive dependencies. Setup commands are in [README.md](../README.md#run-locally). No Qollab credentials are used by the local pipeline.

`scripts/run_pipeline.py` executes extraction, coverage/QUBO, QAOA (or repeated benchmarking), repair, and map generation from the repository root. Each subprocess must succeed and regenerate nonempty expected outputs with fresh modification times. Both map.html and map_data.json are checked. A failed step stops the runner.

Earlier clean-source execution established environment reproducibility; subsequent stages corrected the model and replaced old eight-site artifacts. The current instance has 15 sites and a three-site budget. Current results, not historical intermediate runs, are documented in the README and data artifacts.

Verification commands:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q scripts tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_benchmarks.py
```

For complete recomputation use `scripts/run_pipeline.py --benchmark`, then run `scripts/validate_conservation.py`. Rebuilding the map and validating saved benchmarks do not repeat quantum optimization. Pinned sampling is reproducible on the tested platform/configuration; cross-platform bitwise agreement is not promised.

Local execution, numerical consistency, and browser checks do not establish ecological effectiveness or fulfill the outstanding IonQ/publication/video requirements.
