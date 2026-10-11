# Local execution validation — 2026-10-11

Task 1 of MASTER_TASKS.md completed on Windows with CPython 3.11.4 (64-bit).
An isolated `.venv` was created without system site packages. All installed
application dependencies are pinned in root `requirements.txt`; installation
against that file and `pip check` passed. All scripts passed `compileall`.

## Clean-source run

Exported tracked HEAD files using `git archive` into `.verification/clean`,
applied the map compatibility fix and new runner/setup files, and removed all
generated data outputs and the saved map. Only the committed raw/reference CSVs
and dataset README remained in `data/` before execution. This is a clean source
export with the pending task changes, not a run against stale saved QUBO results.

Ran `.venv/Scripts/python.exe .verification/clean/scripts/run_pipeline.py`.
The runner used the clean copy as its working directory. All four stages
completed sequentially with exit code 0:

| Stage | Observed output |
|---|---|
| Extraction | 8 candidate sites; 40 dwell context sites |
| QUBO | Regenerated coefficient arrays and parameters; proxy optimum [0, 2, 7] |
| QAOA | Ising validation passed; regenerated results at p=1, 2, 3 with 4096 shots each |
| Map | Regenerated `demo/map.html`, 184,333 bytes; 21,972 trail fixes |

QAOA optimizer/sampling times were approximately 5.73 / 13.16 / 16.69 seconds
for p=1 / 2 / 3 in this single validation run. These are execution observations,
not repeated benchmark measurements. The p=1 modal sample varied from the saved
repository result, as expected with currently unseeded final sampling.

The map's Python 3.11-incompatible f-string was replaced with an HTML camera
entity. No optimization or conservation modeling was changed in this task.
The clean-copy outputs and local console log (`.verification/pipeline.log`) are
ignored by Git; existing committed result artifacts were left untouched.

This validates local execution only. The existing baseline still measures
cluster-centroid demand, not actual GPS-fix coverage; score/coverage claims,
site geometry, repair, reproducible sampling, map correctness/accessibility,
and IonQ/Qollab execution remain separate open tasks. Browser rendering was
not audited in this task. See the README for fresh-clone installation commands.

## Step 1 follow-up audit

Installed the exact requirements file into a second fresh isolated Python 3.11
environment; dependency checks passed. Added per-stage checks to the runner:
every expected output must be nonempty and have a modification time after the
stage began. This catches scripts that return exit code 0 early without writing
results, preventing silent reuse of stale artifacts. A simulated no-output stage
was correctly rejected, and the updated runner completed all four real stages
again in the clean source export. `compileall` and `git diff --check` passed.
Step 1 has no outstanding execution/setup blocker; proceed to step 2.
