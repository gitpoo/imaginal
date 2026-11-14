# runs/

Saved results. Everything here is synthetic. The top-level README says what the numbers can and can't show.

| file | what it is |
|---|---|
| `demo.json` | The main matrix: 3 seeds x 3 traces x 5 conditions = 45 runs, all with a verdict, every agent served by `claude-sonnet-5-5`. Conditions 0, 1, 2 and 2d ran on 2026-10-31. The nine condition-2h rows ran on 2026-11-01 and were merged in from `framing.json`. |
| `demo.html` | The page rendered from `demo.json`. `imaginal.py demo --replay runs/demo.json` rebuilds it byte for byte. |
| `framing.json` | The nine condition-2h (refusal) runs on their own, as first saved, before the merge. |
| `demo_pre_2h_2026-11-01.json` | `demo.json` as it stood before the merge: 36 runs. |
| `traces_seed1.json`, `traces_seed2.json`, `traces_seed3.json` | The three traces per seed that every agent in `demo.json` was rebuilt from, plus the condition-1 brief. `survive` reuses them unless `--regen` is given. |
| `demo_truncated_traces_2026-10-31.json` | The first matrix, kept because it was wrong. Both model-written traces were cut off at a 3,000-token output cap, because thinking counts against the cap. That made the remap look about four times cheaper per token than the full transcript. With complete traces it is about 1.3 times. The page's "ends mid-sentence" warning is what caught it. 36 runs plus 22 superseded rows. Don't quote its numbers. |
| `demo_live.json` | The second experiment, the live-deadline variant: the retracted deadline is still ahead on the day the agent resumes. 36 runs, conditions 0, 1, 2 and 2d, scored as first run. |
| `demo_live_rescored.json` | The same 36 runs re-scored after one scorer false positive was fixed ("no longer" added to the negation list). One row changes: seed 3, compaction, condition 1, from acted to caught. |
| `demo_live.html` | The page rendered from `demo_live.json`. |
| `traces_live_seed1.json`, `traces_live_seed2.json`, `traces_live_seed3.json` | The traces for the live variant. |
| `note_continued_2026-11-13.json`, `note_continued_more_2026-11-13.json` | Condition 2c, the note with the run left to go on: 12 runs on four traces, then 6 more on the full transcript. Made with `scripts/framing_control.py`. |
| `framing_control_2026-11-13.json`, `framing_control_more_2026-11-13.json` | Condition 2r, a note plus one sentence saying the answer was not recorded, on the same 18 cells. |
| `claudemem_2026-11-12.json` | claude-mem's trace, deadline already passed, seeds 1 to 3, conditions 0, 1, 2, 2d, 2h. 15 runs. Made with `scripts/fourth_trace.py`. |
| `claudemem_live_2026-11-12.json` | The same with the deadline still ahead, conditions 0, 1, 2, 2d. 12 runs. |
| `claudemem_nohelp_more_2026-11-12.json`, `claudemem_live_nohelp_more_2026-11-12.json` | No help, seeds 4 to 9, 6 runs each, every run on its own claude-mem pass. |
| `claudemem_traces/` | The 18 texts claude-mem injected, with `provenance.json`. |
| `claudemem_2026-11-12_writeup.md` | Longer notes on the claude-mem run. |

In every file here, conditions 2 and 2d ended early. See "The finding" in the top-level README.

Paths inside the files made before 11/12 begin `~/.claude/skills/memory-rot-audit/`. That is where the repo sat when those runs were made. The later files were made with the repo at `~/imaginal-public`. See "Rerun it" in the top-level README.
