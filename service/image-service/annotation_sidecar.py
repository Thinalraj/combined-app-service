"""VISUAL-01: normalized overlay geometry; never changes measurement results.
Class IDs belong to this export only: 0 Ring, 1 Coin, 2 Bar, 3 Bangle.
YOLO detection TXT stores class/cx/cy/w/h; JSON additionally preserves holes.
"""
import cv2

CLASS_NAMES = ["Ring", "Coin", "Bar", "Bangle"]


def build_annotation(image, result, contours, capture_id):
    height, width = image.shape[:2]
    shape = str(result.get("type", "")).title()
    objects = []
    if shape in CLASS_NAMES and contours and contours[0] is not None:
        outer = contours[0]
        x, y, w, h = cv2.boundingRect(outer)
        polygons = []
        for i, contour in enumerate(contours):
            if contour is None:
                continue
            # Subpixel display approximation only; measurement keeps original contours.
            contour = cv2.approxPolyDP(contour, 0.5, True)
            polygons.append({"role": "outer" if i == 0 else "hole",
                "points": [[round(float(px) / width, 7), round(float(py) / height, 7)]
                           for px, py in contour.reshape(-1, 2)]})
        objects.append({"class_id": CLASS_NAMES.index(shape), "label": shape,
            "bbox_xywhn": [(x + w / 2) / width, (y + h / 2) / height, w / width, h / height],
            "polygons": polygons})
    return {"schema": "thinal-overlay-v1", "capture_id": capture_id,
        "image": {"width": width, "height": height, "scope": "measurement AOI crop"},
        "coordinate_system": "normalized_0_1", "classes": CLASS_NAMES,
        "source": "OpenCV geometry, not YOLO inference", "objects": objects,
        "measurement": result}
