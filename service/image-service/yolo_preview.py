"""YOLO-01: coin/bar segmentation without modifying the input image.

Only local .pt files are loaded; no model download or training is started.
Masks describe image pixels, not physical area/volume or gold purity.
Offline checker: py yolo_preview.py --model PATH --image PHOTO
Live checker: py yolo_preview.py --model PATH (uses Image service on 8003)
Add --headless to print JSON. GUI: Q/Esc quit. No scale or signal API is called.
API reference: https://docs.ultralytics.com/modes/predict/
"""
import math
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vision_settings import validate_settings, revision
from system_assets import asset_path
from coin_hole_guard import visible_hole_ratio


class VisionError(RuntimeError):
    pass


def array(value):
    import numpy as np
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


class Segmenter:
    def __init__(self, factory=None):
        self.factory = factory
        self.lock = threading.Lock()
        self.model = None
        self.key = None
        self.names = None

    def _load(self, settings):
        path = asset_path(settings["model_path"], ".pt")
        if not path.is_file():
            raise VisionError("Segmentation .pt file not found: " + str(path))
        stat = path.stat()
        key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
        if self.key == key and self.model is not None:
            return
        try:
            if self.factory is None:
                from ultralytics import YOLO
                factory = YOLO
            else:
                factory = self.factory
            model = factory(str(path))
            if model.task != "segment":
                raise VisionError("Use segmentation weights, not detection/classification weights")
            names = model.names
            names = dict(enumerate(names)) if isinstance(names, list) else names
            names = {int(k): str(v).strip().lower() for k, v in names.items()}
            if set(names.values()) != {"coin", "bar"} or len(names) != 2:
                raise VisionError("This workflow requires exactly the coin and bar classes")
            self.model, self.names, self.key = model, names, key
        except ImportError as exc:
            raise VisionError("Install ultralytics in the Image service's Python environment") from exc
        except VisionError:
            raise
        except Exception as exc:
            raise VisionError("Could not load segmentation weights: " + str(exc)) from exc

    def validate(self, values):
        settings = validate_settings(values)
        if not self.lock.acquire(blocking=False):
            raise VisionError("YOLO is busy; wait for the active frame")
        try:
            self._load(settings)
            return {"ok": True, "task": "segment", "model_classes": self.names,
                    "revision": revision(settings)}
        finally:
            self.lock.release()

    def predict(self, image, values, mask_callback=None):
        import cv2
        import numpy as np
        settings = validate_settings(values)
        if not settings["enabled"]:
            raise VisionError("YOLO is disabled in Engineering")
        if not self.lock.acquire(blocking=False):
            raise VisionError("YOLO is busy; wait for the active frame")
        started = time.monotonic()
        try:
            self._load(settings)
            height, width = image.shape[:2]
            x, y, w, h = settings["roi"]
            x1, y1 = int(x * width), int(y * height)
            x2, y2 = min(width, math.ceil((x + w) * width)), min(height, math.ceil((y + h) * height))
            if x2 - x1 < 2 or y2 - y1 < 2:
                raise VisionError("ROI is too small at this camera resolution")
            crop = image[y1:y2, x1:x2].copy()
            # Keep low-score candidates for counting, then apply the separate 80% acceptance gate.
            result = self.model.predict(source=crop, conf=settings["detection_confidence"],
                imgsz=settings["imgsz"], device="cpu", retina_masks=True,
                save=False, verbose=False, max_det=16, agnostic_nms=True)[0]
            boxes = result.boxes
            scores = array(boxes.conf).reshape(-1) if boxes is not None else np.empty(0)
            classes = array(boxes.cls).reshape(-1) if boxes is not None else np.empty(0)
            rectangles = array(boxes.xyxy) if boxes is not None else np.empty((0, 4))
            masks = array(result.masks.data) if result.masks is not None else None
            if len(scores) and (masks is None or masks.shape != (len(scores), y2 - y1, x2 - x1)):
                raise VisionError("Segmentation mask is absent or not aligned to the ROI image")
            objects = []
            for index, score in enumerate(scores):
                score = float(score)
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise VisionError("Model returned an invalid confidence")
                if score < settings["detection_confidence"]:
                    continue
                model_class = int(classes[index])
                label = self.names.get(model_class)
                if label is None:
                    raise VisionError("Model returned an unknown class ID")
                mask = (masks[index] > .5).astype(np.uint8) * 255
                area = int(np.count_nonzero(mask))
                edge = bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())
                accepted = score >= settings["acceptance_confidence"] and area >= 16 and not edge
                # NUC-03: veto a coin-like prediction with a large visible hole.
                # This does not relabel it as a scientifically confirmed bangle.
                hole_ratio = visible_hole_ratio(crop, mask) if label == "coin" else 0.0
                hole_veto = hole_ratio >= .12
                accepted = accepted and not hole_veto
                contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
                polygons = []
                for j, contour in enumerate(contours):
                    points = cv2.approxPolyDP(contour, 1.0, True).reshape(-1, 2)
                    if len(points) < 3:
                        continue
                    polygons.append({"role": "outer" if hierarchy[0][j][3] == -1 else "hole",
                        "points": [[min(1., max(0., (float(px) + x1) / width)),
                                    min(1., max(0., (float(py) + y1) / height))] for px, py in points]})
                accepted = accepted and any(p["role"] == "outer" for p in polygons)
                bx1, by1, bx2, by2 = [float(v) for v in rectangles[index]]
                if not all(math.isfinite(v) for v in (bx1, by1, bx2, by2)) or bx2 <= bx1 or by2 <= by1:
                    raise VisionError("Model returned an invalid box")
                bx1, bx2 = max(0., bx1 + x1), min(float(width), bx2 + x1)
                by1, by2 = max(0., by1 + y1), min(float(height), by2 + y1)
                if bx2 <= bx1 or by2 <= by1:
                    raise VisionError("Box lies outside the image")
                if mask_callback is not None:
                    mask_callback(index, mask, (x1, y1))
                objects.append({"label": label if accepted else "unknown", "predicted_label": label,
                    "confidence": score, "accepted": accepted, "touches_roi_edge": edge,
                    "visible_hole_ratio": round(hole_ratio,4), "visible_hole_veto": hole_veto,
                    "mask_area_px": area, "model_class_id": model_class,
                    # Canonical export order stays bar=0, coin=1 even if the model's order differs.
                    "class_id": {"bar": 0, "coin": 1}[label] if accepted else None,
                    "bbox_xywhn": [(bx1 + bx2) / (2 * width), (by1 + by2) / (2 * height),
                                   (bx2 - bx1) / width, (by2 - by1) / height], "polygons": polygons})
            count = len(objects)
            eligible = count == 1 and objects[0]["accepted"]
            if count == 0:
                state, message = "no_objects", "No coin/bar detected in ROI"
            elif count > 1:
                state, message = "multiple_objects", f"Multiple objects detected ({count}) in ROI"
            elif objects[0]["touches_roi_edge"]:
                state, message = "roi_edge", "Move the complete item inside the ROI"
            elif objects[0].get("visible_hole_veto"):
                state, message = "unknown", "Visible central hole: inspect bangle/ring-like item and choose manually"
            elif not eligible:
                state, message = "unknown", "Unknown: confidence or mask quality below acceptance limit"
            else:
                state, message = "single_object", objects[0]["label"].title() + " detected"
            detection = {"state": state, "message": message, "count": count, "eligible": eligible,
                "label": objects[0]["label"] if count == 1 else "unknown",
                "confidence": objects[0]["confidence"] if count == 1 else None,
                "bbox_xywhn": objects[0]["bbox_xywhn"] if count == 1 else None,
                "revision": revision(settings), "roi_xywhn": settings["roi"],
                "inference_ms": round((time.monotonic() - started) * 1000, 1),
                "scope": "coin/bar model detections within ROI; zero detections do not prove an empty pan"}
            return objects, detection
        except (VisionError, ValueError):
            raise
        except Exception as exc:
            raise VisionError("YOLO inference failed: " + str(exc)) from exc
        finally:
            self.lock.release()


def main():
    import argparse
    import base64
    import json
    import urllib.request
    import cv2
    import numpy as np
    parser = argparse.ArgumentParser(description="Coin/bar segmentation checker; camera/image only")
    parser.add_argument("--model", required=True, help=".pt path relative to the project system_assets folder")
    parser.add_argument("--image", help="Offline local photo; no camera/services needed")
    parser.add_argument("--url", default="http://127.0.0.1:8003")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    settings = validate_settings({"enabled": True, "model_path": args.model})
    detector = Segmenter() if args.image else None
    try:
        for _ in range(1 if args.image else max(1, args.count)):
            if args.image:
                raw = cv2.imread(args.image)
                if raw is None:
                    raise ValueError("Could not read input photo")
                objects, detection = detector.predict(raw, settings)
            else:
                request = urllib.request.Request(args.url.rstrip("/") + "/yolo/frame",
                    data=json.dumps({"settings": settings}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request, timeout=40) as response:
                    bundle = json.load(response)
                detection, objects = bundle["detection"], bundle["annotation"]["objects"]
                raw = cv2.imdecode(np.frombuffer(base64.b64decode(bundle["raw_jpeg_base64"]), np.uint8), cv2.IMREAD_COLOR)
            print(json.dumps(detection, indent=2), flush=True)
            if not args.headless:
                display = raw.copy()
                height, width = display.shape[:2]
                for obj in objects:
                    for polygon in obj["polygons"]:
                        points = np.array([[int(x * width), int(y * height)] for x, y in polygon["points"]], np.int32)
                        cv2.polylines(display, [points], True, (0, 255, 0), 2)
                cv2.putText(display, detection["message"], (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
                cv2.namedWindow("YOLO checker", cv2.WINDOW_NORMAL)
                cv2.imshow("YOLO checker", display)
                if cv2.waitKey(0 if args.image else 200) & 0xFF in (27, ord("q")):
                    break
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        parser.exit(1, f"YOLO checker: {exc}\n")
    finally:
        if not args.headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
