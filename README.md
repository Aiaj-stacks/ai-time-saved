# AI Time-Saved Tracker

Track the hours you save by using an AI assistant (Hermes) as your first mate.
Plain Python plus a self-contained, interactive dashboard. No external dependencies
at runtime. Static file works on `file://` — no server required.

## Quick start

```bash
git clone https://github.com/Aiaj-stacks/ai-time-saved
cd ai-time-saved
open dashboard.html          # file:// works - DATA is embedded
# OR for live updates:
python3 serve.py             # then open http://localhost:8765
```

## How it works

- `log.jsonl` is the source of truth.
- Each line is one JSON record: `date`, `task`, `category`, `hours_saved`, `hours_invested`, optional `note`.
- `log.py add` appends a new entry; `log.py report` regenerates `data.json` AND re-embeds the data into `dashboard.html`.
- `dashboard.html` is a single self-contained file with embedded data — opens correctly on `file://` without a server.
- `serve.py` runs a tiny local server for live polling and the inline log form (POST `/api/log` writes back to `log.jsonl`).
- `dda.py` is a 4-layer data loss prevention safety net (snapshot / verify / append-only / rollback).

## Files

| File | Purpose |
|---|---|
| `log.jsonl` | Append-only event log (one JSON record per line) |
| `log.py` | CLI: `add` (append) + `report` (rebuild data.json + re-embed) |
| `data.json` | Derived aggregate: total, value, streak, rank, achievements, quests, charts |
| `dashboard.html` | Self-contained interactive dashboard (v14, sci-fi command-deck style) |
| `serve.py` | Optional local server with POST endpoint (auto re-embeds DATA on POST) |
| `dda.py` | Data loss prevention: snapshot before any write, verify after |
| `index.html` | GitHub Pages entry point (copy of dashboard.html) |
| `.nojekyll` | Tells GitHub Pages to serve HTML without Jekyll processing |
| `autopush.py` | Unattended GitHub sync (cron-safe) |
| `hermes-backup.py` | Daily Hermes state backup to OneDrive |
| `.dda/snapshots/` | Local snapshots (gitignored, never committed) |

## Run it locally

### Static (no server, opens directly)
```bash
cd ai-time-saved
open dashboard.html
```

### With live updates
```bash
python3 serve.py
```
Then open http://localhost:8765/ — the dashboard polls `/api/data` every 5s when auto-refresh is on.

## Log an entry

### CLI
```bash
python3 log.py add "Built the onboarding doc" --hours 2.0 --cat TPM
python3 log.py add "Uninstalled Steam games" --hours 1.5 --cat Maintenance
python3 log.py report      # rebuilds data.json + re-embeds in dashboard.html
```

### Inline form (when served)
Use the "Deploy New Entry" panel inside the dashboard. The form POSTs to `/api/log` which writes to `log.jsonl` and re-embeds.

## Hours saved method

Saved equals the time you would have spent doing it solo, minus the time the agent took.
Work the agent did proactively counts as the full solo estimate.

Default value rate: **$50/hour** (override per-entry if needed).

## Dashboard features (v14)

- **4 KPI cards** with sparklines, trend arrows, power meters
- **Rank hero** with 10-step tier ladder + tier rings overlay
- **5 charts:** cumulative area, weekly velocity bars, category donut, ROI arc gauge
- **Gamification:** 18 achievements, 6 artifacts, 5 quests
- **14 keyboard shortcuts:** `⌘K` command palette, `R` refresh, `A` auto, `N` new entry, `G` god mode, `V` voice, `T` time-travel, `C` co-pilot, `M` mini-map, `⌘⇧A` achievement tree, `.` focus mode, `F` fireworks, `⇧R` realtime graph, `⇧H` holochart, `D` hide panels, `Esc` close
- **Drag-to-move** on every fixed panel (realtime, holo, copilot, minimap, tree, timetravel, compass)
- **Interactive compass** with manual bearing + dbl-click reset
- **Meta-bar** at bottom: FPS, ping, memory, draw calls, command count, version pill
- **Mouse trail, click ripples, level-up flash, god mode**, holographic scanlines, hex-grid background
- **WCAG 2.1 AA:** skip link, ARIA, focus rings, reduced-motion honored, `<dialog>`, live region

## Viewing the plot shape

- This repository tracks the full history of your hours saved.
- Watch the cumulative chart grow across commits.
- For a live interactive view, clone the repo, run `serve.py`, and open localhost:8765.

### GitHub Pages (recommended for sharing)

Enabled out of the box. To publish:

1. Repo Settings -> Pages
2. Source: "Deploy from a branch"
3. Branch: `main`, folder: `/ (root)`
4. Save

Public URL: **https://Aiaj-stacks.github.io/ai-time-saved/**

The page is **read-only** (no live `serve.py` on GitHub's static hosting). Re-embed by running `python3 log.py report` locally and pushing, OR click the "Refresh" button in the dashboard to fetch fresh data via the local server.

## Privacy

All data stays in this repository as your personal hours-saved log.
The dashboard makes no external network calls at runtime (fonts are loaded from Google Fonts CDN in browser, but the dashboard works without them).

## Safety

`dda.py` runs a snapshot before any code touches `log.jsonl` or `data.json`. If a subagent or script corrupts the files, you can roll back:

```bash
python3 dda.py list            # list snapshots
python3 dda.py rollback        # roll back to latest snapshot (interactive)
python3 dda.py verify          # check current files against latest snapshot
```
