# PROGRESS — Autonomous Dev Loop

## Project: ai-time-saved
- **Purpose:** Track hours saved by Hermes (per README.md)
- **Stack:** Python 3 stdlib, self-contained dashboard.html, optional local server
- **Current main:** `f4cb02f` (v14: draggable panels + interactive compass)
- **Live preview:** http://127.0.0.1:8767/dashboard.html
- **Server:** `python3 -m http.server 8767 --directory .` (background, PID via process list)

## Roadmap (priority-ordered)
1. Fix README.md to reflect v14 features (it's stale, mentions v3)
2. Add a `serve.py` route to write back to log.jsonl so the dashboard's inline form actually persists
3. Add GitHub Pages config (.nojekyll + index.html alias) so the dashboard is browseable on the web
4. Add per-day cumulative breakdown widget (the chart only shows totals, not which-day stats)
5. Add weekly summary auto-generated text in the log README
6. Cleanup scripts: a one-command "fresh start" script that wipes everything except the data

## Iteration log
- **v6-v14 (just landed on main, commit f4cb02f):** full visual + feature upgrade
- **2026-07-28T20:32:** PROGRESS.md created. Autonomous mode engaged. Next: fix README.
