# RUBY resource budget

## Shot inventory

The primary proposal design contains:

```text
6 geometries x 24 pulse points x 3 replicates = 432 science batches
432 batches x 2,000 shots = 864,000 primary shots
```

The hardware plan adds:

| Category | Batches | Shots/batch | Shots | Purpose |
|---|---:|---:|---:|---|
| Primary science grid | 432 | 2,000 | 864,000 | Predeclared nonadiabatic scan |
| Calibration references | 72 | 500 | 36,000 | Preparation/readout and session references |
| Mechanism controls | 54 | 1,000 | 54,000 | No-drive, endpoint and rapid-sweep controls |
| Confirmation reserve | 44 | 2,000 | 88,000 | Independent confirmation of selected effects |
| **Total** | **602** | — | **1,042,000** | — |

The additional 178,000 shots are a 20.6% overhead above the primary grid.
Calibration batches should be reduced if equivalent hosting-entity calibration
data are supplied without charging them to the project.

## QPU-hour conversion

Pulse duration alone is not QPU time. The conversion must include atom
loading/rearrangement, preparation, waveform execution, readout/reset and
per-batch overhead:

```text
QPU hours =
  (1,042,000 x host per-shot cycle seconds
   + 602 x host per-batch overhead seconds) / 3,600
  + host setup/calibration hours
```

`configs/resource_budget.json` deliberately leaves the host-verified timing
fields null. The committed calculation therefore does **not** assert a final
allocation request. It includes labelled sensitivity examples only:

| Illustrative cycle/overhead/setup | Calculated QPU hours |
|---|---:|
| 0.05 s / 2 s / 1 h | 15.81 h |
| 0.10 s / 5 s / 2 h | 31.78 h |
| 0.20 s / 10 s / 4 h | 63.56 h |

These values are not RUBY specifications. Replace the null timing values with
written TGCC/GENCI/Pasqal guidance and cite that source before copying a QPU
hour number into the proposal.

Recalculate with:

```bash
qbasin resources \
  --config configs/resource_budget.json \
  --output results/resource_budget.json
```

