#!/usr/bin/env python3
"""
AI Time-Saved Tracker - Live Server (v3)
=========================================
Serves the dashboard and a live JSON API from log.jsonl. No external deps.
Run:  python3 serve.py   (then open http://localhost:8765/)

Endpoints
  GET  /              -> dashboard.html (live)
  GET  /api/data      -> aggregated JSON (re-read from log.jsonl every call)
  GET  /log.jsonl     -> raw log
  POST /api/add       -> append a task  (JSON body: task,hours,cat,invested,note)
"""
import http.server
import json
import os
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

    def do_POST(self):
        if self.path == "/api/add":
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
                    return
                with open(LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self._send(200, {"ok": True, "entry": rec, "agg": aggregate(load())})
            except Exception as e:
                self._send(500, {"error": str(e)})
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *a):
        pass  # quiet


def main():
    os.makedirs(BASE, exist_ok=True)
    if not os.path.exists(LOG):
        open(LOG, "a").close()
    srv = http.server.HTTPServer(("0.0.0.0", PORT), H)
    print(f"AI Time-Saved dashboard live at  http://localhost:{PORT}/")
    print(f"Serving log: {LOG}")
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
