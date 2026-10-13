"""FastAPI interface for one-shot RealSense image and size measurements.

Run with: uvicorn api:app --host 0.0.0.0 --port 8003
"""
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock, RLock
import base64
import uuid
import copy
from annotation_sidecar import build_annotation

import cv2
import numpy as np
import pyrealsense2 as rs
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
import json
from ring_geometry import measure_ring_mask

WIDTH, HEIGHT, FPS = 1280, 720, 30
SETTINGS_FILE = Path(__file__).with_name("settings.json")
LEGACY_CONFIG_FILE = Path(__file__).with_name("vision_config.json")
OBJECT_MODES = {
    "coin": "Coin", "bar": "Bar", "chain": "Chain",
    "ring": "Ring", "bangle": "Bangle",
    "ornament": "Ornaments / Pendants / Others",
}


def default_settings():
    return {"version": 2, "modes": {mode: {} for mode in OBJECT_MODES.values()}}


def normalize_settings(settings):
    """Normalize current and pre-v2 settings exactly like the GUI."""
    normalized = default_settings()
    if isinstance(settings, dict):
        normalized.update(settings)
    modes = normalized.setdefault("modes", {})
    legacy_areas = normalized.get("areas", {})
    legacy_calibrations = normalized.get("color_calibrations", {})
    for mode in OBJECT_MODES.values():
        mode_settings = modes.setdefault(mode, {})
        if mode in legacy_areas and "aoi" not in mode_settings:
            mode_settings["aoi"] = legacy_areas[mode]
        if mode in legacy_calibrations and "color_calibration" not in mode_settings:
            mode_settings["color_calibration"] = legacy_calibrations[mode]
    normalized.pop("areas", None)
    normalized.pop("color_calibrations", None)
    normalized["version"] = 2
    return normalized


def load_settings():
    """Read settings from the service directory, including legacy files."""
    config_path = SETTINGS_FILE if SETTINGS_FILE.exists() else LEGACY_CONFIG_FILE
    if not config_path.exists():
        return default_settings()
    try:
        return normalize_settings(json.loads(config_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return default_settings()


def mode_name(object_type):
    normalized = str(object_type).strip().lower()
    try:
        return OBJECT_MODES[normalized]
    except KeyError:
        raise HTTPException(400, "Unsupported type")


def shared_aoi(settings):
    """Return the one AOI shared by every object type."""
    saved = settings.get("aoi")
    if saved is None:
        saved = settings.get("modes", {}).get("Coin", {}).get("aoi")
    if isinstance(saved, dict):
        return saved.get("coordinates")
    return saved


class Camera:
    def __init__(self, serial_number=None):
        self.pipeline = rs.pipeline()
        config = rs.config()
        if serial_number:
            config.enable_device(serial_number)  # Camera-only checker can select one of several devices.
        config.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, FPS)
        config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
        profile = self.pipeline.start(config)
        self.align = rs.align(rs.stream.color)
        self.depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
        self.intrinsics = None
        self.lock = Lock()

    def frame(self):
        with self.lock:
            frames = self.align.process(self.pipeline.wait_for_frames(5000))
            depth = frames.get_depth_frame()
            color = frames.get_color_frame()
            if not depth or not color:
                raise HTTPException(503, "Camera frame is unavailable")
            self.intrinsics = depth.profile.as_video_stream_profile().intrinsics
            return np.asanyarray(color.get_data()).copy(), np.asanyarray(depth.get_data()).copy()

    def close(self):
        self.pipeline.stop()


camera = None
latest_image = None
latest_detected_image = None
# VISUAL-01: raw JPEG and geometry published as one immutable capture bundle.
snapshot_lock = RLock()
latest_bundle = None
annotation_contours = []


class AOIRequest(BaseModel):
    type: str = "coin"
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=1)
    height: int = Field(gt=1)


@asynccontextmanager
async def lifespan(app):
    global camera
    camera = Camera()
    yield
    camera.close()


app = FastAPI(title="Vision Service API", version="1.0", lifespan=lifespan)


@app.get("/settings")
def get_settings(type: str = Query("coin", min_length=1)):
    """Return the AOI and calibration status saved by diameter.py."""
    mode = mode_name(type)
    settings = load_settings()
    mode_settings = settings.get("modes", {}).get(mode, {})
    calibration = mode_settings.get("color_calibration")
    return {"type": mode, "aoi": settings.get("aoi") or settings.get("modes", {}).get("Coin", {}).get("aoi"),
            "calibration_saved": bool(calibration),
            "calibration": calibration}


def object_mask(image, object_type):
    """Build an object mask from the selected mode's saved Lab background."""
    mode = mode_name(object_type)
    calibration = load_settings().get("modes", {}).get(mode, {}).get("color_calibration")
    if not calibration:
        raise HTTPException(400, f"No colour calibration saved for type '{object_type}'")
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    center = np.asarray(calibration["lab_median"], dtype=np.float32)
    spread = np.asarray(calibration["lab_spread"], dtype=np.float32)
    tolerance = np.maximum(spread * 3.0, np.array([12.0, 10.0, 10.0]))
    mask = (~np.all(np.abs(lab - center) <= tolerance, axis=2)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def measure(image, depth, object_type):
    global latest_bundle, annotation_contours
    with snapshot_lock:
        annotation_contours = []
        latest_bundle = None  # Failed detection must not expose an earlier capture.
        result = _measure_legacy(image, depth, object_type)
        if object_type.strip().lower() in {"ring", "bangle", "coin", "bar"}:
            capture_id = uuid.uuid4().hex
            ok, raw = cv2.imencode(".jpg", image)  # Never draw on this array.
            if not ok:
                latest_bundle = None
                raise HTTPException(500, "Could not encode raw capture")
            annotation = build_annotation(image, copy.deepcopy(result), annotation_contours, capture_id)
            latest_bundle = {"capture_id": capture_id, "annotation": annotation,
                "raw_jpeg_base64": base64.b64encode(raw.tobytes()).decode("ascii")}
        else:
            latest_bundle = None  # Do not reuse a prior ring overlay for another shape.
        return result


def _measure_legacy(image, depth, object_type):
    global latest_detected_image, annotation_contours
    mask = object_mask(image, object_type)
    # REV 2026-10-02 / RING-01: canonical type is case-insensitive. Settings
    # use title-case mode names, but dimension dispatch must use lowercase.
    shape = object_type.strip().lower()
    if shape in {"ring", "bangle"}:
        result, outer, hole = measure_ring_mask(
            mask, depth, camera.depth_scale, camera.intrinsics.fx,
            camera.intrinsics.fy, object_type)
        annotation_contours = [outer, hole]
        latest_detected_image = image.copy()
        if outer is not None:
            cv2.drawContours(latest_detected_image, [outer], -1, (0, 255, 0), 2)
        if hole is not None:
            cv2.drawContours(latest_detected_image, [hole], -1, (255, 180, 0), 2)
        if result["geometry_ok"]:
            label = f"Inner {result['inner_diameter_mm']:.2f} / Outer {result['outer_diameter_mm']:.2f} mm"
        else:
            label = "Manual diameters required"
        cv2.putText(latest_detected_image, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 255, 255), 1, cv2.LINE_AA)
        return result
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= 100]
    if not contours:
        latest_detected_image = image.copy()
        return {"detected": False, "type": object_type, "message": "No object"}
    contour = max(contours, key=cv2.contourArea)
    annotation_contours = [contour]
    pixels = cv2.drawContours(np.zeros_like(mask), [contour], -1, 255, -1)
    valid = depth[(pixels > 0) & (depth > 0)]
    if not valid.size:
        latest_detected_image = image.copy()
        return {"detected": False, "type": object_type,
                "message": "No object (no valid depth)"}
    latest_detected_image = image.copy()
    cv2.drawContours(latest_detected_image, [contour], -1, (0, 255, 0), 3)
    z = float(np.median(valid)) * camera.depth_scale
    area = float(cv2.countNonZero(pixels) * z * z /
                 (camera.intrinsics.fx * camera.intrinsics.fy) * 1_000_000)
    result = {"detected": True, "type": object_type, "surface_area_mm2": area,
              "estimated_depth_mm": z * 1000.0}
    if shape == "coin":
        (x, y), radius = cv2.minEnclosingCircle(contour)
        scale = z * 1000.0 * (1 / camera.intrinsics.fx + 1 / camera.intrinsics.fy) / 2
        result.update(center=[round(x, 1), round(y, 1)], diameter_mm=2 * radius * scale)
    else:
        _, _, w, h = cv2.boundingRect(contour)
        result.update(width_mm=w * z / camera.intrinsics.fx * 1000,
                      length_mm=h * z / camera.intrinsics.fy * 1000)
    return result


@app.get("/image")
def get_image():
    global latest_image
    latest_image, _ = camera.frame()
    ok, encoded = cv2.imencode(".jpg", latest_image)
    if not ok:
        raise HTTPException(500, "Could not encode image")
    return Response(content=encoded.tobytes(), media_type="image/jpeg")


@app.get("/image/detected")
def get_detected_image():
    if latest_detected_image is None:
        raise HTTPException(404, "No detection has been performed")
    ok, encoded = cv2.imencode(".jpg", latest_detected_image)
    if not ok:
        raise HTTPException(500, "Could not encode detected image")
    return Response(content=encoded.tobytes(), media_type="image/jpeg")


@app.get("/image/bundle")
def get_image_bundle():
    # One response prevents mismatching a JPEG with another detection's geometry.
    with snapshot_lock:
        if latest_bundle is None:
            raise HTTPException(404, "No sidecar capture available; use legacy image")
        return copy.deepcopy(latest_bundle)


@app.post("/aoi")
def save_aoi(request: AOIRequest):
    """Save an AOI for a mode; subsequent measurements crop to it."""
    mode = mode_name(request.type)
    settings = load_settings()
    settings["aoi"] = {
        "coordinates": [request.x, request.y, request.x + request.width - 1,
                        request.y + request.height - 1],
        "resolution": [WIDTH, HEIGHT],
    }
    for mode_settings in settings.setdefault("modes", {}).values():
        mode_settings.pop("aoi", None)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n")
    return {"saved": True, "type": mode,
            "aoi": request.model_dump() if hasattr(request, "model_dump") else request.dict()}


@app.get("/size")
def get_size(type: str = Query("coin", min_length=1)):
    global latest_image
    normalized = type.strip().lower()
    if normalized not in OBJECT_MODES:
        raise HTTPException(400, f"Unsupported type. Use: {', '.join(OBJECT_MODES)}")
    image, depth = camera.frame()
    mode = mode_name(normalized)
    settings = load_settings()
    aoi = shared_aoi(settings)
    if isinstance(aoi, list) and len(aoi) == 4:
        x1, y1, x2, y2 = [int(v) for v in aoi]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(WIDTH - 1, x2), min(HEIGHT - 1, y2)
        if x2 <= x1 or y2 <= y1:
            raise HTTPException(400, "Invalid AOI; select an area inside the current frame")
        image = image[y1:y2 + 1, x1:x2 + 1]
        depth = depth[y1:y2 + 1, x1:x2 + 1]
    latest_image = image
    return measure(image, depth, mode)
