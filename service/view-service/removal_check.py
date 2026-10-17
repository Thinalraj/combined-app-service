"""REMOVE-01: combine read-only evidence; this module never tares or adjusts.

An empty prediction only means no coin/bar candidates above the configured
floor inside the ROI. Operator inspection is always required, even at zero g.
"""
import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def evaluate(scale, preparation, settings, vision_enabled, detection=None, camera_error=None):
    result = {"ready_for_confirmation": False, "operator_confirmation_required": True,
              "state": "unknown", "message": "Removal not confirmed.",
              "preparation_id": preparation.get("id"), "vision_enabled": vision_enabled,
              "weight_g": scale.get("average"), "range_g": scale.get("range")}
    if preparation.get("state") != "ready" or preparation.get("needs_recovery") or preparation.get("result", {}).get("zero_verified") is not True:
        result["message"] = "No current verified empty-pan zero. Return to Prepare Empty Scale."
        return result
    count = scale.get("samples_valid")
    if (scale.get("success") is not True or scale.get("unit") != "g" or
            not finite(count) or count < 5 or scale.get("stable_samples") != count or
            scale.get("dynamic_samples") != 0 or
            not all(finite(scale.get(k)) for k in ("average", "minimum", "maximum", "range")) or
            scale["minimum"] > scale["maximum"] or scale["range"] < 0 or
            not scale["minimum"] <= scale["average"] <= scale["maximum"]):
        result["message"] = "Stable scale readings unavailable. Removal remains unconfirmed."
        return result
    # Check both extremes, including negative tare/zero drift. No rounded UI values.
    tolerance = settings.get("zero_tolerance_g", .01)
    spread = settings.get("max_spread_g", .02)
    if (not finite(tolerance) or tolerance <= 0 or not finite(spread) or spread <= 0):
        result["message"] = "Invalid scale limits; check Engineering settings."
        return result
    if max(abs(scale["minimum"]), abs(scale["maximum"])) > tolerance or scale["range"] > spread:
        result.update(state="occupied_or_drift", message="Item may still be present, or zero has drifted. Remove it; do not tare over it.")
        return result
    if vision_enabled:
        if camera_error or not isinstance(detection, dict):
            result["message"] = "Camera/model unavailable. Removal remains unconfirmed; retry Live."
            return result
        age = detection.get("capture_age_ms")
        count = detection.get("count")
        if not finite(age) or not 0 <= age <= 5000 or not finite(count) or count < 0:
            result["message"] = "Fresh detection evidence unavailable. Retry Live."
            return result
        if count > 0:
            result.update(state="object_present", message="Object still detected. Remove every item before continuing.")
            return result
    result.update(ready_for_confirmation=True, state="clear_evidence",
        message="Scale is near zero; no coin/bar detected in ROI. Visually check the entire pan and confirm." if vision_enabled else
                "Scale is near zero. YOLO is off; visually check the entire pan and confirm.")
    if camera_error and not vision_enabled:
        result["message"] += " Camera unavailable; inspect the physical pan directly."
    return result
