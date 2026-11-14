#!/usr/bin/env python3
"""framing_control.py - two more salience conditions: 2r (a second answer is required) and 2c (the note, with the run not ended early).

On the results page a retraction changed the agent's next action when it arrived as a refusal (condition 2h) and did
not when it arrived as a note after an accepted answer (conditions 2 and 2d). A refusal differs from that note in two
ways at once: the submission is not accepted, so the agent has to answer again, and the message is an error worded
as a hook denial. Condition 2r keeps the first and drops the second:

  2r  the same one line, the same words, as an ordinary tool result (no error flag, no "hook error" wording), plus
      one sentence: "Your answer was not recorded. Call submit_answer again to record it." Nothing is recorded as
      the answer until the agent submits again.

If 2r changes next actions the way 2h does, what matters is making the agent answer again. If agents resubmit the
same answer, the refusal framing is doing the work.

Condition 2c exists because of what reading the 2r runs turned up. Under conditions 2 and 2d the harness, as published,
ends a run at the end of the agent's first turn after the notice unless that turn is itself a new submission. The
notice says "Re-check the affected items and call submit_answer again". An agent that re-checks first, by opening the
note the notice names, is cut off there and its first answer is kept. It never gets a turn in which to answer again.
Under 2h and 2r the run goes on until the agent resubmits. So the saved note runs cannot be compared with them.

  2c  what condition 2 sends, byte for byte (the notice as an ordinary tool result, nothing added), with the run left
      to go on until the agent submits again or ends its turn. If it ends its turn without submitting again, its
      first answer stands, which is condition 2's own rule.

It imports imaginal.py and changes nothing in it. The run loop is the harness's own hard-denial loop; only the
message the model sees is rewritten on its way out, and the saved rows are labelled 2r or 2c.

  framing_control.py --arms fidelity,compaction,remap,claudemem --seeds 1,2,3 --out runs/NEW.json [--dry]
  framing_control.py --arms fidelity --seeds 4,5,6,7,8,9 --out runs/NEW2.json
  framing_control.py --condition 2c --arms fidelity,compaction,remap,claudemem --seeds 1,2,3 --out runs/NEW3.json
  framing_control.py --rescore runs/NEW.json [--out FILE]        (re-score the saved answers; no model call)

Passed-deadline worlds only, which is where 2h was run. The arm `claudemem` reads
runs/claudemem_traces/passed/seedN.txt. A seed with no saved built-in traces can run the fidelity arm only (the
transcript itself); nothing is generated. The saved traces name files under the folder they were first written in
(see "Where you clone matters" in the README); here that prefix is rewritten to this machine's fixture folder so the
agent can check those paths, as it could in the saved runs.
Nothing is run above --max-usd (default 5), and an existing --out file is never written over. Standard library only.
"""
import argparse, copy, json, sys, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imaginal as im  # noqa: E402

KEY = "2r"          # set from --condition
SENTENCE = "Your answer was not recorded. Call submit_answer again to record it."
CONDS = {
    "2r": dict(sentence=SENTENCE, framing="required", label="just-in-time, second answer required",
               desc="the same one line as an ordinary tool result (no error flag, no hook wording) plus: " + SENTENCE + " Nothing is recorded until the agent submits again.",
               differs_from_2h="no error flag and no 'PreToolUse:submit_answer hook error: ' prefix; the sentence is added",
               differs_from_2="the first answer is not recorded and the sentence says so; the agent has to submit again"),
    "2c": dict(sentence="", framing="soft, run not ended early", label="just-in-time, run not ended early",
               desc="what condition 2 sends, byte for byte (the notice as an ordinary tool result, nothing added); the run goes on until the agent submits again or ends its turn. "
                    "If it ends its turn without submitting again, its first answer stands.",
               differs_from_2h="no error flag, no 'PreToolUse:submit_answer hook error: ' prefix, and the first answer stands if the agent ends its turn without submitting again",
               differs_from_2="nothing in what the agent is sent. The run is no longer ended when the agent's first turn after the notice is a tool call other than submit_answer"),
}
SAVED_PREFIX = "~/.claude/skills/memory-rot-audit/fixtures/synthetic/"
PRICE = {"claude-sonnet-5-5": (2.00, 10.00)}    # $ per million tokens (input, output), list price on 2026-11-03
CM_ARM = dict(key="claudemem", label="claude-mem 15.18.0 (SessionStart injection)",
              desc="what claude-mem injects at the start of a new session, after its hooks saw the parked session")
CM_DIR = im.RUNS / "claudemem_traces" / "passed"
STATS = dict(rewritten_messages=0); LOCK = threading.Lock()


def shown(notice):
    """The notice as the agent is sent it under the condition being run."""
    extra = CONDS[KEY]["sentence"]
    return notice + ("\n" + extra if extra else "")


def rewrite(body):
    """The harness builds a hard denial: an error result holding the notice. Send it as an ordinary result: the same notice, plus SENTENCE under 2r, nothing more under 2c."""
    out = copy.deepcopy(body); n = 0
    for m in out.get("messages", []):
        if m.get("role") != "user" or not isinstance(m.get("content"), list): continue
        for b in m["content"]:
            if b.get("type") == "tool_result" and b.get("is_error") and isinstance(b.get("content"), str) and b["content"].startswith("MEMORY TRUST (just-in-time)"):
                b.pop("is_error"); b["content"] = shown(b["content"]); n += 1
    if n:
        with LOCK: STATS["rewritten_messages"] += 1
    return out


def install(arms, local_prefix):
    """Patch the imported harness in memory: the 2r condition, the outgoing message, and trace loading that never generates."""
    im.HARD_DENIAL_PREFIX = ""          # the notice then starts the result, and rewrite() can find it
    post = im.api_post
    im.api_post = lambda path, body, *a, **k: post(path, rewrite(body) if path == "messages" else body, *a, **k)
    run = im.run_agent_api

    def run_agent_api(ctx, arm, trace_text, cond, model, brief=None, run_seed=0):
        res = run(ctx, arm, trace_text, "2h" if cond == KEY else cond, model, brief=brief, run_seed=run_seed)
        if cond == KEY:
            for inj in res["evidence"].get("injections", []):
                inj["framing"] = CONDS[KEY]["framing"]; inj["shown_to_agent"] = shown(inj["text"])
            if res.get("error") and "hard denial" in res["error"]:
                if KEY == "2c":     # condition 2's rule: the first answer stands unless the agent chooses to submit again
                    res["answer"] = res["evidence"]["injections"][0]["first_answer"]; res["error"] = None
                    res["evidence"]["ended_turn_without_resubmitting"] = True
                else: res["error"] = "second answer required; the agent ended without resubmitting"
        return res
    im.run_agent_api = run_agent_api
    im.CONDITIONS.append(dict(key=KEY, label=CONDS[KEY]["label"], desc=CONDS[KEY]["desc"]))
    if "claudemem" in arms: im.ARMS.append(CM_ARM)
    saved = im.build_traces; extra = {}

    def build_traces(ctx, model, regen=False):
        if (im.RUNS / f"traces_{im.vtag()}seed{ctx['seed']}.json").exists():
            tr = copy.deepcopy(saved(ctx, model, regen=False))          # saved traces and brief; no model call
            for k in ("fidelity", "compaction", "remap"):               # their file paths point at the folder they were written in
                if tr[k].get("text"): tr[k]["text"] = tr[k]["text"].replace(SAVED_PREFIX, local_prefix)
        else:                                                           # seeds 4 and up: the transcript itself and the brief, built here
            session = im.render_transcript(ctx["events"]); brief = im.trust_brief(ctx, session)
            ftok, fhow = im.count_tokens(session, model); btok, bhow = im.count_tokens(brief, model)
            none = dict(text=None, generated_by=None, error="not generated: no saved trace for this seed")
            tr = dict(seed=ctx["seed"], generated=im.now12(), model=model, fidelity=dict(text=session, generated_by="verbatim", tokens=ftok, tokens_method=fhow),
                      compaction=none, remap=dict(none), brief=dict(text=brief, tokens=btok, tokens_method=bhow))
        f = CM_DIR / f"seed{ctx['seed']}.txt"
        if "claudemem" in arms:
            text = f.read_text(); tok, how = im.count_tokens(text, model)
            tr["claudemem"] = dict(text=text, generated_by=CM_ARM["label"], tokens=tok, tokens_method=how, source=f"claudemem_traces/passed/seed{ctx['seed']}.txt")
            extra[str(ctx["seed"])] = tr["claudemem"]
        return tr
    im.build_traces = build_traces
    return extra


def usd(model, tin, tout):
    pi, po = PRICE.get(model, (None, None))
    return None if pi is None else (tin * pi + tout * po) / 1e6


def rescore(src, out):
    data = json.loads(src.read_text()); im.VARIANT = data.get("variant", "passed"); im.ARMS[:] = data["arms"]; n = 0
    for c in data["conditions"]:
        if c["key"] not in [x["key"] for x in im.CONDITIONS]: im.CONDITIONS.append(c)
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
    out.write_text(json.dumps(data, indent=1)); print(f"rescored {n} runs -> {out}")


def main():
    if "--rescore" in sys.argv:
        ap = argparse.ArgumentParser(); ap.add_argument("--rescore", required=True); ap.add_argument("--out", default=None); a = ap.parse_args()
        src = Path(a.rescore); out = Path(a.out) if a.out else src.with_name(src.stem + "_rescored.json")
        if out.exists(): sys.exit(f"{out} exists; pick a new --out")
        return rescore(src, out)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default="fidelity,compaction,remap"); ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--model", default=im.DEFAULT_MODEL); ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out", required=True); ap.add_argument("--max-usd", type=float, default=5.0); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--condition", default="2r", choices=sorted(CONDS))
    a = ap.parse_args()
    global KEY
    KEY = a.condition
    arms = a.arms.split(","); seeds = [int(s) for s in a.seeds.split(",")]; out = Path(a.out)
    if out.exists(): sys.exit(f"{out} exists; pick a new --out (this script never writes over a run file)")
    im.VARIANT = "passed"
    for s in seeds:
        has = (im.RUNS / f"traces_seed{s}.json").exists()
        if not has and any(x in ("compaction", "remap") for x in arms): sys.exit(f"seed {s} has no saved compaction or remap trace; run it with --arms fidelity")
        if "claudemem" in arms and not (CM_DIR / f"seed{s}.txt").exists(): sys.exit(f"missing {CM_DIR / f'seed{s}.txt'}")
    try: local_prefix = "~/" + str(im.FIX.relative_to(Path.home())) + "/"
    except ValueError: local_prefix = str(im.FIX) + "/"          # a clone outside the home folder
    extra = install(arms, local_prefix)

    # ---- estimate from the saved refusal runs (same loop, same number of turns)
    ref = [r for sd in json.loads((im.RUNS / "demo.json").read_text())["seeds"].values() for r in sd["runs"] if r["condition"] == "2h"]
    tin = sum(r["usage"]["input_tokens"] for r in ref) / len(ref); tout = sum(r["usage"]["output_tokens"] for r in ref) / len(ref)
    n = len(seeds) * len(arms); est = n * usd(a.model, tin, tout)
    print(f"{n} runs: condition {KEY}, arms {arms}, seeds {seeds}, model {a.model}; trace paths use {local_prefix}")
    print(f"estimated cost: ${est:.2f}  (the 9 saved refusal runs averaged {tin:,.0f} in / {tout:,.0f} out tokens; list price)")
    if a.dry:
        for s in seeds:
            tr = im.build_traces(im.load_seed(s), a.model)
            print(f"  seed {s}: " + ", ".join(f"{k} {tr[k].get('tokens')} tokens" for k in arms) + f" | saved prefix left in a trace: {any(SAVED_PREFIX in (tr[k].get('text') or '') for k in arms)}")
        return
    if est > a.max_usd: sys.exit(f"estimate ${est:.2f} is above --max-usd {a.max_usd}; nothing was run")

    data = im.survive(seeds, arms, [KEY], "api", a.model, a.parallel, out)
    for s, sd in data["seeds"].items():
        ctx = im.load_seed(int(s)); keep = {"brief": sd["traces"]["brief"]}
        tr = im.build_traces(ctx, a.model)
        for k in arms: keep[k] = extra[s] if k == "claudemem" else tr[k]
        sd["traces"] = keep; sd["transcript_text"] = im.render_transcript(ctx["events"])
    rows = [r for sd in data["seeds"].values() for r in sd["runs"]]
    ti = sum((r.get("usage") or {}).get("input_tokens", 0) for r in rows); to = sum((r.get("usage") or {}).get("output_tokens", 0) for r in rows)
    data["control"] = dict(condition=KEY, sentence=CONDS[KEY]["sentence"],
                           differs_from_2h=CONDS[KEY]["differs_from_2h"],
                           differs_from_2=CONDS[KEY]["differs_from_2"],
                           same_as_both="the MEMORY TRUST notice, word for word, with the one matching retraction line",
                           trace_paths=f"'{SAVED_PREFIX}' in the saved traces rewritten to '{local_prefix}'",
                           requests_sent_with_the_rewritten_message=STATS["rewritten_messages"],
                           usage=dict(input_tokens=ti, output_tokens=to, usd_list_price=round(usd(a.model, ti, to), 4), estimate_usd=round(est, 4)))
    out.write_text(json.dumps(data, indent=1))
    print(f"\nactual: {ti:,} input + {to:,} output tokens = ${usd(a.model, ti, to):.2f} at list price (estimate was ${est:.2f}); requests carrying the rewritten message: {STATS['rewritten_messages']}; saved {out}")


if __name__ == "__main__":
    main()
