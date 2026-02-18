#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Radio Simulator
 
 This program simulates the ground station radio
 
"""

import argparse
import datetime
import logging
import random
import serial
import time
from dataclasses import dataclass, field

## KISS special characters

FEND = b"\xC0"  # frame begin/end
LOCAL_COMMAND = b"\x00"
AVIONICS_DATA = b"\xAA"
DOPPLER_FREQUENCIES = b"\x0D"
MODIFY_MODE = b"\x0C"
STATUS = b"\x09"
CALLSIGN = b"\x0E"

ACK_DELAY_MIN_SECONDS = 0.08
ACK_DELAY_MAX_SECONDS = 0.25
RES_DELAY_MIN_SECONDS = 0.25
RES_DELAY_MAX_SECONDS = 1.20

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
RETRY_DELAY_SECONDS = 2

DEFAULT_PORT = "/tmp/ground_station"
DEFAULT_BAUD_RATE = 19200
MIN_RADIO_FREQUENCY_HZ = 435_000_000
MAX_RADIO_FREQUENCY_HZ = 438_000_000


@dataclass
class FaultProfile:
    remote_nack_rate: float = 0.0
    remote_res_err_rate: float = 0.0
    local_nack_rate: float = 0.0
    local_res_err_rate: float = 0.0
    drop_response_rate: float = 0.0
    force_remote_nack: set[str] = field(default_factory=set)
    force_remote_res_err: set[str] = field(default_factory=set)
    force_local_nack: set[str] = field(default_factory=set)
    force_local_res_err: set[str] = field(default_factory=set)


def open_serial_with_retry(port, baud_rate):
    while True:
        try:
            return serial.Serial(port, baud_rate, timeout=1)
        except Exception as error:
            logging.warning(
                "Unable to open %s yet (%s). Retrying in %d seconds...",
                port,
                error,
                RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)

def read_kiss_payload(serial_connection):
    while True:
        first = serial_connection.read(1)
        if not first:
            return None
        if first == FEND:
            break

    payload = serial_connection.read_until(expected=FEND)
    if not payload:
        return None
    if payload[-1:] != FEND:
        return None
    return payload[:-1]


def random_delay(minimum, maximum):
    time.sleep(random.uniform(minimum, maximum))


def write_frame(serial_connection, command_byte, payload_text):
    frame = FEND + command_byte + payload_text.encode("utf-8") + FEND
    serial_connection.write(frame)
    serial_connection.flush()
    logging.debug("Sent frame: %r", frame)


def ack_or_nack_for_remote(serial_connection, sequence, is_ack=True):
    verb = "ACK" if is_ack else "NACK"
    write_frame(serial_connection, AVIONICS_DATA, f"{verb} {sequence}")


def send_remote_response(serial_connection, response_text):
    write_frame(serial_connection, AVIONICS_DATA, response_text)


def send_local_ack(serial_connection, command_code):
    write_frame(serial_connection, LOCAL_COMMAND, f"ACK {command_code}")


def send_local_nack(serial_connection, command_code):
    write_frame(serial_connection, LOCAL_COMMAND, f"NACK {command_code}")


def send_local_response(serial_connection, response_text):
    write_frame(serial_connection, LOCAL_COMMAND, response_text)


def parse_list(value):
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def clamp_rate(rate):
    return min(1.0, max(0.0, float(rate)))


def profile_defaults(profile_name):
    match profile_name:
        case "none":
            return FaultProfile()
        case "light":
            return FaultProfile(
                remote_nack_rate=0.02,
                remote_res_err_rate=0.03,
                local_nack_rate=0.01,
                local_res_err_rate=0.02,
                drop_response_rate=0.0,
            )
        case "moderate":
            return FaultProfile(
                remote_nack_rate=0.05,
                remote_res_err_rate=0.08,
                local_nack_rate=0.03,
                local_res_err_rate=0.05,
                drop_response_rate=0.02,
            )
        case "aggressive":
            return FaultProfile(
                remote_nack_rate=0.12,
                remote_res_err_rate=0.18,
                local_nack_rate=0.08,
                local_res_err_rate=0.12,
                drop_response_rate=0.08,
            )
    raise ValueError(f"Unsupported profile: {profile_name}")


def build_fault_profile(args):
    profile = profile_defaults(args.fault_profile)

    if args.remote_nack_rate is not None:
        profile.remote_nack_rate = clamp_rate(args.remote_nack_rate)
    if args.remote_res_err_rate is not None:
        profile.remote_res_err_rate = clamp_rate(args.remote_res_err_rate)
    if args.local_nack_rate is not None:
        profile.local_nack_rate = clamp_rate(args.local_nack_rate)
    if args.local_res_err_rate is not None:
        profile.local_res_err_rate = clamp_rate(args.local_res_err_rate)
    if args.drop_response_rate is not None:
        profile.drop_response_rate = clamp_rate(args.drop_response_rate)

    profile.force_remote_nack = parse_list(args.force_remote_nack)
    profile.force_remote_res_err = parse_list(args.force_remote_res_err)
    profile.force_local_nack = parse_list(args.force_local_nack)
    profile.force_local_res_err = parse_list(args.force_local_res_err)

    return profile


def should_happen(rate):
    return random.random() < rate


def apply_remote_faults(command_name, success, response_text, fault_profile):
    if success and (
        command_name in fault_profile.force_remote_nack
        or should_happen(fault_profile.remote_nack_rate)
    ):
        success = False
        logging.info("Fault injected: remote NACK for %s", command_name)

    if success and (
        command_name in fault_profile.force_remote_res_err
        or should_happen(fault_profile.remote_res_err_rate)
    ):
        response_text = "RES ERR"
        logging.info("Fault injected: remote RES ERR for %s", command_name)

    return success, response_text


def apply_local_faults(command_code, success, response_text, fault_profile):
    if success and (
        command_code in fault_profile.force_local_nack
        or should_happen(fault_profile.local_nack_rate)
    ):
        success = False
        logging.info("Fault injected: local NACK for %s", command_code)

    if success and response_text and (
        command_code in fault_profile.force_local_res_err
        or should_happen(fault_profile.local_res_err_rate)
    ):
        response_text = "RES ERR"
        logging.info("Fault injected: local RES ERR for %s", command_code)

    return success, response_text


def parse_signed_remote_message(payload_without_prefix):
    text = payload_without_prefix.decode("utf-8", errors="replace")
    if len(text) < 88:
        return None, None, "signed payload too short"

    signature = text[:64]
    salt = text[64:80]
    sequence_and_command = text[80:]
    sequence_length = 0
    while sequence_length < len(sequence_and_command) and sequence_and_command[
        sequence_length
    ].isdigit():
        sequence_length += 1
    sequence = sequence_and_command[:sequence_length]
    command_text = sequence_and_command[sequence_length:].strip()

    if not all(character in "0123456789abcdef" for character in signature.lower()):
        return None, None, "signature is not hex"
    if not all(character in "0123456789abcdef" for character in salt.lower()):
        return None, None, "salt is not hex"
    if not sequence.isdigit():
        return None, None, "sequence is not numeric"
    if not command_text:
        return sequence, None, "missing command body"

    return sequence, command_text, None


def is_reasonable_frequency(frequency_text):
    if len(frequency_text) != 9 or not frequency_text.isdigit():
        return False
    frequency = int(frequency_text)
    return MIN_RADIO_FREQUENCY_HZ <= frequency <= MAX_RADIO_FREQUENCY_HZ


def validate_datetime_parts(parts):
    if len(parts) != 6:
        return False
    if not all(part.lstrip("-").isdigit() for part in parts):
        return False
    try:
        year, month, day, hour, minute, second = [int(part) for part in parts]
        datetime.datetime(year, month, day, hour, minute, second)
        return True
    except Exception:
        return False


def formatted_now_utc_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def make_get_telemetry_response():
    ax = f"{random.uniform(-0.2, 0.2):.3f}"
    ay = f"{random.uniform(-0.2, 0.2):.3f}"
    az = f"{random.uniform(9.6, 9.9):.3f}"
    rx = f"{random.uniform(-0.05, 0.05):.3f}"
    ry = f"{random.uniform(-0.05, 0.05):.3f}"
    rz = f"{random.uniform(-0.05, 0.05):.3f}"
    temperature = f"{random.uniform(18.0, 35.0):.2f}"
    return (
        "RES GTY"
        f" AX {ax} AY {ay} AZ {az}"
        f" RX {rx} RY {ry} RZ {rz}"
        f" T {temperature}"
    )


def make_get_power_response():
    bbv = f"{random.uniform(7.1, 8.3):.2f}"
    bbc = f"{random.uniform(-0.4, 0.6):.2f}"
    ts1 = f"{random.uniform(10.0, 45.0):.2f}"
    ts2 = f"{random.uniform(10.0, 45.0):.2f}"
    ts3 = f"{random.uniform(10.0, 45.0):.2f}"
    five_volt_current = f"{random.uniform(0.0, 2.5):.2f}"
    h1s = random.choice(["true", "false"])
    h2s = random.choice(["true", "false"])
    h3s = random.choice(["true", "false"])
    return (
        "RES GPW"
        f" BBV {bbv} BBC {bbc}"
        f" TS1 {ts1} TS2 {ts2} TS3 {ts3}"
        f" 5VC {five_volt_current}"
        f" H1S {h1s} H2S {h2s} H3S {h3s}"
    )


def make_get_comms_response():
    mode = random.choice(["0", "1", "2"])
    cca = random.randint(80, 150)
    current_milliamps = random.randint(0, 2100)
    return f"RES GRS MODE {mode} CCA {cca} 5V_MA {current_milliamps}"


def parse_command_name_and_args(command_text):
    first_space = command_text.find(" ")
    if first_space < 0:
        return command_text, []

    name = command_text[:first_space]
    rest = command_text[first_space + 1 :]
    if name == "LogArguments":
        return name, [rest]
    return name, [token for token in rest.split(" ") if token != ""]


def handle_remote_command(command_text):
    command_name, args = parse_command_name_and_args(command_text)

    if command_name in {"Invalid", "Unknown"}:
        return False, None, None

    if command_name == "SetClock":
        if not validate_datetime_parts(args):
            return False, None, None
        return True, "RES SRC", None

    if command_name == "BeaconSp":
        if len(args) != 1 or not args[0].isdigit():
            return False, None, None
        return True, "RES SBI", None

    if command_name == "PicTimes":
        if not validate_datetime_parts(args):
            return False, None, None
        return True, "RES SPT", None

    if command_name == "SSDVTimes":
        if not validate_datetime_parts(args):
            return False, None, None
        return True, "RES SST", None

    if command_name == "ClearPayloadQueue":
        if args:
            return False, None, None
        return True, "RES CPQ", None

    if command_name == "ReportT":
        if args:
            return False, None, None
        return True, f"RES GRC {formatted_now_utc_iso()}", None

    if command_name == "GetTelemetry":
        if args:
            return False, None, None
        return True, make_get_telemetry_response(), None

    if command_name == "GetPower":
        if args:
            return False, None, None
        return True, make_get_power_response(), None

    if command_name == "GetComms":
        if args:
            return False, None, None
        return True, make_get_comms_response(), None

    if command_name == "GetBeaconInterval":
        if args:
            return False, None, None
        return True, "RES GBI 60", None

    if command_name == "PayComms":
        if args:
            return False, None, None
        return True, "RES PYC", None

    if command_name == "TweeSlee":
        if args:
            return False, None, None
        return True, "RES TSL", None

    if command_name == "Watchdog":
        if args:
            return False, None, None
        return True, "RES WDG", None

    if command_name == "ModifyMode":
        if len(args) != 1 or args[0] not in {"0", "1", "2"}:
            return False, None, None
        return True, f"RES RMM {args[0]}", None

    if command_name == "ModifyCCA":
        if len(args) != 1 or len(args[0]) != 3 or not args[0].isdigit():
            return False, None, None
        return True, "RES RMC", None

    if command_name == "NoOperate":
        if args:
            return False, None, None
        return True, "RES NOP", None

    if command_name == "SendTestPacket":
        if args:
            return False, None, None
        return True, "RES STP test", None

    if command_name == "UnsetClock":
        if args:
            return False, None, None
        return True, "RES URC", None

    if command_name == "LogArguments":
        argument_text = args[0] if args else ""
        return True, f"RES LCA {argument_text}", None

    return False, None, None


def handle_local_command(transmission):
    command_byte = transmission[:1]
    body = transmission[1:]

    if command_byte == DOPPLER_FREQUENCIES:
        try:
            body_text = body.decode("utf-8", errors="replace")
            tokens = body_text.split(" ")
            if len(tokens) != 2:
                return False, "D", None
            transmit_frequency = tokens[0]
            receive_frequency = tokens[1]
            if not (
                is_reasonable_frequency(transmit_frequency)
                and is_reasonable_frequency(receive_frequency)
            ):
                return False, "D", None
            return True, "D", f"RES D {transmit_frequency} {receive_frequency}"
        except Exception:
            return False, "D", None

    if command_byte == MODIFY_MODE:
        try:
            index_text = body.decode("utf-8", errors="replace")
            if len(index_text) != 1 or index_text not in {"0", "1", "2"}:
                return False, "C", None
            return True, "C", f"RES C {index_text}"
        except Exception:
            return False, "C", None

    if command_byte == STATUS:
        status_text = (
            "RES 9 "
            "Freq A:435000000 Freq B:435000000 Version:sim-v2 "
            "Overcurrent:false 5V Current:123 5V Current (Max):201 "
            "Shape:0x23 Baud Rate:9600 il2p_enabled:1 framing:0x06 "
            "CCA threshold:120 Pwr%:100"
        )
        return True, "9", status_text

    if command_byte == CALLSIGN:
        return True, "E", None

    return False, "?", None


def handle_transmission(serial_connection, fault_profile, transmission):
    match transmission:
        case _ if transmission.startswith(AVIONICS_DATA):
            sequence, command_text, parse_error = parse_signed_remote_message(
                transmission[1:]
            )
            if parse_error:
                logging.warning("Ignoring malformed remote payload: %s", parse_error)
                return

            success, response_text, _ = handle_remote_command(command_text)
            command_name, _ = parse_command_name_and_args(command_text)
            success, response_text = apply_remote_faults(
                command_name, success, response_text, fault_profile
            )

            random_delay(ACK_DELAY_MIN_SECONDS, ACK_DELAY_MAX_SECONDS)
            ack_or_nack_for_remote(serial_connection, sequence, is_ack=success)

            if not success:
                return

            if should_happen(fault_profile.drop_response_rate):
                logging.info("Fault injected: remote response dropped for %s", command_name)
                return

            random_delay(RES_DELAY_MIN_SECONDS, RES_DELAY_MAX_SECONDS)
            send_remote_response(serial_connection, response_text)
        case _:
            success, command_code, response_text = handle_local_command(transmission)
            if command_code == "?":
                logging.debug("Unknown frame payload: %r", transmission)
                return
            success, response_text = apply_local_faults(
                command_code, success, response_text, fault_profile
            )

            random_delay(ACK_DELAY_MIN_SECONDS, ACK_DELAY_MAX_SECONDS)
            if success:
                send_local_ack(serial_connection, command_code)
            else:
                send_local_nack(serial_connection, command_code)

            if not success or response_text is None:
                return

            if should_happen(fault_profile.drop_response_rate):
                logging.info("Fault injected: local response dropped for %s", command_code)
                return

            random_delay(RES_DELAY_MIN_SECONDS, RES_DELAY_MAX_SECONDS)
            send_local_response(serial_connection, response_text)


def processor(serial_connection, fault_profile):
    while True:
        try:
            transmission = read_kiss_payload(serial_connection)
            if not transmission:
                continue
            logging.debug("Received frame payload: %r", transmission)
        except Exception:
            continue

        try:
            handle_transmission(serial_connection, fault_profile, transmission)
        except Exception as error:
            logging.error("Error processing transmission: %s", error)
            break


def parse_args():
    parser = argparse.ArgumentParser(description="SilverSat ground radio simulator")
    parser.add_argument("--port", default=DEFAULT_PORT, help="Serial port path")
    parser.add_argument(
        "--baud-rate", type=int, default=DEFAULT_BAUD_RATE, help="Serial baud rate"
    )
    parser.add_argument(
        "--fault-profile",
        choices=["none", "light", "moderate", "aggressive"],
        default="none",
        help="Fault profile preset",
    )
    parser.add_argument("--remote-nack-rate", type=float)
    parser.add_argument("--remote-res-err-rate", type=float)
    parser.add_argument("--local-nack-rate", type=float)
    parser.add_argument("--local-res-err-rate", type=float)
    parser.add_argument("--drop-response-rate", type=float)
    parser.add_argument(
        "--force-remote-nack",
        default="",
        help="Comma-separated remote commands to always NACK, e.g. SetClock,ReportT",
    )
    parser.add_argument(
        "--force-remote-res-err",
        default="",
        help="Comma-separated remote commands to always return RES ERR",
    )
    parser.add_argument(
        "--force-local-nack",
        default="",
        help="Comma-separated local command codes to always NACK, e.g. D,C,9",
    )
    parser.add_argument(
        "--force-local-res-err",
        default="",
        help="Comma-separated local command codes to always return RES ERR",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible faults")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.seed is not None:
        random.seed(arguments.seed)

    profile = build_fault_profile(arguments)
    logging.info(
        "Starting radio simulator on %s @ %d with profile=%s",
        arguments.port,
        arguments.baud_rate,
        arguments.fault_profile,
    )
    logging.info(
        "Fault overrides: remote_nack=%.3f remote_res_err=%.3f local_nack=%.3f local_res_err=%.3f drop_res=%.3f",
        profile.remote_nack_rate,
        profile.remote_res_err_rate,
        profile.local_nack_rate,
        profile.local_res_err_rate,
        profile.drop_response_rate,
    )

    radio_serial = open_serial_with_retry(arguments.port, arguments.baud_rate)
    processor(radio_serial, profile)