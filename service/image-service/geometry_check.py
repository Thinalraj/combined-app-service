"""GEOMETRY-01: plane-referenced coin/bar estimates; no scale/signal commands.

SDK rays account for the reported distortion model. Mask-cell integration keeps
holes; all dimensions use mm, volume mm^3. This is a flat-prism approximation,
not a 3D mesh, microscopic contact area or purity determination.
"""
import hashlib
import json
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import system_assets as assets

DEFAULTS = {"samples": 5, "max_plane_rms_mm": 1.5, "min_valid_fraction": .8,
            "max_area_cv_pct": 3., "min_resolvable_height_mm": 1.,
            "max_height_std_mm": .3, "max_reference_shift_mm": 1.,
            "pure_gold_density_g_cm3": 19.32, "density_tolerance_pct": 10.}


def settings(values=None):
    values = assets.read_json("geometry_settings.json", DEFAULTS) if values is None else values
    if not isinstance(values, dict) or set(values) - set(DEFAULTS):
        raise ValueError("Unexpected geometry settings")
    result = {**DEFAULTS, **values}
    if isinstance(result["samples"], bool) or result["samples"] not in (3, 5, 7):
        raise ValueError("Use 3, 5 or 7 frames")
    bounds = {"max_plane_rms_mm": (.1, 3), "min_valid_fraction": (.8, 1),
        "max_area_cv_pct": (.1, 10), "min_resolvable_height_mm": (.5, 10),
        "max_height_std_mm": (.05, 2), "max_reference_shift_mm": (.1, 3),
        "pure_gold_density_g_cm3": (15, 22), "density_tolerance_pct": (1, 30)}
    for key, (low, high) in bounds.items():
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
    return result


def fingerprint(report):
    # Moving/restarting the camera still needs a new reference: session is checked separately.
    data = {"serial": report["device"].get("serial_number"),
            "intrinsics": report["aligned_depth"], "depth_unit_m": report["depth_unit_m"]}
    if not data["serial"] or not isinstance(data["depth_unit_m"], (int, float)) or not 0 < data["depth_unit_m"] < .1:
        raise ValueError("Camera identity/depth scale unavailable")
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def roi_mask(shape, roi):
    import numpy as np
    h, w = shape
    x, y, rw, rh = roi
    result = np.zeros(shape, np.uint8)
    result[int(y*h):min(h, math.ceil((y+rh)*h)), int(x*w):min(w, math.ceil((x+rw)*w))] = 1
    return result


def cloud(depth, report, mask, rays, config):
    import numpy as np
    if depth.shape != mask.shape:
        raise ValueError("Depth and mask are not aligned")
    stride = max(2, math.ceil(math.sqrt(max(1, int(mask.sum())) / 1800)))
    ys, xs = np.mgrid[0:depth.shape[0]:stride, 0:depth.shape[1]:stride]
    chosen = mask[ys, xs] > 0
    xs, ys = xs[chosen], ys[chosen]
    z = depth[ys, xs].astype(float) * report["depth_unit_m"] * 1000
    valid = np.isfinite(z) & (z >= 100) & (z <= 2000)
    if len(z) < 100 or valid.mean() < config["min_valid_fraction"]:
        raise ValueError("Insufficient valid depth in the selected region")
    pixels = np.column_stack((xs[valid], ys[valid]))
    points = rays(pixels) * z[valid, None]
    if not np.isfinite(points).all():
        raise ValueError("Invalid deprojected depth")
    return points, float(valid.mean())


def fit_plane(points, config):
    import numpy as np
    selected = points
    for _ in range(4):
        centre = selected.mean(axis=0)
        _, singular, vh = np.linalg.svd(selected - centre, full_matrices=False)
        if singular[1] < 1:
            raise ValueError("Reference region is too small or degenerate")
        normal = vh[-1]
        if normal[2] > 0:
            normal = -normal
        offset = -float(normal @ centre)
        residual = points @ normal + offset
        median = np.median(residual)
        sigma = 1.4826 * np.median(np.abs(residual - median))
        keep = np.abs(residual - median) <= max(.2, 3*sigma)
        if keep.mean() < .8 or keep.sum() < 100:
            raise ValueError("Reference region is not a sufficiently flat support surface")
        selected = points[keep]
    rms = float(np.sqrt(np.mean((selected @ normal + offset)**2)))
    if rms > config["max_plane_rms_mm"] or -normal[2] < math.cos(math.radians(15)):
        raise ValueError("Support plane is too noisy or tilted; use a flat, near-overhead view")
    return {"normal": normal.tolist(), "offset_mm": offset, "rms_mm": rms}


def plane_distance(points, plane):
    import numpy as np
    return points @ np.asarray(plane["normal"]) + plane["offset_mm"]


def mask_area(mask, plane, height_mm, rays):
    """Integrate pixel coverage over projected 3D quadrilateral cells (max ~2100).

    Grid cells are weighted by the exact number of foreground pixels, including
    holes. Variation inside a cell is approximated; no missing depth is filled.
    """
    import numpy as np
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("Empty segmentation mask")
    left, right, top, bottom = xs.min(), xs.max()+1, ys.min(), ys.max()+1
    stride = max(2, math.ceil(math.sqrt((right-left)*(bottom-top)/2000)))
    xx = np.unique(np.r_[np.arange(left, right, stride), right])
    yy = np.unique(np.r_[np.arange(top, bottom, stride), bottom])
    x0, y0 = np.meshgrid(xx[:-1], yy[:-1]);x1, y1 = np.meshgrid(xx[1:], yy[1:])
    integral = np.pad(mask.astype(np.int64).cumsum(0).cumsum(1), ((1,0),(1,0)))
    count = integral[y1,x1]-integral[y0,x1]-integral[y1,x0]+integral[y0,x0]
    used = count > 0
    x0,y0,x1,y1,count = [v[used] for v in (x0,y0,x1,y1,count)]
    corners = np.stack([np.column_stack((x0-.5,y0-.5)),np.column_stack((x1-.5,y0-.5)),
                        np.column_stack((x1-.5,y1-.5)),np.column_stack((x0-.5,y1-.5))],axis=1)
    directions = rays(corners.reshape(-1,2)).reshape(-1,4,3)
    normal = np.asarray(plane["normal"])
    denominator = directions @ normal
    distance = (height_mm - plane["offset_mm"]) / denominator
    if not np.isfinite(distance).all() or (distance <= 0).any():
        raise ValueError("Reference plane does not intersect the camera rays")
    p = directions * distance[:,:,None]
    areas = (np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
             + np.linalg.norm(np.cross(p[:,2]-p[:,0],p[:,3]-p[:,0]),axis=1))/2
    result = float(np.sum(areas * count / ((x1-x0)*(y1-y0))))
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Invalid projected area")
    return result


def box_iou(a,b):
    def bounds(v):return [v[0]-v[2]/2,v[1]-v[3]/2,v[0]+v[2]/2,v[1]+v[3]/2]
    x,y=bounds(a),bounds(b)
    intersection=max(0,min(x[2],y[2])-max(x[0],y[0]))*max(0,min(x[3],y[3])-max(x[1],y[1]))
    return intersection/max(1e-12,a[2]*a[3]+b[2]*b[3]-intersection)


class Geometry:
    def __init__(self):
        self.session = uuid.uuid4().hex

    def calibrate(self, capture, rays_factory, roi, empty_confirmed):
        import numpy as np
        if empty_confirmed is not True:
            raise ValueError("Remove all items and confirm the support surface is empty")
        config=settings();planes=[];signature=None;reference_point=None
        for _ in range(config["samples"]):
            _,depth,report=capture();current=fingerprint(report)
            if signature is not None and signature != current:
                raise ValueError("Camera configuration changed during calibration")
            signature=current;rays=rays_factory(report)
            points,_=cloud(depth,report,roi_mask(depth.shape,roi),rays,config)
            planes.append(fit_plane(points,config));reference_point=np.median(points,axis=0)
        normal=np.mean([p["normal"] for p in planes],axis=0);normal/=np.linalg.norm(normal)
        offset=float(np.mean([p["offset_mm"] for p in planes]))
        if np.std([float(plane_distance(reference_point,p)) for p in planes]) > config["max_height_std_mm"]:
            raise ValueError("Reference depth is changing; keep the camera and support still")
        result={"reference_id":uuid.uuid4().hex,"session":self.session,"fingerprint":signature,"roi":roi,
                "created_at":datetime.now(timezone.utc).isoformat(),"samples":config["samples"],
                "plane":{"normal":normal.tolist(),"offset_mm":offset,"rms_mm":max(p["rms_mm"] for p in planes)}}
        assets.write_json(assets.ROOT/"geometry_reference.json",result)
        return {"ok":True,**result}

    def measure(self, capture, rays_factory, detector, vision, shape, manual_height_mm=None):
        import numpy as np
        import cv2
        config=settings()
        if shape not in ("coin","bar") or not vision["enabled"]:
            raise ValueError("Enable a validated coin/bar YOLO model first")
        manual=manual_height_mm
        if manual is not None and (isinstance(manual,bool) or not isinstance(manual,(int,float)) or not math.isfinite(manual) or not 0 < manual <= 50):
            raise ValueError("Known thickness must be a number greater than 0 and at most 50 mm")
        reference=assets.read_json("geometry_reference.json",{})
        if reference.get("session") != self.session or reference.get("roi") != vision["roi"]:
            raise ValueError("Capture an empty-support reference in Engineering after camera startup or ROI change")
        detector.validate(vision)  # Warm/load before taking measurement frames.
        frames=[];previous=None
        for _ in range(config["samples"]):
            image,depth,report=capture();started=time.monotonic()
            if fingerprint(report) != reference["fingerprint"]:
                raise ValueError("Camera identity, intrinsics or depth scale changed; recalibrate")
            rays=rays_factory(report);masks=[]
            def receive(index,local,origin):
                full=np.zeros(depth.shape,np.uint8);x,y=origin
                full[y:y+local.shape[0],x:x+local.shape[1]]=(local>0).astype(np.uint8);masks.append(full)
            _,d=detector.predict(image,vision,mask_callback=receive)
            if not d["eligible"] or d["count"] != 1 or d["label"] != shape or len(masks) != 1:
                raise ValueError(d.get("message","One accepted object required"))
            if time.monotonic()-started > 5:
                raise ValueError("Detection too slow for a fresh geometry frame")
            if previous and box_iou(previous["bbox_xywhn"],d["bbox_xywhn"]) < .6:
                raise ValueError("Object moved during measurement; keep it still and retry")
            previous=d;mask=masks[0]
            background=roi_mask(depth.shape,vision["roi"])
            background[cv2.dilate(mask,np.ones((11,11),np.uint8))>0]=0
            points,_=cloud(depth,report,background,rays,config);plane=fit_plane(points,config)
            shifts=plane_distance(points,reference["plane"])
            angle=float(np.dot(plane["normal"],reference["plane"]["normal"]))
            if abs(float(np.median(shifts))) > config["max_reference_shift_mm"] or angle < math.cos(math.radians(.5)):
                raise ValueError("Support/camera reference changed; remove item and recalibrate")
            height=None;warning=None
            if manual is None:
                try:
                    inner=cv2.erode(mask,np.ones((5,5),np.uint8))
                    top_points,valid=cloud(depth,report,inner,rays,config)
                    values=plane_distance(top_points,plane);height=float(np.median(values))
                    noise=float(1.4826*np.median(np.abs(values-height)))
                    threshold=max(config["min_resolvable_height_mm"],3*max(.2,report["depth_unit_m"]*1000,noise,plane["rms_mm"],reference["plane"]["rms_mm"]))
                    if not threshold < height <= 50:
                        raise ValueError("Height is too small/noisy to resolve reliably; enter known thickness")
                except ValueError as exc:height=None;warning=str(exc)
            frames.append({"mask":mask,"plane":plane,"rays":rays,"height":height,"warning":warning,
                           "confidence":d["confidence"],"captured_at":report["captured_at"]})
        heights=[frame["height"] for frame in frames if frame["height"] is not None]
        usable=manual is not None or (len(heights)==len(frames) and float(np.std(heights))<=config["max_height_std_mm"])
        areas=[];volumes=[]
        for frame in frames:
            height=manual if manual is not None else frame["height"] if usable else 0.
            area=mask_area(frame["mask"],frame["plane"],height,frame["rays"]);areas.append(area)
            if usable:volumes.append(area*height)
        cv=float(np.std(areas)/np.mean(areas)*100)
        if cv > config["max_area_cv_pct"]:
            raise ValueError("Area changed too much between frames; keep item still and retry")
        warnings=[frame["warning"] for frame in frames if frame["warning"]]
        if not usable:warnings.append("Volume unavailable; use a known manual thickness")
        result={"schema":"thinal-geometry-v1","ok":True,"shape":shape,"samples":len(frames),
            "reference_id":reference["reference_id"],"reference_created_at":reference["created_at"],
            "camera_fingerprint":reference["fingerprint"],"vision_revision":d["revision"],
            "area_mm2":float(np.mean(areas)),"area_std_mm2":float(np.std(areas)),"area_cv_pct":cv,
            "area_reference":"top_plane" if usable else "support_plane_projection",
            "height_mm":float(manual if manual is not None else np.mean(heights)) if usable else None,
            "height_std_mm":0. if manual is not None else float(np.std(heights)) if usable else None,
            "height_source":"manual_known" if manual is not None else "depth_above_support" if usable else "unavailable",
            "volume_mm3":float(np.mean(volumes)) if usable else None,
            "volume_std_mm3":float(np.std(volumes)) if usable else None,
            "confidence_min":min(frame["confidence"] for frame in frames),
            "first_frame_at":frames[0]["captured_at"],"last_frame_at":frames[-1]["captured_at"],
            "warnings":list(dict.fromkeys(warnings)),"settings":config,
            "assumptions":"Flat coin/bar; uniform thickness; estimated projected footprint, not microscopic contact area. Density does not determine purity."}
        return result


def sdk_rays_factory(rs, report):
    """SDK deprojection preserves the reported lens model; unsupported models fail."""
    import numpy as np
    data=report["aligned_depth"];intr=rs.intrinsics()
    intr.width=data["width"];intr.height=data["height"];intr.fx=data["fx_px"];intr.fy=data["fy_px"]
    intr.ppx=data["ppx_px"];intr.ppy=data["ppy_px"];intr.coeffs=data["distortion_coefficients"]
    model_name=data["distortion_model"].split(".")[-1]
    if model_name == "modified_brown_conrady":
        raise ValueError("SDK deprojection does not support this modified Brown-Conrady profile")
    intr.model=getattr(rs.distortion,model_name)
    def rays(pixels):
        try:return np.array([rs.rs2_deproject_pixel_to_point(intr,[float(x),float(y)],1.) for x,y in pixels],dtype=float)
        except (RuntimeError,AttributeError) as exc:raise ValueError("SDK cannot deproject this camera profile") from exc
    return rays


if __name__ == "__main__":
    import argparse
    import urllib.request
    parser=argparse.ArgumentParser(description="Geometry-only checker; Image service must be running")
    parser.add_argument("--url",default="http://127.0.0.1:8003")
    parser.add_argument("--shape",choices=["coin","bar"],required=True)
    parser.add_argument("--height-mm",type=float)
    args=parser.parse_args()
    from vision_settings import load_settings
    body={"settings":load_settings(assets.ROOT/"vision_settings.json"),"shape":args.shape,"manual_height_mm":args.height_mm}
    request=urllib.request.Request(args.url.rstrip("/")+"/geometry/measure",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(request,timeout=180) as response:print(json.dumps(json.load(response),indent=2))
    except Exception as exc:parser.exit(1,"Geometry checker: "+str(exc)+"\n")
