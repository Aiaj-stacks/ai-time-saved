#!/usr/bin/env python3
"""
AI Time-Saved Tracker  (v2 - full dashboard)
===========================================
Offline, zero-dependency tracker for hours saved by using Hermes as your AI
assistant. Single source of truth: a JSONL log. This script logs entries,
prints summaries, and regenerates a self-contained HTML dashboard (data
inlined, charts drawn with inline SVG -- no CDN, works offline, opens from
OneDrive on any machine).

Commands
--------
  add      Log a task:
             log.py add "task" --hours 2.5 --cat TPM
             log.py add "task" --hours 2.5 --cat TPM --invested 0.5
             (--invested = time YOU spent with the agent on it, for ROI)
  list     Show all logged entries
  bulk     Append entries from a CSV file (header required)
             log.py bulk path/to/entries.csv
             log.py bulk entries.csv --dry-run
             CSV columns: date,task,cat,hours[,invested,note]
  goal     Set, clear, or show the weekly velocity target (hours/week)
             log.py goal set 5.0           # aim for 5h/week
             log.py goal show              # show current goal + progress
             log.py goal clear             # remove the goal
  summary  Print totals (all-time / week / month / by category / ROI)
  report   Regenerate dashboard.html from the log
  sync     Print the OneDrive path + regen dashboard (manual "are we current?")

HOURS SAVED is an ESTIMATE: the time you would have spent doing the task
yourself. Edit log.jsonl by hand anytime (one JSON per line). Everything
downstream regenerates from that file.

AUTO-SYNC: the agent logs + regenerates after substantial work, so the file
in OneDrive is always current across machines. Run `report` to force a rebuild.
"""
import argparse
import json
import os
import re
import csv
import io
import sys
from datetime import date, timedelta


def _base_dir():
    """Resolve BASE dynamically. Honor AI_TIME_SAVED_DIR env var.
    Tests should set os.environ['AI_TIME_SAVED_DIR'] = '/tmp/sb' BEFORE importing
    log, OR monkey-patch the BASE attribute after import (call functions will
    re-read each time)."""
    return os.environ.get(
        "AI_TIME_SAVED_DIR",
        "/mnt/c/Users/rijve/OneDrive/Documents/ai-time-saved",
    )
def _log_path():
    return os.path.join(_base_dir(), "log.jsonl")
def _dash_path():
    return os.path.join(_base_dir(), "dashboard.html")
def _data_path():
    return os.path.join(_base_dir(), "data.json")

# Module-level defaults for backwards compatibility. They point at the
# production paths at import time. Functions that write/read files MUST call
# _log_path() / _dash_path() / _data_path() instead of using LOG / DASH / DATAJSON
# directly, so that test isolation via os.environ or monkey-patch works.
BASE = _base_dir()
LOG = _log_path()
DASH = _dash_path()
DATAJSON = _data_path()


PALETTE = ["#4f9dff", "#34d399", "#fbbf24", "#f472b6",
           "#a78bfa", "#fb7185", "#22d3ee", "#a3e635"]

# 18-entry achievement catalog (mirrored from dashboard.html ALL_ACHIEVEMENTS).
# Keep these IDs in sync with the dashboard so the "done" set is consistent.
ALL_ACHIEVEMENTS = [
    {"id":"first",  "name":"First Steps",         "desc":"Logged your first task"},
    {"id":"week",   "name":"Week Warrior",        "desc":"Logged something this week"},
    {"id":"ten",    "name":"Ten Strong",          "desc":"10 tasks logged"},
    {"id":"q25",    "name":"Quarter Century",     "desc":"25 tasks logged"},
    {"id":"h50",    "name":"Half Hundred",        "desc":"50 tasks logged"},
    {"id":"h100",   "name":"Hundred Club",        "desc":"100 tasks logged"},
    {"id":"h1",     "name":"One Hour Hero",       "desc":"1 hour saved"},
    {"id":"h10",    "name":"Ten Hours Tower",     "desc":"10 hours saved"},
    {"id":"h50h",   "name":"Fifty Hour Fortress", "desc":"50 hours saved"},
    {"id":"h100h",  "name":"Centurion",           "desc":"100 hours saved"},
    {"id":"h500",   "name":"Five-Hundred Sage",   "desc":"500 hours saved"},
    {"id":"cat3",   "name":"Tri-Master",          "desc":"3+ categories"},
    {"id":"cat5",   "name":"Penta-Force",         "desc":"5+ categories"},
    {"id":"hero",   "name":"Heroic Heft",         "desc":"Saved 5+ hours in a single task"},
    {"id":"epic",   "name":"Epic Effort",         "desc":"Saved 10+ hours in a single task"},
    {"id":"s3",     "name":"Triple Threat",       "desc":"3-day streak"},
    {"id":"s7",     "name":"Week Streak",         "desc":"7-day streak"},
    {"id":"s14",    "name":"Fortnight",           "desc":"14-day streak"},
]


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------
def ensure():
    os.makedirs(_base_dir(), exist_ok=True)
    if not os.path.exists(_log_path()):
        open(_log_path(), "a").close()


def load():
    ensure()
    out = []
    try:
        path = _log_path()
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    except FileNotFoundError:
        return []
    return out


def add(task, hours, cat="General", note="", invested=0.0, d=None):
    d = d or date.today().isoformat()
    rec = {"date": d, "task": task, "cat": cat,
           "hours": round(float(hours), 2),
           "invested": round(float(invested), 2),
           "note": note}
    with open(_log_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  + logged {d} | {cat} | saved {rec['hours']}h"
          + (f" | invested {rec['invested']}h" if rec["invested"] else "")
          + f" | {task}")



def find_matches(entries, needle):
    """Find entries whose date+task contains needle (case-insensitive)."""
    needle = (needle or "").strip().lower()
    if not needle:
        return []
    hits = []
    for i, e in enumerate(entries):
        hay = (str(e.get("date", "")) + ":" + str(e.get("task", ""))).lower()
        if needle in hay:
            hits.append((i, e))
    return hits


def edit(match, **fields):
    """Edit one or more fields of entries matching `match` substring.
    Returns the list of (index, before, after) for the changed entries.
    Refuses to act on more than one match unless --yes is passed (we just
    print all matches and require the caller to confirm; the CLI flag controls
    whether this is treated as a confirmation).
    """
    entries = load()
    hits = find_matches(entries, match)
    if not hits:
        print(f"  no entries match: {match!r}")
        return []
    allowed = {"task", "cat", "hours", "invested", "date", "note"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        print("  no fields to update. Allowed: " + ", ".join(sorted(allowed)))
        return []
    changed = []
    for idx, before in hits:
        after = dict(before)
        for k, v in updates.items():
            if k in ("hours", "invested"):
                v = round(float(v), 2)
            after[k] = v
        entries[idx] = after
        changed.append((idx, before, after))
    # Write back: rebuild file
    with open(_log_path(), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  edited {len(changed)} entr{'y' if len(changed)==1 else 'ies'}:")
    for idx, before, after in changed:
        diff_keys = [k for k in after if before.get(k) != after.get(k)]
        diff = ", ".join(f"{k}: {before.get(k)!r} -> {after.get(k)!r}" for k in diff_keys)
        print(f"    [{idx}] {before.get('date')} {before.get('task')[:50]!r}: {diff}")
    return changed


def delete(match, **filters):
    """Delete entries matching `match` substring.
    Optional --date filter restricts to entries on that date.
    Returns the list of deleted entries.
    """
    entries = load()
    hits = find_matches(entries, match)
    if not hits:
        print(f"  no entries match: {match!r}")
        return []
    if filters.get("date"):
        hits = [(i, e) for i, e in hits if str(e.get("date")) == str(filters["date"])]
        if not hits:
            print(f"  no entries match {match!r} on date {filters['date']!r}")
            return []
    keep_idx = {i for i, _ in hits}
    removed = [e for i, e in hits]
    with open(_log_path(), "w", encoding="utf-8") as f:
        for i, e in enumerate(entries):
            if i in keep_idx:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  deleted {len(removed)} entr{'y' if len(removed)==1 else 'ies'}:")
    for e in removed:
        print(f"    - {e.get('date')} {e.get('task')[:60]!r}")
    return removed




def goal(action, hours=None):
    """Manage the weekly velocity target. Stored in data.json."""
    data_file = _data_path()
    d = {}
    if os.path.exists(data_file):
        try: d = json.loads(open(data_file, encoding="utf-8").read())
        except Exception: d = {}
    cur = d.get("goal", {})
    if action == "show":
        if cur:
            wk = d.get("week", 0)
            tgt = cur.get("hours", 0)
            pct = (wk / tgt * 100) if tgt else 0
            status = "on track" if pct >= 100 else "behind" if pct < 60 else "in range"
            print(f"  weekly goal: {tgt}h   this week: {wk:.1f}h   {pct:.0f}%   ({status})")
        else:
            print("  no weekly goal set. Use: log.py goal set <hours>")
        return
    if action == "clear":
        d.pop("goal", None)
        open(data_file, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
        print("  weekly goal cleared")
        return
    if action == "set":
        if hours is None:
            print("  usage: log.py goal set <hours>")
            return
        d["goal"] = {"hours": float(hours), "set_at": date.today().isoformat()}
        open(data_file, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
        print(f"  weekly goal set to {hours}h")
        return
    print(f"  unknown goal action: {action}. Use: set|show|clear")


def bulk(csv_path, dry_run=False):
    """Append entries from a CSV file. Header required.
    Required columns: date, task, cat, hours
    Optional columns: invested, note
    Returns the number of entries appended.
    Refuses if CSV is malformed or any row is missing required fields."""
    if not os.path.exists(csv_path):
        print(f"  [bulk] FAIL: CSV file not found: {csv_path}", file=sys.stderr)
        return None
    required = {"date", "task", "cat", "hours"}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = required - set(fieldnames)
        if missing:
            print(f"  [bulk] FAIL: CSV missing required columns: {sorted(missing)} (have: {fieldnames})", file=sys.stderr)
            return None
        rows = list(reader)
    if not rows:
        print(f"  CSV is empty (header only); nothing to import")
        return 0
    appended = 0
    for i, row in enumerate(rows, 1):
        try:
            d = row["date"].strip()
            task = row["task"].strip()
            cat = row["cat"].strip() or "General"
            hours = round(float(row["hours"]), 2)
            invested = round(float(row.get("invested") or 0), 2)
            note = (row.get("note") or "").strip()
            if not d or not task or hours <= 0:
                raise ValueError(f"date, task, and positive hours required")
        except Exception as e:
            print(f"  [bulk] FAIL: row {i} parse failed: {e}", file=sys.stderr)
            return None
        if dry_run:
            print(f"  [dry-run] {d} | {cat} | {hours}h | {task[:50]}")
            continue
        rec = {"date": d, "task": task, "cat": cat, "hours": hours,
               "invested": invested, "note": note}
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        appended += 1
    if not dry_run:
        report(load())
    print(f"  bulk import complete: {appended} entr{'y' if appended == 1 else 'ies'} appended from {csv_path}")
    return appended


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def summarize(entries):
    total = sum(e["hours"] for e in entries)
    inv = sum(e.get("invested", 0) for e in entries)
    today = date.today()
    ws = today - timedelta(days=today.weekday())
    ms = today.replace(day=1)
    wk = sum(e["hours"] for e in entries if date.fromisoformat(e["date"]) >= ws)
    mo = sum(e["hours"] for e in entries if date.fromisoformat(e["date"]) >= ms)
    by_cat = {}
    for e in entries:
        by_cat[e["cat"]] = by_cat.get(e["cat"], 0) + e["hours"]
    return total, inv, wk, mo, by_cat


def daily_cum(entries):
    d = {}
    for e in entries:
        d[e["date"]] = d.get(e["date"], 0) + e["hours"]
    d = dict(sorted(d.items()))
    cum, run = [], 0
    for k, v in d.items():
        run += v
        cum.append([k, round(run, 2)])
    return cum


def weekly(entries):
    wk = {}
    for e in entries:
        dt = date.fromisoformat(e["date"])
        key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        wk[key] = wk.get(key, 0) + e["hours"]
    return [list(x) for x in sorted(wk.items())]


def entry_streak(entries):
    """Return consecutive calendar days with entries, ending today."""
    days = {e["date"] for e in entries}
    cursor = date.today()
    count = 0
    while cursor.isoformat() in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


# ---------------------------------------------------------------------------
# Gamification — rank ladder, achievements, artifacts, quests
# ---------------------------------------------------------------------------
# Ten tiers. The mid-band hours for "current" progress bar. Inspired by
# chess/Go ranks so the user sees a familiar ladder climb.
RANK_LADDER = [
    # (tier_name, min_hours, max_hours, glyph, color_token)
    ("Novice",        0,    5,  "○",  "ink-3"),
    ("Bronze",        5,   15,  "◔",  "amber"),
    ("Silver",       15,   30,  "◑",  "ink-2"),
    ("Gold",         30,   50,  "◕",  "amber"),
    ("Platinum",     50,  100,  "●",  "cyan"),
    ("Diamond",     100,  200,  "◆",  "cyan"),
    ("Master",      200,  400,  "★",  "cyan"),
    ("Grandmaster", 400,  800,  "✦",  "cyan"),
    ("Sage",        800, 1500,  "❖",  "green"),
    ("AI Grandmaster", 1500, 10**9, "♛", "green"),
]


def rank_for(total_hours: float):
    """Return (current_tier_dict, next_tier_dict_or_None, progress_pct)."""
    cur = RANK_LADDER[0]
    nxt = RANK_LADDER[1] if len(RANK_LADDER) > 1 else None
    for i, t in enumerate(RANK_LADDER):
        if total_hours >= t[1]:
            cur = t
            nxt = RANK_LADDER[i+1] if i+1 < len(RANK_LADDER) else None
    if nxt is None:
        return {
            "name": cur[0], "glyph": cur[2], "color": cur[3],
            "min": cur[1], "max": cur[2] if False else 10**9,
            "current": total_hours, "next": None, "progress": 100.0,
        }, None, 100.0
    span = nxt[1] - cur[1]
    into = max(0, total_hours - cur[1])
    pct = min(100.0, (into / span) * 100) if span > 0 else 100.0
    return {
        "name": cur[0], "glyph": cur[2], "color": cur[3],
        "min": cur[1], "max": nxt[1],
        "current": total_hours, "next": nxt[0], "progress": round(pct, 1),
    }, {
        "name": nxt[0], "glyph": nxt[2], "min": nxt[1],
    }, round(pct, 1)


def compute_achievements(entries, by_cat, total):
    """Return list of unlocked achievements. Each has id, name, desc, glyph, pct."""
    days = {e["date"] for e in entries}
    cats = set(by_cat.keys())
    max_single = max((e.get("hours", 0) for e in entries), default=0)
    total_tasks = len(entries)
    out = []
    # 1: First Steps
    if total_tasks >= 1:
        out.append({"id":"first","name":"First Steps","desc":"Logged your first task","glyph":"◌","pct":100})
    # 2: Week Warrior
    if any(e["date"] >= (date.today() - timedelta(days=7)).isoformat() for e in entries):
        out.append({"id":"week","name":"Week Warrior","desc":"Logged something this week","glyph":"◷","pct":100})
    # 3: Ten Strong
    if total_tasks >= 10:
        out.append({"id":"ten","name":"Ten Strong","desc":"10 tasks logged","glyph":"⑩","pct":100})
    # 4: Quarter Century
    if total_tasks >= 25:
        out.append({"id":"q25","name":"Quarter Century","desc":"25 tasks logged","glyph":"㉕","pct":100})
    # 5: Half Hundred
    if total_tasks >= 50:
        out.append({"id":"h50","name":"Half Hundred","desc":"50 tasks logged","glyph":"㊿","pct":100})
    # 6: Hundred Club
    if total_tasks >= 100:
        out.append({"id":"h100","name":"Hundred Club","desc":"100 tasks logged","glyph":"✪","pct":100})
    # Hours-based
    if total >= 1: out.append({"id":"h1","name":"One Hour Hero","desc":"1 hour saved","glyph":"❶","pct":100})
    if total >= 10: out.append({"id":"h10","name":"Ten Hours Tower","desc":"10 hours saved","glyph":"❿","pct":100})
    if total >= 50: out.append({"id":"h50h","name":"Fifty Hour Fortress","desc":"50 hours saved","glyph":"⓹⓪","pct":100})
    if total >= 100: out.append({"id":"h100h","name":"Centurion","desc":"100 hours saved","glyph":"Ⅽ","pct":100})
    if total >= 500: out.append({"id":"h500","name":"Five-Hundred Sage","desc":"500 hours saved","glyph":"⓿","pct":100})
    # Category diversity
    if len(cats) >= 3: out.append({"id":"cat3","name":"Tri-Master","desc":"3+ categories","glyph":"⧉","pct":100})
    if len(cats) >= 5: out.append({"id":"cat5","name":"Penta-Force","desc":"5+ categories","glyph":"⫶","pct":100})
    # Single-task hero
    if max_single >= 5: out.append({"id":"hero","name":"Heroic Heft","desc":"Saved 5+ hours in a single task","glyph":"🜲","pct":100})
    if max_single >= 10: out.append({"id":"epic","name":"Epic Effort","desc":"Saved 10+ hours in a single task","glyph":"🜞","pct":100})
    # Streak
    streak = entry_streak(entries)
    if streak >= 3: out.append({"id":"s3","name":"Triple Threat","desc":"3-day streak","glyph":"⌛","pct":100})
    if streak >= 7: out.append({"id":"s7","name":"Week Streak","desc":"7-day streak","glyph":"✦","pct":100})
    if streak >= 14: out.append({"id":"s14","name":"Fortnight","desc":"14-day streak","glyph":"✧","pct":100})
    return out


def compute_artifacts(entries, total, by_cat):
    """Return list of 'artifacts' — earned collectibles based on real work done."""
    arts = []
    # Files saved (rough estimate): each task = 1 artifact
    saved_files = len(entries)
    if saved_files > 0:
        arts.append({"id":"files","name":"Files Salvaged","desc":f"{saved_files} tasks logged","glyph":"⎙","count":saved_files})
    # Disk freed (heuristic): maintenance tasks * 5GB avg
    maint = by_cat.get("Maintenance", 0)
    if maint > 0:
        gb = round(maint * 5, 1)
        arts.append({"id":"disk","name":"Disk Reclaimed","desc":f"~{gb} GB freed","glyph":"⊠","count":gb})
    # TPM weeks (heuristic): each 5h of TPM = 1 week
    tpm = by_cat.get("TPM", 0)
    if tpm > 0:
        weeks = round(tpm / 5, 1)
        arts.append({"id":"tpm","name":"TPM Knowledge","desc":f"~{weeks} curriculum weeks","glyph":"✦","count":weeks})
    # Automation multiplier
    auto = by_cat.get("Automation", 0)
    if auto > 0:
        arts.append({"id":"auto","name":"Automation Forged","desc":f"{auto:.1f}h of systems","glyph":"⌘","count":auto})
    # Hours total artifact
    if total > 0:
        arts.append({"id":"hours","name":"Hours Crystallized","desc":f"{total:.1f}h saved","glyph":"◈","count":total})
    # Categories
    cats = len(by_cat)
    if cats > 0:
        arts.append({"id":"domains","name":"Domains Touched","desc":f"{cats} categories","glyph":"❖","count":cats})
    return arts


def compute_quests(entries, by_cat, total, streak):
    """Return list of active quests with progress."""
    quests = []
    # Weekly: 5h this week
    from datetime import timedelta
    week_start = (date.today() - timedelta(days=7)).isoformat()
    wk = sum(e.get("hours", 0) for e in entries if e["date"] >= week_start)
    quests.append({
        "id": "q_week", "name": "Weekly Grinder", "desc": "Save 5h this week",
        "glyph": "⏵", "target": 5, "current": round(wk, 2),
        "pct": min(100, round((wk/5)*100, 1)) if wk else 0
    })
    # Monthly: 20h
    mo_start = (date.today() - timedelta(days=30)).isoformat()
    mo = sum(e.get("hours", 0) for e in entries if e["date"] >= mo_start)
    quests.append({
        "id": "q_month", "name": "Monthly Marathon", "desc": "Save 20h in 30 days",
        "glyph": "◐", "target": 20, "current": round(mo, 2),
        "pct": min(100, round((mo/20)*100, 1)) if mo else 0
    })
    # Tasks: 10 total
    quests.append({
        "id": "q_10", "name": "Task Tactician", "desc": "Log 10 tasks",
        "glyph": "✓", "target": 10, "current": len(entries),
        "pct": min(100, round((len(entries)/10)*100, 1))
    })
    # Streak: 7 days
    quests.append({
        "id": "q_streak", "name": "Streak Sentinel", "desc": "Hit a 7-day streak",
        "glyph": "✦", "target": 7, "current": streak,
        "pct": min(100, round((streak/7)*100, 1)) if streak else 0
    })
    # Diversity: 4 cats
    quests.append({
        "id": "q_div", "name": "Polymath", "desc": "Log 4 categories",
        "glyph": "❖", "target": 4, "current": len(by_cat),
        "pct": min(100, round((len(by_cat)/4)*100, 1)) if by_cat else 0
    })
    return quests


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Time Saved</title>
<style>
  :root{--bg:#0b0f17;--panel:#141a24;--border:#222c3a;--txt:#e6edf3;
        --mut:#8b949e;--accent:#4f9dff;--good:#34d399;}
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#16233a 0,var(--bg) 55%);
       color:var(--txt);font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
  .wrap{max-width:1080px;margin:0 auto;padding:30px 20px 70px;}
  h1{font-size:27px;margin:0 0 4px;letter-spacing:.3px;}
  .sub{color:var(--mut);font-size:13px;margin-bottom:24px;}
  .cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px;}
  .card{background:linear-gradient(180deg,var(--panel),#10151e);border:1px solid var(--border);
        border-radius:14px;padding:18px 14px;text-align:center;position:relative;overflow:hidden;}
  .card:before{content:"";position:absolute;inset:0 0 auto 0;height:3px;
        background:linear-gradient(90deg,var(--accent),var(--good));opacity:.8;}
  .big{font-size:29px;font-weight:800;color:#fff;}
  .big.acc{color:var(--accent);} .big.good{color:var(--good);}
  .lbl{color:var(--mut);font-size:11.5px;margin-top:7px;line-height:1.3;}
  .grid{display:grid;grid-template-columns:1.15fr .85fr;gap:14px;margin-bottom:14px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}
  .panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px;}
  .panel h2{font-size:13.5px;margin:0 0 14px;color:var(--mut);font-weight:600;
        text-transform:uppercase;letter-spacing:.6px;}
  .bar{display:flex;align-items:center;gap:9px;margin:7px 0;font-size:12.5px;}
  .bl{flex:0 0 auto;height:13px;border-radius:4px;min-width:4px;transition:width .4s;}
  .bt{flex:1;color:var(--txt);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .bv{color:var(--mut);font-variant-numeric:tabular-nums;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{text-align:left;padding:9px 6px;border-bottom:1px solid var(--border);}
  th{color:var(--mut);font-weight:600;font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;}
  td.tab{color:var(--mut);} td.tah{text-align:right;font-variant-numeric:tabular-nums;
        color:var(--good);font-weight:700;}
  .legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:10px;font-size:12px;color:var(--mut);}
  .legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle;}
  .foot{color:var(--mut);font-size:11px;margin-top:20px;text-align:center;}
  @media(max-width:820px){.cards{grid-template-columns:repeat(2,1fr)}.grid,.grid2{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
  <h1>AI Time Saved</h1>
  <div class="sub">Estimate of hours you saved by using Hermes as your AI assistant.
    Source of truth: <code>log.jsonl</code> (in OneDrive). Regenerate: <code>log.py report</code>.</div>
  <div class="cards">
    <div class="card"><div class="big acc" id="total">0</div><div class="lbl">Total hours saved</div></div>
    <div class="card"><div class="big" id="week">0</div><div class="lbl">This week</div></div>
    <div class="card"><div class="big" id="month">0</div><div class="lbl">This month</div></div>
    <div class="card"><div class="big good" id="roi">-</div><div class="lbl">ROI (saved / invested)</div></div>
    <div class="card"><div class="big" id="tasks">0</div><div class="lbl">Tasks logged</div></div>
  </div>

  <div class="grid">
    <div class="panel"><h2>Cumulative hours saved</h2><div id="cumChart"></div></div>
    <div class="panel"><h2>Hours by category</h2><div id="pieChart"></div><div class="legend" id="pieLegend"></div></div>
  </div>

  <div class="grid2">
    <div class="panel"><h2>Hours saved per week</h2><div id="weekChart"></div></div>
    <div class="panel"><h2>Category breakdown</h2><div id="catBars"></div></div>
  </div>

  <div class="panel"><h2>All tasks</h2><table id="tbl"></table></div>
  <div class="foot" id="foot"></div>
</div>
<script>
const DATA = /*DATA*/;
const PALETTE=["#4f9dff","#34d399","#fbbf24","#f472b6","#a78bfa","#fb7185","#22d3ee","#a3e635"];
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
$('total').textContent=DATA.total.toFixed(1);
$('week').textContent=DATA.week.toFixed(1);
$('month').textContent=DATA.month.toFixed(1);
$('tasks').textContent=DATA.entries.length;
$('roi').textContent=DATA.invested>0?(DATA.total/DATA.invested).toFixed(1)+'x':'-';

// cumulative area line
(function(){
  const cum=DATA.cum; if(!cum.length)return;
  const W=580,H=230,p=36,maxY=Math.max(...cum.map(d=>d[1]),1),maxX=cum.length-1||1;
  const X=i=>p+(W-2*p)*(i/maxX), Y=v=>H-p-(H-2*p)*(v/maxY);
  const pts=cum.map((d,i)=>`${X(i).toFixed(1)},${Y(d[1]).toFixed(1)}`).join(' ');
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%">`;
  s+=`<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#4f9dff" stop-opacity=".35"/>
      <stop offset="1" stop-color="#4f9dff" stop-opacity="0"/></linearGradient></defs>`;
  s+=`<polygon points="${p},${H-p} ${pts} ${X(maxX).toFixed(1)},${H-p}" fill="url(#g)"/>`;
  s+=`<polyline points="${pts}" fill="none" stroke="#4f9dff" stroke-width="2.6"/>`;
  s+=`<circle cx="${X(maxX).toFixed(1)}" cy="${Y(cum[cum.length-1][1]).toFixed(1)}" r="4" fill="#4f9dff"/>`;
  s+=`<text x="${p}" y="18" fill="#4f9dff" font-size="13" font-weight="800">${DATA.total.toFixed(1)}h</text>`;
  s+=`<text x="${p}" y="${H-12}" fill="#8b949e" font-size="10">${cum[0][0]}</text>`;
  s+=`<text x="${W-p}" y="${H-12}" fill="#8b949e" font-size="10" text-anchor="end">${cum[cum.length-1][0]}</text>`;
  s+=`</svg>`; $('cumChart').innerHTML=s;
})();

// donut pie
(function(){
  const cats=Object.entries(DATA.byCat).sort((a,b)=>b[1]-a[1]); if(!cats.length)return;
  const total=cats.reduce((s,c)=>s+c[1],0),cx=110,cy=110,r=92;
  const polar=(a)=>[cx+r*Math.cos(a),cy+r*Math.sin(a)];
  const slice=(a0,a1)=>{const[x0,y0]=polar(a0),[x1,y1]=polar(a1);
    const lg=(a1-a0)>Math.PI?1:0;
    return `M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 ${lg} 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z`;};
  let ang=-Math.PI/2,s=`<svg viewBox="0 0 220 220" width="100%">`;
  cats.forEach((c,i)=>{const a1=ang+(c[1]/total)*2*Math.PI;
    s+=`<path d="${slice(ang,a1)}" fill="${PALETTE[i%PALETTE.length]}" stroke="#141a24" stroke-width="2"/>`;
    ang=a1;});
  s+=`<circle cx="${cx}" cy="${cy}" r="${r*0.56}" fill="#141a24"/>`;
  s+=`<text x="${cx}" y="${cy-4}" fill="#fff" font-size="20" font-weight="800" text-anchor="middle">${total.toFixed(0)}h</text>`;
  s+=`<text x="${cx}" y="${cy+15}" fill="#8b949e" font-size="10" text-anchor="middle">total</text></svg>`;
  $('pieChart').innerHTML=s;
  $('pieLegend').innerHTML=cats.map((c,i)=>
    `<span><i style="background:${PALETTE[i%PALETTE.length]}"></i>${esc(c[0])} ${c[1].toFixed(1)}h</span>`).join('');
})();

// weekly bars
(function(){
  const w=DATA.weekly; if(!w.length)return;
  const W=560,H=210,p=28,maxY=Math.max(...w.map(d=>d[1]),1);
  const bw=Math.min(54,(W-2*p)/w.length*0.7),gap=(W-2*p)/w.length;
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%">`;
  w.forEach((d,i)=>{const h=(H-p)*(d[1]/maxY),x=p+gap*i+(gap-bw)/2,y=H-p-h;
    s+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="4" fill="#34d399"/>`;
    s+=`<text x="${(x+bw/2).toFixed(1)}" y="${(y-5).toFixed(1)}" fill="#e6edf3" font-size="10" text-anchor="middle">${d[1].toFixed(1)}</text>`;
    s+=`<text x="${(x+bw/2).toFixed(1)}" y="${H-9}" fill="#8b949e" font-size="8.5" text-anchor="middle">${d[0].replace('2026-','')}</text>`;});
  s+=`</svg>`; $('weekChart').innerHTML=s;
})();

// category bars
(function(){
  const cats=Object.entries(DATA.byCat).sort((a,b)=>b[1]-a[1]); if(!cats.length)return;
  const max=Math.max(...cats.map(c=>c[1]),1);
  $('catBars').innerHTML=cats.map((c,i)=>{
    const pct=(c[1]/max*100).toFixed(0);
    return `<div class="bar"><span class="bl" style="width:${pct}%;background:${PALETTE[i%PALETTE.length]}"></span>
      <span class="bt">${esc(c[0])}</span><span class="bv">${c[1].toFixed(1)}h</span></div>`;}).join('');
})();

// table
(function(){
  const rows=DATA.entries.slice().reverse();
  let h='<tr><th>Date</th><th>Task</th><th>Category</th><th style="text-align:right">Saved</th><th style="text-align:right">Invested</th></tr>';
  rows.forEach(e=>{h+=`<tr><td class="tab">${e.date}</td><td>${esc(e.task)}</td><td class="tab">${esc(e.cat)}</td>
    <td class="tah">${e.hours.toFixed(1)}</td><td class="tab" style="text-align:right">${e.get('invested',0)?e.invested.toFixed(1):'-'}</td></tr>`;});
  $('tbl').innerHTML=h;
  $('foot').textContent='Generated '+new Date().toLocaleString()+' • '+DATA.entries.length+' tasks • source: log.jsonl (OneDrive)';
})();
</script>
</body></html>"""


DATAJSON = os.path.join(BASE, "data.json")


def report(entries):
    """Write data.json AND refresh the embedded DATA block inside
    dashboard.html. The embed means the dashboard renders fully when opened
    directly via file:// (no server, no fetch) - just press F5 after a change."""
    total, inv, wk, mo, by_cat = summarize(entries)
    cum = daily_cum(entries)
    wkdata = weekly(entries)
    streak = entry_streak(entries)
    rank, next_rank, rank_pct = rank_for(total)
    achievements = compute_achievements(entries, by_cat, total)
    artifacts = compute_artifacts(entries, total, by_cat)
    quests = compute_quests(entries, by_cat, total, streak)
    # preserve user-managed fields (goal, etc.) from previous data.json
    preserved = {}
    dp = _data_path()
    if os.path.exists(dp):
        try: preserved = json.loads(open(dp, encoding="utf-8").read())
        except Exception: pass
    preserved_user_fields = {k: v for k, v in preserved.items() if k not in {
        "total","value","streak","rank","next_rank","rank_pct","achievements",
        "artifacts","quests","invested","week","month","byCat","cum","weekly",
        "entries","updated"
    }}
    data = {"total": round(total, 2), "value": round(total * 50, 2),
            "streak": streak, "rank": rank, "next_rank": next_rank,
            "rank_pct": rank_pct, "achievements": achievements,
            "artifacts": artifacts, "quests": quests,
            "invested": round(inv, 2), "week": round(wk, 2),
            "month": round(mo, 2), "byCat": by_cat,
            "cum": cum, "weekly": wkdata, "entries": entries,
            "updated": date.today().isoformat(),
            **preserved_user_fields}
    with open(dp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # refresh embedded DATA so file:// view shows current data with no server.
    # Use a regex so it matches whether DATA is null or already-populated.
    try:
        html = open(_dash_path(), encoding="utf-8").read()
        new_block = "let DATA=" + json.dumps(data, ensure_ascii=False) + ", AUTO=null;"
        if re.search(r"let DATA=.*?, AUTO=null;", html, re.S):
            html = re.sub(r"let DATA=.*?, AUTO=null;", new_block, html, count=1, flags=re.S)
            open(DASH, "w", encoding="utf-8").write(html)
            print(f"  > dashboard.html embedded DATA refreshed")
        else:
            print(f"  > (embed marker not found, leaving dashboard.html as-is)")
    except Exception as e:
        print(f"  > (skip embed refresh: {e})")
    print(f"  > data written: {dp}")
    print(f"  > total {total:.1f}h | week {wk:.1f}h | month {mo:.1f}h | ROI "
          + (f"{(total/inv):.1f}x" if inv else "n/a"))
    print(f"  > Open dashboard.html directly (file://) and press F5 - no server needed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="AI Time-Saved Tracker v2")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add")
    a.add_argument("task")
    a.add_argument("--hours", type=float, required=True)
    a.add_argument("--cat", default="General")
    a.add_argument("--note", default="")
    a.add_argument("--invested", type=float, default=0.0)
    a.add_argument("--date", default=None)

    sub.add_parser("list")

    e = sub.add_parser("edit")
    e.add_argument("--match", required=True, help="substring of 'date:task' to find the entry")
    e.add_argument("--task", default=None)
    e.add_argument("--hours", type=float, default=None)
    e.add_argument("--cat", default=None)
    e.add_argument("--note", default=None)
    e.add_argument("--invested", type=float, default=None)
    e.add_argument("--date", default=None, help="set new date (YYYY-MM-DD)")
    e.add_argument("--yes", action="store_true", help="do not prompt for confirmation")

    d = sub.add_parser("delete")
    d.add_argument("--match", required=True)
    d.add_argument("--date", default=None, help="only delete entries on this date")
    d.add_argument("--yes", action="store_true")

    sub.add_parser("summary")

    b = sub.add_parser("bulk")
    b.add_argument("path", help="path to a CSV file with date,task,cat,hours[,invested,note]")
    b.add_argument("--dry-run", action="store_true", help="validate only, do not append")

    g = sub.add_parser("goal")
    g.add_argument("goal_action", choices=["set", "show", "clear"])
    g.add_argument("hours", nargs="?", type=float, default=None)
    sub.add_parser("report")
    sub.add_parser("sync")
    sub.add_parser("backfill")

    args = p.parse_args()
    if args.cmd is None:
        p.print_help(); return

    if args.cmd == "add":
        add(args.task, args.hours, args.cat, args.note, args.invested, args.date)
        report(load())
    elif args.cmd == "list":
        for e in load():
            print(f"{e['date']} | {e['cat']:<12} | saved {e['hours']:>5.1f}h"
                  + (f" | inv {e.get('invested',0):.1f}h" if e.get('invested',0) else "")
                  + f" | {e['task']}")
    elif args.cmd == "edit":
        entries = load()
        hits = find_matches(entries, args.match)
        if not hits:
            print(f"  no entries match: {args.match!r}")
            return
        if len(hits) > 1 and not args.yes:
            print(f"  {len(hits)} entries match. Pass --yes to edit all, or narrow --match:")
            for i, e in hits:
                print(f"    [{i}] {e.get('date')} {e.get('task')[:60]!r}")
            return
        fields = {k: v for k, v in {
            "task": args.task, "cat": args.cat, "hours": args.hours,
            "invested": args.invested, "date": args.date, "note": args.note,
        }.items() if v is not None}
        edit(args.match, **fields)
        report(load())
    elif args.cmd == "delete":
        entries = load()
        hits = find_matches(entries, args.match)
        if not hits:
            print(f"  no entries match: {args.match!r}")
            return
        if args.date:
            hits = [(i, e) for i, e in hits if str(e.get("date")) == str(args.date)]
        if not hits:
            print(f"  no entries match with date filter")
            return
        if len(hits) > 1 and not args.yes:
            print(f"  {len(hits)} entries match. Pass --yes to delete all, or narrow:")
            for i, e in hits:
                print(f"    [{i}] {e.get('date')} {e.get('task')[:60]!r}")
            return
        delete(args.match, date=args.date)
        report(load())
    elif args.cmd == "goal":
        goal(args.goal_action, args.hours)
    elif args.cmd == "bulk":
        bulk(args.path, args.dry_run)
    elif args.cmd == "summary":
        entries = load()
        total, inv, wk, mo, by_cat = summarize(entries)
        streak = entry_streak(entries)
        rank, next_rank, rank_pct = rank_for(total)
        achievements = compute_achievements(entries, by_cat, total)
        artifacts = compute_artifacts(entries, total, by_cat)
        quests = compute_quests(entries, by_cat, total, streak)
        print(f"All-time   : {total:.1f}h across {len(entries)} tasks")
        print(f"This week  : {wk:.1f}h   This month: {mo:.1f}h")
        print(f"Invested   : {inv:.1f}h   ROI: {(total/inv):.1f}x" if inv else "Invested   : n/a (use --invested)")
        print(f"Streak     : {streak} day(s)")
        print(f"Rank       : {rank['name']} ({rank_pct:.1f}% to {next_rank['name'] if next_rank else 'MAX'})")
        print(f"Value      : ${round(total*50,2):.0f}")
        print()
        print("By category:")
        for c, h in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f"  {c:<14} {h:>6.1f}h")
        print()
        print(f"Achievements: {len(achievements)} of {len(ALL_ACHIEVEMENTS)} unlocked")
        done = [a for a in achievements if a.get("pct", 0) >= 100]
        for a in done[:5]:
            print(f"  + {a['name']} - {a['desc']}")
        if len(done) > 5:
            print(f"  ... and {len(done)-5} more")
        print()
        print(f"Artifacts: {len(artifacts)} collected")
        for a in artifacts:
            print(f"  * {a['name']} - {a['desc']}")
        print()
        print(f"Quests: {sum(1 for q in quests if q.get('pct',0) >= 100)} of {len(quests)} done")
        for q in quests:
            mark = "[x]" if q.get('pct',0) >= 100 else ("[ ]" if q.get('pct',0) == 0 else "[~]")
            print(f"  {mark} {q['name']} - {q['desc']} ({q.get('pct',0):.0f}%)")
        # goal (read from data.json, set by 'goal' subcommand)
        data_file = _data_path()
        if os.path.exists(data_file):
            try:
                goal_data = json.loads(open(data_file, encoding="utf-8").read()).get("goal")
                if goal_data:
                    pct = (wk / goal_data["hours"] * 100) if goal_data.get("hours") else 0
                    print()
                    print(f"Weekly goal: {goal_data['hours']}h   this week: {wk:.1f}h   {pct:.0f}%")
            except Exception: pass
    elif args.cmd == "report":
        report(load())
    elif args.cmd == "sync":
        report(load())
        print("  > OneDrive path is the single source of truth; open dashboard.html on any machine.")
    elif args.cmd == "backfill":
        # Auto-capture work the assistant did for the user (no manual typing).
        # Hours = time the USER would have spent solo; proactive work = full estimate.
        tasks = [
            ("Built interactive AI Time-Saved dashboard (charts, hover tooltips, drill-down)",
             "Tooling", 3.0, "Hand-building a self-contained HTML/SVG dashboard + local server from scratch"),
            ("Created and pushed GitHub repository ai-time-saved",
             "Tooling", 0.5, "Account setup, repo create, commit, push, verify"),
            ("Researched + applied global operating-rules standards",
             "Research", 0.4, "Reading skill docs and translating to your 8 rules"),
        ]
        for t, c, h, n in tasks:
            add(t, h, c, n, 0.0, None)
        report(load())
        print("  > backfilled assistant-performed tasks")


if __name__ == "__main__":
    main()
