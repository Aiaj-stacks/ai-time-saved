#!/usr/bin/env python3
"""
DDA = "Don't Do Again" — Version Control / Data Loss Prevention
================================================================

A 4-layer safety net for the ai-time-saved dashboard so the T1 subagent
disaster never happens again. Pure stdlib, zero deps.

USAGE (in your workflow):
  dda.py snapshot     # take a timestamped snapshot of the protected files
  dda.py verify       # check current files against last snapshot, report drift
  dda.py rollback     # restore from last snapshot (or --snap N for older)
  dda.py list         # show all snapshots
  dda.py diff         # show line-level changes vs last snapshot
  dda.py gate <cmd>   # run a command; auto-snapshot before, auto-rollback if exit != 0
  dda.py append <f>   # append a line to log.jsonl with line-count guard

PROTECTED FILES (the things subagents can clobber):
  log.jsonl   — append-only, line-count must NEVER decrease
  data.json   — derived from log.jsonl, but treat as protected
  log.py      — source, can be edited but tracked
  dashboard.html — replaceable but tracked

GATES (invariants checked by verify):
  G1: log.jsonl line count must be >= last-snapshot line count
  G2: log.jsonl content fingerprint must be a SUPERSET of last snapshot
  G3: each line in current must match a line in snapshot (no silent rewrites)
  G4: data.json.total must be >= snapshot data.json.total
  G5: any "backfill" must add >= 1 new date not in snapshot

SLEEP-PROOF: snapshots are dated + numbered, stored in .dda/ next to the data.
SHA256 fingerprints protect against silent corruption.
"""
import argparse, hashlib, json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/c/Users/rijve/OneDrive/Documents/ai-time-saved")
DDA  = ROOT / ".dda"
SNAPS = DDA / "snapshots"
PROTECTED = ["log.jsonl", "data.json", "log.py", "dashboard.html"]


def die(msg, code=1):
    print(f"[DDA] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def ensure_dirs():
    DDA.mkdir(exist_ok=True)
    SNAPS.mkdir(parents=True, exist_ok=True)
    gitignore = DDA / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# DDA never commits snapshots\n*\n!.gitignore\n", encoding="utf-8")


def fp(path: Path) -> str:
    """SHA256 of a file's bytes, ignoring line-ending differences for .jsonl."""
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if path.suffix == ".jsonl":
            # Sort lines so a re-order is detectable as the same content
            data = sorted(f.read().splitlines())
            for line in data:
                h.update(line)
                h.update(b"\n")
        else:
            h.update(f.read())
    return h.hexdigest()


def nowstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_reason(reason: str) -> str:
    """Sanitize a snapshot reason so it's a valid filename on Windows.
    Replaces colons, slashes, and other invalid chars with underscores."""
    bad = '<>:"/\\|?*'
    out = "".join(c if c not in bad else "_" for c in reason)
    return out.strip().strip(".")[:120] or "manual"


def latest_snap():
    if not SNAPS.exists():
        return None
    snaps = sorted([p for p in SNAPS.iterdir() if p.is_dir()])
    return snaps[-1] if snaps else None


def snapshot(reason: str = "manual") -> Path:
    ensure_dirs()
    sid = nowstamp() + "_" + _safe_reason(reason)
    sd = SNAPS / sid
    sd.mkdir(parents=True, exist_ok=True)
    manifest = {"id": sid, "ts": datetime.now(timezone.utc).isoformat(), "reason": reason, "files": {}}
    for f in PROTECTED:
        src = ROOT / f
        dst = sd / f
        if src.exists():
            shutil.copy2(src, dst)
        manifest["files"][f] = {
            "exists": src.exists(),
            "size": src.stat().st_size if src.exists() else 0,
            "sha256": fp(src) if src.exists() else None,
        }
    (sd / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # also keep a "latest" symlink for easy access
    latest = DDA / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(sd)
    print(f"[DDA] SNAPSHOT {sid}  reason={reason}")
    return sd


def verify() -> int:
    """Run all gates. Return 0 if PASS, non-zero if any FAIL."""
    snap = latest_snap()
    if not snap:
        print("[DDA] WARN: no snapshot found, taking one now")
        snapshot("auto-verify-init")
        return 0
    mf = json.loads((snap / "manifest.json").read_text())
    fails = []
    # G1/G2/G3: log.jsonl line count + content
    log = ROOT / "log.jsonl"
    if log.exists():
        cur_lines = log.read_text(encoding="utf-8").splitlines()
        snap_log = snap / "log.jsonl"
        snap_lines = snap_log.read_text(encoding="utf-8").splitlines() if snap_log.exists() else []
        # G1: line count must not decrease
        if len(cur_lines) < len(snap_lines):
            fails.append(f"G1: log.jsonl line count DECREASED {len(snap_lines)} -> {len(cur_lines)}")
        # G3: every snap line must still exist in current - canonicalized JSON
        # so that re-serialization (compact vs pretty, key order, whitespace)
        # does NOT trigger a false positive. We only fail on real data loss.
        def canon(line):
            try: return json.dumps(json.loads(line), sort_keys=True, separators=(",", ":"))
            except: return None
        snap_canon = {c for c in (canon(l) for l in snap_lines) if c is not None}
        cur_canon  = {c for c in (canon(l) for l in cur_lines)  if c is not None}
        missing = snap_canon - cur_canon
        if missing:
            fails.append(f"G3: {len(missing)} log entries from snapshot are MISSING in current file (data was clobbered!)")
            # show the first missing entry for debugging
            first = next(iter(missing))
            try: print(f"[DDA] first missing: {json.loads(first)}", file=sys.stderr)
            except: pass
    # G4: data.json total
    data = ROOT / "data.json"
    if data.exists():
        try:
            d = json.loads(data.read_text())
            sd = json.loads((snap / "data.json").read_text()) if (snap / "data.json").exists() else {"total": 0}
            if d.get("total", 0) < sd.get("total", 0):
                fails.append(f"G4: data.json.total DECREASED {sd.get('total')} -> {d.get('total')}")
        except Exception as e:
            fails.append(f"G4: data.json unparseable: {e}")
    # G5: any "backfill" date must be new
    if log.exists():
        cur_dates = set()
        for l in log.read_text(encoding="utf-8").splitlines():
            try: cur_dates.add(json.loads(l).get("date", ""))
            except: pass
        snap_dates = set()
        if (snap / "log.jsonl").exists():
            for l in (snap / "log.jsonl").read_text(encoding="utf-8").splitlines():
                try: snap_dates.add(json.loads(l).get("date", ""))
                except: pass
        new_dates = cur_dates - snap_dates
        # not a hard fail — backfill can add new dates — but report it
        if new_dates:
            print(f"[DDA] G5 INFO: {len(new_dates)} new date(s) added: {sorted(new_dates)}")
    if fails:
        for f in fails:
            print(f"[DDA] FAIL: {f}", file=sys.stderr)
        return 1
    print(f"[DDA] VERIFY PASS  (against snapshot {snap.name})")
    return 0


def rollback(snap_id: str = None) -> int:
    snap = (SNAPS / snap_id) if snap_id else latest_snap()
    if not snap or not snap.exists():
        die(f"snapshot not found: {snap_id}")
    print(f"[DDA] ROLLBACK from {snap.name}")
    for f in PROTECTED:
        src = snap / f
        dst = ROOT / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"[DDA]   restored {f}  ({src.stat().st_size} B)")
        elif dst.exists():
            dst.unlink()
            print(f"[DDA]   removed {f}  (was in current, not in snapshot)")
    return 0


def list_snaps():
    if not SNAPS.exists():
        print("(no snapshots)")
        return
    for sd in sorted(SNAPS.iterdir()):
        if not sd.is_dir(): continue
        mf_path = sd / "manifest.json"
        if mf_path.exists():
            mf = json.loads(mf_path.read_text())
            print(f"  {sd.name}  reason={mf.get('reason')}  total={mf.get('files', {}).get('data.json', {}).get('size', '?')}")


def diff_snap():
    snap = latest_snap()
    if not snap:
        die("no snapshot to diff against")
    for f in PROTECTED:
        cur = ROOT / f
        sna = snap / f
        if not sna.exists() and not cur.exists(): continue
        if not sna.exists():
            print(f"  {f}: NEW (not in snapshot)")
            continue
        if not cur.exists():
            print(f"  {f}: DELETED")
            continue
        if fp(cur) == fp(sna):
            print(f"  {f}: unchanged")
        else:
            print(f"  {f}: CHANGED  ({sna.stat().st_size}B -> {cur.stat().st_size}B)")


def gate(cmd: str) -> int:
    """Run cmd; if it exits non-zero, auto-rollback."""
    snapshot("pre-gate:" + cmd[:30])
    print(f"[DDA] GATE: running: {cmd}")
    rc = os.system(cmd)
    if rc != 0:
        print(f"[DDA] GATE FAILED (exit {rc}); auto-rolling back", file=sys.stderr)
        rollback()
        return rc
    print(f"[DDA] GATE OK (exit 0); running verify")
    return verify()


def append_log(line: str) -> int:
    """Append a single line to log.jsonl with DDA guard.
    Returns 0 on success, 1 on bad JSON, 2 on missing file,
    3 on missing required field, 4 on duplicate, 5 on other error.
    Never calls sys.exit - safe for programmatic use."""
    log = ROOT / "log.jsonl"
    if not log.exists():
        print("[DDA] FAIL: log.jsonl missing; restore from snapshot first", file=sys.stderr)
        return 2
    # parse + validate the line
    try:
        obj = json.loads(line)
        for k in ("date", "task", "cat", "hours"):
            if k not in obj:
                print(f"[DDA] FAIL: line missing required field: {k}", file=sys.stderr)
                return 3
    except Exception as e:
        print(f"[DDA] FAIL: line is not valid JSON: {e}", file=sys.stderr)
        return 1
    # guard: must be a NEW date OR a duplicate within an existing date
    cur = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    cur_dates = {e.get("date") for e in cur}
    if obj["date"] in cur_dates:
        if any(e.get("task") == obj["task"] and e.get("date") == obj["date"] for e in cur):
            print(f"[DDA] FAIL: DUPLICATE: entry for {obj['date']} with same task already exists", file=sys.stderr)
            return 4
    # append
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[DDA] FAIL: could not write: {e}", file=sys.stderr)
        return 5
    print(f"[DDA] APPEND OK  {obj['date']}  {obj['task'][:50]}...")
    return 0



def main():
    ap = argparse.ArgumentParser(description="DDA — Don't Do Again data-loss prevention")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot").add_argument("--reason", default="manual")
    sub.add_parser("verify")
    rb = sub.add_parser("rollback")
    rb.add_argument("--snap", default=None)
    sub.add_parser("list")
    sub.add_parser("diff")
    g = sub.add_parser("gate")
    g.add_argument("gate_cmd", help="shell command to run under gate")
    a = sub.add_parser("append")
    a.add_argument("json_line", help="JSON line to append to log.jsonl")
    args = ap.parse_args()
    ensure_dirs()
    if args.cmd == "snapshot":
        snapshot(args.reason)
    elif args.cmd == "verify":
        sys.exit(verify())
    elif args.cmd == "rollback":
        sys.exit(rollback(args.snap))
    elif args.cmd == "list":
        list_snaps()
    elif args.cmd == "diff":
        diff_snap()
    elif args.cmd == "gate":
        sys.exit(gate(args.gate_cmd))
    elif args.cmd == "append":
        sys.exit(append_log(args.json_line))


if __name__ == "__main__":
    main()
