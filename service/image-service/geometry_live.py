"""NUC-02: same-frame segmentation metrology using a visible support plane.

No empty reference is created with an item present. A prior reference is optional;
fresh, flat, repeatable background depth defines height. Without it, top-surface
depth can define area, but height/volume need known manual thickness. Without
either calibrated plane, only pixel-mask evidence is returned (never box mm).
"""
import math
import time
import numpy as np
import cv2
from geometry_check import (settings, fingerprint, roi_mask, cloud, fit_plane,
                            plane_distance, mask_area, box_iou)
from overlay_capture import build_bundle
import system_assets as assets


def dimensions(mask, plane, height, rays, shape, area):
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    boundary=np.concatenate([c[:,0] for c in contours]).astype(float)
    boundary=boundary[::max(1,math.ceil(len(boundary)/1500))]
    directions=rays(boundary)
    normal=np.asarray(plane["normal"])
    distance=(height-plane["offset_mm"])/(directions@normal)
    points=directions*distance[:,None]
    # A 2-D basis IN the support plane, not the camera's tilted image axes.
    axis=np.cross(normal,[0.,1.,0.]);axis/=np.linalg.norm(axis)
    other=np.cross(normal,axis)
    projected=np.column_stack((points@axis,points@other)).astype(np.float32)
    _,(a,b),_=cv2.minAreaRect(projected)
    if shape=="coin":
        diameter=2*math.sqrt(area/math.pi)
        return {"width_mm":diameter,"length_mm":diameter,"diameter_mm":diameter,
                "method":"equivalent diameter from physical segmentation area"}
    return {"width_mm":min(a,b),"length_mm":max(a,b),"diameter_mm":None,
            "method":"minimum rotated rectangle around projected mask boundary"}


def measure_live(engine,capture,rays_factory,detector,vision,shape,manual=None):
    config=settings()
    if shape not in ("coin","bar") or not vision["enabled"]:
        raise ValueError("Enable a validated coin/bar segmentation model first")
    if manual is not None and (isinstance(manual,bool) or not isinstance(manual,(int,float)) or not math.isfinite(manual) or not 0<manual<=50):
        raise ValueError("Known thickness must be greater than 0 and at most 50 mm")
    detector.validate(vision)  # Warm the model before capturing measurement pixels.
    reference=assets.read_json("geometry_reference.json",{})
    frames=[];signature=None;previous=None;objects=[];last_image=None
    for _ in range(config["samples"]):
        image,depth,report=capture();started=time.monotonic()
        current=fingerprint(report)
        if signature is not None and current!=signature:raise ValueError("Camera profile changed during measurement")
        signature=current;masks=[];rays=rays_factory(report)
        def receive(index,local,origin):
            full=np.zeros(depth.shape,np.uint8);x,y=origin
            full[y:y+local.shape[0],x:x+local.shape[1]]=(local>0).astype(np.uint8);masks.append(full)
        objects,d=detector.predict(image,vision,mask_callback=receive)
        if (d.get("count")!=1 or not d.get("eligible") or d.get("label")!=shape or
                len(masks)!=1 or d.get("confidence",0)<max(.9,vision["acceptance_confidence"])):
            raise ValueError("One matching segmentation at 90% or higher is required. "+d.get("message",""))
        if time.monotonic()-started>5:raise ValueError("Detection too slow; retry with a fresh frame")
        if previous and box_iou(previous["bbox_xywhn"],d["bbox_xywhn"])<.6:raise ValueError("Item moved; keep it still and retry")
        previous=d;mask=masks[0];background=roi_mask(depth.shape,vision["roi"])
        background[cv2.dilate(mask,np.ones((11,11),np.uint8))>0]=0
        frame={"mask":mask,"rays":rays,"plane":None,"height":None,"source":None,
               "confidence":d["confidence"],"at":report["captured_at"],"warning":None}
        try:
            points,valid=cloud(depth,report,background,rays,config)
            plane=fit_plane(points,config)
            if (reference.get("session")==engine.session and reference.get("roi")==vision["roi"] and
                    reference.get("fingerprint")==signature):
                if abs(float(np.median(plane_distance(points,reference["plane"]))))>config["max_reference_shift_mm"]:
                    raise ValueError("Visible plane differs from current empty-support reference; check ROI/support")
            frame.update(plane=plane,source="live_support_plane",background_valid_fraction=valid)
            if frames and frames[-1]["source"]=="live_support_plane":
                old=frames[-1]["plane"]
                if abs(float(np.median(plane_distance(points,old))))>config["max_reference_shift_mm"] or np.dot(plane["normal"],old["normal"])<math.cos(math.radians(.5)):
                    raise RuntimeError("Visible support/camera moved between frames; retry")
            if manual is None:
                try:
                    inner=cv2.erode(mask,np.ones((5,5),np.uint8))
                    top,_=cloud(depth,report,inner,rays,config)
                    heights=plane_distance(top,plane);height=float(np.median(heights))
                    noise=float(1.4826*np.median(np.abs(heights-height)))
                    threshold=max(config["min_resolvable_height_mm"],3*max(.2,report["depth_unit_m"]*1000,noise,plane["rms_mm"]))
                    if not threshold<height<=50:raise ValueError("Depth height too shallow/noisy; enter known thickness")
                    frame["height"]=height
                except ValueError as exc:frame["warning"]=str(exc)
        except ValueError as exc:
            frame["warning"]="Visible support depth unavailable: "+str(exc)
            # Valid object-top depth still gives a physical footprint; it cannot
            # tell thickness without the support or a known manual measurement.
            try:
                top,_=cloud(depth,report,cv2.erode(mask,np.ones((5,5),np.uint8)),rays,config)
                frame.update(plane=fit_plane(top,config),source="object_top_plane")
            except ValueError:pass
        frames.append(frame);last_image=image
    # NUC-04: missing/intermittent depth is partial data, not an HTTP failure.
    # Never average support-plane and object-top projections together.
    warnings=list(dict.fromkeys(f["warning"] for f in frames if f["warning"]))
    groups={source:[f for f in frames if f["plane"] is not None and f["source"]==source]
            for source in ("live_support_plane","object_top_plane")}
    selected=max(groups.values(),key=len)
    if len(groups["live_support_plane"])>=2:
        selected=groups["live_support_plane"]
    if len(selected)<len(frames):
        warnings.append("Depth incomplete or plane source changed; physical dimensions use only the consistent valid subset.")
    heights=[f["height"] for f in selected if f["height"] is not None]
    usable=manual is not None or (len(heights)>=2 and float(np.std(heights))<=config["max_height_std_mm"])
    height=float(manual if manual is not None else np.mean(heights)) if usable else None
    areas=[];dims=[]
    for frame in selected:
        projection_height=(height or 0.) if frame["source"]=="live_support_plane" else 0.
        try:
            area=mask_area(frame["mask"],frame["plane"],projection_height,frame["rays"])
            dimension=dimensions(frame["mask"],frame["plane"],projection_height,frame["rays"],shape,area)
            if not all(math.isfinite(dimension[k]) and dimension[k]>0 for k in ("width_mm","length_mm")):
                raise ValueError("Invalid projected dimensions")
            areas.append(area);dims.append(dimension)
        except (ValueError,FloatingPointError) as exc:
            warnings.append("Physical dimensions unavailable for one frame: "+str(exc))
    physical=bool(areas)
    cv=float(np.std(areas)/np.mean(areas)*100) if physical else None
    if physical and cv>config["max_area_cv_pct"]:
        warnings.append("Physical dimensions unstable; enter independently measured dimensions.")
        physical=False;areas=[];dims=[];cv=None
    if not physical:warnings.append("Only pixel mask available. Enter independently measured dimensions; no box size is substituted.")
    if not usable:warnings.append("Thickness/volume unavailable; use a known manual thickness.")
    volumes=[area*height for area in areas] if physical and usable else []
    result={"schema":"thinal-geometry-v1","geometry_mode":"live_mask","ok":True,"shape":shape,
        "camera_session":engine.session,"reference_id":None,"reference_created_at":None,
        "camera_fingerprint":signature,"vision_revision":d["revision"],"samples":len(frames),
        "area_mm2":float(np.mean(areas)) if physical else None,"area_std_mm2":float(np.std(areas)) if physical else None,
        "area_cv_pct":cv,"area_px":float(np.mean([f["mask"].sum() for f in frames])),
        "area_reference":selected[0]["source"] if physical else "pixel_mask_only",
        "dimension_samples":len(dims),"height_samples":len(heights),
        "height_mm":height,"height_std_mm":0. if manual is not None else float(np.std(heights)) if usable else None,
        "height_source":"manual_known" if manual is not None else "depth_above_support" if usable else "unavailable",
        "volume_mm3":float(np.mean(volumes)) if physical and usable else None,
        "volume_std_mm3":float(np.std(volumes)) if physical and usable else None,
        "width_mm":float(np.mean([v["width_mm"] for v in dims])) if physical else None,
        "length_mm":float(np.mean([v["length_mm"] for v in dims])) if physical else None,
        "dimension_method":dims[-1]["method"] if physical else "manual required",
        "confidence_min":min(f["confidence"] for f in frames),"first_frame_at":frames[0]["at"],"last_frame_at":frames[-1]["at"],
        "warnings":warnings,"settings":config,"assumptions":"Flat uniform coin/bar. Mask footprint is not microscopic coil contact. Density does not identify gold/purity."}
    preview=build_bundle(last_image,shape)
    preview["annotation"].update(objects=objects,detection=d,source="YOLO segmentation metrology",label_source="model_prediction",
        measurement={"type":shape,"message":"Measured segmentation mask; raw pixels preserved"})
    preview["detection"]=d;result["preview"]=preview
    return result
