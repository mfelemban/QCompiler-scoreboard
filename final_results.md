# Final Test Results — COE 530 (Term 252)

Each group's optimizer was run against 5 benchmark circuits of escalating
difficulty (circuit 1: very easy → circuit 5: very hard). All circuits
were run locally; metrics are computed on the **fully decomposed**
optimized output (custom gate definitions in QASM are unfolded before
counting depth and gate count, so all groups are measured the same way).

**Score formula** (lower is better): `10 · Qubits + Depth + Gates`

## Leaderboard

| Rank | Team             |    C1 |    C2 |    C3 |    C4 |    C5 |  Total |
|:----:|:-----------------|------:|------:|------:|------:|------:|-------:|
| 1    | Abdulrahman      |  36.0 |  65.0 |  97.0 | 145.0 | 157.0 |  500.0 |
| 2    | Hanbash          |  36.0 |  65.0 |  99.0 | 158.0 | 219.0 |  577.0 |
| 3    | Zahra and Team   |  36.0 |  65.0 | 101.0 | 157.0 | 219.0 |  578.0 |
| 4    | Ibraheem         |  36.0 |  65.0 | 101.0 | 158.0 | 219.0 |  579.0 |
| 5    | Rawan and Team   |  36.0 |  65.0 | 104.0 | 158.0 | 219.0 |  582.0 |
| 6    | Mutab and Team   |  36.0 |  70.0 | 103.0 | 160.0 | 219.0 |  588.0 |
| 7    | Ryadh and Team   |  36.0 |  64.0 |  99.0 | 157.0 | 236.0 |  592.0 |
| 8    | Fahad            |  36.0 |  65.0 |  97.0 | 166.0 | 229.0 |  593.0 |
| 9    | Badr             |  36.0 |  65.0 | 105.0 | 182.0 | 229.0 |  617.0 |
| 10   | Zining           |  36.0 |  65.0 | 113.0 | 223.0 | 316.0 |  753.0 |

## Per-circuit best score

| Circuit | Baseline (unoptimized) |  Best | Best team(s) |
|:-:|------:|------:|:------|
| 1 |  55.0 |  36.0 | All groups (tied) |
| 2 | 103.0 |  64.0 | Ryadh and Team |
| 3 | 147.0 |  97.0 | Abdulrahman, Fahad |
| 4 | 247.0 | 145.0 | Abdulrahman |
| 5 | 322.0 | 157.0 | Abdulrahman |

## Benchmarks

| # | Difficulty | Qubits | Depth | Gates | Baseline score |
|:-:|:--|:-:|:-:|:-:|:-:|
| 1 | very easy | 3 | 10 |  15 |  55 |
| 2 | easy      | 5 | 16 |  37 | 103 |
| 3 | medium    | 7 | 19 |  58 | 147 |
| 4 | hard      | 10 | 33 | 114 | 247 |
| 5 | very hard | 12 | 23 | 179 | 322 |

## Notes

- All 50 (group, circuit) pairs completed and passed automatic
  unitary-equivalence verification.
