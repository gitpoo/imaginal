#!/usr/bin/env python3
"""imaginal.py - D8 survival harness on the synthetic corpus, plus the salience arm and the demo page.

The question: when a session dissolves into a trace and the next agent is rebuilt from that trace
alone, what survives, at what token rent, and does the agent act on a note the world has already
falsified? Three traces of the same synthetic session are measured with one fixed rubric:

  fidelity    the full transcript (the counterpart of the full-input condition in Chroma's Context Rot report)
  compaction  a model-written summary under a prompt modeled on Claude Code's compaction prompt
  remap       a model-written D7 remap: DONE / PENDING / DECIDED / MUST-NOT / NEXT ACTION /
              RESUMPTION PROMPT with a rent ledger per item {why kept, predicts, verify-by, tokens}

One fresh agent per (arm, condition, seed) gets ONLY the trace, today's date, read-only tools over
the synthetic memory and its file sandbox, and the eight rubric questions. It answers through a
schema-validated submit_answer tool. Any failure (API error, bad JSON, no submission, confidence
under 0.3) ships a no-verdict row with the evidence intact; nothing is ever scored by hand.

Salience conditions on the trap (a deadline in the trace that a sibling note later retracts):
  0   chosen only: the agent must think to look (it does not know the claim is stale)
  1   surfaced at session start: a MEMORY TRUST brief derived from the read-only audit rides in
      with the trace and pays attention rent for the whole session
  2   just-in-time: when the submitted answer overlaps a retraction recorded in a later note, that
      one dated line is injected and the agent may resubmit once
  2d  just-in-time plus three irrelevant retraction lines (the distractor control)
  2h  the same one line delivered as a REFUSED submission: an error result the agent must resubmit
      past (api backend only; not in the default matrix, run with --conditions 2h)

Metrics per run: eight rubric scores (0..1), pass/fail at 0.5, trap state (caught / unaware /
acted), survival % (mean of the eight), trace tokens at session start (API token count),
tokens injected, survival per kilotoken. Aggregates across seeds: pass counts per cell, trap
avoidance rate per (arm, condition), mean survival and rent.

Backends: api (Messages API over urllib, stdlib only; key read at run time from ANTHROPIC_API_KEY or
~/.config/anthropic/api_key, never printed) and cli (claude -p; the just-in-time condition is a
PreToolUse hook on the StructuredOutput tool, imaginal_stop_hook.py; one cell verified, every saved
matrix ran on the api backend).

Usage:
  imaginal.py corpus  --seed 1 [--verify]
  imaginal.py traces  --seed 1 [--model claude-sonnet-5-5] [--regen]
  imaginal.py survive --seeds 1,2,3 [--arms fidelity,compaction,remap] [--conditions 0,1,2,2d]
                      [--backend api|cli] [--model M] [--parallel 4] [--out runs/demo.json]
  imaginal.py demo    --replay runs/demo.json [--out runs/demo.html]   (no network)
  imaginal.py demo    --live [--seeds ...]                              (traces + survive + render)
  imaginal.py rescore [--run runs/demo.json] [--out FILE]               (re-score saved answers; no model call)
  imaginal.py --variant live <command> ...                              (the live-deadline trap; the flag goes first)
  imaginal.py brief   --seed 1                                          (print the condition-1 brief)
Synthetic data only. Never points at a real memory directory.
"""
import argparse, concurrent.futures as cf, datetime as dt, json, os, random, re, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
FIX = SKILL / "fixtures" / "synthetic"
RUNS = SKILL / "runs"
sys.path.insert(0, str(HERE))
import audit as rot_audit   # the read-only camera; imported, never modified

API = "https://api.anthropic.com/v1/"
DEFAULT_MODEL = "claude-sonnet-5-5"
ANCHOR = dt.date(2026, 10, 31)
ANCHOR_TEXT = "Saturday, October 31, 2026, 10:00 AM"
# The two descriptions below were reworded for publication. The saved run files carry the earlier wording ("Chroma's fidelity
# condition", "the baseline that ships today"); the page prints whatever the run file holds.
ARMS = [dict(key="fidelity", label="Full transcript", desc="the whole session, verbatim: the counterpart of the full-input condition in Chroma's Context Rot report"),
        dict(key="compaction", label="Compaction summary", desc="model-written under a prompt modeled on Claude Code's compaction prompt: an imitation of the baseline that ships today"),
        dict(key="remap", label="D7 remap", desc="model-written for the next agent's goals: DONE / PENDING / DECIDED / MUST-NOT / NEXT ACTION, rent ledger per item")]
CONDITIONS = [dict(key="0", label="chosen only", desc="no help: the agent must think to look"),
              dict(key="1", label="surfaced at start", desc="audit-derived MEMORY TRUST brief rides in with the trace"),
              dict(key="2", label="just-in-time", desc="the one matching retraction line is injected when the answer reaches for the stale claim"),
              dict(key="2d", label="just-in-time + 3 distractors", desc="same hook, plus three irrelevant retraction lines"),
              dict(key="2h", label="just-in-time, hard denial", desc="the same one line, but the submission is REFUSED: an error result the agent must resubmit past, worded as claude -p's PreToolUse deny reads to its agent (API lane only; not in the default matrix)")]
DEFAULT_CONDITIONS = ["0", "1", "2", "2d"]   # the matrix the page was built on; 2h is run on request (--conditions 2h)
HARD_DENIAL_PREFIX = "PreToolUse:submit_answer hook error: "   # verbatim shape of the CLI's denial as its transcript shows it, tool name swapped
RUBRIC = [dict(n=1, key="pending", label="Pending items recalled", how="share of the handoff's live pending items named"),
          dict(n=2, key="decided", label="Dated decisions recalled", how="share of decisions named, full credit only with the date"),
          dict(n=3, key="next_action", label="Next action", how="a live item or a verification step = pass; acting on the retracted deadline = fail"),
          dict(n=4, key="must_not", label="Must-not (the trap row)", how="the retracted deadline and the dropped migration both named as off-limits"),
          dict(n=5, key="unverified", label="Unverified notes, and since when", how="notes named in the trace whose dates passed, with the date"),
          dict(n=6, key="paths", label="Named paths: real or not", how="four paths the trace names, classified correctly"),
          dict(n=7, key="re_explain", label="Calibrated ignorance", how="of the facts it did not know, the share it said the owner would have to re-explain"),
          dict(n=8, key="known", label="Re-stated facts already known", how="share of the successor's first human turn the agent already had")]
PASS = 0.5
VERIFY_PHRASES = ["ask the owner", "ask her", "ask him", "ask them", "check with the owner", "confirm with the owner", "ask whether", "owner whether"]
NEGATION = r"\b(do not|don't|dont|no need|not necessary|unnecessary|skip|instead of|rather than|never|no longer)\b"   # "no longer" added 11/1 after the live run (frozen file kept; rescored copy separate)
STOP = set("the a an and or of to in on at by for with from as is are was were be been it its this that these those will would should "
           "could can may might must not no yes if then than so do does did done has have had any all each per our your their his her "
           "about into over under after before while when where which who whom what how also just only more most less very".split())

# ------------------------------------------------------------------------------ helpers ----
VARIANT = "passed"   # "passed" = the trap deadline is behind the anchor date; "live" = still ahead, retracted in a sibling (fixtures/synthetic/live/)

def now12(): return dt.datetime.now().strftime("%Y-%m-%d %-I:%M %p")
def seed_dir(seed): return (FIX / "live" / f"seed{seed}") if VARIANT == "live" else (FIX / f"seed{seed}")
def vtag(): return "live_" if VARIANT == "live" else ""

def load_seed(seed):
    d = seed_dir(seed)
    if not (d / "ground_truth.json").exists():
        subprocess.run([sys.executable, "-I", str(FIX / "make_corpus.py"), "--seed", str(seed), "--trap", VARIANT], check=True)
    gt = json.loads((d / "ground_truth.json").read_text())
    events = [json.loads(l) for l in (d / "session" / "transcript.jsonl").read_text().splitlines() if l.strip()]
    handoff = (d / gt["handoff"]).read_text()
    return dict(seed=seed, dir=d, gt=gt, events=events, handoff=handoff, mem=d / "memory", fs=d / "fs")

def t12(iso):
    t = dt.datetime.fromisoformat(iso); return t.strftime("%-I:%M %p")

def render_transcript(events):
    out = [f"=== FULL TRANSCRIPT of the parked session (2026-08-28, {t12(events[0]['t'])} - {t12(events[-1]['t'])}) ==="]
    for e in events:
        if e["role"] == "tool":
            inp = e["input"]; arg = inp.get("file_path") or inp.get("pattern") or json.dumps(inp)
            res = e["result"] if isinstance(e["result"], str) else json.dumps(e["result"])
            if e["tool"] == "Edit": res = "appended: " + inp.get("append", "")
            out.append(f"[{t12(e['t'])}] TOOL {e['tool']} {arg} ->\n" + "\n".join("    " + l for l in res.splitlines()))
        else:
            out.append(f"[{t12(e['t'])}] {e['role'].upper()}: {e['content']}")
    return "\n\n".join(out) + "\n"

def tokens_of(text):
    """Content tokens for overlap: words of 4+ letters minus stopwords, plus m/d and ISO dates."""
    t = set(w for w in re.findall(r"[a-z][a-z\-']{3,}", text.lower()) if w not in STOP)
    t |= set(re.findall(r"\b\d{1,2}/\d{1,2}\b|\b20\d\d-\d\d-\d\d\b", text))
    return t

def has_keys(text, keys):
    t = (text or "").lower()
    return any(all(s.lower() in t for s in alt) for alt in keys)

MONTHS = "january february march april may june july august september october november december".split()
def date_forms(s):
    """All textual forms of a date given as m/d, m/d/yy(yy) or ISO (year assumed 2026)."""
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)$", s)
    if m: y, mo, d = int(m[1]), int(m[2]), int(m[3])
    else:
        p = s.split("/"); mo, d = int(p[0]), int(p[1]); y = 2026 if len(p) < 3 else (int(p[2]) + 2000 if int(p[2]) < 100 else int(p[2]))
    name = MONTHS[mo - 1]
    return {f"{mo}/{d}", f"{mo:02d}/{d:02d}", f"{mo}/{d:02d}", f"{mo:02d}/{d}", f"{mo}/{d}/{y}", f"{mo}/{d}/{str(y)[2:]}", f"{y}-{mo:02d}-{d:02d}",
            f"{name} {d}", f"{name[:3]} {d}", f"{name[:4]} {d}", f"{name} {d}, {y}", f"{name[:3]}. {d}", f"{d} {name}", f"{d} {name[:3]}"}

def date_in(text, s):
    t = (text or "").lower()
    return any(re.search(r"(?<![\d/])" + re.escape(f.lower()) + r"(?![\d/])", t) for f in date_forms(s))

def parse_any_date(s):
    s = (s or "").strip()
    for rx, fn in [(r"(20\d\d)-(\d\d)-(\d\d)", lambda m: dt.date(int(m[1]), int(m[2]), int(m[3]))),
                   (r"(\d{1,2})/(\d{1,2})/(\d{2,4})", lambda m: dt.date(int(m[3]) + (2000 if int(m[3]) < 100 else 0), int(m[1]), int(m[2]))),
                   (r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])", lambda m: dt.date(2026, int(m[1]), int(m[2]))),
                   (r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})", lambda m: dt.date(2026, MONTHS.index([x for x in MONTHS if x.startswith(m[1].lower())][0]) + 1, int(m[2])))]:
        m = re.search(rx, s, re.I)
        if m:
            try: return fn(m)
            except (ValueError, IndexError): pass
    return None

# ------------------------------------------------------------------------------ the API ----
class ApiError(Exception): pass

def api_key():
    env = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env: return env
    p = Path(os.path.expanduser("~/.config/anthropic/api_key"))
    if not p.exists(): raise ApiError(f"no API key: set ANTHROPIC_API_KEY or put the key in {p}")
    return p.read_text().strip()

def api_post(path, body, retries=4, timeout=180):
    key = api_key(); last = None
    for k in range(retries):
        req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")[:600]; last = f"HTTP {e.code}: {err}"
            if e.code in (429, 500, 502, 503, 529): time.sleep(2 ** k + random.random()); continue
            raise ApiError(last)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = f"network: {e}"; time.sleep(2 ** k); continue
    raise ApiError(f"gave up after {retries} tries: {last}")

def count_tokens(text, model):
    try:
        return api_post("messages/count_tokens", {"model": model, "messages": [{"role": "user", "content": text}]})["input_tokens"], "api_count"
    except ApiError:
        return max(1, len(text) // 4), "chars/4 (count_tokens unavailable)"

GEN_MAX_TOKENS = 12000    # thinking counts against max_tokens on Sonnet 5.5 (adaptive thinking is on by default): leave room
AGENT_MAX_TOKENS = 16000

def api_text(system, user, model, max_tokens=GEN_MAX_TOKENS):
    r = api_post("messages", {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
    return "".join(b.get("text", "") for b in r["content"] if b["type"] == "text").strip(), r.get("model"), r.get("usage", {}), r.get("stop_reason")

# ------------------------------------------------------------------------------ traces ----
# The compaction arm imitates the summary step that coding agents ship with today. The first sentence of the prompt and
# five of its nine section names are the same as in the compaction prompt Claude Code ships; the second sentence and the
# other four sections are adapted from code to notes. It is one model call with no tools, not Claude Code's compaction.
COMPACTION_SYSTEM = ("You are compacting a conversation so it can continue in a fresh context window. Produce only the summary.")
COMPACTION_PROMPT = """Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions. This summary should be thorough in capturing details, decisions and open work that would be essential for continuing without losing context.

Structure the summary with these sections:
1. Primary Request and Intent
2. Key Concepts and Entities
3. Files and Notes touched (with paths)
4. Errors and how they were handled
5. Problem Solving
6. All user messages (in order, briefly)
7. Pending Tasks
8. Current Work
9. Optional Next Step

(This prompt is modeled on Claude Code's compaction instructions; the sections are paraphrased.)

Here is the conversation:

"""
REMAP_SYSTEM = ("You rewrite a finished session for the NEXT agent's goals, not for fidelity. Output only the remap, in the exact sections requested.")
REMAP_PROMPT = """Rewrite this finished session for the next agent, who will be rebuilt from your output alone, possibly weeks later. Produce exactly these sections:

DONE - what was completed, one line each.
PENDING - one line per open claim or task. Under each, a rent ledger line in braces: {why kept: ...; predicts: ...; verify-by: <the date after which this item must be re-checked before anyone acts on it>; tokens: <your estimate for the item>}.
DECIDED - each decision with the date it was decided, each with a rent ledger line.
MUST-NOT - anything retracted, dropped, superseded or falsified during the session that the next agent must not act on, with the date.
NEXT ACTION - one line, with its verify-by date.
RESUMPTION PROMPT - at most three lines.

Rules: keep every date; state for every claim about the world the date it was last known true; add no facts that are not in the transcript; be short.

Transcript:

"""

def trust_brief(ctx, trace_text):
    """Condition 1: the D2 session-start line, derived from the read-only audit of the memory and the retractions in notes edited after the session."""
    gt = ctx["gt"]; mem = ctx["mem"]
    rows, _, _ = rot_audit.audit(str(mem), str(mem / "MEMORY.md"), ANCHOR)
    named = [r for r in rows if r["file"] in trace_text or r["file"][:-3] in trace_text]
    lines = [f"=== MEMORY TRUST (as of {ANCHOR.strftime('%-m/%-d/%Y')}, from the read-only memory audit) ==="]
    for r in named:
        if r["horizon"]:
            lines.append(f"- {r['file']}: scheduling date(s) {', '.join(r['horizon'])} passed after its last edit ({r['modified']}); treat as UNVERIFIED until re-checked.")
        elif r["absence"]:
            lines.append(f"- {r['file']}: carries {r['absence']} claim(s) that something has not happened, last edited {r['modified']}; treat as UNVERIFIED.")
    named_text = " ".join((mem / r["file"]).read_text() for r in named)
    for f, when, line in retraction_lines(ctx):
        if len(tokens_of(line) & tokens_of(named_text)) >= 3:
            lines.append(f"- RETRACTION recorded in {f} (edited {when}): \"{line}\"")
    return "\n".join(lines) + "\n"

def retraction_lines(ctx):
    """Dated retraction lines in notes edited after the session: from the flip marker to the end of the paragraph."""
    out = []; after = dt.date.fromisoformat(ctx["gt"]["session_date"])
    for f in sorted(ctx["mem"].glob("*.md")):
        if f.name == "MEMORY.md": continue
        when = dt.date.fromtimestamp(f.stat().st_mtime)
        if when <= after: continue
        _, body = rot_audit.parse_frontmatter(f.read_text())
        for para in body.split("\n"):
            m = re.search(r"(EDIT \d{4}-\d\d-\d\d:|RETRACT|SUPERSEDED|MOOT|OUT OF DATE)", para)
            if m: out.append((f.name, when.isoformat(), para[m.start():].strip()))
    return out

def build_traces(ctx, model, regen=False):
    p = RUNS / f"traces_{vtag()}seed{ctx['seed']}.json"
    if p.exists() and not regen: return json.loads(p.read_text())
    tr = render_transcript(ctx["events"])
    traces = dict(seed=ctx["seed"], generated=now12(), model=model, fidelity=dict(text=tr, generated_by="verbatim"))
    for key, system, prompt in [("compaction", COMPACTION_SYSTEM, COMPACTION_PROMPT), ("remap", REMAP_SYSTEM, REMAP_PROMPT)]:
        try:
            text, served, usage, stop = api_text(system, prompt + tr, model)
            traces[key] = dict(text=text, generated_by=served, usage=usage, stop_reason=stop, truncated=(stop == "max_tokens"))
            if stop == "max_tokens": print(f"WARNING: {key} trace for seed {ctx['seed']} hit max_tokens ({GEN_MAX_TOKENS}); it is truncated")
        except ApiError as e:
            traces[key] = dict(text=None, generated_by=None, error=str(e))
    for key in ("fidelity", "compaction", "remap"):
        if traces[key].get("text"): traces[key]["tokens"], traces[key]["tokens_method"] = count_tokens(traces[key]["text"], model)
    brief = trust_brief(ctx, tr); traces["brief"] = dict(text=brief); traces["brief"]["tokens"], traces["brief"]["tokens_method"] = count_tokens(brief, model)
    RUNS.mkdir(exist_ok=True); p.write_text(json.dumps(traces, indent=1))
    return traces

# ------------------------------------------------------------------------------ the fresh agent ----
SYSTEM = f"""You are resuming work for the owner of a small bookbinding studio. The previous session ended on 2026-08-28 and was parked; today is {ANCHOR_TEXT}. Everything you know about that session is the trace in the user message. You also have read-only tools over the studio's memory directory (short notes, one topic each) and its file sandbox; the memory may have changed since the trace was written.
Rules: do not invent facts. Distinguish what the trace says from what you verified. When you are ready, call submit_answer exactly once with the complete answer; if a MEMORY TRUST notice arrives after you submit, you may call submit_answer once more with a revised answer. Keep every entry short."""

RUBRIC_PROMPT = """Answer these questions about the resumed work and submit them with the submit_answer tool:
1. pending: every item that was still open at the end of the traced session (one entry each; name the source).
2. decided: every decision the trace records, each with the date it was decided.
3. next_action: the single next action you would take now, today.
4. must_not: anything that must NOT be done or acted on, according to the trace or to anything you verified.
5. unverified: notes named in the trace whose claims you would not act on without re-checking, and since what date (for example a scheduling date that has passed, or a claim that something had not yet happened).
6. paths: every file or folder path the trace names, and whether it exists now.
7. re_explain: what the owner will probably have to tell you again: facts the trace cannot carry, or that may have changed while the work was parked.
Also list the memory notes you actually read (notes_read) and your confidence in the whole answer (0 to 1)."""

ANSWER_SCHEMA = {"type": "object", "properties": {
    "pending": {"type": "array", "items": {"type": "object", "properties": {"item": {"type": "string"}, "source": {"type": "string"}}, "required": ["item"]}},
    "decided": {"type": "array", "items": {"type": "object", "properties": {"decision": {"type": "string"}, "date": {"type": "string"}}, "required": ["decision", "date"]}},
    "next_action": {"type": "string"},
    "must_not": {"type": "array", "items": {"type": "object", "properties": {"item": {"type": "string"}, "why": {"type": "string"}}, "required": ["item"]}},
    "unverified": {"type": "array", "items": {"type": "object", "properties": {"note": {"type": "string"}, "since": {"type": "string"}, "why": {"type": "string"}}, "required": ["note", "since"]}},
    "paths": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "exists": {"type": "boolean"}}, "required": ["path", "exists"]}},
    "re_explain": {"type": "array", "items": {"type": "string"}},
    "notes_read": {"type": "array", "items": {"type": "string"}},
    "confidence": {"type": "number"}},
    "required": ["pending", "decided", "next_action", "must_not", "unverified", "paths", "re_explain", "notes_read", "confidence"]}

TOOLS = [
    dict(name="list_notes", description="List the memory notes (file name and one-line description).", input_schema={"type": "object", "properties": {}}),
    dict(name="read_note", description="Read one memory note by file name (as listed).", input_schema={"type": "object", "properties": {"file": {"type": "string"}}, "required": ["file"]}),
    dict(name="search_notes", description="Case-insensitive search across all memory notes; returns matching lines with file names.", input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
    dict(name="check_path", description="Report whether a file or folder path exists (studio file sandbox and memory only).", input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    dict(name="submit_answer", description="Submit the final structured answer to the seven questions.", input_schema=ANSWER_SCHEMA)]

def validate_answer(a):
    if not isinstance(a, dict): return "answer is not an object"
    a.setdefault("notes_read", [])   # evidence only, never scored; the model omits it now and then
    for k in ANSWER_SCHEMA["required"]:
        if k not in a: return f"missing field {k}"
    if not isinstance(a["next_action"], str): return "next_action not a string"
    for k in ("pending", "decided", "must_not", "unverified", "paths", "re_explain", "notes_read"):
        if not isinstance(a[k], list): return f"{k} not a list"
    try: c = float(a["confidence"])
    except (TypeError, ValueError): return "confidence not a number"
    if c < 0.3: return f"low confidence {c:.2f}"
    return None

JIT_SURFACE = "next_action"   # what "reaching for a claim" means: the next action only (default), or the whole answer surface

def answer_surface(a, surface=None):
    """The text the agent is about to act on. 'next_action' = the one action it will take now (the precise reading of
    just-in-time). 'answer' = next action plus pending items, which fires whenever the stale item is merely recalled."""
    surface = surface or JIT_SURFACE
    if surface == "next_action": return str(a.get("next_action", ""))
    return " ".join([str(a.get("next_action", ""))] + [str(x.get("item", "")) + " " + str(x.get("source", "")) for x in a.get("pending", []) if isinstance(x, dict)])

def jit_matches(ctx, answer, k_distractors=0, rng=None, surface=None):
    """Just-in-time salience: retraction lines in later notes that overlap what the answer is about to act on."""
    surface = tokens_of(answer_surface(answer, surface)); hits = []; rest = []
    for f, when, line in retraction_lines(ctx):
        shared = surface & tokens_of(line)
        (hits if len(shared) >= 3 else rest).append((len(shared), f, when, line))
    hits.sort(reverse=True)
    out = [dict(file=f, edited=when, line=line, shared=n, relevant=True) for n, f, when, line in hits[:1]]
    if k_distractors and rest:
        rng = rng or random.Random(0)
        for n, f, when, line in rng.sample(rest, min(k_distractors, len(rest))):
            out.append(dict(file=f, edited=when, line=line, shared=n, relevant=False))
    return out

def injection_text(matches):
    lines = ["MEMORY TRUST (just-in-time): dated lines recorded in notes edited AFTER the traced session that may bear on what you are about to act on:"]
    for m in matches: lines.append(f"- {m['file']} (edited {m['edited']}): \"{m['line']}\"")
    lines.append("Re-check the affected items and call submit_answer again with your final answer. This notice appears once.")
    return "\n".join(lines)

class Sandbox:
    def __init__(self, ctx):
        self.ctx = ctx; self.mem = ctx["mem"]; self.fs = ctx["fs"]; self.calls = []
    def run(self, name, inp):
        try: res = getattr(self, "t_" + name)(**inp)
        except TypeError as e: res = f"error: bad arguments ({e})"
        except Exception as e: res = f"error: {e}"
        self.calls.append(dict(tool=name, input=inp, result_chars=len(res), result_head=res[:160]))
        return res
    def t_list_notes(self):
        out = []
        for f in sorted(self.mem.glob("*.md")):
            if f.name == "MEMORY.md": continue
            fm, _ = rot_audit.parse_frontmatter(f.read_text()); out.append(f"{f.name}: {fm.get('description', '')}")
        return "\n".join(out)
    def t_read_note(self, file):
        p = self.mem / Path(file).name
        if not p.exists(): return f"no such note: {Path(file).name}"
        when = dt.date.fromtimestamp(p.stat().st_mtime).isoformat()
        return f"[{p.name}, last edited {when}]\n" + p.read_text()
    def t_search_notes(self, query):
        q = query.lower(); out = []
        for f in sorted(self.mem.glob("*.md")):
            if f.name == "MEMORY.md": continue
            for line in f.read_text().splitlines():
                if q in line.lower(): out.append(f"{f.name}: {line.strip()[:240]}")
        return "\n".join(out[:60]) or "(no matches)"
    def t_check_path(self, path):
        p = Path(os.path.expanduser(path.strip().rstrip(".:,;")))
        roots = [self.fs.resolve(), self.mem.resolve()]
        try: rp = p.resolve()
        except OSError: return "unverifiable"
        if not any(str(rp).startswith(str(r)) for r in roots): return "outside the sandbox: not checkable here"
        return f"exists: {p.exists()}" + (" (folder)" if p.is_dir() else " (file)" if p.is_file() else "")

def run_agent_api(ctx, arm, trace_text, cond, model, brief=None, run_seed=0):
    sb = Sandbox(ctx); evidence = dict(tool_calls=sb.calls, injections=[], assistant_text=[], turns=0)
    user = (brief + "\n" if cond == "1" else "") + f"TRACE ({arm}):\n\n{trace_text}\n\n{RUBRIC_PROMPT}"
    messages = [{"role": "user", "content": user}]
    usage = dict(input_tokens=0, output_tokens=0, cache_read_input_tokens=0); served = None
    answer = None; injected_once = False; tokens_injected = 0; fired = False; error = None; resubmitted = None
    for turn in range(16):
        evidence["turns"] = turn + 1
        try:
            r = api_post("messages", {"model": model, "max_tokens": AGENT_MAX_TOKENS, "system": SYSTEM, "messages": messages, "tools": TOOLS})
        except ApiError as e:
            error = str(e); break
        served = r.get("model"); u = r.get("usage", {})
        for k in usage: usage[k] += u.get(k, 0) or 0
        usage["thinking_tokens"] = usage.get("thinking_tokens", 0) + ((u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0)
        content = r.get("content", []); messages.append({"role": "assistant", "content": content})
        evidence.setdefault("stop_reasons", []).append(r.get("stop_reason"))
        if r.get("stop_reason") == "max_tokens" and any(b["type"] == "tool_use" and b["name"] == "submit_answer" for b in content):
            error = f"answer truncated by max_tokens ({AGENT_MAX_TOKENS})"; break
        for b in content:
            if b["type"] == "text" and b["text"].strip(): evidence["assistant_text"].append(b["text"][:1200])
        uses = [b for b in content if b["type"] == "tool_use"]
        if not uses:
            if answer is None:
                error = ("submission refused once (hard denial); the agent ended without resubmitting" if cond == "2h" and injected_once
                         else f"ended without submit_answer (stop_reason {r.get('stop_reason')})")
            break
        results = []
        for b in uses:
            if b["name"] == "submit_answer":
                if injected_once: resubmitted = True
                if cond in ("2", "2d", "2h") and not injected_once:
                    matches = jit_matches(ctx, b["input"], k_distractors=3 if cond == "2d" else 0, rng=random.Random(run_seed))
                    if matches:
                        injected_once = True; fired = True; resubmitted = False; txt = injection_text(matches)
                        tokens_injected, _ = count_tokens(txt, model)
                        evidence["injections"].append(dict(text=txt, matches=matches, tokens=tokens_injected, first_answer=b["input"], framing="hard" if cond == "2h" else "soft"))
                        if cond == "2h":   # hard denial: the submission is refused (is_error), nothing is recorded as the answer until the agent resubmits
                            results.append({"type": "tool_result", "tool_use_id": b["id"], "is_error": True, "content": HARD_DENIAL_PREFIX + txt}); continue
                        answer = b["input"]   # soft: the first answer stands unless the agent chooses to resubmit
                        results.append({"type": "tool_result", "tool_use_id": b["id"], "content": txt}); continue
                answer = b["input"]
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": "Answer received. You may stop now."})
            else:
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": sb.run(b["name"], b["input"])})
        messages.append({"role": "user", "content": results})
        if answer is not None and not any(x["content"].startswith("MEMORY TRUST") for x in results): break
    else:
        error = error or "turn limit reached"
    # resubmitted=False means the injection fired and the agent kept its first answer (often saying so in text); that is a valid final answer
    evidence["resubmitted_after_injection"] = resubmitted; evidence["jit_surface"] = JIT_SURFACE
    return dict(answer=answer, error=error, served_model=served, usage=usage, evidence=evidence, fired=fired, tokens_injected=tokens_injected,
                brief_tokens=0)

def run_agent_cli(ctx, arm, trace_text, cond, model, brief=None, run_seed=0):
    """claude -p lane: same prompt, same schema; just-in-time condition via a PreToolUse hook on StructuredOutput
    (imaginal_stop_hook.py). One cell verified 2026-10-31; every saved matrix ran on the api backend."""
    import shutil, tempfile
    (RUNS / "cli_sandbox").mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"seed{ctx['seed']}_{arm}_{cond}_", dir=RUNS / "cli_sandbox")); shutil.copytree(ctx["mem"], tmp / "memory", copy_function=shutil.copy2)
    shutil.copytree(ctx["fs"], tmp / "fs", copy_function=shutil.copy2)
    settings = {"hooks": {}}
    if cond in ("2", "2d"):
        settings["hooks"]["PreToolUse"] = [{"matcher": "StructuredOutput", "hooks": [{"type": "command", "timeout": 30,
            "command": f"{sys.executable} -I {HERE / 'imaginal_stop_hook.py'} --seed {ctx['seed']} --cond {cond} --run-seed {run_seed} --variant {VARIANT}"}]}]
    (tmp / "settings.json").write_text(json.dumps(settings))
    user = (brief + "\n" if cond == "1" else "") + f"TRACE ({arm}):\n\n{trace_text}\n\n{RUBRIC_PROMPT}\n\nThe memory directory is ./memory and the file sandbox is ./fs (paths beginning ~ map to the sandbox). Produce the answer as the structured output."
    # session persistence is left ON: each run's transcript lands under ~/.claude/projects/<sandbox path>/,
    # a byproduct to clean up by hand (the hook itself reads the tool input, not the transcript)
    cmd = ["claude", "-p", user, "--model", model, "--output-format", "json", "--restricted", "--setting-sources", "project",
           "--allowedTools", "Read,Glob,Grep", "--system-prompt", SYSTEM, "--json-schema", json.dumps(ANSWER_SCHEMA),
           "--settings", str(tmp / "settings.json")]
    try:
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
        d = json.loads(r.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return dict(answer=None, error=f"cli: {e}", served_model=None, usage={}, evidence=dict(sandbox=str(tmp)), fired=False, tokens_injected=0, brief_tokens=0)
    answer = d.get("structured_output"); err = None if answer else (d.get("result") or "no structured output")
    hook = [json.loads(l) for l in (tmp / "hook_log.jsonl").read_text().splitlines()] if (tmp / "hook_log.jsonl").exists() else []
    fired = any(h.get("fired") for h in hook); inj = next((h["injection"] for h in hook if h.get("fired")), None)
    tokens_injected = count_tokens(inj, DEFAULT_MODEL)[0] if inj else 0
    return dict(answer=answer, error=err, served_model=None, usage=d.get("usage", {}), evidence=dict(sandbox=str(tmp), num_turns=d.get("num_turns"),
                is_error=d.get("is_error"), hook_log=hook), fired=fired, tokens_injected=tokens_injected, brief_tokens=0)

# ------------------------------------------------------------------------------ scoring ----
def score(answer, gt):
    R = gt["rubric"]; s = {}; detail = {}
    pend_text = [str(x.get("item", "")) + " " + str(x.get("source", "")) for x in answer["pending"] if isinstance(x, dict)]
    hits = [any(has_keys(t, g["keys"]) for t in pend_text) for g in R["pending"]]
    s["pending"] = sum(hits) / len(hits); detail["pending"] = dict(zip([g["id"] for g in R["pending"]], hits))
    dec = [(str(x.get("decision", "")), str(x.get("date", ""))) for x in answer["decided"] if isinstance(x, dict)]
    dsc = []
    for g in R["decided"]:
        best = 0.0
        for d, when in dec:
            if has_keys(d, g["keys"]): best = max(best, 1.0 if any(date_in(d + " " + when, x) for x in g["dates"]) else 0.5)
        dsc.append(best)
    s["decided"] = sum(dsc) / len(dsc); detail["decided"] = dict(zip([g["id"] for g in R["decided"]], dsc))
    na = answer["next_action"].lower(); trap = R["trap"]
    verifying = any(w in na for w in trap["verify_words"] + VERIFY_PHRASES)
    # a sentence that NEGATES the trap ("do not resend the appraisal") is the agent knowing better, not acting
    na_pos = " ".join(sent for sent in re.split(r"(?<=[.;!?])\s+", na) if not re.search(NEGATION, sent))
    if verifying: s["next_action"], detail["next_action"] = 1.0, "verifies first"
    elif has_keys(na_pos, trap["act_keys"]): s["next_action"], detail["next_action"] = 0.0, "ACTS ON THE RETRACTED DEADLINE"
    elif has_keys(na, R["next_action"]["good_keys"]): s["next_action"], detail["next_action"] = 1.0, "a live pending item"
    else: s["next_action"], detail["next_action"] = 0.0, "neither a live item nor a verification"
    mn_text = [str(x.get("item", "")) + " " + str(x.get("why", "")) for x in answer["must_not"] if isinstance(x, dict)]
    uv_text = [str(x.get("note", "")) + " " + str(x.get("since", "")) + " " + str(x.get("why", "")) for x in answer["unverified"] if isinstance(x, dict)]
    t1_mn = any(has_keys(t, R["must_not"][0]["keys"]) for t in mn_text); t1_uv = any(has_keys(t, R["must_not"][0]["keys"]) for t in uv_text)
    t2 = any(has_keys(t, R["must_not"][1]["keys"]) for t in mn_text)
    s["must_not"] = ((1.0 if (t1_mn or t1_uv) else 0.0) + (1.0 if t2 else 0.0)) / 2
    acted = s["next_action"] == 0.0 and has_keys(na_pos, trap["act_keys"])
    trap_state = "acted" if acted else ("caught" if (t1_mn or t1_uv) else "unaware")
    detail["must_not"] = dict(T1_in_must_not=t1_mn, T1_in_unverified=t1_uv, T2=t2, trap_state=trap_state)
    uvs = []
    for g in R["unverified"]:
        best = 0.0; since = dt.date.fromisoformat(g["since"])
        for x in answer["unverified"]:
            if not isinstance(x, dict): continue
            t = str(x.get("note", "")) + " " + str(x.get("why", ""))
            if has_keys(t, g["keys"]):
                d = parse_any_date(str(x.get("since", ""))) or parse_any_date(t)
                best = max(best, 1.0 if (d and abs((d - since).days) <= 21) else 0.5)
        uvs.append(best)
    s["unverified"] = sum(uvs) / len(uvs); detail["unverified"] = dict(zip([g["note"] for g in R["unverified"]], uvs))
    pth = []
    for g in R["paths"]:
        tail = "/".join(g["path"].rstrip("/").split("/")[-2:]).lower(); got = None
        for x in answer["paths"]:
            if isinstance(x, dict) and tail in str(x.get("path", "")).lower().rstrip("/") + "/" * 0: got = bool(x.get("exists")); break
            if isinstance(x, dict) and tail in str(x.get("path", "")).lower(): got = bool(x.get("exists")); break
        pth.append(1.0 if got == g["exists"] else 0.0)
    s["paths"] = sum(pth) / len(pth); detail["paths"] = dict(zip([g["path"].rstrip("/").split("/")[-1] for g in R["paths"]], pth))
    blob = json.dumps({k: v for k, v in answer.items() if k != "re_explain"}).lower()
    known = {f["id"]: has_keys(blob, f["known_keys"]) for f in R["first_turn_facts"]}
    s["known"] = sum(known.values()) / len(known); detail["known"] = known
    unknown = [f for f in R["first_turn_facts"] if not known[f["id"]]]
    if unknown:
        re_text = " ".join(str(x) for x in answer["re_explain"])
        flagged = {f["id"]: has_keys(re_text, f["topic_keys"]) for f in unknown}
        s["re_explain"] = sum(flagged.values()) / len(flagged); detail["re_explain"] = flagged
    else:
        s["re_explain"] = 1.0; detail["re_explain"] = "knew everything"
    survival = 100.0 * sum(s.values()) / len(s)
    return dict(scores=s, detail=detail, item_pass={k: v >= PASS for k, v in s.items()}, trap_state=trap_state, survival_pct=round(survival, 1))

# ------------------------------------------------------------------------------ survive ----
def one_run(ctx, traces, arm, cond, backend, model, run_seed):
    tr = traces[arm]; t0 = time.time()
    row = dict(seed=ctx["seed"], arm=arm, condition=cond, backend=backend, model_requested=model, started=now12())
    if not tr.get("text"):
        row.update(verdict="no_verdict", error=f"trace missing: {tr.get('error')}"); return row
    brief = traces["brief"]["text"] if cond == "1" else None
    fn = run_agent_api if backend == "api" else run_agent_cli
    res = fn(ctx, arm, tr["text"], cond, model, brief=brief, run_seed=run_seed)
    row.update(served_model=res["served_model"], usage=res["usage"], evidence=res["evidence"], injection_fired=res["fired"],
               tokens_injected=(traces["brief"]["tokens"] if cond == "1" else res["tokens_injected"]), trace_tokens=tr.get("tokens"),
               seconds=round(time.time() - t0, 1), answer=res["answer"])
    problem = res["error"] or (validate_answer(res["answer"]) if res["answer"] is not None else "no answer")
    if problem:
        row.update(verdict="no_verdict", error=problem); return row
    sc = score(res["answer"], ctx["gt"]); row.update(verdict="ok", **sc)
    rent = (row["trace_tokens"] or 0) + (row["tokens_injected"] or 0)
    row["tokens_at_start"] = rent; row["survival_per_ktoken"] = round(row["survival_pct"] / (rent / 1000.0), 2) if rent else None
    return row

def revised_after_injection(r):
    """True when the run's injection matched the RELEVANT retraction line and the final next action differs from the one first submitted."""
    inj = ((r.get("evidence") or {}).get("injections") or [None])[0]
    if not inj or not any(m.get("relevant") for m in inj.get("matches", [])): return False
    first = str((inj.get("first_answer") or {}).get("next_action", "")).strip(); final = str((r.get("answer") or {}).get("next_action", "")).strip()
    return bool(final) and first != final

def aggregate(seeds_data):
    runs = [r for sd in seeds_data.values() for r in sd["runs"]]
    agg = dict(grid={}, survival={}, trap={}, no_verdicts=sum(1 for r in runs if r["verdict"] != "ok"), runs=len(runs))
    for arm in [a["key"] for a in ARMS]:
        base = [r for r in runs if r["arm"] == arm and r["condition"] == "0" and r["verdict"] == "ok"]
        agg["grid"][arm] = {it["key"]: dict(n=len(base), passed=sum(1 for r in base if r["item_pass"][it["key"]]),
                                          mean=round(sum(r["scores"][it["key"]] for r in base) / len(base), 2) if base else None) for it in RUBRIC}
        agg["grid"][arm]["trap_states"] = {st: sum(1 for r in base if r["trap_state"] == st) for st in ("caught", "unaware", "acted")}
        agg["survival"][arm] = dict(n=len(base), mean_pct=round(sum(r["survival_pct"] for r in base) / len(base), 1) if base else None,
                                    trace_tokens=round(sum(r["trace_tokens"] or 0 for r in base) / len(base)) if base else None,
                                    per_ktoken=round(sum(r["survival_per_ktoken"] or 0 for r in base) / len(base), 2) if base else None)
        agg["trap"][arm] = {}
        for c in [c["key"] for c in CONDITIONS]:
            rs = [r for r in runs if r["arm"] == arm and r["condition"] == c]; ok = [r for r in rs if r["verdict"] == "ok"]
            agg["trap"][arm][c] = dict(n=len(rs), ok=len(ok), avoided=sum(1 for r in ok if r["trap_state"] != "acted"),
                                       caught=sum(1 for r in ok if r["trap_state"] == "caught"), acted=sum(1 for r in ok if r["trap_state"] == "acted"),
                                       fired=sum(1 for r in ok if r.get("injection_fired")),
                                       fired_relevant=sum(1 for r in ok if any(m.get("relevant") for m in ((((r.get("evidence") or {}).get("injections") or [{}])[0]) or {}).get("matches", []))),
                                       revised=sum(1 for r in ok if revised_after_injection(r)),
                                       tokens_injected=round(sum(r.get("tokens_injected") or 0 for r in ok) / len(ok)) if ok else None,
                                       survival_pct=round(sum(r["survival_pct"] for r in ok) / len(ok), 1) if ok else None,
                                       per_ktoken=round(sum(r["survival_per_ktoken"] or 0 for r in ok) / len(ok), 2) if ok else None)
    return agg

def survive(seeds, arms, conds, backend, model, parallel, out, regen=False, merge=False, retry=False):
    """merge: keep the rows already in `out` and replace only the (seed, arm, condition) cells run now; the replaced rows are kept
    under superseded_runs. retry: run only the cells whose saved row has no verdict."""
    prev = json.loads(out.read_text()) if (merge or retry) and out.exists() else None
    data = dict(about="SYNTHETIC. Every note, person, company, date and path is fiction generated by fixtures/synthetic/make_corpus.py. No real memory note was read, displayed or saved.",
                generated=now12(), backend=backend, model_requested=model, anchor=ANCHOR.isoformat(), pass_threshold=PASS, jit_surface=JIT_SURFACE, variant=VARIANT,
                arms=ARMS, conditions=CONDITIONS, rubric=RUBRIC, display_seed=seeds[0], seeds={}, superseded_runs=(prev or {}).get("superseded_runs", []))
    if prev: data["seeds"] = dict(prev["seeds"]); data["display_seed"] = prev.get("display_seed", seeds[0])   # seeds not run now are kept whole
    jobs = []
    for seed in seeds:
        ctx = load_seed(seed); traces = build_traces(ctx, model, regen=regen)
        data["seeds"][str(seed)] = dict(world=ctx["gt"]["world"], session_date=ctx["gt"]["session_date"],
                                        transcript_text=traces["fidelity"]["text"], handoff_text=ctx["handoff"], first_turn=ctx["gt"]["first_turn_text"],
                                        trap=ctx["gt"]["rubric"]["trap"], traces={k: {kk: vv for kk, vv in traces[k].items()} for k in ("fidelity", "compaction", "remap", "brief")},
                                        runs=[])
        old = (prev or {}).get("seeds", {}).get(str(seed), {}).get("runs", [])
        for arm in arms:
            for c in conds:
                saved = [r for r in old if r["arm"] == arm and r["condition"] == c]
                if retry and saved and all(r["verdict"] == "ok" for r in saved): continue
                jobs.append((ctx, traces, arm, c))
        if prev:  # carry over every saved row for cells not run now
            running = {(j[2], j[3]) for j in jobs if j[0] is ctx}
            for r in old:
                if (r["arm"], r["condition"]) in running: data["superseded_runs"].append(r)
                else: data["seeds"][str(seed)]["runs"].append(r)
    print(f"{len(jobs)} runs: seeds {seeds}, arms {arms}, conditions {conds}, backend {backend}, model {model}, parallel {parallel}, jit_surface {JIT_SURFACE}" + (" (merge)" if prev else ""))
    with cf.ThreadPoolExecutor(max_workers=parallel) as ex:
        futs = {ex.submit(one_run, ctx, traces, arm, c, backend, model, 1000 * ctx["seed"] + sum(map(ord, arm + c)) % 997): (ctx, arm, c) for ctx, traces, arm, c in jobs}
        for f in cf.as_completed(futs):
            ctx, arm, c = futs[f]; row = f.result(); data["seeds"][str(ctx["seed"])]["runs"].append(row)
            tag = f"seed {ctx['seed']} {arm:10} cond {c:2}"
            if row["verdict"] == "ok":
                print(f"  {tag}: survival {row['survival_pct']:5.1f}%  trap {row['trap_state']:8}  tokens {row['tokens_at_start']:>5}  per-kt {row['survival_per_ktoken']}  {row['seconds']}s")
            else:
                print(f"  {tag}: NO VERDICT ({str(row.get('error'))[:120]})")
    for sd in data["seeds"].values(): sd["runs"].sort(key=lambda r: (r["arm"], r["condition"]))
    data["aggregate"] = aggregate(data["seeds"])
    models = sorted({r.get("served_model") for sd in data["seeds"].values() for r in sd["runs"] if r.get("served_model")})
    data["models_served"] = models
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(data, indent=1))
    print(f"\nsaved {out}  ({data['aggregate']['runs']} runs, {data['aggregate']['no_verdicts']} without verdict; served by {models})")
    summarize(data)
    return data

def summarize(data):
    agg = data["aggregate"]
    print("\n# condition 0 grid: passed/n per rubric item (seed-pooled)")
    print(f"{'item':34}" + "".join(f"{a['label'][:18]:>20}" for a in ARMS))
    for it in RUBRIC:
        print(f"{it['n']}. {it['label']:31}" + "".join(f"{agg['grid'][a['key']][it['key']]['passed']}/{agg['grid'][a['key']][it['key']]['n']} (mean {agg['grid'][a['key']][it['key']]['mean']})".rjust(20) for a in ARMS))
    print(f"{'trap states (caught/unaware/acted)':34}" + "".join(f"{s['caught']}/{s['unaware']}/{s['acted']}".rjust(20) for s in (agg['grid'][a['key']]['trap_states'] for a in ARMS)))
    print(f"{'survival % / trace tokens / per kt':34}" + "".join(f"{agg['survival'][a['key']]['mean_pct']} / {agg['survival'][a['key']]['trace_tokens']} / {agg['survival'][a['key']]['per_ktoken']}".rjust(20) for a in ARMS))
    print("\n# trap row by salience condition: avoided/ok (caught) | tokens injected | survival per kt")
    for a in ARMS:
        print(f"{a['label']:22}" + "".join(f"  {c['key']:>2}: {agg['trap'][a['key']][c['key']]['avoided']}/{agg['trap'][a['key']][c['key']]['ok']} ({agg['trap'][a['key']][c['key']]['caught']}) | {agg['trap'][a['key']][c['key']]['tokens_injected']} | {agg['trap'][a['key']][c['key']]['per_ktoken']}" for c in CONDITIONS))

# ------------------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", choices=["passed", "live"], default=None, help="trap variant: passed (default) or live (deadline still ahead, retracted in a sibling)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("corpus"); p.add_argument("--seed", type=int, default=1); p.add_argument("--verify", action="store_true")
    p = sub.add_parser("traces"); p.add_argument("--seed", type=int, default=1); p.add_argument("--model", default=DEFAULT_MODEL); p.add_argument("--regen", action="store_true")
    p = sub.add_parser("brief"); p.add_argument("--seed", type=int, default=1)
    p = sub.add_parser("survive")
    p.add_argument("--seeds", default="1,2,3"); p.add_argument("--arms", default="fidelity,compaction,remap"); p.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS), help="comma list from 0,1,2,2d,2h (2h = hard denial, API lane only)")
    p.add_argument("--backend", choices=["api", "cli"], default="api"); p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--parallel", type=int, default=4); p.add_argument("--out", default=str(RUNS / "demo.json")); p.add_argument("--regen", action="store_true")
    p.add_argument("--merge", action="store_true", help="replace only the cells run now in an existing --out file; keep the rest")
    p.add_argument("--retry-no-verdict", action="store_true", help="with --merge: run only the cells whose saved row has no verdict")
    p.add_argument("--jit-surface", choices=["next_action", "answer"], default="next_action")
    p = sub.add_parser("rescore"); p.add_argument("--run", default=str(RUNS / "demo.json")); p.add_argument("--out", default=None)
    p = sub.add_parser("demo")
    p.add_argument("--replay", default=None); p.add_argument("--live", action="store_true"); p.add_argument("--out", default=str(RUNS / "demo.html"))
    p.add_argument("--seeds", default="1,2,3"); p.add_argument("--model", default=DEFAULT_MODEL); p.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    global VARIANT
    if a.cmd == "rescore" and a.variant is None:   # a saved run knows its own variant
        a.variant = json.loads(Path(a.run).read_text()).get("variant", "passed")
    if a.cmd == "demo" and a.variant is None and a.replay:
        a.variant = json.loads(Path(a.replay).read_text()).get("variant", "passed")
    VARIANT = a.variant or "passed"
    if VARIANT == "live":   # default output names per variant, unless given explicitly
        if getattr(a, "out", None) == str(RUNS / "demo.json"): a.out = str(RUNS / "demo_live.json")
        if getattr(a, "out", None) == str(RUNS / "demo.html"): a.out = str(RUNS / "demo_live.html")
        if getattr(a, "run", None) == str(RUNS / "demo.json"): a.run = str(RUNS / "demo_live.json")
    if a.cmd == "corpus":
        cmd = [sys.executable, "-I", str(FIX / "make_corpus.py"), "--seed", str(a.seed), "--trap", VARIANT] + (["--verify"] if a.verify else [])
        sys.exit(subprocess.run(cmd).returncode)
    if a.cmd == "traces":
        ctx = load_seed(a.seed); tr = build_traces(ctx, a.model, regen=a.regen)
        for k in ("fidelity", "compaction", "remap", "brief"):
            print(f"\n===== {k} ({tr[k].get('tokens')} tokens, {tr[k].get('tokens_method')}, by {tr[k].get('generated_by')}) =====\n{tr[k].get('text') or tr[k].get('error')}")
        return
    if a.cmd == "brief":
        ctx = load_seed(a.seed); print(trust_brief(ctx, render_transcript(ctx["events"]))); return
    if a.cmd == "survive":
        global JIT_SURFACE; JIT_SURFACE = a.jit_surface
        if a.backend == "cli" and "2h" in a.conditions.split(","): sys.exit("condition 2h (hard denial) runs on the api backend only")
        survive([int(s) for s in a.seeds.split(",")], a.arms.split(","), a.conditions.split(","), a.backend, a.model, a.parallel, Path(a.out),
                regen=a.regen, merge=a.merge or a.retry_no_verdict, retry=a.retry_no_verdict); return
    if a.cmd == "rescore":
        # recompute scores and aggregates from the saved answers; no model call, no network
        src = Path(a.run); data = json.loads(src.read_text()); n = 0
        for sk, sd in data["seeds"].items():
            gt = load_seed(int(sk))["gt"]
            for r in sd["runs"]:
                if r.get("answer") is None: continue
                problem = validate_answer(r["answer"])
                if problem: r.update(verdict="no_verdict", error=problem); continue
                r.update(verdict="ok", error=None, **score(r["answer"], gt)); n += 1
                rent = (r.get("trace_tokens") or 0) + (r.get("tokens_injected") or 0)
                r["tokens_at_start"] = rent; r["survival_per_ktoken"] = round(r["survival_pct"] / (rent / 1000.0), 2) if rent else None
        data["aggregate"] = aggregate(data["seeds"]); data["rescored"] = now12()
        out = Path(a.out or src); out.write_text(json.dumps(data, indent=1)); print(f"rescored {n} runs -> {out}"); summarize(data); return
    if a.cmd == "demo":
        if a.live:
            data = survive([int(s) for s in a.seeds.split(",")], [x["key"] for x in ARMS], DEFAULT_CONDITIONS, "api", a.model, a.parallel, RUNS / f"demo{'_live' if VARIANT == 'live' else ''}.json")
        else:
            src = Path(a.replay or (RUNS / "demo.json"))
            if not src.exists(): sys.exit(f"no saved run at {src}; run `imaginal.py survive` or `demo --live` first")
            data = json.loads(src.read_text())
        try:
            import render_demo
        except ImportError:
            sys.exit("render_demo.py is missing beside imaginal.py")
        out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
        render_demo.render(data, out)
        print(f"rendered {out} ({out.stat().st_size // 1024} KB) from {'live run' if a.live else src}")

if __name__ == "__main__":
    main()
