#!/usr/bin/env python3
"""
test_log.py - unit tests for log.py (add/edit/delete + report).
Uses unittest from stdlib. No external deps. Run with:
    python3 tests/test_log.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make log.py importable. It's in the project root, one level up from tests/.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import log  # noqa: E402


class TestLog(unittest.TestCase):
    def setUp(self):
        # Use a tempdir so we never touch the real log.jsonl
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir = Path(self.tmp.name)
        # Monkey-patch log.BASE/LOG/DASH to point inside tmpdir
        self._orig_base, self._orig_log, self._orig_dash = log.BASE, log.LOG, log.DASH
        log.BASE = str(self.tmpdir)
        log.LOG = str(self.tmpdir / "log.jsonl")
        log.DASH = str(self.tmpdir / "dashboard.html")
        # Create an empty dashboard.html stub so report() does not error
        (self.tmpdir / "dashboard.html").write_text("<html></html>")

    def tearDown(self):
        log.BASE, log.LOG, log.DASH = self._orig_base, self._orig_log, self._orig_dash

    # --- add / load ---
    def test_add_appends_one_line(self):
        log.add("task a", 1.5, "TPM")
        self.assertTrue(Path(log.LOG).exists())
        lines = Path(log.LOG).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["task"], "task a")
        self.assertEqual(rec["hours"], 1.5)
        self.assertEqual(rec["cat"], "TPM")

    def test_add_incremental_ids(self):
        # No IDs are auto-assigned but order is preserved
        log.add("first", 1.0)
        log.add("second", 2.0)
        log.add("third", 3.0)
        entries = log.load()
        self.assertEqual([e["task"] for e in entries], ["first", "second", "third"])
        self.assertEqual([e["hours"] for e in entries], [1.0, 2.0, 3.0])

    # --- edit ---
    def test_edit_single_match_changes_field(self):
        log.add("test edit", 1.0, "Test")
        log.edit("test edit", hours=2.0, note="edited")
        entries = log.load()
        self.assertEqual(entries[0]["hours"], 2.0)
        self.assertEqual(entries[0]["note"], "edited")

    def test_edit_no_match_is_noop(self):
        log.add("a", 1.0)
        log.edit("nonexistent", hours=99.0)
        entries = log.load()
        self.assertEqual(entries[0]["hours"], 1.0)

    def test_edit_multi_match_returns_list(self):
        log.add("foo task A", 1.0)
        log.add("foo task B", 2.0)
        changed = log.edit("foo", hours=5.0)
        # Without --yes the CLI rejects but the function itself returns the list
        self.assertEqual(len(changed), 2)

    # --- delete ---
    def test_delete_single_match_removes_entry(self):
        log.add("keep me", 1.0)
        log.add("delete me", 1.0)
        removed = log.delete("delete me")
        self.assertEqual(len(removed), 1)
        entries = log.load()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["task"], "keep me")

    def test_delete_no_match_is_noop(self):
        log.add("a", 1.0)
        removed = log.delete("nonexistent")
        self.assertEqual(removed, [])
        self.assertEqual(len(log.load()), 1)

    def test_delete_with_date_filter(self):
        log.add("a", 1.0, d="2026-01-01")
        log.add("b", 1.0, d="2026-01-02")
        removed = log.delete("a", date="2026-01-01")
        self.assertEqual(len(removed), 1)
        entries = log.load()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["task"], "b")

    # --- summarize ---
    def test_summarize_totals(self):
        log.add("a", 1.0, "TPM")
        log.add("b", 2.5, "Tooling")
        log.add("c", 0.5, "TPM", invested=0.2)
        entries = log.load()
        total, inv, wk, mo, by_cat = log.summarize(entries)
        self.assertEqual(total, 4.0)
        self.assertEqual(inv, 0.2)
        self.assertEqual(by_cat["TPM"], 1.5)
        self.assertEqual(by_cat["Tooling"], 2.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)