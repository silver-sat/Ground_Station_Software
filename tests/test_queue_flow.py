import os
import sqlite3
import tempfile
import unittest

from ground_software import create_app
from ground_software import control
from ground_software.database import get_database, init_database, migrate_database, next_sequence_value
from ground_software import serial_read_interface, serial_write_interface


class _FakeWriteSerial:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)


class _FakeReadSerial:
    def __init__(self, stream_bytes):
        self.stream = stream_bytes
        self.position = 0

    def read(self, n=1):
        if self.position >= len(self.stream):
            return b""
        chunk = self.stream[self.position : self.position + n]
        self.position += len(chunk)
        return chunk

    def read_until(self, expected=b"\n"):
        if self.position >= len(self.stream):
            return b""
        index = self.stream.find(expected, self.position)
        if index == -1:
            chunk = self.stream[self.position :]
            self.position = len(self.stream)
            return chunk
        end = index + len(expected)
        chunk = self.stream[self.position : end]
        self.position = end
        return chunk


class QueueFlowTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="queue_flow_", suffix=".db")
        os.close(fd)

        fd_secret, self.secret_path = tempfile.mkstemp(prefix="queue_secret_", suffix=".txt")
        os.close(fd_secret)
        with open(self.secret_path, "wb") as secret_file:
            secret_file.write(b"queue-test-secret")

        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "SECRET_KEY": "test",
                "COMMAND_SECRET_PATH": self.secret_path,
            }
        )

        with self.app.app_context():
            init_database()
            migrate_database()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        if os.path.exists(self.secret_path):
            os.unlink(self.secret_path)

    def test_enqueue_drain_and_response_ordering(self):
        with self.app.app_context():
            control.insert(control.sign("NoOperate"))
            control.insert(control.sign("GetPower"))
            control.insert(control.sign("GetTelemetry"))

            database = get_database()
            transmissions = database.execute(
                "SELECT message_sequence, command FROM transmissions ORDER BY message_sequence"
            ).fetchall()
            self.assertEqual(len(transmissions), 3)

            write_connection = sqlite3.connect(self.db_path)
            write_cursor = write_connection.cursor()
            fake_writer = _FakeWriteSerial()
            serial_write_interface.drain_pending_transmissions(
                write_connection, write_cursor, fake_writer
            )

            self.assertEqual(len(fake_writer.writes), 3)
            self.assertEqual(fake_writer.writes, [row["command"] for row in transmissions])

            status_rows = write_connection.execute(
                "SELECT status FROM transmissions ORDER BY message_sequence"
            ).fetchall()
            self.assertTrue(all(row[0] == "transmitted" for row in status_rows))

            response_stream = (
                b"\xC0\xAAACK 1\xC0"
                b"\xC0\xAARES OK\xC0"
            )
            fake_reader = _FakeReadSerial(response_stream)
            while True:
                frame = serial_read_interface.read_kiss_frame(fake_reader)
                if frame is None:
                    break
                msg_sequence = next_sequence_value(write_connection, "message_sequence", 1)
                write_cursor.execute(
                    "INSERT INTO responses (message_sequence, response) VALUES (?, ?)",
                    (msg_sequence, frame),
                )
                write_connection.commit()

            combined = write_connection.execute(
                "SELECT message_sequence, type FROM combined_messages ORDER BY message_sequence"
            ).fetchall()
            self.assertEqual(len(combined), 5)
            self.assertEqual([row[1] for row in combined[:3]], ["transmission"] * 3)
            self.assertEqual([row[1] for row in combined[3:]], ["response", "response"])

            write_connection.close()


if __name__ == "__main__":
    unittest.main()
