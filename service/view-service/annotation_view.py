"""VISUAL-01: render saved/live JSON geometry above an unchanged raw image.
No external libraries, remote assets, or executable annotation content.
"""
import base64
import html
import math


def decode_bundle(bundle):
    annotation = bundle.get("annotation", {})
    if annotation.get("schema") != "thinal-overlay-v1":
        raise ValueError("Unsupported annotation schema")
    data = base64.b64decode(bundle["raw_jpeg_base64"], validate=True)
    if not data.startswith(b"\xff\xd8") or not 0 < len(data) <= 20 * 1024 * 1024:
        raise ValueError("Invalid raw JPEG")
    return data, annotation


def yolo_text(annotation):
    return "".join(str(int(obj["class_id"])) + " " +
        " ".join(f"{float(v):.7f}" for v in obj["bbox_xywhn"]) + "\n"
        for obj in annotation.get("objects", []))


def viewer_html(annotation, image_src):
    shapes = []
    for obj in annotation.get("objects", []):
        for polygon in obj.get("polygons", []):
            points = []
            for x, y in polygon["points"]:
                if not all(math.isfinite(float(v)) and 0 <= float(v) <= 1 for v in (x, y)):
                    raise ValueError("Invalid normalized coordinates")
                points.append(f"{float(x)*1000:.4f},{float(y)*1000:.4f}")
            color = "#22d3ee" if polygon["role"] == "hole" else "#22c55e"
            shapes.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/>')
        cx, cy, w, h = [float(v)*1000 for v in obj["bbox_xywhn"]]
        shapes.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" fill="none" stroke="#fbbf24" stroke-width="1" stroke-dasharray="5 3" vector-effect="non-scaling-stroke"/>')
    result = annotation.get("measurement", {})
    caption = str(result.get("message") or result.get("type") or "Detection")
    if result.get("geometry_ok"):
        caption = f"Inner {result['inner_diameter_mm']:.2f} / Outer {result['outer_diameter_mm']:.2f} mm"
    elif result.get("diameter_mm") is not None:
        caption = f"Diameter {result['diameter_mm']:.2f} mm"
    elif result.get("width_mm") is not None:
        caption = f"Width {result['width_mm']:.2f} / Length {result['length_mm']:.2f} mm"
    dimensions = annotation.get("image", {})
    ratio = float(dimensions.get("width", 4)) / float(dimensions.get("height", 3))
    if not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("Invalid image dimensions")
    # CSS checkbox toggles overlays without scripts, including under file://.
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raw image and annotation</title><style>
*{box-sizing:border-box}body{margin:0;padding:8px;background:#111827;color:#fff;font:13px Arial}
label{display:inline-block;margin-bottom:6px} .frame{position:relative;width:min(100%,calc((100vh - 70px) * ''' + str(ratio) + '''));margin:0 auto;line-height:0}
img{width:100%;height:auto;display:block}svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
#overlay:not(:checked)~.frame svg{display:none}p{margin:6px 0;line-height:1.3;overflow-wrap:anywhere}
</style><body><input id="overlay" type="checkbox" checked><label for="overlay"> Show annotation</label>
<div class="frame"><img alt="Unannotated measurement image" src="''' + html.escape(image_src, quote=True) + '''">
<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label="Detection overlay">''' + ''.join(shapes) + '''</svg></div><p>''' + html.escape(caption) + '''</p></body></html>'''
