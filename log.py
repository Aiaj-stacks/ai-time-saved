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
from datetime import date, timedelta

BASE = os.environ.get(
    "AI_TIME_SAVED_DIR",
    "/mnt/c/Users/rijve/OneDrive/Documents/ai-time-saved",
)
LOG = os.path.join(BASE, "log.jsonl")
DASH = os.path.join(BASE, "dashboard.html")

PALETTE = ["#4f9dff", "#34d399", "#fbbf24", "#f472b6",
           "#a78bfa", "#fb7185", "#22d3ee", "#a3e635"]


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------
def ensure():
    os.makedirs(BASE, exist_ok=True)
    if not os.path.exists(LOG):
        open(LOG, "a").close()


def load():
    ensure()
    out = []
    for line in open(LOG, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def add(task, hours, cat="General", note="", invested=0.0, d=None):
    d = d or date.today().isoformat()
    rec = {"date": d, "task": task, "cat": cat,
           "hours": round(float(hours), 2),
           "invested": round(float(invested), 2),
           "note": note}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  + logged {d} | {cat} | saved {rec['hours']}h"
          + (f" | invested {rec['invested']}h" if rec["invested"] else "")
          + f" | {task}")


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
    data = {"total": round(total, 2), "invested": round(inv, 2), "week": round(wk, 2),
            "month": round(mo, 2), "byCat": by_cat, "cum": cum,
            "weekly": wkdata, "entries": entries, "updated": date.today().isoformat()}
    with open(DATAJSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # refresh embedded DATA so file:// view shows current data with no server.
    # Use a regex so it matches whether DATA is null or already-populated.
    try:
        html = open(DASH, encoding="utf-8").read()
        new_block = "let DATA=" + json.dumps(data, ensure_ascii=False) + ", AUTO=null;"
        if re.search(r"let DATA=.*?, AUTO=null;", html, re.S):
            html = re.sub(r"let DATA=.*?, AUTO=null;", new_block, html, count=1, flags=re.S)
            open(DASH, "w", encoding="utf-8").write(html)
            print(f"  > dashboard.html embedded DATA refreshed")
        else:
            print(f"  > (embed marker not found, leaving dashboard.html as-is)")
    except Exception as e:
        print(f"  > (skip embed refresh: {e})")
    print(f"  > data written: {DATAJSON}")
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
    sub.add_parser("summary")
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
    elif args.cmd == "summary":
        entries = load()
        total, inv, wk, mo, by_cat = summarize(entries)
        print(f"All-time : {total:.1f}h across {len(entries)} tasks")
        print(f"This week : {wk:.1f}h   This month: {mo:.1f}h")
        print(f"Invested  : {inv:.1f}h   ROI: {(total/inv):.1f}x" if inv else "Invested  : n/a (use --invested)")
        print("By category:")
        for c, h in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f"  {c:<12} {h:>6.1f}h")
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
