"""YOLO-01: shared, dependency-free configuration schema for Image and View services."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

DEFAULTS = {"enabled": False, "model_path": "vision/coin_bar_seg.pt",
            "detection_confidence": .25, "acceptance_confidence": .80,
            "roi": [0., 0., 1., 1.], "imgsz": 640}


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError("Expected a settings object")
    result = {**DEFAULTS, **{k: values[k] for k in DEFAULTS if k in values}}
    if not isinstance(result["enabled"], bool):
        raise ValueError("Enabled must be true or false")
    path = result["model_path"]
    if not isinstance(path, str) or not path.strip() or len(path) > 1024 or "\x00" in path or "://" in path or not path.lower().endswith(".pt"):
        raise ValueError("Enter a local segmentation .pt path")
    from system_assets import asset_path
    asset_path(path.strip(), ".pt")
    result["model_path"] = path.strip()
    for key in ("detection_confidence", "acceptance_confidence"):
        value = result[key]
        if isinstance(value, bool):
            raise ValueError("Invalid " + key)
        value = float(value)
        if not math.isfinite(value) or not .01 <= value <= 1:
            raise ValueError(key + " must be between 0.01 and 1")
        result[key] = value
    if result["detection_confidence"] > result["acceptance_confidence"]:
        raise ValueError("Detection floor must not exceed acceptance confidence")
    roi = result["roi"]
    if not isinstance(roi, list) or len(roi) != 4 or any(isinstance(v, bool) for v in roi):
        raise ValueError("ROI requires x, y, width, height")
    roi = [float(v) for v in roi]
    x, y, w, h = roi
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in roi) or min(w, h) <= 0 or x + w > 1.000001 or y + h > 1.000001:
        raise ValueError("ROI must fit within the image")
    result["roi"] = roi
    if result["imgsz"] not in (320, 640, 960):
        raise ValueError("Image size must be 320, 640 or 960")
    return result


def revision(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:16]


def load_settings(path):
    path = Path(path)
    return validate_settings(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else validate_settings({})


def save_settings(path, values):
    result = validate_settings(values)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result


def public_settings(settings):
    return {key: value for key, value in settings.items() if key != "model_path"} | {"revision": revision(settings)}
