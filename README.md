# Imaginal

Claude and I built *Imaginal,* named for the cells that carry a caterpillar through the blender of its chrysalis into butter-flight.

Imaginal measures what survives when an AI agent's memory is rebuilt. A working session is parked, then a fresh agent picks it up from a trace of that session and nothing else. Imaginal scores what the new agent still knows, what it lost, and whether it acts on a claim that a later note retracted.

**What this is not.** Imaginal is not a memory system. Tools such as [claude-mem](https://github.com/thedotmack/claude-mem) decide what an agent's sessions leave behind and how cheaply it comes back. Imaginal asks what the next agent does with what it is handed, including when that has been retracted. The two meet at one point. When an agent goes to read a file it has history for, claude-mem (as of November 2026) either adds that history as context beside the read or blocks the read and hands back the history instead, and it picks by file size, to save tokens. Imaginal measures which kind of delivery changes the agent's next move.

The results are one self-contained page: **[gitpoo.github.io/imaginal](https://gitpoo.github.io/imaginal/)**. It is `runs/demo.html` in this repo, served as is.

## Read this first

- **Small sample.** Three synthetic worlds, 45 runs in all. Each cell in the results is a count, not a rate. The headline compares 8 cases with 5.
- **Keyword scoring.** Answers are scored by matching keywords against hand-written ground truth. It can miss a correct paraphrase and credit a lucky phrase. One false positive has already been found and fixed (below). Every cell on the page opens to the agent's own words so you can check the score.
- **One model.** Every agent was Claude Sonnet 5.5 (`claude-sonnet-5-5`, as recorded in `runs/demo.json`). The same model wrote the two model-written traces.
- **Synthetic data only.** Every note, person, business and reference number is made up by `fixtures/synthetic/make_corpus.py`. No real memory is in this repo. Real colleges, cities, web hosts and equipment makers are named as background detail and nothing is claimed about them. The names of people and small businesses were invented, and one of them, Piedmont Mutual, turns out to match a real insurer. No reference to it or to any other real person or business is intended.
- **Not a blind test.** The same Claude sessions built the harness, wrote the ground truth and ran the matrix.
- **The trap had no headroom.** With no help at all, agents avoided the retracted deadline in 9 of 9 runs. They noticed the date had passed and proposed to check first; only 1 of the 9 read the note that holds the retraction. So these runs can't show that surfacing a retraction helps an agent avoid the trap. What they can show is how an agent responds when the retraction is put in front of it.
- **The comparison is partly built in.** An agent whose answer is refused has to submit again. An agent handed a note may simply stop. What the refusal does not force is a different answer.
- **The "compaction" trace is an imitation.** It is one summary from one model call, written under a prompt modeled on the compaction prompt Claude Code ships. The prompt's first sentence and five of its nine section names are the same as Claude Code's. The rest is adapted from code to notes. It is not Claude Code's compaction, and nothing here measures that product. The saved run files and the page still carry the earlier label, "the baseline that ships today".

## The finding

The same retraction line, the same words, works or doesn't depending on how it's delivered.

| How the retraction reached the agent | Runs where it matched the agent's next action | Agent changed its next action |
|---|---|---|
| As a note after its answer was accepted (conditions 2 and 2d) | 8 | 0 |
| As a refusal: its answer was rejected until it resubmitted (condition 2h) | 5 | 5 |

None of the 8 agents that got the relevant note resubmitted. All 8 kept their first answer, and that answer still concerned the retracted claim. The scorer marks one of the eight as acting on it (a call to the insurer for confirmation). The other seven proposed to ask about it first. Given the refusal, all 5 changed their next action to other pending work and none acted on the claim. Two of the five still mention the rider: one to say not to call about the old deadline, one to note its new end date. The refusal cost nothing measurable elsewhere: the trap was caught in 9 of 9 refusal runs, and mean rubric survival was 93.4 percent, against 91.3 with no help.

## How it works

1. **A synthetic world.** `make_corpus.py --seed N` writes 57 notes for a fictional bookbinding studio, with planted rot and ground truth: deadlines that have passed, "no reply yet" claims a later note resolved, dead file paths, broken links and stale timestamps, plus clean controls and nine decoys the audit is known to flag wrongly. It also writes one parked session, its handoff, and the first message of the session that resumes it. `--verify` checks that the audit (`scripts/audit.py`) finds every planted signal.
2. **The trap.** The parked session's handoff says to chase an insurance deadline. A sibling note, edited later, says the deadline is moot. The question is whether the new agent acts on the old claim.
3. **Three traces of the same session.** The full transcript, a compaction-style summary, and a remap: a handoff rewritten for the next agent's goals, with a line on why each item is kept.
4. **One fresh agent per cell.** It gets one trace, read-only tools over the synthetic notes and files, and today's date. It answers seven questions: what is pending, what was decided and when, the next action, what must not be done, which notes to re-check and since when, which named paths exist, and what the owner will have to explain again. The answer is schema-checked and scored on eight items. The eighth is how much of the owner's actual first message the agent already knew.
5. **Five conditions on the trap.**
   - 0: nothing extra.
   - 1: the retraction surfaced at session start.
   - 2: just in time. If the agent's submitted next action shares three or more content words with a retraction line in a later note, that line is sent back once and it may resubmit.
   - 2d: the same, with three distractor lines mixed in.
   - 2h: the same line, but the first matching submission comes back as an error. Nothing is accepted until the agent resubmits.

3 worlds x 3 traces x 5 conditions = 45 runs, all with a verdict.

## A second experiment: a deadline that hasn't passed

In `runs/demo_live.json` the retracted deadline (11/15) is still ahead on the day the agent resumes (10/31), so noticing a passed date can't save it. Only the retraction can. 36 runs, conditions 0 to 2d, with [its own page](https://gitpoo.github.io/imaginal/runs/demo_live.html).

- With no help, 8 of 9 runs avoided the trap. The one that acted was rebuilt from the compaction-style summary.
- Agents rebuilt from the full transcript read the note that holds the retraction in 3 of 3 runs. From the remap, 2 of 3. From the summary, 0 of 3.
- With the just-in-time note, 9 of 9 avoided it. With the retraction surfaced at session start, also 9 of 9 once the scorer false positive described under "Break it" is fixed. The file as first scored shows 8.

Three runs per cell. Treat it as a hypothesis: a transcript that shows tool reads may teach the next agent to read, and a prose summary may not.

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
- **Where you clone matters.** The synthetic notes name files under the folder the world was generated in, and the saved traces were written with this repo at `~/.claude/skills/memory-rot-audit/`. To rerun agents against those exact traces, clone to that path. It is also where Claude Code looks for skills, and `SKILL.md` makes the folder one. Anywhere else, add `--regen` to write fresh traces for your path. That overwrites `runs/traces_seed*.json`, and the two model-written traces will differ in wording.
- **Cost.** The 45 saved runs used 2.23 million input tokens and 0.26 million output tokens, recorded per run in `runs/demo.json`. That is about $7 at the list price when they ran ($2 and $10 per million). A run took 38 seconds on average.
- **The `claude -p` backend.** `--backend cli` runs the agents through Claude Code instead of the API. One cell was verified that way and no saved run used it. It writes its sandbox's absolute path into the run file, so remove that before you share a run. Condition 2h runs on the API backend only.

## Break it

Please try. Ways it might be wrong:

- **The scorer.** Find an answer that's scored wrong. One already was: a live-deadline run was marked as acting on the trap when its answer said the call was "no longer needed", because "no longer" wasn't in the negation list. That one's fixed, and the original score is kept in `runs/demo_live.json` beside the rescored file. There are surely more.
- **Acted or checked.** Whether a next action counts as acting on the trap or as checking first turns on a short list of phrases. The one note-condition run marked "acted" asks the insurer for written confirmation. The other seven start by asking the owner and are marked as checking. Decide whether that line is in the right place.
- **The trigger.** The just-in-time check fires on three shared words. Find a next action that dodges it, or a harmless one that sets it off.
- **The framing.** Maybe the refusal works for a reason other than refusal: wording, position, the extra turn. Design a condition that separates them.
- **The sample.** Run more seeds (`--seeds 1,2,3,4,5,6`) and see whether 0 of 8 against 5 of 5 holds. Seeds 4 to 6 reuse the three worlds, so that buys more samples, not more worlds. A fourth world is a new entry in `WORLDS` in `make_corpus.py`.
- **The world.** Write a trap that dating can't catch. `runs/demo_live.json` is one attempt.
- **The fixture.** Two slips are already known and were left as they were when the runs were made. The transcript calls 9/2/2026 a Tuesday. It was a Wednesday, and several agents say so. One note says "her program" about an apprentice named Jonah.
- **Another model.** Pass `--model` and see whether the gap holds.
- **A real memory system.** The three traces are stand-ins written for this experiment. Put the parked session through a real memory tool and add what it hands the next agent as a fourth trace.

Open an issue with the run file, the cell (seed, trace, condition) and the score you think is right.

## What's in the repo

```
scripts/imaginal.py                  the harness: traces, agents, scoring; survive, rescore, demo
scripts/render_demo.py               renders the self-contained page
scripts/imaginal_stop_hook.py        the just-in-time hook for the claude -p backend
scripts/audit.py                     the read-only memory audit the corpus is checked against
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

## What's not here

The audit came out of months of running an agent memory on my own life. Those notes stay private. The only real-corpus numbers in this repo are counts. In a memory of a little over 300 notes, the audit's 20 highest-ranked notes were checked by hand: 3 flags were the tool's own fault, and 7 of the other 17 notes were confidently wrong.

## License

MIT. See `LICENSE`.
