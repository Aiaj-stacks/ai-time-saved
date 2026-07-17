# AI Time-Saved Tracker

Track the hours you save by using an AI assistant (Hermes) as your first mate.
Plain Python plus a self-contained, interactive dashboard. No external dependencies.

## How it works

- `log.jsonl` is the source of truth.
- Each line is one JSON record: date, task, category, hours saved, hours invested.
- `log.py` adds entries and regenerates `data.json`.
- `dashboard.html` is a live, interactive dashboard with hover tooltips and click-to-drill.
- `serve.py` runs a tiny local server for real-time updates and an inline log form.

## Run it locally

```bash
cd ai-time-saved
python3 serve.py
```

Then open http://localhost:8765/ in your browser.

## Log an entry

```bash
python3 log.py add "Built the onboarding doc" --hours 2.0 --cat TPM
```

Or use the inline "Log an entry" form inside the dashboard itself.

## Hours saved method

Saved equals the time you would have spent doing it solo, minus the time the agent took.
Work the agent did proactively counts as the full solo estimate.

## Viewing the plot shape

- This repository tracks the full history of your hours saved.
- Watch the cumulative chart grow across commits.
- For a live interactive view, clone the repo, run `serve.py`, and open localhost:8765.
- You can also enable GitHub Pages (Settings, Pages, branch main) to view the static dashboard online.

## Privacy

All data stays in this repository as your personal hours-saved log.
The dashboard makes no external network calls.
