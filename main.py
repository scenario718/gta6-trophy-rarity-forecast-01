#!/usr/bin/env python3
"""GTA VI trophy rarity forecast.

Reads one case file from $MAKEFUN_INPUT_DIR (else /input) and writes
<case-id>.out to $MAKEFUN_OUTPUT_DIR (else /output): for every trophy,
five quantiles (0.05, 0.25, 0.5, 0.75, 0.95) of its Exophase earn rate
(percent of tracked players) at the case's target time.

Model, per trophy, in logit space with rates clamped to [0.01, 99.99]:
a recency-weighted least-squares fit of logit(rate) against
ln(1 + hours since release) over the last ~36 hours of reads, blended
with last-read persistence by point count and fit quality.  The page
moves in steps, so runs of equal rates are first collapsed to their
last read: repeated identical reads carry no new information and must
not inflate the fit's point count or shrink its uncertainty.  The
spread combines a slightly tightened house random-walk scale with the
fit's residual sd and slope uncertainty, floored and capped so no
case is over- or under-confident.  Fallbacks keep every case valid:
too few usable reads means persistence plus the house spread.

Deterministic: no randomness, no wall clock, no dict-order dependence.
Python 3 standard library only.
"""

import json
import math
import os
import sys
from datetime import datetime

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z = (-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722)
LO = 0.01
HI = 99.99
SIGMA_FLOOR = 0.30
SIGMA_CAP = 2.5


def clamp_rate(r):
    if r < LO:
        return LO
    if r > HI:
        return HI
    return r


def logit(p):
    # p is a percent in [LO, HI]
    x = p / 100.0
    return math.log(x / (1.0 - x))


def inv_logit(y):
    if y >= 0:
        return 100.0 / (1.0 + math.exp(-y))
    e = math.exp(y)
    return 100.0 * e / (1.0 + e)


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def wlsq(xs, ys, ws):
    """Weighted least squares y ~ a + b*x.

    Returns (a, b, sxx, xbar); sxx is 0 when every x is identical.
    """
    sw = sum(ws)
    xbar = sum(w * x for x, w in zip(xs, ws)) / sw
    ybar = sum(w * y for y, w in zip(ys, ws)) / sw
    sxx = sum(w * (x - xbar) ** 2 for x, w in zip(xs, ws))
    if sxx <= 0.0:
        return ybar, 0.0, 0.0, xbar
    sxy = sum(w * (x - xbar) * (y - ybar)
              for x, y, w in zip(xs, ys, ws))
    b = sxy / sxx
    return ybar - b * xbar, b, sxx, xbar


def quantiles(y_mid, sigma):
    if sigma < SIGMA_FLOOR:
        sigma = SIGMA_FLOOR
    if sigma > SIGMA_CAP:
        sigma = SIGMA_CAP
    out = []
    prev = 0.0
    for z in Z:
        q = inv_logit(y_mid + z * sigma)
        q = round(q, 4)
        if q < prev:
            q = prev
        if q < 0.0:
            q = 0.0
        if q > 100.0:
            q = 100.0
        out.append(q)
        prev = q
    return out


def forecast(points, t_target_h, horizon_days):
    """points: [(hours_since_release, rate_percent)], oldest first.

    Returns the five quantile percents for one trophy.
    """
    house_sigma = 0.5 * math.sqrt(max(horizon_days, 0.0))
    if not points:
        return quantiles(logit(1.0), house_sigma)
    # Collapse each run of equal rates to its last read (the page is a
    # step function between refreshes); the final point never moves.
    steps = []
    for i, p in enumerate(points):
        if i + 1 == len(points) or points[i + 1][1] != p[1]:
            steps.append(p)
    points = steps
    y_last = logit(points[-1][1])
    t_end = points[-1][0]
    # Recent window: the last ~36 h of reads; widen when it is too thin.
    window = [p for p in points if p[0] >= t_end - 36.0]
    if len(window) < 8:
        window = points
    if len(window) >= 3:
        xs = [math.log1p(max(t, 0.0)) for t, _ in window]
        ys = [logit(r) for _, r in window]
        ws = [0.5 ** ((t_end - t) / 12.0) for t, _ in window]
        a, b, sxx, xbar = wlsq(xs, ys, ws)
        if sxx > 0.0:
            x_t = math.log1p(max(t_target_h, 0.0))
            y_fit = a + b * x_t
            dof = max(len(window) - 2, 1)
            sse = sum(w * (y - (a + b * x)) ** 2
                      for x, y, w in zip(xs, ys, ws))
            s_res = math.sqrt(sse / dof) if sse > 0.0 else 0.0
            var_fit = s_res * s_res * (1.0 + 1.0 / len(window)
                                       + (x_t - xbar) ** 2 / sxx)
            # Blend the fit with persistence: more points earn the fit
            # more trust, a noisy fit earns it less.
            w_fit = len(window) / (len(window) + 5.0)
            if w_fit > 0.85:
                w_fit = 0.85
            if s_res > 1.0:
                w_fit *= 0.5
            y_pred = w_fit * y_fit + (1.0 - w_fit) * y_last
            rw = 0.45 * math.sqrt(max(horizon_days, 0.0))
            sigma = math.sqrt(rw * rw + var_fit)
            return quantiles(y_pred, sigma)
    # Fallback: persistence plus the house random-walk spread.
    return quantiles(y_last, house_sigma)


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    names = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    if not names:
        return 1
    with open(os.path.join(in_dir, names[0]), "r", encoding="utf-8") as fh:
        case = json.load(fh)
    release = parse_time(case["game"]["release_date"] + "T00:00:00Z")
    target = parse_time(case["target"])
    t_target_h = (target - release).total_seconds() / 3600.0
    horizon_days = float(case.get("horizon_minutes", 0)) / 1440.0
    history = case.get("history") or []
    rows = []
    for idx, tr in enumerate(case["trophies"]):
        points = []
        for read in history:
            rates = read.get("rates") or []
            if idx >= len(rates):
                continue
            r = rates[idx]
            if r is None:
                continue
            stamp = read.get("slot") or read.get("at")
            t_h = (parse_time(stamp) - release).total_seconds() / 3600.0
            points.append((t_h, clamp_rate(float(r))))
        rows.append({"id": tr["id"],
                     "q": forecast(points, t_target_h, horizon_days)})
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, str(case["id"]) + ".out")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"trophies": rows}, fh, separators=(",", ":"))
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
