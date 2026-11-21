# gta6-trophy-rarity-forecast-01

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/scenario718/gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/scenario718/gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

A forecast of every GTA VI (PS5) trophy's Exophase earn rate at the case target time, as five quantiles per trophy. `main.py` (Python 3, standard library only) works per trophy in logit space with rates clamped to [0.01, 99.99]: it collapses runs of equal rates to their last read (the page moves in steps between refreshes, so repeated identical reads carry no new information), fits a recency-weighted least-squares line of logit(rate) against ln(1 + hours since release) over the last ~36 hours of reads, and blends that fit with last-read persistence by point count and fit quality. The spread combines a slightly tightened house random-walk scale with the fit's residual sd and slope uncertainty, floored and capped; trophies with too few usable reads fall back to persistence plus the house spread. Fully deterministic — no randomness, no wall clock — and each case runs in a fraction of a second.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

(with a case file such as the kit's `input/p00.in` in the input directory; it writes `<case-id>.out` to the output directory.)

---

<sub>Entered on [make.fun](https://make.fun/?ref=d8zsd3e7&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
