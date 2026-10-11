# Two-minute demo script

Status: script only; recording and attachment remain open. This version describes verified local Aer execution. Do not call it an IonQ run unless stage 9 is completed and the narration/results are updated from saved evidence.

## 0:00–0:20 — Problem

Show the map with the GPS trail and candidates enabled.

“Where should a conservation team place three monitoring sites? Signal in the Bush explores that question using real GPS observations of one elephant in Gourma, Mali, and compares classical placement algorithms with a quantum algorithm called QAOA.”

## 0:20–0:45 — Data and candidate sites

Hover over a candidate, then zoom in to its monitoring zone.

“We use about 22,000 observations recorded from 2008 to 2010. After checking movement intervals, we select 15 observed transit locations with local support. Each site has an assumed 400-metre monitoring zone. That is a planning assumption, not a camera detection range, and these locations still need field validation.”

## 0:45–1:10 — Hybrid computation

Show the results table and QAOA depth layers.

“The classical baseline finds the three sites covering the most recorded observations. QAOA uses 15 simulated qubits to optimize a simpler transit-activity score. We check the mathematical conversion exhaustively, run three circuit depths on local Qiskit Aer, select the best feasible measured answer, and preserve raw and classically repaired results separately.”

## 1:10–1:40 — Actual result

Enable only classical and depth-3 repaired layers. Point out shared sites 0/1 and differing sites 4/2; show the table.

“The classical optimum covers 1,075 observations at sites zero, one, and four. All nine seeded QAOA trials found the proxy optimum at zero, one, and two, covering 883 observations—about 82 percent of the coverage optimum. Those selected answers already use three sites, so budget repair leaves them unchanged. The comparison reveals the cost of our simplified objective; it does not show quantum advantage.”

## 1:40–2:00 — Evidence and close

Show README setup and the repeated benchmark report.

“The repository includes input hashes, full measurement counts, repeated timing, convergence logs, tests, and this map. Classical methods are faster here. The IonQ simulator run, public project verification, and video submission are still pending. This is a reproducible local experiment, with its assumptions and limitations visible.”

Before recording, confirm the latest artifact values and completion states. Keep required support attribution visible: “This effort is supported by Qollab & IonQ.” Include the repository link and AI/data/library disclosures from SUBMISSION.md in the accompanying description. Do not describe Banzena as a selected site or claim that covered observations equal protected animals.
