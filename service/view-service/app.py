from __future__ import annotations

import csv
import json
import math
import os
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from brass_classifier import (
    CH1_F1_RULE_PARAMS,
    CH1_F3_RULE_PARAMS,
    CH2_F1_F3_COVERAGE_RANGE,
    CH2_F1_F3_MODEL_NAME,
    CH2_F1_F3_THICKNESS_RANGE,
    CH2_F1_PARAMS,
    CH2_F3_PARAMS,
    BrassModelParams,
    BrassSurfaceParams,
    brass_surface,
    classify_brass,
    classify_brass_ch2_f1_f3,
)
from serial_collect import collect_frequency_sequence, collect_live_rms_burst, send_frequency_mode, summarize_channel, summarize_packets

try:
    import joblib
except Exception:
    joblib = None

try:
    import serial
except ImportError:
    serial = None

try:
    from scipy.optimize import curve_fit
except Exception:
    curve_fit = None


BASE_DIR = Path(__file__).resolve().parent
MEASUREMENTS_FILE = BASE_DIR / "measurements.json"
CALIBRATION_FILE = BASE_DIR / "calibration.json"
TEACHING_FILE = BASE_DIR / "teaching_library.json"
SETTINGS_FILE = BASE_DIR / "settings.json"
CLASSIFIER_MODEL_FILE = BASE_DIR / "classifier_model.json"
VALIDATION_RESULTS_FILE = BASE_DIR / "validation_results.json"
VALIDATION_REPORTS_DIR = BASE_DIR / "validation_reports"
DAQ_OFFSET_FILE = BASE_DIR / "daq_offset.json"
FREQUENCY_RF_GOLD_MODEL_FILE = BASE_DIR / "model_gold_frequency_best_20260630_RF.joblib"
FREQUENCY_RF_PURITY_MODEL_FILE = BASE_DIR / "model_purity_frequency_best_20260630_RF.joblib"
FREQUENCY_RF_GOLD_FALLBACK_FILE = BASE_DIR.parent / "teaching_master_build_20260630" / "model_gold_frequency_best_20260630_RF.joblib"
FREQUENCY_RF_PURITY_FALLBACK_FILE = BASE_DIR.parent / "teaching_master_build_20260630" / "model_purity_frequency_best_20260630_RF.joblib"
FREQUENCY_RF_MODEL_VERSION = "frequency_rf_20260630"
FREQUENCY_RF_FEATURE_NAMES = [
    "f1_delta_ch1",
    "f1_delta_ch2",
    "f2_delta_ch1",
    "f2_delta_ch2",
    "f3_delta_ch1",
    "f3_delta_ch2",
    "f1_delta_pct",
    "f2_delta_pct",
    "f3_delta_pct",
    "weight_g",
    "thickness_mm",
    "contact_area_ratio",
]
ADMIN_PIN = "242218"
LOAD_CELL_PORT = "/dev/ttyUSB0"
LOAD_CELL_BAUD = 9600
LOAD_CELL_READ_COMMAND = "SI"
LOAD_CELL_ZERO_COMMAND = "TI"
LOAD_CELL_READ_WAIT_SECONDS = 0.25
LOAD_CELL_STABLE_RETRY_SECONDS = 0.5
LOAD_CELL_STABLE_MAX_ATTEMPTS = 8
LOAD_CELL_HANDLE = None
LOAD_CELL_LOCK = threading.Lock()
DAQ_LOCK = threading.Lock()
SERVICE_TIMEOUT_SECONDS = 8.0
KNN_FEATURE_KEYS = [
    "delta_ratio",
    "delta_ch2_pct",
    "delta_ch2_per_g",
    "delta_ch1_per_g",
    "weight_g",
]
KNN_WEIGHTS = {
    "delta_ratio": 5.0,
    "delta_ch2_pct": 4.0,
    "delta_ch2_per_g": 3.0,
    "delta_ch1_per_g": 2.0,
    "weight_g": 1.0,
}
MAHALANOBIS_FEATURE_KEYS = [
    "weight_g",
    "thickness_mm",
    "contact_area_ratio",
    "f1_ch1_delta_pct",
    "f2_ch1_delta_pct",
    "f3_ch1_delta_pct",
    "f1_ch2_delta_pct",
    "f2_ch2_delta_pct",
    "f3_ch2_delta_pct",
]
CLASSIFIER_METHOD = "regularized pooled-covariance Mahalanobis classifier"
CLASSIFIER_VERSION = 1
CLASSIFIER_REGULARIZATION = 0.08
CLASSIFIER_MIN_ACTIVE_SAMPLES = 5
CLASSIFIER_THRESHOLD_K = 2.5
CLASSIFIER_MIN_THRESHOLD = 1.5
CLASSIFIER_UNCERTAIN_GAP = 0.30
CLASSIFIER_DEFAULT_ALGORITHM = "two_pass_frequency_rf"
CLASSIFIER_ALGORITHMS = {
    "mahalanobis": {
        "label": "Mahalanobis",
        "method": "regularized pooled-covariance Mahalanobis classifier",
    },
    "knn_cluster": {
        "label": "KNN Cluster",
        "method": "normalized centroid KNN cluster classifier",
    },
    "hybrid_hill_knn": {
        "label": "Hill + KNN",
        "method": "Hill geometry residual model with normalized KNN fallback",
    },
    "two_pass_gold_gate": {
        "label": "Two-pass Gold Gate",
        "method": "two-pass gold-like gate with gold purity KNN classifier",
    },
    "two_pass_compact_gate": {
        "label": "Two-pass Compact Gate",
        "method": "two-pass gold-like gate with compact sum, slope, ratio and per-gram KNN classifier",
    },
    "binary_brass_ch1_f1": {
        "label": "Binary Brass CH1 F1",
        "method": "binary brass compatibility classifier using CH1 F1 physics response surface",
    },
    "binary_brass_ch2_f1_f3": {
        "label": "Binary Brass CH2 F1/F3",
        "method": "two-feature brass classifier using CH2 F1 and CH2 F3 normalized surface residuals",
    },
    "two_pass_frequency_rf": {
        "label": "Gold Standard",
        "method": "two-pass frequency-vector random forest classifier",
    },
}
COMPACT_TWO_PASS_FEATURE_KEYS = [
    "weight_g",
    "thickness_mm",
    "contact_area_ratio",
    "ch1_sum",
    "ch2_sum",
    "ch1_slope",
    "ch2_slope",
    "ch1_mean",
    "ch2_mean",
    "ch2_ch1_ratio",
    "ch1_sum_per_g",
    "ch2_sum_per_g",
    "ch1_abs_sum_per_g",
    "ch2_abs_sum_per_g",
]
KNN_CLUSTER_K = 5
KNN_CLUSTER_CENTROID_WEIGHT = 0.70
KNN_CLUSTER_NEIGHBOR_WEIGHT = 0.30
HYBRID_KNN_K = 3
HILL_MIN_SAMPLES = 6
HILL_MIN_UNIQUE_AREA = 4
TWO_PASS_K = 3
TWO_PASS_GATE_UNCERTAIN_GAP = 0.03
TWO_PASS_GOLD_LABELS = {"Gold 999", "Gold 916", "Gold 750"}
TWO_PASS_NON_GOLD_BASES = {
    "brass",
    "copper",
    "silver",
    "stainless steel",
    "tungsten",
    "gold-plated brass",
    "gold-plated copper",
}
MIN_SAME_SHAPE_RECORDS = 3
FALLBACK_SHAPE_PENALTY = 0.35
COIL_DIAMETER_MM = 70.0
COIL_RADIUS_MM = COIL_DIAMETER_MM / 2.0
COIL_AREA_MM2 = math.pi * (COIL_RADIUS_MM ** 2)
LATEST_SENSOR_STATE = {
    "ch1": {
        "device": "primary_current",
        "rms": 0.0,
        "std": 0.0,
        "quality": 0.0,
        "unit": "A",
        "source": "not connected",
        "valid": False,
        "error": "CH1 serial node not connected",
    },
    "ch2": {
        "device": "secondary_voltage",
        "rms": 0.0,
        "std": 0.0,
        "quality": 0.0,
        "unit": "V",
        "source": "not connected",
        "valid": False,
        "error": "CH2 serial node not connected",
    },
    "timestamp": None,
    "status": "waiting_for_sensor_node",
}

DEFAULT_DAQ_OFFSET = {
    "enabled": True,
    "version": 1,
    "description": "DAQ compatibility correction applied after RMS acquisition",
    "ch1": {
        "scale": 1.049,
        "offset": 0.0,
    },
    "ch2": {
        "scale": 1.112,
        "offset": 0.0,
    },
}

app = Flask(__name__, static_folder=None)


def save_daq_offset_settings(data: dict) -> None:
    with DAQ_OFFSET_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_daq_offset_settings() -> dict:
    if not DAQ_OFFSET_FILE.exists():
        save_daq_offset_settings(DEFAULT_DAQ_OFFSET)
        return json.loads(json.dumps(DEFAULT_DAQ_OFFSET))

    try:
        with DAQ_OFFSET_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        save_daq_offset_settings(DEFAULT_DAQ_OFFSET)
        return json.loads(json.dumps(DEFAULT_DAQ_OFFSET))

    if not isinstance(data, dict):
        save_daq_offset_settings(DEFAULT_DAQ_OFFSET)
        return json.loads(json.dumps(DEFAULT_DAQ_OFFSET))

    merged = json.loads(json.dumps(DEFAULT_DAQ_OFFSET))
    merged["enabled"] = bool(data.get("enabled", merged["enabled"]))
    merged["version"] = int(parse_float(data.get("version"), merged["version"]) or merged["version"])
    merged["description"] = str(data.get("description", merged["description"]))
    for channel in ("ch1", "ch2"):
        source = data.get(channel) if isinstance(data.get(channel), dict) else {}
        merged[channel]["scale"] = parse_float(source.get("scale"), merged[channel]["scale"]) or merged[channel]["scale"]
        merged[channel]["offset"] = parse_float(source.get("offset"), merged[channel]["offset"]) or 0.0
    return merged


def daq_correction_metadata(settings: dict | None = None) -> dict:
    data = settings or load_daq_offset_settings()
    enabled = bool(data.get("enabled", True))
    ch1 = data.get("ch1", {}) if isinstance(data.get("ch1"), dict) else {}
    ch2 = data.get("ch2", {}) if isinstance(data.get("ch2"), dict) else {}
    return {
        "enabled": enabled,
        "version": int(parse_float(data.get("version"), 1) or 1),
        "ch1_scale": parse_float(ch1.get("scale"), 1.0) if enabled else 1.0,
        "ch1_offset": parse_float(ch1.get("offset"), 0.0) if enabled else 0.0,
        "ch2_scale": parse_float(ch2.get("scale"), 1.0) if enabled else 1.0,
        "ch2_offset": parse_float(ch2.get("offset"), 0.0) if enabled else 0.0,
        "applied_at": "after_rms_before_features",
    }


def corrected_rms_value(channel: str, raw_rms: float | None, settings: dict | None = None) -> float | None:
    value = parse_float(raw_rms)
    if value is None:
        return None
    data = settings or load_daq_offset_settings()
    enabled = bool(data.get("enabled", True))
    scale = 1.0
    offset = 0.0
    if enabled:
        channel_settings = data.get(channel, {}) if isinstance(data.get(channel), dict) else {}
        scale = parse_float(channel_settings.get("scale"), 1.0) or 1.0
        offset = parse_float(channel_settings.get("offset"), 0.0) or 0.0
    return (value * scale) + offset


def raw_rms_mean_from_packets(samples: list[dict]) -> float | None:
    values = [parse_float(sample.get("rms_raw")) for sample in samples if parse_float(sample.get("rms_raw")) is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def apply_daq_correction_to_packets(samples: list[dict], channel: str, settings: dict | None = None) -> None:
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        raw_rms = parse_float(sample.get("rms"))
        corrected = corrected_rms_value(channel, raw_rms, settings=settings)
        sample["rms_raw"] = round(raw_rms, 6) if raw_rms is not None else None
        if corrected is not None:
            sample["rms"] = round(corrected, 6)


def rebuild_corrected_frequency_steps(channels: dict[str, list[dict]], previous_steps: list[dict] | None = None) -> list[dict]:
    settle_by_frequency = {}
    for step in previous_steps or []:
        if not isinstance(step, dict):
            continue
        command = str(step.get("frequency_command") or "").lower()
        if command:
            settle_by_frequency[command] = step.get("settle_seconds")
    frequency_commands = []
    for channel_name in ("ch1", "ch2"):
        for packet in channels.get(channel_name, []):
            command = str(packet.get("frequency_command") or "").lower()
            if command and command not in frequency_commands:
                frequency_commands.append(command)

    steps = []
    for command in frequency_commands:
        step_channels = {}
        for channel_name in ("ch1", "ch2"):
            packets = [item for item in channels.get(channel_name, []) if str(item.get("frequency_command") or "").lower() == command]
            summary = summarize_packets(packets)
            if summary is None:
                continue
            latest_packet = packets[-1]
            step_channels[channel_name] = {
                **summary,
                "command": latest_packet.get("command", ""),
                "rms_raw": raw_rms_mean_from_packets(packets),
            }
        steps.append(
            {
                "frequency_command": command,
                "settle_seconds": settle_by_frequency.get(command, 5.0),
                "channels": step_channels,
            }
        )
    return steps


def apply_daq_correction_to_collection(collection, settings: dict | None = None):
    if collection is None or not hasattr(collection, "channels"):
        return collection
    active_settings = settings or load_daq_offset_settings()
    for channel_name in ("ch1", "ch2"):
        apply_daq_correction_to_packets(collection.channels.get(channel_name, []), channel_name, settings=active_settings)
    if hasattr(collection, "frequency_steps") and isinstance(collection.frequency_steps, list):
        collection.frequency_steps = rebuild_corrected_frequency_steps(collection.channels, collection.frequency_steps)
    return collection


def load_settings() -> dict:
    default_settings = {
        "acquisition_mode": "daq",
        "confidence_threshold_pct": 40.0,
        "multi_frequencies_khz": [10.0, 20.0, 30.0],
        "active_frequency_slot": 1,
        "classifier_algorithm": CLASSIFIER_DEFAULT_ALGORITHM,
        "service_mode_enabled": True,
        "weight_service_url": "http://127.0.0.1:8002",
        "vision_service_url": "http://127.0.0.1:8003",
        "signal_service_url": "http://127.0.0.1:8001",
    }
    if not SETTINGS_FILE.exists():
        return default_settings

    with SETTINGS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return default_settings

    mode = data.get("acquisition_mode", "daq")
    if mode not in {"simulator", "daq"}:
        mode = "daq"
    multi_frequencies = data.get("multi_frequencies_khz", [10.0, 20.0, 30.0])
    if not isinstance(multi_frequencies, list):
        multi_frequencies = [10.0, 20.0, 30.0]
    parsed_multi = []
    for value in multi_frequencies[:3]:
        parsed = parse_float(value)
        if parsed is not None and parsed > 0:
            parsed_multi.append(round(parsed, 3))
    while len(parsed_multi) < 3:
        parsed_multi.append([10.0, 20.0, 30.0][len(parsed_multi)])

    active_slot_raw = data.get("active_frequency_slot", 1)
    try:
        active_slot = int(active_slot_raw)
    except (TypeError, ValueError):
        active_slot = 1
    if active_slot < 1 or active_slot > 3:
        active_slot = 1

    confidence_threshold = parse_float(data.get("confidence_threshold_pct"), 40.0) or 40.0
    confidence_threshold = max(0.0, min(100.0, confidence_threshold))
    classifier_algorithm = str(data.get("classifier_algorithm", CLASSIFIER_DEFAULT_ALGORITHM))
    if classifier_algorithm not in CLASSIFIER_ALGORITHMS:
        classifier_algorithm = CLASSIFIER_DEFAULT_ALGORITHM
    return {
        **default_settings,
        **data,
        "acquisition_mode": mode,
        "confidence_threshold_pct": confidence_threshold,
        "multi_frequencies_khz": parsed_multi,
        "active_frequency_slot": active_slot,
        "classifier_algorithm": classifier_algorithm,
    }


def save_settings(settings: dict) -> None:
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2, ensure_ascii=False)
        file.write("\n")


def acquisition_mode() -> str:
    return load_settings()["acquisition_mode"]


def selected_classifier_algorithm() -> str:
    return load_settings().get("classifier_algorithm", CLASSIFIER_DEFAULT_ALGORITHM)


def service_mode_enabled() -> bool:
    return bool(load_settings().get("service_mode_enabled", True))


def service_base_url(name: str) -> str:
    settings = load_settings()
    key = f"{name}_service_url"
    return str(settings.get(key, "")).rstrip("/")


def service_json_request(
    method: str,
    base_url: str,
    path: str,
    query: dict | None = None,
    payload: dict | None = None,
    timeout: float = SERVICE_TIMEOUT_SECONDS,
) -> dict:
    if not base_url:
        raise RuntimeError("Service URL is not configured")

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request_obj = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request_obj, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} is unavailable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"{url} timed out") from exc

    try:
        decoded = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{url} returned non-JSON response") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{url} returned unexpected JSON payload")
    return decoded


def service_binary_get(base_url: str, path: str, timeout: float = SERVICE_TIMEOUT_SECONDS) -> tuple[bytes, str]:
    if not base_url:
        raise RuntimeError("Service URL is not configured")
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    request_obj = urllib.request.Request(url, headers={"Accept": "image/jpeg"}, method="GET")
    try:
        with urllib.request.urlopen(request_obj, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type() or "application/octet-stream"
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} is unavailable: {exc.reason}") from exc


def normalize_weight_service_payload(payload: dict) -> dict:
    ok = bool(payload.get("success", payload.get("ok", True)))
    weight = parse_float(payload.get("weight_g"))
    if weight is None:
        weight = parse_float(payload.get("average"))
    if weight is None:
        weight = parse_float(payload.get("weight"))
    if weight is None:
        ok = False
    sample_count = int(parse_float(payload.get("samples_valid"), parse_float(payload.get("sample_count"), 0)) or 0)
    minimum = parse_float(payload.get("minimum"), parse_float(payload.get("min_g")))
    maximum = parse_float(payload.get("maximum"), parse_float(payload.get("max_g")))
    range_value = parse_float(payload.get("range"))
    std_g = parse_float(payload.get("std_g"))
    if std_g is None and range_value is not None:
        std_g = range_value / 2.0
    return {
        "ok": ok,
        "weight_g": round(weight, 3) if weight is not None else None,
        "std_g": round(std_g or 0.0, 4),
        "min_g": round(minimum, 3) if minimum is not None else None,
        "max_g": round(maximum, 3) if maximum is not None else None,
        "unit": payload.get("unit", "g"),
        "stable": int(parse_float(payload.get("dynamic_samples"), 0) or 0) == 0,
        "status": "service_average",
        "sample_count": sample_count,
        "requested_sample_count": int(parse_float(payload.get("samples_requested"), sample_count) or sample_count),
        "stable_sample_count": int(parse_float(payload.get("stable_samples"), 0) or 0),
        "dynamic_sample_count": int(parse_float(payload.get("dynamic_samples"), 0) or 0),
        "raw_response": payload.get("raw", ""),
        "source": "weight_service",
        "service_payload": payload,
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
    }


def read_weight_service_average(sample_count: int = 10) -> dict:
    del sample_count
    payload = service_json_request("GET", service_base_url("weight"), "/weight/average", timeout=20.0)
    return normalize_weight_service_payload(payload)


def tare_weight_service() -> dict:
    payload = service_json_request("POST", service_base_url("weight"), "/tare", timeout=5.0)
    ok = bool(payload.get("success", payload.get("ok", True)))
    return {
        "ok": ok,
        "zero_command": "TI",
        "zero_response": payload.get("response", payload.get("raw_response", "")),
        "zero_error": "" if ok else payload.get("detail", "Unable to tare load cell"),
        "message": "Tare command sent" if ok else "Unable to tare load cell",
        "source": "weight_service",
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "service_payload": payload,
    }


def vision_type_for_shape(shape: str) -> str:
    normalized = str(shape or "other").strip().lower()
    if normalized in {"coin", "bar", "chain", "ring", "bangle"}:
        return normalized
    return "ornament"


def normalize_vision_payload(payload: dict, shape: str) -> dict:
    detected = bool(payload.get("detected", payload.get("ok", True)))
    diameter = parse_float(payload.get("diameter_mm"), parse_float(payload.get("equivalent_diameter_mm")))
    bbox = payload.get("bounding_box_mm") if isinstance(payload.get("bounding_box_mm"), dict) else {}
    width = parse_float(payload.get("width_mm"), parse_float(bbox.get("width")))
    length = parse_float(payload.get("length_mm"), parse_float(bbox.get("height")))
    surface_area = parse_float(payload.get("surface_area_mm2"), parse_float(payload.get("projected_area_mm2")))
    shape_mode = vision_type_for_shape(shape)
    if shape_mode == "coin" and diameter is not None:
        width = diameter
        length = diameter
    return {
        "ok": detected,
        "shape": shape,
        "vision_type": shape_mode,
        "width_mm": round(width, 3) if width is not None else None,
        "length_mm": round(length, 3) if length is not None else None,
        "diameter_mm": round(diameter, 3) if diameter is not None else None,
        "surface_area_mm2": round(surface_area, 3) if surface_area is not None else None,
        "estimated_depth_mm": rounded_or_none(parse_float(payload.get("estimated_depth_mm"))),
        "image_url": payload.get("image_url") or "/api/vision/image/detected",
        "message": payload.get("message", "Vision measurement completed" if detected else "No object detected"),
        "source": "vision_service",
        "service_payload": payload,
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
    }


def read_vision_service_size(shape: str) -> dict:
    payload = service_json_request(
        "GET",
        service_base_url("vision"),
        "/size",
        query={"type": vision_type_for_shape(shape)},
        timeout=20.0,
    )
    return normalize_vision_payload(payload, shape)


def normalize_signal_service_step(payload: dict, frequency_command: str, frequency_hz: float, sample_count: int) -> dict:
    stats = payload.get("statistics") if isinstance(payload.get("statistics"), dict) else {}
    rms_stats = stats.get("ac_rms_v") if isinstance(stats.get("ac_rms_v"), dict) else {}
    mean = parse_float(rms_stats.get("mean"), parse_float(payload.get("ac_rms_v")))
    std = parse_float(rms_stats.get("std_dev"), parse_float(rms_stats.get("plus_minus"), 0.0))
    if mean is None:
        raise RuntimeError("Signal service response did not include ac_rms_v")
    # Digilent service currently returns one measured waveform. Mirror it into CH1
    # and leave CH2 available for the later second-channel service contract.
    return {
        "frequency_command": frequency_command,
        "frequency_hz": frequency_hz,
        "settle_seconds": 5.0,
        "channels": {
            "ch1": {
                "rms": round(mean, 6),
                "std": round(std or 0.0, 6),
                "quality": 1.0,
                "unit": "V",
                "source": "signal_service",
                "command": "measurement/average",
                "sample_count": int(parse_float(payload.get("sample_size"), sample_count) or sample_count),
            },
            "ch2": {
                "rms": round(mean, 6),
                "std": round(std or 0.0, 6),
                "quality": 1.0,
                "unit": "V",
                "source": "signal_service_mirrored",
                "command": "measurement/average",
                "sample_count": int(parse_float(payload.get("sample_size"), sample_count) or sample_count),
            },
        },
        "raw_service_payload": payload,
    }


def collect_signal_service_frequency_summaries(
    target_sample_count: int = 30,
    frequency_commands: list[str] | None = None,
) -> dict:
    settings = load_settings()
    frequencies_khz = settings.get("multi_frequencies_khz", [10.0, 20.0, 30.0])
    commands = frequency_commands or ["f1", "f2", "f3"]
    frequency_steps = []
    errors = []
    for command in commands:
        try:
            slot = max(1, min(3, int(str(command).lower().replace("f", ""))))
        except ValueError:
            slot = 1
        frequency_hz = float(frequencies_khz[slot - 1]) * 1000.0
        try:
            payload = service_json_request(
                "GET",
                service_base_url("signal"),
                "/measurement/average",
                query={
                    "frequency_hz": int(round(frequency_hz)),
                    "sample_size": target_sample_count,
                    "interval_s": 0.05,
                    "amplitude_v": 1.0,
                },
                timeout=45.0,
            )
            frequency_steps.append(normalize_signal_service_step(payload, command, frequency_hz, target_sample_count))
        except RuntimeError as exc:
            errors.append(f"{command}: {exc}")

    if not frequency_steps:
        return {
            "ok": False,
            "mode": "signal_service",
            "ch1": None,
            "ch2": None,
            "errors": errors or ["No signal service readings collected"],
            "frequency_sequence": [],
            "daq_correction": daq_correction_metadata(),
        }

    raw_collection = type("ServiceCollection", (), {})()
    raw_collection.channels = {"ch1": [], "ch2": []}
    raw_collection.frequency_steps = frequency_steps
    for step in frequency_steps:
        for channel_name, summary in step["channels"].items():
            raw_collection.channels[channel_name].append({
                "rms": summary["rms"],
                "std": summary["std"],
                "quality": summary["quality"],
                "unit": summary["unit"],
                "device": channel_name,
                "source": summary["source"],
                "frequency_command": step["frequency_command"],
            })
    apply_daq_correction_to_collection(raw_collection)
    return {
        "ok": True,
        "mode": "signal_service",
        "ch1": summarize_optional_channel(raw_collection.channels["ch1"], "V"),
        "ch2": summarize_optional_channel(raw_collection.channels["ch2"], "V"),
        "errors": errors[-10:],
        "frequency_sequence": format_frequency_sequence(raw_collection.frequency_steps or []),
        "daq_correction": daq_correction_metadata(),
        "raw_measurement": {
            "ch1_rms_raw": raw_rms_mean_from_packets(raw_collection.channels["ch1"]),
            "ch2_rms_raw": raw_rms_mean_from_packets(raw_collection.channels["ch2"]),
        },
    }


def load_measurements() -> list[dict]:
    if not MEASUREMENTS_FILE.exists():
        return []

    with MEASUREMENTS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    return data


def save_measurements(records: list[dict]) -> None:
    with MEASUREMENTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_calibration() -> dict:
    if not CALIBRATION_FILE.exists():
        return {}

    with CALIBRATION_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, dict) else {}


def save_calibration(record: dict) -> None:
    with CALIBRATION_FILE.open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_teaching_records() -> list[dict]:
    if not TEACHING_FILE.exists():
        return []

    with TEACHING_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, list) else []


def save_teaching_records(records: list[dict]) -> None:
    with TEACHING_FILE.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_classifier_model() -> dict:
    if not CLASSIFIER_MODEL_FILE.exists():
        return {}

    with CLASSIFIER_MODEL_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, dict) else {}


def save_classifier_model(record: dict) -> None:
    with CLASSIFIER_MODEL_FILE.open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False)
        file.write("\n")


def load_validation_results() -> list[dict]:
    if not VALIDATION_RESULTS_FILE.exists():
        return []

    with VALIDATION_RESULTS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, list) else []


def save_validation_results(records: list[dict]) -> None:
    with VALIDATION_RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")


def calculate_delta(sample: dict, calibration: dict, channel: str) -> dict[str, float | None]:
    calibration_mean = calibration.get(channel, {}).get("mean")
    sample_mean = sample.get("mean")
    if not isinstance(calibration_mean, (int, float)) or not isinstance(sample_mean, (int, float)):
        return {"mean_delta": None, "mean_delta_pct": None}

    delta = sample_mean - calibration_mean
    delta_pct = (delta / calibration_mean * 100) if calibration_mean else None
    return {
        "mean_delta": round(delta, 6),
        "mean_delta_pct": round(delta_pct, 3) if delta_pct is not None else None,
    }


def format_measurement(summary: dict) -> str:
    mean = parse_float(summary.get("mean")) if isinstance(summary, dict) else None
    if mean is None:
        return "--"
    return f"{mean:.6f} {summary.get('unit', '')}".strip()


def format_std(summary: dict) -> str:
    std = parse_float(summary.get("std")) if isinstance(summary, dict) else None
    if std is None:
        return "--"
    return f"{std:.6f} {summary.get('unit', '')}".strip()


def parse_float(value, default: float | None = None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        token = value.strip().split(" ")[0]
        try:
            return float(token)
        except ValueError:
            return default
    return default


def build_geometry(width_mm: float, length_mm: float, thickness_mm: float = 0.0, shape: str = "standard") -> dict:
    safe_width = max(width_mm, 0.0)
    safe_length = max(length_mm, 0.0)
    safe_thickness = max(thickness_mm, 0.0)
    shape_mode = normalize_label_text(shape)
    if shape_mode == "coin":
        radius = safe_width / 2.0
        sample_area_mm2 = math.pi * (radius ** 2)
        safe_length = safe_width
    elif shape_mode in {"ring", "bangle"}:
        inner_radius = safe_width / 2.0
        outer_radius = safe_length / 2.0
        sample_area_mm2 = max(0.0, math.pi * ((outer_radius ** 2) - (inner_radius ** 2)))
    else:
        sample_area_mm2 = safe_width * safe_length
    contact_area_ratio = (sample_area_mm2 / COIL_AREA_MM2) if COIL_AREA_MM2 > 0 else 0.0
    return {
        "width_mm": round(safe_width, 3),
        "length_mm": round(safe_length, 3),
        "thickness_mm": round(safe_thickness, 3),
        "sample_area_mm2": round(sample_area_mm2, 3),
        "coil_area_mm2": round(COIL_AREA_MM2, 3),
        "contact_area_ratio": round(contact_area_ratio, 6),
    }


def normalize_material_and_purity(material_label: str) -> tuple[str, int | None]:
    text = str(material_label or "").strip()
    parts = text.split()
    if len(parts) >= 2 and parts[-1].isdigit():
        return " ".join(parts[:-1]), int(parts[-1])
    return text or "Other", None


def build_measurement_features(
    ch1: dict,
    ch2: dict,
    calibration: dict,
    weight_grams: float,
    shape: str,
    geometry: dict | None = None,
) -> dict:
    ch1_air = parse_float(calibration.get("ch1", {}).get("mean"))
    ch2_air = parse_float(calibration.get("ch2", {}).get("mean"))
    ch1_rms = parse_float(ch1.get("mean"))
    ch2_rms = parse_float(ch2.get("mean"))
    delta_ch1 = (ch1_rms - ch1_air) if ch1_rms is not None and ch1_air is not None else None
    delta_ch2 = (ch2_rms - ch2_air) if ch2_rms is not None and ch2_air is not None else None
    delta_ch1_pct = (delta_ch1 / ch1_air * 100) if delta_ch1 is not None and ch1_air else None
    delta_ch2_pct = (delta_ch2 / ch2_air * 100) if delta_ch2 is not None and ch2_air else None
    raw_ratio = (ch1_rms / ch2_rms) if ch1_rms not in (None, 0) and ch2_rms not in (None, 0) else None
    delta_ratio = (delta_ch1 / delta_ch2) if delta_ch1 is not None and delta_ch2 not in (None, 0) else None
    delta_ch1_per_g = (delta_ch1 / weight_grams) if delta_ch1 is not None and weight_grams > 0 else None
    delta_ch2_per_g = (delta_ch2 / weight_grams) if delta_ch2 is not None and weight_grams > 0 else None
    geometry = geometry or {}
    return {
        "ch1_rms": ch1_rms,
        "ch2_rms": ch2_rms,
        "delta_ch1": round(delta_ch1, 6) if delta_ch1 is not None else None,
        "delta_ch2": round(delta_ch2, 6) if delta_ch2 is not None else None,
        "delta_ch1_pct": round(delta_ch1_pct, 3) if delta_ch1_pct is not None else None,
        "delta_ch2_pct": round(delta_ch2_pct, 3) if delta_ch2_pct is not None else None,
        "raw_ratio": round(raw_ratio, 6) if raw_ratio is not None else None,
        "delta_ratio": round(delta_ratio, 6) if delta_ratio is not None else None,
        "delta_ch1_per_g": round(delta_ch1_per_g, 6) if delta_ch1_per_g is not None else None,
        "delta_ch2_per_g": round(delta_ch2_per_g, 6) if delta_ch2_per_g is not None else None,
        "weight_g": weight_grams,
        "shape": shape,
        "width_mm": geometry.get("width_mm"),
        "length_mm": geometry.get("length_mm"),
        "thickness_mm": geometry.get("thickness_mm"),
        "sample_area_mm2": geometry.get("sample_area_mm2"),
        "coil_area_mm2": geometry.get("coil_area_mm2"),
        "contact_area_ratio": geometry.get("contact_area_ratio"),
    }


def teaching_record_features(record: dict) -> dict:
    measurement = record.get("measurement") if isinstance(record.get("measurement"), dict) else {}
    features = record.get("features") if isinstance(record.get("features"), dict) else {}
    calibration = record.get("calibration") if isinstance(record.get("calibration"), dict) else {}

    ch1_rms = parse_float(record.get("ch1_rms"), parse_float(measurement.get("ch1_rms")))
    ch2_rms = parse_float(record.get("ch2_rms"), parse_float(measurement.get("ch2_rms")))
    ch1_air = parse_float(calibration.get("ch1_air"))
    ch2_air = parse_float(calibration.get("ch2_air"))
    delta_ch1 = parse_float(record.get("ch1_delta"), parse_float(features.get("delta_ch1")))
    delta_ch2 = parse_float(record.get("ch2_delta"), parse_float(features.get("delta_ch2")))
    if delta_ch1 is None and ch1_rms is not None and ch1_air is not None:
        delta_ch1 = ch1_rms - ch1_air
    if delta_ch2 is None and ch2_rms is not None and ch2_air is not None:
        delta_ch2 = ch2_rms - ch2_air

    delta_ch1_pct = parse_float(record.get("ch1_delta_pct"), parse_float(features.get("delta_ch1_pct")))
    delta_ch2_pct = parse_float(record.get("ch2_delta_pct"), parse_float(features.get("delta_ch2_pct")))
    if delta_ch1_pct is None and delta_ch1 is not None and ch1_air:
        delta_ch1_pct = delta_ch1 / ch1_air * 100
    if delta_ch2_pct is None and delta_ch2 is not None and ch2_air:
        delta_ch2_pct = delta_ch2 / ch2_air * 100

    raw_ratio = parse_float(record.get("ratio"), parse_float(features.get("raw_ratio")))
    if raw_ratio is None and ch1_rms not in (None, 0) and ch2_rms not in (None, 0):
        raw_ratio = ch1_rms / ch2_rms
    delta_ratio = parse_float(features.get("delta_ratio"))
    if delta_ratio is None and delta_ch1 is not None and delta_ch2 not in (None, 0):
        delta_ratio = delta_ch1 / delta_ch2

    weight_g = parse_float(record.get("weight_g"), parse_float(record.get("weight"), 0.0))
    delta_ch1_per_g = parse_float(features.get("delta_ch1_per_g"))
    delta_ch2_per_g = parse_float(features.get("delta_ch2_per_g"))
    if delta_ch1_per_g is None and delta_ch1 is not None and weight_g and weight_g > 0:
        delta_ch1_per_g = delta_ch1 / weight_g
    if delta_ch2_per_g is None and delta_ch2 is not None and weight_g and weight_g > 0:
        delta_ch2_per_g = delta_ch2 / weight_g

    return {
        "delta_ratio": delta_ratio,
        "delta_ch2_pct": delta_ch2_pct,
        "delta_ch2_per_g": delta_ch2_per_g,
        "delta_ch1_per_g": delta_ch1_per_g,
        "weight_g": weight_g,
        "ch1_rms": ch1_rms,
        "ch2_rms": ch2_rms,
        "shape": record.get("shape", "Other"),
    }


def knn_confidence(best_distance: float, second_distance: float | None) -> tuple[str, float]:
    if second_distance is None:
        return ("LOW", 0.0)
    nearest_gap = second_distance - best_distance
    if nearest_gap > 0.75:
        return ("HIGH", nearest_gap)
    if nearest_gap >= 0.30:
        return ("MEDIUM", nearest_gap)
    return ("LOW", nearest_gap)


def confidence_from_gap(nearest_gap: float) -> int:
    if nearest_gap > 0.75:
        return 92
    if nearest_gap >= 0.30:
        return 76
    return 58


def confidence_from_top_matches(matches: list[dict]) -> float:
    if not matches:
        return 0.0
    top = matches[:3]
    similarities = []
    for item in top:
        score = parse_float(item.get("match_score"), 0.0) or 0.0
        similarities.append(math.exp(-score))
    total = sum(similarities)
    if total <= 0:
        return 0.0
    return round((similarities[0] / total) * 100, 2)


def reference_matches(features: dict, records: list[dict]) -> tuple[list[dict], str]:
    prepared = []
    for record in records:
        f = teaching_record_features(record)
        if all(isinstance(parse_float(f.get(key)), (int, float)) for key in KNN_FEATURE_KEYS):
            prepared.append((record, f))

    if not prepared:
        return ([], "shape-filtered normalized weighted KNN")

    sample_shape = str(features.get("shape", "")).strip().lower()
    same_shape = [(record, f) for record, f in prepared if str(f.get("shape", "")).strip().lower() == sample_shape]
    use_fallback_shapes = len(same_shape) < MIN_SAME_SHAPE_RECORDS
    candidates = prepared if use_fallback_shapes else same_shape

    # Normalize features by teaching-library statistics.
    feature_stats = {}
    for key in KNN_FEATURE_KEYS:
        vals = [float(f[key]) for _, f in prepared if isinstance(parse_float(f.get(key)), (int, float))]
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance) if variance > 0 else 1.0
        feature_stats[key] = (mean, std)

    sample_z = {}
    for key in KNN_FEATURE_KEYS:
        mean, std = feature_stats[key]
        sample_z[key] = (float(features[key]) - mean) / std

    matches = []
    for record, f in candidates:
        distance_sq = 0.0
        for key in KNN_FEATURE_KEYS:
            mean, std = feature_stats[key]
            ref_z = (float(f[key]) - mean) / std
            distance_sq += KNN_WEIGHTS[key] * ((sample_z[key] - ref_z) ** 2)
        distance = math.sqrt(distance_sq)
        if use_fallback_shapes and str(f.get("shape", "")).strip().lower() != sample_shape:
            distance += FALLBACK_SHAPE_PENALTY
        matches.append({**record, "match_score": round(distance, 6)})

    return (sorted(matches, key=lambda item: item["match_score"]), "shape-filtered normalized weighted KNN")


def matrix_inverse(matrix: list[list[float]]) -> list[list[float]] | None:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        return None

    augmented = [
        [float(matrix[row][col]) for col in range(size)] + [1.0 if row == col else 0.0 for col in range(size)]
        for row in range(size)
    ]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]

        pivot_value = augmented[col][col]
        augmented[col] = [value / pivot_value for value in augmented[col]]

        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0:
                continue
            augmented[row] = [
                augmented[row][idx] - factor * augmented[col][idx]
                for idx in range(size * 2)
            ]

    return [row[size:] for row in augmented]


def vector_mean(rows: list[list[float]]) -> list[float]:
    if not rows:
        return []
    count = len(rows)
    return [sum(row[idx] for row in rows) / count for idx in range(len(rows[0]))]


def covariance_matrix(rows: list[list[float]], mean: list[float]) -> list[list[float]]:
    size = len(mean)
    if len(rows) <= 1:
        return [[1.0 if row == col else 0.0 for col in range(size)] for row in range(size)]

    denom = len(rows) - 1
    cov = [[0.0 for _ in range(size)] for _ in range(size)]
    for values in rows:
        diff = [values[idx] - mean[idx] for idx in range(size)]
        for row in range(size):
            for col in range(size):
                cov[row][col] += diff[row] * diff[col] / denom
    return cov


def regularize_covariance(cov: list[list[float]], regularization: float) -> list[list[float]]:
    size = len(cov)
    diag_mean = sum(cov[idx][idx] for idx in range(size)) / size if size else 1.0
    floor = diag_mean if diag_mean > 1e-9 else 1.0
    return [
        [
            cov[row][col] + (regularization * floor if row == col else 0.0)
            for col in range(size)
        ]
        for row in range(size)
    ]


def mahalanobis_distance(values: list[float], centroid: list[float], inv_cov: list[list[float]]) -> float:
    diff = [values[idx] - centroid[idx] for idx in range(len(values))]
    temp = [
        sum(diff[col] * inv_cov[col][row] for col in range(len(values)))
        for row in range(len(values))
    ]
    distance_sq = sum(temp[idx] * diff[idx] for idx in range(len(values)))
    return math.sqrt(max(distance_sq, 0.0))


def mean_and_sample_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, math.sqrt(max(variance, 0.0))


def vector_std(rows: list[list[float]], mean: list[float]) -> list[float]:
    if not rows:
        return []
    if len(rows) < 2:
        return [1.0 for _ in mean]
    std_values = []
    for idx, center in enumerate(mean):
        variance = sum((row[idx] - center) ** 2 for row in rows) / (len(rows) - 1)
        std = math.sqrt(max(variance, 0.0))
        std_values.append(std if std > 1e-9 else 1.0)
    return std_values


def normalize_vector(values: list[float], mean: list[float], std: list[float]) -> list[float]:
    return [
        (values[idx] - mean[idx]) / (std[idx] if abs(std[idx]) > 1e-9 else 1.0)
        for idx in range(len(values))
    ]


def euclidean_distance(values: list[float], centroid: list[float]) -> float:
    return math.sqrt(sum((values[idx] - centroid[idx]) ** 2 for idx in range(len(values))))


def classifier_decision_from_best(
    best: dict,
    second: dict | None,
    accepted: bool,
    uncertain_gap: float,
) -> tuple[str, str, str, bool]:
    gap = (parse_float(second.get("distance")) - parse_float(best.get("distance"))) if second else None
    best_family = best.get("family", material_family(best["material"]))
    second_family = second.get("family", material_family(second["material"])) if second else None
    uncertain = (
        gap is not None
        and gap < uncertain_gap
        and (
            best_family != second_family
            or best_family == "gold"
            or second_family == "gold"
        )
    )

    if not accepted:
        return (
            "Unknown / suspicious sample",
            "unknown",
            f"Nearest class {best['material']} is outside threshold.",
            uncertain,
        )
    if uncertain:
        return (
            "Uncertain",
            "uncertain",
            f"Nearest classes are too close: {best['material']} and {second['material']}.",
            True,
        )
    if best_family == "gold":
        return (
            f"Genuine gold: {best['material']}",
            "genuine_gold",
            f"Accepted within {best['material']} threshold.",
            False,
        )
    if best_family in {"non_gold", "unknown"}:
        return (
            f"Non-gold: {best['material']}" if best_family == "non_gold" else "Unknown / suspicious sample",
            "known_non_gold" if best_family == "non_gold" else "unknown",
            f"Accepted within {best['material']} threshold.",
            False,
        )
    return (
        best["material"],
        "accepted",
        f"Accepted within {best['material']} threshold.",
        False,
    )


def material_family(label: str) -> str:
    normalized = normalize_label_text(label)
    if normalized.startswith("gold "):
        return "gold"
    if normalized in {"brass", "copper", "silver", "tungsten", "stainless steel"}:
        return "non_gold"
    if "plated" in normalized:
        return "non_gold"
    if normalized == "unknown":
        return "unknown"
    return "other"


def class_label_for_record(record: dict) -> str:
    material = record.get("material_base") or record.get("material") or "Unknown"
    purity_value = parse_float(record.get("purity_value"))
    purity = record.get("purity")
    if purity_value is not None:
        return f"{material} {int(purity_value)}"
    if purity and purity not in {"Known", "Unknown", "Enter Later"} and str(purity).strip():
        purity_text = str(purity).strip()
        if purity_text.lower() not in str(material).lower():
            return f"{material} {purity_text}"
    return str(material).strip() or "Unknown"


def frequency_channel_summary(record: dict, frequency: str, channel: str) -> dict:
    for step in record.get("frequency_sequence") or []:
        if str(step.get("frequency_command", "")).lower() != frequency:
            continue
        channels = step.get("channels") if isinstance(step.get("channels"), dict) else {}
        item = channels.get(channel)
        return item if isinstance(item, dict) else {}
    return {}


def calibration_frequency_air(calibration: dict, frequency: str, channel: str) -> dict:
    air = calibration.get("frequency_air") if isinstance(calibration.get("frequency_air"), dict) else {}
    item = air.get(frequency, {}).get(channel, {}) if isinstance(air.get(frequency), dict) else {}
    return item if isinstance(item, dict) else {}


def delta_pct_from_air(value: float | None, air: float | None) -> float | None:
    if value is None or air in (None, 0):
        return None
    return ((value - air) / air) * 100


def mahalanobis_features_from_frequency_sequence(
    frequency_sequence: list[dict],
    calibration: dict,
    weight_g: float,
    thickness_mm: float,
    contact_area_ratio: float,
) -> dict:
    feature_values = {
        "weight_g": weight_g,
        "thickness_mm": thickness_mm,
        "contact_area_ratio": contact_area_ratio,
    }

    pseudo_record = {"frequency_sequence": frequency_sequence}
    for frequency in ("f1", "f2", "f3"):
        for channel in ("ch1", "ch2"):
            sample = parse_float(frequency_channel_summary(pseudo_record, frequency, channel).get("rms"))
            air = parse_float(calibration_frequency_air(calibration, frequency, channel).get("rms"))
            feature_values[f"{frequency}_{channel}_delta_pct"] = (
                round(delta_pct_from_air(sample, air), 3)
                if delta_pct_from_air(sample, air) is not None
                else None
            )
    return feature_values


def mahalanobis_features_from_teaching_record(record: dict, calibration: dict) -> tuple[dict | None, str | None]:
    weight_g = parse_float(record.get("weight_g"), parse_float(record.get("weight")))
    thickness_mm = parse_float(record.get("thickness_mm"))
    contact_area_ratio = parse_float(record.get("contact_area_ratio"))
    if weight_g is None or thickness_mm is None or contact_area_ratio is None:
        return None, "missing geometry or weight"
    if not record.get("frequency_sequence"):
        return None, "missing frequency sequence"

    features = mahalanobis_features_from_frequency_sequence(
        record.get("frequency_sequence") or [],
        calibration,
        weight_g,
        thickness_mm,
        contact_area_ratio,
    )
    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        return None, f"missing features: {', '.join(missing)}"
    return features, None


def vector_from_mahalanobis_features(features: dict) -> list[float]:
    return [float(features[key]) for key in MAHALANOBIS_FEATURE_KEYS]


def frequency_rf_model_paths() -> tuple[Path, Path]:
    gold_path = FREQUENCY_RF_GOLD_MODEL_FILE if FREQUENCY_RF_GOLD_MODEL_FILE.exists() else FREQUENCY_RF_GOLD_FALLBACK_FILE
    purity_path = FREQUENCY_RF_PURITY_MODEL_FILE if FREQUENCY_RF_PURITY_MODEL_FILE.exists() else FREQUENCY_RF_PURITY_FALLBACK_FILE
    return gold_path, purity_path


def load_frequency_rf_models() -> tuple[dict, dict]:
    if joblib is None:
        raise ValueError("joblib is not available. Install scikit-learn and joblib on the Pi to use Gold Standard mode.")
    gold_path, purity_path = frequency_rf_model_paths()
    if not gold_path.exists():
        raise ValueError(f"Gold Standard model file not found: {gold_path.name}")
    if not purity_path.exists():
        raise ValueError(f"Gold Standard purity model file not found: {purity_path.name}")
    gold_model = joblib.load(gold_path)
    purity_model = joblib.load(purity_path)
    if not isinstance(gold_model, dict) or "model" not in gold_model:
        raise ValueError("Gold Standard gold model file is invalid")
    if not isinstance(purity_model, dict) or "model" not in purity_model:
        raise ValueError("Gold Standard purity model file is invalid")
    return gold_model, purity_model


def _frequency_rf_feature_value(
    frequency_sequence: list[dict],
    calibration: dict,
    frequency: str,
    channel: str,
) -> dict[str, float | None]:
    pseudo_record = {"frequency_sequence": frequency_sequence or []}
    measured_rms = parse_float(frequency_channel_summary(pseudo_record, frequency, channel).get("rms"))
    air_rms = parse_float(calibration_frequency_air(calibration, frequency, channel).get("rms"))
    delta = measured_rms - air_rms if measured_rms is not None and air_rms is not None else None
    delta_pct = delta_pct_from_air(measured_rms, air_rms)
    return {
        "measured_rms": measured_rms,
        "air_rms": air_rms,
        "delta": delta,
        "delta_pct": delta_pct,
    }


def build_frequency_rf_feature_payload(
    frequency_sequence: list[dict],
    calibration: dict,
    weight_g: float,
    thickness_mm: float,
    contact_area_ratio: float,
) -> dict:
    feature_map: dict[str, float | list | dict | None] = {
        "weight_g": round(weight_g, 6),
        "thickness_mm": round(thickness_mm, 6),
        "contact_area_ratio": round(contact_area_ratio, 6),
    }
    measured_frequency_values: dict[str, dict] = {}
    calibration_frequency_values: dict[str, dict] = {}

    for frequency in ("f1", "f2", "f3"):
        measured_frequency_values[frequency] = {}
        calibration_frequency_values[frequency] = {}
        ch1 = _frequency_rf_feature_value(frequency_sequence, calibration, frequency, "ch1")
        ch2 = _frequency_rf_feature_value(frequency_sequence, calibration, frequency, "ch2")

        feature_map[f"{frequency}_delta_ch1"] = rounded_or_none(ch1["delta"])
        feature_map[f"{frequency}_delta_ch2"] = rounded_or_none(ch2["delta"])
        avg_pct = None
        if ch1["delta_pct"] is not None and ch2["delta_pct"] is not None:
            avg_pct = (ch1["delta_pct"] + ch2["delta_pct"]) / 2.0
        feature_map[f"{frequency}_delta_pct"] = rounded_or_none(avg_pct, 6)

        measured_frequency_values[frequency]["ch1_rms"] = rounded_or_none(ch1["measured_rms"])
        measured_frequency_values[frequency]["ch2_rms"] = rounded_or_none(ch2["measured_rms"])
        calibration_frequency_values[frequency]["ch1_air_rms"] = rounded_or_none(ch1["air_rms"])
        calibration_frequency_values[frequency]["ch2_air_rms"] = rounded_or_none(ch2["air_rms"])

    feature_vector = []
    missing = []
    for key in FREQUENCY_RF_FEATURE_NAMES:
        value = parse_float(feature_map.get(key))
        if value is None:
            missing.append(key)
            feature_vector.append(None)
        else:
            feature_vector.append(round(value, 6))

    return {
        "feature_names": list(FREQUENCY_RF_FEATURE_NAMES),
        "feature_vector": feature_vector,
        "feature_map": feature_map,
        "missing": missing,
        "measured_frequency_values": measured_frequency_values,
        "calibration_frequency_air": calibration_frequency_values,
    }


def compact_two_pass_features(features: dict) -> dict:
    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        raise ValueError(f"Missing classifier features: {', '.join(missing)}")

    weight_g = parse_float(features.get("weight_g"), 0.0) or 0.0
    f1_ch1 = parse_float(features.get("f1_ch1_delta_pct"), 0.0) or 0.0
    f2_ch1 = parse_float(features.get("f2_ch1_delta_pct"), 0.0) or 0.0
    f3_ch1 = parse_float(features.get("f3_ch1_delta_pct"), 0.0) or 0.0
    f1_ch2 = parse_float(features.get("f1_ch2_delta_pct"), 0.0) or 0.0
    f2_ch2 = parse_float(features.get("f2_ch2_delta_pct"), 0.0) or 0.0
    f3_ch2 = parse_float(features.get("f3_ch2_delta_pct"), 0.0) or 0.0
    ch1_sum = f1_ch1 + f2_ch1 + f3_ch1
    ch2_sum = f1_ch2 + f2_ch2 + f3_ch2
    return {
        "weight_g": weight_g,
        "thickness_mm": parse_float(features.get("thickness_mm"), 0.0) or 0.0,
        "contact_area_ratio": parse_float(features.get("contact_area_ratio"), 0.0) or 0.0,
        "ch1_sum": ch1_sum,
        "ch2_sum": ch2_sum,
        "ch1_slope": f3_ch1 - f1_ch1,
        "ch2_slope": f3_ch2 - f1_ch2,
        "ch1_mean": ch1_sum / 3.0,
        "ch2_mean": ch2_sum / 3.0,
        "ch2_ch1_ratio": ch2_sum / ch1_sum if abs(ch1_sum) > 1e-9 else 0.0,
        "ch1_sum_per_g": ch1_sum / weight_g if weight_g > 0 else 0.0,
        "ch2_sum_per_g": ch2_sum / weight_g if weight_g > 0 else 0.0,
        "ch1_abs_sum_per_g": abs(ch1_sum) / weight_g if weight_g > 0 else 0.0,
        "ch2_abs_sum_per_g": abs(ch2_sum) / weight_g if weight_g > 0 else 0.0,
    }


def vector_from_compact_two_pass_features(features: dict) -> list[float]:
    compact = compact_two_pass_features(features)
    return [float(compact[key]) for key in COMPACT_TWO_PASS_FEATURE_KEYS]


def build_classifier_training_rows(records: list[dict], calibration: dict) -> tuple[list[dict], list[dict]]:
    rows = []
    excluded = []
    for record in records:
        features, reason = mahalanobis_features_from_teaching_record(record, calibration)
        label = class_label_for_record(record)
        if features is None:
            excluded.append({
                "id": record.get("id"),
                "label": label,
                "reason": reason or "unknown reason",
            })
            continue
        rows.append({
            "id": record.get("id"),
            "label": label,
            "shape": record.get("shape", "Other"),
            "features": features,
            "vector": vector_from_mahalanobis_features(features),
        })
    return rows, excluded


def hill_response(area: float, params: dict) -> float:
    smin = parse_float(params.get("smin"), 0.0) or 0.0
    smax = parse_float(params.get("smax"), smin) or smin
    a50 = max(parse_float(params.get("a50"), 1.0) or 1.0, 1e-9)
    n_value = max(parse_float(params.get("n"), 1.0) or 1.0, 1e-6)
    area = max(float(area or 0.0), 1e-9)
    return smin + ((smax - smin) / (1.0 + ((a50 / area) ** n_value)))


def fit_hill_model(points: list[tuple[float, float]]) -> dict | None:
    clean = [(float(area), float(value)) for area, value in points if area and area > 0 and value is not None]
    unique_areas = sorted({round(area, 6) for area, _ in clean})
    if len(clean) < HILL_MIN_SAMPLES or len(unique_areas) < HILL_MIN_UNIQUE_AREA:
        return None

    areas = [area for area, _ in clean]
    values = [value for _, value in clean]
    amin, amax = min(areas), max(areas)
    if amin <= 0 or amax <= amin:
        return None

    a50_candidates = [
        amin + ((amax - amin) * step / 12.0)
        for step in range(1, 12)
    ]
    n_candidates = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]
    best = None
    for a50 in a50_candidates:
        for n_value in n_candidates:
            g_values = [1.0 / (1.0 + ((a50 / max(area, 1e-9)) ** n_value)) for area in areas]
            x0 = [1.0 - g for g in g_values]
            x1 = g_values
            s00 = sum(value * value for value in x0)
            s01 = sum(x0[idx] * x1[idx] for idx in range(len(x0)))
            s11 = sum(value * value for value in x1)
            b0 = sum(x0[idx] * values[idx] for idx in range(len(x0)))
            b1 = sum(x1[idx] * values[idx] for idx in range(len(x1)))
            det = (s00 * s11) - (s01 * s01)
            if abs(det) < 1e-12:
                continue
            smin = ((b0 * s11) - (b1 * s01)) / det
            smax = ((s00 * b1) - (s01 * b0)) / det
            predicted = [
                smin + ((smax - smin) / (1.0 + ((a50 / max(area, 1e-9)) ** n_value)))
                for area in areas
            ]
            mse = sum((predicted[idx] - values[idx]) ** 2 for idx in range(len(values))) / len(values)
            if best is None or mse < best["mse"]:
                best = {
                    "smin": smin,
                    "smax": smax,
                    "a50": a50,
                    "n": n_value,
                    "mse": mse,
                }
    if best is None:
        return None
    return {
        "smin": round(best["smin"], 9),
        "smax": round(best["smax"], 9),
        "a50": round(best["a50"], 9),
        "n": round(best["n"], 6),
        "mse": round(best["mse"], 9),
        "sample_count": len(clean),
        "unique_contact_area_count": len(unique_areas),
    }


def standard_features_with_sums(features: dict) -> dict:
    item = dict(features)
    ch1_values = [parse_float(item.get(f"f{idx}_ch1_delta_pct")) for idx in (1, 2, 3)]
    ch2_values = [parse_float(item.get(f"f{idx}_ch2_delta_pct")) for idx in (1, 2, 3)]
    if all(value is not None for value in ch1_values):
        item["ch1_sum"] = round(sum(ch1_values), 6)
        item["ch1_slope"] = round(ch1_values[2] - ch1_values[0], 6)
    else:
        item["ch1_sum"] = None
        item["ch1_slope"] = None
    if all(value is not None for value in ch2_values):
        item["ch2_sum"] = round(sum(ch2_values), 6)
        item["ch2_slope"] = round(ch2_values[2] - ch2_values[0], 6)
    else:
        item["ch2_sum"] = None
        item["ch2_slope"] = None
    return item


def shape_one_hot(shape: str, categories: list[str]) -> list[float]:
    normalized = normalize_label_text(shape)
    return [1.0 if normalize_label_text(category) == normalized else 0.0 for category in categories]


def hill_key(label: str, shape: str) -> str:
    return f"{normalize_label_text(label)}::{normalize_label_text(shape)}"


def hybrid_features_for_label(features: dict, label: str, shape: str, model: dict | None = None) -> dict:
    item = standard_features_with_sums(features)
    hill_models = model.get("hill_models", {}) if isinstance(model, dict) else {}
    group_model = hill_models.get(hill_key(label, shape)) if isinstance(hill_models, dict) else None
    area = parse_float(item.get("contact_area_ratio"), 0.0) or 0.0
    ch1_sum = parse_float(item.get("ch1_sum"), 0.0) or 0.0
    ch2_sum = parse_float(item.get("ch2_sum"), 0.0) or 0.0
    item["hill_available"] = 0.0
    item["predicted_ch1_sum"] = None
    item["predicted_ch2_sum"] = None
    item["ch1_residual"] = 0.0
    item["ch2_residual"] = 0.0
    if isinstance(group_model, dict) and group_model.get("hill_available"):
        ch1_model = group_model.get("ch1_sum")
        ch2_model = group_model.get("ch2_sum")
        item["hill_available"] = 1.0
        if isinstance(ch1_model, dict):
            predicted_ch1 = hill_response(area, ch1_model)
            item["predicted_ch1_sum"] = round(predicted_ch1, 6)
            item["ch1_residual"] = round(ch1_sum - predicted_ch1, 6)
        if isinstance(ch2_model, dict):
            predicted_ch2 = hill_response(area, ch2_model)
            item["predicted_ch2_sum"] = round(predicted_ch2, 6)
            item["ch2_residual"] = round(ch2_sum - predicted_ch2, 6)
    return item


def hybrid_vector_from_features(features: dict, shape: str, shape_categories: list[str]) -> list[float]:
    keys = [
        "weight_g",
        "thickness_mm",
        "contact_area_ratio",
        "f1_ch1_delta_pct",
        "f2_ch1_delta_pct",
        "f3_ch1_delta_pct",
        "f1_ch2_delta_pct",
        "f2_ch2_delta_pct",
        "f3_ch2_delta_pct",
        "ch1_sum",
        "ch2_sum",
        "ch1_slope",
        "ch2_slope",
        "ch1_residual",
        "ch2_residual",
        "hill_available",
    ]
    return [float(parse_float(features.get(key), 0.0) or 0.0) for key in keys] + shape_one_hot(shape, shape_categories)


def two_pass_gate_label(material_label: str) -> str | None:
    label = str(material_label or "").strip()
    normalized = normalize_label_text(label)
    if label in TWO_PASS_GOLD_LABELS:
        return "GOLD_LIKE"
    base = normalized
    if normalized.startswith("gold-plated"):
        base = normalized
    elif normalized.startswith("silver"):
        base = "silver"
    elif normalized.startswith("brass"):
        base = "brass"
    elif normalized.startswith("copper"):
        base = "copper"
    if base in TWO_PASS_NON_GOLD_BASES:
        return "NON_GOLD"
    return None


def build_normalized_knn_model(rows: list[dict], label_key: str, vector_key: str = "vector") -> dict:
    vectors = [row[vector_key] for row in rows]
    scaler_mean = vector_mean(vectors)
    scaler_std = vector_std(vectors, scaler_mean)
    normalized_rows = [
        {
            **row,
            "normalized_vector": normalize_vector(row[vector_key], scaler_mean, scaler_std),
        }
        for row in rows
    ]
    groups: dict[str, list[dict]] = {}
    for row in normalized_rows:
        groups.setdefault(row[label_key], []).append(row)

    classes = {}
    for label, label_rows in groups.items():
        class_vectors = [row["normalized_vector"] for row in label_rows]
        centroid = vector_mean(class_vectors)
        training_distances = [euclidean_distance(vector, centroid) for vector in class_vectors]
        distance_mean, distance_std = mean_and_sample_std(training_distances)
        classes[label] = {
            "sample_count": len(label_rows),
            "centroid": [round(value, 9) for value in centroid],
            "training_vectors": [
                {
                    "id": row.get("id"),
                    "material": row.get("label"),
                    "shape": row.get("shape", "Other"),
                    "vector": [round(value, 9) for value in row["normalized_vector"]],
                }
                for row in label_rows
            ],
            "training_distances": [round(value, 6) for value in training_distances],
            "distance_mean": round(distance_mean, 6),
            "distance_std": round(distance_std, 6),
            "acceptance_threshold": round(max(distance_mean + (CLASSIFIER_THRESHOLD_K * distance_std), CLASSIFIER_MIN_THRESHOLD), 6),
            "active": len(label_rows) >= CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "status": "Active" if len(label_rows) >= CLASSIFIER_MIN_ACTIVE_SAMPLES else "Learning",
        }
    return {
        "scaler_mean": [round(value, 9) for value in scaler_mean],
        "scaler_std": [round(value, 9) for value in scaler_std],
        "classes": classes,
    }


def score_normalized_knn_model(vector: list[float], model: dict, k: int) -> list[dict]:
    scaler_mean = [float(value) for value in model.get("scaler_mean", [])]
    scaler_std = [float(value) for value in model.get("scaler_std", [])]
    classes = model.get("classes") if isinstance(model.get("classes"), dict) else {}
    if not scaler_mean or not scaler_std or not classes:
        raise ValueError("KNN model is incomplete")
    normalized = normalize_vector(vector, scaler_mean, scaler_std)
    matches = []
    for label, item in classes.items():
        centroid = item.get("centroid")
        training_vectors = item.get("training_vectors") if isinstance(item.get("training_vectors"), list) else []
        if not isinstance(centroid, list) or len(centroid) != len(normalized):
            continue
        centroid_distance = euclidean_distance(normalized, [float(value) for value in centroid])
        neighbor_distances = []
        for training_item in training_vectors:
            training_vector = training_item.get("vector") if isinstance(training_item, dict) else None
            if isinstance(training_vector, list) and len(training_vector) == len(normalized):
                neighbor_distances.append(euclidean_distance(normalized, [float(value) for value in training_vector]))
        neighbor_distances.sort()
        nearest = neighbor_distances[:min(max(1, k), len(neighbor_distances))]
        neighbor_distance = sum(nearest) / len(nearest) if nearest else centroid_distance
        distance = min(centroid_distance, neighbor_distance)
        threshold = parse_float(item.get("acceptance_threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
        matches.append({
            "material": label,
            "distance": round(distance, 6),
            "centroid_distance": round(centroid_distance, 6),
            "neighbor_distance": round(neighbor_distance, 6),
            "sample_count": item.get("sample_count", 0),
            "active": bool(item.get("active", False)),
            "status": item.get("status", "Learning"),
            "threshold": threshold,
            "accepted": bool(item.get("active", False)) and distance <= threshold,
        })
    matches.sort(key=lambda item: item["distance"])
    return matches


def nearest_material_label(vector: list[float], model: dict, allowed_gate: str | None = None) -> str | None:
    scaler_mean = [float(value) for value in model.get("scaler_mean", [])]
    scaler_std = [float(value) for value in model.get("scaler_std", [])]
    if not scaler_mean or not scaler_std:
        return None
    normalized = normalize_vector(vector, scaler_mean, scaler_std)
    best = None
    for item in model.get("rows", []):
        if allowed_gate and item.get("gate_label") != allowed_gate:
            continue
        item_vector = item.get("normalized_vector")
        if not isinstance(item_vector, list) or len(item_vector) != len(normalized):
            continue
        distance = euclidean_distance(normalized, [float(value) for value in item_vector])
        if best is None or distance < best[0]:
            best = (distance, item.get("label"))
    return best[1] if best else None


def nearest_gate_votes(vector: list[float], model: dict, k: int) -> list[dict]:
    scaler_mean = [float(value) for value in model.get("scaler_mean", [])]
    scaler_std = [float(value) for value in model.get("scaler_std", [])]
    if not scaler_mean or not scaler_std:
        return []
    normalized = normalize_vector(vector, scaler_mean, scaler_std)
    rows = []
    for item in model.get("rows", []):
        item_vector = item.get("normalized_vector")
        if not isinstance(item_vector, list) or len(item_vector) != len(normalized):
            continue
        rows.append({
            "distance": round(euclidean_distance(normalized, [float(value) for value in item_vector]), 6),
            "gate_label": item.get("gate_label"),
            "material": item.get("label"),
            "shape": item.get("shape"),
            "id": item.get("id"),
        })
    rows.sort(key=lambda item: item["distance"])
    return rows[:max(1, k)]


def classifier_status_payload() -> dict:
    records = load_teaching_records()
    calibration = load_calibration()
    rows, excluded = build_classifier_training_rows(records, calibration)
    selected_algorithm = selected_classifier_algorithm()
    frequency_rf_gold_path, frequency_rf_purity_path = frequency_rf_model_paths()
    class_counts: dict[str, int] = {}
    for row in rows:
        class_counts[row["label"]] = class_counts.get(row["label"], 0) + 1

    model = load_classifier_model()
    model_classes = model.get("classes") if isinstance(model.get("classes"), dict) else {}
    class_readiness = []
    known_labels = sorted(set(class_counts) | set(model_classes))
    for label in known_labels:
        model_item = model_classes.get(label, {}) if isinstance(model_classes.get(label), dict) else {}
        count = int(model_item.get("sample_count", class_counts.get(label, 0)) or 0)
        active = bool(model_item.get("active", count >= CLASSIFIER_MIN_ACTIVE_SAMPLES))
        threshold = parse_float(model_item.get("acceptance_threshold"))
        distance_mean = parse_float(model_item.get("distance_mean"))
        distance_std = parse_float(model_item.get("distance_std"))
        class_readiness.append({
            "label": label,
            "sample_count": count,
            "minimum_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "active": active,
            "status": "Active" if active else "Learning",
            "needed_samples": max(0, CLASSIFIER_MIN_ACTIVE_SAMPLES - count),
            "acceptance_threshold": round(threshold, 3) if threshold is not None else None,
            "distance_mean": round(distance_mean, 3) if distance_mean is not None else None,
            "distance_std": round(distance_std, 3) if distance_std is not None else None,
            "family": model_item.get("family", material_family(label)),
        })

    warnings = []
    for item in class_readiness:
        if not item["active"]:
            warnings.append(f"{item['label']} learning mode: {item['sample_count']} / {CLASSIFIER_MIN_ACTIVE_SAMPLES} samples")
        elif item["sample_count"] < 10:
            warnings.append(f"{item['label']} active but still early: {item['sample_count']} samples")
    model_exists = bool(model)
    model_trained_at = model.get("trained_at")
    model_method = model.get("classification_method")
    model_algorithm = model.get("algorithm", model.get("classifier_algorithm", "mahalanobis"))
    feature_keys = MAHALANOBIS_FEATURE_KEYS
    if selected_algorithm == "two_pass_frequency_rf":
        model_exists = frequency_rf_gold_path.exists() and frequency_rf_purity_path.exists()
        model_trained_at = None
        model_method = CLASSIFIER_ALGORITHMS["two_pass_frequency_rf"]["method"]
        model_algorithm = "two_pass_frequency_rf"
        feature_keys = FREQUENCY_RF_FEATURE_NAMES

    return {
        "teaching_record_count": len(records),
        "eligible_record_count": len(rows),
        "excluded_record_count": len(excluded),
        "class_count": len(class_counts),
        "class_counts": class_counts,
        "class_readiness": class_readiness,
        "active_class_count": sum(1 for item in class_readiness if item["active"]),
        "learning_class_count": sum(1 for item in class_readiness if not item["active"]),
        "warnings": warnings,
        "model_exists": model_exists,
        "model_trained_at": model_trained_at,
        "model_method": model_method,
        "model_algorithm": model_algorithm,
        "selected_algorithm": selected_algorithm,
        "classifier_algorithms": [
            {"key": key, "label": item["label"], "method": item["method"]}
            for key, item in CLASSIFIER_ALGORITHMS.items()
        ],
        "model_feature_version": 1 if selected_algorithm == "two_pass_frequency_rf" else model.get("feature_version"),
        "model_record_count": model.get("eligible_record_count"),
        "calibrated_at": calibration.get("calibrated_at"),
        "feature_keys": feature_keys,
        "threshold_k": CLASSIFIER_THRESHOLD_K,
        "minimum_threshold": CLASSIFIER_MIN_THRESHOLD,
        "minimum_active_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
        "uncertain_gap": CLASSIFIER_UNCERTAIN_GAP,
        "excluded_preview": excluded[:8],
        "external_model_files": {
            "gold_model": str(frequency_rf_gold_path),
            "purity_model": str(frequency_rf_purity_path),
        } if selected_algorithm == "two_pass_frequency_rf" else None,
    }


def train_knn_cluster_classifier() -> dict:
    records = load_teaching_records()
    calibration = load_calibration()
    rows, excluded = build_classifier_training_rows(records, calibration)
    if len(rows) < 2:
        raise ValueError("Not enough eligible teaching records to train classifier")

    class_rows: dict[str, list[dict]] = {}
    for row in rows:
        class_rows.setdefault(row["label"], []).append(row)

    if len(class_rows) < 2:
        raise ValueError("At least two material classes are required to train classifier")

    raw_vectors = [row["vector"] for row in rows]
    scaler_mean = vector_mean(raw_vectors)
    scaler_std = vector_std(raw_vectors, scaler_mean)
    normalized_rows = [
        {
            **row,
            "normalized_vector": normalize_vector(row["vector"], scaler_mean, scaler_std),
        }
        for row in rows
    ]

    classes = {}
    for label, label_rows in class_rows.items():
        normalized_vectors = [
            row["normalized_vector"]
            for row in normalized_rows
            if row["label"] == label
        ]
        centroid = vector_mean(normalized_vectors)
        training_distances = [
            euclidean_distance(vector, centroid)
            for vector in normalized_vectors
        ]
        distance_mean, distance_std = mean_and_sample_std(training_distances)
        acceptance_threshold = max(
            distance_mean + (CLASSIFIER_THRESHOLD_K * distance_std),
            CLASSIFIER_MIN_THRESHOLD,
        )
        sample_count = len(label_rows)
        classes[label] = {
            "sample_count": sample_count,
            "record_ids": [row["id"] for row in label_rows],
            "centroid": [round(value, 9) for value in centroid],
            "training_vectors": [
                {
                    "id": row["id"],
                    "shape": row.get("shape", "Other"),
                    "vector": [round(value, 9) for value in row["normalized_vector"]],
                }
                for row in normalized_rows
                if row["label"] == label
            ],
            "training_distances": [round(value, 6) for value in training_distances],
            "distance_mean": round(distance_mean, 6),
            "distance_std": round(distance_std, 6),
            "acceptance_threshold": round(acceptance_threshold, 6),
            "minimum_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "active": sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "status": "Active" if sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES else "Learning",
            "family": material_family(label),
        }

    model = {
        "model_version": CLASSIFIER_VERSION,
        "feature_version": 3,
        "algorithm": "knn_cluster",
        "classification_method": CLASSIFIER_ALGORITHMS["knn_cluster"]["method"],
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "teaching_record_count": len(records),
        "eligible_record_count": len(rows),
        "excluded_record_count": len(excluded),
        "excluded_records": excluded,
        "feature_keys": MAHALANOBIS_FEATURE_KEYS,
        "class_count": len(classes),
        "class_counts": {label: item["sample_count"] for label, item in classes.items()},
        "classes": classes,
        "scaler_mean": [round(value, 9) for value in scaler_mean],
        "scaler_std": [round(value, 9) for value in scaler_std],
        "knn_k": KNN_CLUSTER_K,
        "centroid_weight": KNN_CLUSTER_CENTROID_WEIGHT,
        "neighbor_weight": KNN_CLUSTER_NEIGHBOR_WEIGHT,
        "minimum_active_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
        "threshold_k": CLASSIFIER_THRESHOLD_K,
        "minimum_threshold": CLASSIFIER_MIN_THRESHOLD,
        "uncertain_gap": CLASSIFIER_UNCERTAIN_GAP,
        "active_class_count": sum(1 for item in classes.values() if item["active"]),
        "learning_class_count": sum(1 for item in classes.values() if not item["active"]),
        "calibration_used": calibration.get("calibrated_at"),
        "calibration_frequency_air": calibration.get("frequency_air", {}),
    }
    save_classifier_model(model)
    return model


def train_hybrid_hill_knn_classifier() -> dict:
    records = load_teaching_records()
    calibration = load_calibration()
    rows, excluded = build_classifier_training_rows(records, calibration)
    if len(rows) < 2:
        raise ValueError("Not enough eligible teaching records to train classifier")

    class_rows: dict[str, list[dict]] = {}
    for row in rows:
        class_rows.setdefault(row["label"], []).append(row)

    if len(class_rows) < 2:
        raise ValueError("At least two material classes are required to train classifier")

    shape_categories = sorted({str(row.get("shape") or "Other") for row in rows})
    grouped_points: dict[str, dict[str, list[tuple[float, float]]]] = {}
    for row in rows:
        features = standard_features_with_sums(row["features"])
        group_key = hill_key(row["label"], row.get("shape", "Other"))
        grouped_points.setdefault(group_key, {"ch1_sum": [], "ch2_sum": []})
        area = parse_float(features.get("contact_area_ratio"))
        ch1_sum = parse_float(features.get("ch1_sum"))
        ch2_sum = parse_float(features.get("ch2_sum"))
        if area is not None and ch1_sum is not None:
            grouped_points[group_key]["ch1_sum"].append((area, ch1_sum))
        if area is not None and ch2_sum is not None:
            grouped_points[group_key]["ch2_sum"].append((area, ch2_sum))

    hill_models = {}
    for group_key, targets in grouped_points.items():
        ch1_model = fit_hill_model(targets["ch1_sum"])
        ch2_model = fit_hill_model(targets["ch2_sum"])
        hill_available = ch1_model is not None or ch2_model is not None
        hill_models[group_key] = {
            "hill_available": hill_available,
            "ch1_sum": ch1_model,
            "ch2_sum": ch2_model,
            "sample_count": max(len(targets["ch1_sum"]), len(targets["ch2_sum"])),
            "unique_contact_area_count": len({round(area, 6) for area, _ in targets["ch2_sum"]}),
        }

    enriched_rows = []
    for row in rows:
        enriched = hybrid_features_for_label(row["features"], row["label"], row.get("shape", "Other"), {"hill_models": hill_models})
        vector = hybrid_vector_from_features(enriched, row.get("shape", "Other"), shape_categories)
        enriched_rows.append({
            **row,
            "hybrid_features": enriched,
            "hybrid_vector": vector,
        })

    raw_vectors = [row["hybrid_vector"] for row in enriched_rows]
    scaler_mean = vector_mean(raw_vectors)
    scaler_std = vector_std(raw_vectors, scaler_mean)
    normalized_rows = [
        {
            **row,
            "normalized_vector": normalize_vector(row["hybrid_vector"], scaler_mean, scaler_std),
        }
        for row in enriched_rows
    ]

    classes = {}
    for label, label_rows in class_rows.items():
        normalized_vectors = [
            row["normalized_vector"]
            for row in normalized_rows
            if row["label"] == label
        ]
        centroid = vector_mean(normalized_vectors)
        training_distances = [
            euclidean_distance(vector, centroid)
            for vector in normalized_vectors
        ]
        distance_mean, distance_std = mean_and_sample_std(training_distances)
        acceptance_threshold = max(
            distance_mean + (CLASSIFIER_THRESHOLD_K * distance_std),
            CLASSIFIER_MIN_THRESHOLD,
        )
        sample_count = len(label_rows)
        classes[label] = {
            "sample_count": sample_count,
            "record_ids": [row["id"] for row in label_rows],
            "centroid": [round(value, 9) for value in centroid],
            "training_vectors": [
                {
                    "id": row["id"],
                    "shape": row.get("shape", "Other"),
                    "vector": [round(value, 9) for value in row["normalized_vector"]],
                    "hill_available": bool(row["hybrid_features"].get("hill_available")),
                }
                for row in normalized_rows
                if row["label"] == label
            ],
            "training_distances": [round(value, 6) for value in training_distances],
            "distance_mean": round(distance_mean, 6),
            "distance_std": round(distance_std, 6),
            "acceptance_threshold": round(acceptance_threshold, 6),
            "minimum_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "active": sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "status": "Active" if sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES else "Learning",
            "family": material_family(label),
        }

    model = {
        "model_version": CLASSIFIER_VERSION,
        "feature_version": 4,
        "algorithm": "hybrid_hill_knn",
        "classification_method": CLASSIFIER_ALGORITHMS["hybrid_hill_knn"]["method"],
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "teaching_record_count": len(records),
        "eligible_record_count": len(rows),
        "excluded_record_count": len(excluded),
        "excluded_records": excluded,
        "feature_keys": [
            "weight_g",
            "thickness_mm",
            "contact_area_ratio",
            "shape_one_hot",
            "f1_ch1_delta_pct",
            "f2_ch1_delta_pct",
            "f3_ch1_delta_pct",
            "f1_ch2_delta_pct",
            "f2_ch2_delta_pct",
            "f3_ch2_delta_pct",
            "ch1_sum",
            "ch2_sum",
            "ch1_slope",
            "ch2_slope",
            "ch1_residual",
            "ch2_residual",
            "hill_available",
        ],
        "class_count": len(classes),
        "class_counts": {label: item["sample_count"] for label, item in classes.items()},
        "classes": classes,
        "shape_categories": shape_categories,
        "hill_models": hill_models,
        "hill_available_group_count": sum(1 for item in hill_models.values() if item.get("hill_available")),
        "hill_group_count": len(hill_models),
        "scaler_mean": [round(value, 9) for value in scaler_mean],
        "scaler_std": [round(value, 9) for value in scaler_std],
        "knn_k": HYBRID_KNN_K,
        "minimum_active_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
        "hill_min_samples": HILL_MIN_SAMPLES,
        "hill_min_unique_area": HILL_MIN_UNIQUE_AREA,
        "threshold_k": CLASSIFIER_THRESHOLD_K,
        "minimum_threshold": CLASSIFIER_MIN_THRESHOLD,
        "uncertain_gap": CLASSIFIER_UNCERTAIN_GAP,
        "active_class_count": sum(1 for item in classes.values() if item["active"]),
        "learning_class_count": sum(1 for item in classes.values() if not item["active"]),
        "calibration_used": calibration.get("calibrated_at"),
        "calibration_frequency_air": calibration.get("frequency_air", {}),
    }
    save_classifier_model(model)
    return model


def train_two_pass_gold_gate_classifier(compact: bool = False) -> dict:
    records = load_teaching_records()
    calibration = load_calibration()
    rows, excluded = build_classifier_training_rows(records, calibration)
    algorithm = "two_pass_compact_gate" if compact else "two_pass_gold_gate"
    feature_keys = COMPACT_TWO_PASS_FEATURE_KEYS if compact else MAHALANOBIS_FEATURE_KEYS
    feature_version = 6 if compact else 5
    gate_rows = []
    purity_rows = []
    mapping_excluded = []
    for row in rows:
        gate_label = two_pass_gate_label(row["label"])
        if gate_label is None:
            mapping_excluded.append({
                "id": row.get("id"),
                "label": row.get("label"),
                "reason": "not mapped to two-pass gold gate",
            })
            continue
        if compact:
            try:
                vector = vector_from_compact_two_pass_features(row["features"])
            except ValueError as exc:
                mapping_excluded.append({
                    "id": row.get("id"),
                    "label": row.get("label"),
                    "reason": str(exc),
                })
                continue
        else:
            vector = row["vector"]
        model_row = {**row, "vector": vector}
        gate_row = {**model_row, "gate_label": gate_label}
        gate_rows.append(gate_row)
        if row["label"] in TWO_PASS_GOLD_LABELS:
            purity_rows.append({**model_row, "purity_label": row["label"]})

    if len(gate_rows) < 2:
        raise ValueError("Not enough eligible mapped records to train two-pass classifier")
    gate_labels = {row["gate_label"] for row in gate_rows}
    if not {"GOLD_LIKE", "NON_GOLD"}.issubset(gate_labels):
        raise ValueError("Two-pass classifier needs both GOLD_LIKE and NON_GOLD teaching samples")

    purity_labels = {row["purity_label"] for row in purity_rows}
    if len(purity_labels) < 2:
        raise ValueError("Gold purity pass needs at least two of Gold 999 / Gold 916 / Gold 750")

    gate_model = build_normalized_knn_model(gate_rows, "gate_label")
    purity_model = build_normalized_knn_model(purity_rows, "purity_label")

    gate_mean = [float(value) for value in gate_model["scaler_mean"]]
    gate_std = [float(value) for value in gate_model["scaler_std"]]
    gate_model["rows"] = [
        {
            "id": row.get("id"),
            "label": row.get("label"),
            "gate_label": row.get("gate_label"),
            "shape": row.get("shape", "Other"),
            "normalized_vector": [
                round(value, 9)
                for value in normalize_vector(row["vector"], gate_mean, gate_std)
            ],
        }
        for row in gate_rows
    ]

    model = {
        "model_version": CLASSIFIER_VERSION,
        "feature_version": feature_version,
        "algorithm": algorithm,
        "classification_method": CLASSIFIER_ALGORITHMS[algorithm]["method"],
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "teaching_record_count": len(records),
        "eligible_record_count": len(gate_rows),
        "excluded_record_count": len(excluded) + len(mapping_excluded),
        "excluded_records": excluded + mapping_excluded,
        "feature_keys": feature_keys,
        "source_feature_keys": MAHALANOBIS_FEATURE_KEYS,
        "class_count": len(gate_model["classes"]),
        "class_counts": {
            label: sum(1 for row in gate_rows if row["gate_label"] == label)
            for label in sorted(gate_labels)
        },
        "classes": gate_model["classes"],
        "gate_model": gate_model,
        "purity_model": purity_model,
        "purity_class_counts": {
            label: sum(1 for row in purity_rows if row["purity_label"] == label)
            for label in sorted(purity_labels)
        },
        "knn_k": TWO_PASS_K,
        "minimum_active_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
        "threshold_k": CLASSIFIER_THRESHOLD_K,
        "minimum_threshold": CLASSIFIER_MIN_THRESHOLD,
        "uncertain_gap": TWO_PASS_GATE_UNCERTAIN_GAP,
        "active_class_count": sum(1 for item in gate_model["classes"].values() if item["active"]),
        "learning_class_count": sum(1 for item in gate_model["classes"].values() if not item["active"]),
        "calibration_used": calibration.get("calibrated_at"),
        "calibration_frequency_air": calibration.get("frequency_air", {}),
    }
    save_classifier_model(model)
    return model


def train_two_pass_compact_gate_classifier() -> dict:
    return train_two_pass_gold_gate_classifier(compact=True)


def train_binary_brass_ch1_f1_classifier() -> dict:
    params = BrassModelParams()
    records = load_teaching_records()
    brass_records = [
        record for record in records
        if normalize_label_text(record.get("material") or record.get("material_base")) == "brass"
    ]
    model = {
        "algorithm": "binary_brass_ch1_f1",
        "classification_method": CLASSIFIER_ALGORITHMS["binary_brass_ch1_f1"]["method"],
        "feature_version": 4,
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "eligible_record_count": len(brass_records),
        "model_params": {
            "model_name": params.model_name,
            "rmin": params.rmin,
            "rspan": params.rspan,
            "k": params.k,
            "alpha": params.alpha,
            "d": params.d,
            "sa0": params.sa0,
            "t0": params.t0,
            "min_coverage_pct": params.min_coverage_pct,
            "max_coverage_pct": params.max_coverage_pct,
            "min_thickness_mm": params.min_thickness_mm,
            "max_thickness_mm": params.max_thickness_mm,
        },
        "classes": {
            "brass": {
                "sample_count": len(brass_records),
                "minimum_samples": 0,
                "active": True,
                "status": "Physics model",
                "acceptance_threshold": 2.5,
                "family": "non_gold",
            },
            "not_brass": {
                "sample_count": 0,
                "minimum_samples": 0,
                "active": True,
                "status": "Residual rejection",
                "acceptance_threshold": 2.5,
                "family": "unknown",
            },
        },
        "notes": [
            "Zero-floor brass bar model fitted from the 28-Jun-2026 brass bar scan data.",
            "Valid only for practical flat bar samples using CH1 F1 absolute delta percentage.",
            "Do not use for rings, bangles, chains, hollow, curved, or irregular objects.",
        ],
    }
    save_classifier_model(model)
    return model


def train_binary_brass_ch2_f1_f3_classifier() -> dict:
    records = load_teaching_records()
    brass_records = [
        record for record in records
        if normalize_label_text(record.get("material") or record.get("material_base")) == "brass"
    ]
    model = {
        "algorithm": "binary_brass_ch2_f1_f3",
        "classification_method": CLASSIFIER_ALGORITHMS["binary_brass_ch2_f1_f3"]["method"],
        "feature_version": 5,
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "eligible_record_count": len(brass_records),
        "model_params": {
            "model_name": CH2_F1_F3_MODEL_NAME,
            "sa0": 16.7641,
            "t0": 0.2700,
            "coverage_pct_min": CH2_F1_F3_COVERAGE_RANGE[0],
            "coverage_pct_max": CH2_F1_F3_COVERAGE_RANGE[1],
            "thickness_mm_min": CH2_F1_F3_THICKNESS_RANGE[0],
            "thickness_mm_max": CH2_F1_F3_THICKNESS_RANGE[1],
            "ch2_f1": {
                "rmin": CH2_F1_PARAMS.rmin,
                "rspan": CH2_F1_PARAMS.rspan,
                "k": CH2_F1_PARAMS.k,
                "alpha": CH2_F1_PARAMS.alpha,
                "d": CH2_F1_PARAMS.d,
                "rmse": CH2_F1_PARAMS.rmse,
                "r2": CH2_F1_PARAMS.r2,
            },
            "ch2_f3": {
                "rmin": CH2_F3_PARAMS.rmin,
                "rspan": CH2_F3_PARAMS.rspan,
                "k": CH2_F3_PARAMS.k,
                "alpha": CH2_F3_PARAMS.alpha,
                "d": CH2_F3_PARAMS.d,
                "rmse": CH2_F3_PARAMS.rmse,
                "r2": CH2_F3_PARAMS.r2,
            },
        },
        "classes": {
            "brass": {
                "sample_count": len(brass_records),
                "minimum_samples": 0,
                "active": True,
                "status": "Surface model",
                "acceptance_threshold": 2.0,
                "family": "non_gold",
            },
            "brass_like": {
                "sample_count": len(brass_records),
                "minimum_samples": 0,
                "active": True,
                "status": "Surface model medium band",
                "acceptance_threshold": 3.0,
                "family": "non_gold",
            },
            "not_brass_or_outlier": {
                "sample_count": 0,
                "minimum_samples": 0,
                "active": True,
                "status": "Normalized residual rejection",
                "acceptance_threshold": 3.0,
                "family": "unknown",
            },
        },
        "notes": [
            "Uses CH2 F1 and CH2 F3 absolute delta percentages.",
            "Residuals are normalized by each surface RMSE before distance scoring.",
            "CH2 F3 is weaker than CH2 F1, so diagnostic normalized residuals are shown separately.",
            "Valid for flat brass-compatible samples inside the calibrated geometry range.",
        ],
    }
    save_classifier_model(model)
    return model


def train_mahalanobis_classifier() -> dict:
    records = load_teaching_records()
    calibration = load_calibration()
    rows, excluded = build_classifier_training_rows(records, calibration)
    if len(rows) < 2:
        raise ValueError("Not enough eligible teaching records to train classifier")

    class_rows: dict[str, list[dict]] = {}
    for row in rows:
        class_rows.setdefault(row["label"], []).append(row)

    if len(class_rows) < 2:
        raise ValueError("At least two material classes are required to train classifier")

    vectors = [row["vector"] for row in rows]
    mean = vector_mean(vectors)
    cov = covariance_matrix(vectors, mean)
    regularized = regularize_covariance(cov, CLASSIFIER_REGULARIZATION)
    inv_cov = matrix_inverse(regularized)
    if inv_cov is None:
        raise ValueError("Unable to invert covariance matrix")

    classes = {}
    for label, label_rows in class_rows.items():
        class_vectors = [row["vector"] for row in label_rows]
        centroid = vector_mean(class_vectors)
        training_distances = [
            mahalanobis_distance(values, centroid, inv_cov)
            for values in class_vectors
        ]
        distance_mean, distance_std = mean_and_sample_std(training_distances)
        acceptance_threshold = max(
            distance_mean + (CLASSIFIER_THRESHOLD_K * distance_std),
            CLASSIFIER_MIN_THRESHOLD,
        )
        sample_count = len(label_rows)
        classes[label] = {
            "sample_count": sample_count,
            "record_ids": [row["id"] for row in label_rows],
            "centroid": [round(value, 9) for value in centroid],
            "training_distances": [round(value, 6) for value in training_distances],
            "distance_mean": round(distance_mean, 6),
            "distance_std": round(distance_std, 6),
            "acceptance_threshold": round(acceptance_threshold, 6),
            "minimum_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "active": sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES,
            "status": "Active" if sample_count >= CLASSIFIER_MIN_ACTIVE_SAMPLES else "Learning",
            "family": material_family(label),
        }

    model = {
        "model_version": CLASSIFIER_VERSION,
        "feature_version": 3,
        "algorithm": "mahalanobis",
        "classification_method": CLASSIFIER_METHOD,
        "trained_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "teaching_record_count": len(records),
        "eligible_record_count": len(rows),
        "excluded_record_count": len(excluded),
        "excluded_records": excluded,
        "feature_keys": MAHALANOBIS_FEATURE_KEYS,
        "class_count": len(classes),
        "class_counts": {label: item["sample_count"] for label, item in classes.items()},
        "classes": classes,
        "global_mean": [round(value, 9) for value in mean],
        "covariance_matrix": [[round(value, 12) for value in row] for row in cov],
        "regularized_covariance_matrix": [[round(value, 12) for value in row] for row in regularized],
        "inverse_covariance_matrix": [[round(value, 12) for value in row] for row in inv_cov],
        "regularization": CLASSIFIER_REGULARIZATION,
        "minimum_active_samples": CLASSIFIER_MIN_ACTIVE_SAMPLES,
        "threshold_k": CLASSIFIER_THRESHOLD_K,
        "minimum_threshold": CLASSIFIER_MIN_THRESHOLD,
        "uncertain_gap": CLASSIFIER_UNCERTAIN_GAP,
        "active_class_count": sum(1 for item in classes.values() if item["active"]),
        "learning_class_count": sum(1 for item in classes.values() if not item["active"]),
        "calibration_used": calibration.get("calibrated_at"),
        "calibration_frequency_air": calibration.get("frequency_air", {}),
    }
    save_classifier_model(model)
    return model


def train_selected_classifier() -> dict:
    algorithm = selected_classifier_algorithm()
    if algorithm == "two_pass_frequency_rf":
        gold_path, purity_path = frequency_rf_model_paths()
        if not gold_path.exists() or not purity_path.exists():
            missing = []
            if not gold_path.exists():
                missing.append(gold_path.name)
            if not purity_path.exists():
                missing.append(purity_path.name)
            raise ValueError(f"Gold Standard model files missing: {', '.join(missing)}")
        return {
            "algorithm": algorithm,
            "classification_method": CLASSIFIER_ALGORITHMS[algorithm]["method"],
            "model_version": FREQUENCY_RF_MODEL_VERSION,
            "feature_version": 1,
            "feature_names": list(FREQUENCY_RF_FEATURE_NAMES),
            "gold_model_file": str(gold_path),
            "purity_model_file": str(purity_path),
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "message": "Gold Standard external Random Forest models are ready.",
        }
    if algorithm == "binary_brass_ch2_f1_f3":
        return train_binary_brass_ch2_f1_f3_classifier()
    if algorithm == "binary_brass_ch1_f1":
        return train_binary_brass_ch1_f1_classifier()
    if algorithm == "two_pass_compact_gate":
        return train_two_pass_compact_gate_classifier()
    if algorithm == "two_pass_gold_gate":
        return train_two_pass_gold_gate_classifier()
    if algorithm == "hybrid_hill_knn":
        return train_hybrid_hill_knn_classifier()
    if algorithm == "knn_cluster":
        return train_knn_cluster_classifier()
    return train_mahalanobis_classifier()


def predict_with_mahalanobis(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Classifier model not found. Train classifier first.")
    if model.get("algorithm", "mahalanobis") != "mahalanobis":
        raise ValueError("Selected model is not a Mahalanobis model. Recompute the selected classifier.")

    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        raise ValueError(f"Missing classifier features: {', '.join(missing)}")

    vector = vector_from_mahalanobis_features(features)
    inv_cov = model.get("inverse_covariance_matrix")
    classes = model.get("classes") if isinstance(model.get("classes"), dict) else {}
    if not inv_cov or not classes:
        raise ValueError("Classifier model is incomplete")

    all_matches = []
    matches = []
    for label, item in classes.items():
        centroid = item.get("centroid")
        if not isinstance(centroid, list) or len(centroid) != len(vector):
            continue
        distance = mahalanobis_distance(vector, [float(value) for value in centroid], inv_cov)
        match_item = {
            "material": label,
            "distance": round(distance, 6),
            "sample_count": item.get("sample_count", 0),
            "active": bool(item.get("active", False)),
            "status": item.get("status", "Learning"),
            "threshold": item.get("acceptance_threshold"),
            "accepted": bool(item.get("active", False)) and distance <= (parse_float(item.get("acceptance_threshold")) or 0.0),
            "family": item.get("family", material_family(label)),
        }
        all_matches.append(match_item)
        if match_item["active"]:
            matches.append(match_item)

    matches.sort(key=lambda item: item["distance"])
    all_matches.sort(key=lambda item: item["distance"])
    if not matches:
        raise ValueError("Classifier model has no active classes. Add at least 5 samples for one class.")

    best = matches[0]
    second = matches[1] if len(matches) > 1 else None
    gap = (second["distance"] - best["distance"]) if second else 0.0
    threshold = parse_float(best.get("threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
    accepted = bool(best.get("accepted"))
    decision, result_type, decision_message, uncertain = classifier_decision_from_best(
        best,
        second,
        accepted,
        CLASSIFIER_UNCERTAIN_GAP,
    )

    distance_ratio = min(best["distance"] / threshold, 2.0) if threshold > 0 else 2.0
    threshold_confidence = max(0.0, min(99.9, (1.0 - (distance_ratio / 2.0)) * 100.0))
    gap_bonus = min(max(gap, 0.0), 1.0) * 10.0
    confidence_pct = max(0.0, min(99.9, threshold_confidence + gap_bonus))
    return {
        "prediction": decision,
        "nearest_class": best["material"],
        "result_type": result_type,
        "decision_message": decision_message,
        "accepted": accepted,
        "uncertain": uncertain,
        "threshold": round(threshold, 6),
        "distance": best["distance"],
        "nearest_gap": round(gap, 6),
        "confidence": round(confidence_pct, 2),
        "top_matches": [
            {
                "rank": index + 1,
                "material": item["material"],
                "distance": item["distance"],
                "sample_count": item["sample_count"],
                "threshold": item.get("threshold"),
                "accepted": item.get("accepted"),
                "active": item.get("active"),
                "status": item.get("status"),
            }
            for index, item in enumerate(matches[:3])
        ],
        "all_matches": all_matches[:8],
        "classification_method": model.get("classification_method", CLASSIFIER_METHOD),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version"),
    }


def predict_with_knn_cluster(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Classifier model not found. Train classifier first.")
    if model.get("algorithm") != "knn_cluster":
        raise ValueError("Selected model is not a KNN cluster model. Recompute the selected classifier.")

    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        raise ValueError(f"Missing classifier features: {', '.join(missing)}")

    raw_vector = vector_from_mahalanobis_features(features)
    scaler_mean = model.get("scaler_mean")
    scaler_std = model.get("scaler_std")
    classes = model.get("classes") if isinstance(model.get("classes"), dict) else {}
    if not scaler_mean or not scaler_std or not classes:
        raise ValueError("KNN cluster model is incomplete")

    vector = normalize_vector(raw_vector, [float(value) for value in scaler_mean], [float(value) for value in scaler_std])
    k = max(1, int(model.get("knn_k", KNN_CLUSTER_K) or KNN_CLUSTER_K))
    centroid_weight = parse_float(model.get("centroid_weight"), KNN_CLUSTER_CENTROID_WEIGHT) or KNN_CLUSTER_CENTROID_WEIGHT
    neighbor_weight = parse_float(model.get("neighbor_weight"), KNN_CLUSTER_NEIGHBOR_WEIGHT) or KNN_CLUSTER_NEIGHBOR_WEIGHT

    all_matches = []
    matches = []
    for label, item in classes.items():
        centroid = item.get("centroid")
        training_vectors = item.get("training_vectors") if isinstance(item.get("training_vectors"), list) else []
        if not isinstance(centroid, list) or len(centroid) != len(vector):
            continue
        centroid_distance = euclidean_distance(vector, [float(value) for value in centroid])
        neighbor_distances = []
        for training_item in training_vectors:
            training_vector = training_item.get("vector") if isinstance(training_item, dict) else None
            if isinstance(training_vector, list) and len(training_vector) == len(vector):
                neighbor_distances.append(euclidean_distance(vector, [float(value) for value in training_vector]))
        neighbor_distances.sort()
        nearest_neighbors = neighbor_distances[:min(k, len(neighbor_distances))]
        neighbor_distance = sum(nearest_neighbors) / len(nearest_neighbors) if nearest_neighbors else centroid_distance
        combined_distance = (centroid_weight * centroid_distance) + (neighbor_weight * neighbor_distance)
        threshold = parse_float(item.get("acceptance_threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
        match_item = {
            "material": label,
            "distance": round(combined_distance, 6),
            "centroid_distance": round(centroid_distance, 6),
            "neighbor_distance": round(neighbor_distance, 6),
            "sample_count": item.get("sample_count", 0),
            "active": bool(item.get("active", False)),
            "status": item.get("status", "Learning"),
            "threshold": threshold,
            "accepted": bool(item.get("active", False)) and combined_distance <= threshold,
            "family": item.get("family", material_family(label)),
        }
        all_matches.append(match_item)
        if match_item["active"]:
            matches.append(match_item)

    matches.sort(key=lambda item: item["distance"])
    all_matches.sort(key=lambda item: item["distance"])
    if not matches:
        raise ValueError("Classifier model has no active classes. Add at least 5 samples for one class.")

    best = matches[0]
    second = matches[1] if len(matches) > 1 else None
    gap = (second["distance"] - best["distance"]) if second else 0.0
    threshold = parse_float(best.get("threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
    accepted = bool(best.get("accepted"))
    decision, result_type, decision_message, uncertain = classifier_decision_from_best(
        best,
        second,
        accepted,
        CLASSIFIER_UNCERTAIN_GAP,
    )

    distance_ratio = min(best["distance"] / threshold, 2.0) if threshold > 0 else 2.0
    threshold_confidence = max(0.0, min(99.9, (1.0 - (distance_ratio / 2.0)) * 100.0))
    gap_bonus = min(max(gap, 0.0), 1.0) * 10.0
    confidence_pct = max(0.0, min(99.9, threshold_confidence + gap_bonus))
    return {
        "prediction": decision,
        "nearest_class": best["material"],
        "result_type": result_type,
        "decision_message": decision_message,
        "accepted": accepted,
        "uncertain": uncertain,
        "threshold": round(threshold, 6),
        "distance": best["distance"],
        "nearest_gap": round(gap, 6),
        "confidence": round(confidence_pct, 2),
        "top_matches": [
            {
                "rank": index + 1,
                "material": item["material"],
                "distance": item["distance"],
                "sample_count": item["sample_count"],
                "threshold": item.get("threshold"),
                "accepted": item.get("accepted"),
                "active": item.get("active"),
                "status": item.get("status"),
            }
            for index, item in enumerate(matches[:3])
        ],
        "all_matches": all_matches[:8],
        "classification_method": model.get("classification_method", CLASSIFIER_ALGORITHMS["knn_cluster"]["method"]),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version"),
    }


def predict_with_hybrid_hill_knn(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Classifier model not found. Train classifier first.")
    if model.get("algorithm") != "hybrid_hill_knn":
        raise ValueError("Selected model is not a Hill + KNN model. Recompute the selected classifier.")

    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        raise ValueError(f"Missing classifier features: {', '.join(missing)}")

    scaler_mean = model.get("scaler_mean")
    scaler_std = model.get("scaler_std")
    classes = model.get("classes") if isinstance(model.get("classes"), dict) else {}
    shape_categories = model.get("shape_categories") if isinstance(model.get("shape_categories"), list) else []
    if not scaler_mean or not scaler_std or not classes or not shape_categories:
        raise ValueError("Hill + KNN model is incomplete")

    shape = str(features.get("shape") or "Other")
    k = max(1, int(model.get("knn_k", HYBRID_KNN_K) or HYBRID_KNN_K))
    all_matches = []
    matches = []
    for label, item in classes.items():
        enriched = hybrid_features_for_label(features, label, shape, model)
        raw_vector = hybrid_vector_from_features(enriched, shape, shape_categories)
        vector = normalize_vector(raw_vector, [float(value) for value in scaler_mean], [float(value) for value in scaler_std])
        centroid = item.get("centroid")
        training_vectors = item.get("training_vectors") if isinstance(item.get("training_vectors"), list) else []
        if not isinstance(centroid, list) or len(centroid) != len(vector):
            continue
        centroid_distance = euclidean_distance(vector, [float(value) for value in centroid])
        neighbor_distances = []
        for training_item in training_vectors:
            training_vector = training_item.get("vector") if isinstance(training_item, dict) else None
            if isinstance(training_vector, list) and len(training_vector) == len(vector):
                neighbor_distances.append(euclidean_distance(vector, [float(value) for value in training_vector]))
        neighbor_distances.sort()
        nearest_neighbors = neighbor_distances[:min(k, len(neighbor_distances))]
        neighbor_distance = sum(nearest_neighbors) / len(nearest_neighbors) if nearest_neighbors else centroid_distance
        combined_distance = min(centroid_distance, neighbor_distance)
        threshold = parse_float(item.get("acceptance_threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
        match_item = {
            "material": label,
            "distance": round(combined_distance, 6),
            "centroid_distance": round(centroid_distance, 6),
            "neighbor_distance": round(neighbor_distance, 6),
            "sample_count": item.get("sample_count", 0),
            "active": bool(item.get("active", False)),
            "status": item.get("status", "Learning"),
            "threshold": threshold,
            "accepted": bool(item.get("active", False)) and combined_distance <= threshold,
            "family": item.get("family", material_family(label)),
            "hill_available": bool(enriched.get("hill_available")),
            "ch1_residual": enriched.get("ch1_residual"),
            "ch2_residual": enriched.get("ch2_residual"),
        }
        all_matches.append(match_item)
        if match_item["active"]:
            matches.append(match_item)

    matches.sort(key=lambda item: item["distance"])
    all_matches.sort(key=lambda item: item["distance"])
    if not matches:
        raise ValueError("Classifier model has no active classes. Add at least 5 samples for one class.")

    best = matches[0]
    second = matches[1] if len(matches) > 1 else None
    nearest_non_gold = next((item for item in matches if item.get("family") != "gold"), None)
    if best.get("family") == "gold" and nearest_non_gold and nearest_non_gold is not best:
        non_gold_gap = nearest_non_gold["distance"] - best["distance"]
        if non_gold_gap < CLASSIFIER_UNCERTAIN_GAP:
            second = nearest_non_gold
    gap = (second["distance"] - best["distance"]) if second else 0.0
    threshold = parse_float(best.get("threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
    accepted = bool(best.get("accepted"))
    decision, result_type, decision_message, uncertain = classifier_decision_from_best(
        best,
        second,
        accepted,
        CLASSIFIER_UNCERTAIN_GAP,
    )

    distance_ratio = min(best["distance"] / threshold, 2.0) if threshold > 0 else 2.0
    threshold_confidence = max(0.0, min(99.9, (1.0 - (distance_ratio / 2.0)) * 100.0))
    gap_bonus = min(max(gap, 0.0), 1.0) * 10.0
    confidence_pct = max(0.0, min(99.9, threshold_confidence + gap_bonus))
    return {
        "prediction": decision,
        "nearest_class": best["material"],
        "result_type": result_type,
        "decision_message": decision_message,
        "accepted": accepted,
        "uncertain": uncertain,
        "threshold": round(threshold, 6),
        "distance": best["distance"],
        "nearest_gap": round(gap, 6),
        "confidence": round(confidence_pct, 2),
        "top_matches": [
            {
                "rank": index + 1,
                "material": item["material"],
                "distance": item["distance"],
                "sample_count": item["sample_count"],
                "threshold": item.get("threshold"),
                "accepted": item.get("accepted"),
                "active": item.get("active"),
                "status": item.get("status"),
                "hill_available": item.get("hill_available"),
            }
            for index, item in enumerate(matches[:3])
        ],
        "all_matches": all_matches[:8],
        "classification_method": model.get("classification_method", CLASSIFIER_ALGORITHMS["hybrid_hill_knn"]["method"]),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version"),
        "hill_available": bool(best.get("hill_available")),
    }


def predict_with_two_pass_gold_gate(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Classifier model not found. Train classifier first.")
    algorithm = model.get("algorithm")
    if algorithm not in {"two_pass_gold_gate", "two_pass_compact_gate"}:
        raise ValueError("Selected model is not a Two-pass Gold Gate model. Recompute the selected classifier.")

    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(features.get(key)) is None]
    if missing:
        raise ValueError(f"Missing classifier features: {', '.join(missing)}")

    vector = (
        vector_from_compact_two_pass_features(features)
        if algorithm == "two_pass_compact_gate"
        else vector_from_mahalanobis_features(features)
    )
    gate_model = model.get("gate_model") if isinstance(model.get("gate_model"), dict) else {}
    purity_model = model.get("purity_model") if isinstance(model.get("purity_model"), dict) else {}
    k = max(1, int(model.get("knn_k", TWO_PASS_K) or TWO_PASS_K))
    gate_matches = score_normalized_knn_model(vector, gate_model, k)
    active_gate_matches = [item for item in gate_matches if item.get("active")]
    if not active_gate_matches:
        raise ValueError("Gold gate model has no active classes. Add more GOLD_LIKE and NON_GOLD samples.")

    best_gate = active_gate_matches[0]
    second_gate = active_gate_matches[1] if len(active_gate_matches) > 1 else None
    gate_gap = (second_gate["distance"] - best_gate["distance"]) if second_gate else 0.0
    gate_threshold = parse_float(best_gate.get("threshold"), CLASSIFIER_MIN_THRESHOLD) or CLASSIFIER_MIN_THRESHOLD
    gate_accepted = bool(best_gate.get("accepted"))
    gate_votes = nearest_gate_votes(vector, gate_model, k)
    gold_vote_count = sum(1 for item in gate_votes if item.get("gate_label") == "GOLD_LIKE")
    non_gold_vote_count = sum(1 for item in gate_votes if item.get("gate_label") == "NON_GOLD")
    gate_vote = "GOLD_LIKE" if gold_vote_count > non_gold_vote_count else "NON_GOLD"
    first_two_gate_votes = [item.get("gate_label") for item in gate_votes[:2]]
    strong_non_gold_vote = (
        non_gold_vote_count > gold_vote_count
        and len(first_two_gate_votes) >= 2
        and all(label == "NON_GOLD" for label in first_two_gate_votes)
    )
    best_gold_gate = next((item for item in active_gate_matches if item["material"] == "GOLD_LIKE"), None)
    best_non_gold_gate = next((item for item in active_gate_matches if item["material"] == "NON_GOLD"), None)
    critical_non_gold_close = (
        gate_vote == "GOLD_LIKE"
        and best_gold_gate is not None
        and best_non_gold_gate is not None
        and (best_non_gold_gate["distance"] - best_gold_gate["distance"]) < TWO_PASS_GATE_UNCERTAIN_GAP
    )
    nearest_non_gold = nearest_material_label(vector, gate_model, "NON_GOLD")

    if not gate_accepted:
        decision = "Unknown / suspicious sample"
        result_type = "unknown"
        accepted = False
        uncertain = False
        nearest_class = nearest_non_gold or best_gate["material"]
        decision_message = f"Gold gate rejected nearest class {best_gate['material']}."
        purity_matches = []
    elif strong_non_gold_vote:
        decision = f"Non-gold: {nearest_non_gold or 'Sample'}"
        result_type = "known_non_gold"
        accepted = True
        uncertain = False
        nearest_class = nearest_non_gold or "NON_GOLD"
        decision_message = "Gold gate classified the sample as non-gold with strong nearest-neighbor support."
        purity_matches = []
    elif gate_vote == "NON_GOLD":
        decision = "Unknown / suspicious sample"
        result_type = "unknown"
        accepted = False
        uncertain = True
        nearest_class = nearest_non_gold or "NON_GOLD"
        decision_message = "Gold gate is mixed; non-gold vote is not strong enough."
        purity_matches = []
    elif critical_non_gold_close:
        decision = "Unknown / suspicious sample"
        result_type = "unknown"
        accepted = False
        uncertain = True
        nearest_class = best_gate["material"]
        decision_message = "Gold gate vote is gold-like, but nearest non-gold is critically close."
        purity_matches = []
    else:
        purity_matches = score_normalized_knn_model(vector, purity_model, k)
        active_purity_matches = [item for item in purity_matches if item.get("active")]
        if not active_purity_matches:
            decision = "Gold-like but purity uncertain"
            result_type = "gold_like_uncertain"
            accepted = True
            uncertain = True
            nearest_class = "GOLD_LIKE"
            decision_message = "Gold gate accepted, but purity model has no active purity classes."
        else:
            best_purity = active_purity_matches[0]
            second_purity = active_purity_matches[1] if len(active_purity_matches) > 1 else None
            purity_gap = (second_purity["distance"] - best_purity["distance"]) if second_purity else 0.0
            purity_accepted = bool(best_purity.get("accepted"))
            if not purity_accepted or (second_purity is not None and purity_gap < CLASSIFIER_UNCERTAIN_GAP):
                decision = "Gold-like but purity uncertain"
                result_type = "gold_like_uncertain"
                accepted = True
                uncertain = True
                nearest_class = best_purity["material"]
                decision_message = "Gold gate accepted, but purity confidence is low."
            else:
                decision = f"Genuine gold: {best_purity['material']}"
                result_type = "genuine_gold"
                accepted = True
                uncertain = False
                nearest_class = best_purity["material"]
                decision_message = f"Gold gate accepted and purity matched {best_purity['material']}."

    distance_ratio = min(best_gate["distance"] / gate_threshold, 2.0) if gate_threshold > 0 else 2.0
    threshold_confidence = max(0.0, min(95.0, (1.0 - (distance_ratio / 2.0)) * 100.0))
    vote_confidence = 95.0 if max(gold_vote_count, non_gold_vote_count) >= 3 else 72.0
    separation_confidence = min(95.0, max(0.0, (gate_gap / 0.25) * 95.0))
    confidence_pct = min(threshold_confidence, max(vote_confidence * 0.65, separation_confidence))
    if uncertain or critical_non_gold_close:
        confidence_pct = min(confidence_pct, 55.0)
    top_matches = [
        {
            "rank": index + 1,
            "material": item["material"],
            "distance": item["distance"],
            "sample_count": item["sample_count"],
            "threshold": item.get("threshold"),
            "accepted": item.get("accepted"),
            "active": item.get("active"),
            "status": item.get("status"),
        }
        for index, item in enumerate((purity_matches or active_gate_matches)[:3])
    ]
    return {
        "prediction": decision,
        "nearest_class": nearest_class,
        "result_type": result_type,
        "decision_message": decision_message,
        "accepted": accepted,
        "uncertain": uncertain,
        "threshold": round(gate_threshold, 6),
        "distance": best_gate["distance"],
        "nearest_gap": round(gate_gap, 6),
        "confidence": round(confidence_pct, 2),
        "top_matches": top_matches,
        "all_matches": active_gate_matches[:8],
        "gate_result": best_gate["material"],
        "gate_matches": active_gate_matches[:3],
        "gate_vote": gate_vote,
        "gate_votes": gate_votes,
        "gold_vote_count": gold_vote_count,
        "non_gold_vote_count": non_gold_vote_count,
        "strong_non_gold_vote": strong_non_gold_vote,
        "purity_matches": (purity_matches or [])[:3],
        "classification_method": model.get("classification_method", CLASSIFIER_ALGORITHMS[algorithm]["method"]),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version"),
    }


def predict_with_binary_brass_ch1_f1(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Binary Brass CH1 F1 model is not ready. Press Compute Model first.")
    if model.get("algorithm") != "binary_brass_ch1_f1":
        raise ValueError("Selected model is not a Binary Brass CH1 F1 model. Recompute the selected classifier.")

    coverage_ratio = parse_float(features.get("contact_area_ratio"))
    thickness_mm = parse_float(features.get("thickness_mm"))
    ch1_f1_delta_pct = parse_float(features.get("f1_ch1_delta_pct"))
    missing = []
    if coverage_ratio is None:
        missing.append("contact_area_ratio")
    if thickness_mm is None:
        missing.append("thickness_mm")
    if ch1_f1_delta_pct is None:
        missing.append("f1_ch1_delta_pct")
    if missing:
        raise ValueError(f"Missing brass classifier features: {', '.join(missing)}")

    coverage_pct = coverage_ratio * 100.0 if coverage_ratio <= 10.0 else coverage_ratio
    result = classify_brass(coverage_pct, thickness_mm, abs(ch1_f1_delta_pct))
    is_brass = result["label"] == "brass"
    confidence_map = {"high": 96.0, "medium": 78.0, "low": 35.0}
    confidence_pct = confidence_map.get(result["confidence"], 0.0)
    threshold = result["tolerance_used"]
    residual_distance = result["abs_residual"]
    primary_label = result["label"]
    secondary_label = "not_brass" if primary_label == "brass" else "brass"
    top_matches = [
        {
            "rank": 1,
            "material": primary_label,
            "distance": round(residual_distance, 6),
            "sample_count": model.get("eligible_record_count", 0) if primary_label == "brass" else 0,
            "threshold": threshold,
            "accepted": True,
            "active": True,
            "status": result["confidence"],
            "match_percent": confidence_pct,
        },
        {
            "rank": 2,
            "material": secondary_label,
            "distance": round(residual_distance, 6),
            "sample_count": model.get("eligible_record_count", 0) if secondary_label == "brass" else 0,
            "threshold": threshold,
            "accepted": False,
            "active": True,
            "status": "alternate",
            "match_percent": 0.0,
        },
    ]
    return {
        "prediction": result["label"],
        "nearest_class": result["label"],
        "result_type": "known_non_gold" if is_brass else "not_brass",
        "decision_message": (
            "CH1 F1 residual is compatible with the fitted brass response surface."
            if is_brass
            else "CH1 F1 residual is outside the brass response tolerance."
        ),
        "accepted": is_brass,
        "uncertain": result["confidence"] == "medium",
        "threshold": round(threshold, 6),
        "distance": round(residual_distance, 6),
        "nearest_gap": round(abs(threshold - residual_distance), 6),
        "confidence": confidence_pct,
        "top_matches": top_matches,
        "all_matches": top_matches,
        "classification_method": model.get("classification_method", CLASSIFIER_ALGORITHMS["binary_brass_ch1_f1"]["method"]),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version", 4),
        "brass_model": result,
        "warnings": result.get("warnings", []),
        "predicted_ch1_f1": round(result["predicted_ch1_f1"], 6),
        "measured_ch1_f1": round(result["measured_ch1_f1"], 6),
        "residual": round(result["residual"], 6),
        "abs_residual": round(result["abs_residual"], 6),
    }


def predict_with_binary_brass_ch2_f1_f3(features: dict, model: dict | None = None) -> dict:
    model = model or load_classifier_model()
    if not model:
        raise ValueError("Binary Brass CH2 F1/F3 model is not ready. Press Compute Model first.")
    if model.get("algorithm") != "binary_brass_ch2_f1_f3":
        raise ValueError("Selected model is not a Binary Brass CH2 F1/F3 model. Recompute the selected classifier.")

    coverage_ratio = parse_float(features.get("contact_area_ratio"))
    thickness_mm = parse_float(features.get("thickness_mm"))
    ch2_f1_delta_pct = parse_float(features.get("f1_ch2_delta_pct"))
    ch2_f3_delta_pct = parse_float(features.get("f3_ch2_delta_pct"))
    missing = []
    if coverage_ratio is None:
        missing.append("contact_area_ratio")
    if thickness_mm is None:
        missing.append("thickness_mm")
    if ch2_f1_delta_pct is None:
        missing.append("f1_ch2_delta_pct")
    if ch2_f3_delta_pct is None:
        missing.append("f3_ch2_delta_pct")
    if missing:
        raise ValueError(f"Missing brass CH2 classifier features: {', '.join(missing)}")

    coverage_pct = coverage_ratio * 100.0 if coverage_ratio <= 10.0 else coverage_ratio
    result = classify_brass_ch2_f1_f3(
        coverage_pct,
        thickness_mm,
        abs(ch2_f1_delta_pct),
        abs(ch2_f3_delta_pct),
    )
    is_accepted = result["label"] in {"brass", "brass_like"}
    confidence_map = {"high": 96.0, "medium": 78.0, "low": 35.0}
    confidence_pct = confidence_map.get(result["confidence"], 0.0)
    distance = result["two_feature_distance"]
    secondary_label = "not_brass_or_outlier" if is_accepted else "brass"
    top_matches = [
        {
            "rank": 1,
            "material": result["label"],
            "distance": round(distance, 6),
            "sample_count": model.get("eligible_record_count", 0) if is_accepted else 0,
            "threshold": 2.0 if result["label"] == "brass" else 3.0,
            "accepted": True,
            "active": True,
            "status": result["confidence"],
            "match_percent": confidence_pct,
        },
        {
            "rank": 2,
            "material": secondary_label,
            "distance": round(distance, 6),
            "sample_count": 0 if is_accepted else model.get("eligible_record_count", 0),
            "threshold": 3.0,
            "accepted": False,
            "active": True,
            "status": "alternate",
            "match_percent": 0.0,
        },
    ]
    return {
        "prediction": result["label"],
        "nearest_class": result["label"],
        "result_type": "known_non_gold" if is_accepted else "not_brass",
        "decision_message": (
            "CH2 F1/F3 normalized residual distance is compatible with the fitted brass surfaces."
            if is_accepted
            else "CH2 F1/F3 normalized residual distance is outside the brass surface tolerance."
        ),
        "accepted": is_accepted,
        "uncertain": result["label"] == "brass_like",
        "threshold": 2.0 if result["label"] == "brass" else 3.0,
        "distance": round(distance, 6),
        "nearest_gap": round(abs((2.0 if result["label"] == "brass" else 3.0) - distance), 6),
        "confidence": confidence_pct,
        "top_matches": top_matches,
        "all_matches": top_matches,
        "classification_method": model.get("classification_method", CLASSIFIER_ALGORITHMS["binary_brass_ch2_f1_f3"]["method"]),
        "model_trained_at": model.get("trained_at"),
        "feature_version": model.get("feature_version", 5),
        "brass_model": result,
        "warnings": [result["warning"]] if result.get("warning") else [],
        "predicted_ch2_f1": round(result["predicted_ch2_f1"], 6),
        "measured_ch2_f1": round(result["measured_ch2_f1"], 6),
        "residual_ch2_f1": round(result["residual_ch2_f1"], 6),
        "norm_residual_ch2_f1": round(result["norm_residual_ch2_f1"], 6),
        "predicted_ch2_f3": round(result["predicted_ch2_f3"], 6),
        "measured_ch2_f3": round(result["measured_ch2_f3"], 6),
        "residual_ch2_f3": round(result["residual_ch2_f3"], 6),
        "norm_residual_ch2_f3": round(result["norm_residual_ch2_f3"], 6),
        "two_feature_distance": round(distance, 6),
    }


def predict_with_selected_classifier(features: dict) -> dict:
    algorithm = selected_classifier_algorithm()
    if algorithm == "two_pass_frequency_rf":
        return predict_with_two_pass_frequency_rf(features)
    model = load_classifier_model()
    model_algorithm = model.get("algorithm", "mahalanobis") if model else None
    if model_algorithm != algorithm:
        label = CLASSIFIER_ALGORITHMS.get(algorithm, CLASSIFIER_ALGORITHMS[CLASSIFIER_DEFAULT_ALGORITHM])["label"]
        raise ValueError(f"{label} model is not trained. Press Compute Model after selecting the classifier.")
    if algorithm == "binary_brass_ch2_f1_f3":
        return predict_with_binary_brass_ch2_f1_f3(features, model)
    if algorithm == "binary_brass_ch1_f1":
        return predict_with_binary_brass_ch1_f1(features, model)
    if algorithm in {"two_pass_gold_gate", "two_pass_compact_gate"}:
        return predict_with_two_pass_gold_gate(features, model)
    if algorithm == "hybrid_hill_knn":
        return predict_with_hybrid_hill_knn(features, model)
    if algorithm == "knn_cluster":
        return predict_with_knn_cluster(features, model)
    return predict_with_mahalanobis(features, model)


def predict_with_two_pass_frequency_rf(features: dict) -> dict:
    feature_names = features.get("feature_names") if isinstance(features.get("feature_names"), list) else []
    feature_vector = features.get("feature_vector") if isinstance(features.get("feature_vector"), list) else []
    if feature_names != FREQUENCY_RF_FEATURE_NAMES:
        raise ValueError("Gold Standard feature order is invalid")
    if len(feature_vector) != len(FREQUENCY_RF_FEATURE_NAMES):
        raise ValueError("Gold Standard feature vector is incomplete")
    if any(parse_float(value) is None for value in feature_vector):
        missing = [name for name, value in zip(FREQUENCY_RF_FEATURE_NAMES, feature_vector) if parse_float(value) is None]
        raise ValueError(f"Missing Gold Standard features: {', '.join(missing)}")

    gold_bundle, purity_bundle = load_frequency_rf_models()
    gold_model = gold_bundle["model"]
    purity_model = purity_bundle["model"]
    vector_2d = [[float(value) for value in feature_vector]]

    gold_label = str(gold_model.predict(vector_2d)[0])
    gold_proba = gold_model.predict_proba(vector_2d)[0] if hasattr(gold_model, "predict_proba") else None
    gold_classes = [str(value) for value in getattr(gold_model, "classes_", gold_bundle.get("labels", []))]
    gold_prob_map = {
        label: round(float(prob), 6)
        for label, prob in zip(gold_classes, list(gold_proba) if gold_proba is not None else [])
    }
    gold_confidence = max(gold_prob_map.values()) if gold_prob_map else 1.0
    sorted_gold = sorted(gold_prob_map.items(), key=lambda item: item[1], reverse=True)
    gold_margin = (sorted_gold[0][1] - sorted_gold[1][1]) if len(sorted_gold) > 1 else sorted_gold[0][1] if sorted_gold else 0.0

    is_ambiguous_gold = gold_confidence < 0.55 or gold_margin < 0.10
    if is_ambiguous_gold:
        top_matches = [
            {"rank": idx + 1, "material": label, "distance": round(1.0 - prob, 6), "match_percent": round(prob * 100.0, 2)}
            for idx, (label, prob) in enumerate(sorted_gold[:3])
        ]
        return {
            "prediction": "Unknown Metal Type Kindly Verify the sample",
            "nearest_class": sorted_gold[0][0] if sorted_gold else "Unknown",
            "result_type": "unknown",
            "decision_message": "Gold gate prediction is ambiguous. Kindly verify the sample.",
            "accepted": False,
            "uncertain": True,
            "threshold": 55.0,
            "distance": round(1.0 - gold_confidence, 6),
            "nearest_gap": round(gold_margin, 6),
            "confidence": round(gold_confidence * 100.0, 2),
            "top_matches": top_matches,
            "all_matches": top_matches,
            "classification_method": CLASSIFIER_ALGORITHMS["two_pass_frequency_rf"]["method"],
            "model_trained_at": None,
            "feature_version": 1,
            "material_result": "Unknown Metal Type Kindly Verify the sample",
            "purity_result": None,
            "model_version": FREQUENCY_RF_MODEL_VERSION,
            "feature_names": list(feature_names),
            "feature_vector": [round(float(value), 6) for value in feature_vector],
            "gold_prediction": gold_label,
            "gold_probabilities": gold_prob_map,
            "purity_prediction": None,
        }

    if gold_label.lower() != "gold":
        top_matches = [
            {"rank": idx + 1, "material": label, "distance": round(1.0 - prob, 6), "match_percent": round(prob * 100.0, 2)}
            for idx, (label, prob) in enumerate(sorted_gold[:3])
        ]
        return {
            "prediction": "Non-Gold",
            "nearest_class": gold_label,
            "result_type": "known_non_gold",
            "decision_message": "Gold gate classified this sample as Non-Gold.",
            "accepted": True,
            "uncertain": False,
            "threshold": 55.0,
            "distance": round(1.0 - gold_confidence, 6),
            "nearest_gap": round(gold_margin, 6),
            "confidence": round(gold_confidence * 100.0, 2),
            "top_matches": top_matches,
            "all_matches": top_matches,
            "classification_method": CLASSIFIER_ALGORITHMS["two_pass_frequency_rf"]["method"],
            "model_trained_at": None,
            "feature_version": 1,
            "material_result": "Non-Gold",
            "purity_result": None,
            "model_version": FREQUENCY_RF_MODEL_VERSION,
            "feature_names": list(feature_names),
            "feature_vector": [round(float(value), 6) for value in feature_vector],
            "gold_prediction": gold_label,
            "gold_probabilities": gold_prob_map,
            "purity_prediction": None,
        }

    purity_label = str(purity_model.predict(vector_2d)[0])
    purity_proba = purity_model.predict_proba(vector_2d)[0] if hasattr(purity_model, "predict_proba") else None
    purity_classes = [str(value) for value in getattr(purity_model, "classes_", purity_bundle.get("labels", []))]
    purity_prob_map = {
        label: round(float(prob), 6)
        for label, prob in zip(purity_classes, list(purity_proba) if purity_proba is not None else [])
    }
    sorted_purity = sorted(purity_prob_map.items(), key=lambda item: item[1], reverse=True)
    purity_confidence = max(purity_prob_map.values()) if purity_prob_map else 1.0
    purity_margin = (sorted_purity[0][1] - sorted_purity[1][1]) if len(sorted_purity) > 1 else sorted_purity[0][1] if sorted_purity else 0.0
    if purity_confidence < 0.55 or purity_margin < 0.08:
        prediction = "Unknown Metal Type Kindly Verify the sample"
        accepted = False
        uncertain = True
        result_type = "unknown"
        decision_message = "Purity prediction is ambiguous. Kindly verify the sample."
        purity_result = None
    else:
        prediction = f"Gold {purity_label}"
        accepted = True
        uncertain = False
        result_type = "genuine_gold"
        decision_message = f"Gold gate accepted. Purity classified as {purity_label}."
        purity_result = purity_label

    top_matches = [
        {"rank": idx + 1, "material": f"Gold {label}", "distance": round(1.0 - prob, 6), "match_percent": round(prob * 100.0, 2)}
        for idx, (label, prob) in enumerate(sorted_purity[:3])
    ]
    confidence_pct = min(gold_confidence, purity_confidence) * 100.0
    return {
        "prediction": prediction,
        "nearest_class": f"Gold {purity_label}" if purity_label else "Gold",
        "result_type": result_type,
        "decision_message": decision_message,
        "accepted": accepted,
        "uncertain": uncertain,
        "threshold": 55.0,
        "distance": round(1.0 - min(gold_confidence, purity_confidence), 6),
        "nearest_gap": round(min(gold_margin, purity_margin), 6),
        "confidence": round(confidence_pct, 2),
        "top_matches": top_matches,
        "all_matches": top_matches,
        "classification_method": CLASSIFIER_ALGORITHMS["two_pass_frequency_rf"]["method"],
        "model_trained_at": None,
        "feature_version": 1,
        "material_result": "Gold",
        "purity_result": purity_result,
        "model_version": FREQUENCY_RF_MODEL_VERSION,
        "feature_names": list(feature_names),
        "feature_vector": [round(float(value), 6) for value in feature_vector],
        "gold_prediction": gold_label,
        "gold_probabilities": gold_prob_map,
        "purity_prediction": purity_label,
        "purity_probabilities": purity_prob_map,
    }


def add_match_percentages(matches: list[dict], score_key: str = "distance") -> list[dict]:
    if not matches:
        return []
    similarities = []
    for item in matches:
        score = parse_float(item.get(score_key), 0.0) or 0.0
        similarities.append(math.exp(-score))
    total_similarity = sum(similarities) or 1.0
    for idx, item in enumerate(matches):
        item["match_percent"] = round((similarities[idx] / total_similarity) * 100, 2)
    return matches


def is_classifier_model_error(message: str | None) -> bool:
    text = str(message or "").lower()
    if not text:
        return False
    markers = (
        "model file",
        "model not found",
        "error loading model",
        "joblib is not available",
        "gold standard",
        "selected model is not",
        "model is invalid",
        "not trained",
    )
    return any(marker in text for marker in markers)


def classifier_prediction_for_collection(
    collection: dict,
    calibration: dict,
    weight_grams: float,
    thickness_mm: float,
    contact_area_ratio: float,
    shape: str = "Other",
) -> tuple[dict | None, dict | None]:
    selected_algorithm = selected_classifier_algorithm()
    if selected_algorithm == "two_pass_frequency_rf":
        classifier_features = build_frequency_rf_feature_payload(
            collection.get("frequency_sequence", []),
            calibration,
            weight_grams,
            thickness_mm,
            contact_area_ratio,
        )
        if classifier_features["missing"]:
            return None, {
                "message": f"Gold Standard classifier skipped. Missing features: {', '.join(classifier_features['missing'])}",
                "features": classifier_features,
            }
        classifier_features["shape"] = shape
        classifier_features["daq_correction"] = collection.get("daq_correction") or daq_correction_metadata()
        try:
            prediction = predict_with_selected_classifier(classifier_features)
        except ValueError as exc:
            return None, {
                "message": str(exc),
                "features": classifier_features,
            }
        prediction["measured_frequency_values"] = classifier_features["measured_frequency_values"]
        prediction["calibration_frequency_air"] = classifier_features["calibration_frequency_air"]
        prediction["daq_correction"] = classifier_features["daq_correction"]
        return prediction, {"features": classifier_features}

    classifier_features = mahalanobis_features_from_frequency_sequence(
        collection.get("frequency_sequence", []),
        calibration,
        weight_grams,
        thickness_mm,
        contact_area_ratio,
    )
    classifier_features["shape"] = shape
    if selected_algorithm == "binary_brass_ch2_f1_f3":
        brass_required = ["contact_area_ratio", "thickness_mm", "f1_ch2_delta_pct", "f3_ch2_delta_pct"]
        missing = [key for key in brass_required if parse_float(classifier_features.get(key)) is None]
        if missing:
            return None, {
                "message": f"Brass CH2 classifier skipped. Missing features: {', '.join(missing)}",
                "features": classifier_features,
            }
        try:
            prediction = predict_with_selected_classifier(classifier_features)
        except ValueError as exc:
            return None, {
                "message": str(exc),
                "features": classifier_features,
            }
        return prediction, {"features": classifier_features}

    if selected_algorithm == "binary_brass_ch1_f1":
        brass_required = ["contact_area_ratio", "thickness_mm", "f1_ch1_delta_pct"]
        missing = [key for key in brass_required if parse_float(classifier_features.get(key)) is None]
        if missing:
            return None, {
                "message": f"Brass classifier skipped. Missing features: {', '.join(missing)}",
                "features": classifier_features,
            }
        try:
            prediction = predict_with_selected_classifier(classifier_features)
        except ValueError as exc:
            return None, {
                "message": str(exc),
                "features": classifier_features,
            }
        return prediction, {"features": classifier_features}

    missing = [key for key in MAHALANOBIS_FEATURE_KEYS if parse_float(classifier_features.get(key)) is None]
    if missing:
        return None, {
            "message": f"Classifier skipped. Missing features: {', '.join(missing)}",
            "features": classifier_features,
        }

    try:
        prediction = predict_with_selected_classifier(classifier_features)
    except ValueError as exc:
        return None, {
            "message": str(exc),
            "features": classifier_features,
        }

    prediction["top_matches"] = add_match_percentages(prediction.get("top_matches", []), "distance")
    return prediction, {"features": classifier_features}


def display_match_label(match: dict) -> str:
    material = match.get("material_base") or match.get("material") or "Unknown"
    purity_value = parse_float(match.get("purity_value"))
    purity = match.get("purity")
    if purity_value is not None and str(int(purity_value)) not in str(material):
        material = f"{material} {int(purity_value)}"
    elif purity and purity not in {"Known", "Unknown", "Enter Later"} and str(purity) not in str(material):
        material = f"{material} {purity}"
    return material


def normalize_label_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def parse_load_cell_response(response: str) -> dict:
    text = str(response or "").strip()
    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*$", text)
    weight_g = parse_float(match.group(1)) if match else None
    unit = match.group(2) if match and match.group(2) else "g"
    tokens = text.split()
    first_token = tokens[0].upper() if len(tokens) >= 1 else ""
    second_token = tokens[1].upper() if len(tokens) >= 2 else ""
    stable = first_token == "S" and second_token == "S"
    dynamic = first_token == "S" and second_token == "D"
    status = "stable" if stable else ("dynamic" if dynamic else "unknown")
    return {
        "raw_response": text,
        "weight_g": round(weight_g, 3) if weight_g is not None else None,
        "unit": unit,
        "status": status,
        "stable": stable,
        "dynamic": dynamic,
        "mode_tokens": [first_token, second_token],
    }


def open_load_cell_handle():
    global LOAD_CELL_HANDLE
    if serial is None:
        return None, "pyserial is not installed"

    if LOAD_CELL_HANDLE is not None and getattr(LOAD_CELL_HANDLE, "is_open", False):
        return LOAD_CELL_HANDLE, None

    try:
        LOAD_CELL_HANDLE = serial.Serial(
            port=LOAD_CELL_PORT,
            baudrate=LOAD_CELL_BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,
            write_timeout=1.0,
        )
        time.sleep(0.5)
        LOAD_CELL_HANDLE.reset_input_buffer()
        return LOAD_CELL_HANDLE, None
    except Exception as exc:
        LOAD_CELL_HANDLE = None
        return None, f"Unable to open {LOAD_CELL_PORT}: {exc}"


def reset_load_cell_handle() -> None:
    global LOAD_CELL_HANDLE
    if LOAD_CELL_HANDLE is not None:
        try:
            LOAD_CELL_HANDLE.close()
        except Exception:
            pass
    LOAD_CELL_HANDLE = None


def send_load_cell_command(command: str, wait_seconds: float = 0.05, require_weight: bool = True) -> dict:
    if serial is None:
        return {"ok": False, "error": "pyserial is not installed", "raw_response": ""}

    with LOAD_CELL_LOCK:
        handle, error = open_load_cell_handle()
        if handle is None:
            return {"ok": False, "error": error or "Unable to open load cell port", "raw_response": ""}

        try:
            handle.reset_input_buffer()
            handle.write((command + "\r\n").encode("ascii"))
            handle.flush()
            time.sleep(wait_seconds)
            response = handle.readline().decode("ascii", errors="replace").strip()
        except Exception as exc:
            reset_load_cell_handle()
            return {"ok": False, "error": f"Load cell command failed: {exc}", "raw_response": ""}
        finally:
            reset_load_cell_handle()

    parsed = parse_load_cell_response(response)
    if require_weight and parsed["weight_g"] is None:
        return {
            "ok": False,
            **parsed,
            "error": f"No valid weight received for command {command!r}",
        }

    return {"ok": True, **parsed}


def load_cell_reading_with_meta(reading: dict, attempts: int) -> dict:
    return {
        **reading,
        "attempts": attempts,
        "port": LOAD_CELL_PORT,
        "baud": LOAD_CELL_BAUD,
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
    }


def read_load_cell(
    stable_only: bool = False,
    max_attempts: int = LOAD_CELL_STABLE_MAX_ATTEMPTS,
    retry_seconds: float = LOAD_CELL_STABLE_RETRY_SECONDS,
) -> dict:
    last_reading = None
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        reading = send_load_cell_command(LOAD_CELL_READ_COMMAND, wait_seconds=LOAD_CELL_READ_WAIT_SECONDS, require_weight=True)
        last_reading = reading
        if reading.get("ok") and (not stable_only or reading.get("stable")):
            return load_cell_reading_with_meta(reading, attempt)
        if attempt < attempts:
            time.sleep(retry_seconds)

    if last_reading is None:
        return load_cell_reading_with_meta(
            {"ok": False, "error": "No load cell response received", "raw_response": "", "stable": False, "dynamic": False},
            attempts,
        )
    if stable_only and last_reading.get("ok") and last_reading.get("dynamic"):
        last_reading = {
            **last_reading,
            "ok": False,
            "error": "Load cell reading remained dynamic (S D). Please wait for a stable reading.",
        }
    return load_cell_reading_with_meta(last_reading, attempts)


def read_load_cell_average(
    sample_count: int = 10,
    sample_gap_seconds: float = LOAD_CELL_STABLE_RETRY_SECONDS,
    stable_only: bool = False,
) -> dict:
    readings = []
    raw_readings = []
    errors = []
    stable_count = 0
    dynamic_count = 0
    for _ in range(max(1, sample_count)):
        reading = read_load_cell(
            stable_only=stable_only,
            max_attempts=1 if not stable_only else LOAD_CELL_STABLE_MAX_ATTEMPTS,
            retry_seconds=0.0 if not stable_only else LOAD_CELL_STABLE_RETRY_SECONDS,
        )
        if reading.get("ok") and parse_float(reading.get("weight_g")) is not None:
            readings.append(float(reading["weight_g"]))
            raw_readings.append(reading.get("raw_response", ""))
            if reading.get("stable"):
                stable_count += 1
            elif reading.get("dynamic"):
                dynamic_count += 1
        elif reading.get("error"):
            errors.append(reading["error"])
        time.sleep(sample_gap_seconds)

    if not readings:
        return {
            "ok": False,
            "error": errors[-1] if errors else "No valid load cell readings",
            "sample_count": 0,
            "requested_sample_count": sample_count,
            "port": LOAD_CELL_PORT,
            "baud": LOAD_CELL_BAUD,
            "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        }

    mean = sum(readings) / len(readings)
    variance = sum((value - mean) ** 2 for value in readings) / len(readings)
    return {
        "ok": True,
        "weight_g": round(mean, 3),
        "std_g": round(math.sqrt(variance), 4),
        "min_g": round(min(readings), 3),
        "max_g": round(max(readings), 3),
        "unit": "g",
        "stable": dynamic_count == 0,
        "status": "averaged_stable" if dynamic_count == 0 else "averaged_dynamic",
        "sample_count": len(readings),
        "requested_sample_count": sample_count,
        "stable_sample_count": stable_count,
        "dynamic_sample_count": dynamic_count,
        "raw_response": raw_readings[-1] if raw_readings else "",
        "port": LOAD_CELL_PORT,
        "baud": LOAD_CELL_BAUD,
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
    }


def simulated_summary(channel: str) -> dict:
    if channel == "ch1":
        base = random.uniform(0.830, 0.865)
        unit = "V RMS"
        device = "primary_voltage"
        tolerance_floor = 0.004
    else:
        base = random.uniform(0.930, 0.970)
        unit = "V RMS"
        device = "secondary_voltage"
        tolerance_floor = 0.006

    std = random.uniform(0.0018, 0.0045)
    return {
        "mean": round(base, 6),
        "std": round(std, 6),
        "tolerance": round(max(std * 3, tolerance_floor), 6),
        "unit": unit,
        "sample_count": random.randint(90, 130),
        "last_device": device,
        "source": "simulator",
    }


def simulated_sensor_state() -> dict:
    ch1 = simulated_summary("ch1")
    ch2 = simulated_summary("ch2")
    return {
        "ch1": {
            "device": ch1["last_device"],
            "rms": ch1["mean"],
            "std": ch1["std"],
            "quality": round(random.uniform(0.965, 0.996), 3),
            "unit": "V",
            "source": "simulator",
            "valid": True,
            "error": "",
        },
        "ch2": {
            "device": ch2["last_device"],
            "rms": ch2["mean"],
            "std": ch2["std"],
            "quality": round(random.uniform(0.960, 0.990), 3),
            "unit": "V",
            "source": "simulator",
            "valid": True,
            "error": "",
        },
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "status": "online",
        "acquisition_mode": "simulator",
    }


def format_frequency_sequence(sequence: list[dict]) -> list[dict]:
    formatted = []
    for step in sequence or []:
        channels = step.get("channels", {}) if isinstance(step, dict) else {}
        formatted.append(
            {
                "frequency_command": step.get("frequency_command"),
                "settle_seconds": step.get("settle_seconds"),
                "channels": {
                    key: {
                        "rms": round(parse_float(value.get("rms"), 0.0) or 0.0, 6),
                        "rms_raw": rounded_or_none(parse_float(value.get("rms_raw"))),
                        "std": round(parse_float(value.get("std"), 0.0) or 0.0, 6),
                        "quality": round(parse_float(value.get("quality"), 1.0) or 0.0, 3),
                        "unit": value.get("unit", "V"),
                        "source": value.get("source", ""),
                        "command": value.get("command", ""),
                        "sample_count": int(parse_float(value.get("sample_count"), 0) or 0),
                    }
                    for key, value in channels.items()
                    if isinstance(value, dict)
                },
            }
        )
    return formatted


def build_frequency_air_record(sequence: list[dict]) -> dict:
    air = {}
    for step in sequence or []:
        if not isinstance(step, dict):
            continue
        command = str(step.get("frequency_command") or "").lower()
        if not command:
            continue
        channels = step.get("channels", {}) if isinstance(step.get("channels"), dict) else {}
        air[command] = {
            "ch1": channels.get("ch1"),
            "ch2": channels.get("ch2"),
        }
    return air


def summarize_optional_channel(samples: list[dict], default_unit: str) -> dict:
    if samples:
        return summarize_channel(samples, default_unit)
    return {
        "mean": None,
        "std": None,
        "tolerance": None,
        "unit": f"{default_unit} RMS",
        "sample_count": 0,
        "last_device": "not_configured",
    }


def collect_daq_frequency_summaries(
    target_sample_count: int = 30,
    frequency_commands: list[str] | None = None,
    settle_seconds: float = 5.0,
    channel_commands: dict[str, str] | None = None,
    required_channels: tuple[str, ...] = ("ch1", "ch2"),
) -> dict:
    if service_mode_enabled():
        service_result = collect_signal_service_frequency_summaries(
            target_sample_count=target_sample_count,
            frequency_commands=frequency_commands,
        )
        if service_result.get("ok"):
            return service_result

    with DAQ_LOCK:
        sequence = collect_frequency_sequence(
            frequency_commands=frequency_commands or ["f1", "f2", "f3"],
            ports=["/dev/ttyACM0"],
            settle_seconds=settle_seconds,
            read_timeout_seconds=1.5,
            samples_per_frequency=target_sample_count,
            channel_commands=channel_commands,
            required_channels=required_channels,
        )
    apply_daq_correction_to_collection(sequence)
    if not sequence.ok:
        return {
            "ok": False,
            "mode": "daq",
            "ch1": None,
            "ch2": None,
            "errors": sequence.errors[-10:],
            "frequency_sequence": format_frequency_sequence(sequence.frequency_steps or []),
            "daq_correction": daq_correction_metadata(),
        }

    return {
        "ok": True,
        "mode": "daq",
        "ch1": summarize_optional_channel(sequence.channels["ch1"], "V"),
        "ch2": summarize_optional_channel(sequence.channels["ch2"], "V"),
        "errors": sequence.errors[-10:],
        "frequency_sequence": format_frequency_sequence(sequence.frequency_steps or []),
        "daq_correction": daq_correction_metadata(),
        "raw_measurement": {
            "ch1_rms_raw": raw_rms_mean_from_packets(sequence.channels["ch1"]),
            "ch2_rms_raw": raw_rms_mean_from_packets(sequence.channels["ch2"]),
        },
    }


def collect_channel_summaries(duration_seconds: int):
    mode = acquisition_mode()
    if mode == "simulator":
        return {
            "ok": True,
            "mode": mode,
            "ch1": simulated_summary("ch1"),
            "ch2": simulated_summary("ch2"),
            "errors": [],
            "frequency_sequence": [],
        }

    return collect_daq_frequency_summaries(target_sample_count=30)


def collect_teaching_summaries(duration_seconds: int, target_sample_count: int):
    mode = acquisition_mode()
    if mode == "simulator":
        ch1 = simulated_summary("ch1")
        ch2 = simulated_summary("ch2")
        ch1["sample_count"] = target_sample_count
        ch2["sample_count"] = target_sample_count
        return {
            "ok": True,
            "mode": mode,
            "ch1": ch1,
            "ch2": ch2,
            "errors": [],
            "frequency_sequence": [],
        }

    return collect_daq_frequency_summaries(target_sample_count=target_sample_count)


def collect_verification_summaries(
    duration_seconds: int,
    target_sample_count: int,
    frequency_commands: list[str] | None = None,
):
    mode = acquisition_mode()
    if mode == "simulator":
        ch1 = simulated_summary("ch1")
        ch2 = simulated_summary("ch2")
        ch1["sample_count"] = target_sample_count
        ch2["sample_count"] = target_sample_count
        return {"ok": True, "mode": mode, "ch1": ch1, "ch2": ch2, "errors": [], "frequency_sequence": []}

    if selected_classifier_algorithm() in {"binary_brass_ch2_f1_f3", "binary_brass_ch1_f1"}:
        return collect_daq_frequency_summaries(
            target_sample_count=target_sample_count,
            frequency_commands=["f1", "f3"],
            settle_seconds=1.0,
            channel_commands={"ch1": "R", "ch2": "S"},
            required_channels=("ch1", "ch2"),
        )

    return collect_daq_frequency_summaries(
        target_sample_count=target_sample_count,
        frequency_commands=frequency_commands,
    )


def simulated_frequency_collection(
    frequency_commands: list[str],
    target_sample_count: int,
    required_channels: tuple[str, ...] = ("ch1", "ch2"),
) -> dict:
    steps = []
    ch1_values = []
    ch2_values = []
    for command in frequency_commands:
        channels = {}
        if "ch1" in required_channels:
            ch1 = simulated_summary("ch1")
            ch1["sample_count"] = target_sample_count
            channels["ch1"] = {
                "rms": ch1["mean"],
                "std": ch1["std"],
                "quality": 0.985,
                "unit": "V",
                "source": "simulator",
                "command": "R",
                "sample_count": target_sample_count,
            }
            ch1_values.append(ch1)
        if "ch2" in required_channels:
            ch2 = simulated_summary("ch2")
            ch2["sample_count"] = target_sample_count
            channels["ch2"] = {
                "rms": ch2["mean"],
                "std": ch2["std"],
                "quality": 0.982,
                "unit": "V",
                "source": "simulator",
                "command": "S",
                "sample_count": target_sample_count,
            }
            ch2_values.append(ch2)
        steps.append(
            {
                "frequency_command": command,
                "settle_seconds": 5.0,
                "channels": channels,
            }
        )

    return {
        "ok": True,
        "mode": "simulator",
        "ch1": summarize_optional_channel(ch1_values, "V"),
        "ch2": summarize_optional_channel(ch2_values, "V"),
        "errors": [],
        "frequency_sequence": steps,
    }


def collect_validation_summaries(
    target_sample_count: int = 30,
    settle_seconds: float = 5.0,
) -> dict:
    mode = acquisition_mode()
    if mode == "simulator":
        return simulated_frequency_collection(["f1", "f3"], target_sample_count, required_channels=("ch1", "ch2"))
    return collect_daq_frequency_summaries(
        target_sample_count=target_sample_count,
        frequency_commands=["f1", "f3"],
        settle_seconds=settle_seconds,
        channel_commands={"ch1": "R", "ch2": "S"},
        required_channels=("ch1", "ch2"),
    )


def rounded_or_none(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None else None


def validation_frequency_features(frequency_sequence: list[dict], calibration: dict) -> dict:
    pseudo_record = {"frequency_sequence": frequency_sequence or []}
    feature_map: dict[str, float | None] = {}
    for frequency in ("f1", "f2", "f3"):
        for channel in ("ch1", "ch2"):
            summary = frequency_channel_summary(pseudo_record, frequency, channel)
            air = calibration_frequency_air(calibration, frequency, channel)
            rms = parse_float(summary.get("rms"))
            std = parse_float(summary.get("std"))
            sample_count = int(parse_float(summary.get("sample_count"), 0) or 0)
            air_rms = parse_float(air.get("rms"))
            delta_pct = delta_pct_from_air(rms, air_rms)
            prefix = f"{frequency}_{channel}"
            feature_map[f"{prefix}_rms"] = rounded_or_none(rms)
            feature_map[f"{prefix}_std"] = rounded_or_none(std)
            feature_map[f"{prefix}_sample_count"] = sample_count
            feature_map[f"{prefix}_air_rms"] = rounded_or_none(air_rms)
            feature_map[f"{prefix}_delta_pct"] = rounded_or_none(delta_pct, 3)
            feature_map[f"{prefix}_abs_delta_pct"] = rounded_or_none(abs(delta_pct), 3) if delta_pct is not None else None
    f1_ch1_abs = parse_float(feature_map.get("f1_ch1_abs_delta_pct"))
    f1_ch2_abs = parse_float(feature_map.get("f1_ch2_abs_delta_pct"))
    f3_ch1_abs = parse_float(feature_map.get("f3_ch1_abs_delta_pct"))
    f3_ch2_abs = parse_float(feature_map.get("f3_ch2_abs_delta_pct"))
    feature_map["gain_f1"] = rounded_or_none((f1_ch1_abs / f1_ch2_abs) if f1_ch1_abs is not None and f1_ch2_abs not in (None, 0) else None, 6)
    feature_map["gain_f3"] = rounded_or_none((f3_ch1_abs / f3_ch2_abs) if f3_ch1_abs is not None and f3_ch2_abs not in (None, 0) else None, 6)
    feature_map["voltage_freq_ratio"] = rounded_or_none((f3_ch1_abs / f1_ch1_abs) if f3_ch1_abs is not None and f1_ch1_abs not in (None, 0) else None, 6)
    feature_map["current_freq_ratio"] = rounded_or_none((f3_ch2_abs / f1_ch2_abs) if f3_ch2_abs is not None and f1_ch2_abs not in (None, 0) else None, 6)
    return feature_map


def evaluation_percent_from_membership(mu_value: float | None) -> float:
    if mu_value is None:
        return 0.0
    return round(max(0.0, min(1.0, mu_value)) * 100.0, 2)


def rule_pass_fail(expected_material: str, predicted_label: str) -> bool:
    expected = normalize_label_text(expected_material)
    predicted = normalize_label_text(predicted_label)
    expected_is_brass = "brass" in expected
    if expected_is_brass:
        return predicted == "brass"
    return predicted == "not_brass"


def _fuzzy_primary_membership(z_value: float | None) -> float:
    if z_value is None:
        return 0.0
    if z_value <= 1.5:
        return 1.0
    if z_value <= 2.5:
        return max(0.0, 2.5 - z_value)
    return 0.0


def _mu_label(mu_value: float) -> tuple[str, str]:
    if mu_value >= 0.75:
        return ("brass", "high")
    if mu_value >= 0.40:
        return ("brass_like_uncertain", "medium")
    return ("not_brass", "low")


def _residual_direction(residual: float | None) -> str | None:
    if residual is None:
        return None
    if residual > 0:
        return "response is stronger than brass model"
    if residual < 0:
        return "response is weaker than brass model"
    return "response matches brass model"


def _coverage_pct_from_ratio(contact_area_ratio: float | None) -> float | None:
    if contact_area_ratio is None:
        return None
    return contact_area_ratio * 100.0 if contact_area_ratio <= 10.0 else contact_area_ratio


def _surface_bundle(params: BrassSurfaceParams, source: str, training_count: int, feature_key: str) -> dict:
    return {
        "params": params,
        "source": source,
        "training_count": training_count,
        "feature_key": feature_key,
    }


def _fit_surface_bundle(rows: list[dict], feature_key: str, fallback: BrassSurfaceParams) -> dict:
    valid_rows = [
        row for row in rows
        if parse_float(row.get("coverage_pct")) not in (None, 0)
        and parse_float(row.get("thickness_mm")) not in (None, 0)
        and parse_float(row.get(feature_key)) is not None
    ]
    training_count = len(valid_rows)
    unique_coverage = len({round(parse_float(row.get("coverage_pct"), 0.0) or 0.0, 4) for row in valid_rows})
    if curve_fit is None or training_count < 6 or unique_coverage < 4:
        return _surface_bundle(fallback, "fallback", training_count, feature_key)

    coverage_values = [float(parse_float(row.get("coverage_pct"))) for row in valid_rows]
    thickness_values = [float(parse_float(row.get("thickness_mm"))) for row in valid_rows]
    observed_values = [float(parse_float(row.get(feature_key))) for row in valid_rows]

    def model(xdata, rmin, rspan, k, alpha, d):
        coverage_list, thickness_list = xdata
        return [
            brass_surface(coverage, thickness, rmin, rspan, k, alpha, d)
            for coverage, thickness in zip(coverage_list, thickness_list)
        ]

    try:
        popt, _ = curve_fit(
            model,
            (coverage_values, thickness_values),
            observed_values,
            p0=[fallback.rmin, fallback.rspan, fallback.k, fallback.alpha, fallback.d],
            bounds=([0.0, 0.001, 0.001, 0.1, 0.05], [150.0, 500.0, 100000.0, 8.0, 20.0]),
            maxfev=20000,
        )
    except Exception:
        return _surface_bundle(fallback, "fallback_fit_error", training_count, feature_key)

    predicted_values = [
        brass_surface(coverage, thickness, popt[0], popt[1], popt[2], popt[3], popt[4])
        for coverage, thickness in zip(coverage_values, thickness_values)
    ]
    residuals = [observed - predicted for observed, predicted in zip(observed_values, predicted_values)]
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals)) if residuals else fallback.rmse
    mean_observed = sum(observed_values) / len(observed_values) if observed_values else 0.0
    ss_res = sum(value * value for value in residuals)
    ss_tot = sum((value - mean_observed) ** 2 for value in observed_values)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    fitted = BrassSurfaceParams(
        rmin=float(popt[0]),
        rspan=float(popt[1]),
        k=float(popt[2]),
        alpha=float(popt[3]),
        d=float(popt[4]),
        rmse=rmse if rmse > 1e-9 else fallback.rmse,
        r2=r2,
        name=fallback.name,
    )
    return _surface_bundle(fitted, "fitted", training_count, feature_key)


def brass_training_feature_rows(teaching_records: list[dict], calibration: dict) -> list[dict]:
    rows = []
    for record in teaching_records:
        material_text = normalize_label_text(record.get("material_base") or record.get("material") or "")
        if "brass" not in material_text:
            continue
        thickness_mm = parse_float(record.get("thickness_mm"))
        contact_area_ratio = parse_float(record.get("contact_area_ratio"))
        frequency_sequence = record.get("frequency_sequence") if isinstance(record.get("frequency_sequence"), list) else []
        if thickness_mm in (None, 0) or contact_area_ratio is None or not frequency_sequence:
            continue
        feature_map = validation_frequency_features(frequency_sequence, calibration)
        coverage_pct = _coverage_pct_from_ratio(contact_area_ratio)
        row = {
            "id": record.get("id"),
            "material": record.get("material"),
            "coverage_pct": coverage_pct,
            "thickness_mm": thickness_mm,
            "f1_ch1_abs_delta_pct": parse_float(feature_map.get("f1_ch1_abs_delta_pct")),
            "f1_ch2_abs_delta_pct": parse_float(feature_map.get("f1_ch2_abs_delta_pct")),
            "f3_ch1_abs_delta_pct": parse_float(feature_map.get("f3_ch1_abs_delta_pct")),
            "f3_ch2_abs_delta_pct": parse_float(feature_map.get("f3_ch2_abs_delta_pct")),
        }
        rows.append(row)
    return rows


def build_brass_surface_model(teaching_records: list[dict], calibration: dict) -> dict:
    training_rows = brass_training_feature_rows(teaching_records, calibration)
    return {
        "model_name": "brass_rejection_ch1f1_ch2f1_v1",
        "training_rows": training_rows,
        "coverage_range": list(CH2_F1_F3_COVERAGE_RANGE),
        "thickness_range": list(CH2_F1_F3_THICKNESS_RANGE),
        "surfaces": {
            "ch1f1": _fit_surface_bundle(training_rows, "f1_ch1_abs_delta_pct", CH1_F1_RULE_PARAMS),
            "ch2f1": _fit_surface_bundle(training_rows, "f1_ch2_abs_delta_pct", CH2_F1_PARAMS),
            "ch1f3": _fit_surface_bundle(training_rows, "f3_ch1_abs_delta_pct", CH1_F3_RULE_PARAMS),
            "ch2f3": _fit_surface_bundle(training_rows, "f3_ch2_abs_delta_pct", CH2_F3_PARAMS),
        },
    }


def _predict_surface_bundle(bundle: dict, coverage_pct: float, thickness_mm: float) -> float:
    params = bundle["params"]
    return brass_surface(coverage_pct, thickness_mm, params.rmin, params.rspan, params.k, params.alpha, params.d)


def validation_rule_bundle(
    coverage_pct: float | None,
    thickness_mm: float | None,
    flat_features: dict,
    brass_model: dict,
) -> dict:
    if coverage_pct is None or thickness_mm is None or coverage_pct <= 0 or thickness_mm <= 0:
        return {
            "error": "Missing valid geometry for rule validation",
            "brass_rejection_ch1f1_ch2f1": None,
        }

    f1_ch1_abs = parse_float(flat_features.get("f1_ch1_abs_delta_pct"))
    f1_ch2_abs = parse_float(flat_features.get("f1_ch2_abs_delta_pct"))
    f3_ch1_abs = parse_float(flat_features.get("f3_ch1_abs_delta_pct"))
    f3_ch2_abs = parse_float(flat_features.get("f3_ch2_abs_delta_pct"))
    required = {
        "f1_ch1_abs_delta_pct": f1_ch1_abs,
        "f1_ch2_abs_delta_pct": f1_ch2_abs,
        "f3_ch1_abs_delta_pct": f3_ch1_abs,
        "f3_ch2_abs_delta_pct": f3_ch2_abs,
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        return {
            "error": f"Missing validation features: {', '.join(missing)}",
            "brass_rejection_ch1f1_ch2f1": None,
        }

    surfaces = brass_model["surfaces"]
    pred_ch1f1 = _predict_surface_bundle(surfaces["ch1f1"], coverage_pct, thickness_mm)
    pred_ch2f1 = _predict_surface_bundle(surfaces["ch2f1"], coverage_pct, thickness_mm)
    pred_ch1f3 = _predict_surface_bundle(surfaces["ch1f3"], coverage_pct, thickness_mm)
    pred_ch2f3 = _predict_surface_bundle(surfaces["ch2f3"], coverage_pct, thickness_mm)

    residual_ch1f1 = f1_ch1_abs - pred_ch1f1
    residual_ch2f1 = f1_ch2_abs - pred_ch2f1
    residual_ch1f3 = f3_ch1_abs - pred_ch1f3
    residual_ch2f3 = f3_ch2_abs - pred_ch2f3

    z_ch1f1 = abs(residual_ch1f1) / surfaces["ch1f1"]["params"].rmse
    z_ch2f1 = abs(residual_ch2f1) / surfaces["ch2f1"]["params"].rmse
    z_ch1f3 = abs(residual_ch1f3) / surfaces["ch1f3"]["params"].rmse
    z_ch2f3 = abs(residual_ch2f3) / surfaces["ch2f3"]["params"].rmse

    mu_ch1f1 = _fuzzy_primary_membership(z_ch1f1)
    mu_ch2f1 = _fuzzy_primary_membership(z_ch2f1)
    mu_brass = mu_ch1f1 * mu_ch2f1
    label, confidence = _mu_label(mu_brass)
    within_range = (
        brass_model["coverage_range"][0] <= coverage_pct <= brass_model["coverage_range"][1]
        and brass_model["thickness_range"][0] <= thickness_mm <= brass_model["thickness_range"][1]
    )
    warning = None if within_range else "Input is outside calibrated geometry range. Prediction is extrapolated."

    result = {
        "model_name": brass_model["model_name"],
        "label": label,
        "confidence": confidence,
        "mu_brass": rounded_or_none(mu_brass, 6),
        "within_calibrated_range": within_range,
        "warning": warning,
        "measured_ch1f1": rounded_or_none(f1_ch1_abs, 6),
        "predicted_ch1f1": rounded_or_none(pred_ch1f1, 6),
        "residual_ch1f1": rounded_or_none(residual_ch1f1, 6),
        "z_ch1f1": rounded_or_none(z_ch1f1, 6),
        "mu_ch1f1": rounded_or_none(mu_ch1f1, 6),
        "residual_direction_ch1f1": _residual_direction(residual_ch1f1),
        "measured_ch2f1": rounded_or_none(f1_ch2_abs, 6),
        "predicted_ch2f1": rounded_or_none(pred_ch2f1, 6),
        "residual_ch2f1": rounded_or_none(residual_ch2f1, 6),
        "z_ch2f1": rounded_or_none(z_ch2f1, 6),
        "mu_ch2f1": rounded_or_none(mu_ch2f1, 6),
        "residual_direction_ch2f1": _residual_direction(residual_ch2f1),
        "measured_ch1f3": rounded_or_none(f3_ch1_abs, 6),
        "predicted_ch1f3": rounded_or_none(pred_ch1f3, 6),
        "residual_ch1f3": rounded_or_none(residual_ch1f3, 6),
        "z_ch1f3": rounded_or_none(z_ch1f3, 6),
        "residual_direction_ch1f3": _residual_direction(residual_ch1f3),
        "measured_ch2f3": rounded_or_none(f3_ch2_abs, 6),
        "predicted_ch2f3": rounded_or_none(pred_ch2f3, 6),
        "residual_ch2f3": rounded_or_none(residual_ch2f3, 6),
        "z_ch2f3": rounded_or_none(z_ch2f3, 6),
        "residual_direction_ch2f3": _residual_direction(residual_ch2f3),
        "gain_f1": flat_features.get("gain_f1"),
        "gain_f3": flat_features.get("gain_f3"),
        "voltage_freq_ratio": flat_features.get("voltage_freq_ratio"),
        "current_freq_ratio": flat_features.get("current_freq_ratio"),
        "surface_model": {
            key: {
                "params": asdict(bundle["params"]),
                "source": bundle["source"],
                "training_count": bundle["training_count"],
                "feature_key": bundle["feature_key"],
            }
            for key, bundle in surfaces.items()
        },
    }
    return {
        "error": None,
        "brass_rejection_ch1f1_ch2f1": result,
    }


def write_csv_file(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def validation_feature_report_rows(records: list[dict]) -> list[dict]:
    rows = []
    for record in records:
        feature_map = record.get("validation_features") if isinstance(record.get("validation_features"), dict) else {}
        rows.append(
            {
                "id": record.get("id"),
                "sample_id": record.get("sample_id"),
                "repeat_index": record.get("repeat_index"),
                "date": record.get("date"),
                "time": record.get("time"),
                "material": record.get("material"),
                "shape": record.get("shape"),
                "weight_g": record.get("weight_g"),
                "width_mm": record.get("width_mm"),
                "length_mm": record.get("length_mm"),
                "thickness_mm": record.get("thickness_mm"),
                "sample_area_mm2": record.get("sample_area_mm2"),
                "coil_area_mm2": record.get("coil_area_mm2"),
                "contact_area_ratio": record.get("contact_area_ratio"),
                "calibration_used": record.get("calibration_used"),
                "f1_ch1_delta_pct": feature_map.get("f1_ch1_delta_pct"),
                "f1_ch1_abs_delta_pct": feature_map.get("f1_ch1_abs_delta_pct"),
                "f1_ch2_delta_pct": feature_map.get("f1_ch2_delta_pct"),
                "f1_ch2_abs_delta_pct": feature_map.get("f1_ch2_abs_delta_pct"),
                "f3_ch1_delta_pct": feature_map.get("f3_ch1_delta_pct"),
                "f3_ch1_abs_delta_pct": feature_map.get("f3_ch1_abs_delta_pct"),
                "f3_ch2_delta_pct": feature_map.get("f3_ch2_delta_pct"),
                "f3_ch2_abs_delta_pct": feature_map.get("f3_ch2_abs_delta_pct"),
                "gain_f1": feature_map.get("gain_f1"),
                "gain_f3": feature_map.get("gain_f3"),
                "voltage_freq_ratio": feature_map.get("voltage_freq_ratio"),
                "current_freq_ratio": feature_map.get("current_freq_ratio"),
            }
        )
    return rows


def validation_result_rows(records: list[dict]) -> list[dict]:
    rows = []
    for record in records:
        result = record.get("rule_models", {}).get("brass_rejection_ch1f1_ch2f1")
        if not isinstance(result, dict):
            continue
        rows.append(
            {
                "id": record.get("id"),
                "sample_id": record.get("sample_id"),
                "repeat_index": record.get("repeat_index"),
                "date": record.get("date"),
                "time": record.get("time"),
                "material": record.get("material"),
                "shape": record.get("shape"),
                "weight_g": record.get("weight_g"),
                "width_mm": record.get("width_mm"),
                "length_mm": record.get("length_mm"),
                "thickness_mm": record.get("thickness_mm"),
                "contact_area_ratio": record.get("contact_area_ratio"),
                "model_name": result.get("model_name"),
                "label": result.get("label"),
                "confidence": result.get("confidence"),
                "mu_brass": result.get("mu_brass"),
                "within_calibrated_range": result.get("within_calibrated_range"),
                "warning": result.get("warning"),
                "measured_ch1f1": result.get("measured_ch1f1"),
                "predicted_ch1f1": result.get("predicted_ch1f1"),
                "residual_ch1f1": result.get("residual_ch1f1"),
                "z_ch1f1": result.get("z_ch1f1"),
                "mu_ch1f1": result.get("mu_ch1f1"),
                "measured_ch2f1": result.get("measured_ch2f1"),
                "predicted_ch2f1": result.get("predicted_ch2f1"),
                "residual_ch2f1": result.get("residual_ch2f1"),
                "z_ch2f1": result.get("z_ch2f1"),
                "mu_ch2f1": result.get("mu_ch2f1"),
                "measured_ch1f3": result.get("measured_ch1f3"),
                "predicted_ch1f3": result.get("predicted_ch1f3"),
                "residual_ch1f3": result.get("residual_ch1f3"),
                "z_ch1f3": result.get("z_ch1f3"),
                "measured_ch2f3": result.get("measured_ch2f3"),
                "predicted_ch2f3": result.get("predicted_ch2f3"),
                "residual_ch2f3": result.get("residual_ch2f3"),
                "z_ch2f3": result.get("z_ch2f3"),
                "gain_f1": result.get("gain_f1"),
                "gain_f3": result.get("gain_f3"),
                "voltage_freq_ratio": result.get("voltage_freq_ratio"),
                "current_freq_ratio": result.get("current_freq_ratio"),
            }
        )
    return rows


def validation_group_summary_rows(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        key = (
            record.get("material"),
            record.get("width_mm"),
            record.get("length_mm"),
            record.get("thickness_mm"),
        )
        groups.setdefault(key, []).append(record)

    rows = []
    for (material, width_mm, length_mm, thickness_mm), items in groups.items():
        feature_maps = [item.get("validation_features") if isinstance(item.get("validation_features"), dict) else {} for item in items]
        results = [
            item.get("rule_models", {}).get("brass_rejection_ch1f1_ch2f1")
            for item in items
            if isinstance(item.get("rule_models", {}).get("brass_rejection_ch1f1_ch2f1"), dict)
        ]
        labels = [result.get("label") for result in results if result.get("label")]
        label_counts = Counter(labels)
        if not label_counts:
            group_label = "no_result"
        else:
            top_two = label_counts.most_common(2)
            group_label = "mixed" if len(top_two) > 1 and top_two[0][1] == top_two[1][1] else top_two[0][0]

        def collect_numeric(source_list: list[dict], key: str) -> list[float]:
            values = []
            for source in source_list:
                value = parse_float(source.get(key))
                if value is not None:
                    values.append(value)
            return values

        row = {
            "material": material,
            "width_mm": width_mm,
            "length_mm": length_mm,
            "thickness_mm": thickness_mm,
            "repeat_count": len(items),
            "group_label": group_label,
            "label_counts": ", ".join(f"{label}:{count}" for label, count in label_counts.items()),
        }
        for key in [
            "f1_ch1_abs_delta_pct",
            "f1_ch2_abs_delta_pct",
            "f3_ch1_abs_delta_pct",
            "f3_ch2_abs_delta_pct",
        ]:
            mean_value, std_value = mean_and_sample_std(collect_numeric(feature_maps, key))
            row[f"{key}_mean"] = rounded_or_none(mean_value, 6)
            row[f"{key}_std"] = rounded_or_none(std_value, 6)
        for key in ["z_ch1f1", "z_ch2f1", "z_ch1f3", "z_ch2f3"]:
            mean_value, std_value = mean_and_sample_std(collect_numeric(results, key))
            row[f"{key}_mean"] = rounded_or_none(mean_value, 6)
            row[f"{key}_std"] = rounded_or_none(std_value, 6)
        rows.append(row)
    return rows


def generate_validation_reports(records: list[dict], brass_model: dict) -> dict:
    VALIDATION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    feature_rows = validation_feature_report_rows(records)
    result_rows = validation_result_rows(records)
    group_rows = validation_group_summary_rows(records)

    write_csv_file(
        VALIDATION_REPORTS_DIR / "validation_features.csv",
        feature_rows,
        [
            "id", "sample_id", "repeat_index", "date", "time", "material", "shape", "weight_g",
            "width_mm", "length_mm", "thickness_mm", "sample_area_mm2", "coil_area_mm2",
            "contact_area_ratio", "calibration_used", "f1_ch1_delta_pct", "f1_ch1_abs_delta_pct",
            "f1_ch2_delta_pct", "f1_ch2_abs_delta_pct", "f3_ch1_delta_pct", "f3_ch1_abs_delta_pct",
            "f3_ch2_delta_pct", "f3_ch2_abs_delta_pct", "gain_f1", "gain_f3",
            "voltage_freq_ratio", "current_freq_ratio",
        ],
    )
    write_csv_file(
        VALIDATION_REPORTS_DIR / "validation_brass_rejection_ch1f1_ch2f1.csv",
        result_rows,
        [
            "id", "sample_id", "repeat_index", "date", "time", "material", "shape", "weight_g",
            "width_mm", "length_mm", "thickness_mm", "contact_area_ratio", "model_name", "label",
            "confidence", "mu_brass", "within_calibrated_range", "warning",
            "measured_ch1f1", "predicted_ch1f1", "residual_ch1f1", "z_ch1f1", "mu_ch1f1",
            "measured_ch2f1", "predicted_ch2f1", "residual_ch2f1", "z_ch2f1", "mu_ch2f1",
            "measured_ch1f3", "predicted_ch1f3", "residual_ch1f3", "z_ch1f3",
            "measured_ch2f3", "predicted_ch2f3", "residual_ch2f3", "z_ch2f3",
            "gain_f1", "gain_f3", "voltage_freq_ratio", "current_freq_ratio",
        ],
    )
    write_csv_file(
        VALIDATION_REPORTS_DIR / "validation_group_summary.csv",
        group_rows,
        [
            "material", "width_mm", "length_mm", "thickness_mm", "repeat_count", "group_label", "label_counts",
            "f1_ch1_abs_delta_pct_mean", "f1_ch1_abs_delta_pct_std",
            "f1_ch2_abs_delta_pct_mean", "f1_ch2_abs_delta_pct_std",
            "f3_ch1_abs_delta_pct_mean", "f3_ch1_abs_delta_pct_std",
            "f3_ch2_abs_delta_pct_mean", "f3_ch2_abs_delta_pct_std",
            "z_ch1f1_mean", "z_ch1f1_std", "z_ch2f1_mean", "z_ch2f1_std",
            "z_ch1f3_mean", "z_ch1f3_std", "z_ch2f3_mean", "z_ch2f3_std",
        ],
    )

    summary_lines = [
        "# Validation Model Summary",
        "",
        f"- Generated at: {datetime.now().strftime('%d %b %Y %H:%M:%S')}",
        f"- Validation records: {len(records)}",
        f"- Feature rows: {len(feature_rows)}",
        f"- Brass rejection rows: {len(result_rows)}",
        f"- Group summary rows: {len(group_rows)}",
        f"- Brass teaching rows used for fitting: {len(brass_model.get('training_rows', []))}",
        "",
        "## Surface Fits",
    ]
    for key, bundle in brass_model["surfaces"].items():
        summary_lines.extend(
            [
                f"### {key}",
                f"- source: {bundle['source']}",
                f"- training_count: {bundle['training_count']}",
                f"- params: `{json.dumps(asdict(bundle['params']))}`",
                "",
            ]
        )
    summary_lines.append("## Validation Label Counts")
    label_counts = Counter(row.get("label") for row in result_rows if row.get("label"))
    for label in ("brass", "brass_like_uncertain", "not_brass"):
        summary_lines.append(f"- {label}: {label_counts.get(label, 0)}")
    (VALIDATION_REPORTS_DIR / "validation_model_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "directory": str(VALIDATION_REPORTS_DIR),
        "features_csv": str(VALIDATION_REPORTS_DIR / "validation_features.csv"),
        "rejection_csv": str(VALIDATION_REPORTS_DIR / "validation_brass_rejection_ch1f1_ch2f1.csv"),
        "group_csv": str(VALIDATION_REPORTS_DIR / "validation_group_summary.csv"),
        "summary_md": str(VALIDATION_REPORTS_DIR / "validation_model_summary.md"),
    }


def verification_frequency_commands_for_classifier() -> list[str]:
    if selected_classifier_algorithm() == "binary_brass_ch2_f1_f3":
        return ["f1", "f3"]
    if selected_classifier_algorithm() == "binary_brass_ch1_f1":
        return ["f1"]
    return ["f1", "f2", "f3"]


def latest_daq_sensor_state() -> dict:
    settings = load_settings()
    active_slot = settings.get("active_frequency_slot", 1)
    frequencies = settings.get("multi_frequencies_khz", [10.0, 20.0, 30.0])
    frequency_hz = frequencies[active_slot - 1] if 1 <= active_slot <= len(frequencies) else None
    command = f"f{active_slot}"
    with DAQ_LOCK:
        collection = collect_live_rms_burst(
            frequency_command=command,
            sample_count=10,
            ports=["/dev/ttyACM0"],
        )
    apply_daq_correction_to_collection(collection)
    if not collection.channels.get("ch1") or not collection.channels.get("ch2"):
        return {
            "ch1": {**LATEST_SENSOR_STATE["ch1"], "valid": False, "error": "CH1 serial data unavailable"},
            "ch2": {**LATEST_SENSOR_STATE["ch2"], "valid": False, "error": "CH2 serial data unavailable"},
            "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
            "status": "error",
            "acquisition_mode": "daq",
            "frequency_slot": active_slot,
            "frequency_hz": frequency_hz,
            "frequency_command": command,
            "errors": collection.errors[-10:],
        }

    ch1 = summarize_channel(collection.channels["ch1"], "V")
    ch2 = summarize_channel(collection.channels["ch2"], "V")
    return {
        "ch1": {
            "device": ch1["last_device"],
            "rms": ch1["mean"],
            "rms_raw": raw_rms_mean_from_packets(collection.channels["ch1"]),
            "std": ch1["std"],
            "quality": 1.0,
            "unit": ch1["unit"].replace(" RMS", ""),
            "source": "serial",
            "valid": True,
            "error": "",
        },
        "ch2": {
            "device": ch2["last_device"],
            "rms": ch2["mean"],
            "rms_raw": raw_rms_mean_from_packets(collection.channels["ch2"]),
            "std": ch2["std"],
            "quality": 1.0,
            "unit": ch2["unit"].replace(" RMS", ""),
            "source": "serial",
            "valid": True,
            "error": "",
        },
        "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        "status": "online",
        "acquisition_mode": "daq",
        "frequency_slot": active_slot,
        "frequency_hz": frequency_hz,
        "frequency_command": command,
        "daq_correction": daq_correction_metadata(),
        "errors": collection.errors[-10:],
    }


def normalize_channel(payload: dict, previous: dict, default_unit: str) -> dict:
    data = payload if isinstance(payload, dict) else {}
    return {
        "device": data.get("device", previous.get("device", "")),
        "rms": float(data.get("rms", previous.get("rms", 0.0))),
        "std": float(data.get("std", previous.get("std", 0.0))),
        "quality": float(data.get("quality", previous.get("quality", 0.0))),
        "unit": data.get("unit", previous.get("unit", default_unit)),
        "source": data.get("source", previous.get("source", "unknown")),
        "valid": bool(data.get("valid", previous.get("valid", False))),
        "error": data.get("error", ""),
    }


load_daq_offset_settings()


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename: str):
    allowed = {
        "styles.css",
        "app.js",
        "measurements.json",
        "calibration.json",
        "teaching_library.json",
        "settings.json",
        "daq_offset.json",
    }
    if filename.startswith("assets/"):
        return send_from_directory(BASE_DIR, filename)
    if filename not in allowed:
        abort(404)
    return send_from_directory(BASE_DIR, filename)


@app.get("/api/history")
def get_history():
    return jsonify(load_measurements())


@app.get("/api/history/<record_id>")
def get_history_record(record_id: str):
    for record in load_measurements():
        if record.get("id") == record_id:
            return jsonify(record)
    abort(404)


@app.post("/api/history")
def add_history_record():
    payload = request.get_json(silent=True) or {}
    records = load_measurements()
    now = datetime.now()
    record = {
        "id": payload.get("id") or f"M-{now.strftime('%H%M%S')}",
        "date": payload.get("date") or now.strftime("%d %b %Y"),
        "time": payload.get("time") or now.strftime("%H:%M"),
        "result": payload.get("result", "Unknown"),
        "weight": payload.get("weight", "0 g"),
        "shape": payload.get("shape", "Other"),
        "confidence": payload.get("confidence", "0%"),
        "status": payload.get("status", "Saved by Flask demo"),
    }
    records.insert(0, record)
    save_measurements(records)
    return jsonify(record), 201


@app.post("/api/history/<record_id>/delete")
def delete_history_record(record_id: str):
    payload = request.get_json(silent=True) or {}
    if payload.get("pin") != ADMIN_PIN:
        return jsonify({"error": "invalid_pin"}), 403

    records = load_measurements()
    next_records = [record for record in records if record.get("id") != record_id]
    if len(next_records) == len(records):
        abort(404)

    save_measurements(next_records)
    return jsonify({"deleted": record_id})


@app.post("/api/measurement/verify")
def verify_measurement():
    payload = request.get_json(silent=True) or {}
    now = datetime.now()
    weight_grams = parse_float(payload.get("weight"), 0.0) or 0.0
    width_mm = parse_float(payload.get("width_mm"), 0.0) or 0.0
    length_mm = parse_float(payload.get("length_mm"), 0.0) or 0.0
    thickness_mm = parse_float(payload.get("thickness_mm"), 0.0) or 0.0
    shape = payload.get("shape", "Other")
    frequency_hz = parse_float(payload.get("frequency_hz"))
    frequency_slot = payload.get("frequency_slot")
    calibration = load_calibration()
    teaching_records = load_teaching_records()
    geometry = build_geometry(width_mm, length_mm, thickness_mm, shape)

    collection = collect_verification_summaries(
        duration_seconds=5,
        target_sample_count=10,
        frequency_commands=verification_frequency_commands_for_classifier(),
    )
    if not collection["ok"]:
        return (
            jsonify(
                {
                    "error": "measurement_failed",
                    "message": "Unable to collect valid CH1 teaching readings",
                    "acquisition_mode": collection["mode"],
                    "details": collection["errors"],
                }
            ),
            503,
        )

    ch1 = collection["ch1"]
    ch2 = collection["ch2"]
    features = build_measurement_features(ch1, ch2, calibration, weight_grams, shape, geometry=geometry)
    frequency_features = validation_frequency_features(collection.get("frequency_sequence", []), calibration)
    features.update(frequency_features)
    use_surface_classifier = selected_classifier_algorithm() in {"binary_brass_ch1_f1", "binary_brass_ch2_f1_f3", "two_pass_frequency_rf"}
    if use_surface_classifier:
        matches, classification_method = [], CLASSIFIER_ALGORITHMS[selected_classifier_algorithm()]["method"]
    else:
        matches, classification_method = reference_matches(features, teaching_records)
    classifier_prediction, classifier_meta = classifier_prediction_for_collection(
        collection,
        calibration,
        weight_grams,
        geometry["thickness_mm"],
        geometry["contact_area_ratio"],
        shape,
    )
    top_matches = [
        {
            "rank": index + 1,
            "id": item.get("id"),
            "material": display_match_label(item),
            "shape": item.get("shape"),
            "weight": item.get("weight"),
            "match_score": item.get("match_score"),
        }
        for index, item in enumerate(matches[:3])
    ]
    top_matches = sorted(top_matches, key=lambda item: float(item.get("match_score", 999999.0)))
    for index, item in enumerate(top_matches, start=1):
        item["rank"] = index
    match = matches[0] if matches else None
    second = matches[1] if len(matches) > 1 else None
    confidence_label, nearest_gap = knn_confidence(
        match.get("match_score") if match else 0.0,
        second.get("match_score") if second else None,
    )
    confidence_pct = confidence_from_top_matches(matches)
    score_threshold_pct = load_settings().get("confidence_threshold_pct", 40.0)

    if top_matches:
        add_match_percentages(top_matches, "match_score")

    classifier_missing_features = (
        classifier_prediction is None
        and isinstance(classifier_meta, dict)
        and "Missing features" in str(classifier_meta.get("message", ""))
    )
    classifier_model_error = (
        classifier_prediction is None
        and isinstance(classifier_meta, dict)
        and is_classifier_model_error(classifier_meta.get("message"))
    )

    if classifier_prediction:
        classification_method = classifier_prediction["classification_method"]
        result = classifier_prediction["prediction"]
        confidence_pct = classifier_prediction["confidence"]
        nearest_gap = classifier_prediction["nearest_gap"]
        confidence_label = "HIGH" if confidence_pct >= 95 else ("MEDIUM" if confidence_pct >= 75 else "LOW")
        top_matches = classifier_prediction["top_matches"]
        match = {
            "id": None,
            "match_score": classifier_prediction["distance"],
        }
    elif classifier_missing_features:
        classification_method = "multi-frequency classifier unavailable"
        result = "Non Gold"
        confidence_pct = 0.0
        confidence_label = "LOW"
        nearest_gap = 0.0
        top_matches = []
        match = None
    elif classifier_model_error:
        classification_method = "model_load_error"
        result = "Unable to Detect Material"
        confidence_pct = 0.0
        confidence_label = "LOW"
        nearest_gap = 0.0
        top_matches = []
        match = None

    needs_verify = match is None or confidence_pct < score_threshold_pct
    if classifier_prediction:
        needs_verify = needs_verify or not classifier_prediction.get("accepted") or classifier_prediction.get("uncertain")
    result = result if (classifier_prediction or classifier_missing_features or classifier_model_error) else (display_match_label(match) if match else "Unable to Detect Material")
    if not classifier_prediction and not classifier_missing_features and not classifier_model_error and confidence_pct <= 0.01:
        result = "Non Gold"
        needs_verify = True

    if not top_matches:
        if classifier_missing_features:
            status_text = "Multi-frequency classifier data missing. Check DAQ mode and frequency sampling. Confidence 0.00%."
        elif classifier_model_error:
            status_text = "Error Loading Model"
        else:
            status_text = f"No reference matches found. Confidence {confidence_pct:.2f}%."
    else:
        top_text = " | ".join(
            f"{item['rank']} {item['material']} {float(item.get('match_percent', 0.0)):.2f}%"
            for item in top_matches
        )
        status_text = f"Match confidence {confidence_pct:.2f}%. Top 3: {top_text}"
    if needs_verify:
        status_text = f"{status_text} Kindly verify the sample."

    record = {
        "id": payload.get("id") or f"M-{now.strftime('%H%M%S')}",
        "date": payload.get("date") or now.strftime("%d %b %Y"),
        "time": payload.get("time") or now.strftime("%H:%M"),
        "result": result,
        "weight": f"{weight_grams:g} g",
        "shape": shape,
        "width_mm": geometry["width_mm"],
        "length_mm": geometry["length_mm"],
        "thickness_mm": geometry["thickness_mm"],
        "sample_area_mm2": geometry["sample_area_mm2"],
        "coil_area_mm2": geometry["coil_area_mm2"],
        "contact_area_ratio": geometry["contact_area_ratio"],
        "frequency_hz": round(frequency_hz, 3) if frequency_hz is not None else None,
        "frequency_slot": frequency_slot,
        "vision_measurement": payload.get("vision_measurement"),
        "status": status_text,
        "ch1_rms": format_measurement(ch1),
        "ch2_rms": format_measurement(ch2),
        "raw_measurement": collection.get("raw_measurement", {}),
        "ch1_std": format_std(ch1),
        "ch2_std": format_std(ch2),
        "ch1_delta": features.get("delta_ch1"),
        "ch2_delta": features.get("delta_ch2"),
        "ch1_delta_pct": features.get("delta_ch1_pct"),
        "ch2_delta_pct": features.get("delta_ch2_pct"),
        "f1_ch1_delta_pct": features.get("f1_ch1_delta_pct"),
        "f1_ch2_delta_pct": features.get("f1_ch2_delta_pct"),
        "f2_ch1_delta_pct": features.get("f2_ch1_delta_pct"),
        "f2_ch2_delta_pct": features.get("f2_ch2_delta_pct"),
        "f3_ch1_delta_pct": features.get("f3_ch1_delta_pct"),
        "f3_ch2_delta_pct": features.get("f3_ch2_delta_pct"),
        "ratio": f"{(features.get('raw_ratio') or 0):.6f}",
        "matched_record_id": match.get("id") if match else None,
        "match_score": match.get("match_score") if match else None,
        "top_matches": top_matches,
        "classifier_result": classifier_prediction,
        "classifier_status": classifier_meta,
        "classifier_features": classifier_meta.get("features") if classifier_meta else None,
        "confidence": f"{confidence_pct:.2f}%",
        "confidence_label": confidence_label,
        "nearest_gap": round(nearest_gap, 6),
        "acquisition_mode": collection["mode"],
        "daq_correction": collection.get("daq_correction", daq_correction_metadata()),
        "frequency_sequence": collection.get("frequency_sequence", []),
        "calibration_used": calibration.get("calibrated_at", "No calibration record"),
        "features_used": features,
        "feature_version": 3 if classifier_prediction else 2,
        "classification_method": classification_method,
        "confidence_threshold_pct": score_threshold_pct,
        "needs_verification": needs_verify,
        "model_version": classifier_prediction.get("model_version") if classifier_prediction else None,
        "gold_prediction": classifier_prediction.get("gold_prediction") if classifier_prediction else None,
        "purity_prediction": classifier_prediction.get("purity_prediction") if classifier_prediction else None,
        "feature_names": classifier_prediction.get("feature_names") if classifier_prediction else None,
        "feature_vector": classifier_prediction.get("feature_vector") if classifier_prediction else None,
        "measured_frequency_values": classifier_prediction.get("measured_frequency_values") if classifier_prediction else None,
        "calibration_frequency_air": classifier_prediction.get("calibration_frequency_air") if classifier_prediction else None,
    }

    records = load_measurements()
    records.insert(0, record)
    save_measurements(records)
    return jsonify(record), 201


@app.get("/api/calibration")
def get_calibration():
    return jsonify(load_calibration())


@app.post("/api/calibration/start")
def start_calibration():
    now = datetime.now()
    payload = request.get_json(silent=True) or {}
    frequency_hz = parse_float(payload.get("frequency_hz"))
    frequency_slot = payload.get("frequency_slot")
    collection = collect_channel_summaries(duration_seconds=10)
    if not collection["ok"]:
        return (
            jsonify(
                {
                    "error": "calibration_failed",
                    "message": "Unable to collect valid CH1 and CH2 air readings",
                    "acquisition_mode": collection["mode"],
                    "details": collection["errors"],
                }
            ),
            503,
        )

    ch1 = collection["ch1"]
    ch2 = collection["ch2"]
    frequency_sequence = collection.get("frequency_sequence", [])
    record = {
        "calibrated_at": now.strftime("%d %b %Y %H:%M"),
        "sample_count": ch1.get("sample_count", 0),
        "samples_per_frequency": 30,
        "duration_seconds": 48,
        "condition": "No material / air reading",
        "acquisition_mode": collection["mode"],
        "frequency_hz": round(frequency_hz, 3) if frequency_hz is not None else None,
        "frequency_slot": frequency_slot,
        "frequency_sequence": frequency_sequence,
        "frequency_air": build_frequency_air_record(frequency_sequence),
        "ch1": ch1,
        "ch2": ch2,
        "raw_measurement": collection.get("raw_measurement", {}),
        "daq_correction": collection.get("daq_correction", daq_correction_metadata()),
        "errors": collection["errors"],
    }
    save_calibration(record)
    return jsonify(record), 201


@app.post("/api/calibration/validate")
def validate_calibration():
    payload = request.get_json(silent=True) or {}
    frequency_hz = parse_float(payload.get("frequency_hz"))
    frequency_slot = payload.get("frequency_slot")
    calibration = load_calibration()
    if not calibration:
        return (
            jsonify(
                {
                    "error": "no_calibration_record",
                    "message": "No calibration record found. Please run calibration first.",
                }
            ),
            400,
        )

    base_ch1 = parse_float(calibration.get("ch1", {}).get("mean"))
    base_ch2 = parse_float(calibration.get("ch2", {}).get("mean"))
    if base_ch1 in (None, 0) or base_ch2 in (None, 0):
        return (
            jsonify(
                {
                    "error": "invalid_calibration_record",
                    "message": "Calibration record is incomplete. Please run calibration again.",
                }
            ),
            400,
        )

    collection = collect_channel_summaries(duration_seconds=10)
    if not collection["ok"]:
        return (
            jsonify(
                {
                    "error": "calibration_validation_failed",
                    "message": "Unable to collect valid CH1 and CH2 readings",
                    "acquisition_mode": collection["mode"],
                    "details": collection["errors"],
                }
            ),
            503,
        )

    ch1 = collection["ch1"]
    ch2 = collection["ch2"]
    frequency_sequence = collection.get("frequency_sequence", [])
    new_ch1 = parse_float(ch1.get("mean")) or 0.0
    new_ch2 = parse_float(ch2.get("mean")) or 0.0
    ch1_drift_pct = ((new_ch1 - base_ch1) / base_ch1) * 100
    ch2_drift_pct = ((new_ch2 - base_ch2) / base_ch2) * 100
    max_drift_pct = max(abs(ch1_drift_pct), abs(ch2_drift_pct))
    threshold_pct = 5.0
    drift_exceeded = max_drift_pct > threshold_pct
    validation_status = "Recalibration Required" if drift_exceeded else "Calibration Valid"
    recommendation = (
        "Drift exceeds 5%. Please perform a new calibration."
        if drift_exceeded
        else "Calibration drift is within 5% threshold."
    )

    return jsonify(
        {
            "validated_at": datetime.now().strftime("%d %b %Y %H:%M:%S"),
            "validation_status": validation_status,
            "recommendation": recommendation,
            "threshold_pct": threshold_pct,
            "max_drift_pct": round(max_drift_pct, 3),
            "ch1_drift_pct": round(ch1_drift_pct, 3),
            "ch2_drift_pct": round(ch2_drift_pct, 3),
            "latest_calibrated_at": calibration.get("calibrated_at"),
            "new_air_reading": {
                "ch1_mean": round(new_ch1, 6),
                "ch2_mean": round(new_ch2, 6),
            },
            "new_air_by_frequency": build_frequency_air_record(frequency_sequence),
            "acquisition_mode": collection["mode"],
            "frequency_hz": round(frequency_hz, 3) if frequency_hz is not None else None,
            "frequency_slot": frequency_slot,
            "frequency_sequence": frequency_sequence,
            "raw_measurement": collection.get("raw_measurement", {}),
            "daq_correction": collection.get("daq_correction", daq_correction_metadata()),
        }
    )


@app.get("/api/teaching")
def get_teaching_records():
    return jsonify(load_teaching_records())


@app.post("/api/teaching")
def add_teaching_record():
    payload = request.get_json(silent=True) or {}
    records = load_teaching_records()
    now = datetime.now()
    target_sample_count = 30
    frequency_hz = parse_float(payload.get("frequency_hz"))
    frequency_slot = payload.get("frequency_slot")
    collection = collect_teaching_summaries(duration_seconds=5, target_sample_count=target_sample_count)
    if not collection["ok"]:
        return (
            jsonify(
                {
                    "error": "teaching_failed",
                    "message": "Unable to collect valid CH1 and CH2 readings",
                    "acquisition_mode": collection["mode"],
                    "details": collection["errors"],
                }
            ),
            503,
        )

    calibration = load_calibration()
    ch1 = collection["ch1"]
    ch2 = collection["ch2"]
    ch1_delta = calculate_delta(ch1, calibration, "ch1")
    ch2_delta = calculate_delta(ch2, calibration, "ch2")
    ratio = ch1["mean"] / ch2["mean"] if parse_float(ch2.get("mean")) else 0
    material_label = payload.get("material", "Other")
    material, purity_value = normalize_material_and_purity(material_label)
    shape = payload.get("shape", "Other")
    weight_g = parse_float(payload.get("weight"), 0.0) or 0.0
    width_mm = parse_float(payload.get("width_mm"), 0.0) or 0.0
    length_mm = parse_float(payload.get("length_mm"), 0.0) or 0.0
    thickness_mm = parse_float(payload.get("thickness_mm"), 0.0) or 0.0
    dimension_mode = payload.get("dimension_mode", "standard")
    dimension_labels = payload.get("dimension_labels", {})
    if not isinstance(dimension_labels, dict):
        dimension_labels = {}
    geometry = build_geometry(width_mm, length_mm, thickness_mm, shape)
    delta_ch1 = ch1_delta["mean_delta"] or 0.0
    delta_ch2 = ch2_delta["mean_delta"] or 0.0
    delta_ch1_per_g = (delta_ch1 / weight_g) if weight_g > 0 else None
    delta_ch2_per_g = (delta_ch2 / weight_g) if weight_g > 0 else None
    ch1_std_value = parse_float(ch1.get("std"), 0.0) or 0.0
    ch2_std_value = parse_float(ch2.get("std"))

    calibration_block = {
        "ch1_air": calibration.get("ch1", {}).get("mean"),
        "ch2_air": calibration.get("ch2", {}).get("mean"),
        "calibrated_at": calibration.get("calibrated_at", "No calibration record"),
    }
    measurement_block = {
        "ch1_rms": round(parse_float(ch1.get("mean"), 0.0) or 0.0, 6),
        "ch2_rms": round(parse_float(ch2.get("mean"), 0.0) or 0.0, 6) if parse_float(ch2.get("mean")) is not None else None,
        "ch1_std": round(parse_float(ch1.get("std"), 0.0) or 0.0, 6),
        "ch2_std": round(parse_float(ch2.get("std"), 0.0) or 0.0, 6) if parse_float(ch2.get("std")) is not None else None,
        "sample_count": target_sample_count,
    }
    delta_ratio = (delta_ch1 / delta_ch2) if delta_ch2 not in (None, 0) else None
    features_block = {
        "delta_ch1": round(delta_ch1, 6),
        "delta_ch2": round(delta_ch2, 6),
        "delta_ch1_pct": ch1_delta["mean_delta_pct"],
        "delta_ch2_pct": ch2_delta["mean_delta_pct"],
        "raw_ratio": round(ratio, 6),
        "delta_ratio": round(delta_ratio, 6) if delta_ratio is not None else None,
        "delta_ch1_per_g": round(delta_ch1_per_g, 6) if delta_ch1_per_g is not None else None,
        "delta_ch2_per_g": round(delta_ch2_per_g, 6) if delta_ch2_per_g is not None else None,
        "abs_delta_ch2": round(abs(delta_ch2), 6),
        "noise_ch1": round(ch1_std_value, 6),
        "noise_ch2": round(ch2_std_value, 6) if ch2_std_value is not None else None,
        "sample_area_mm2": geometry["sample_area_mm2"],
        "contact_area_ratio": geometry["contact_area_ratio"],
    }

    record = {
        "id": payload.get("id") or f"T-{now.strftime('%H%M%S')}",
        "date": payload.get("date") or now.strftime("%d %b %Y"),
        "time": payload.get("time") or now.strftime("%H:%M"),
        "material": material_label,
        "purity": payload.get("purity", "Known"),
        "shape": shape,
        "frequency_hz": round(frequency_hz, 3) if frequency_hz is not None else None,
        "frequency_slot": frequency_slot,
        "vision_measurement": payload.get("vision_measurement"),
        "weight": payload.get("weight", "0 g"),
        "material_base": material,
        "purity_value": purity_value,
        "weight_g": round(weight_g, 3),
        "width_mm": geometry["width_mm"],
        "length_mm": geometry["length_mm"],
        "thickness_mm": geometry["thickness_mm"],
        "dimension_mode": dimension_mode,
        "dimension_labels": dimension_labels,
        "sample_area_mm2": geometry["sample_area_mm2"],
        "coil_area_mm2": geometry["coil_area_mm2"],
        "contact_area_ratio": geometry["contact_area_ratio"],
        "calibration": calibration_block,
        "measurement": measurement_block,
        "raw_measurement": collection.get("raw_measurement", {}),
        "features": features_block,
        "feature_version": 2,
        "ch1_rms": format_measurement(ch1),
        "ch2_rms": format_measurement(ch2),
        "ch1_std": f"{(parse_float(ch1.get('std'), 0.0) or 0.0):.6f} {ch1.get('unit', '')}",
        "ch2_std": f"{(parse_float(ch2.get('std'), 0.0) or 0.0):.6f} {ch2.get('unit', '')}" if parse_float(ch2.get("std")) is not None else "--",
        "ch1_delta": ch1_delta["mean_delta"],
        "ch2_delta": ch2_delta["mean_delta"],
        "ch1_delta_pct": ch1_delta["mean_delta_pct"],
        "ch2_delta_pct": ch2_delta["mean_delta_pct"],
        "ratio": f"{ratio:.6f}",
        "ch1_summary": ch1,
        "ch2_summary": ch2,
        "calibration_used": calibration.get("calibrated_at", "No calibration record"),
        "acquisition_mode": collection["mode"],
        "daq_correction": collection.get("daq_correction", daq_correction_metadata()),
        "frequency_sequence": collection.get("frequency_sequence", []),
        "duration_seconds": 48,
        "samples_per_frequency": target_sample_count,
        "sample_count": ch1.get("sample_count", target_sample_count),
        "status": payload.get("status", "Reference sample"),
    }
    records.insert(0, record)
    save_teaching_records(records)
    return jsonify(record), 201


@app.post("/api/teaching/validate")
def validate_teaching_sample():
    payload = request.get_json(silent=True) or {}
    now = datetime.now()
    weight_grams = parse_float(payload.get("weight"), 0.0) or 0.0
    width_mm = parse_float(payload.get("width_mm"), 0.0) or 0.0
    length_mm = parse_float(payload.get("length_mm"), 0.0) or 0.0
    thickness_mm = parse_float(payload.get("thickness_mm"), 0.0) or 0.0
    shape = payload.get("shape", "Other")
    frequency_hz = parse_float(payload.get("frequency_hz"))
    frequency_slot = payload.get("frequency_slot")
    expected_material = payload.get("material", "Unknown")
    calibration = load_calibration()
    teaching_records = load_teaching_records()
    geometry = build_geometry(width_mm, length_mm, thickness_mm, shape)
    coverage_pct = geometry["contact_area_ratio"] * 100.0
    brass_model = build_brass_surface_model(teaching_records, calibration)

    collection = collect_validation_summaries(target_sample_count=30, settle_seconds=5.0)
    if not collection["ok"]:
        return (
            jsonify(
                {
                    "error": "validation_failed",
                    "message": "Unable to collect valid F1 and F3 readings for CH1 and CH2",
                    "acquisition_mode": collection["mode"],
                    "details": collection["errors"],
                }
            ),
            503,
        )

    ch1 = collection["ch1"]
    ch2 = collection["ch2"]
    features = build_measurement_features(ch1, ch2, calibration, weight_grams, shape, geometry=geometry)
    validation_features = validation_frequency_features(collection.get("frequency_sequence", []), calibration)
    features.update(validation_features)
    use_surface_classifier = selected_classifier_algorithm() in {"binary_brass_ch1_f1", "binary_brass_ch2_f1_f3", "two_pass_frequency_rf"}
    if use_surface_classifier:
        matches, classification_method = [], CLASSIFIER_ALGORITHMS[selected_classifier_algorithm()]["method"]
    else:
        matches, classification_method = reference_matches(features, teaching_records)
    classifier_prediction, classifier_meta = classifier_prediction_for_collection(
        collection,
        calibration,
        weight_grams,
        geometry["thickness_mm"],
        geometry["contact_area_ratio"],
        shape,
    )
    rule_models = validation_rule_bundle(coverage_pct, geometry["thickness_mm"], validation_features, brass_model)
    primary_rule = rule_models.get("brass_rejection_ch1f1_ch2f1")
    top_matches = [
        {
            "rank": index + 1,
            "id": item.get("id"),
            "material": display_match_label(item),
            "shape": item.get("shape"),
            "weight": item.get("weight"),
            "match_score": item.get("match_score"),
        }
        for index, item in enumerate(matches[:3])
    ]

    best = matches[0] if matches else None
    second = matches[1] if len(matches) > 1 else None
    confidence_label, nearest_gap = knn_confidence(
        best.get("match_score") if best else 0.0,
        second.get("match_score") if second else None,
    )
    confidence_pct = confidence_from_gap(nearest_gap)

    predicted_material = display_match_label(best) if best else "Unknown"
    comparison_material = predicted_material
    if classifier_prediction:
        classification_method = classifier_prediction["classification_method"]
        predicted_material = classifier_prediction["prediction"]
        comparison_material = classifier_prediction.get("nearest_class") if classifier_prediction.get("accepted") else predicted_material
        confidence_pct = classifier_prediction["confidence"]
        nearest_gap = classifier_prediction["nearest_gap"]
        top_matches = classifier_prediction["top_matches"]
        confidence_label = "HIGH" if confidence_pct >= 95 else ("MEDIUM" if confidence_pct >= 75 else "LOW")
    elif isinstance(classifier_meta, dict) and is_classifier_model_error(classifier_meta.get("message")):
        predicted_material = "Unable to Detect Material"
        comparison_material = predicted_material
        confidence_pct = 0.0
        confidence_label = "LOW"
        nearest_gap = 0.0
        classification_method = "model_load_error"
        top_matches = []

    if primary_rule:
        comparison_material = primary_rule["label"]
        predicted_material = primary_rule["label"]
        confidence_pct = evaluation_percent_from_membership(parse_float(primary_rule.get("mu_brass")))
        confidence_label = str(primary_rule.get("confidence", "low")).upper()
        nearest_gap = rounded_or_none(parse_float(primary_rule.get("mu_brass")), 6) or 0.0
        classification_method = primary_rule["model_name"]
        top_matches = [
            {
                "rank": 1,
                "material": primary_rule["label"],
                "match_percent": confidence_pct,
                "distance": rounded_or_none(1.0 - (parse_float(primary_rule.get("mu_brass"), 0.0) or 0.0), 6),
                "status": primary_rule.get("confidence"),
            }
        ]

    pass_result = rule_pass_fail(expected_material, comparison_material) if primary_rule else (normalize_label_text(comparison_material) == normalize_label_text(expected_material))
    validation_result = "PASS" if pass_result else "FAIL"
    status_text = f"{validation_result} ({confidence_pct}%)"
    if isinstance(classifier_meta, dict) and is_classifier_model_error(classifier_meta.get("message")):
        status_text = "Error Loading Model"

    record = {
            "id": payload.get("id") or f"V-{now.strftime('%H%M%S')}",
            "sample_id": payload.get("sample_id"),
            "repeat_index": payload.get("repeat_index"),
            "date": payload.get("date") or now.strftime("%d %b %Y"),
            "time": payload.get("time") or now.strftime("%H:%M"),
            "material": expected_material,
            "shape": shape,
            "frequency_hz": round(frequency_hz, 3) if frequency_hz is not None else None,
            "frequency_slot": frequency_slot,
            "vision_measurement": payload.get("vision_measurement"),
            "weight": f"{weight_grams:g} g",
            "weight_g": round(weight_grams, 3),
            "width_mm": geometry["width_mm"],
            "length_mm": geometry["length_mm"],
            "thickness_mm": geometry["thickness_mm"],
            "sample_area_mm2": geometry["sample_area_mm2"],
            "coil_area_mm2": geometry["coil_area_mm2"],
            "contact_area_ratio": geometry["contact_area_ratio"],
            "validation_result": validation_result,
            "confidence": f"{confidence_pct}%",
            "confidence_label": confidence_label,
            "nearest_gap": round(nearest_gap, 6),
            "predicted_material": predicted_material,
            "status": status_text,
            "ch1_rms": format_measurement(ch1),
            "ch2_rms": format_measurement(ch2),
            "raw_measurement": collection.get("raw_measurement", {}),
            "ch1_std": format_std(ch1),
            "ch2_std": format_std(ch2),
            "ch1_delta": features.get("delta_ch1"),
            "ch2_delta": features.get("delta_ch2"),
            "ch1_delta_pct": features.get("delta_ch1_pct"),
            "ch2_delta_pct": features.get("delta_ch2_pct"),
            "f1_ch1_delta_pct": validation_features.get("f1_ch1_delta_pct"),
            "f1_ch2_delta_pct": validation_features.get("f1_ch2_delta_pct"),
            "f2_ch1_delta_pct": validation_features.get("f2_ch1_delta_pct"),
            "f2_ch2_delta_pct": validation_features.get("f2_ch2_delta_pct"),
            "f3_ch1_delta_pct": validation_features.get("f3_ch1_delta_pct"),
            "f3_ch2_delta_pct": validation_features.get("f3_ch2_delta_pct"),
            "ratio": f"{(features.get('raw_ratio') or 0):.6f}",
            "matched_record_id": best.get("id") if best else None,
            "match_score": best.get("match_score") if best else None,
            "top_matches": top_matches,
            "classifier_result": classifier_prediction,
            "classifier_status": classifier_meta,
            "classifier_features": classifier_meta.get("features") if classifier_meta else None,
            "validation_features": validation_features,
            "rule_models": {
                "brass_rejection_ch1f1_ch2f1": primary_rule,
                "error": rule_models.get("error"),
            },
            "measured_ch1f1": primary_rule.get("measured_ch1f1") if primary_rule else None,
            "predicted_ch1f1": primary_rule.get("predicted_ch1f1") if primary_rule else None,
            "residual_ch1f1": primary_rule.get("residual_ch1f1") if primary_rule else None,
            "z_ch1f1": primary_rule.get("z_ch1f1") if primary_rule else None,
            "mu_ch1f1": primary_rule.get("mu_ch1f1") if primary_rule else None,
            "measured_ch2f1": primary_rule.get("measured_ch2f1") if primary_rule else None,
            "predicted_ch2f1": primary_rule.get("predicted_ch2f1") if primary_rule else None,
            "residual_ch2f1": primary_rule.get("residual_ch2f1") if primary_rule else None,
            "z_ch2f1": primary_rule.get("z_ch2f1") if primary_rule else None,
            "mu_ch2f1": primary_rule.get("mu_ch2f1") if primary_rule else None,
            "measured_ch1f3": primary_rule.get("measured_ch1f3") if primary_rule else None,
            "predicted_ch1f3": primary_rule.get("predicted_ch1f3") if primary_rule else None,
            "residual_ch1f3": primary_rule.get("residual_ch1f3") if primary_rule else None,
            "z_ch1f3": primary_rule.get("z_ch1f3") if primary_rule else None,
            "measured_ch2f3": primary_rule.get("measured_ch2f3") if primary_rule else None,
            "predicted_ch2f3": primary_rule.get("predicted_ch2f3") if primary_rule else None,
            "residual_ch2f3": primary_rule.get("residual_ch2f3") if primary_rule else None,
            "z_ch2f3": primary_rule.get("z_ch2f3") if primary_rule else None,
            "gain_f1": validation_features.get("gain_f1"),
            "gain_f3": validation_features.get("gain_f3"),
            "voltage_freq_ratio": validation_features.get("voltage_freq_ratio"),
            "current_freq_ratio": validation_features.get("current_freq_ratio"),
            "mu_brass_ch1f1_ch2f1": primary_rule.get("mu_brass") if primary_rule else None,
            "label_ch1f1_ch2f1": primary_rule.get("label") if primary_rule else None,
            "acquisition_mode": collection["mode"],
            "daq_correction": collection.get("daq_correction", daq_correction_metadata()),
            "calibration_used": calibration.get("calibrated_at", "No calibration record"),
            "features_used": features,
            "feature_version": 3 if classifier_prediction else 2,
            "classification_method": classification_method,
            "frequency_sequence": collection.get("frequency_sequence", []),
            "model_version": classifier_prediction.get("model_version") if classifier_prediction else None,
            "gold_prediction": classifier_prediction.get("gold_prediction") if classifier_prediction else None,
            "purity_prediction": classifier_prediction.get("purity_prediction") if classifier_prediction else None,
            "feature_names": classifier_prediction.get("feature_names") if classifier_prediction else None,
            "feature_vector": classifier_prediction.get("feature_vector") if classifier_prediction else None,
            "measured_frequency_values": classifier_prediction.get("measured_frequency_values") if classifier_prediction else None,
            "calibration_frequency_air": classifier_prediction.get("calibration_frequency_air") if classifier_prediction else None,
        }
    validation_records = load_validation_results()
    validation_records.insert(0, record)
    save_validation_results(validation_records)
    reports = generate_validation_reports(validation_records, brass_model)
    record["validation_reports"] = reports
    return jsonify(record)


@app.post("/api/teaching/<record_id>/delete")
def delete_teaching_record(record_id: str):
    payload = request.get_json(silent=True) or {}
    if payload.get("pin") != ADMIN_PIN:
        return jsonify({"error": "invalid_pin"}), 403

    records = load_teaching_records()
    next_records = [record for record in records if record.get("id") != record_id]
    if len(next_records) == len(records):
        abort(404)

    save_teaching_records(next_records)
    return jsonify({"deleted": record_id})


@app.get("/api/classifier/status")
def get_classifier_status():
    return jsonify(classifier_status_payload())


@app.post("/api/classifier/train")
def train_classifier():
    try:
        model = train_selected_classifier()
    except ValueError as exc:
        return jsonify({"error": "classifier_training_failed", "message": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "message": "Classifier model updated",
            "trained_at": model.get("trained_at"),
            "classification_method": model.get("classification_method"),
            "algorithm": model.get("algorithm"),
            "eligible_record_count": model.get("eligible_record_count"),
            "excluded_record_count": model.get("excluded_record_count"),
            "class_counts": model.get("class_counts", {}),
            "feature_keys": model.get("feature_keys", []),
            "model_file": CLASSIFIER_MODEL_FILE.name,
        }
    )


@app.get("/api/validation-results")
def get_validation_results():
    return jsonify(load_validation_results())


@app.get("/api/settings")
def get_settings():
    return jsonify(load_settings())


@app.post("/api/settings")
def update_settings():
    payload = request.get_json(silent=True) or {}
    settings = load_settings()

    if "acquisition_mode" in payload:
        mode = payload.get("acquisition_mode")
        if mode not in {"simulator", "daq"}:
            return jsonify({"error": "invalid_acquisition_mode"}), 400
        settings["acquisition_mode"] = mode

    if "confidence_threshold_pct" in payload:
        threshold = parse_float(payload.get("confidence_threshold_pct"))
        if threshold is None:
            return jsonify({"error": "invalid_confidence_threshold"}), 400
        settings["confidence_threshold_pct"] = max(0.0, min(100.0, threshold))

    if "multi_frequencies_khz" in payload:
        values = payload.get("multi_frequencies_khz")
        if not isinstance(values, list):
            return jsonify({"error": "invalid_multi_frequencies"}), 400
        parsed_multi = []
        for value in values[:3]:
            parsed = parse_float(value)
            if parsed is None or parsed <= 0:
                return jsonify({"error": "invalid_multi_frequencies"}), 400
            parsed_multi.append(round(parsed, 3))
        while len(parsed_multi) < 3:
            parsed_multi.append([10.0, 20.0, 30.0][len(parsed_multi)])
        settings["multi_frequencies_khz"] = parsed_multi

    if "active_frequency_slot" in payload:
        try:
            slot = int(payload.get("active_frequency_slot"))
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_active_frequency_slot"}), 400
        if slot < 1 or slot > 3:
            return jsonify({"error": "invalid_active_frequency_slot"}), 400
        settings["active_frequency_slot"] = slot

    if "classifier_algorithm" in payload:
        algorithm = payload.get("classifier_algorithm")
        if algorithm not in CLASSIFIER_ALGORITHMS:
            return jsonify({"error": "invalid_classifier_algorithm"}), 400
        settings["classifier_algorithm"] = algorithm

    if "service_mode_enabled" in payload:
        settings["service_mode_enabled"] = bool(payload.get("service_mode_enabled"))

    for service_name in ("weight", "vision", "signal"):
        key = f"{service_name}_service_url"
        if key in payload:
            url = str(payload.get(key) or "").strip().rstrip("/")
            if url and not (url.startswith("http://") or url.startswith("https://")):
                return jsonify({"error": f"invalid_{key}"}), 400
            settings[key] = url

    save_settings(settings)
    return jsonify(settings)


@app.post("/api/daq/frequency")
def set_daq_frequency():
    payload = request.get_json(silent=True) or {}
    try:
        slot = int(payload.get("active_frequency_slot"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_active_frequency_slot"}), 400
    if slot < 1 or slot > 3:
        return jsonify({"error": "invalid_active_frequency_slot"}), 400

    settings = load_settings()
    settings["active_frequency_slot"] = slot
    save_settings(settings)

    command = f"f{slot}"
    if settings.get("acquisition_mode") == "simulator":
        return jsonify({
            "ok": True,
            "simulator": True,
            "active_frequency_slot": slot,
            "frequency_hz": settings.get("multi_frequencies_khz", [10.0, 20.0, 30.0])[slot - 1],
            "frequency_command": command,
            "message": "Simulator mode",
        })

    with DAQ_LOCK:
        result = send_frequency_mode(command, ports=["/dev/ttyACM0"])
    status_code = 200 if result.get("ok") else 503
    return jsonify({
        **result,
        "active_frequency_slot": slot,
        "frequency_hz": settings.get("multi_frequencies_khz", [10.0, 20.0, 30.0])[slot - 1],
        "frequency_command": command,
    }), status_code


@app.get("/api/load-cell/latest")
def get_load_cell_latest():
    reading = read_load_cell(stable_only=False, max_attempts=1, retry_seconds=0.0)
    status_code = 200 if reading.get("ok") else 503
    return jsonify(reading), status_code


@app.get("/api/load-cell/average")
def get_load_cell_average():
    try:
        sample_count = int(request.args.get("samples", "10"))
    except (TypeError, ValueError):
        sample_count = 10
    sample_count = max(1, min(30, sample_count))
    if service_mode_enabled():
        try:
            reading = read_weight_service_average(sample_count=sample_count)
            status_code = 200 if reading.get("ok") else 503
            return jsonify(reading), status_code
        except RuntimeError as exc:
            return jsonify(
                {
                    "ok": False,
                    "error": str(exc),
                    "source": "weight_service",
                    "fallback_available": True,
                    "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
                }
            ), 503
    reading = read_load_cell_average(sample_count=sample_count, stable_only=False)
    status_code = 200 if reading.get("ok") else 503
    return jsonify(reading), status_code


@app.post("/api/load-cell/zero")
def zero_load_cell():
    if service_mode_enabled():
        try:
            result = tare_weight_service()
            return jsonify(result), 200 if result.get("ok") else 503
        except RuntimeError as exc:
            return jsonify(
                {
                    "ok": False,
                    "zero_command": "TI",
                    "zero_response": "",
                    "zero_error": str(exc),
                    "message": "Unable to tare load cell",
                    "source": "weight_service",
                    "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
                }
            ), 503
    result = send_load_cell_command(LOAD_CELL_ZERO_COMMAND, wait_seconds=0.1, require_weight=False)
    ok = bool(result.get("ok"))
    status_code = 200 if ok else 503
    return jsonify(
        {
            "ok": ok,
            "zero_command": LOAD_CELL_ZERO_COMMAND,
            "zero_response": result.get("raw_response", ""),
            "zero_error": result.get("error", ""),
            "message": "Tare command sent" if ok else "Unable to tare load cell",
            "port": LOAD_CELL_PORT,
            "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
        }
    ), status_code


@app.get("/api/vision/size")
def get_vision_size():
    shape = request.args.get("shape", "Other")
    try:
        result = read_vision_service_size(shape)
        return jsonify(result), 200 if result.get("ok") else 503
    except RuntimeError as exc:
        return jsonify(
            {
                "ok": False,
                "shape": shape,
                "vision_type": vision_type_for_shape(shape),
                "message": str(exc),
                "source": "vision_service",
                "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
            }
        ), 503


@app.get("/api/vision/image/detected")
def get_vision_detected_image():
    try:
        data, content_type = service_binary_get(service_base_url("vision"), "/image/detected", timeout=10.0)
        return Response(data, mimetype=content_type)
    except RuntimeError as exc:
        return jsonify({"ok": False, "message": str(exc), "source": "vision_service"}), 503


@app.get("/api/sensors/latest")
def get_latest_sensors():
    if acquisition_mode() == "simulator":
        return jsonify(simulated_sensor_state())

    return jsonify(latest_daq_sensor_state())


@app.post("/api/sensors/update")
def update_latest_sensors():
    payload = request.get_json(silent=True) or {}
    now = datetime.now()
    LATEST_SENSOR_STATE["ch1"] = normalize_channel(payload.get("ch1"), LATEST_SENSOR_STATE["ch1"], "A")
    LATEST_SENSOR_STATE["ch2"] = normalize_channel(payload.get("ch2"), LATEST_SENSOR_STATE["ch2"], "V")
    LATEST_SENSOR_STATE["timestamp"] = payload.get("timestamp") or now.strftime("%d %b %Y %H:%M:%S")
    LATEST_SENSOR_STATE["status"] = payload.get("status", "online")
    return jsonify(LATEST_SENSOR_STATE)


@app.get("/api/status")
def status():
    settings = load_settings()
    return jsonify(
        {
            "system": "DanFishel AFiS",
            "mode": "demo",
            "acquisition_mode": settings["acquisition_mode"],
            "measurement_storage": "measurements.json",
            "calibration_storage": "calibration.json",
            "teaching_storage": "teaching_library.json",
            "daq_offset_storage": "daq_offset.json",
            "sensor_api": {
                "latest": "GET /api/sensors/latest",
                "update": "POST /api/sensors/update",
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
