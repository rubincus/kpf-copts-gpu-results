"""Reproduce the Hamming-ball certificates of data/certificates/certificates.csv.

A certificate states that no solution within Hamming distance r of a centre solution x0 has a value higher than
f(x0). The script solves, with HiGHS through SciPy, the integer programming model of the KPF with all items free:
binary x_i, one variable v_ij in [0, 1] for each pair of items with total forfeit cost D_ij > 0 (the costs of a pair
listed more than once are added), v_ij >= x_i + x_j - 1, the capacity constraint, the ball

    sum_{i : x0_i = 1} (1 - x_i) + sum_{i : x0_i = 0} x_i <= r,

and the cut f(x) = p.x - D.v >= f(x0) + 1. When HiGHS proves this problem infeasible, no solution within distance r
of x0 improves on it. The centres are in solutions/certificate_centers.csv.

    python scripts/certificate.py --instance LK_800_08 --radius 6
    python scripts/certificate.py --all                 # every certificate of data/certificates/certificates.csv

Requires numpy and scipy >= 1.9 (pip install -r requirements.txt) and the instances (scripts/download_instances.py).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kpf_instance import Instance, parse_items, read_csv, read_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def ball_problem(ins, x0, f0, radius):
    n = ins.n
    D = {}
    for i, j, d in ins.pairs:
        a, b = min(i, j), max(i, j)
        D[a, b] = D.get((a, b), 0) + d
    pairs = sorted(k for k, d in D.items() if d > 0)
    m = len(pairs)
    p = np.array(ins.profits, dtype=float)
    w = np.array(ins.weights, dtype=float)
    dk = np.array([D[k] for k in pairs], dtype=float)
    rows, cols, vals, lo, hi = [], [], [], [], []
    r = 0
    rows += [r] * n; cols += list(range(n)); vals += list(w); lo.append(-np.inf); hi.append(float(ins.capacity)); r += 1
    for k, (a, b) in enumerate(pairs):                        # v_ab >= x_a + x_b - 1
        rows += [r, r, r]; cols += [a, b, n + k]; vals += [1.0, 1.0, -1.0]; lo.append(-np.inf); hi.append(1.0); r += 1
    inside = x0 == 1                                          # Hamming ball of radius r around x0
    rows += [r] * n; cols += list(range(n)); vals += list(np.where(inside, -1.0, 1.0))
    lo.append(-np.inf); hi.append(float(radius - inside.sum())); r += 1
    rows += [r] * (n + m); cols += list(range(n + m)); vals += list(np.concatenate([p, -dk]))   # f >= f0 + 1
    lo.append(float(f0 + 1)); hi.append(np.inf); r += 1
    A = coo_matrix((vals, (rows, cols)), shape=(r, n + m)).tocsr()
    c = np.concatenate([-p, dk])
    integrality = np.concatenate([np.ones(n), np.zeros(m)])
    return c, LinearConstraint(A, np.array(lo), np.array(hi)), integrality, Bounds(np.zeros(n + m), np.ones(n + m))


def certify(ins, items, f0, radius, time_limit):
    x0 = np.zeros(ins.n, dtype=np.int64)
    x0[items] = 1
    c, cons, integrality, bounds = ball_problem(ins, x0, f0, radius)
    t0 = time.time()
    res = milp(c, constraints=cons, integrality=integrality, bounds=bounds,
               options={"time_limit": time_limit, "disp": False, "mip_rel_gap": 0.0})
    seconds = time.time() - t0
    if res.status == 2:
        return "certified", seconds
    if res.x is not None:
        sel = [i for i in range(ins.n) if res.x[i] > 0.5]
        f, wgt = ins.evaluate(sel)
        if wgt <= ins.capacity and f > f0:
            return f"better solution with value {f}", seconds
    return "time limit", seconds


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--instance", help="instance name, e.g. LK_800_08")
    ap.add_argument("--radius", type=int, nargs="+", help="radii to certify")
    ap.add_argument("--all", action="store_true", help="every certificate listed in data/certificates/certificates.csv")
    ap.add_argument("--time-limit", type=float, default=3600.0, help="seconds per problem (default 3600)")
    ap.add_argument("--instances", type=Path, default=ROOT / "instances")
    args = ap.parse_args()
    if args.all:
        todo = [(r["instance"], int(r["radius"])) for r in read_csv(ROOT / "data" / "certificates" / "certificates.csv")]
    elif args.instance and args.radius:
        todo = [(args.instance, r) for r in args.radius]
    else:
        ap.error("give --instance and --radius, or --all")
    manifest = read_manifest(ROOT / "data" / "instances_manifest.csv")
    centres = {r["instance"]: r for r in read_csv(ROOT / "solutions" / "certificate_centers.csv")}
    for name, radius in todo:
        ins = Instance.read(args.instances / manifest[name]["file"], name)
        centre = centres[name]
        items = parse_items(centre["items"])
        f0, wgt = ins.evaluate(items)
        assert f0 == int(centre["value"]) and wgt <= ins.capacity, f"{name}: the centre does not verify"
        verdict, seconds = certify(ins, items, f0, radius, args.time_limit)
        print(f"{name}  r={radius:<3d} centre value {f0}: {verdict}  [{seconds:.1f} s]", flush=True)


if __name__ == "__main__":
    main()
