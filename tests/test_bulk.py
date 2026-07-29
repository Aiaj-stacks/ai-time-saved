#!/usr/bin/env python3
"""
test_bulk.py - unit tests for log.py bulk() CSV import.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import log  # noqa: E402


class TestBulk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir = Path(self.tmp.name)
        self._orig_base, self._orig_log, self._orig_dash = log.BASE, log.LOG, log.DASH
        log.BASE = str(self.tmpdir)
        log.LOG = str(self.tmpdir / "log.jsonl")
        log.DASH = str(self.tmpdir / "dashboard.html")
        (self.tmpdir / "dashboard.html").write_text("<html></html>")

    def tearDown(self):
        log.BASE, log.LOG, log.DASH = self._orig_base, self._orig_log, self._orig_dash

    def _write_csv(self, content):
        path = self.tmpdir / "import.csv"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_bulk_dry_run_no_mutation(self):
        path = self._write_csv(
            "date,task,cat,hours\n"
            "2026-01-01,a,Test,1.0\n"
            "2026-01-02,b,Test,2.0\n"
        )
        n = log.bulk(path, dry_run=True)
        self.assertEqual(n, 0)  # dry_run returns 0 appended
        # file should not exist
        self.assertFalse(Path(log.LOG).exists())

    def test_bulk_real_import_appends_all_rows(self):
        path = self._write_csv(
            "date,task,cat,hours,invested,note\n"
            "2026-01-01,a,Test,1.0,0.1,n1\n"
            "2026-01-02,b,Test,2.0,,n2\n"
        )
        n = log.bulk(path)
        self.assertEqual(n, 2)
        entries = log.load()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["task"], "a")
        self.assertEqual(entries[1]["invested"], 0.0)  # blank CSV -> 0

    def test_bulk_missing_required_column_exits(self):
        path = self._write_csv("date,task\n2026-01-01,foo\n")
        with self.assertRaises(SystemExit):
            log.bulk(path)

    def test_bulk_empty_file_is_noop(self):
        path = self._write_csv("date,task,cat,hours\n")
        n = log.bulk(path)
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
