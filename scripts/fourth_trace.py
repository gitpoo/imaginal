#!/usr/bin/env python3
"""fourth_trace.py - run the survive conditions on a trace that came from outside the harness.

The three built-in traces (full transcript, compaction summary, remap) are stand-ins written for the experiment.
This script adds one more arm whose text you supply, one file per seed: whatever a real memory tool handed the next
agent after it was put through the same parked session. It then runs the same fresh-agent conditions on that arm,
with the same system prompt, tools, rubric, scorer and model. It imports imaginal.py and changes nothing in it.

  fourth_trace.py --name claudemem --label "claude-mem 15.18.0" --trace-dir runs/claudemem_traces/passed \\
                  --seeds 1,2,3 --conditions 0,1,2,2d,2h --out runs/NEW.json
  fourth_trace.py --variant live ...            (the live-deadline worlds; the flag works anywhere on the line)
  fourth_trace.py ... --dry                     (count tokens, print the cost estimate, run nothing)
  fourth_trace.py --rescore runs/NEW.json [--out FILE]   (re-score the saved answers; no model call)

--trace-dir holds seed1.txt, seed2.txt, ... and, optionally, provenance.json (how the texts were made; copied into
the run file). The condition-1 brief is the saved one the built-in arms use; for a seed with no saved traces (4 and
up) it is built here the same way, with no model call. The run file has the same shape as
runs/demo.json with a single arm. Re-score it with --rescore here: `imaginal.py rescore` builds its totals for the
three built-in arms only.

Nothing is run if the estimate is above --max-usd (default 5), and an existing --out file is never written over.
The API key is read the way imaginal.py reads it. Standard library only.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imaginal as im  # noqa: E402

PRICE = {"claude-sonnet-5-5": (2.00, 10.00)}   # $ per million tokens (input, output), list price on 2026-11-03


def usd(model, tin, tout):
    pi, po = PRICE.get(model, (None, None))
    return None if pi is None else (tin * pi + tout * po) / 1e6


def reference_usage(variant, conds):
    """Mean input/output tokens per run, per condition, in the saved matrix of the same variant (all three arms pooled)."""
    src = im.RUNS / ("demo_live_rescored.json" if variant == "live" else "demo.json")
    if not src.exists(): return {}, None
    rows = [r for sd in json.loads(src.read_text())["seeds"].values() for r in sd["runs"]]
    out = {}
    for c in conds:
        rs = [r for r in rows if r["condition"] == c and r.get("usage")] or [r for r in rows if r.get("usage")]
        if rs: out[c] = (sum(r["usage"].get("input_tokens", 0) for r in rs) / len(rs), sum(r["usage"].get("output_tokens", 0) for r in rs) / len(rs),
                         sum(r.get("trace_tokens") or 0 for r in rs) / len(rs), sum((r.get("evidence") or {}).get("turns", 0) for r in rs) / len(rs))
    return out, src.name


def rescore(src, out):
    """Recompute every score and the totals from the saved answers, for the arm(s) the run file names. No model call."""
    data = json.loads(src.read_text()); im.VARIANT = data.get("variant", "passed"); im.ARMS[:] = data["arms"]; n = 0
    for sk, sd in data["seeds"].items():
        gt = im.load_seed(int(sk))["gt"]
        for r in sd["runs"]:
            if r.get("answer") is None: continue
            problem = im.validate_answer(r["answer"])
            if problem: r.update(verdict="no_verdict", error=problem); continue
            r.update(verdict="ok", error=None, **im.score(r["answer"], gt)); n += 1
            rent = (r.get("trace_tokens") or 0) + (r.get("tokens_injected") or 0)
            r["tokens_at_start"] = rent; r["survival_per_ktoken"] = round(r["survival_pct"] / (rent / 1000.0), 2) if rent else None
    data["aggregate"] = im.aggregate(data["seeds"]); data["rescored"] = im.now12()
    out.write_text(json.dumps(data, indent=1)); print(f"rescored {n} runs -> {out}"); im.summarize(data)


def main():
    if "--rescore" in sys.argv:
        ap = argparse.ArgumentParser(); ap.add_argument("--rescore", required=True); ap.add_argument("--out", default=None); a = ap.parse_args()
        src = Path(a.rescore); out = Path(a.out) if a.out else src.with_name(src.stem + "_rescored.json")
        if out.exists(): sys.exit(f"{out} exists; pick a new --out")
        return rescore(src, out)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="arm key, letters and digits (shown to the agent as TRACE (<name>))")
    ap.add_argument("--label", required=True); ap.add_argument("--desc", default="supplied from outside the harness")
    ap.add_argument("--trace-dir", required=True); ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--conditions", default="0,1,2,2d,2h"); ap.add_argument("--variant", choices=["passed", "live"], default="passed")
    ap.add_argument("--model", default=im.DEFAULT_MODEL); ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out", required=True); ap.add_argument("--max-usd", type=float, default=5.0); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not a.name.isalnum() or a.name in [x["key"] for x in im.ARMS] or a.name == "brief": sys.exit("--name must be letters and digits and not the name of a built-in trace")
    seeds = [int(s) for s in a.seeds.split(",")]; conds = a.conditions.split(","); tdir = Path(a.trace_dir); out = Path(a.out)
    bad = [c for c in conds if c not in [x["key"] for x in im.CONDITIONS]]
    if bad: sys.exit(f"unknown condition(s): {bad}")
    if out.exists(): sys.exit(f"{out} exists; pick a new --out (this script never writes over a run file)")
    im.VARIANT = a.variant
    for s in seeds:
        if not (tdir / f"seed{s}.txt").exists(): sys.exit(f"missing {tdir / f'seed{s}.txt'}")
    prov = json.loads((tdir / "provenance.json").read_text()) if (tdir / "provenance.json").exists() else {}

    arm = dict(key=a.name, label=a.label, desc=a.desc)
    im.ARMS[:] = [arm]                                  # the run file and its aggregates carry this arm only
    saved = im.build_traces; extra = {}

    def build_traces(ctx, model, regen=False):
        if (im.RUNS / f"traces_{im.vtag()}seed{ctx['seed']}.json").exists():
            tr = dict(saved(ctx, model, regen=False))   # the saved built-in traces and the condition-1 brief; no model call
        else:                                           # a seed with no saved traces (4 and up): session text and brief built here, no model call, nothing written
            session = im.render_transcript(ctx["events"]); brief = im.trust_brief(ctx, session); btok, bhow = im.count_tokens(brief, model)
            none = dict(text=None, generated_by=None, error="not generated: this script runs the supplied trace only")
            tr = dict(seed=ctx["seed"], generated=im.now12(), model=model, fidelity=dict(text=session, generated_by="verbatim"),
                      compaction=none, remap=dict(none), brief=dict(text=brief, tokens=btok, tokens_method=bhow))
        text = (tdir / f"seed{ctx['seed']}.txt").read_text()
        tok, how = im.count_tokens(text, model)
        tr[a.name] = dict(text=text, generated_by=a.label, tokens=tok, tokens_method=how, source=f"{tdir.name}/seed{ctx['seed']}.txt")
        extra[str(ctx["seed"])] = tr[a.name]
        return tr
    im.build_traces = build_traces

    # ---- estimate first, from the saved matrix of the same variant
    ref, ref_name = reference_usage(a.variant, conds); toks = {}
    for s in seeds: toks[s] = build_traces(im.load_seed(s), a.model)[a.name]["tokens"]
    est = 0.0; lines = []
    for c in conds:
        if c not in ref: continue
        tin, tout, ttrace, turns = ref[c]
        for s in seeds:
            e = usd(a.model, max(0.0, tin + (toks[s] - ttrace) * turns), tout)   # the trace is re-sent on every turn
            if e is None: sys.exit(f"no price on file for {a.model}; add it to PRICE")
            est += e
        lines.append(f"  condition {c:2}: saved runs average {tin:,.0f} in / {tout:,.0f} out tokens over {turns:.1f} turns with a {ttrace:,.0f}-token trace")
    n = len(seeds) * len(conds)
    print(f"{n} runs: arm {a.name!r} ({a.label}), variant {a.variant}, seeds {seeds}, conditions {conds}, model {a.model}")
    print(f"trace tokens per seed: {toks}"); print("\n".join(lines))
    print(f"estimated cost: ${est:.2f}  (list price, scaled from {ref_name}; a rough guide, agents vary in how many notes they read)")
    if a.dry: return
    if est > a.max_usd: sys.exit(f"estimate ${est:.2f} is above --max-usd {a.max_usd}; nothing was run")

    data = im.survive(seeds, [a.name], conds, "api", a.model, a.parallel, out)
    for s, sd in data["seeds"].items():   # keep what this arm used: its own trace, the condition-1 brief, and the session as this machine's fixture has it
        sd["traces"] = {"brief": sd["traces"]["brief"], a.name: extra[s]}
        sd["transcript_text"] = im.render_transcript(im.load_seed(int(s))["events"])
    rows = [r for sd in data["seeds"].values() for r in sd["runs"]]
    tin = sum((r.get("usage") or {}).get("input_tokens", 0) for r in rows); tout = sum((r.get("usage") or {}).get("output_tokens", 0) for r in rows)
    data["fourth_trace"] = dict(name=a.name, label=a.label, desc=a.desc, trace_dir=tdir.name, provenance=prov,
                                note="One arm only. Each seed's `traces` holds this arm's text and the condition-1 brief; `transcript_text` is the parked session rendered from this machine's fixture.",
                                usage=dict(input_tokens=tin, output_tokens=tout, usd_list_price=round(usd(a.model, tin, tout), 4), estimate_usd=round(est, 4)))
    out.write_text(json.dumps(data, indent=1))
    print(f"\nactual: {tin:,} input + {tout:,} output tokens = ${usd(a.model, tin, tout):.2f} at list price (estimate was ${est:.2f}); saved {out}")


if __name__ == "__main__":
    main()
