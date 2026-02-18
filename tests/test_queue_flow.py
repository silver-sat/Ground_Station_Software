import os
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import socket as pysocket

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


class _FakeRuntimeSerial:
    def __init__(self, *args, **kwargs):
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    def close(self):
        pass


class _TimeoutNotifySocket:
    def settimeout(self, _seconds):
        pass

    def bind(self, _path):
        pass

    def recv(self, _size):
        raise pysocket.timeout()

    def close(self):
        pass


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

    def test_timeout_polling_drains_pending_doppler_without_notify(self):
        db_dir = tempfile.mkdtemp(prefix="doppler_pending_")
        db_path = os.path.join(db_dir, "radio.db")

        app = create_app(
            {
                "TESTING": True,
                "DATABASE": db_path,
                "SECRET_KEY": "test",
                "COMMAND_SECRET_PATH": self.secret_path,
            }
        )
        with app.app_context():
            init_database()
            migrate_database()

        shutdown_event = threading.Event()

        def socket_factory(*_args, **_kwargs):
            return _TimeoutNotifySocket()

        with patch.object(serial_write_interface.serial, "Serial", _FakeRuntimeSerial), patch.object(
            serial_write_interface.socket, "socket", side_effect=socket_factory
        ), patch.object(serial_write_interface.os.path, "abspath", return_value=db_path), patch.object(
            serial_write_interface, "NOTIFY_SOCKET_PATH", "/tmp/test_radio_notify_unused"
        ):
            writer_thread = threading.Thread(
                target=serial_write_interface.serial_write,
                args=("/tmp/fake_radio", shutdown_event),
                daemon=True,
            )
            writer_thread.start()

            # Ensure startup drain runs before inserting a new Doppler item.
            time.sleep(0.05)

            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    "INSERT INTO transmissions (message_sequence, command, status) VALUES (?, ?, 'pending')",
                    (1, b"\xC0\x0D433000000 433001000\xC0"),
                )
                connection.commit()

            deadline = time.time() + 2.0
            transmitted = False
            while time.time() < deadline:
                with sqlite3.connect(db_path) as connection:
                    row = connection.execute(
                        "SELECT status FROM transmissions WHERE message_sequence = 1"
                    ).fetchone()
                if row and row[0] == "transmitted":
                    transmitted = True
                    break
                time.sleep(0.02)

            shutdown_event.set()
            writer_thread.join(timeout=1.0)

            self.assertTrue(transmitted)


if __name__ == "__main__":
    unittest.main()
