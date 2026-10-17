"""CAMERA-DEBUG-01: read-only RealSense diagnostics and camera-only GUI checker.

Existing Image service: py camera_debug.py
Camera alone (stop Image service first): py camera_debug.py --direct
No window: py camera_debug.py --headless --count 5
GUI keys: D toggle diagnostic display, Q/Esc quit. Raw frames are never modified.
SDK API: https://realsenseai.github.io/librealsense/python_docs/
"""
from datetime import datetime, timezone
import math


def intrinsics_dict(profile):
    intr = profile.as_video_stream_profile().get_intrinsics()
    return {"width": int(intr.width), "height": int(intr.height),
            "fx_px": float(intr.fx), "fy_px": float(intr.fy),
            "ppx_px": float(intr.ppx), "ppy_px": float(intr.ppy),
            "distortion_model": str(intr.model),
            "distortion_coefficients": [float(x) for x in intr.coeffs],
            "configured_fps": int(profile.fps())}


def camera_metadata(profile, rs):
    device = profile.get_device()
    info = {}
    for name in ("name", "serial_number", "firmware_version", "usb_type_descriptor"):
        try:
            field = getattr(rs.camera_info, name)
            info[name] = device.get_info(field) if device.supports(field) else None
        except (RuntimeError, AttributeError):
            info[name] = None
    return {"device": info, "streams": {
        "color": intrinsics_dict(profile.get_stream(rs.stream.color)),
        "native_depth": intrinsics_dict(profile.get_stream(rs.stream.depth))}}


def frame_diagnostics(metadata, depth, depth_scale, aligned_profile, color):
    import numpy as np
    # A sparse grid is enough for debugging; these are scene statistics, not metrology.
    sample = depth[::4, ::4]
    valid = sample[sample > 0]
    scale_ok = math.isfinite(depth_scale) and depth_scale > 0
    distances = valid.astype(np.float64) * depth_scale * 1000 if scale_ok else []
    warnings = []
    if not scale_ok:
        warnings.append("Invalid depth scale")
    if not valid.size:
        warnings.append("No valid depth samples in this frame")
    return {**metadata, "captured_at": datetime.now(timezone.utc).isoformat(),
        "color_frame_number": int(color.get_frame_number()),
        "color_timestamp_ms": float(color.get_timestamp()),
        "aligned_depth": intrinsics_dict(aligned_profile),
        "depth_unit_m": float(depth_scale) if scale_ok else None,
        "depth_grid_stride_px": 4, "depth_samples": int(sample.size),
        "valid_depth_samples": int(valid.size),
        "valid_depth_percent": round(100 * valid.size / sample.size, 2) if sample.size else 0,
        "scene_distance_mm": {"median": float(np.median(distances)),
            "minimum": float(np.min(distances)), "maximum": float(np.max(distances))} if len(distances) else None,
        "depth_note": "Sampled scene distance from camera; NOT item thickness or tray-relative height",
        "measurement_method": "OpenCV background mask; not YOLO inference", "warnings": warnings}


def main():
    import argparse
    import base64
    import json
    import time
    import urllib.request
    parser = argparse.ArgumentParser(description="Camera-only checker: no scale or signal commands")
    parser.add_argument("--url", default="http://127.0.0.1:8003")
    parser.add_argument("--direct", action="store_true", help="Own camera directly; stop Image service first")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--count", type=int, help="Frame count; default 5 headless, unlimited GUI")
    args = parser.parse_args()
    count = args.count if args.count is not None else 5 if args.headless else 0
    if count < 0 or (args.headless and count == 0):
        parser.error("Use a positive count for headless mode")
    camera = None
    show_debug = True
    try:
        if args.direct:
            import api
            camera = api.Camera()
            api.camera = camera
        if not args.headless:
            import cv2
            import numpy as np
            cv2.namedWindow("Camera checker", cv2.WINDOW_NORMAL)
        index = 0
        while not count or index < count:
            if camera:
                bundle = api.capture_bundle("unknown", annotations=False, debug=True)
            else:
                url = args.url.rstrip("/") + "/image/frame?type=unknown&annotations=false&debug=true"
                with urllib.request.urlopen(url, timeout=8) as response:
                    bundle = json.load(response)
            report = bundle.get("camera_debug")
            if not report:
                raise RuntimeError("No diagnostics returned. Apply CAMERA-DEBUG-01 and restart Image service.")
            if index == 0 or args.headless:
                print(json.dumps(report, indent=2, allow_nan=False), flush=True)
            index += 1
            if not args.headless:
                raw = cv2.imdecode(np.frombuffer(base64.b64decode(bundle["raw_jpeg_base64"]), np.uint8), cv2.IMREAD_COLOR)
                if raw is None:
                    raise RuntimeError("Camera JPEG could not be decoded")
                display = raw.copy()
                if show_debug:
                    intr = report["aligned_depth"]
                    distance = (report["scene_distance_mm"] or {}).get("median")
                    lines = [str(report["device"].get("name")) + " / " + str(report["device"].get("serial_number")),
                        f"Aligned: {intr['width']}x{intr['height']} | fx={intr['fx_px']:.2f} fy={intr['fy_px']:.2f} px",
                        f"Scene distance: {distance if distance is not None else 'unavailable'} mm (NOT thickness)",
                        f"Valid sampled depth: {report['valid_depth_percent']}%",
                        "D: debug on/off | Q: quit"]
                    for i, line in enumerate(lines):
                        point = (12, 26 + i * 25)
                        cv2.putText(display, line, point, cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 3)
                        cv2.putText(display, line, point, cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
                cv2.imshow("Camera checker", display)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord("d"):
                    show_debug = not show_debug
            time.sleep(.2)
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, f"Camera checker: {exc}\nCheck Image service on 8003, or use --direct with that service stopped.\n")
    finally:
        if camera:
            camera.close()
        if not args.headless and "cv2" in locals():
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
