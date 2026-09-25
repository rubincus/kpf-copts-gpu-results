"""Verify every solution and every per-run value of this repository against the benchmark instances.

For each solution, the script reads its instance, checks that the item indices are valid and distinct, recomputes
the weight and the objective value (every listed forfeit pair is charged, as in the integer programming model of
the KPF) and compares them with the recorded ones; a solution passes only if its weight does not exceed the
capacity. The script then checks that the per-run tables, the traces, the per-instance summary, the best-solution
files, the reference values and the certificate centres agree with the verified solutions.

    python scripts/verify_solutions.py                   # instances in instances/ (see download_instances.py)
    python scripts/verify_solutions.py --instances DIR

Only the Python standard library is used. The exit status is 0 when every check passes.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kpf_instance import Instance, parse_items, read_csv, read_manifest, sha256_file  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOL = ROOT / "solutions"


class Report:
    def __init__(self):
        self.ok = defaultdict(int)
        self.fail = defaultdict(list)
        self.order = []

    def _see(self, check):
        if check not in self.order:
            self.order.append(check)

    def passed(self, check, k=1):
        self._see(check)
        self.ok[check] += k

    def failed(self, check, msg):
        self._see(check)
        self.fail[check].append(msg)

    def print(self):
        width = max(len(c) for c in self.order)
        for c in self.order:
            bad = len(self.fail[c])
            print(f"  {c:{width}s}  {self.ok[c]:6d} passed" + (f", {bad} FAILED" if bad else ""))
        failures = [(c, m) for c in self.order for m in self.fail[c]]
        for c, m in failures[:30]:
            print(f"    {c}: {m}")
        if len(failures) > 30:
            print(f"    ... and {len(failures) - 30} more")
        return not failures


def key_of(row):
    return row["experiment"], row["variant"], row["instance"], int(row["seed"])


def check_instances(rep, manifest, folder):
    inst = {}
    for name, row in manifest.items():
        path = folder / row["file"]
        if not path.exists():
            rep.failed("instances", f"{name}: {path} not found (run scripts/download_instances.py)")
            continue
        if sha256_file(path) != row["sha256"]:
            rep.failed("instances", f"{name}: SHA-256 differs from the manifest")
            continue
        ins = Instance.read(path, name)
        if (ins.n, ins.l, ins.capacity) != (int(row["n"]), int(row["pairs"]), int(row["capacity"])):
            rep.failed("instances", f"{name}: n, pairs or capacity differ from the manifest")
            continue
        inst[name] = ins
        rep.passed("instances")
    return inst


def check_solution(rep, check, inst, name, items, value, weight, where):
    """Evaluate one solution; True when it is feasible and its recorded value and weight are exact."""
    if name not in inst:
        rep.failed(check, f"{where}: unknown instance {name}")
        return False
    try:
        f, w = inst[name].evaluate(items)
    except ValueError as e:
        rep.failed(check, f"{where}: {e}")
        return False
    if w > inst[name].capacity:
        rep.failed(check, f"{where}: weight {w} exceeds the capacity {inst[name].capacity}")
    elif f != value or w != weight:
        rep.failed(check, f"{where}: recomputed value {f} and weight {w}, recorded {value} and {weight}")
    else:
        rep.passed(check)
        return True
    return False


def check_solution_files(rep, inst):
    verified = {}
    for fp in sorted(SOL.glob("*.csv")):
        if fp.name == "certificate_centers.csv":
            continue
        check = f"solutions/{fp.name}"
        for k, row in enumerate(read_csv(fp), start=2):
            key = key_of(row)
            if key in verified:
                rep.failed(check, f"line {k}: {key} appears twice")
                continue
            items = parse_items(row["items"])
            if check_solution(rep, check, inst, row["instance"], items, int(row["value"]), int(row["weight"]),
                              f"line {k} ({row['instance']}, seed {row['seed']})"):
                verified[key] = (int(row["value"]), sorted(items))
    return verified


def check_best_files(rep, inst, manifest, verified):
    camp = defaultdict(dict)
    for (exp, var, name, seed), (value, _) in verified.items():
        if exp == "campaign":
            camp[name][seed] = value
    seen = set()
    for fp in sorted((SOL / "best").glob("*.json")):
        d = json.loads(fp.read_text())
        name, where = d["instance"], f"best/{fp.name}"
        seen.add(name)
        items = d["selected_items_0based"]
        if not check_solution(rep, "solutions/best/*.json", inst, name, items, d["value"], d["weight"], where):
            continue
        key = (d["experiment"], d["variant"], name, d["seed"])
        if d["instance_sha256"] != manifest[name]["sha256"] or d["capacity"] != inst[name].capacity:
            rep.failed("best = campaign maximum", f"{where}: instance hash or capacity differ")
        elif key not in verified or verified[key][1] != sorted(items):
            rep.failed("best = campaign maximum", f"{where}: not the solution of campaign run {key}")
        elif d["value"] != max(camp[name].values()) or d["seed"] != min(s for s, v in camp[name].items()
                                                                          if v == d["value"]):
            rep.failed("best = campaign maximum", f"{where}: not the smallest seed attaining the campaign best")
        else:
            rep.passed("best = campaign maximum")
    for name in manifest:
        if name not in seen:
            rep.failed("best = campaign maximum", f"{name}: no best-solution file")


def trace_time_to(points, value):
    """Time at which the run first reaches its final value (the last trace point when it is never recorded)."""
    return next((t for t, v in points if v == value), points[-1][0])


def check_run_tables(rep, verified):
    runs = {}
    for fp in sorted(DATA.glob("*/runs.csv")):
        if fp.parent.name == "enumeration_benchmark":
            continue
        check = f"data/{fp.parent.name}/runs.csv"
        keys = set()
        for k, row in enumerate(read_csv(fp), start=2):
            key = key_of(row)
            keys.add(key)
            if key not in verified:
                rep.failed(check, f"line {k}: no verified solution for {key}")
            elif int(row["value"]) != verified[key][0]:
                rep.failed(check, f"line {k}: value {row['value']} differs from its solution")
            else:
                rep.passed(check)
                runs[key] = row
        exp = {key[0] for key in keys}
        missing = [key for key in verified if key[0] in exp and key not in keys]
        for key in missing:
            rep.failed(check, f"verified solution {key} has no row")
        tr = DATA / fp.parent.name / "traces.csv"
        if tr.exists():
            points = defaultdict(list)
            for row in read_csv(tr):
                points[key_of(row)].append((float(row["time_s"]), int(row["value"])))
            for key in keys:
                pts = points.get(key)
                if not pts:
                    rep.failed(f"data/{fp.parent.name}/traces.csv", f"{key}: no trace")
                    continue
                ordered = all(a[0] < b[0] and a[1] < b[1] for a, b in zip(pts, pts[1:]))
                row = runs.get(key)
                if not ordered:
                    rep.failed(f"data/{fp.parent.name}/traces.csv", f"{key}: times or values do not increase")
                elif row is None or pts[-1][1] > int(row["value"]):
                    rep.failed(f"data/{fp.parent.name}/traces.csv", f"{key}: trace above the final value")
                elif abs(trace_time_to(pts, int(row["value"])) - float(row["time_to_best_s"])) > 1e-9:
                    rep.failed(f"data/{fp.parent.name}/traces.csv", f"{key}: time_to_best_s differs from the trace")
                else:
                    rep.passed(f"data/{fp.parent.name}/traces.csv")
    return runs


def check_reference_values(rep, inst):
    sources = [s for s in read_csv(DATA / "reference_sources.csv") if s["group"]]    # averages have no group
    ref = {}
    for row in read_csv(DATA / "reference_values.csv"):
        name = row["instance"]
        vals = {s["column"]: int(row[s["column"]]) for s in sources if row[s["column"]] != ""}
        top = max(vals.values())
        attaining = sorted(c for c, v in vals.items() if v == top)
        groups = "".join(g for g in "CGIMRHZ" if any(s["group"] == g and s["column"] in attaining for s in sources))
        if int(row["reference_value"]) != top:
            rep.failed("data/reference_values.csv", f"{name}: reference {row['reference_value']} is not the maximum {top}")
        elif sorted(row["sources"].split(";")) != attaining or row["source_groups"] != groups:
            rep.failed("data/reference_values.csv", f"{name}: the sources are not the columns attaining the maximum")
        elif row["proven_optimum"] == "1" and top != int(row["cplex_3h"]):
            rep.failed("data/reference_values.csv", f"{name}: proven optimum differs from the CPLEX value")
        elif name not in inst:
            rep.failed("data/reference_values.csv", f"{name}: unknown instance")
        else:
            rep.passed("data/reference_values.csv")
        ref[name] = row
    return ref


def check_summary(rep, runs, ref):
    vals = defaultdict(list)
    for (exp, var, name, seed), row in runs.items():
        if exp == "campaign":
            vals[name].append(int(row["value"]))
    for row in read_csv(DATA / "campaign" / "summary.csv"):
        name = row["instance"]
        v = vals.get(name, [])
        if not v:
            rep.failed("data/campaign/summary.csv", f"{name}: no campaign runs")
            continue
        r = int(ref[name]["reference_value"])
        best, mean = max(v), sum(v) / len(v)
        sd = math.sqrt(sum((x - mean) ** 2 for x in v) / len(v))
        status = "improved" if best > r else ("equal" if best == r else "below")
        expect = dict(runs=len(v), best=best, runs_at_best=v.count(best), runs_at_or_above_reference=sum(x >= r for x in v),
                      reference_value=r, best_minus_reference=best - r)
        bad = [k for k, e in expect.items() if int(row[k]) != e]
        if abs(float(row["mean"]) - mean) > 6e-5 or abs(float(row["sd"]) - sd) > 6e-5:
            bad.append("mean or sd")
        if row["status"] != status:
            bad.append("status")
        if bad:
            rep.failed("data/campaign/summary.csv", f"{name}: {', '.join(bad)} differ from the runs")
        else:
            rep.passed("data/campaign/summary.csv")


def check_certificates(rep, inst, verified):
    centres = {}
    for k, row in enumerate(read_csv(SOL / "certificate_centers.csv"), start=2):
        items = parse_items(row["items"])
        if not check_solution(rep, "solutions/certificate_centers.csv", inst, row["instance"], items,
                              int(row["value"]), int(row["weight"]), f"line {k} ({row['instance']})"):
            continue
        source = (row["source_experiment"], row["source_variant"], row["instance"], int(row["source_seed"]))
        if source in verified and verified[source][1] != sorted(items):
            rep.failed("certificate centre = its run", f"line {k}: differs from the solution of run {source}")
        else:
            rep.passed("certificate centre = its run")
            centres[row["instance"]] = int(row["value"])
    for row in read_csv(DATA / "certificates" / "certificates.csv"):
        name = row["instance"]
        if centres.get(name) != int(row["center_value"]):
            rep.failed("data/certificates/certificates.csv", f"{name} r={row['radius']}: centre value differs")
        else:
            rep.passed("data/certificates/certificates.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--instances", type=Path, default=ROOT / "instances", help="folder written by download_instances.py")
    args = ap.parse_args()
    rep = Report()
    manifest = read_manifest(DATA / "instances_manifest.csv")
    inst = check_instances(rep, manifest, args.instances)
    if len(inst) < len(manifest):
        rep.print()
        sys.exit("the instances are missing or differ from the manifest")
    verified = check_solution_files(rep, inst)
    check_best_files(rep, inst, manifest, verified)
    runs = check_run_tables(rep, verified)
    ref = check_reference_values(rep, inst)
    check_summary(rep, runs, ref)
    check_certificates(rep, inst, verified)
    print("Verification of the solutions and tables")
    ok = rep.print()
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
