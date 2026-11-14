---
name: memory-rot-audit
description: >
  Read-only audit of a file-based agent memory (one fact per Markdown note, a MEMORY.md
  index) for notes that are still confident but probably no longer true. Ranks notes by
  rot risk from six signals: scheduling dates the note points at that have passed since
  its last edit, claims about things NOT having happened, absolute language weighted by
  age, filesystem paths it names that no longer exist, dangling [[wikilinks]], and the
  drift between a note's own "modified" stamp and its real mtime. Never edits, moves or
  deletes anything.

  Use when asked to "audit memory", "find stale memories", "what has rotted", "which notes
  are probably wrong now", "memory hygiene", before a consolidation pass, or on a schedule.
  Also use the --public mode when someone wants corpus-level numbers they can share without
  exposing a single note.
---

# memory-rot-audit

The failure mode this hunts is not forgetting. It is the opposite: a note that was true
when written, is still written in the voice of certainty, and nothing has touched it since
the world changed. Recall-based retrieval loves these notes. They are short, assertive and
high-signal, so they win the context budget and the agent acts on them.

Four months of running a 300-note memory on one person's real life produced the heuristics
below. Each one is a pattern that actually bit.

## Run it

```bash
python3 -I scripts/audit.py [MEMORY_DIR] [--index MEMORY.md] [--top 25] [--json out.json] [--public] [--today YYYY-MM-DD]
```

Defaults: `MEMORY_DIR` = `$MEMORY_DIR` or the current directory, index = `MEMORY_DIR/MEMORY.md`.
`--public` prints counts only, no filenames and no note text. `--today` lets you replay the audit
as of an earlier date.

## Signals and why each exists

| signal | what it measures | the incident behind it |
|---|---|---|
| horizon | dates the note points AT (by, due, results ~, re-check) that are now in the past AND later than the note's last edit | notes written as "results expected around <date>" kept predicting events that had already happened; the agent re-reported them as upcoming |
| absence | claims that something did NOT happen: no reply, never arrived, unverified, pending, waiting on | absence rots fastest. A "lost" note outlived the recovery by weeks and kept winning until an explicit retraction line was added. Silence in a mailbox was being read as "no mail" |
| absolute | NEVER / ALWAYS / DEAD / CLOSED / 🔴 markers, weighted 1x under 30 days, 1.5x to 90, 2x after | the louder the note, the more it gets loaded and obeyed, and the less anyone re-reads it |
| deadpath | `~/...` or `/Users/...` paths the note names that no longer exist | notes pointing at scripts, plists and Desktop folders that had been moved or rebuilt |
| dangling | `[[links]]` whose target note does not exist | a planned note that was never written, so the chain of reasoning stops at a stub |
| stamp drift | real mtime minus the note's own `modified:` stamp | scripted edits do not rewrite the frontmatter stamp, so the field that says "last true as of" is itself the stalest line in the file |

Score = (horizon x3 + absence x2 + absolute x0.5) x age weight + dead paths x2 + dangling x1.
Horizon, absence and absolute are each capped so one verbose note cannot dominate.
Stamp drift, flip markers and index reachability are reported for each note but are not part of the score.

## What to do with the output

Review list, not a delete list. For each candidate the next step is one of:
- re-verify from the primary source (the mailbox, the public record, the filesystem) and append a dated line
- add an explicit retraction line that names the superseded claim ("EDIT 10/26: X RETRACTED, now Y")
- leave it, with a dated "still true as of" line so the horizon clock resets honestly

Never let the agent delete or rewrite history on its own. The audit is read-only on purpose.

## Known limits

- Dates without a year are counted only when a scheduling cue precedes them, otherwise "3/6 rejected" reads as March 6.
- A path cut at a space in the real folder name is reported as unverifiable, not dead.
- Absolute-language counting is crude by design. It is a weight, not a verdict.
- Found by hand-verifying the top 20 on 2026-10-26 (3 of 20 flags were the tool's own fault): the path regex can swallow
  trailing junk and flag an existing folder; a path on a remote host looks local; a date used as a modeling input looks
  like an expectation. Hit rate on the judgeable 17 was 7 confirmed wrong, so treat the list as a review queue, not a verdict.

## Imaginal (demo slice, 2026-10-31): synthetic corpus + survival harness + page
    python3 -I fixtures/synthetic/make_corpus.py --seed 1 --verify   # 57 synthetic notes with planted rot and ground truth, checked against audit.py
    python3 -I scripts/imaginal.py survive --seeds 1,2,3 --out runs/rerun.json   # 3 traces x 4 salience conditions per seed, one fresh agent each (Messages API; key from ANTHROPIC_API_KEY or ~/.config/anthropic/api_key). Without --out it overwrites runs/demo.json
    python3 -I scripts/imaginal.py demo --replay runs/demo.json       # renders runs/demo.html from the saved run; no network
    python3 -I scripts/imaginal.py rescore --out runs/rescored.json   # re-scores the saved answers after a scorer change; no model call. Without --out it rewrites runs/demo.json in place
    python3 -I scripts/imaginal.py survive --seeds 1,2,3 --conditions 2h --out runs/rerun_2h.json   # the same just-in-time line as a REFUSED submission (API lane only); saved as runs/framing.json. The 11/1 comparison with the note (5/5 revised vs 0/8) was wrong: conditions 2 and 2d end a run early. See "The finding" in README.md
Synthetic data only. audit.py is imported by the harness, never modified by it. `--backend cli` runs the agents through `claude -p` instead (just-in-time injection = a PreToolUse hook on StructuredOutput); one cell verified 10/31.
`imaginal.py --variant live ...` = the live-deadline trap (fixtures/synthetic/live/, runs/demo_live.*). See README.md for the results and their limits.
