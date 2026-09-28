"""Code knives for the canonical wall.

These probes make sure a broken or counterfeit append-only trigger cannot stroll
past verification just because it is wearing the right name tag.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from runtime.kiki_mind.ledger import EventLedger, IntegrityError


class KikiMindImplementation0012Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "mind.db"
        EventLedger(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _exec(self, sql: str) -> None:
        conn = sqlite3.connect(self.db)
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    def test_same_named_noop_update_trigger_is_rejected(self):
        self._exec(
            """
            DROP TRIGGER canonical_events_no_update;
            CREATE TRIGGER canonical_events_no_update
            BEFORE UPDATE ON canonical_events
            BEGIN
                SELECT 1;
            END;
            """
        )

        with self.assertRaisesRegex(
            IntegrityError,
            "trigger definition drift",
        ):
            EventLedger(self.db)

    def test_same_named_noop_delete_trigger_is_rejected(self):
        self._exec(
            """
            DROP TRIGGER canonical_events_no_delete;
            CREATE TRIGGER canonical_events_no_delete
            BEFORE DELETE ON canonical_events
            BEGIN
                SELECT 1;
            END;
            """
        )

        with self.assertRaisesRegex(
            IntegrityError,
            "trigger definition drift",
        ):
            EventLedger(self.db)

    def test_missing_trigger_fails_without_silent_repair(self):
        self._exec("DROP TRIGGER canonical_events_no_update;")

        with self.assertRaisesRegex(
            IntegrityError,
            "trigger set drift",
        ):
            EventLedger(self.db)

        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute(
                """
                SELECT 1
                FROM sqlite_schema
                WHERE type='trigger'
                  AND name='canonical_events_no_update'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNone(row)

    def test_unacknowledged_extra_trigger_is_rejected(self):
        self._exec(
            """
            CREATE TRIGGER extra_trigger
            AFTER INSERT ON canonical_events
            BEGIN
                SELECT 1;
            END;
            """
        )

        with self.assertRaisesRegex(
            IntegrityError,
            "trigger set drift",
        ):
            EventLedger(self.db)


if __name__ == "__main__":
    unittest.main()
