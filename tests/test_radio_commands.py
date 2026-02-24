import os
import tempfile
import unittest

from ground_software import create_app
from ground_software import control
from ground_software.database import get_database, init_database, migrate_database


class RadioCommandsTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="radio_commands_", suffix=".db")
        os.close(fd)

        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "SECRET_KEY": "test",
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            init_database()
            migrate_database()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_build_local_command_frame_callsign(self):
        frame = control.build_local_command_frame("0E", {})
        self.assertEqual(frame, b"\xC0\x0E\xC0")

    def test_build_local_command_frame_doppler(self):
        frame = control.build_local_command_frame(
            "0D",
            {
                "tx_frequency": "433000000",
                "rx_frequency": "433001000",
            },
        )
        self.assertEqual(frame, b"\xC0\x0D433000000 433001000\xC0")

    def test_build_local_command_frame_rejects_invalid_frequency(self):
        with self.assertRaises(ValueError):
            control.build_local_command_frame(
                "0D",
                {
                    "tx_frequency": "43300",
                    "rx_frequency": "433001000",
                },
            )

    def test_build_raw_local_command_frame(self):
        frame = control.build_raw_local_command_frame("1C", "255")
        self.assertEqual(frame, b"\xC0\x1C255\xC0")

    def test_build_raw_local_command_frame_rejects_bad_code(self):
        with self.assertRaises(ValueError):
            control.build_raw_local_command_frame("1CG", "255")

    def test_radio_post_enqueues_local_command(self):
        self.client.post(
            "/radio",
            data={
                "clicked_button": "SendLocal",
                "command_code": "0D",
                "tx_frequency": "433000000",
                "rx_frequency": "433001000",
            },
        )

        with self.app.app_context():
            database = get_database()
            row = database.execute(
                "SELECT command FROM transmissions ORDER BY message_sequence DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["command"], b"\xC0\x0D433000000 433001000\xC0")

    def test_radio_rssi_endpoint_returns_last_window_of_available_data(self):
        with self.app.app_context():
            database = get_database()
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) "
                "VALUES ('2026-01-01 10:00:00', ?, ?)",
                (500, "N: rssi -91 dBm"),
            )
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) "
                "VALUES ('2026-01-01 09:50:00', ?, ?)",
                (501, "N: rssi -95 dBm"),
            )
            database.execute(
                "INSERT INTO radio_logs (timestamp, message_sequence, log_line) "
                "VALUES ('2026-01-01 09:40:00', ?, ?)",
                (502, "N: rssi -99 dBm"),
            )
            database.commit()

        response = self.client.get("/radio/rssi?minutes=15")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["message_sequence"], 501)
        self.assertEqual(payload[0]["rssi_dbm"], -95.0)
        self.assertEqual(payload[1]["message_sequence"], 500)
        self.assertEqual(payload[1]["rssi_dbm"], -91.0)

    def test_radio_post_enqueues_raw_local_command(self):
        self.client.post(
            "/radio",
            data={
                "clicked_button": "SendRawLocal",
                "raw_command_code": "1C",
                "raw_payload": "255",
            },
        )

        with self.app.app_context():
            database = get_database()
            row = database.execute(
                "SELECT command FROM transmissions ORDER BY message_sequence DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["command"], b"\xC0\x1C255\xC0")


if __name__ == "__main__":
    unittest.main()
