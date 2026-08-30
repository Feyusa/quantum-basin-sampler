# Curated results

This directory contains small, reproducible reference results suitable for
version control. Large production scans remain ignored by default.

## Included

- `proposal_landscape_screen.csv`: exact basin/barrier screening for the six
  proposal geometries at the selected final detunings.
- `disorder_ensemble_screen.csv`: exact screening across three connected
  jittered-Kagome and three connected amorphous realizations.
- `quickstart_verified/`: the fully verified nine-atom end-to-end run with
  eight pulse points, two independent replicates, 300 shots per method, and
  100 finite-shot bootstrap resamples. It includes CSV/JSON data and PNG plots.
- `n12_coarse_scan/`: a verified connected jittered-Kagome scan with 12 atoms,
  eight pulse points, two replicates, 500 samples per method, exact basin and
  barrier analysis, and uniform-random/annealing/parallel-tempering baselines.
- `resource_budget.json`: 1,042,000-shot science/control inventory and labelled
  QPU-hour sensitivity calculations. The host-verified estimate remains null.

## Reproduce

From the repository root:

```bash
qbasin screen \
  --config configs/proposal_scan.json \
  --output results/proposal_landscape_screen.csv

qbasin screen \
  --config configs/disorder_ensemble_screen.json \
  --output results/disorder_ensemble_screen.csv

qbasin scan \
  --config configs/quickstart.json \
  --output results/quickstart_verified

qbasin scan \
  --config configs/n12_coarse_scan.json \
  --output results/n12_coarse_scan

qbasin resources \
  --config configs/resource_budget.json \
  --output results/resource_budget.json
```

Generated artifacts record configuration and seeds. Emulator wall times are
machine-dependent and should not be treated as hardware timings.
