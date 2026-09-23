from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    import pyrealsense2 as rs
except ImportError:
    rs = None


@dataclass
class VisionConfig:
    width: int = 1280
    height: int = 720
    fps: int = 15
    warmup_frames: int = 20
    blur_kernel: int = 7
    canny_low: int = 50
    canny_high: int = 140
    adaptive_block_size: int = 31
    adaptive_c: int = 6
    morph_kernel: int = 5
    min_contour_area_px: int = 1500
    circle_min_radius_px: int = 20
    circle_max_radius_px: int = 260
    circle_param1: int = 120
    circle_param2: int = 22
    pixels_per_mm: float | None = None


@dataclass
class VisionCapture:
    color_bgr: np.ndarray
    depth_mm: np.ndarray | None
    intrinsics: dict[str, float] | None
    source: str
    captured_at: str


def _timestamp_text() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _odd(value: int, fallback: int) -> int:
    parsed = int(value or fallback)
    if parsed < 3:
        parsed = fallback
    return parsed if parsed % 2 == 1 else parsed + 1


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _depth_area_mm2(mask: np.ndarray, depth_mm: np.ndarray, intrinsics: dict[str, float]) -> float | None:
    if depth_mm is None or not intrinsics:
        return None
    fy = float(intrinsics.get("fy") or 0.0)
    fx = float(intrinsics.get("fx") or 0.0)
    if fx <= 0 or fy <= 0:
        return None
    depth_values = depth_mm[mask > 0].astype(np.float64)
    if depth_values.size == 0:
        return None
    depth_values = depth_values[np.isfinite(depth_values) & (depth_values > 0)]
    if depth_values.size == 0:
        return None
    pixel_areas = (depth_values / fx) * (depth_values / fy)
    return float(pixel_areas.sum())


def _pixel_scale_mm(mask: np.ndarray, depth_mm: np.ndarray, intrinsics: dict[str, float]) -> float | None:
    if depth_mm is None or not intrinsics:
        return None
    fx = float(intrinsics.get("fx") or 0.0)
    fy = float(intrinsics.get("fy") or 0.0)
    if fx <= 0 or fy <= 0:
        return None
    depth_values = depth_mm[mask > 0].astype(np.float64)
    depth_values = depth_values[np.isfinite(depth_values) & (depth_values > 0)]
    if depth_values.size == 0:
        return None
    median_depth = float(np.median(depth_values))
    mm_per_px_x = median_depth / fx
    mm_per_px_y = median_depth / fy
    return (mm_per_px_x + mm_per_px_y) / 2.0


def _fallback_scale_mm_per_px(config: VisionConfig) -> float | None:
    if config.pixels_per_mm and config.pixels_per_mm > 0:
        return 1.0 / config.pixels_per_mm
    return None


def analyze_frame(capture: VisionCapture, config: VisionConfig) -> dict[str, Any]:
    color = capture.color_bgr.copy()
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    blur_kernel = _odd(config.blur_kernel, 7)
    blurred = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)

    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        _odd(config.adaptive_block_size, 31),
        config.adaptive_c,
    )
    edges = cv2.Canny(blurred, config.canny_low, config.canny_high)
    combined = cv2.bitwise_or(thresh, edges)

    kernel_size = max(3, int(config.morph_kernel))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= config.min_contour_area_px]
    if not contours:
        return {
            "ok": False,
            "message": "No object contour detected",
            "captured_at": capture.captured_at,
            "source": capture.source,
        }

    contour = max(contours, key=cv2.contourArea)
    contour_area_px = float(cv2.contourArea(contour))
    x, y, w, h = cv2.boundingRect(contour)
    perimeter_px = float(cv2.arcLength(contour, True))
    hull = cv2.convexHull(contour)
    hull_area_px = float(cv2.contourArea(hull))
    solidity = contour_area_px / hull_area_px if hull_area_px > 0 else 0.0
    circularity = (4.0 * math.pi * contour_area_px / (perimeter_px * perimeter_px)) if perimeter_px > 0 else 0.0

    mask_single = np.zeros_like(gray)
    cv2.drawContours(mask_single, [contour], -1, 255, thickness=-1)

    mm_per_px = _pixel_scale_mm(mask_single, capture.depth_mm, capture.intrinsics)
    if mm_per_px is None:
        mm_per_px = _fallback_scale_mm_per_px(config)

    area_mm2 = _depth_area_mm2(mask_single, capture.depth_mm, capture.intrinsics)
    if area_mm2 is None and mm_per_px is not None:
        area_mm2 = contour_area_px * (mm_per_px ** 2)

    width_mm = w * mm_per_px if mm_per_px is not None else None
    height_mm = h * mm_per_px if mm_per_px is not None else None
    equivalent_diameter_mm = None
    if area_mm2 is not None and area_mm2 > 0:
        equivalent_diameter_mm = math.sqrt((4.0 * area_mm2) / math.pi)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(40, gray.shape[1] // 6),
        param1=config.circle_param1,
        param2=config.circle_param2,
        minRadius=config.circle_min_radius_px,
        maxRadius=config.circle_max_radius_px,
    )

    shape_guess = "Irregular"
    circle_candidates: list[dict[str, float]] = []
    if circles is not None:
        for item in np.round(circles[0, :]).astype(int):
            cx, cy, radius = int(item[0]), int(item[1]), int(item[2])
            if x <= cx <= x + w and y <= cy <= y + h:
                circle_candidates.append(
                    {
                        "center_x_px": float(cx),
                        "center_y_px": float(cy),
                        "radius_px": float(radius),
                        "diameter_mm": float(radius * 2 * mm_per_px) if mm_per_px is not None else None,
                    }
                )
        if circle_candidates:
            shape_guess = "Circular"
        elif solidity > 0.92:
            shape_guess = "Bar"
    else:
        if circularity >= 0.72:
            shape_guess = "Circular"
        elif solidity > 0.92:
            shape_guess = "Bar"

    overlay = color.copy()
    cv2.drawContours(overlay, [contour], -1, (0, 255, 255), 3)
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 200, 0), 2)
    for item in circle_candidates:
        cx = int(item["center_x_px"])
        cy = int(item["center_y_px"])
        radius = int(item["radius_px"])
        cv2.circle(overlay, (cx, cy), radius, (0, 180, 255), 2)
        cv2.circle(overlay, (cx, cy), 2, (0, 180, 255), 3)

    return {
        "ok": True,
        "message": "Object detected",
        "captured_at": capture.captured_at,
        "source": capture.source,
        "shape_guess": shape_guess,
        "contour_area_px": round(contour_area_px, 3),
        "perimeter_px": round(perimeter_px, 3),
        "circularity": round(circularity, 4),
        "solidity": round(solidity, 4),
        "bounding_box_px": {"x": x, "y": y, "width": w, "height": h},
        "bounding_box_mm": {
            "width": round(width_mm, 3) if width_mm is not None else None,
            "height": round(height_mm, 3) if height_mm is not None else None,
        },
        "projected_area_mm2": round(area_mm2, 3) if area_mm2 is not None else None,
        "equivalent_diameter_mm": round(equivalent_diameter_mm, 3) if equivalent_diameter_mm is not None else None,
        "mm_per_pixel": round(mm_per_px, 6) if mm_per_px is not None else None,
        "circle_candidates": circle_candidates,
        "mask": mask_single,
        "overlay": overlay,
    }


def capture_from_image(image_path: Path) -> VisionCapture:
    color = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if color is None:
        raise ValueError(f"Unable to read image: {image_path}")
    return VisionCapture(
        color_bgr=color,
        depth_mm=None,
        intrinsics=None,
        source=str(image_path),
        captured_at=_timestamp_text(),
    )


def capture_from_realsense(config: VisionConfig) -> VisionCapture:
    if rs is None:
        raise RuntimeError("pyrealsense2 is not installed")

    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.color, config.width, config.height, rs.format.bgr8, config.fps)
    rs_config.enable_stream(rs.stream.depth, config.width, config.height, rs.format.z16, config.fps)
    align = rs.align(rs.stream.color)

    profile = pipeline.start(rs_config)
    try:
        for _ in range(max(1, config.warmup_frames)):
            pipeline.wait_for_frames()

        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        color_frame = aligned.get_color_frame()
        depth_frame = aligned.get_depth_frame()
        if not color_frame or not depth_frame:
            raise RuntimeError("Unable to capture aligned color/depth frames")

        color = np.asanyarray(color_frame.get_data()).copy()
        depth = np.asanyarray(depth_frame.get_data()).astype(np.float32)
        depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
        depth_mm = depth * float(depth_scale) * 1000.0

        intr = color_frame.profile.as_video_stream_profile().intrinsics
        intrinsics = {
            "fx": float(intr.fx),
            "fy": float(intr.fy),
            "ppx": float(intr.ppx),
            "ppy": float(intr.ppy),
        }
        return VisionCapture(
            color_bgr=color,
            depth_mm=depth_mm,
            intrinsics=intrinsics,
            source="intel_realsense",
            captured_at=_timestamp_text(),
        )
    finally:
        pipeline.stop()


def save_artifacts(result: dict[str, Any], output_dir: Path, stem: str) -> dict[str, str]:
    _ensure_dir(output_dir)
    mask = result.pop("mask", None)
    overlay = result.pop("overlay", None)
    saved: dict[str, str] = {}

    if overlay is not None:
        overlay_path = output_dir / f"{stem}_overlay.png"
        cv2.imwrite(str(overlay_path), overlay)
        saved["overlay_path"] = str(overlay_path)
    if mask is not None:
        mask_path = output_dir / f"{stem}_mask.png"
        cv2.imwrite(str(mask_path), mask)
        saved["mask_path"] = str(mask_path)

    return saved


def run_capture(
    *,
    image_path: Path | None,
    use_realsense: bool,
    output_dir: Path,
    pixels_per_mm: float | None,
) -> dict[str, Any]:
    config = VisionConfig(pixels_per_mm=pixels_per_mm)
    capture = capture_from_realsense(config) if use_realsense else capture_from_image(image_path)  # type: ignore[arg-type]
    result = analyze_frame(capture, config)
    stem = f"vision_{time.strftime('%Y%m%d_%H%M%S')}"
    saved = save_artifacts(result, output_dir, stem)
    result.update(saved)

    json_path = output_dir / f"{stem}_result.json"
    _ensure_dir(output_dir)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["result_json_path"] = str(json_path)
    return result


def build_demo_image(output_dir: Path) -> Path:
    _ensure_dir(output_dir)
    image = np.full((720, 1280, 3), 20, dtype=np.uint8)
    cv2.rectangle(image, (120, 120), (1160, 600), (55, 55, 55), thickness=-1)
    cv2.circle(image, (640, 360), 120, (225, 225, 225), thickness=-1)
    cv2.circle(image, (640, 360), 58, (55, 55, 55), thickness=-1)
    path = output_dir / "vision_demo_ring.png"
    cv2.imwrite(str(path), image)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone Intel RealSense / OpenCV vision test tool")
    parser.add_argument("--image", type=Path, help="Analyze a saved image instead of RealSense")
    parser.add_argument("--realsense", action="store_true", help="Capture one frame from Intel RealSense")
    parser.add_argument("--output-dir", type=Path, default=Path("vision_debug"), help="Where to save debug outputs")
    parser.add_argument("--pixels-per-mm", type=float, default=None, help="Fallback pixel calibration for image-only mode")
    parser.add_argument("--demo-image", action="store_true", help="Generate a synthetic ring image and analyze it")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.demo_image:
        demo_path = build_demo_image(args.output_dir)
        args.image = demo_path
        args.realsense = False
        if args.pixels_per_mm is None:
            args.pixels_per_mm = 4.0

    if not args.realsense and args.image is None:
        raise SystemExit("Use --image PATH, --demo-image, or --realsense")
    if args.realsense and args.image is not None:
        raise SystemExit("Choose either --realsense or --image, not both")

    result = run_capture(
        image_path=args.image,
        use_realsense=bool(args.realsense),
        output_dir=args.output_dir,
        pixels_per_mm=args.pixels_per_mm,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
