# #061 Haiku-or-Opus routing gate (Claude Code CLI)

**Question.** If a cheap Haiku call first labels each task EASY/HARD and routes it to Haiku or Opus, how do cost and pass rate compare with always-Haiku and always-Opus?

**Short answer.** On #017's 10 tasks the gate labelled **all 10 EASY**, so the routed arm was just Haiku plus a gate tax. All arms passed **10/10**. Routed cost **$0.0046/task** vs **$0.0035** always-Haiku (+32%) and **$0.109** always-Opus (−96%), API-equivalent. The gate itself was $0.0008/task, about 22% of a Haiku solve. The rest of the gap is Haiku run-to-run noise. These tasks are too easy to show any benefit from routing: Haiku already solves all of them, so the best a router can do is match always-Haiku, and it costs more because of the gate.

## Setup
- Claude Code 2.1.300 (same build as #017), Pro sign-in, headless. Run: 2026-10-14 ~23:25–23:28 UTC (04:55–04:58 IST).
- **Tasks:** the same 10 SUITE14 fixtures as #017 (N01_median, N02_duration, N03_csv, T02_duplicate, T05_stale, T06_neardup, T07_multihunk, T08_insert, T09_delete, T10_replace_all), from `/workspace/work/tig/_harness/fixtures/SUITE14`. n = 10, 1 run per cell.
- **Gate** (`scripts/classify.py`): `claude -p "<routing prompt + full contents of the task's files>" --output-format json --model haiku --effort low --tools "" --strict-mcp-config --no-session-persistence`, run from an empty temp dir. The prompt asks for exactly `EASY` or `HARD`. EASY → Haiku, HARD → Opus. An unparseable reply would count as EASY (never happened; every reply was exactly `EASY`).
- **Solver runs** (`scripts/harness/run_cc.py`, copied unchanged from `_harness`): same prompt and flags as #017 (`Make \`node test.js\` pass by fixing the code. Do not edit test.js.`, stream-json, fresh copy per run). EASY → `--model haiku --effort medium`, HARD → `--model opus`, matching #017's `haiku_medium` and `opus_default` arms exactly. Pass = `node test.js` exits 0 and test.js is unchanged.
- **Fixed arms are reused from #017's raw results** (`results/017_runs.csv` is a copy of #017's `runs.csv`, filtered to `haiku_medium` and `opus_default`). They're compatible: same CLI build, tasks, prompt, flags and pass check. As a drift check I re-ran always-Opus fresh (`opus_default_rerun`). It came in within 1% of #017 ($1.084 vs $1.093). I did not re-run always-Haiku separately; the routed arm's 10 Haiku runs serve as a fresh Haiku sample.
- **Cost** = Claude Code's `total_cost_usd`. These are **API-equivalent estimates only**: Pro isn't billed per token.

## Exact commands
```bash
source /workspace/tools/setup.sh
F=/workspace/work/tig/_harness/fixtures/SUITE14
python3 scripts/classify.py $F/N01_median $F/N02_duration ...   # -> results/routes.csv, results/classify/*.json
# scripts/jobs.txt built from routes.csv (routed + opus_default_rerun), run 4-way parallel:
cat scripts/jobs.txt | xargs -d '\n' -P 4 -n 1 bash -c 'eval "python3 scripts/harness/run_cc.py $1"' _
python3 scripts/analyze.py   # -> results/summary.csv, results/chart.png
```

## Results (n = 10 tasks)
| Arm | Source | Solved | Gate $ | Solver $ | **Total est. $** | **$/task** | Wall/task |
|---|---|---|---|---|---|---|---|
| always-Haiku (haiku medium) | #017 raw, reused | 10/10 | – | 0.0346 | **0.0346** | **0.0035** | 9.4 s |
| **routed** (Haiku gate → Haiku ×10, Opus ×0) | new | 10/10 | 0.0076 | 0.0380 | **0.0456** | **0.0046** | 13.2 s |
| always-Opus (opus default) | #017 raw, reused | 10/10 | – | 1.0934 | **1.0934** | **0.1093** | 10.2 s |
| always-Opus rerun | new | 10/10 | – | 1.0836 | 1.0836 | 0.1084 | 12.5 s |

Gate details (`results/routes.csv`): 10/10 EASY. About $0.0006–0.0015 per call (N03_csv was the costliest because its data.csv is in the prompt), ~3.1–7.6k cache-write tokens, ~5 output tokens, 2.1–3.0 s.

Chart: `results/chart.png`. Raw data: `results/raw/` (stream-json per solver run), `results/classify/` (gate JSON), `results/runs.csv`, `results/summary.csv`.

## Caveats
- **The task set can't test routing.** Haiku solves all 10 in #017, so no task needs Opus. The router could only lose here, by misrouting to Opus or by paying for the gate. It didn't misroute, but I never saw it say HARD, so I don't know whether it can recognise a hard task at all. A real test needs tasks where Haiku sometimes fails.
- n = 10, 1 run each. The routed arm's Haiku runs cost 10% more than #017's ($0.0380 vs $0.0346). That's ordinary run-to-run variance, not an effect of routing.
- The gate is a full `claude -p` call, so it carries Claude Code's system-prompt overhead (~3k+ cache-write tokens) even with tools disabled. A raw API call with a tiny prompt would be cheaper. At Haiku prices the gate is still ~22% of a whole Haiku solve.
- The gate adds ~2.5 s of serial latency per task.
- Costs are API-equivalent estimates from the CLI, not billed amounts.
