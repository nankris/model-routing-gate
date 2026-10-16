#!/usr/bin/env python3
"""Compare routed arm (gate + routed run) vs always-Haiku / always-Opus (017 raw rows, reused) + fresh Opus rerun."""
import csv, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{E}/results"
gate = {r["task"]: r for r in csv.DictReader(open(f"{R}/routes.csv"))}
tasks = list(gate)
old = [r for r in csv.DictReader(open(f"{R}/017_runs.csv")) if r["task"] in gate]
new = list(csv.DictReader(open(f"{R}/runs.csv")))
def arm(rows, cond, add_gate=False):
    rs = {r["task"]: r for r in rows if r["cond"] == cond}
    assert set(rs) == set(tasks), (cond, set(tasks) - set(rs))
    run = sum(float(rs[t]["est_cost_usd"]) for t in tasks)
    g = sum(float(gate[t]["gate_cost_usd"]) for t in tasks) if add_gate else 0.0
    return dict(solved=sum(rs[t]["passed"] == "True" for t in tasks), run=run, gate=g,
                wall=sum(float(rs[t]["wall_s"]) for t in tasks) / len(tasks) + (sum(float(gate[t]["gate_wall_s"]) for t in tasks) / len(tasks) if add_gate else 0))
arms = [("always-Haiku (017 haiku_medium, reused)", arm(old, "haiku_medium")),
        ("routed: Haiku gate -> Haiku/Opus (new)", arm(new, "routed", True)),
        ("always-Opus (017 opus_default, reused)", arm(old, "opus_default")),
        ("always-Opus rerun (new, drift check)", arm(new, "opus_default_rerun"))]
n = len(tasks)
with open(f"{R}/summary.csv", "w") as f:
    w = csv.writer(f); w.writerow(["arm", "n", "solved", "run_cost", "gate_cost", "total_cost", "cost_per_task", "cost_per_solved", "wall_per_task_s"])
    for name, a in arms:
        tot = a["run"] + a["gate"]
        w.writerow([name, n, a["solved"], round(a["run"], 4), round(a["gate"], 4), round(tot, 4), round(tot / n, 5), round(tot / max(a["solved"], 1), 5), round(a["wall"], 1)])
        print(f"{name:45s} {a['solved']}/{n}  run ${a['run']:.4f} gate ${a['gate']:.4f} total ${tot:.4f}  per-task ${tot/n:.4f}  wall {a['wall']:.1f}s")
print("routes:", {t: gate[t]["label"] for t in tasks})
# chart: $ per task, log x so the 30x gap and the gate overhead are both visible
fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
labels = [a[0] for a in arms][::-1]; vals = [(a[1]["run"] + a[1]["gate"]) / n for a in arms][::-1]
cols = ["#2a78d6" if "routed" not in l else "#eb6834" for l in labels]
ax.barh(labels, vals, color=cols, height=0.55)
for i, (l, v) in enumerate(zip(labels, vals)):
    a = dict(arms)[l]
    extra = f"  (gate \\${a['gate']/n:.4f} = {a['gate']/(a['run']+a['gate']):.0%})" if a["gate"] else ""
    ax.text(v * 1.08, i, f"\\${v:.4f}/task · {a['solved']}/{n} pass{extra}", va="center", fontsize=8, color="#0b0b0b")
ax.set_xscale("log"); ax.set_xlim(1e-3, 2)
ax.set_xlabel("API-equivalent est. $ per task (log scale)", color="#52514e", fontsize=9)
ax.set_title("#061 Haiku routing gate on 017's 10 tasks: gate said EASY 10/10", fontsize=10, loc="left", color="#0b0b0b")
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.tick_params(labelsize=8, colors="#52514e"); ax.grid(axis="x", color="#e6e5e0", lw=0.6); ax.set_axisbelow(True)
plt.tight_layout(); plt.savefig(f"{R}/chart.png", facecolor=fig.get_facecolor())
