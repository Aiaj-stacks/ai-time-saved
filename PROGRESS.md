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

- **2026-07-28T20:34:** v15 README refresh + PROGRESS.md created (commit 316a436)
- **2026-07-28T20:40:** v15.1 serve.py re-embeds after POST + port configurable + /api/log alias (commit e10ffc8)

## Roadmap (priority-ordered, updated)
1. ~~Fix README.md to reflect v14 features~~ DONE (v15)
2. ~~Add serve.py POST that actually persists + re-embeds~~ DONE (v15.1)
3. Add GitHub Pages config (.nojekyll + index.html alias) so dashboard is browseable on web
4. Add `log.py edit` and `log.py delete` subcommands (currently append-only, but allow corrections)
5. Add a "weekly velocity target" - log a goal and show progress in the dashboard
6. Add CSV/JSON export endpoint for the log
7. Add per-day cumulative breakdown widget (the chart only shows totals)
8. Refactor dashboard.html to extract the 7 inline scripts into separate .js files (huge win for maintenance)
9. Add a basic test harness for log.py / dda.py / serve.py
10. Add a `make` or just a `dev.sh` that brings up the whole stack with one command

- **2026-07-28T20:46:** v15.3 GitHub Pages config (.nojekyll + index.html) (commit 9adc7a6)
- **2026-07-28T20:48:** v15.4 README documents GitHub Pages (commit 2da99d6)
- **2026-07-28T20:55:** v15.5 log.py edit + delete subcommands with --match safety (commit 2ec8cf6)
- **2026-07-28T20:58:** v15.6 DDA G3 canonical-JSON comparison (no false positives) (commit 5218482)
- **2026-07-28T20:59:** v15.7 re-serialize log.jsonl to compact format (commit a46d4fb)
- **2026-07-28T20:59:** pushed 8 commits to main (origin: f4cb02f -> a46d4fb)

## Roadmap (priority-ordered, updated)
1-2. ~~README refresh, serve.py POST persistence~~ DONE
3. ~~GitHub Pages config~~ DONE
4. ~~log.py edit + delete~~ DONE
5. Add CSV/JSON export endpoint
6. Add weekly velocity target (log a goal, show progress)
7. Refactor dashboard.html into separate JS files (huge win for maintenance)
8. Add basic test harness for log.py / dda.py / serve.py
9. Add `dev.sh` that brings up the stack with one command
10. Per-day cumulative breakdown widget

- **2026-07-28T21:02:** v15.9 serve.py /export.csv + /export.json (commit b15b606)
- **2026-07-28T21:05:** v15.10 dev.sh one-command startup + README (commit 61b77f0)
- **2026-07-28T21:09:** v15.11 test suite (16 tests pass) + dda.append_log returns codes (commit 9701170)

## Roadmap (priority-ordered, updated)
1-5,8,9. ~~All earlier items DONE~~
6. Add weekly velocity target (log a goal, show progress)
7. Refactor dashboard.html into separate JS files
10. Per-day cumulative breakdown widget

## Other candidate tasks
- Make the v14 dashboard form actually persist via serve.py's POST (it should already work - verify in browser)
- Add a stats-overview CLI command that prints the current totals (1-shot summary)
- Add `log.py bulk` to import entries from a CSV file (useful for migrations)
- Add a daily-summary cron that emails/tosts a recap
- Add an `--invested` flag to the `edit` command (it's already there but verify)
