# CoPTS-GPU on the knapsack problem with forfeits: solutions, data and verification

This repository holds the solutions, the per-run records and the verification scripts of the computational study of
CoPTS-GPU, a cooperative portfolio tabu search on a GPU, on the 120 benchmark instances of the knapsack problem with
forfeits (KPF) of Capobianco et al. (2022). Every solution can be checked with the scripts included here, which use
only the Python standard library.

## Results

CoPTS-GPU performed 6 independent runs of 120 s on each instance (720 runs). The reference value of an
instance is the best value reported for it under the integer programming model of the KPF
(`data/reference_values.csv`). The best value of CoPTS-GPU exceeds the reference value on 5 instances,
equals it on 101 and is below it on 14, and it attains the proven optimum on all 19 instances whose
optimum was proven by CPLEX. New best-known values:

| Instance | Reference value | CoPTS-GPU |
|---|---:|---:|
| O_1000_02 | 4994 | 4995 |
| O_1000_04 | 5144 | 5147 |
| LK_1000_02 | 5164 | 5167 |
| MF_1000_04 | 4598 | 4599 |
| MF_1000_10 | 4672 | 4674 |

Per-instance results are in `data/campaign/summary.csv`.

## Verify the solutions

Python 3.8 or later is required.

```sh
python scripts/download_instances.py
python scripts/verify_solutions.py
```

`download_instances.py` downloads the archive `kpf_soco_instances.zip` from the public repository
[neteasefans/knapsack-problem-with-forfeits-](https://github.com/neteasefans/knapsack-problem-with-forfeits-) at
commit `85ff5e1`, checks its SHA-256 and the SHA-256 of every instance file against
`data/instances_manifest.csv`, and writes the instances to `instances/`. A local copy of the archive can be given
with `--archive`. The instances are not redistributed here.

`verify_solutions.py` recomputes the weight and the objective value of every solution and checks that it fits in the
knapsack. The objective charges every listed forfeit pair, as the integer programming model does with one variable
per listed pair; some instances list the same pair of items more than once, and each listing is charged. The script
then checks that the per-run tables, the traces, the per-instance summary, the best-solution files, the reference
values and the certificate centres agree with the verified solutions. The evaluator has unit tests:

```sh
python -m unittest discover -s scripts
```

## Hamming-ball certificates

On the six instances of sets LK and MF with n of at least 800 on which the best value of CoPTS-GPU is below the
reference value, exact problems examine the neighbourhood of its best solution. Each one asks HiGHS for a solution
within Hamming distance r of the best solution, with all items free, whose value is higher; when HiGHS proves the
problem infeasible, no such solution exists. `data/certificates/certificates.csv` lists the 33 problems
solved, with radius 14 certified on all six instances, and `scripts/certificate.py` reproduces them:

```sh
python -m pip install -r requirements.txt
python scripts/certificate.py --instance LK_800_08 --radius 6
python scripts/certificate.py --all
```

## Contents

- `data/instances_manifest.csv`: file, size and SHA-256 of every instance; `data/instances_source.json`: the source
  archive.
- `data/reference_values.csv`: reference value of every instance, the sources that attain it and the values of every
  source; `data/reference_sources.csv` describes each column. The source groups C, G, I, M, R, H and Z are those of
  the tables of the manuscript.
- `data/campaign/`: `runs.csv` (one row per run: value, weight, time at which the run reaches its best value, wall
  and kernel time, iterations, walkers, budget and configuration hash), `traces.csv` (best value of each run at each
  improvement, read at epoch boundaries) and `summary.csv` (one row per instance).
- Runs and traces of the analyses of the manuscript, with `data/variants.csv` describing each variant; the default
  configuration of these analyses is the campaign run with the same instance and seed:
  - `data/ablation/`: 4 variants that each remove one component, on 12 instances with seeds 1 to 3 and runs of 120 s (144 runs).
  - `data/late_ablation/`: the variants without restarts and without archive on the 7 instances on which at least two of five campaign runs improve after 10 s or end at different values, with seeds 1 to 5 and runs of 120 s (70 runs).
  - `data/sensitivity/`: a low and a high value of each of six parameters, on 12 instances with seeds 1 to 3 and runs of 60 s (432 runs).
  - `data/design_study/`: 10 variants of the design on the 6 instances of sets LK and MF with n of at least 800 on which the best value of CoPTS-GPU is below the reference value, with seed 1 and runs of 120 s or 600 s (60 runs).
- `data/enumeration_benchmark/runs.csv`: the class evaluation of the swap moves against their explicit enumeration,
  with the same search and seeds: time per iteration, the best value after the initial solutions and after each
  epoch, and the digest of the trajectory, which is the same in both modes.
- `data/certificates/certificates.csv`: the Hamming-ball certificates.
- `solutions/`: the best solution of every run, as selected items numbered from 0, in `campaign.csv` and in one file
  per analysis; `best/<instance>.json` holds the best solution of each instance (the smallest seed attaining the
  best value of the campaign), and `certificate_centers.csv` the centre of each certificate.
- `PUBLIC_EXPORT_MANIFEST.json`: export date, number of runs of each experiment and SHA-256 of every file.

The implementation of CoPTS-GPU is maintained separately.

## References

- Capobianco, G., D'Ambrosio, C., Pavone, L., Raiconi, A., Vitale, G., Sebastiano, F., 2022. A hybrid metaheuristic
  for the knapsack problem with forfeits. Soft Computing 26, 749-762. https://doi.org/10.1007/s00500-021-06331-x
- Jovanovic, R., Voß, S., 2024. Fixed set search matheuristic applied to the knapsack problem with forfeits.
  Computers & Operations Research 168, 106685. https://doi.org/10.1016/j.cor.2024.106685
- Souto de Jesus Augusto, G., 2025. A hybrid matheuristic applied to the knapsack problem with forfeits. Master's
  thesis, COPPE, Universidade Federal do Rio de Janeiro.
- Vieira, M.M., 2023. Uma meta-heurística para o problema da mochila com penalidades. Master's thesis, Universidade
  Federal de Alagoas. https://www.repositorio.ufal.br/handle/123456789/14877
- Zhao, J., Hifi, M., 2024. A reinforcement learning-driven cooperative scatter search for the knapsack problem with
  forfeits. Computers & Industrial Engineering 198, 110713. https://doi.org/10.1016/j.cie.2024.110713
- Zhou, K., Luo, X., Zhao, J., Song, Y., 2026. CUDA-accelerated cooperative scatter search for solving the knapsack
  problem with forfeits. Journal of King Saud University Computer and Information Sciences 38, 462.
  https://doi.org/10.1007/s44443-026-00717-3
- Zhou, Q., Hao, J.-K., Jiang, Z.-Z., Wu, Q., 2025. Adaptive feasible and infeasible evolutionary search for the
  knapsack problem with forfeits. International Transactions in Operational Research 32, 1442-1471.
  https://doi.org/10.1111/itor.13512
