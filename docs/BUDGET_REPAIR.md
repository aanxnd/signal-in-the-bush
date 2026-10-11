# Classical budget repair

`scripts/repair_qaoa.py` preserves saved QAOA counts and evaluates the selected raw answer, mode, and every measured outcome before and after deterministic classical repair. Frequencies are unchanged: this is postprocessing, not new quantum sampling.

For more than three sites, remove the site with least unique GPS coverage loss until feasible. For fewer than three, add the site with greatest positive marginal GPS coverage until full or no improvement remains. Ties use ascending actual site ID. Exactly-budget selections are unchanged. Repair is idempotent and is not a swap search or replacement by an exact solution.

The repair objective is all-observation coverage, different from the proxy. Additions improve coverage; trimming can lower coverage to restore the budget. Raw infeasible results retain their coverage count but have null coverage ratios and an invalid-comparison flag. No benefit from extra sensors is counted as a budget-valid improvement.

At every depth, current selected raw and repaired sites are [0,1,2], with no actions. They score 2.8542 (the proxy optimum) and cover 883 observations (82.14% of GPS optimum 1,075). Repair does not close this modeling gap. All observed outcomes become feasible after repair, but this is a deterministic property, not a 100% quantum success rate. Shot-weighted repaired means describe the postprocessed distribution; raw means include infeasible samples and are not budget-valid benchmark comparisons.

Run `scripts/repair_qaoa.py` after QAOA and baseline generation. Outputs `data/qaoa_repair_p*.json` retain selected/modal raw/repaired metrics, action logs, distribution summaries, backend, and hashes. `data/qaoa_repair_samples_p*.csv` retain each observed bitstring, frequency, selections, actions, and metrics. Current artifacts, regenerated from canonical seed-42 benchmark samples, are authoritative.

The stage rebuilds GPS coverage, checks saved matrices and input hashes, recomputes references, and replays selection summaries. Tests cover trimming, positive-gain filling, no-gain stopping, actual-ID ties, zero budget, unchanged full-budget inputs, invalid selections, feasibility/idempotence, and infeasible coverage comparisons. Saved benchmark validation independently checks selected repairs and metrics.
