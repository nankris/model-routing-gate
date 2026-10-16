#!/usr/bin/env python3
"""Routing gate: one cheap headless Haiku call per task labels it EASY or HARD.
Writes results/classify/<task>.json (raw CLI JSON) and appends results/routes.csv."""
import csv, json, os, subprocess, sys, tempfile, time
EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = """You are a routing gate. A coding agent must make `node test.js` pass by fixing the code (not test.js).
Decide if a small cheap model can do it reliably (EASY) or it needs a strong model (HARD).
Reply with exactly one word: EASY or HARD.

{files}"""
def files_blob(task, cap=6000):
    out = []
    for f in sorted(os.listdir(task)):
        p = os.path.join(task, f)
        if os.path.isfile(p):
            out.append(f"--- {f} ---\n" + open(p, errors="replace").read()[:cap])
    return "\n".join(out)
def main(tasks):
    os.makedirs(f"{EXP}/results/classify", exist_ok=True)
    path = f"{EXP}/results/routes.csv"
    new = not os.path.exists(path)
    w = csv.writer(open(path, "a"))
    if new: w.writerow(["task", "label", "route_model", "gate_cost_usd", "gate_input", "gate_cache_create", "gate_cache_read", "gate_output", "gate_wall_s", "raw_answer"])
    for task in tasks:
        name = os.path.basename(task.rstrip("/"))
        cmd = ["claude", "-p", PROMPT.format(files=files_blob(task)), "--output-format", "json",
               "--model", "haiku", "--effort", "low", "--tools", "", "--strict-mcp-config", "--no-session-persistence"]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=tempfile.mkdtemp(prefix="gate_"), stdin=subprocess.DEVNULL, timeout=180)
        wall = time.time() - t0
        open(f"{EXP}/results/classify/{name}.json", "w").write(p.stdout)
        r = json.loads(p.stdout); u = r.get("usage", {})
        ans = str(r.get("result", "")).strip()
        label = "HARD" if "HARD" in ans.upper() else "EASY"   # anything unparseable -> EASY (cheap default)
        w.writerow([name, label, "opus" if label == "HARD" else "haiku", r.get("total_cost_usd"), u.get("input_tokens"),
                    u.get("cache_creation_input_tokens"), u.get("cache_read_input_tokens"), u.get("output_tokens"), round(wall, 1), ans[:80]])
        print(name, label, r.get("total_cost_usd"), flush=True)
if __name__ == "__main__":
    main(sys.argv[1:])
