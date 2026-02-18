import unittest
from types import SimpleNamespace
import sys
import types

if "serial" not in sys.modules:
    serial_stub = types.ModuleType("serial")

    class _DummySerial:
        def __init__(self, *args, **kwargs):
            pass

    serial_stub.Serial = _DummySerial
    sys.modules["serial"] = serial_stub

from tests import radio_simulator


class RadioSimulatorFaultTests(unittest.TestCase):
    def _args(self, **overrides):
        defaults = {
            "fault_profile": "none",
            "remote_nack_rate": None,
            "remote_res_err_rate": None,
            "local_nack_rate": None,
            "local_res_err_rate": None,
            "drop_response_rate": None,
            "force_remote_nack": "",
            "force_remote_res_err": "",
            "force_local_nack": "",
            "force_local_res_err": "",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_build_fault_profile_parses_forced_lists(self):
        profile = radio_simulator.build_fault_profile(
            self._args(
                force_remote_nack="SetClock,ReportT",
                force_local_res_err="D,C",
            )
        )

        self.assertEqual(profile.force_remote_nack, {"SetClock", "ReportT"})
        self.assertEqual(profile.force_local_res_err, {"D", "C"})

    def test_apply_remote_faults_forced_nack(self):
        profile = radio_simulator.build_fault_profile(
            self._args(force_remote_nack="SetClock")
        )

        success, response = radio_simulator.apply_remote_faults(
            "SetClock", True, "RES SRC", profile
        )

        self.assertFalse(success)
        self.assertEqual(response, "RES SRC")

    def test_apply_remote_faults_forced_res_err(self):
        profile = radio_simulator.build_fault_profile(
            self._args(force_remote_res_err="ReportT")
        )

        success, response = radio_simulator.apply_remote_faults(
            "ReportT", True, "RES GRC 2026-02-18T00:00:00+00:00", profile
        )

        self.assertTrue(success)
        self.assertEqual(response, "RES ERR")

    def test_apply_local_faults_forced_res_err(self):
        profile = radio_simulator.build_fault_profile(
            self._args(force_local_res_err="D")
        )

        success, response = radio_simulator.apply_local_faults(
            "D", True, "RES D 435000000 435000000", profile
        )

        self.assertTrue(success)
        self.assertEqual(response, "RES ERR")

    def test_rate_override_one_forces_remote_nack(self):
        profile = radio_simulator.build_fault_profile(
            self._args(remote_nack_rate=1.0)
        )

        success, response = radio_simulator.apply_remote_faults(
            "GetPower", True, "RES GPW", profile
        )

        self.assertFalse(success)
        self.assertEqual(response, "RES GPW")

    def test_handle_transmission_remote_setclock_ack_then_res(self):
        profile = radio_simulator.build_fault_profile(self._args())

        class _FakeSerial:
            def __init__(self):
                self.writes = []

            def write(self, data):
                self.writes.append(data)

            def flush(self):
                pass

        serial_connection = _FakeSerial()

        original_delay = radio_simulator.random_delay
        try:
            radio_simulator.random_delay = lambda *_args, **_kwargs: None
            command = "SetClock 2026 02 18 12 30 15"
            signed = (
                ("a" * 64) + ("b" * 16) + "00000042" + command
            ).encode("utf-8")
            transmission = radio_simulator.AVIONICS_DATA + signed

            radio_simulator.handle_transmission(
                serial_connection, profile, transmission
            )
        finally:
            radio_simulator.random_delay = original_delay

        self.assertEqual(len(serial_connection.writes), 2)
        self.assertEqual(
            serial_connection.writes[0],
            radio_simulator.FEND
            + radio_simulator.AVIONICS_DATA
            + b"ACK 00000042"
            + radio_simulator.FEND,
        )
        self.assertEqual(
            serial_connection.writes[1],
            radio_simulator.FEND
            + radio_simulator.AVIONICS_DATA
            + b"RES SRC"
            + radio_simulator.FEND,
        )

    def test_handle_transmission_local_doppler_ack_then_res(self):
        profile = radio_simulator.build_fault_profile(self._args())

        class _FakeSerial:
            def __init__(self):
                self.writes = []

            def write(self, data):
                self.writes.append(data)

            def flush(self):
                pass

        serial_connection = _FakeSerial()

        original_delay = radio_simulator.random_delay
        try:
            radio_simulator.random_delay = lambda *_args, **_kwargs: None
            transmission = b"\x0D435000000 435001000"
            radio_simulator.handle_transmission(
                serial_connection, profile, transmission
            )
        finally:
            radio_simulator.random_delay = original_delay

        self.assertEqual(len(serial_connection.writes), 2)
        self.assertEqual(
            serial_connection.writes[0],
            radio_simulator.FEND
            + radio_simulator.LOCAL_COMMAND
            + b"ACK D"
            + radio_simulator.FEND,
        )
        self.assertEqual(
            serial_connection.writes[1],
            radio_simulator.FEND
            + radio_simulator.LOCAL_COMMAND
            + b"RES D 435000000 435001000"
            + radio_simulator.FEND,
        )

    def test_handle_transmission_remote_forced_nack_has_no_res(self):
        profile = radio_simulator.build_fault_profile(
            self._args(force_remote_nack="SetClock")
        )

        class _FakeSerial:
            def __init__(self):
                self.writes = []

            def write(self, data):
                self.writes.append(data)

            def flush(self):
                pass

        serial_connection = _FakeSerial()

        original_delay = radio_simulator.random_delay
        try:
            radio_simulator.random_delay = lambda *_args, **_kwargs: None
            command = "SetClock 2026 02 18 12 30 15"
            signed = (
                ("a" * 64) + ("b" * 16) + "00000077" + command
            ).encode("utf-8")
            transmission = radio_simulator.AVIONICS_DATA + signed

            radio_simulator.handle_transmission(
                serial_connection, profile, transmission
            )
        finally:
            radio_simulator.random_delay = original_delay

        self.assertEqual(len(serial_connection.writes), 1)
        self.assertEqual(
            serial_connection.writes[0],
            radio_simulator.FEND
            + radio_simulator.AVIONICS_DATA
            + b"NACK 00000077"
            + radio_simulator.FEND,
        )

    def test_handle_transmission_remote_forced_res_err_ack_then_res_err(self):
        profile = radio_simulator.build_fault_profile(
            self._args(force_remote_res_err="SetClock")
        )

        class _FakeSerial:
            def __init__(self):
                self.writes = []

            def write(self, data):
                self.writes.append(data)

            def flush(self):
                pass

        serial_connection = _FakeSerial()

        original_delay = radio_simulator.random_delay
        try:
            radio_simulator.random_delay = lambda *_args, **_kwargs: None
            command = "SetClock 2026 02 18 12 30 15"
            signed = (
                ("a" * 64) + ("b" * 16) + "00000088" + command
            ).encode("utf-8")
            transmission = radio_simulator.AVIONICS_DATA + signed

            radio_simulator.handle_transmission(
                serial_connection, profile, transmission
            )
        finally:
            radio_simulator.random_delay = original_delay

        self.assertEqual(len(serial_connection.writes), 2)
        self.assertEqual(
            serial_connection.writes[0],
            radio_simulator.FEND
            + radio_simulator.AVIONICS_DATA
            + b"ACK 00000088"
            + radio_simulator.FEND,
        )
        self.assertEqual(
            serial_connection.writes[1],
            radio_simulator.FEND
            + radio_simulator.AVIONICS_DATA
            + b"RES ERR"
            + radio_simulator.FEND,
        )


if __name__ == "__main__":
    unittest.main()
