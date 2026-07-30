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

- **2026-07-28T21:18:** v16 weekly goal CLI + dashboard widget (commit eb68632)
- **2026-07-28T21:19:** v16.1 README documents goal/edit/delete subcommands (commit a9be1aa)
- **2026-07-28T21:25:** v17 per-day breakdown panel (commit 76a6f7b)

## Roadmap (priority-ordered, updated)
1-6,8,9,10. ~~All earlier items DONE~~
7. Refactor dashboard.html into separate JS files (deferred - risk without real-browser verification)

## Other candidate tasks
- Add a stats-overview CLI command that prints the current totals
- Add `log.py bulk` to import entries from a CSV file
- Add daily-summary cron that toasts a recap
- Make the dashboard show "next achievement closest to unlock" prominently
- Add export to Markdown summary (for sharing in PRs / notes)
- Add an "Activity heatmap" widget (year-at-a-glance grid)

- **2026-07-28T21:32:** v18 log.py bulk CSV import + tests/test_bulk.py (commit 9acc42d)
- **2026-07-28T21:33:** v18.1 enhanced summary CLI shows rank/ach/artifacts/quests/goal (commit a806cc4)
- **2026-07-28T21:34:** v18.2 README documents bulk + summary (commit 065ff14)

## Test count
- 20/20 unit tests pass (test_log: 9, test_dda: 7, test_bulk: 4)

## Roadmap (priority-ordered, updated)
1-11, #7 (refactor dashboard.html) - deferred; #10 (per-day breakdown) DONE in v17
- Add stats-overview CLI command - merged into enhanced summary (v18.1)
- Add log.py bulk to import entries from a CSV file - DONE (v18)
- Other candidates:
  - Make the dashboard show "next achievement closest to unlock" prominently
  - Add export to Markdown summary (for sharing in PRs / notes)
  - Add an "Activity heatmap" widget (year-at-a-glance grid)
  - Add a tag system (so each entry can have multiple tags)
  - Add `log.py import` (vs bulk which uses CSV - accept JSON arrays)
  - Auto-detect daily summary cron (suggest via toast if no entry today)

- **2026-07-28T22:10:** v18.4 CRITICAL FIX - test isolation (commit 3c33179)

## Lessons learned (v18.4)
- **Test scripts that write to the real data path = silent data loss.**
  The `log.py` module used module-level `LOG = os.path.join(BASE, "log.jsonl")` which was
  bound at import time. Tests set `log.BASE = tmpdir` but `log.LOG` was still production.
  Test entries leaked into production log.jsonl, shrinking it from 29 to 2 entries.
- **Fix:** added `_base_dir()/_log_path()/_dash_path()/_data_path()` helpers that
  re-read `os.environ['AI_TIME_SAVED_DIR']` at every call. All write/read sites use them.
- **DDA saved the day:** the snapshot from earlier let me `git checkout HEAD -- log.jsonl data.json`
  and recover immediately. This is exactly the failure mode DDA was built for.
- **Lesson:** any code that mutates user data MUST go through DDA or use environment-driven paths.
  Tests must never silently write to production.

## Roadmap (priority-ordered, updated)
1-11, v15-v18 - DONE
- Test count now 20/20 pass with proper isolation
- Refactor dashboard.html into separate JS files - deferred (high risk)

- **2026-07-28T22:35:** v19 activity heatmap panel (commit f0db150)

## v19 detail
- Added a year-at-a-glance heatmap panel (53 weeks x 7 days = 371 cells)
- 5 intensity tiers colored from low (cyan/transparent) to high (bright cyan glow)
- Today cell outlined with cyan glow
- Hover tooltip shows date + hours
- Month labels along top, day of week implied by row position
- Stats: days active, longest streak, peak day
- **Bug fixed during v19:** renderGoal() and renderPerDay() were declared but
  never called from v10_renderAll. Both functions + renderHeatmap() now wired in.
- All 7 inline scripts still parse clean.

## Roadmap (priority-ordered, updated)
- DONE: v15 (README), v15.1 (serve.py POST), v15.3 (GitHub Pages),
       v15.5 (log.py edit/delete), v15.6 (DDA G3 canonical),
       v15.9 (exports), v15.10 (dev.sh), v15.11 (tests),
       v16 (goal CLI + widget), v17 (per-day panel), v18 (bulk + summary),
       v18.4 (test isolation fix), v19 (activity heatmap)
- Refactor dashboard.html into separate JS files - still deferred (risk without real browser)

- **2026-07-29T15:42: v21 — DATA ACCURACY + HEATMAP TOP-CENTER GITHUB-CLONE**
  - User: "none of my data are accurately showing up" + heatmap in middle, GitHub-clone, reflects previous days.
  - Spawned 3 parallel subagents (data accuracy, heatmap redesign, E2E verifier build).
  - Bugs found and fixed:
    - log.py rank_for tuple indices (glyph was reading max_hours = 100, now reads char = '●')
    - log.py value float drift (51.27 * 50 = 2563.3499... → 2563.35; now rounds total first → 2563.50)
    - Heatmap redesigned to GitHub-clone (52w x 7d, 5 green tiers, square cells, weekday/month labels)
    - Heatmap moved to TOP-CENTER above KPI cards (no scroll required)
    - 48 broken `$('#xxx')` calls in script 1 (its `$` is getElementById, no # prefix)
    - Empty `<script>` tag at end of HTML (caused SyntaxError)
    - Heatmap math off by 7 days (startSun used (totalWeeks-1)*7 instead of totalWeeks*7)
    - rankTier render had tierNames outside function scope
    - kpiValue Math.round(.5) shows $2,564 from $2563.50; changed to Math.floor → $2,563
    - dda.py had no _safe_reason() for Windows-incompatible colon in snapshot reason
  - Verification: **41/41 PASS, 0 FAIL** via headless jsdom verifier
  - 20/20 unit tests pass; DDA verify PASS; all 7 scripts parse clean
  - Live preview at http://127.0.0.1:8767/dashboard.html fully working
