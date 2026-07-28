#!/usr/bin/env python3
"""
AI Time-Saved Tracker - Live Server (v15)
==========================================
Serves the dashboard and a live JSON API from log.jsonl. No external deps.
Run:  python3 serve.py   (then open http://localhost:8765/)

Endpoints
  GET  /              -> dashboard.html (live)
  GET  /api/data      -> aggregated JSON (re-read from log.jsonl every call)
  GET  /data.json     -> latest derived data.json (on disk)
  GET  /log.jsonl     -> raw log
  POST /api/add       -> append a task, regenerate data.json + re-embed in dashboard.html
                        (JSON body: date, task, hours, cat, invested, note)
  POST /api/log       -> alias for /api/add (the v14 dashboard form uses this path)
  POST /api/reembed   -> re-run python3 log.py report (re-derive data.json + re-embed DATA)
                        useful after manual edits to log.jsonl

After every successful POST, the server runs `python3 log.py report` so
the dashboard always reflects the freshest data without needing a restart.
"""
import http.server
import json
import os
import subprocess
import sys
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "log.jsonl")
PORT = 8765


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load():
    out = []
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def aggregate(entries):
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
    d = {}
    for e in entries:
        d[e["date"]] = d.get(e["date"], 0) + e["hours"]
    d = dict(sorted(d.items()))
    cum, run = [], 0
    for k, v in d.items():
        run += v
        cum.append([k, round(run, 2)])
    wkmap = {}
    for e in entries:
        dt = date.fromisoformat(e["date"])
        key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        wkmap[key] = wkmap.get(key, 0) + e["hours"]
    weekly = [list(x) for x in sorted(wkmap.items())]
    return {
        "total": round(total, 2), "invested": round(inv, 2),
        "week": round(wk, 2), "month": round(mo, 2),
        "byCat": by_cat, "cum": cum, "weekly": weekly,
        "entries": entries, "updated": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# handler
# ---------------------------------------------------------------------------
class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            try:
                html = open(os.path.join(BASE, "dashboard.html"), encoding="utf-8").read()
                self._send(200, html, "text/html")
            except FileNotFoundError:
                self._send(404, "dashboard.html missing", "text/plain")
        elif p == "/api/data":
            self._send(200, aggregate(load()))
        elif p == "/data.json":
            try:
                self._send(200, open(os.path.join(BASE, "data.json"), encoding="utf-8").read(), "application/json")
            except FileNotFoundError:
                self._send(404, "no data.json - run: python3 log.py report", "text/plain")
        elif p == "/log.jsonl":
            try:
                self._send(200, open(LOG, encoding="utf-8").read(), "application/json")
            except FileNotFoundError:
                self._send(404, "no log", "text/plain")
        else:
            self._send(404, "not found", "text/plain")

    def _do_add(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode("utf-8")
            b = json.loads(raw)
            rec = {
                "date": b.get("date") or date.today().isoformat(),
                "task": str(b.get("task", "")).strip(),
                "cat": str(b.get("cat", "General")).strip() or "General",
                "hours": round(float(b.get("hours", 0) or 0), 2),
                "invested": round(float(b.get("invested", 0) or 0), 2),
                "note": str(b.get("note", "")).strip(),
            }
            if not rec["task"] or rec["hours"] <= 0:
                self._send(400, {"error": "task and positive hours required"})
                return None
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            # Re-embed: run log.py report to refresh data.json + the DATA block in dashboard.html
            try:
                subprocess.run(
                    [sys.executable, os.path.join(BASE, "log.py"), "report"],
                    check=True, capture_output=True, text=True, timeout=30
                )
            except subprocess.CalledProcessError as e:
                self._send(500, {"error": "logged but re-embed failed: " + e.stderr.strip()})
                return None
            return rec
        except Exception as e:
            self._send(500, {"error": str(e)})
            return None

    def _do_reembed(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            self.rfile.read(n)  # discard any body
            r = subprocess.run(
                [sys.executable, os.path.join(BASE, "log.py"), "report"],
                capture_output=True, text=True, timeout=30, cwd=BASE
            )
            if r.returncode != 0:
                self._send(500, {"error": "re-embed failed: " + r.stderr.strip()})
                return
            self._send(200, {"ok": True, "stdout": r.stdout.strip()})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def do_POST(self):
        if self.path in ("/api/add", "/api/log"):
            rec = self._do_add()
            if rec is not None:
                self._send(200, {"ok": True, "entry": rec, "agg": aggregate(load())})
        elif self.path == "/api/reembed":
            self._do_reembed()
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *a):
        pass  # quiet


def main():
    port = PORT
    # CLI override: python3 serve.py 8768
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except: pass
    # env override: PORT=8768 python3 serve.py
    port = int(os.environ.get("AURA_PORT", port))
    os.makedirs(BASE, exist_ok=True)
    if not os.path.exists(LOG):
        open(LOG, "a").close()
    # Allow port reuse to avoid "Address already in use" after Ctrl-C
    socketserver = http.server.HTTPServer
    class ReusableTCPServer(socketserver):
        allow_reuse_address = True
    srv = ReusableTCPServer(("0.0.0.0", port), H)
    print(f"AI Time-Saved dashboard live at  http://localhost:{port}/")
    print(f"Serving log: {LOG}")
    print(f"Serving log: {LOG}")
    print(f"Env override: AURA_PORT=<n> python3 serve.py [<n>]")
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
