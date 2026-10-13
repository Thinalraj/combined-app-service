"""RING-01 / 2026-10-02: shared ring/bangle geometry for API and camera checker.

Measure a flat, approximately circular annulus. Keep the hole separate from the
outer contour and use depth on foreground material only. These quality limits
are conservative workflow heuristics; validate millimetres against calipers.
OpenCV hierarchy/fitEllipse: https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html
"""
import math

import cv2
import numpy as np

MIN_OUTER_AREA_PX = 100
MIN_HOLE_AREA_PX = 25
MIN_DEPTH_POINTS = 20
MIN_AXIS_RATIO = 0.85  # Reject visibly oval/tilted rings: one circular diameter is ambiguous.
MAX_FIT_RESIDUAL = 0.12
MAX_CENTER_OFFSET_RATIO = 0.10


def _fit_metric_ellipse(contour, z_mm, fx, fy):
    if len(contour) < 5:
        raise ValueError("Too few contour points")
    points = contour.astype(np.float32).copy()
    points[:, 0, 0] *= z_mm / fx
    points[:, 0, 1] *= z_mm / fy
    center, axes, angle = cv2.fitEllipse(points)
    if not all(math.isfinite(v) and v > 0 for v in axes):
        raise ValueError("Invalid fitted axes")
    xy = points[:, 0, :] - np.asarray(center)
    theta = math.radians(angle)
    rotation = np.array([[math.cos(theta), math.sin(theta)],
                         [-math.sin(theta), math.cos(theta)]])
    local = xy @ rotation.T
    radial = np.sqrt((local[:, 0] / (axes[0] / 2)) ** 2
                     + (local[:, 1] / (axes[1] / 2)) ** 2)
    return {"center": center, "axes": axes, "diameter": sum(axes) / 2,
            "axis_ratio": min(axes) / max(axes),
            "residual_p90": float(np.percentile(np.abs(radial - 1), 90))}


def measure_ring_mask(mask, depth, depth_scale, fx, fy, object_type="Ring"):
    """Return (JSON-safe result, outer contour, hole contour). No camera I/O.

    width_mm/length_mm are compatibility aliases for INNER/OUTER diameters,
    never a bounding-box width/height. Invalid geometry has no auto-fill values.
    """
    result = {"detected": False, "type": object_type, "geometry_ok": False,
              "manual_required": True, "measurement_method": "annulus_contours_v1",
              "inner_diameter_mm": None, "outer_diameter_mm": None,
              "width_mm": None, "length_mm": None, "surface_area_mm2": None,
              "message": "No object detected"}

    def fail(message, outer=None, hole=None):
        result["message"] = message + ". Enter measured inner/outer diameters manually."
        return result, outer, hole

    if mask.ndim != 2 or depth.shape != mask.shape:
        return fail("Colour mask and aligned depth have different dimensions")
    if not all(math.isfinite(float(v)) and float(v) > 0 for v in (depth_scale, fx, fy)):
        return fail("Invalid depth scale or camera intrinsics")
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return fail("No ring outline detected")
    links = hierarchy[0]
    roots = [i for i, link in enumerate(links)
             if link[3] < 0 and cv2.contourArea(contours[i]) >= MIN_OUTER_AREA_PX]
    if not roots:
        return fail("No sufficiently large ring outline")
    index = max(roots, key=lambda i: cv2.contourArea(contours[i]))
    outer = contours[index]
    result["detected"] = True
    x, y, w, h = cv2.boundingRect(outer)
    if x <= 0 or y <= 0 or x + w >= mask.shape[1] or y + h >= mask.shape[0]:
        return fail("Outline touches the AOI edge; move the item inward or enlarge the AOI", outer)

    holes = [i for i, link in enumerate(links)
             if link[3] == index and cv2.contourArea(contours[i]) >= MIN_HOLE_AREA_PX]
    # Intersect with the original foreground mask: hole/background pixels never
    # contribute to material area or the depth used for metric scaling.
    pixels = cv2.drawContours(np.zeros_like(mask), [outer], -1, 255, -1)
    pixels = cv2.bitwise_and(pixels, mask)
    valid = depth[(pixels > 0) & (depth > 0)]
    if valid.size < MIN_DEPTH_POINTS:
        return fail("Insufficient depth on the metal surface", outer)
    z_mm = float(np.median(valid)) * depth_scale * 1000
    result.update(estimated_depth_mm=round(z_mm, 3),
                  valid_depth_points=int(valid.size),
                  surface_area_mm2=round(float(cv2.countNonZero(pixels) * z_mm ** 2 / (fx * fy)), 3))
    if not holes:
        return fail("No enclosed hole detected; check lighting, background calibration and placement", outer)
    hole_index = max(holes, key=lambda i: cv2.contourArea(contours[i]))
    hole = contours[hole_index]
    significant = [i for i in holes if cv2.contourArea(contours[i]) > 0.05 * cv2.contourArea(outer)]
    if len(significant) > 1:
        return fail("Multiple substantial holes; circular annulus geometry is ambiguous", outer, hole)
    try:
        out_fit = _fit_metric_ellipse(outer, z_mm, fx, fy)
        in_fit = _fit_metric_ellipse(hole, z_mm, fx, fy)
    except (ValueError, cv2.error):
        return fail("Unable to fit both diameter boundaries", outer, hole)

    result["outer_axes_mm"] = [round(v, 3) for v in out_fit["axes"]]
    result["inner_axes_mm"] = [round(v, 3) for v in in_fit["axes"]]
    result["quality"] = {"outer_axis_ratio": round(out_fit["axis_ratio"], 4),
                         "inner_axis_ratio": round(in_fit["axis_ratio"], 4),
                         "outer_fit_residual_p90": round(out_fit["residual_p90"], 4),
                         "inner_fit_residual_p90": round(in_fit["residual_p90"], 4)}
    if min(out_fit["axis_ratio"], in_fit["axis_ratio"]) < MIN_AXIS_RATIO:
        return fail("Outline is oval or tilted; lay a circular ring/bangle flat", outer, hole)
    if max(out_fit["residual_p90"], in_fit["residual_p90"]) > MAX_FIT_RESIDUAL:
        return fail("Outline is too irregular for circular diameter measurement", outer, hole)
    offset = math.dist(out_fit["center"], in_fit["center"])
    if offset > out_fit["diameter"] * MAX_CENTER_OFFSET_RATIO:
        return fail("Hole and outer outline are not sufficiently concentric", outer, hole)
    inner, outer_mm = in_fit["diameter"], out_fit["diameter"]
    if not 0 < inner < outer_mm or max(in_fit["axes"]) >= min(out_fit["axes"]):
        return fail("Inner diameter is inconsistent with the outer diameter", outer, hole)
    result.update(geometry_ok=True, manual_required=False,
                  inner_diameter_mm=round(inner, 3), outer_diameter_mm=round(outer_mm, 3),
                  width_mm=round(inner, 3), length_mm=round(outer_mm, 3),
                  annular_area_mm2=round(math.pi * (outer_mm ** 2 - inner ** 2) / 4, 3),
                  message="Inner/outer diameters measured; verify against calipers for your fixture")
    return result, outer, hole
