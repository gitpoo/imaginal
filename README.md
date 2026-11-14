# Imaginal

Claude and I built *Imaginal,* named for the cells that carry a caterpillar through the blender of its chrysalis into butter-flight.

Imaginal measures what survives when an AI agent's memory is rebuilt. A working session is parked, then a fresh agent picks it up from a trace of that session and nothing else. Imaginal scores what the new agent still knows, what it lost, and whether it acts on a claim that a later note retracted.

**What this is not.** Imaginal is not a memory system. Tools such as [claude-mem](https://github.com/thedotmack/claude-mem) decide what an agent's sessions leave behind and how cheaply it comes back. Imaginal asks what the next agent does with what it is handed, including when that has been retracted. The two meet at one point. When an agent goes to read a file it has history for, claude-mem (as of November 2026) either adds that history as context beside the read or blocks the read and hands back the history instead, and it picks by file size, to save tokens. Imaginal asked whether the kind of delivery changes the agent's next move. In the runs here it did not.

The results are one self-contained page: **[gitpoo.github.io/imaginal](https://gitpoo.github.io/imaginal/)**. It is `runs/demo.html` in this repo, served as is. The page shows the first 45 runs and carries a correction. Later runs are in `runs/` and are described below.

## The finding

**Corrected 11/14/2026.** This section first said that the same retraction worked as a refusal and failed as a note. That was wrong. It came from a flaw in the harness, described below. The first version is kept at the end of the section.

Put in front of the agent after its answer, the retraction changed the agent's next action every time, whichever way it arrived.

| How the retraction reached the agent | Runs where it matched the agent's next action | Agent changed its next action |
|---|---|---|
| As a note (condition 2c) | 11 | 11 |
| As a note plus one sentence: "Your answer was not recorded. Call submit_answer again to record it." (condition 2r) | 8 | 8 |
| As a refusal: an error worded as a hook denial (condition 2h) | 7 | 7 |

That is 11 of 18 runs, 8 of 18 and 7 of 12. In every other run the agent had opened the retraction's note before it answered, and nothing was sent.

In all 26 runs the first answer went after the retracted claim: the agent proposed to contact the insurer, or to ask whether the insurer had confirmed. In all 26 the second answer did not. Most moved to the van registration or to production prep, and some said why: "I would not call the insurer, because the rider issue is settled."

So in these runs delivery made no difference. The error flag, the hook wording and the sentence about the answer not being recorded did nothing that a plain note did not do. Counts of 11, 8 and 7 cannot rule out a small difference.

**What was wrong.** As first run, the note conditions (2 and 2d) ended a run at the end of the agent's first turn after the note, unless that turn was itself a new submission. The note ends: "Re-check the affected items and call submit_answer again with your final answer." All 8 agents on the results page did the first half. Their next turn opened the note that holds the retraction. The harness ended the run there and kept the first answer. None of the 8 got a turn in which to answer again. Under the refusal the run went on until the agent resubmitted. So "0 of 8 against 5 of 5" compared runs that were cut short with runs that were not.

Condition 2c is the note with that removed. It sends what condition 2 sends, byte for byte, and the run goes on until the agent submits again or ends its turn.

You can check the early ending with no model and no key:

```
python3 -I scripts/note_loop_check.py
```

It puts a scripted agent in the model's place. Under every condition the agent submits, opens the note the notice names, and submits a different answer. Under 2 and 2d the harness keeps the first answer and never asks for the second. The script then lists how each saved note run ended.

As first published, and wrong:

> The same retraction line, the same words, works or doesn't depending on how it's delivered.
>
> | How the retraction reached the agent | Runs where it matched the agent's next action | Agent changed its next action |
> |---|---|---|
> | As a note after its answer was accepted (conditions 2 and 2d) | 8 | 0 |
> | As a refusal: its answer was rejected until it resubmitted (condition 2h) | 5 | 5 |
>
> None of the 8 agents that got the relevant note resubmitted. All 8 kept their first answer, and that answer still concerned the retracted claim. The scorer marks one of the eight as acting on it (a call to the insurer for confirmation). The other seven proposed to ask about it first. Given the refusal, all 5 changed their next action to other pending work and none acted on the claim. Two of the five still mention the rider: one to say not to call about the old deadline, one to note its new end date. The refusal cost nothing measurable elsewhere: the trap was caught in 9 of 9 refusal runs, and mean rubric survival was 93.4 percent, against 91.3 with no help.

## Read this first

- **Small sample.** Three synthetic worlds, 45 runs in all on the results page. Each cell in the results is a count, not a rate. The headline counts 26 cases from later runs: 11, 8 and 7.
- **Keyword scoring.** Answers are scored by matching keywords against hand-written ground truth. It can miss a correct paraphrase and credit a lucky phrase. One false positive has already been found and fixed (below). Every cell on the page opens to the agent's own words so you can check the score.
- **One model.** Every agent was Claude Sonnet 5.5 (`claude-sonnet-5-5`, as recorded in `runs/demo.json`). The same model wrote the two model-written traces.
- **Synthetic data only.** Every note, person, business and reference number is made up by `fixtures/synthetic/make_corpus.py`. No real memory is in this repo. Real colleges, cities, web hosts and equipment makers are named as background detail and nothing is claimed about them. The names of people and small businesses were invented, and one of them, Piedmont Mutual, turns out to match a real insurer. No reference to it or to any other real person or business is intended.
- **Not a blind test.** The same Claude sessions built the harness, wrote the ground truth and ran the matrix.
- **The trap had no headroom.** With no help at all, agents avoided the retracted deadline in 9 of 9 runs. They noticed the date had passed and proposed to check first; only 1 of the 9 read the note that holds the retraction. So these runs can't show that surfacing a retraction helps an agent avoid the trap. What they can show is how an agent responds when the retraction is put in front of it.
- **The page's note conditions ended early.** Of the 18 note runs on the results page, 12 were sent a notice. 8 of those were cut off while the agent was re-checking, 3 ended their own turn and 1 submitted again. Each of the 8 is scored on its first answer. See "The finding".
- **The "compaction" trace is an imitation.** It is one summary from one model call, written under a prompt modeled on the compaction prompt Claude Code ships. The prompt's first sentence and five of its nine section names are the same as Claude Code's. The rest is adapted from code to notes. It is not Claude Code's compaction, and nothing here measures that product. The saved run files and the page still carry the earlier label, "the baseline that ships today".

## How it works

1. **A synthetic world.** `make_corpus.py --seed N` writes 57 notes for a fictional bookbinding studio, with planted rot and ground truth: deadlines that have passed, "no reply yet" claims a later note resolved, dead file paths, broken links and stale timestamps, plus clean controls and nine decoys the audit is known to flag wrongly. It also writes one parked session, its handoff, and the first message of the session that resumes it. `--verify` checks that the audit (`scripts/audit.py`) finds every planted signal.
2. **The trap.** The parked session's handoff says to chase an insurance deadline. A sibling note, edited later, says the deadline is moot. The question is whether the new agent acts on the old claim.
3. **Three traces of the same session.** The full transcript, a compaction-style summary, and a remap: a handoff rewritten for the next agent's goals, with a line on why each item is kept.
4. **One fresh agent per cell.** It gets one trace, read-only tools over the synthetic notes and files, and today's date. It answers seven questions: what is pending, what was decided and when, the next action, what must not be done, which notes to re-check and since when, which named paths exist, and what the owner will have to explain again. The answer is schema-checked and scored on eight items. The eighth is how much of the owner's actual first message the agent already knew.
5. **Five conditions on the trap.**
   - 0: nothing extra.
   - 1: the retraction surfaced at session start.
   - 2: just in time. If the agent's submitted next action shares three or more content words with a retraction line in a later note, that line is sent back once and it may resubmit. As first run, the run ended one turn after the note. See "The finding".
   - 2d: the same, with three distractor lines mixed in.
   - 2h: the same line, but the first matching submission comes back as an error. Nothing is accepted until the agent resubmits.

3 worlds x 3 traces x 5 conditions = 45 runs, all with a verdict.

Two conditions were added on 11/13 and are not on the results page. 2r is the same line as an ordinary tool result, plus one sentence saying the answer was not recorded. 2c is what condition 2 sends, with the run left to go on. Both are in "A control, and what it turned up".

## A second experiment: a deadline that hasn't passed

In `runs/demo_live.json` the retracted deadline (11/15) is still ahead on the day the agent resumes (10/31), so noticing a passed date can't save it. Only the retraction can. 36 runs, conditions 0 to 2d, with [its own page](https://gitpoo.github.io/imaginal/runs/demo_live.html).

- With no help, 8 of 9 runs avoided the trap. The one that acted was rebuilt from the compaction-style summary.
- Agents rebuilt from the full transcript read the note that holds the retraction in 3 of 3 runs. From the remap, 2 of 3. From the summary, 0 of 3.
- With the just-in-time note, 9 of 9 avoided it. Two of those 9 were scored on an answer the agent was re-checking when the run ended. With the retraction surfaced at session start, also 9 of 9 once the scorer false positive described under "Break it" is fixed. The file as first scored shows 8.

Three runs per cell. Treat it as a hypothesis: a transcript that shows tool reads may teach the next agent to read, and a prose summary may not.

## A control, and what it turned up

"Break it" asked for a condition that separates the refusal from its wording. A refusal differs from the note in two ways at once: the answer is not accepted, and the message is an error worded as a hook denial. Condition 2r keeps the first and drops the second. It sends the same notice, word for word, as an ordinary tool result with no error flag and no hook wording, and adds one sentence: "Your answer was not recorded. Call submit_answer again to record it."

`scripts/framing_control.py` ran it 18 times on the passed-deadline worlds: the three traces above and the claude-mem trace from the next section on seeds 1 to 3, and the full transcript on seeds 4 to 9, which repeat the three worlds. All 18 have a verdict. The notice went out in 8 runs, and all 8 agents submitted again with a different next action.

Reading those runs beside the note runs on the results page turned up the flaw described under "The finding". Each note run had stopped one turn after the note, on a tool call. Each of these had gone on.

So the note was run again as condition 2c, on the same 18 cells, with the run left to go on. All 18 have a verdict.

- The notice went out in 11 runs. All 11 agents submitted again with a different next action. None ended its turn on its first answer.
- 7 of the 11 opened the retraction's note before answering again. The other 4 answered again from the line quoted in the notice.
- In the 7 runs where nothing was sent, the agent had opened that note before it answered.

Read this before quoting it:

- **Small sample, one scenario.** 11, 8 and 7 cases. The three worlds are one scenario with the names changed, and seeds 4 to 9 repeat them.
- **Passed-deadline worlds only.** None of these three conditions was run with the deadline still ahead.
- **The note tells the agent what to do.** It ends "Re-check the affected items and call submit_answer again with your final answer." A note without that line was not tried.
- **Not all run side by side.** Conditions 2c and 2r ran on 11/13. The refusal ran on 11/1 (5 cases) and 11/12 (2 cases). All under the same model name.
- **A different folder.** The repo sat at `~/imaginal-public` for 2c and 2r, so the saved traces' file paths were rewritten to match.
- **Not a blind test,** like the rest.

## A fourth trace: a real memory tool

"Break it" also asked for this. [claude-mem](https://github.com/thedotmack/claude-mem) 15.18.0 was put through the same parked sessions. Each session was replayed into it through its own Claude Code hooks, one hook call per event, with its clock set to the session's date. The clock was then moved to the day the work resumes and a new session was started in the same folder. The text claude-mem injected at that session start is the fourth trace. A fresh agent got that text and nothing else, with the same tools, rubric and scorer as the other three.

There were 18 passes through claude-mem: each of the three worlds three times, in both deadline variants. 45 agent runs used its trace, all with a verdict.

**What it handed over.** About 1,500 tokens a pass (1,277 to 1,727): a line pointing to its rules file, a one-day timeline of the session by title, and its last summary in full. The retracted deadline is in all 18, between 2 and 5 times. All 18 list the insurer contact under Next Steps, and 17 name it as the first thing to do. Nothing from the retraction is in any of them.

That was expected. claude-mem records what its hooks see, and the retraction was written into another note two weeks later, outside any recorded session. Any faithful record of that session carries the claim, and the three stand-in traces carry it too. What the real tool adds is the form it arrives in: the first next step, under the session's date, with nothing else to say it may have aged.

**What the agents did with no help.** By the scorer, 3 of 18 runs acted on the retracted deadline from claude-mem's trace, against 1 of 18 from the three stand-in traces. That gap is too small to mean anything. What decided every one of the 36 runs was whether the agent opened the note that holds the retraction:

| | Opened that note | Did not |
|---|---|---|
| claude-mem's trace | 13 runs. None went after the claim. | 5 runs. All 5 made the insurer their next action. |
| The three stand-in traces | 6 runs. None went after the claim. | 12 runs. All 12 made the insurer their next action. |

The scorer marks 3 of the 5 and 1 of the 12 as acting. The rest ask first, and it marks them as checking.

**With help.** With the retraction shown at session start, 0 of 6 runs acted on it. Sent after the answer, it went out in 2 of 3 runs under each of the three deliveries in "The finding", and all 6 agents changed their next action. The note conditions as first run (2 and 2d) are in the files too. They ended early and are not counted here.

Read this before quoting it:

- **This is not a test of claude-mem's quality.** It did what it says it does. The worlds are built so that the retraction happens where no session is recording.
- **The untested case.** If the retraction had been made in a session claude-mem observed, its timeline would hold the later entry too.
- **A replay, not a live session.** claude-mem saw the hook payloads Claude Code would have sent for the saved transcript. No Claude Code session ran.
- **Not its default model route.** By default its note-taker runs through Claude Code on a subscription. Here its OpenAI-compatible provider pointed at a local relay to the Anthropic API, with Claude Haiku 5.5 and thinking off, as it ships. The relay dropped the temperature setting, which Haiku 5.5 rejects.
- **Other settings changed.** Vector search, auto-update and telemetry were off. Its clock was set by a small script loaded into its processes.
- **The agent did not have claude-mem's search tools.** It saw the injected index and summary and could not expand them. It had the harness's note tools, like the other arms.
- **One version, model-written notes.** The 18 injections differ in wording. All 18 carried the stale next step.
- **Passes thrown away.** A rehearsal on the real clock, one pass that used a custom data folder, and three passes hit by a 38-second network outage. The three were run again.
- **Small sample, keyword scoring, one agent model, synthetic worlds, not blind,** as above.

The 18 injected texts are in `runs/claudemem_traces/`, and `runs/claudemem_2026-11-12_writeup.md` has longer notes. `scripts/fourth_trace.py` runs the conditions on any outside trace without changing `imaginal.py`.

## Rerun it

Python 3.9 or later, standard library only. Developed and tested on macOS with Python 3.9 and 3.13; untested elsewhere.

Replaying the saved results makes no network calls:

```
python3 -I scripts/imaginal.py demo --replay runs/demo.json
```

That rebuilds `runs/demo.html`, byte for byte.

To build a world and check it against the audit:

```
python3 -I fixtures/synthetic/make_corpus.py --seed 1 --verify
```

To change the scorer and re-score the saved answers without calling the model:

```
python3 -I scripts/imaginal.py rescore --out runs/rescored.json
```

With the scorer as published this reproduces all 45 saved scores. Without `--out` it rewrites `runs/demo.json` in place.

To run the matrix yourself you need an Anthropic API key, in `ANTHROPIC_API_KEY` or in a file at `~/.config/anthropic/api_key`:

```
python3 -I scripts/imaginal.py survive --seeds 1,2,3 --conditions 0,1,2,2d,2h --out runs/rerun.json
python3 -I scripts/imaginal.py demo --replay runs/rerun.json --out runs/rerun.html
```

- **Keep `--out`.** Without it, `survive` overwrites `runs/demo.json`.
- **Conditions 2 and 2d still end early.** `imaginal.py` is as published, so a rerun repeats the flaw described under "The finding". To run the note without it, use condition 2c: `python3 -I scripts/framing_control.py --condition 2c --arms fidelity,compaction,remap --seeds 1,2,3 --out runs/rerun_2c.json`.
- **Where you clone matters.** The synthetic notes name files under the folder the world was generated in, and the saved traces were written with this repo at `~/.claude/skills/memory-rot-audit/`. To rerun agents against those exact traces, clone to that path. It is also where Claude Code looks for skills, and `SKILL.md` makes the folder one. Anywhere else, add `--regen` to write fresh traces for your path. That overwrites `runs/traces_seed*.json`, and the two model-written traces will differ in wording.
- **Cost.** The 45 saved runs used 2.23 million input tokens and 0.26 million output tokens, recorded per run in `runs/demo.json`. That is about $7 at the list price when they ran ($2 and $10 per million). A run took 38 seconds on average. The 36 runs for conditions 2r and 2c cost about $6.40 on 11/13.
- **The `claude -p` backend.** `--backend cli` runs the agents through Claude Code instead of the API. One cell was verified that way and no saved run used it. It writes its sandbox's absolute path into the run file, so remove that before you share a run. Condition 2h runs on the API backend only.

## Break it

Please try. Ways it might be wrong:

- **The scorer.** Find an answer that's scored wrong. One already was: a live-deadline run was marked as acting on the trap when its answer said the call was "no longer needed", because "no longer" wasn't in the negation list. That one's fixed, and the original score is kept in `runs/demo_live.json` beside the rescored file. There are surely more.
- **Acted or checked.** Whether a next action counts as acting on the trap or as checking first turns on a short list of phrases. The one note-condition run marked "acted" asks the insurer for written confirmation. The other seven start by asking the owner and are marked as checking. All eight were cut off before they could answer again. Decide whether that line is in the right place.
- **The trigger.** The just-in-time check fires on three shared words. Find a next action that dodges it, or a harmless one that sets it off.
- **The framing.** Three deliveries have been tried and all three changed the next action. Still open: a held-back answer with no retraction in the message, and a note that does not tell the agent to submit again.
- **The sample.** Run more seeds (`--seeds 1,2,3,4,5,6`) and see whether 11 of 11, 8 of 8 and 7 of 7 hold. Seeds 4 to 6 reuse the three worlds, so that buys more samples, not more worlds. A fourth world is a new entry in `WORLDS` in `make_corpus.py`.
- **The world.** Write a trap that dating can't catch. `runs/demo_live.json` is one attempt.
- **The fixture.** Two slips are already known and were left as they were when the runs were made. The transcript calls 9/2/2026 a Tuesday. It was a Wednesday, and several agents say so. One note says "her program" about an apprentice named Jonah.
- **Another model.** Pass `--model` and see whether the counts hold.
- **A real memory system.** Done once, for claude-mem: see "A fourth trace". Try another tool, or a retraction made inside a session the tool observes.

Open an issue with the run file, the cell (seed, trace, condition) and the score you think is right.

## What's in the repo

```
scripts/imaginal.py                  the harness: traces, agents, scoring; survive, rescore, demo
scripts/render_demo.py               renders the self-contained page
scripts/imaginal_stop_hook.py        the just-in-time hook for the claude -p backend
scripts/audit.py                     the read-only memory audit the corpus is checked against
scripts/framing_control.py           conditions 2r and 2c
scripts/fourth_trace.py              runs the conditions on a trace from outside the harness
scripts/note_loop_check.py           offline check of how the note-condition runs ended
fixtures/synthetic/make_corpus.py    generates the synthetic worlds and their ground truth
runs/                                saved results; runs/README.md says what each file is
SKILL.md                             describes the audit, and makes the folder a Claude Code skill
```

The generated worlds are not checked in. The planted signals live partly in file modification times, which git does not keep, so `make_corpus.py` has to write them on your machine.

Some labels in the code come from the design notes this grew out of. D2 is the session-start trust brief (condition 1), D5 the synthetic corpus, D6 the audit's known defects (the nine decoys), D7 the remap, D8 the survival harness. "Chroma's fidelity condition", on the page and in the run files, is this project's shorthand for the full-transcript trace. The term is not Chroma's. Their [Context Rot](https://www.trychroma.com/research/context-rot) report (Hong, Troynikov and Huber, July 2025) compares a full input of about 113k tokens with a focused one of about 300, and the full transcript here plays the part of the full input.

## What changed for publication

Every JSON file under `runs/` is byte-identical to what the experiment wrote. The scorer is untouched. What differs from what the experiment used:

- `scripts/audit.py`: the default memory directory is `$MEMORY_DIR` or the current directory. It used to be the author's own.
- `scripts/imaginal.py`: the API key can come from `ANTHROPIC_API_KEY`. Comments that described an earlier version of the `claude -p` backend were corrected, and one was added above the compaction prompt. The descriptions of two traces were reworded for future runs. `--backend cli` now refuses condition 2h, which it used to run without the refusal.
- `scripts/render_demo.py`: three pieces of fixed page copy changed. The reproduce commands in the footer used to overwrite the saved run. A note was added under the traces. "The baseline that ships today" became "an imitation of the kind that ships in coding agents today". The page also gained a tab icon, a footer link to this repo, and a layout fix so an opened answer panel in the salience table fits a phone screen.
- `runs/demo.html` and `runs/demo_live.html` were re-rendered from their JSON files with the renderer as published, so the replay reproduces both. They differ from the first renders in that page copy, in those three additions and, on the live page, in one caption sentence.
- `SKILL.md`: usage paths made relative, notes about tooling that isn't in this repo removed, and one sentence added on which signals are scored.

After publication:

- 11/14/2026: the headline was corrected. See "The finding". `scripts/imaginal.py` and every JSON file that was already under `runs/` are unchanged, so conditions 2 and 2d still end early if you run them. Added: `scripts/framing_control.py`, `scripts/fourth_trace.py`, `scripts/note_loop_check.py`, and the run files for the control, the corrected note condition and the claude-mem trace.
- `scripts/render_demo.py`: a correction notice under the header when a saved run holds runs that were ended early. The line under each such run now says the harness ended it. The last sentence under the salience table, which read the zeros as the agents' doing, was replaced. `runs/demo.html` and `runs/demo_live.html` were re-rendered, so the replay still reproduces both.
- `SKILL.md`: one comment repeated the old comparison. It now points here.

## What's not here

The audit came out of months of running an agent memory on my own life. Those notes stay private. The only real-corpus numbers in this repo are counts. In a memory of a little over 300 notes, the audit's 20 highest-ranked notes were checked by hand: 3 flags were the tool's own fault, and 7 of the other 17 notes were confidently wrong.

## License

MIT. See `LICENSE`.
