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
```

Generated artifacts record configuration and seeds. Emulator wall times are
machine-dependent and should not be treated as hardware timings.
