#!/usr/bin/env python3
"""render_demo.py - the Imaginal demo page.

render(data, out) takes the dict that `imaginal.py survive` saved (runs/demo.json) and writes ONE
self-contained static HTML file: inline CSS and JS only, no network request of any kind (no CDN, no web fonts, no
images, no links). Every number on the page is read from `data`; the only fixed copy is the framing text, the legends,
the real-corpus line and the reproduce commands. Rows whose verdict is not "ok" are drawn grey as "no verdict" and are
left out of every mean. Expects the `aggregate` block that imaginal.py writes beside the seeds.
Stdlib only: datetime, html, pathlib.
"""
import datetime, html, pathlib

REAL_CORPUS_LINE = ("On the real 318-note corpus the audit's hit rate on hand-verified candidates was 41% (7 of 17 judgeable), "
                    "Wilson 95% interval roughly 22 to 64%; no real note appears on this page.")
COMMANDS = ("python3 -I fixtures/synthetic/make_corpus.py --seed 1 --verify\n"
            "python3 -I scripts/imaginal.py survive --seeds 1,2,3 --conditions 0,1,2,2d,2h --out runs/rerun.json\n"
            "python3 -I scripts/imaginal.py demo --replay runs/demo.json")
COMMANDS_LIVE = ("python3 -I fixtures/synthetic/make_corpus.py --seed 1 --trap live --verify\n"
                 "python3 -I scripts/imaginal.py --variant live survive --seeds 1,2,3 --out runs/rerun_live.json\n"
                 "python3 -I scripts/imaginal.py demo --replay runs/demo_live.json")
TRACE_NOTE = ("The labels are the saved run's own. \"Chroma's fidelity condition\" is this project's shorthand for the full-input "
              "condition in Chroma's Context Rot report; the term is not Chroma's. The compaction summary is an imitation written for "
              "this experiment under a prompt modeled on Claude Code's. It is not output from Claude Code.")
STATE_TONE = {"caught": "pass", "unaware": "mixed", "acted": "fail"}
TONE_WORDS = {"pass": "pass-majority", "mixed": "mixed (tied)", "fail": "fail-majority", "none": "no verdict"}

DARK = ("color-scheme:dark;--bg:#121211;--surface:#1b1b19;--surface2:#242421;--text:#ecece6;--muted:#a3a39b;--line:#383833;--bar:#d3d3ca;--bar-bg:#2d2d29;"
        "--pass:#6fd68a;--pass-bg:#14301c;--pass-line:#2b6a3d;--fail:#ff9488;--fail-bg:#3b1713;--fail-line:#7d3028;"
        "--mixed:#f2c94f;--mixed-bg:#35290b;--mixed-line:#7a5f1c;--none:#a3a39b;--none-bg:#2a2a27;--none-line:#42423d")

CSS = """
:root{color-scheme:light dark;--bg:#f6f6f2;--surface:#fff;--surface2:#eeede7;--text:#1d1d1b;--muted:#5f5f58;--line:#d9d8d0;--bar:#3a3a36;--bar-bg:#e3e2db;
--pass:#166534;--pass-bg:#dcf3e1;--pass-line:#9fd5ad;--fail:#b42318;--fail-bg:#fde4e1;--fail-line:#f1aaa3;
--mixed:#7a5200;--mixed-bg:#fbefc9;--mixed-line:#e6cd85;--none:#5c5c56;--none-bg:#ecebe6;--none-line:#cfcec6;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){__DARK__}}
:root[data-theme="dark"]{__DARK__}
:root[data-theme="light"]{color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 var(--sans)}
[hidden]{display:none!important}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px 56px}
h1{font-size:38px;line-height:1.1;letter-spacing:-.02em;margin:0}
h2{font-size:21px;line-height:1.25;margin:0 0 6px}
h3{font-size:15px;margin:18px 0 4px}
h4{margin:0 0 4px;font-size:13.5px}
p{margin:0 0 10px}
code,pre{font-family:var(--mono)}
code{font-size:.88em;background:var(--surface2);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
.muted{color:var(--muted)}
.cap{font-size:13px;max-width:100ch}
.lede{color:var(--muted);max-width:80ch}
section{margin:44px 0 0}
.top{display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:flex-start;padding:28px 0 16px}
.sub{font-size:18px;color:var(--muted);margin:6px 0 0;max-width:36em}
.theme{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.theme button{font:inherit;font-size:13px;color:var(--muted);background:var(--surface);border:0;padding:6px 12px;cursor:pointer}
.theme button+button{border-left:1px solid var(--line)}
.theme button[aria-pressed="true"]{background:var(--text);color:var(--bg)}
button:focus-visible,summary:focus-visible{outline:2px solid var(--text);outline-offset:2px}
.banner{border:2px solid var(--text);border-radius:10px;background:var(--surface);padding:14px 16px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:0 0 4px}
.flag{font-weight:600;margin:0 0 12px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px 16px;margin:0}
.facts dt{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.facts dd{margin:0;font-weight:600;overflow-wrap:anywhere}
.defs{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:4px 24px}
dl.d{margin:0}
dl.d dt{font-weight:600;font-size:14px}
dl.d dd{margin:0 0 8px;color:var(--muted);font-size:13.5px}
details{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:8px 0}
summary{cursor:pointer;padding:10px 14px;font-weight:600}
details>pre{margin:0 12px 12px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12.5px;line-height:1.5;background:var(--surface2);border:1px solid var(--line);border-radius:8px;padding:12px;max-height:420px;overflow:auto;margin:0}
pre.cmd{white-space:pre;overflow-wrap:normal;max-height:none}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px;min-width:0}
.card.small{margin-top:12px;max-width:540px;padding:10px 14px;font-size:13.5px}
.card h3{margin:0 0 2px;font-size:16px}
.card details{background:none;border:0;margin:6px 0 0}
.card summary{padding:6px 0}
.card details>pre{margin:0}
.tok{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-top:8px;font-weight:600}
.tbar{height:8px;background:var(--bar-bg);border-radius:4px;overflow:hidden;margin:4px 0 8px}
.tbar i,.track i{display:block;height:100%;background:var(--bar)}
.kv{font-size:12.5px;color:var(--muted);margin:0 0 4px}
.warn{font-size:13px;border:1px dashed var(--text);border-radius:6px;padding:6px 10px;margin:8px 0}
.callout{border-left:4px solid var(--text);background:var(--surface);padding:10px 14px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px}
.legend{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;font-size:12.5px;color:var(--muted);margin:10px 0}
.scroll{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
.cell,.chip{--tf:var(--none);--tb:var(--none-bg);--tl:var(--none-line)}
.t-pass{--tf:var(--pass);--tb:var(--pass-bg);--tl:var(--pass-line)}
.t-fail{--tf:var(--fail);--tb:var(--fail-bg);--tl:var(--fail-line)}
.t-mixed{--tf:var(--mixed);--tb:var(--mixed-bg);--tl:var(--mixed-line)}
.chip{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:600;line-height:1.5;color:var(--tf);background:var(--tb);border:1px solid var(--tl);white-space:nowrap}
.chip.sm{font-size:11px;padding:0 6px}
.chip.zero{opacity:.55}
.cell{display:block;width:100%;font:inherit;text-align:center;color:var(--tf);background:var(--tb);border:1px solid var(--tl);border-radius:8px;padding:8px 4px;cursor:pointer}
.cell:hover{filter:brightness(.96)}
.cell[aria-expanded="true"]{outline:2px solid var(--text);outline-offset:1px}
.cell.dashed{border-style:dashed}
.cell b{display:block;font-size:18px;line-height:1.25}
.cell small{display:block;font-size:11.5px}
.tstates{display:flex;flex-wrap:wrap;gap:3px;justify-content:center;margin-top:8px}
.grid{table-layout:fixed}
.grid col:first-child{width:31%}
.ah{font-size:12.5px;text-align:center;vertical-align:bottom;padding:6px 4px;border-bottom:2px solid var(--line)}
.ah:first-child{text-align:left}
.grid>tbody>tr>*{border-top:1px solid var(--line)}
.rl{text-align:left;font-size:13.5px;font-weight:600;vertical-align:top;padding:8px 6px 8px 4px}
.rl .n{display:inline-block;min-width:1.5em;color:var(--muted);font-weight:400}
.how{display:block;font-size:11.5px;font-weight:400;color:var(--muted);margin-top:2px}
.lnk{display:block;font:inherit;font-size:11.5px;font-weight:400;color:var(--muted);background:none;border:0;border-bottom:1px dotted var(--muted);padding:0;margin-top:4px;cursor:pointer}
.tag{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.06em;border:1px solid var(--text);border-radius:4px;padding:0 5px;margin-left:4px}
.gc{padding:6px 4px;vertical-align:top}
tr.trap>.rl,.srow>td{border-left:4px solid var(--text)}
tr.trap>.rl{padding-left:8px}
tr.trap>.gc{padding-top:12px;padding-bottom:12px}
tr.trap .cell{padding:14px 4px}
.drow>td{background:var(--surface2);padding:12px}
.srow>td{padding:10px 0 14px 12px}
.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:10px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;min-width:0;font-size:13px}
.panel .how{font-size:12px;margin:0 0 6px}
.seedrow+.seedrow{border-top:1px solid var(--line);margin-top:8px;padding-top:8px}
.said{margin:6px 0 4px;padding-left:18px}
.said li{margin:2px 0;overflow-wrap:anywhere}
.scoring{font:11.5px/1.4 var(--mono);color:var(--muted);margin:4px 0;overflow-wrap:anywhere}
.panel details{margin:6px 0}
.panel pre{max-height:240px}
.dt{min-width:620px}
.dt th,.dt td{border:1px solid var(--line);padding:6px;text-align:center;vertical-align:top;font-size:13px}
.dt thead th{background:var(--surface2)}
.dt tbody th{text-align:left}
.dt .cell{padding:6px 4px}
.dt .drow>td{text-align:left}
.bars{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:24px}
.bar{display:grid;grid-template-columns:minmax(80px,140px) minmax(0,1fr) auto;gap:8px;align-items:center;margin:8px 0;font-size:13.5px}
.track{height:22px;background:var(--bar-bg);border-radius:4px;overflow:hidden}
.val{font-weight:600;white-space:nowrap}
.val small{font-weight:400;color:var(--muted)}
.limits{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--text);border-radius:8px;padding:12px 18px}
.limits ul{margin:0;padding-left:20px}
.limits li{margin:8px 0}
footer{margin-top:44px;border-top:1px solid var(--line);padding-top:16px}
@media (max-width:640px){.rl .how{display:none}h1{font-size:32px}}
""".replace("__DARK__", DARK)

HEAD_JS = ("<script>try{var t=localStorage.getItem('imaginal-theme');"
           "if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>")

JS = """
(function(){
var root=document.documentElement,KEY='imaginal-theme';
function mode(m){return m==='light'||m==='dark'?m:'auto'}
function applyTheme(m){
  m=mode(m);
  if(m==='auto')root.removeAttribute('data-theme');else root.setAttribute('data-theme',m);
  document.querySelectorAll('[data-theme-set]').forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-theme-set')===m))});
}
var saved='auto';
try{saved=localStorage.getItem(KEY)||'auto'}catch(e){}
applyTheme(saved);
function sync(p){
  var row=p.closest('.drow');
  if(row)row.hidden=!row.querySelector('.panel:not([hidden])');
  document.querySelectorAll('[data-toggle~="'+p.id+'"]').forEach(function(b){b.setAttribute('aria-expanded',String(!p.hidden))});
}
document.addEventListener('click',function(e){
  var t=e.target.closest('[data-theme-set]');
  if(t){var m=mode(t.getAttribute('data-theme-set'));applyTheme(m);try{localStorage.setItem(KEY,m)}catch(err){}return}
  var b=e.target.closest('[data-toggle]');
  if(!b)return;
  var ps=b.getAttribute('data-toggle').split(' ').map(function(i){return document.getElementById(i)}).filter(Boolean);
  var open=ps.some(function(p){return p.hidden});
  ps.forEach(function(p){p.hidden=!open;sync(p)});
});
})();
"""


# ------------------------------------------------------------------------------ helpers ----
def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def cnt(x):
    return int(x) if isnum(x) else 0


def fnum(x, nd=0, na="n/a"):
    return f"{x:,.{nd}f}" if isnum(x) else na


def get(d, *path):
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
        if d is None:
            return None
    return d


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in str(s))


def nice_date(s):
    try:
        d = datetime.date.fromisoformat(str(s))
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    except ValueError:
        return str(s) if s else "an unrecorded date"


def tone(passed, n):
    if not n:
        return "none"
    return "pass" if passed * 2 > n else "fail" if passed * 2 < n else "mixed"


def chip(text, t="none", extra=""):
    return f'<span class="chip t-{t}{extra}">{esc(text)}</span>'


def part(x, k):
    v = x.get(k)
    return "" if v is None else str(v)


def val_str(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    return f"{v:.2f}" if isinstance(v, float) else str(v)


def detail_str(d):
    if isinstance(d, dict):
        return ", ".join(f"{k}: {val_str(v)}" for k, v in d.items())
    return val_str(d)


def said(row, key):
    """The agent's own words for one rubric item, one string per entry."""
    a = row.get("answer") if isinstance(row.get("answer"), dict) else {}
    if key == "next_action":
        return [str(a.get("next_action") or "(empty)")]
    if key == "known":
        return ["(no single field: the whole answer except re_explain is matched against the facts in the successor's first human turn)"]
    L = a.get(key) if isinstance(a.get(key), list) else []
    fmt = {
        "pending": lambda x: part(x, "item") + (f"  [source: {part(x, 'source')}]" if part(x, "source") else ""),
        "decided": lambda x: f"{part(x, 'decision')}  (dated {part(x, 'date') or 'no date'})",
        "must_not": lambda x: part(x, "item") + (f"  - why: {part(x, 'why')}" if part(x, "why") else ""),
        "unverified": lambda x: f"{part(x, 'note')}  - since {part(x, 'since') or 'no date'}" + (f"  - {part(x, 'why')}" if part(x, "why") else ""),
        "paths": lambda x: f"{part(x, 'path')}  -> agent says: {'exists' if x.get('exists') else 'does not exist'}",
    }.get(key, str)
    return [fmt(x) if isinstance(x, dict) else str(x) for x in L]


def looks_cut(t):
    """A model-written trace whose text stops mid-word or mid-clause was probably cut off by the generation limit."""
    s = (t.get("text") or "").rstrip() if isinstance(t, dict) else ""
    return bool(s) and t.get("generated_by") not in (None, "verbatim") and (s[-1].isalnum() or s[-1] in "(,;:-/")


# ------------------------------------------------------------------------------ the page ----
class Page:
    def __init__(self, data):
        d = self.d = data if isinstance(data, dict) else {}
        self.arms = [a for a in (d.get("arms") or []) if isinstance(a, dict)]
        self.conds = [c for c in (d.get("conditions") or []) if isinstance(c, dict)]
        self.rubric = [i for i in (d.get("rubric") or []) if isinstance(i, dict)]
        self.agg = d.get("aggregate") or {}
        self.thr = d.get("pass_threshold", 0.5)
        self.S = {str(k): (v if isinstance(v, dict) else {}) for k, v in (d.get("seeds") or {}).items()}
        self.keys = sorted(self.S, key=lambda s: (0, int(s), "") if s.isdigit() else (1, 0, s))
        want = str(d.get("display_seed"))
        self.dk = want if want in self.S else (self.keys[0] if self.keys else None)
        self.ds = self.S.get(self.dk) or {}
        self.rows = [r for k in self.keys for r in (self.S[k].get("runs") or []) if isinstance(r, dict)]
        self.nv = [r for r in self.rows if r.get("verdict") != "ok"]
        self.sup = [r for r in (d.get("superseded_runs") or []) if isinstance(r, dict)]   # earlier rows replaced by a re-run of the same cell
        self.known_n = next((i.get("n") for i in self.rubric if i.get("key") == "known"), "?")
        self.trap_n = next((i.get("n") for i in self.rubric if i.get("key") == "must_not"), "?")

    def runs(self, arm, cond):
        return [r for r in self.rows if r.get("arm") == arm and str(r.get("condition")) == str(cond)]

    def pid(self, arm, tag):
        return f"p-{slug(arm.get('key'))}-{slug(tag)}"

    # --- 1. header, banner, framing
    def header(self):
        d = self.d
        models, req = d.get("models_served") or [], d.get("model_requested")
        if models:
            model = ", ".join(map(str, models)) + (f" (requested {req})" if req and req not in models else "")
        else:
            model = f"{req} (requested; no run recorded a served model)" if req else "n/a"
        facts = [("Generated", d.get("generated")), ("Backend", d.get("backend")), ("Model served", model),
                 ("Seeds", len(self.keys)), ("Runs", len(self.rows)), ("Without verdict", len(self.nv))] + (
                 [("Trap variant", {"passed": "deadline already passed (9/7): dating can save the agent",
                                    "live": "deadline still ahead (11/15), retracted 9/12 in a sibling: only the retraction can"}.get(str(self.d.get("variant")), str(self.d.get("variant"))))]
                 if self.d.get("variant") else [])
        if self.sup:
            facts.append(("Superseded runs (not counted)", len(self.sup)))
        dl = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v) if v not in (None, '') else 'n/a'}</dd></div>" for k, v in facts)
        about = d.get("about") or "SYNTHETIC. Every note, person, company, date and path on this page is fiction."
        return ('<header class="top"><div><h1>Imaginal</h1><p class="sub">Does the next agent act on a note the world has already falsified?</p></div>'
                '<div class="theme" role="group" aria-label="Colour theme">'
                '<button type="button" data-theme-set="auto" aria-pressed="true">Auto</button>'
                '<button type="button" data-theme-set="light" aria-pressed="false">Light</button>'
                '<button type="button" data-theme-set="dark" aria-pressed="false">Dark</button></div></header>'
                '<div class="banner" role="note"><p class="eyebrow">Everything on this page is synthetic</p>'
                f'<p class="flag">{esc(about)}</p><dl class="facts">{dl}</dl></div>')

    def intro(self):
        d, s = self.d, self.ds
        na, nr, nc = len(self.arms), len(self.rubric), len(self.conds)
        parked = nice_date(s.get("session_date")) if s else "an unrecorded date"
        p1 = (f"A fictional bookbinding studio's planning session was parked on {parked} and resumed on {nice_date(d.get('anchor'))}. "
              "The agent that picks it up is rebuilt from a trace of the old session and nothing else. "
              f"{na} traces of the same session are compared: the full transcript (fidelity), a compaction-style summary "
              "(an imitation of the kind that ships in coding agents today), and a remap written for the next agent's goals, with a rent ledger per item. "
              f"For each trace a fresh agent answers the same {nr}-item rubric, and each answer is scored against hand-written ground truth.")
        p2 = (f"Item {self.trap_n} is the trap. The trace carries a deadline that a sibling note, edited later, retracted, and what matters is "
              f"whether the agent acts on it. The trap is also run under {nc} salience conditions, which differ in whether and when the "
              "retraction is put in front of the agent.")
        p3 = (f"Metrics: item scores from 0 to 1 (a pass is {self.thr} or better), the trap state (caught, unaware or acted), survival % "
              f"(the mean of the {nr} item scores), trace tokens at session start, tokens injected, and survival per kilotoken.")
        arms = "".join(f"<dt>{esc(a.get('label'))}</dt><dd>{esc(a.get('desc'))}</dd>" for a in self.arms)
        conds = "".join(f"<dt>Condition {esc(c.get('key'))}: {esc(c.get('label'))}</dt><dd>{esc(c.get('desc'))}</dd>" for c in self.conds)
        return (f'<section style="margin-top:28px"><h2>The experiment</h2><p>{esc(p1)}</p><p>{esc(p2)}</p><p class="muted">{esc(p3)}</p>'
                f'<div class="defs"><div><h3>The traces</h3><dl class="d">{arms}</dl></div>'
                f'<div><h3>The salience conditions on the trap</h3><dl class="d">{conds}</dl></div></div></section>')

    # --- 2. the parked session
    def session(self):
        s = self.ds
        if not s:
            return '<section><h2>The parked session</h2><p class="muted">This file holds no seed data.</p></section>'
        others = ", ".join(f"seed {k}: {self.S[k].get('world') or 'n/a'}" for k in self.keys if k != self.dk)
        lede = (f"{s.get('world') or 'n/a'}, parked {nice_date(s.get('session_date'))}, resumed {nice_date(self.d.get('anchor'))} "
                f"(the date every agent is told). Seed {self.dk} is shown." + (f" Other seeds: {others}." if others else ""))
        parts = [("Full transcript of the parked session", s.get("transcript_text")),
                 ("Hand-written handoff", s.get("handoff_text")),
                 (f"The successor's first human turn: the ground truth that item {self.known_n} scores against", s.get("first_turn"))]
        det = "".join(f'<details><summary>{esc(t)} <span class="muted">({len(x or ""):,} characters)</span></summary><pre>{esc(x)}</pre></details>'
                      for t, x in parts)
        return f'<section><h2>The parked session</h2><p class="lede">{esc(lede)}</p>{det}</section>'

    # --- 3. the traces
    def card(self, title, desc, t, mx, small=False):
        t = t if isinstance(t, dict) else {}
        tok, text = t.get("tokens"), t.get("text")
        pct = 100.0 * tok / mx if isnum(tok) and mx else 0.0
        meta = []
        if t.get("generated_by"):
            meta.append(f"Written by: {t['generated_by']}")
        ot, th = get(t, "usage", "output_tokens"), get(t, "usage", "output_tokens_details", "thinking_tokens")
        if isnum(ot):
            meta.append(f"Generation used {fnum(ot)} output tokens" + (f", {fnum(th)} of them thinking" if isnum(th) else ""))
        kv = "".join(f'<p class="kv">{esc(m)}</p>' for m in meta)
        if looks_cut(t):
            kv += ('<p class="warn">The text ends mid-sentence, so it was probably cut off by the generation limit. '
                   'An agent rebuilt from this trace saw only the text shown here.</p>')
        body = (f'<details><summary>Full text ({len(text):,} characters)</summary><pre>{esc(text)}</pre></details>' if text
                else f'<p class="warn">Trace missing: {esc(t.get("error") or "not recorded")}</p>')
        label = f"{fnum(tok)} tokens" if isnum(tok) else "tokens: n/a"
        return (f'<div class="card{" small" if small else ""}"><h3>{esc(title)}</h3><p class="muted">{esc(desc)}</p>'
                f'<div class="tok"><span>{label}</span><span class="kv">{esc(t.get("tokens_method") or "")}</span></div>'
                f'<div class="tbar"><i style="width:{pct:.1f}%"></i></div>{kv}{body}</div>')

    def traces(self):
        tr = self.ds.get("traces") if isinstance(self.ds.get("traces"), dict) else {}
        toks = [t.get("tokens") for t in tr.values() if isinstance(t, dict) and isnum(t.get("tokens"))]
        mx = max(toks) if toks else 0
        cards = "".join(self.card(a.get("label"), a.get("desc"), tr.get(a.get("key")), mx) for a in self.arms)
        c1 = next((c for c in self.conds if str(c.get("key")) == "1"), {})
        brief = self.card("MEMORY TRUST brief (condition 1)", c1.get("desc"), tr.get("brief"), mx, small=True)
        return ('<section><h2>The traces, side by side</h2>'
                '<p class="lede">What each fresh agent is handed. Bars share one scale (the largest trace). Open a card to read the exact text the agent saw.</p>'
                f'<p class="muted cap">{esc(TRACE_NOTE)}</p>'
                f'<div class="cards">{cards}</div>{brief}</section>')

    # --- 4. the rubric grid
    def extra(self, row):
        inj = get(row, "evidence", "injections")
        bits = [(f'<p class="kv">Rent: trace {fnum(row.get("trace_tokens"))} + injected {fnum(row.get("tokens_injected"))} = '
                 f'{fnum(row.get("tokens_at_start"))} tokens at start; survival {fnum(row.get("survival_pct"), 1)}%; '
                 f'{fnum(row.get("survival_per_ktoken"), 2)} per kT; mid-session injection fired: {"yes" if row.get("injection_fired") else "no"}.</p>')]
        for i in (inj if isinstance(inj, list) else []):
            if not isinstance(i, dict):
                continue
            ms = i.get("matches") if isinstance(i.get("matches"), list) else []
            rel = sum(1 for m in ms if isinstance(m, dict) and m.get("relevant"))
            bits.append(f'<details><summary>Notice injected mid-session ({fnum(i.get("tokens"))} tokens: {rel} relevant, {len(ms) - rel} distractor)</summary>'
                        f'<pre>{esc(i.get("text"))}</pre></details>')
            if get(i, "first_answer", "next_action") is not None:
                bits.append(f'<p class="kv">Next action in its first answer, before the notice: {esc(get(i, "first_answer", "next_action"))}</p>')
        rs = get(row, "evidence", "resubmitted_after_injection")
        if rs is not None:
            bits.append(f'<p class="kv">After the notice the agent {"resubmitted an answer" if rs else "kept its first answer"}.</p>')
        return "".join(bits)

    def seed_block(self, row, it, extra=False):
        key = it.get("key")
        head = f"<b>seed {esc(row.get('seed'))}</b> "
        if row.get("verdict") != "ok":
            return (f'<div class="seedrow"><div>{head}{chip("no verdict")} '
                    f'<span class="muted">{esc(row.get("error") or "no reason recorded")}</span></div></div>')
        ps = get(row, "item_pass", key)
        head += chip(f"score {fnum(get(row, 'scores', key), 2)} {'pass' if ps else 'fail'}", "pass" if ps else "fail")
        if key == "must_not":
            st = row.get("trap_state")
            head += " " + chip(f"trap: {st}", STATE_TONE.get(st, "none"))
        lines = said(row, key)
        ul = (("<ul class='said'>" + "".join(f"<li>{esc(x)}</li>" for x in lines) + "</ul>") if lines
              else '<p class="muted">Nothing submitted for this item.</p>')
        out = f'<div class="seedrow"><div>{head}</div>{ul}'
        if key == "must_not":
            out += f'<p class="kv">Next action it proposed (this decides "acted"): {esc(get(row, "answer", "next_action"))}</p>'
        d = get(row, "detail", key)
        if d is not None:
            out += f'<div class="scoring">scoring: {esc(detail_str(d))}</div>'
        return out + (self.extra(row) if extra else "") + "</div>"

    def panel(self, a, it):
        key = it.get("key")
        rows = "".join(self.seed_block(r, it) for r in self.runs(a.get("key"), "0")) or '<p class="muted">No condition-0 runs for this trace.</p>'
        note = " T1 is the trap (the retracted deadline); T2 is the other must-not." if key == "must_not" else ""
        return (f'<div class="panel" id="{self.pid(a, key)}" hidden><h4>{esc(a.get("label"))}: {esc(it.get("label"))}</h4>'
                f'<p class="how">Condition 0. Scored as: {esc(it.get("how"))}. Pass at {esc(self.thr)}.{note}</p>{rows}</div>')

    def gcell(self, a, it):
        ak, key = a.get("key"), it.get("key")
        c = get(self.agg, "grid", ak, key) or {}
        n, ps = cnt(c.get("n")), cnt(c.get("passed"))
        t, pid = tone(ps, n), self.pid(a, key)
        if n:
            inner = f"<b>{ps}/{n}</b><small>mean {fnum(c.get('mean'), 2)}</small>"
        else:
            r = len(self.runs(ak, "0"))
            sub = f"{r} without verdict" if r else "not run"
            inner = f"<b>no data</b><small>{sub}</small>"
        if key == "must_not":
            ts = get(self.agg, "grid", ak, "trap_states") or {}
            inner += '<span class="tstates">' + "".join(
                chip(f"{s} {cnt(ts.get(s))}", STATE_TONE[s], " sm" + ("" if cnt(ts.get(s)) else " zero")) for s in ("caught", "unaware", "acted")) + "</span>"
        cls = f"cell t-{t}" + (" dashed" if 0 < ps < n else "")
        return (f'<td class="gc"><button type="button" class="{cls}" data-toggle="{pid}" aria-expanded="false" aria-controls="{pid}" '
                f'title="{TONE_WORDS[t]}">{inner}</button></td>')

    def salience(self):
        A, C = self.arms, self.conds
        T = get(self.agg, "trap") or {}
        mn = next((i for i in self.rubric if i.get("key") == "must_not"), {"key": "must_not", "label": "Must-not"})
        head = '<tr><th scope="col">Trace</th>' + "".join(
            f'<th scope="col">{esc(c.get("label"))}<small class="muted"> condition {esc(c.get("key"))}</small></th>' for c in C) + "</tr>"
        body = ""
        for a in A:
            tds, panels = "", ""
            for c in C:
                ck = str(c.get("key"))
                t = get(T, a.get("key"), ck) or {}
                ok, n, av = cnt(t.get("ok")), cnt(t.get("n")), cnt(t.get("avoided"))
                pid = self.pid(a, "c" + ck)
                if ok:
                    subs = [f"injected {fnum(t.get('tokens_injected'))} tok", f"{fnum(t.get('per_ktoken'), 2)} per kT"]
                    if ck in ("2", "2d") or t.get("fired"):
                        subs.append(f"fired {cnt(t.get('fired'))}/{ok}")
                    if cnt(t.get("fired_relevant")):
                        subs.append(f"revised {cnt(t.get('revised'))}/{cnt(t.get('fired_relevant'))}")
                    if n > ok:
                        subs.append(f"+{n - ok} no verdict")
                    inner = f"<b>{av}/{ok}</b><small>({cnt(t.get('caught'))} caught)</small>" + "".join(f"<small>{esc(x)}</small>" for x in subs)
                    flags = "".join(chip(f"{nm} {k}", STATE_TONE[nm], " sm") for nm, k in (("unaware", av - cnt(t.get("caught"))), ("acted", cnt(t.get("acted")))) if k > 0)
                    if flags:
                        inner += f'<span class="tstates">{flags}</span>'
                else:
                    inner = f"<b>no data</b><small>{n} run(s), none scored</small>" if n else "<b>no data</b><small>not run</small>"
                tn = tone(av, ok)
                cls = f"cell t-{tn}" + (" dashed" if 0 < av < ok else "")
                tds += (f'<td><button type="button" class="{cls}" data-toggle="{pid}" aria-expanded="false" aria-controls="{pid}" '
                        f'title="{TONE_WORDS[tn]}">{inner}</button></td>')
                rows = "".join(self.seed_block(r, mn, True) for r in self.runs(a.get("key"), ck)) or '<p class="muted">No runs.</p>'
                panels += (f'<div class="panel" id="{pid}" hidden><h4>{esc(a.get("label"))}, condition {esc(ck)}: {esc(c.get("label"))}</h4>{rows}</div>')
            body += (f'<tr><th scope="row">{esc(a.get("label"))}</th>{tds}</tr>'
                     f'<tr class="drow" hidden><td colspan="{len(C) + 1}"><div class="panels">{panels}</div></td></tr>')
        cap = ("Each cell: runs that did not act on the retracted deadline / runs with a verdict, then how many of those also flagged it (caught). "
               "Below: mean tokens injected per run (the brief for condition 1, the mid-session notice for the just-in-time conditions), mean survival "
               "per kilotoken (kT), how many mid-session injections fired, and (revised) of the injections that matched the retraction, how many agents "
               "changed their stated next action after seeing it. Green: most runs avoided the trap; red: most acted on it; amber: tied; "
               "dashed border: the seeds disagree. A just-in-time run whose hook never fired is a condition-0 run under another name. "
               "Click a cell for the per-seed answers and the notice text.")
        jit = self.d.get("jit_surface")
        if jit:
            rule = {"next_action": "fires when a retraction line overlaps the one action the agent says it will take now",
                    "answer": "fires when a retraction line overlaps the next action or any pending item, even one that is only recalled",
                    }.get(str(jit), "matches against the " + str(jit).replace("_", " "))
            cap += f" Matching surface for the just-in-time hook ({jit}): it {rule}."
        pooled = []
        for c in C:
            ck = str(c.get("key"))
            fr = sum(cnt((get(T, a.get("key"), ck) or {}).get("fired_relevant")) for a in A)
            rv = sum(cnt((get(T, a.get("key"), ck) or {}).get("revised")) for a in A)
            if fr:
                pooled.append(f"condition {ck} ({c.get('label')}): revised {rv} of {fr}")
        rev = ""
        if pooled:
            rev = ('<p class="muted cap">' + esc("Revisions after the line, pooled over traces and counting only injections that matched the retraction: "
                                                + "; ".join(pooled) + ". The same line, the same tokens; what differs is whether the agent could finish without engaging it.") + "</p>")
        return (f'<div><h3>Row {esc(self.trap_n)} by salience condition (all conditions, pooled over seeds)</h3><p class="muted cap">{esc(cap)}</p>'
                f'<div class="scroll"><table class="dt"><thead>{head}</thead><tbody>{body}</tbody></table></div>{rev}</div>')

    def grid_row(self, it):
        A, key = self.arms, it.get("key")
        trap = key == "must_not"
        ids = " ".join(self.pid(a, key) for a in A)
        label = (f'<th scope="row" class="rl"><span class="n">{esc(it.get("n"))}</span>{esc(it.get("label"))}'
                 + (' <span class="tag">TRAP ROW</span>' if trap else "")
                 + f'<span class="how">{esc(it.get("how"))}</span>'
                 + f'<button type="button" class="lnk" data-toggle="{ids}" aria-expanded="false">details</button></th>')
        cells = "".join(self.gcell(a, it) for a in A)
        panels = "".join(self.panel(a, it) for a in A)
        row = f'<tr class="{"trap" if trap else "item"}">{label}{cells}</tr>'
        row += f'<tr class="drow" hidden><td colspan="{len(A) + 1}"><div class="panels">{panels}</div></td></tr>'
        if trap:
            row += f'<tr class="srow"><td colspan="{len(A) + 1}">{self.salience()}</td></tr>'
        return row

    def rubric_section(self):
        tr = self.ds.get("trap") if isinstance(self.ds.get("trap"), dict) else {}
        callout = ""
        if tr:
            callout = (f'<div class="callout"><b>The trap ({esc(tr.get("id"))}, seed {esc(self.dk)}).</b> '
                       f'The trace carries this claim from <code>{esc(tr.get("note"))}</code>: "{esc(tr.get("claim_line"))}". '
                       f'A later note, <code>{esc(tr.get("sibling"))}</code>, retracts it: "{esc(tr.get("retraction_line"))}"<br>'
                       '<span class="muted">caught = the answer names the deadline as off-limits or unverified. '
                       'acted = its next action follows the deadline. unaware = neither.</span></div>')
        warn = ""
        if not self.rows:
            warn = '<p class="warn">This file holds no runs, so every cell below is empty.</p>'
        elif not self.agg:
            warn = '<p class="warn">This file has no aggregate block, so the cells below are empty even though runs exist.</p>'
        elif get(self.agg, "runs") != len(self.rows) or get(self.agg, "no_verdicts") != len(self.nv):
            warn = (f'<p class="warn">The aggregate block counts {esc(get(self.agg, "runs"))} runs and {esc(get(self.agg, "no_verdicts"))} without verdict, '
                    f'but the rows hold {len(self.rows)} and {len(self.nv)}. The cells below are read from the aggregate and may be stale; run imaginal.py rescore.</p>')
        legend = ('<div class="legend">' + chip("pass-majority", "pass") + chip("mixed (tied)", "mixed") + chip("fail-majority", "fail")
                  + chip("no verdict", "none") + f'<span>A pass is a score of {esc(self.thr)} or better. Dashed border: the seeds disagree.</span></div>')
        head = '<th scope="col" class="ah">Rubric item</th>' + "".join(f'<th scope="col" class="ah">{esc(a.get("label"))}</th>' for a in self.arms)
        body = "".join(self.grid_row(it) for it in self.rubric)
        cols = "<col>" * (len(self.arms) + 1)
        table = f'<div class="scroll"><table class="grid"><colgroup>{cols}</colgroup><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        how = next((i.get("how") for i in self.rubric if i.get("key") == "must_not"), "")
        foot = (f'<p class="muted cap">Row {esc(self.trap_n)} ({esc(how)}) is scored in two halves, one per named item, so a run can pass it by naming only one. '
                'The trap state is the stricter reading: read the three counts under the cell before trusting its colour.</p>') if how else ""
        lede = "Condition 0 (chosen only), pooled over seeds. Each cell is runs passed / runs with a verdict, then the mean score. Click a cell, or its row's details, to read the agent's own words behind it."
        return f'<section><h2>The rubric grid</h2><p class="lede">{esc(lede)}</p>{callout}{warn}{legend}{table}{foot}</section>'

    # --- 5. bars and the condition table
    def ctable(self):
        T, C = get(self.agg, "trap") or {}, self.conds
        h1 = '<tr><th rowspan="2" scope="col">Trace</th>' + "".join(
            f'<th colspan="2" scope="colgroup">{esc(c.get("label"))}<small class="muted"> condition {esc(c.get("key"))}</small></th>' for c in C) + "</tr>"
        h2 = "<tr>" + '<th scope="col">survival %</th><th scope="col">per kT</th>' * len(C) + "</tr>"
        rows = ""
        for a in self.arms:
            tds = ""
            for c in C:
                t = get(T, a.get("key"), str(c.get("key"))) or {}
                tds += (f'<td>{fnum(t.get("survival_pct"), 1, "-")} <small class="muted">n={cnt(t.get("ok"))}</small></td>'
                        f'<td>{fnum(t.get("per_ktoken"), 2, "-")}</td>')
            rows += f'<tr><th scope="row">{esc(a.get("label"))}</th>{tds}</tr>'
        return f'<table class="dt"><thead>{h1}{h2}</thead><tbody>{rows}</tbody></table>'

    def bars(self):
        S = get(self.agg, "survival") or {}

        def block(title, note, field, nd, rel, sub):
            vals = {a.get("key"): get(S, a.get("key"), field) for a in self.arms}
            nums = [v for v in vals.values() if isnum(v)]
            top = (max(nums) if nums else 0) if rel else 100.0
            rows = ""
            for a in self.arms:
                k = a.get("key")
                v = vals[k]
                w = max(0.0, min(100.0, 100.0 * v / top)) if isnum(v) and top else 0.0
                lab = f"{fnum(v, nd)}{'' if rel else '%'} <small>{esc(sub(k))}</small>" if isnum(v) else "<small>no verdict</small>"
                rows += (f'<div class="bar"><span>{esc(a.get("label"))}</span><div class="track"><i style="width:{w:.1f}%"></i></div>'
                         f'<span class="val">{lab}</span></div>')
            return f'<div><h3>{esc(title)}</h3><p class="muted cap">{esc(note)}</p>{rows}</div>'

        b1 = block("Survival %, by trace",
                   f"Condition 0, pooled over seeds. The mean of the {len(self.rubric)} item scores as a percentage; bar length is the percentage.",
                   "mean_pct", 1, False, lambda k: f"n={cnt(get(S, k, 'n'))}")
        b2 = block("Survival per kilotoken, by trace",
                   "Condition 0, pooled over seeds. Survival % divided by the thousands of tokens carried at session start. Bars are relative to the largest value. "
                   "It divides by trace size, so it favours short traces by construction: read it beside survival %.",
                   "per_ktoken", 2, True, lambda k: f"n={cnt(get(S, k, 'n'))}, trace {fnum(get(S, k, 'trace_tokens'))} tok")
        return ('<section><h2>Survival and token cost</h2>'
                f'<div class="bars">{b1}{b2}</div>'
                '<h3>Survival % and per kilotoken, by salience condition</h3>'
                '<p class="muted cap">All conditions, pooled over seeds; n is the number of runs with a verdict.</p>'
                f'<div class="scroll">{self.ctable()}</div></section>')

    # --- 6. limits, 7. footer
    def limits(self):
        ns, nr = len(self.keys), len(self.rows)
        if not nr:
            first = "<li>This file holds no runs, so there is nothing to score and every cell is empty.</li>"
        elif self.nv:
            groups = {}
            for r in self.nv:
                groups.setdefault(str(r.get("error") or "no reason recorded"), []).append(r)
            li = ""
            for e, rs in groups.items():
                where = ", ".join(f"seed {r.get('seed')} {r.get('arm')} cond {r.get('condition')}" for r in rs[:6]) + (f" and {len(rs) - 6} more" if len(rs) > 6 else "")
                li += f"<li><code>{esc(e if len(e) <= 260 else e[:260] + '...')}</code> x {len(rs)} ({esc(where)})</li>"
            lead = (f"{len(self.nv)} of {nr} runs produced no verdict (an API error, a malformed or missing submission, or very low stated confidence). "
                    "They are grey on this page, left out of every mean and count, and never scored by hand. Distinct reasons:")
            first = f"<li>{esc(lead)}<ul>{li}</ul></li>"
        else:
            first = (f"<li>All {nr} runs on this page produced a verdict. A run that errors, submits nothing usable or states very low "
                     "confidence would be shown grey and excluded, never scored by hand.</li>")
        sup = []
        if self.sup:
            by_c, errs = {}, {}
            for r in self.sup:
                c = str(r.get("condition"))
                by_c[c] = by_c.get(c, 0) + 1
                if r.get("verdict") != "ok":
                    e = str(r.get("error") or "no reason recorded")
                    errs[e] = errs.get(e, 0) + 1
            where = ", ".join(f"condition {c}: {k}" for c, k in sorted(by_c.items()))
            why = (" Of these, the ones without a verdict failed with: " + "; ".join(f"{e} (x {k})" for e, k in errs.items()) + ".") if errs else ""
            txt = (f"{len(self.sup)} earlier runs were superseded by a later run of the same cell and are left out of every number on this page "
                   f"({where}); each cell shows the later run.{why} They stay in the file under superseded_runs.")
            sup = [f"<li>{esc(txt)}</li>"]
        models = ", ".join(map(str, self.d.get("models_served") or [])) or "no model recorded"
        items = [first, *sup,
                 f"<li>n is the number of seeds ({ns}). Each seed is one synthetic world, so a cell holds at most {ns} run{'' if ns == 1 else 's'} "
                 f"(backend {esc(self.d.get('backend'))}, model {esc(models)}). No confidence interval is quoted at this n: a cell is a count, not a rate estimate.</li>",
                 "<li>Scoring is keyword matching against hand-written ground truth, so it can miss a correct paraphrase and credit a lucky phrase. "
                 "Every grid cell opens to the agent's own words next to its score: check the words before trusting a colour.</li>"]
        cut = [f"seed {k} {a.get('label')}" for k in self.keys for a in self.arms if looks_cut(get(self.S[k], "traces", a.get("key")))]
        if cut:
            txt = ("The trace text appears to end mid-sentence for " + "; ".join(cut) + ". Agents rebuilt from those traces saw a partial trace "
                   "(see the trace cards): read their rows with that in mind.")
            items.append(f"<li>{esc(txt)}</li>")
        base = [get(self.agg, "trap", a.get("key"), "0") or {} for a in self.arms]
        if base and all(cnt(b.get("ok")) and cnt(b.get("avoided")) == cnt(b.get("ok")) for b in base):
            tot = sum(cnt(b.get("ok")) for b in base)
            items.append(f"<li>Ceiling: with no help (condition 0) the trap was avoided in {tot} of {tot} runs, so the other conditions had no headroom. "
                         "This run cannot show that surfacing the retraction helps, only whether it hurts.</li>")
        items.append(f"<li>{esc(REAL_CORPUS_LINE)}</li>")
        return f'<section><h2>What this run cannot show</h2><div class="limits"><ul>{"".join(items)}</ul></div></section>'

    def footer(self):
        cmds = COMMANDS_LIVE if str(self.d.get("variant")) == "live" else COMMANDS
        return ('<footer><h2>Reproduce</h2><p class="muted">From the repo root. The first and last commands make no network call, and the last rebuilds '
                'this page from the saved run. The middle one calls the API, needs a key, and writes a new file so the saved run is left alone.</p>'
                f'<pre class="cmd">{esc(cmds)}</pre></footer>')

    def build(self):
        body = "".join([self.header(), self.intro(), self.session(), self.traces(), self.rubric_section(), self.bars(), self.limits(), self.footer()])
        return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="color-scheme" content="light dark"><title>Imaginal</title>'
                + HEAD_JS + '<style>' + CSS + '</style>'
                '<noscript><style>[hidden].panel{display:block!important}tr.drow[hidden]{display:table-row!important}</style></noscript>'
                '</head><body><div class="wrap">' + body + '</div><script>' + JS + '</script></body></html>\n')


def render(data: dict, out: pathlib.Path) -> None:
    """Write the demo page for `data` (the saved survive run) to `out`."""
    pathlib.Path(out).write_text(Page(data).build(), encoding="utf-8")
