#!/usr/bin/env python3
"""memory-rot-audit: find confident-stale notes in a file-based agent memory.

Read-only. Never edits, moves or deletes anything. Prints a ranked review list.

Signals per note (all heuristic, all explained in SKILL.md):
  horizon   dates the note points AT that have since passed without the note being touched
  absence   claims about something NOT happening (no reply, never arrived, unverified, pending)
  absolute  NEVER / ALWAYS / DEAD / CLOSED style certainty markers, weighted by age
  deadpath  filesystem paths named in the note that no longer exist
  dangling  [[wikilinks]] to notes that do not exist
  flips     RETRACTED / EDIT / FLIP markers = rot that was already caught once
  index     whether the note is reachable from the index file at all

Usage:
  audit.py [MEMORY_DIR] [--index MEMORY.md] [--top N] [--json out.json] [--public] [--today YYYY-MM-DD]
  --public prints corpus-level counts only: no filenames, no note text. Safe to paste anywhere.
"""
import argparse, datetime as dt, json, os, re, sys
from pathlib import Path

MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
RE_ISO   = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
RE_USY   = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\b")
RE_USN   = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")
RE_MON   = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b", re.I)
CUE      = re.compile(r"(by|due|on|until|till|~|≈|since|from|→|as of|verdict|results?|re-?check|rebook|deadline|expires?|ends?|starts?|through|thru|before|after|at|arrives?|landed|sent|posted|opened|closed|paid|call|visit|hearing|filing|renew|ask)\s*$", re.I)
RE_ABS   = re.compile(r"\b(never arrived|no reply|no replies|0 (?:human )?replies|zero replies|silence|not (?:yet )?received|no (?:confirmation|invite|email|answer|response|word)|unverified|unrecorded|not done|unbooked|unsent|pending|waiting on|awaiting|still open|outcome unknown|no action|not applied|never (?:came|landed|showed))\b", re.I)
RE_CERT  = re.compile(r"(\bNEVER\b|\bALWAYS\b|\bDEAD\b|\bCLOSED\b|\bRETIRED\b|\bKILLED\b|\bBANNED\b|\bSETTLED\b|\bRESOLVED\b|\bFINAL\b|🔴|🚨|🛑|\bdo not\b|\bdon't\b|\bnever\b|\balways\b)")
RE_FLIP  = re.compile(r"(RETRACT(?:ED|ION)?|\bEDIT\b|\bFLIP\b|SUPERSEDED|CORRECTION|was wrong|turned out|STALE|OVERTURNED)", re.I)
RE_PATH  = re.compile(r"(?<![\w.])(~/[^\s`'\"\)\]<>,;*…]+|/Users/[^\s`'\"\)\]<>,;*…]+)")
RE_LINK  = re.compile(r"\[\[([^\]|#]+)")
RE_FM    = re.compile(r"^---\n(.*?)\n---\n", re.S)

def parse_frontmatter(text):
    m = RE_FM.match(text)
    fm = {}
    if not m: return fm, text
    for line in m.group(1).splitlines():
        mm = re.match(r"^\s*([A-Za-z_]+):\s*(.*)$", line)
        if mm: fm[mm.group(1)] = mm.group(2).strip().strip('"')
    return fm, text[m.end():]

def fm_modified(fm):
    v = fm.get("modified")
    if not v: return None
    try: return dt.datetime.fromisoformat(v.replace("Z","+00:00")).date()
    except ValueError: return None

def note_modified(path, fm):
    # the filesystem mtime is the last real edit; the frontmatter stamp is only
    # rewritten by the memory tool, so scripted edits leave it behind (measured as drift)
    return dt.date.fromtimestamp(path.stat().st_mtime)

def dates_in(text, default_year):
    out = []
    for m in RE_ISO.finditer(text):
        try: out.append(dt.date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError: pass
    for m in RE_USY.finditer(text):
        y = int(m[3]); y = y + 2000 if y < 100 else y
        try: out.append(dt.date(y, int(m[1]), int(m[2])))
        except ValueError: pass
    for m in RE_USN.finditer(text):
        # no year: only count when a scheduling cue precedes it, else it is a ratio ("3/6 rejected")
        if not CUE.search(text[max(0, m.start()-28):m.start()]): continue
        try: out.append(dt.date(default_year, int(m[1]), int(m[2])))
        except ValueError: pass
    for m in RE_MON.finditer(text):
        mon = MONTHS.index(m[1][:3].lower()) + 1
        y = int(m[3]) if m[3] else default_year
        try: out.append(dt.date(y, mon, int(m[2])))
        except ValueError: pass
    return out

def path_exists(p):
    p = os.path.expanduser(p.rstrip(".:"))
    if any(c in p for c in "<>{}$[\\"): return None   # templated or escaped, not checkable
    if os.path.exists(p): return True
    parent, leaf = os.path.split(p)
    if not leaf or not os.path.isdir(parent): return False if os.path.isdir(os.path.dirname(parent) or "/") else None
    try:
        if any(e.startswith(leaf) for e in os.listdir(parent)): return None  # cut at a space in the real name
    except OSError:
        return None
    return False

def audit(mem_dir, index_path, today):
    files = sorted(Path(mem_dir).glob("*.md"))
    files = [f for f in files if f.name != "MEMORY.md"]
    slugs = set()
    for f in files:
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
        for s in (fm.get("name",""), f.stem):
            if s: slugs.add(s.replace("_","-").lower())
    indexed = set()
    index_missing = []
    if index_path and Path(index_path).exists():
        for m in re.finditer(r"\]\(([^)]+\.md)\)", Path(index_path).read_text(encoding="utf-8", errors="replace")):
            tgt = m.group(1).split("/")[-1]
            indexed.add(tgt)
            if not (Path(mem_dir) / tgt).exists(): index_missing.append(tgt)
    rows = []
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(raw)
        mod = note_modified(f, fm)
        age = (today - mod).days
        ds = dates_in(raw, today.year)
        horizon = sorted({d for d in ds if mod < d <= today})
        absence = RE_ABS.findall(body)
        cert = RE_CERT.findall(body)
        flips = RE_FLIP.findall(body)
        paths = sorted(set(RE_PATH.findall(body)))
        dead = [p for p in paths if path_exists(p) is False]
        links = sorted(set(RE_LINK.findall(body)))
        dangling = [l for l in links if l.strip().replace("_","-").lower() not in slugs]
        age_w = 1.0 if age <= 30 else 1.5 if age <= 90 else 2.0
        score = (min(len(horizon),3)*3 + min(len(absence),3)*2 + min(len(cert),4)*0.5) * age_w \
                + len(dead)*2 + len(dangling)*1
        fmd = fm_modified(fm)
        drift = (mod - fmd).days if fmd else None
        rows.append(dict(file=f.name, type=fm.get("type",""), modified=mod.isoformat(), age_days=age, stamp_drift_days=drift,
                         horizon=[d.isoformat() for d in horizon], absence=len(absence), absolute=len(cert),
                         flips=len(flips), dead_paths=dead, dangling=dangling,
                         indexed=f.name in indexed, score=round(score,1),
                         desc=fm.get("description","")[:110]))
    rows.sort(key=lambda r: (-r["score"], -r["age_days"]))
    stats = dict(
        today=today.isoformat(), notes=len(rows),
        indexed=sum(r["indexed"] for r in rows), unindexed=sum(not r["indexed"] for r in rows),
        index_entries_missing_file=len(index_missing),
        age_buckets={"<=30d":sum(r["age_days"]<=30 for r in rows),"31-90d":sum(30<r["age_days"]<=90 for r in rows),">90d":sum(r["age_days"]>90 for r in rows)},
        notes_with_passed_horizon=sum(bool(r["horizon"]) for r in rows),
        passed_horizon_dates=sum(len(r["horizon"]) for r in rows),
        notes_with_absence_claims=sum(r["absence"]>0 for r in rows),
        absence_claims_total=sum(r["absence"] for r in rows),
        absence_claims_older_than_30d=sum(r["absence"] for r in rows if r["age_days"]>30),
        notes_with_absolutes=sum(r["absolute"]>0 for r in rows),
        absolutes_total=sum(r["absolute"] for r in rows),
        absolutes_in_notes_older_than_90d=sum(r["absolute"] for r in rows if r["age_days"]>90),
        notes_with_flip_markers=sum(r["flips"]>0 for r in rows), flip_markers_total=sum(r["flips"] for r in rows),
        notes_with_dead_paths=sum(bool(r["dead_paths"]) for r in rows), dead_paths_total=sum(len(r["dead_paths"]) for r in rows),
        notes_with_dangling_links=sum(bool(r["dangling"]) for r in rows), dangling_links_total=sum(len(r["dangling"]) for r in rows),
        high_risk_notes_score_ge_8=sum(r["score"]>=8 for r in rows),
        stamped_notes=sum(r["stamp_drift_days"] is not None for r in rows),
        stamped_notes_edited_after_stamp_7d_plus=sum(1 for r in rows if r["stamp_drift_days"] is not None and r["stamp_drift_days"]>7),
        max_stamp_drift_days=max([r["stamp_drift_days"] or 0 for r in rows] or [0]),
    )
    stats["_unindexed_files"] = [r["file"] for r in rows if not r["indexed"]]
    return rows, stats, index_missing

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mem_dir", nargs="?", default=os.environ.get("MEMORY_DIR", "."),
                    help="directory of one-fact-per-file Markdown notes (default: $MEMORY_DIR or .)")
    ap.add_argument("--index", default=None)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--json", default=None)
    ap.add_argument("--public", action="store_true")
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    index = a.index or os.path.join(a.mem_dir, "MEMORY.md")
    rows, stats, index_missing = audit(a.mem_dir, index, today)
    print("# memory-rot-audit  (read-only)")
    for k, v in stats.items():
        if k.startswith("_") and a.public: continue
        print(f"{k}: {v}")
    if a.public:
        return
    if index_missing: print("\nindex entries pointing at missing files:", index_missing)
    print(f"\n## top {a.top} review candidates  (score = horizon*3 + absence*2 + absolute*0.5, x age weight, + dead paths*2 + dangling*1)")
    print(f"{'score':>5} {'age':>4} {'hz':>2} {'ab':>2} {'cf':>2} {'fl':>2} {'dp':>2} {'dl':>2} idx file")
    for r in rows[:a.top]:
        print(f"{r['score']:>5} {r['age_days']:>4} {len(r['horizon']):>2} {r['absence']:>2} {r['absolute']:>2} {r['flips']:>2} {len(r['dead_paths']):>2} {len(r['dangling']):>2} {'y' if r['indexed'] else 'n':>3} {r['file']}")
        if r["horizon"]: print(f"{'':>34}passed horizons: {', '.join(r['horizon'][:4])}")
        if r["dead_paths"]: print(f"{'':>34}dead paths: {', '.join(r['dead_paths'][:3])}")
        if r["dangling"]: print(f"{'':>34}dangling: {', '.join(r['dangling'][:4])}")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(stats=stats, rows=rows, index_missing=index_missing), indent=1))
        print(f"\njson -> {a.json}")

if __name__ == "__main__":
    main()
