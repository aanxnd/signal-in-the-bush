# Qollab runnable package

Build from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/package_qollab.py
```

Upload `dist/signal-in-the-bush-qollab.zip` through **Code → Browse → Files**. The archive contains root-level index.html/main.js/main.css, a browser-compatible Python runner, Qiskit requirements, saved evidence, full local source/tests/docs, and compressed original raw data. Every extracted file is under 2 MB and the archive has fewer than 100 files. Do not upload the whole repository or .venv.

Qollab's [runtime documentation](https://qollab.xyz/learn/docs/runtime-environment) specifies browser Python/Pyodide, a backend selected in the Run dialog, literal data paths, and one job per run on IonQ. The package avoids subprocesses and Aer in its browser entry; requirements.txt includes Qiskit, and NumPy is provided by Pyodide. Full local requirements are retained separately as requirements-local.txt. Data used in the run have literal paths for preloading and are SHA-256 checked.

The project starts as HTML/JS. Saved benchmark selections and the generated map are clearly labeled as archived local-Aer evidence. Classical exact and greedy coverage are freshly recomputed from the verified saved observation matrix. The live measurement button binds previously optimized seed-42 QAOA angles at the chosen depth and submits one circuit to the backend selected by the judge. It performs fresh sampling, selection, and repair, not a fresh optimization. The live backend/job ID, counts, rates, selections, repair actions, and scoped measurement time can be downloaded as JSON. Fresh sampling can differ from archived results. Green map markers identify the live repaired answer; the map's existing table continues to report archived evidence.

Choose the **built-in local simulator** for the initial test. Choose depth 1/2/3 and 128–8192 shots, then click **Measure QAOA circuit**. Press Stop and Run again for another measurement. The code respects whichever backend Qollab provides; it never substitutes a hardcoded backend. IonQ execution remains deferred and has not been tested by this packaging task.

The original 7.2 MB CSV is included losslessly as data/elephant_gps_raw.csv.gz. It is not downloaded from an external service. Full extraction, optimization, conservation sensitivity, and repeated benchmarks are reproducible locally via the repository. The browser demonstration uses the verified saved matrix and previously optimized parameters to provide a practical interactive judging experience.

## Verification and current blocker

The archive passed limits and lossless raw-data roundtrip checks. Native Qiskit BasicSimulator tested the packaged live circuit; the main regression suite also covers archive limits, classical recomputation, invalid settings, and tampered inputs. The initial uploaded project initialized on Qollab, but OpenStreetMap rejected its background tile requests with HTTP 403. The corrected map embeds its libraries and public-domain boundaries, uses no online tiles, and was visually tested in a sandbox with external resources blocked. The corrected upload still needs its on-platform run/public verification.

Automated upload is currently blocked because the ChatGPT Chrome extension does not have **Allow access to file URLs** enabled. No file was uploaded by the failed attempt. Upload the prepared ZIP manually through Browse → Files, or explicitly authorize/enable that extension setting, then continue the on-platform run and visual checks. A local test does not establish a successful Qollab run. Stage 11 remains open until upload, publication, and public runnable verification are complete.

Before public verification, confirm the updated Project Card retains the theme, Qollab/IonQ attribution, data/library/AI disclosures, repository link, accurate backend statement, and eventual video link. Publishing this demonstration does not complete the deferred full IonQ experiment or the video requirement.
