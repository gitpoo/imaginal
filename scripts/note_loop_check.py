#!/usr/bin/env python3
"""note_loop_check.py - did a note-condition agent get a turn in which to answer again? No model, no network.

Conditions 2 and 2d send the retraction back as a note that ends "Re-check the affected items and call submit_answer
again with your final answer." This script checks what the harness (scripts/imaginal.py, as published) does next.

Part 1 puts a scripted agent in the model's place. Under every condition it does the same three things:
    turn 1  submits an answer whose next action goes after the retracted deadline (this sets off the notice)
    turn 2  opens the note the notice names
    turn 3  submits a different answer
and the script prints how many turns the harness asked for and which answer it kept.

Part 2 reads saved run files and lists how each note-condition run that was sent a notice ended: on a new
submission, on the agent ending its turn, or cut off after a tool call that was not a submission.

  python3 -I scripts/note_loop_check.py                       part 1, then part 2 on runs/demo.json
  python3 -I scripts/note_loop_check.py runs/demo_live.json   part 2 on another file (any number of files)

Standard library only. It imports imaginal.py and changes nothing in it. On a fresh clone part 1 first builds the
synthetic world for seed 1 (fixtures/synthetic/seed1), as `make_corpus.py --seed 1` does. It writes nothing else.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imaginal as im  # noqa: E402


def scripted_agent(first, second, note, log):
    def api_post(path, body, *a, **k):
        if path != "messages": raise im.ApiError("offline")     # token counting falls back to an estimate
        log.append(path); n = len(log)
        if n == 1: use = dict(type="tool_use", id="t1", name="submit_answer", input=first)
        elif n == 2: use = dict(type="tool_use", id="t2", name="read_note", input=dict(file=note))
        elif n == 3: use = dict(type="tool_use", id="t3", name="submit_answer", input=second)
        else: return dict(model="scripted", stop_reason="end_turn", usage={}, content=[dict(type="text", text="done")])
        return dict(model="scripted", stop_reason="tool_use", usage={}, content=[use])
    return api_post


def part1():
    ctx = im.load_seed(1); trap = ctx["gt"]["rubric"]["trap"]
    first = dict(pending=[], decided=[], must_not=[], unverified=[], paths=[], re_explain=[], notes_read=[], confidence=0.5,
                 next_action="Call the insurer to confirm the appraisal PDF is on file and the cutter rider is in force; the appraisal deadline has passed.")
    second = dict(first, next_action="Ask the owner whether the van registration was renewed.", notes_read=[trap["sibling"]])
    print("Part 1. A scripted agent: submit, open the note the notice names, submit a different answer.\n")
    real = im.api_post
    try:
        for cond in ("2", "2d", "2h"):
            log = []; im.api_post = scripted_agent(first, second, trap["sibling"], log)
            res = im.run_agent_api(ctx, "fidelity", "(trace)", cond, "scripted")
            kept = (res["answer"] or {}).get("next_action")
            which = "first" if kept == first["next_action"] else "second" if kept == second["next_action"] else "neither"
            print(f"  condition {cond:2}: notice sent: {bool(res['evidence']['injections'])} | turns the harness asked for: {len(log)} of the agent's 3 | answer kept: the {which} one")
    finally:
        im.api_post = real
    print("\n  Under 2 and 2d the harness stops after turn 2, so the second answer is never asked for.")


def name(x): return Path(str(x)).name.replace(".md", "").strip().lower()


def part2(files):
    print("\nPart 2. How each saved note-condition run that was sent a notice ended.")
    for f in files:
        data = json.loads(Path(f).read_text()); tally = {}; lines = []
        for seed, sd in data["seeds"].items():
            trap = sd["trap"]; note = name(trap["sibling"])
            for r in sd["runs"]:
                if r["condition"] not in ("2", "2d"): continue
                ev = r.get("evidence") or {}; inj = (ev.get("injections") or [None])[0]
                if not inj: continue
                top = [m for m in inj["matches"] if m.get("relevant")]
                kind = "the trap's retraction line" if top and top[0]["line"].strip() == trap["retraction_line"].strip() else "unrelated lines only"
                had = note in [name(x) for x in (inj["first_answer"].get("notes_read") or [])]
                if kind.startswith("the trap") and had: kind += " (agent had already opened that note)"
                calls = ev.get("tool_calls") or []
                if ev.get("resubmitted_after_injection"): end = "submitted again"
                elif (ev.get("stop_reasons") or [""])[-1] == "end_turn": end = "ended its turn"
                else: end = "CUT OFF after a tool call" + (f" ({calls[-1]['tool']} {calls[-1]['input'].get('file', '')})".replace(" )", ")") if calls else "")
                tally[(kind, end.split(" (")[0])] = tally.get((kind, end.split(" (")[0]), 0) + 1
                lines.append(f"    seed {seed} {r['arm']:10} {r['condition']:2}  {kind}: {end}")
        print(f"\n  {f}")
        for l in lines: print(l)
        for (kind, end), n in sorted(tally.items()): print(f"  {n:3}  {kind}: {end}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args: part1()
    part2(args or ["runs/demo.json" if Path("runs/demo.json").exists() else str(im.RUNS / "demo.json")])
