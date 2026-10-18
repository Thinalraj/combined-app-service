"""ZERO-02: serialized MT-SICS preparation; never equate tare with zero.

I0 reports supported commands. TST3 is an internal sensitivity test; its
deviation may be in the device's definition units, not grams or percent.
C3 is internal adjustment. Z/ZI set zero. No command is assumed supported.
Run this file directly for a weight-service-only diagnostic client.
Protocol reference (availability is checked on the actual device):
https://www.mt.com/dam/product_organizations/industry/apw/generic/11781363_La_MAN_RM_MTSICS-APW_en.pdf
"""
import copy
import math
import shlex
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

DEFAULTS = {"empty_limit_g": 0.10, "zero_tolerance_g": 0.01,
            "max_spread_g": 0.02, "internal_mode": "auto"}


def validate_settings(values):
    result = dict(DEFAULTS)
    if not isinstance(values, dict):
        raise ValueError("Expected preparation settings")
    for key in ("empty_limit_g", "zero_tolerance_g", "max_spread_g"):
        value = values.get(key, result[key])
        if isinstance(value, bool):
            raise ValueError("Invalid " + key)
        value = float(value)
        if not math.isfinite(value) or not 0 < value <= 5:
            raise ValueError(key + " must be positive and at most 5 g")
        result[key] = value
    if result["zero_tolerance_g"] > result["empty_limit_g"]:
        raise ValueError("Zero tolerance must not exceed empty-pan limit")
    mode = values.get("internal_mode", "auto")
    if mode not in {"auto", "test", "adjust", "skip"}:
        raise ValueError("Unknown internal operation")
    result["internal_mode"] = mode
    return result


def grams(weight, unit):
    factors = {"g": 1.0, "mg": 0.001, "kg": 1000.0}
    if unit not in factors or not math.isfinite(float(weight)):
        raise ValueError("Unsupported or invalid scale unit: " + str(unit))
    return float(weight) * factors[unit]


def stable_average(ser, read_weight, count=10, interval=0.1, timeout=20):
    values, skipped, source_unit = [], 0, None
    deadline = time.monotonic() + timeout
    while len(values) < count and time.monotonic() < deadline:
        try:
            reading = read_weight(ser)
        except RuntimeError:
            values.clear()
            skipped += 1
            time.sleep(interval)
            continue
        native = reading.get("source_unit", reading["unit"])
        if source_unit is not None and native != source_unit:
            raise RuntimeError("Scale unit changed during sampling")
        source_unit = native
        if reading["status"] != "S":
            values.clear()
            skipped += 1
        else:
            value = float(reading["weight"])
            if not math.isfinite(value):
                raise RuntimeError("Non-finite scale reading")
            values.append(value)
        if len(values) < count:
            time.sleep(interval)
    if len(values) != count:
        raise RuntimeError(f"Could not obtain {count} consecutive stable scale readings")
    return {"average": statistics.mean(values), "std_g": statistics.pstdev(values),
        "minimum": min(values), "maximum": max(values), "range": max(values)-min(values),
        "samples": values, "samples_requested": count, "samples_valid": count,
        "stable_samples": count, "dynamic_samples": 0, "discarded_readings": skipped,
        "unit": "g", "source_unit": source_unit}


class CommandTimeout(RuntimeError):
    pass


def transaction(ser, command, timeout=10, log=None):
    """Write once, then wait through B/progress responses for the terminal reply."""
    ser.reset_input_buffer()
    ser.write((command + "\r\n").encode("ascii"))
    ser.flush()
    deadline, replies = time.monotonic() + timeout, []
    while time.monotonic() < deadline:
        raw = ser.readline().decode("ascii", errors="replace").strip()
        if not raw:
            continue
        if log:
            log(command, raw)
        if raw in {"ES", "ET", "EL"}:
            raise RuntimeError(command + " rejected: " + raw)
        try:
            parts = shlex.split(raw)
        except ValueError:
            raise RuntimeError("Malformed scale response: " + raw)
        if len(parts) < 2 or parts[0] != command:
            continue
        replies.append(parts)
        status = parts[1]
        if status in {"I", "L", "+", "-"}:
            raise RuntimeError(command + " failed: " + raw)
        if status == "A" or (command == "ZI" and status in {"S", "D"}):
            return replies
    raise CommandTimeout(command + " did not report completion before timeout")


class Preparation:
    def __init__(self, open_serial, read_weight, serial_lock):
        self.open_serial, self.read_weight, self.serial_lock = open_serial, read_weight, serial_lock
        self.lock = threading.Lock()
        self.state = {"state": "idle", "stage": "idle", "message": "Not prepared", "result": None}
        self.startup_internal = None
        self.last_device = None

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.state)
            result["startup_internal"] = copy.deepcopy(self.startup_internal)
            return result

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def device_disconnected(self):
        # A later connection must repeat the startup operation, even in the same process.
        with self.lock:
            self.startup_internal = None

    def blocked(self):
        state = self.snapshot()
        return state["state"] == "running" or bool(state.get("needs_recovery"))

    def start(self, empty_confirmed, settings, repeat_internal=False):
        if empty_confirmed is not True:
            raise ValueError("Remove every item and confirm that the pan is empty")
        settings = validate_settings(settings)
        with self.lock:
            if self.state["state"] == "running":
                return False
            recovery = bool(self.state.get("needs_recovery"))
            if repeat_internal:
                # A failed repeat must not fall back to the pre-move startup result.
                self.startup_internal = None
            self.state = {"id": uuid.uuid4().hex, "state": "running", "stage": "waiting",
                "message": "Keep the pan empty until preparation finishes", "result": None,
                "needs_recovery": recovery, "log": [], "settings": settings}
        threading.Thread(target=self._worker, args=(settings, repeat_internal), daemon=True).start()
        return True

    def _log(self, command, response):
        with self.lock:
            if len(self.state["log"]) < 600:
                self.state["log"].append({"command": command, "response": response[:500]})

    def _worker(self, settings, repeat_internal=False):
        commands, active = set(), None
        try:
            with self.serial_lock, self.open_serial() as ser:
                ser.timeout = 0.25
                self.update(stage="capabilities", message="Reading supported balance commands")
                rows = transaction(ser, "I0", timeout=15, log=self._log)
                commands = {row[3] for row in rows if len(row) >= 4}
                zero = "Z" if "Z" in commands else "ZI" if "ZI" in commands else None
                if not zero:
                    raise RuntimeError("Balance does not advertise Z/ZI; no zero command was sent")
                device = transaction(ser, "I2", log=self._log)[-1][2:] if "I2" in commands else []
                if self.last_device is not None and device != self.last_device:
                    self.device_disconnected()
                self.last_device = device
                self.update(stage="empty", message="Checking the empty-pan reading")
                # Clearing a previous tare reveals a load which a net-zero reading can hide.
                if "TAC" in commands:
                    transaction(ser, "TAC", log=self._log)
                initial = stable_average(ser, self.read_weight, count=5)
                if abs(initial["average"]) > settings["empty_limit_g"] or initial["range"] > settings["max_spread_g"]:
                    raise RuntimeError("Empty-pan reading is outside the configured limit; remove item or inspect zero offset")
                mode = settings["internal_mode"]
                command = ("TST3" if "TST3" in commands else None) if mode == "auto" else {"test": "TST3", "adjust": "C3", "skip": None}[mode]
                internal = {"status": "skipped" if mode == "skip" else "unsupported", "command": None}
                if self.startup_internal and not repeat_internal:
                    internal = {**copy.deepcopy(self.startup_internal), "status": "already_completed_this_startup"}
                    command = None
                if command:
                    if command not in commands:
                        raise RuntimeError("Requested internal operation is not supported: " + command)
                    self.update(stage="internal", message=f"Running {command}; waiting for its completion reply")
                    active = command
                    reply = transaction(ser, command, timeout=90, log=self._log)[-1]
                    active = None
                    internal = {"status": "completed", "command": command,
                        "deviation_raw": " ".join(reply[2:]) if command == "TST3" else None,
                        "deviation_unit": "device definition units; not assumed g or %" if command == "TST3" else None,
                        "completed_at": datetime.now(timezone.utc).isoformat()}
                    # In memory only: service restart or observed disconnection requires a new check.
                    with self.lock:
                        self.startup_internal = copy.deepcopy(internal)
                self.update(stage="zero", message="Setting actual zero; do not place an item yet")
                active = zero
                transaction(ser, zero, timeout=30, log=self._log)
                active = None
                self.update(stage="residual", message="Averaging 10 consecutive stable readings after zero")
                residual = stable_average(ser, self.read_weight, count=10)
                result = {"device": device, "commands": sorted(commands), "internal": internal,
                    "zero_command": zero, "initial": initial, "residual": residual,
                    "settings": settings, "zero_verified": abs(residual["average"]) <= settings["zero_tolerance_g"] and residual["range"] <= settings["max_spread_g"],
                    "verified_at": datetime.now(timezone.utc).isoformat()}
                self.update(result=result)
                if not result["zero_verified"]:
                    raise RuntimeError("Post-zero residual or spread exceeds the configured limit")
                note = "Internal operation " + internal["status"] + ". " if internal["status"] in {"unsupported", "skipped"} else ""
                self.update(state="ready", stage="ready", needs_recovery=False,
                            message=note + "Zero verified. You may place the item.")
        except Exception as exc:
            if isinstance(exc, OSError) or (isinstance(exc, CommandTimeout) and active is not None):
                with self.lock:
                    self.startup_internal = None
            # A timeout after starting an operation may leave the balance busy.
            # Block ordinary readings until a subsequent preparation completes.
            self.update(state="failed", stage="failed", message=str(exc),
                        needs_recovery=bool(self.snapshot().get("needs_recovery")) or
                        (isinstance(exc, CommandTimeout) and active is not None))


if __name__ == "__main__":
    import argparse
    import json
    import urllib.request
    parser = argparse.ArgumentParser(description="Weight-service-only preparation checker; no other sensors")
    parser.add_argument("--url", default="http://127.0.0.1:8002")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--pan-empty", action="store_true")
    args = parser.parse_args()
    if args.prepare and not args.pan_empty:
        parser.error("--prepare requires --pan-empty after physically emptying the pan")
    if args.prepare:
        request = urllib.request.Request(args.url + "/preparation/start", data=json.dumps({"pan_empty_confirmed": True}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
    while True:
        with urllib.request.urlopen(args.url + "/preparation/status", timeout=5) as response:
            result = json.load(response)
        if not args.prepare or result["state"] != "running":
            print(json.dumps(result, indent=2))
            break
        print(result["stage"] + ": " + result["message"], flush=True)
        time.sleep(1)
