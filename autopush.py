#!/usr/bin/env python3
"""Auto-publish the AI Time-Saved dashboard to GitHub.

Runs unattended (cron). Commits any new data.json / log.jsonl / dashboard.html
and pushes to origin/main so the repo's plot shape never goes stale.
Exits silently when there is nothing to push (normal case).
"""
import subprocess, sys, os

REPO = "/mnt/c/Users/rijve/OneDrive/Documents/ai-time-saved"
os.chdir(REPO)

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

# stage data + dashboard (never auto-commit anything outside these)
run("git add data.json log.jsonl dashboard.html")
status = run("git status --porcelain")
if not status.stdout.strip():
    sys.exit(0)  # nothing changed - stay quiet

run('git commit -m "auto: sync hours-saved data"')
push = run("git push origin main")
if push.returncode != 0:
    # surface failure to cron logs (don't silently lose data)
    print("PUSH FAILED:\n" + push.stderr)
    sys.exit(1)
print("pushed hours-saved update")
