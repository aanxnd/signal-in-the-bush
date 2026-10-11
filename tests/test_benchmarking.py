import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from benchmark_pipeline import mean_std, write_metrics
import run_qaoa


class BenchmarkTests(unittest.TestCase):
    def test_sample_standard_deviation(self):
        stats = mean_std([1., 3.])
        self.assertEqual(stats['n'], 2)
        self.assertEqual(stats['mean'], 2.)
        self.assertAlmostEqual(stats['std'], np.sqrt(2.))
        self.assertEqual(mean_std([2.])['std'], 0.)

    def test_summary_generation_without_live_solver_state(self):
        classical = [dict(method=name, wall_time_s=float(i), covered_fixes=10,
            coverage_ratio_to_feasible_optimum=1.)
            for name in ('exact_gps_coverage', 'greedy_gps_coverage', 'exact_proxy') for i in (1, 2)]
        hybrid = [dict(p=p, seed=seed, hybrid_wall_time_s=float(i),
            repaired_metrics=dict(covered_fixes=8, coverage_ratio_to_feasible_optimum=.8,
                                  penalized_proxy_score=2.),
            proxy_optimal_rate=.1, feasible_rate=.7,
            convergence={'all_restarts_converged': False})
            for p in (1, 2, 3) for i, seed in enumerate((42, 43, 44), 1)]
        with patch('pandas.DataFrame.to_csv'), patch('pathlib.Path.write_text') as writer:
            rows = write_metrics(classical, hybrid)
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1]['mean_wall_time_s'], 2.)
        self.assertEqual(rows[-1]['std_wall_time_s'], 1.)
        self.assertIn('QAOA_selection_repair', writer.call_args.args[0])
        with self.assertRaises(ValueError):
            write_metrics(classical, hybrid[:-1])
        with self.assertRaises(ValueError):
            write_metrics(classical, hybrid + [hybrid[0]])

    def test_seeded_sampling_and_convergence_evidence(self):
        h, J, const, _, _ = run_qaoa.qubo_to_ising(np.array([1., .5]), np.zeros((2, 2)), 1., 1)
        hamiltonian = run_qaoa.build_hamiltonian(h, J, const, 2)
        with patch.object(run_qaoa, 'RANDOM_RESTARTS', 1), patch.object(run_qaoa, 'MAX_ITERATIONS', 30):
            first = run_qaoa.run_qaoa_depth(hamiltonian, 2, 1, shots=128, seed=10)
            second = run_qaoa.run_qaoa_depth(hamiltonian, 2, 1, shots=128, seed=10)
        self.assertEqual(first[1], second[1])
        self.assertEqual(sum(first[1].values()), 128)
        evidence = first[4]['restarts'][0]
        self.assertEqual(evidence['evaluations'], len(evidence['energy_history']))
        self.assertIn(evidence['final_energy'], evidence['energy_history'])
        self.assertGreater(first[3], 0)
        self.assertGreaterEqual(first[3], first[2])
        self.assertIn('success', evidence)
        self.assertEqual(first[4]['aer_threads'], 1)


if __name__ == '__main__':
    unittest.main()
