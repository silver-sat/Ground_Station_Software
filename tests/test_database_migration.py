import os
import sqlite3
import tempfile
import unittest

from ground_software import create_app
from ground_software.database import get_database, migrate_database


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="legacy_db_", suffix=".db")
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _build_legacy_database(self):
        connection = sqlite3.connect(self.db_path)
        connection.executescript(
            """
            CREATE TABLE transmissions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                command NOT NULL,
                status NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE responses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                response NOT NULL
            );

            CREATE TABLE settings(
                key TEXT PRIMARY KEY,
                value DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO transmissions(command, status) VALUES (X'C0AA434D4431C0', 'pending');
            INSERT INTO transmissions(command, status) VALUES (X'C0AA434D4432C0', 'transmitted');
            INSERT INTO responses(response) VALUES (X'C0AA41434B2031C0');
            INSERT INTO responses(response) VALUES (X'C0AA524553204F4BC0');
            INSERT INTO settings(key, value) VALUES ('responses_cleared_at', datetime('now'));
            """
        )
        connection.commit()
        connection.close()

    def test_migrate_legacy_database_backfills_sequence_and_views(self):
        self._build_legacy_database()

        app = create_app({"TESTING": True, "DATABASE": self.db_path, "SECRET_KEY": "test"})
        with app.app_context():
            migrate_database()
            database = get_database()

            tx_columns = [
                row["name"] for row in database.execute("PRAGMA table_info(transmissions)").fetchall()
            ]
            rsp_columns = [
                row["name"] for row in database.execute("PRAGMA table_info(responses)").fetchall()
            ]

            self.assertIn("message_sequence", tx_columns)
            self.assertIn("message_sequence", rsp_columns)

            null_tx = database.execute(
                "SELECT COUNT(*) AS c FROM transmissions WHERE message_sequence IS NULL"
            ).fetchone()["c"]
            null_rsp = database.execute(
                "SELECT COUNT(*) AS c FROM responses WHERE message_sequence IS NULL"
            ).fetchone()["c"]
            self.assertEqual(null_tx, 0)
            self.assertEqual(null_rsp, 0)

            combined = database.execute(
                "SELECT message_sequence, type FROM combined_messages ORDER BY message_sequence"
            ).fetchall()
            self.assertEqual(len(combined), 4)
            sequences = [row["message_sequence"] for row in combined]
            self.assertEqual(sequences, sorted(sequences))

            cleared = database.execute(
                "SELECT value FROM settings WHERE key='responses_cleared_sequence'"
            ).fetchone()
            self.assertIsNotNone(cleared)

    def test_migrate_database_is_idempotent(self):
        self._build_legacy_database()

        app = create_app({"TESTING": True, "DATABASE": self.db_path, "SECRET_KEY": "test"})
        with app.app_context():
            migrate_database()
            database = get_database()
            first_sequences = database.execute(
                "SELECT message_sequence FROM combined_messages ORDER BY message_sequence"
            ).fetchall()
            first_next = int(
                database.execute("SELECT value FROM settings WHERE key='message_sequence'").fetchone()["value"]
            )

            migrate_database()
            second_sequences = database.execute(
                "SELECT message_sequence FROM combined_messages ORDER BY message_sequence"
            ).fetchall()
            second_next = int(
                database.execute("SELECT value FROM settings WHERE key='message_sequence'").fetchone()["value"]
            )

            self.assertEqual(first_sequences, second_sequences)
            self.assertEqual(first_next, second_next)

    def test_radio_log_rssi_view_extracts_dbm_values(self):
        self._build_legacy_database()

        app = create_app({"TESTING": True, "DATABASE": self.db_path, "SECRET_KEY": "test"})
        with app.app_context():
            migrate_database()
            database = get_database()
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) VALUES (?, ?, ?)",
                ("2026-02-15 12:34:56", 100, "N: rssi -97 dBm, snr 7"),
            )
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) VALUES (?, ?, ?)",
                ("2026-02-15 12:35:56", 101, "N: rssi=-102 dBm"),
            )
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) VALUES (?, ?, ?)",
                ("2026-02-15 12:36:56", 102, "unrelated line"),
            )
            database.commit()

            rows = database.execute(
                "SELECT message_sequence, rssi_dbm FROM radio_log_rssi ORDER BY message_sequence"
            ).fetchall()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["message_sequence"], 100)
            self.assertEqual(rows[0]["rssi_dbm"], -97.0)
            self.assertEqual(rows[1]["message_sequence"], 101)
            self.assertEqual(rows[1]["rssi_dbm"], -102.0)


if __name__ == "__main__":
    unittest.main()
