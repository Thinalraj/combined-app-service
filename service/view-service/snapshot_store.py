"""PHOTO-01: persist raw photos and separate annotation files; never burn overlays in.

Automatic outlines must be reviewed before training. A saved user verification
photo is evidence of appearance, not a known material/purity training label.
"""
import copy
import json
import os
from pathlib import Path
import uuid

from flask import Response, abort, send_from_directory
from annotation_view import decode_bundle, viewer_html


def save_snapshot(bundle, directory, url_prefix, phase):
    raw, annotation = decode_bundle(bundle)
    annotation = copy.deepcopy(annotation)
    capture_id = uuid.uuid4().hex
    stem = "IMG-" + capture_id
    annotation["image"]["filename"] = stem + ".jpg"
    annotation["storage_id"] = capture_id
    annotation["capture_phase"] = phase
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    files = {stem + ".jpg": raw,
        stem + ".html": viewer_html(annotation, stem + ".jpg").encode("utf-8")}
    # Coin/bar YOLO segmentation suggestions only. Holes cannot be represented
    # faithfully by a simple YOLO polygon, so those objects are not exported.
    rows = []
    for obj in annotation.get("objects", []):
        polygons = obj.get("polygons", [])
        if obj.get("class_id") not in (0, 1) or any(p["role"] == "hole" for p in polygons):
            continue
        for polygon in polygons:
            if polygon["role"] == "outer":
                values = [str(obj["class_id"])]
                values += [f"{float(v):.7f}" for point in polygon["points"] for v in point]
                rows.append(" ".join(values))
    if rows:
        files[stem + ".txt"] = ("\n".join(rows) + "\n").encode("ascii")
    # JSON is written last as the completed snapshot's manifest.
    files[stem + ".json"] = json.dumps(annotation, indent=2, allow_nan=False).encode("utf-8")
    written = []
    try:
        for name, content in files.items():
            temporary = directory / (name + ".tmp")
            written.append(temporary)
            temporary.write_bytes(content)
            target = directory / name
            os.replace(temporary, target)
            written.append(target)
    except OSError:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    prefix = url_prefix.rstrip("/") + "/" + stem
    return {"capture_id": annotation["capture_id"], "storage_id": capture_id,
        "captured_at": annotation.get("captured_at"), "capture_phase": phase,
        "annotation_status": "auto_unreviewed", "image_url": prefix + ".jpg",
        "overlay_url": prefix + ".html", "annotation_url": prefix + ".json",
        "yolo_segmentation_url": prefix + ".txt" if rows else None,
        "annotation_warning": annotation.get("warning")}


def serve_snapshot(directory, filename):
    if filename != Path(filename).name or Path(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".html", ".json", ".txt"}:
        abort(404)
    directory = Path(directory)
    if filename.endswith(".html") and not (directory / filename).exists():
        sidecar = (directory / filename).with_suffix(".json")
        if sidecar.exists():
            annotation = json.loads(sidecar.read_text(encoding="utf-8"))
            image_name = Path(str(annotation["image"]["filename"])).name
            return Response(viewer_html(annotation, image_name), mimetype="text/html",
                            headers={"Cache-Control": "no-store"})
        # Older records may contain only a pre-annotated JPEG.
        for suffix in (".jpg", ".jpeg", ".png"):
            legacy = (directory / filename).with_suffix(suffix)
            if legacy.exists():
                return send_from_directory(directory, legacy.name)
    response = send_from_directory(directory, filename)
    response.headers["Cache-Control"] = "no-store"
    return response
