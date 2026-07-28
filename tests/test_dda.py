#!/usr/bin/env python3
"""
test_dda.py - unit tests for dda.py (snapshot / verify / append / rollback).
Uses unittest from stdlib. No external deps. Run with:
    python3 tests/test_dda.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dda  # noqa: E402


class TestDDA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir = Path(self.tmp.name)
        # Monkey-patch dda.ROOT, dda.SNAPS, dda.DDA to point inside tmpdir
        self._orig_root = dda.ROOT
        self._orig_snaps = dda.SNAPS
        self._orig_dda_dir = dda.DDA
        dda.ROOT = self.tmpdir
        dda.DDA = self.tmpdir / ".dda"
        dda.SNAPS = dda.DDA / "snapshots"
        dda.ensure_dirs()
        # write a log.jsonl with 2 entries
        (self.tmpdir / "log.jsonl").write_text(
            json.dumps({"date":"2026-01-01","task":"a","cat":"X","hours":1.0}) + "\n" +
            json.dumps({"date":"2026-01-02","task":"b","cat":"X","hours":2.0}) + "\n"
        )

    def tearDown(self):
        dda.ROOT = self._orig_root
        dda.SNAPS = self._orig_snaps
        dda.DDA = self._orig_dda_dir

    def test_snapshot_creates_manifest_and_copies(self):
        dda.snapshot("unit-test")
        snaps = list(dda.SNAPS.iterdir())
        self.assertEqual(len(snaps), 1)
        manifest = json.loads((snaps[0] / "manifest.json").read_text())
        self.assertIn("files", manifest)
        self.assertIn("log.jsonl", manifest["files"])
        self.assertTrue((snaps[0] / "log.jsonl").exists())

    def test_verify_passes_after_snapshot(self):
        dda.snapshot("unit-test")
        self.assertEqual(dda.verify(), 0)

    def test_verify_flags_line_count_decrease(self):
        dda.snapshot("unit-test")
        # overwrite log with 1 entry
        (self.tmpdir / "log.jsonl").write_text(
            json.dumps({"date":"2026-01-01","task":"a","cat":"X","hours":1.0}) + "\n"
        )
        self.assertEqual(dda.verify(), 1)

    def test_verify_passes_when_log_only_grows(self):
        dda.snapshot("unit-test")
        # append a 3rd entry
        with open(self.tmpdir / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"date":"2026-01-03","task":"c","cat":"X","hours":3.0}) + "\n")
        self.assertEqual(dda.verify(), 0)

    def test_verify_handles_formatting_differences(self):
        """Re-serialization with different whitespace/key-order should still PASS.
        Note: log.jsonl must remain single-line JSON per convention; multi-line
        JSON is invalid JSONL and would correctly trigger a verify failure."""
        dda.snapshot("unit-test")
        # rewrite as single-line JSON but with different key order + extra spaces
        (self.tmpdir / "log.jsonl").write_text(
            json.dumps({"hours":1.0,"cat":"X","task":"a","date":"2026-01-01"}) + "\n" +
            json.dumps({"hours":2.0,"cat":"X","task":"b","date":"2026-01-02"}, separators=(", ", ": ")) + "\n"
        )
        # G3 canonicalizes JSON so this should still pass
        self.assertEqual(dda.verify(), 0)

    def test_append_log_adds_new_line(self):
        dda.snapshot("unit-test")
        rc = dda.append_log(json.dumps({"date":"2026-01-03","task":"c","cat":"X","hours":3.0}))
        self.assertEqual(rc, 0)
        self.assertEqual(len((self.tmpdir / "log.jsonl").read_text().splitlines()), 3)

    def test_append_log_rejects_invalid_json(self):
        dda.snapshot("unit-test")
        rc = dda.append_log("not json {")
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)