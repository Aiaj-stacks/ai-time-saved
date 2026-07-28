#!/usr/bin/env python3
"""Daily refresh of the Hermes state backup into OneDrive.

Runs unattended (cron). Tars the portable parts of ~/.hermes into
OneDrive/Documents/hermes-backup/, overwriting hermes-state-latest.tar.gz daily.
Keeps heavy caches out of the archive. Silent on success.
"""
import subprocess, os, shutil, sys

HOME = os.path.expanduser("~")
BACKUP_DIR = "/mnt/c/Users/rijve/OneDrive/Documents/hermes-backup"
# fixed name so it overwrites daily (OneDrive keeps version history)
DEST = os.path.join(BACKUP_DIR, "hermes-state-latest.tar.gz")
os.makedirs(BACKUP_DIR, exist_ok=True)

EXCLUDE = [
    ".hermes/cache", ".hermes/hermes-agent", ".hermes/image_cache",
    ".hermes/audio_cache", ".hermes/lsp", ".hermes/logs", ".hermes/pastes",
    ".hermes/models_dev_cache.json", ".hermes/ollama_cloud_models_cache.json",
    ".hermes/config.yaml.bak.*", ".hermes/.hermes_history",
]
excl_args = [f"--exclude={e}" for e in EXCLUDE]

src = os.path.join(HOME, ".hermes")
tmp = DEST + ".tmp"

# The gateway writes to ~/.hermes/state.db continuously. Tarring a live,
# changing file raises "file changed as we read it" and aborts the backup.
# Pause the gateway for a consistent snapshot, then ALWAYS restart it.
import time
gw_stopped = False
try:
    try:
        subprocess.run(["systemctl", "--user", "stop", "hermes-gateway"],
                       check=True, capture_output=True, text=True)
        gw_stopped = True
        time.sleep(2)  # let any in-flight writes flush
    except subprocess.CalledProcessError:
        gw_stopped = False  # no gateway running; tar anyway

    cmd = ["tar", "czf", tmp] + excl_args + ["-C", HOME, ".hermes"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("BACKUP FAILED:\n" + r.stderr)
        sys.exit(1)
    shutil.move(tmp, DEST)
    print(f"hermes backup refreshed -> {DEST}")
finally:
    if gw_stopped:
        try:
            subprocess.run(["systemctl", "--user", "start", "hermes-gateway"],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            print("WARN: failed to restart hermes-gateway after backup")
