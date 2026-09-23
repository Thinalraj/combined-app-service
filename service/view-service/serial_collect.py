from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

try:
    import serial
except ImportError:
    serial = None


DEFAULT_PORTS = ["/dev/ttyACM0"]
PORT_CHANNEL_MAP = {
    "/dev/ttyACM0": "ch1",
}
CHANNEL_COMMANDS = {
    "ch1": "R",
    "ch2": "S",
}
DEVICE_ALIASES = {
    "primary_voltage": "ch1",
    "primary_current": "ch1",
    "primary": "ch1",
    "ch1": "ch1",
    "secondary_voltage": "ch2",
    "secondary_volatge": "ch2",
    "secondary": "ch2",
    "ch2": "ch2",
}
MODE_WAIT_TIME = 0.2
RMS_WAIT_TIME = 0.15
SAMPLE_GAP_TIME = 0.05


@dataclass
class CollectionResult:
    ok: bool
    channels: dict[str, list[dict[str, Any]]]
    errors: list[str]
    frequency_steps: list[dict[str, Any]] | None = None


def normalize_device(device: str) -> str | None:
    return DEVICE_ALIASES.get(str(device).strip().lower())


def parse_packet(line: str, fallback_channel: str | None = None) -> tuple[str, dict[str, Any]]:
    text = line.strip()
    if not text:
        raise ValueError("empty packet")

    payload = json.loads(text)
    if isinstance(payload, (int, float)):
        if fallback_channel is None:
            raise ValueError("numeric packet requires fallback channel")
        return fallback_channel, {
            "device": fallback_channel,
            "rms": float(payload) / 1000.0,
            "std": 0.0,
            "quality": 1.0,
            "unit": "V",
        }

    if not isinstance(payload, dict):
        raise ValueError("packet must be object or numeric JSON")

    channel = normalize_device(payload.get("device", ""))
    if channel is None:
        channel = fallback_channel
    if channel is None:
        raise ValueError(f"unknown device label: {payload.get('device')}")

    return channel, {
        "device": payload.get("device", channel),
        "rms": float(payload["rms"]),
        "std": float(payload.get("std", 0.0)),
        "quality": float(payload.get("quality", 1.0)),
        "unit": payload.get("unit", "V"),
    }


def parse_response_line(line: str, fallback_channel: str) -> tuple[str, dict[str, Any]]:
    text = line.strip()
    if not text:
        raise ValueError("empty response")

    try:
        return parse_packet(text, fallback_channel=fallback_channel)
    except (json.JSONDecodeError, KeyError, ValueError):
        try:
            rms = float(text) / 1000.0
        except ValueError as exc:
            raise ValueError(f"unrecognized response: {text}") from exc
        return fallback_channel, {
            "device": fallback_channel,
            "rms": rms,
            "std": 0.0,
            "quality": 1.0,
            "unit": "V",
        }


def open_serial_handles(
    ports: list[str] | None = None,
    baudrate: int = 115200,
    timeout: float = 0.3,
) -> tuple[list[Any], list[str]]:
    active_ports = ports or DEFAULT_PORTS
    handles: list[Any] = []
    errors: list[str] = []

    if serial is None:
        return handles, ["pyserial is not installed"]

    for port in active_ports:
        try:
            handle = serial.Serial(port, baudrate=baudrate, timeout=timeout, write_timeout=timeout)
            try:
                handle.reset_input_buffer()
                handle.reset_output_buffer()
            except Exception:
                pass
            handles.append(handle)
        except serial.SerialException as exc:
            errors.append(f"{port}: {exc}")

    return handles, errors


def close_serial_handles(handles: list[Any]) -> None:
    for handle in handles:
        try:
            handle.close()
        except Exception:
            pass


def read_single_rms_response(handle: Any, read_timeout_seconds: float = 1.5) -> tuple[str | None, dict[str, Any] | None, str | None]:
    deadline = time.monotonic() + read_timeout_seconds
    fallback_channel = PORT_CHANNEL_MAP.get(getattr(handle, "port", ""), "ch1")
    last_error = None

    while time.monotonic() < deadline:
        try:
            raw = handle.readline()
        except serial.SerialException as exc:
            return None, None, f"{handle.port}: read error: {exc}"

        if not raw:
            continue

        try:
            channel, packet = parse_response_line(raw.decode("utf-8", errors="replace"), fallback_channel)
            packet["source"] = handle.port
            return channel, packet, None
        except ValueError as exc:
            last_error = f"{handle.port}: invalid response: {exc}"

    return None, None, last_error or f"{handle.port}: timed out waiting for RMS response"


def extract_last_reply(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def summarize_packets(packets: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not packets:
        return None
    values = [float(packet["rms"]) for packet in packets if isinstance(packet.get("rms"), (int, float))]
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = math.sqrt(variance)
    return {
        "rms": round(mean, 6),
        "std": round(std, 6),
        "quality": round(sum(float(packet.get("quality", 1.0)) for packet in packets) / len(packets), 3),
        "unit": packets[-1].get("unit", "V"),
        "source": packets[-1].get("source", ""),
        "sample_count": len(values),
    }


def send_raw_command(
    handle: Any,
    cmd: str,
    wait_seconds: float,
    require_reply: bool = True,
) -> tuple[str | None, str | None]:
    try:
        handle.reset_input_buffer()
    except Exception:
        pass

    try:
        handle.write(cmd.encode("utf-8"))
        handle.flush()
    except serial.SerialException as exc:
        return None, f"{handle.port}: unable to send {cmd.strip()}: {exc}"

    time.sleep(wait_seconds)

    try:
        reply = handle.read_all().decode("utf-8", errors="ignore").strip()
    except serial.SerialException as exc:
        return None, f"{handle.port}: read error: {exc}"

    parsed = extract_last_reply(reply)
    if not parsed:
        if not require_reply:
            return "", None
        return None, f"{handle.port}: blank reply for {cmd.strip()}"
    return parsed, None


def collect_channel_command(
    handle: Any,
    command: str,
    fallback_channel: str,
    frequency_command: str,
    wait_seconds: float,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    reply, error = send_raw_command(handle, command, wait_seconds)
    if error:
        return None, None, error
    try:
        channel, packet = parse_response_line(reply or "", fallback_channel)
    except ValueError as exc:
        return None, None, f"{handle.port}: invalid {fallback_channel} response: {exc}"
    packet["source"] = handle.port
    packet["frequency_command"] = frequency_command
    packet["command"] = command
    return channel, packet, None


def send_frequency_mode(
    frequency_command: str,
    ports: list[str] | None = None,
    baudrate: int = 115200,
    mode_wait_seconds: float = MODE_WAIT_TIME,
) -> dict[str, Any]:
    handles, open_errors = open_serial_handles(ports=ports, baudrate=baudrate, timeout=0.5)
    replies: dict[str, str] = {}
    errors = list(open_errors)

    if not handles:
        return {"ok": False, "command": frequency_command, "replies": replies, "errors": errors or ["No serial ports opened"]}

    try:
        for handle in handles:
            reply, error = send_raw_command(handle, frequency_command, mode_wait_seconds, require_reply=False)
            port = getattr(handle, "port", "unknown")
            if error:
                errors.append(error)
                continue
            replies[port] = reply or ""
    finally:
        close_serial_handles(handles)

    return {
        "ok": bool(replies),
        "command": frequency_command,
        "replies": replies,
        "errors": errors,
    }


def collect_frequency_sequence(
    frequency_commands: list[str] | None = None,
    ports: list[str] | None = None,
    baudrate: int = 115200,
    settle_seconds: float = 5.0,
    read_timeout_seconds: float = 1.5,
    samples_per_frequency: int = 1,
    channel_commands: dict[str, str] | None = None,
    required_channels: tuple[str, ...] = ("ch1", "ch2"),
) -> CollectionResult:
    commands = frequency_commands or ["f1", "f2", "f3"]
    active_channel_commands = channel_commands or CHANNEL_COMMANDS
    channels: dict[str, list[dict[str, Any]]] = {"ch1": [], "ch2": []}
    errors: list[str] = []
    frequency_steps: list[dict[str, Any]] = []
    handles, open_errors = open_serial_handles(ports=ports, baudrate=baudrate, timeout=read_timeout_seconds)
    errors.extend(open_errors)

    if not handles:
        return CollectionResult(False, channels, errors or ["No serial ports opened"], frequency_steps)

    try:
        for command in commands:
            step_channels: dict[str, dict[str, Any]] = {}
            for handle in handles:
                try:
                    handle.write(command.encode("utf-8"))
                    handle.flush()
                except serial.SerialException as exc:
                    errors.append(f"{handle.port}: unable to send {command}: {exc}")

            time.sleep(settle_seconds)

            for _ in range(max(1, samples_per_frequency)):
                for handle in handles:
                    for fallback_channel, channel_command in active_channel_commands.items():
                        channel, packet, error = collect_channel_command(
                            handle,
                            channel_command,
                            fallback_channel,
                            command,
                            RMS_WAIT_TIME,
                        )
                        if error:
                            errors.append(error)
                            continue
                        if channel is None or packet is None:
                            continue
                        channels[channel].append(packet)
                        step_channels[channel] = {
                            "rms": packet["rms"],
                            "std": packet.get("std", 0.0),
                            "quality": packet.get("quality", 1.0),
                            "unit": packet.get("unit", "V"),
                            "source": packet.get("source", ""),
                            "command": packet.get("command", channel_command),
                            "sample_count": len([item for item in channels[channel] if item.get("frequency_command") == command]),
                        }
                time.sleep(SAMPLE_GAP_TIME)

            step_summaries = {}
            for channel_name in ("ch1", "ch2"):
                packets = [item for item in channels[channel_name] if item.get("frequency_command") == command]
                summary = summarize_packets(packets)
                if summary is not None:
                    step_summaries[channel_name] = summary

            frequency_steps.append(
                {
                    "frequency_command": command,
                    "settle_seconds": settle_seconds,
                    "channels": step_summaries or step_channels,
                }
            )
    finally:
        close_serial_handles(handles)

    ok = all(bool(channels.get(channel_name)) for channel_name in required_channels)
    for channel_name in required_channels:
        if not channels.get(channel_name):
            errors.append(f"No {channel_name.upper()} packets collected")

    return CollectionResult(ok, channels, errors, frequency_steps)


def collect_live_rms_burst(
    frequency_command: str,
    sample_count: int = 10,
    ports: list[str] | None = None,
    baudrate: int = 115200,
    mode_wait_seconds: float = MODE_WAIT_TIME,
    rms_wait_seconds: float = RMS_WAIT_TIME,
    sample_gap_seconds: float = SAMPLE_GAP_TIME,
) -> CollectionResult:
    channels: dict[str, list[dict[str, Any]]] = {"ch1": [], "ch2": []}
    errors: list[str] = []
    frequency_steps: list[dict[str, Any]] = []
    handles, open_errors = open_serial_handles(ports=ports, baudrate=baudrate, timeout=0.5)
    errors.extend(open_errors)

    if not handles:
        return CollectionResult(False, channels, errors or ["No serial ports opened"], frequency_steps)

    try:
        step_channels: dict[str, dict[str, Any]] = {}
        for handle in handles:
            reply, error = send_raw_command(handle, frequency_command, mode_wait_seconds, require_reply=False)
            if error:
                errors.append(error)
                continue
            step_channels[PORT_CHANNEL_MAP.get(getattr(handle, "port", ""), "ch1")] = {
                "mode_reply": reply,
            }

        for _ in range(max(1, sample_count)):
            for handle in handles:
                for fallback_channel, channel_command in CHANNEL_COMMANDS.items():
                    channel, packet, error = collect_channel_command(
                        handle,
                        channel_command,
                        fallback_channel,
                        frequency_command,
                        rms_wait_seconds,
                    )
                    if error:
                        errors.append(error)
                        continue
                    if channel is None or packet is None:
                        continue
                    channels[channel].append(packet)
                    step_channels[channel] = {
                        "rms": packet["rms"],
                        "std": packet.get("std", 0.0),
                        "quality": packet.get("quality", 1.0),
                        "unit": packet.get("unit", "V"),
                        "source": packet.get("source", ""),
                        "command": packet.get("command", channel_command),
                    }
            time.sleep(sample_gap_seconds)

        frequency_steps.append(
            {
                "frequency_command": frequency_command,
                "settle_seconds": mode_wait_seconds,
                "channels": {key: value for key, value in step_channels.items() if "rms" in value},
            }
        )
    finally:
        close_serial_handles(handles)

    ok = bool(channels["ch1"]) and bool(channels["ch2"])
    if not channels["ch1"]:
        errors.append("No CH1 RMS samples collected")
    if not channels["ch2"]:
        errors.append("No CH2 RMS samples collected")
    return CollectionResult(ok, channels, errors, frequency_steps)


def collect_sensor_window(
    duration_seconds: float,
    ports: list[str] | None = None,
    baudrate: int = 115200,
) -> CollectionResult:
    active_ports = ports or DEFAULT_PORTS
    handles, errors = open_serial_handles(ports=active_ports, baudrate=baudrate, timeout=0.03)
    channels: dict[str, list[dict[str, Any]]] = {"ch1": [], "ch2": []}

    if not handles:
        return CollectionResult(False, channels, errors or ["No serial ports opened"])

    start = time.monotonic()
    try:
        while time.monotonic() - start < duration_seconds:
            for handle in handles:
                try:
                    raw = handle.readline()
                except serial.SerialException as exc:
                    errors.append(f"{handle.port}: read error: {exc}")
                    continue

                if not raw:
                    continue

                fallback_channel = PORT_CHANNEL_MAP.get(getattr(handle, "port", ""))
                try:
                    channel, packet = parse_packet(raw.decode("utf-8", errors="replace"), fallback_channel=fallback_channel)
                    packet["source"] = handle.port
                    channels[channel].append(packet)
                except (json.JSONDecodeError, ValueError, KeyError) as exc:
                    errors.append(f"{handle.port}: invalid packet: {exc}")

            time.sleep(0.002)
    finally:
        close_serial_handles(handles)

    ok = bool(channels["ch1"]) and bool(channels["ch2"])
    if not channels["ch1"]:
        errors.append("No CH1 packets collected")
    if not channels["ch2"]:
        errors.append("No CH2 packets collected")

    return CollectionResult(ok, channels, errors)


def summarize_channel(samples: list[dict[str, Any]], default_unit: str) -> dict[str, Any]:
    values = [sample["rms"] for sample in samples]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = math.sqrt(variance)
    tolerance = max(std * 3, 0.005 if default_unit.startswith("A") else 0.006)
    unit = samples[-1].get("unit") or default_unit

    return {
        "mean": round(mean, 6),
        "std": round(std, 6),
        "tolerance": round(tolerance, 6),
        "unit": f"{unit} RMS",
        "sample_count": len(samples),
        "last_device": samples[-1].get("device", ""),
        "source": samples[-1].get("source", ""),
    }
