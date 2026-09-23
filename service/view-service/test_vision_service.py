from __future__ import annotations

import numpy as np

from vision_service import VisionCapture, VisionConfig, analyze_frame


def build_ring_image() -> np.ndarray:
    image = np.full((720, 1280, 3), 20, dtype=np.uint8)
    image[120:600, 120:1160] = 55
    yy, xx = np.ogrid[:720, :1280]
    outer = (xx - 640) ** 2 + (yy - 360) ** 2 <= 120 ** 2
    inner = (xx - 640) ** 2 + (yy - 360) ** 2 <= 58 ** 2
    image[outer] = 225
    image[inner] = 55
    return image


def test_analyze_frame_detects_circular_shape() -> None:
    capture = VisionCapture(
        color_bgr=build_ring_image(),
        depth_mm=None,
        intrinsics=None,
        source="synthetic",
        captured_at="2026-08-29 10:00:00",
    )
    config = VisionConfig(pixels_per_mm=4.0)
    result = analyze_frame(capture, config)
    assert result["ok"] is True
    assert result["shape_guess"] == "Circular"
    assert result["projected_area_mm2"] is not None
    assert result["equivalent_diameter_mm"] is not None


def test_analyze_frame_handles_missing_object() -> None:
    image = np.full((720, 1280, 3), 30, dtype=np.uint8)
    capture = VisionCapture(
        color_bgr=image,
        depth_mm=None,
        intrinsics=None,
        source="synthetic",
        captured_at="2026-08-29 10:00:00",
    )
    config = VisionConfig(pixels_per_mm=4.0)
    result = analyze_frame(capture, config)
    assert result["ok"] is False
    assert "No object contour detected" in result["message"]
