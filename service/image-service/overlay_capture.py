"""PHOTO-01: clean camera image plus same-frame, unreviewed OpenCV overlays.

These polygons are suggestions, not YOLO inference or verified training labels.
Mask/depth measurements are deliberately left to the existing measurement code.
"""
import base64
from datetime import datetime, timezone
import uuid

import cv2


def build_bundle(image, shape, mask=None, warning=None, measurement=None):
    height, width = image.shape[:2]
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise ValueError("Could not encode camera photograph")
    objects = []
    if mask is not None:
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is not None:
            for i, contour in enumerate(contours):
                if hierarchy[0][i][3] != -1 or cv2.contourArea(contour) < 100:
                    continue
                selected = [("outer", contour)]
                child = hierarchy[0][i][2]
                while child != -1:
                    if cv2.contourArea(contours[child]) >= 20:
                        selected.append(("hole", contours[child]))
                    child = hierarchy[0][child][0]
                polygons = []
                for role, points in selected:
                    points = cv2.approxPolyDP(points, 0.5, True).reshape(-1, 2)
                    if len(points) >= 3:
                        polygons.append({"role": role, "points": [
                            [round(float(x) / width, 7), round(float(y) / height, 7)]
                            for x, y in points]})
                if not polygons:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                # Export mapping for this coin/bar project only; other shapes have no YOLO ID.
                label = str(shape).strip().lower()
                objects.append({"label": label,
                    "class_id": {"bar": 0, "coin": 1}.get(label),
                    "bbox_xywhn": [(x + w / 2) / width, (y + h / 2) / height, w / width, h / height],
                    "polygons": polygons})
    annotation = {"schema": "thinal-overlay-v1", "capture_id": uuid.uuid4().hex,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "coordinate_system": "normalized_0_1", "classes": ["bar", "coin"],
        "image": {"width": width, "height": height, "scope": "camera frame"},
        "source": "OpenCV background mask; not YOLO inference",
        "label_source": "operator-selected shape", "annotation_status": "auto_unreviewed",
        "warning": warning, "objects": objects, "measurement": measurement or {"type": shape}}
    return {"raw_jpeg_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
            "annotation": annotation}
