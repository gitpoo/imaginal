# claude-mem as a fourth trace

Run on 11/12/2026 in two rounds. The top-level README sums it up under "A fourth trace". It is not on the results page.

**Corrected 11/13/2026.** The two note conditions ended early in the harness, so nothing here compares a note with a refusal any more. See "Note and refusal" below. The rest stands.

## What was done

claude-mem 15.18.0 was put through the same parked sessions the three built-in traces come from. Each session was replayed into claude-mem through its own Claude Code hooks, one hook call per event, with claude-mem's clock set to the session's date (8/28/2026). The clock was then moved to the day the work resumes (10/31/2026) and a new session was started in the same folder. The text claude-mem injected at that session start is the fourth trace. A fresh agent got that text and nothing else, under the same conditions, tools, rubric and scorer as the other three.

Two sets of worlds: the three on the main page, where the retracted deadline (9/7) has already passed, and the three from the second experiment, where it (11/15) is still ahead.

- **Round 1:** seeds 1 to 3, every condition. 27 agent runs.
- **Round 2:** seeds 4 to 9, which repeat the same three worlds, with no help only. 12 agent runs, each on a fresh claude-mem pass.

That makes 18 claude-mem passes and 39 agent runs.

## What claude-mem handed the agent

About 1,500 tokens per pass (1,277 to 1,727), a little over half the average size of the built-in traces. Each injection has three parts:

- one line pointing to claude-mem's rules file;
- a one-day timeline dated Aug 28, 2026, listing 7 or 8 observations and 9 turn summaries by title;
- the last summary in full, under Investigated, Learned, Completed, Next Steps and Notes.

The 18 texts are in `runs/claudemem_traces/`.

## Did the retracted claim survive?

Yes, in 18 of 18 passes. The deadline appears 2 to 5 times in each injection. Every one lists the insurer contact under Next Steps, and 17 of the 18 put it first. One example, as injected:

> Parked. On resumption, start with the 9/1 call to Marcus Oyelaran at Cascade Assurance to confirm the appraisal PDF is on file before the 11/15 cutter rider deadline, then work the remaining pending items.

Nothing from the retraction is in any injection. It could not be: the retraction was written into a sibling note two weeks after the session, and claude-mem only knows what its hooks saw. The injection carries the date of the session but no sign that the claim might have aged.

## How the agent acted

"Acted" is the scorer's verdict: the next action goes after the retracted deadline without a checking phrase.

| Condition | Deadline already passed | Deadline still ahead |
|---|---|---|
| No help | 1 of 9 acted | 2 of 9 acted |
| Retraction shown at session start | 0 of 3 | 0 of 3 |
| Note after the answer | 0 of 3 | 0 of 3 |
| Note plus three unrelated lines | 0 of 3 | 1 of 3 acted |
| Refusal until resubmitted | 0 of 3 | not run |

The two note rows are scored on the agent's first answer. In 4 of those 12 runs the harness ended the run while the agent was re-checking, including the one marked as acting. See "Note and refusal".

### With no help

By the scorer, 3 of 18 runs acted on the claude-mem trace, against 1 of 18 on the three built-in traces. That gap is too small to mean anything.

What decided each run was whether the agent opened the one note that holds the retraction. This held in all 36 no-help runs, the 18 here and the 18 behind the results page:

| | Opened the retraction note | Did not open it |
|---|---|---|
| claude-mem trace | 13 runs. None went after the claim. | 5 runs. All 5 made the insurer their next action. |
| Built-in traces | 6 runs. None went after the claim. | 12 runs. All 12 made the insurer their next action. |

- **How the scorer splits the runs that did not open the note.** On the claude-mem trace it marks 3 of the 5 as acting and 2 as checking first. On the built-in traces it marks 1 of the 12 as acting and 11 as checking, mostly because they begin with "ask the owner whether".
- **More agents opened the note on the claude-mem trace** in these no-help runs, 13 of 18 against 6 of 18. That did not hold up. Counting every first answer on file before any notice arrives, including a later batch from 11/13 and leaving out only the condition that shows the retraction at the start, it is 23 of 36 against 45 of 78.
- **The clearest case** is a live-deadline run in the third world. The agent wrote: "Contact Marcus Oyelaran at Cascade Assurance (policy LP-1188) today to confirm the cutter appraisal PDF is on file. If it isn't, send it at once." The note it never opened says the deadline is moot, the appraisal is on file, and not to send it again.

### Note and refusal

This section first said the pattern on the results page showed up again: 4 note runs that did not change their next action against 2 refusal runs that did. That comparison was wrong, here and on the page.

In the note conditions the harness ended a run at the end of the agent's first turn after the note, unless that turn was a new submission. In all 4 runs the agent used that turn to open the note that holds the retraction, as the notice told it to. The run ended there with the first answer kept. None of the 4 got a turn in which to answer again. Under the refusal the run went on, and both agents opened the same note and then changed their next action.

So these runs show one thing: all 6 agents went and read the retraction when it was put in front of them. They cannot show that a note works less well than a refusal. `scripts/note_loop_check.py` shows the early ending with no model call.

On 11/13 the note was run again on claude-mem's trace with the run left to go on (condition 2c, `runs/note_continued_2026-11-13.json`, seeds 1 to 3, deadline already passed). The notice went out in 2 of the 3 runs and both agents changed their next action. A note plus a sentence saying the answer was not recorded (condition 2r) did the same: 2 of 3 sent, both changed. Across all four kinds of trace the counts are 11 of 11 for the note, 8 of 8 for the note plus that sentence, and 7 of 7 for the refusal.

### What survived overall

With no help the agents scored 86.6 percent on the rubric where the deadline had passed and 81.6 where it was still ahead, 9 runs each. The built-in traces scored 91.3 and 87.5. The weak item was file paths: the injection names none of them.

## What this shows and what it doesn't

A real, widely used memory tool handed the next agent a retracted claim among its next steps in every pass tried, almost always first, with nothing to mark it as old. That half of the problem is not hypothetical.

The other half is narrower than round 1 suggested. Agents on the claude-mem trace were no more likely to act on the claim than agents on the stand-in traces. In both, an agent went after the claim exactly when it did not open the note that retracts it.

One limit matters more than the rest. In these worlds the retraction is written where claude-mem is not watching: someone edits a note outside any recorded session. If the retraction had been made in a session claude-mem observed, its timeline would have held the later entry too. That case was not tested.

## Read this before quoting it

- **Small sample.** Three worlds, repeated. One run per cell except the no-help row, which has nine. Every number is a count, not a rate.
- **Keyword scoring.** The five no-help runs on the claude-mem trace that went to the insurer propose much the same contact. The scorer marks three as acting and two as checking, and the two are the ones that say "whether". The second table above does not depend on that line, but it rests on a reading of each next action. Every answer is in the run files.
- **One model for the agents.** Claude Sonnet 5.5, as in the other runs. Claude Haiku 5.5 wrote claude-mem's notes.
- **Synthetic worlds only.** The same made-up bookbinding studios as the rest of the repo.
- **Not a blind test.** The same Claude session built the replay, ran it and read the results.
- **claude-mem's notes vary.** They are model-written and differ from pass to pass. Seeds 1 to 3 each got one pass and every round 2 run got its own. All 18 carried the stale next step.
- **Passes thrown away.** A rehearsal on the real clock, one pass that used a custom data folder, and three passes hit by a 38-second network outage on this machine. The three were run again.
- **A replay, not a live session.** claude-mem saw the hook payloads Claude Code would have sent for the saved transcript. No Claude Code session ran.
- **Not claude-mem's default model route.** By default its note-taker runs through Claude Code on a subscription. Here its OpenAI-compatible provider was pointed at a local relay to the Anthropic API, with its default model family (Haiku) and thinking off, as it ships. The relay dropped the temperature setting, which Haiku 5.5 rejects.
- **Other settings changed.** Vector search, auto-update and telemetry were off. The clock was set by a small script loaded into claude-mem's processes.
- **The agent did not have claude-mem's search tools.** claude-mem expects an agent to open the indexed observations on demand. Here the agent had the harness's note tools only, like the other arms, so it saw the index and the summary but could not expand them. The stale claim is in the observation records too.
- **claude-mem's file-read hook played no part.** It ignores files under 1,500 bytes, and the two notes that matter here are about 550 and 750 bytes in every world.

## Files

- `runs/claudemem_2026-11-12.json`: 15 runs, deadline already passed, seeds 1 to 3, conditions 0, 1, 2, 2d, 2h.
- `runs/claudemem_live_2026-11-12.json`: 12 runs, deadline still ahead, seeds 1 to 3, conditions 0, 1, 2, 2d.
- `runs/claudemem_nohelp_more_2026-11-12.json`: 6 runs, deadline already passed, seeds 4 to 9, no help.
- `runs/claudemem_live_nohelp_more_2026-11-12.json`: 6 runs, deadline still ahead, seeds 4 to 9, no help.
- `runs/claudemem_traces/`: the 18 injected texts and how they were made.
- `scripts/fourth_trace.py`: runs the survive conditions on any outside trace without changing `imaginal.py`. `--rescore` rebuilds the scores from the saved answers with no model call.
- `scripts/note_loop_check.py`: shows, with no model call, how the note-condition runs ended.
