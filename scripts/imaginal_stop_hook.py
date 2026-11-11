#!/usr/bin/env python3
"""Just-in-time salience hook for the claude -p lane of imaginal.py (conditions 2 and 2d).

Registered as a PreToolUse hook on the StructuredOutput tool (the final answer under --json-schema). The tool input IS the
agent's answer, so this is the moment it reaches for a claim: the hook runs the same matcher as the API lane against the
retraction lines in notes edited after the parked session and, on a match, denies the submission ONCE with the dated
retraction line(s) as the reason, so the agent revises and submits again. A marker file in the run's sandbox (the cwd)
makes the second submission pass. Every call is logged to hook_log.jsonl in the sandbox as evidence.
(A Stop hook cannot do this job: in --json-schema mode the structured answer is not in the transcript when Stop fires.)
Synthetic corpus only. Verified live on one cell, 2026-10-31.
"""
import argparse, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import imaginal

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, required=True); ap.add_argument("--cond", default="2"); ap.add_argument("--run-seed", type=int, default=0)
    ap.add_argument("--variant", default="passed")
    a = ap.parse_args(); imaginal.VARIANT = a.variant
    inp = json.load(sys.stdin)
    answer = inp.get("tool_input") or {}
    marker = Path.cwd() / "jit_injected.marker"; log = Path.cwd() / "hook_log.jsonl"
    rec = dict(event=inp.get("hook_event_name"), tool=inp.get("tool_name"), has_answer="next_action" in answer, already_injected=marker.exists(), fired=False)
    if marker.exists() or "next_action" not in answer:
        log.open("a").write(json.dumps(rec) + "\n"); return
    ctx = imaginal.load_seed(a.seed)
    matches = imaginal.jit_matches(ctx, answer, k_distractors=3 if a.cond == "2d" else 0, rng=random.Random(a.run_seed))
    rec.update(matches=[dict(file=m["file"], shared=m["shared"], relevant=m["relevant"]) for m in matches], first_answer=answer)
    if matches:
        txt = imaginal.injection_text(matches); rec.update(fired=True, injection=txt); marker.write_text("1")
        log.open("a").write(json.dumps(rec) + "\n")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": txt}}))
        return
    log.open("a").write(json.dumps(rec) + "\n")

if __name__ == "__main__":
    main()
