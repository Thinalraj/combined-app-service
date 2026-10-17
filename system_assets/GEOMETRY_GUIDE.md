# GEOMETRY-01 — flat coin/bar estimates

Apply after YOLO/Assets-01. Restart Image 8003 and View 8080, then hard-refresh Chrome.
No new dependencies beyond the Image service's existing NumPy/OpenCV/RealSense/Ultralytics are required.

## Setup and use

1. Put best.pt in `system_assets/vision/`, then Engineering → Vision Model → Scan → select → Test → enable → Save.
2. Keep camera nearly overhead (within 15 degrees), support flat, and the complete working area inside YOLO ROI.
3. Remove ALL items. In the same Engineering screen expand Geometry: empty-support reference, tick the confirmation,
   then Capture empty reference. This fits the support plane; it does not zero the scale or change camera intrinsics.
4. Put a single coin/bar flat on the support. On user or Teaching dimensions choose Measure area + depth height.
5. If height cannot be resolved, enter a known measured thickness using the existing keypad, then Use entered thickness.
   Manual thickness is explicitly labelled; it is never presented as a camera measurement.

Default five fresh frames are averaged; choose 3/5/7 in Geometry quality settings. Keep the object still throughout.
The HMI also requests five stable scale samples. If mass is unavailable, camera geometry remains saved but density is unavailable.
Geometry is optional: old measurement/teaching behavior continues when no geometry check is requested.
Moving camera/support, changing camera/ROI or restarting Image requires a new empty-support reference.
Calibration failures preserve the previous reference but do not report a new success; inspect the error before continuing.

## Reported values

- `area_mm2`: estimated projected footprint (mask coverage, holes retained), with frame-to-frame SD and CV.
- `height_mm`: median top-surface height above the support, averaged across frames; not distance to the camera.
- `height_source`: depth_above_support, manual_known or unavailable.
- `volume_mm3`: area × height, averaged per frame (flat, uniform-thickness prism assumption).
- `density_check.density_g_cm3`: averaged mass_g × 1000 / volume_mm3.
- `density_check.deviation_pct`: 100 × (density/reference_density − 1).

Default nominal pure-gold reference is 19.32 g/cm³ and comparison tolerance ±10%, editable in Engineering.
This tolerance is an initial operating preset, not validated measurement uncertainty or an assay acceptance limit.
An outside-reference message does not mean non-gold or lower grade. A 916 alloy need not have pure gold's density.
A within-reference message does not establish gold or distinguish 916/999. No classifier decision is overwritten.

The estimate describes a flat coin/bar footprint, not microscopic contact with the coil, side area or a full 3D surface.
Relief, bevels, hollows, bending or nonuniform thickness can make the prism-volume approximation inaccurate.
Compare against known dimensions/mass before relying on physical estimates. No real camera metrology was validated here.

## Quality handling

Each sample uses a matched color/depth frame, aligned intrinsics, reported depth scale and SDK deprojection.
Depth is checked within 100–2000 mm; unsupported SDK deprojection profiles fail explicitly.
The stored support plane is checked against the currently visible background around the dilated segmentation mask.
A changed plane, insufficient valid depth, multiple objects, low-confidence/edge masks or object movement rejects the check.
The camera profile/serial and Image-process session must match the reference.
Auto height must exceed the configured minimum and three times the largest estimated noise/depth increment.
Quantized/noisy thin-item depth can therefore require manual thickness even when the camera supplies a depth map.
Missing object depth is not filled. With no reliable height, only support-plane projected area is shown and volume is null.
With manual known height, area is projected onto that height plane, so volume can be computed despite missing reflective top depth,
provided valid support-background depth is available.

Projected area integrates 3D pixel-grid cells weighted by exact foreground pixel counts. SDK distortion is retained;
coverage variation within a cell is approximated. SD/CV report repeatability, not total calibration/systematic uncertainty.
Settings are `system_assets/geometry_settings.json`; empty-reference metadata is `geometry_reference.json`.
The View service saves readings in `service/view-service/geometry_readings/` and attaches evidence to verification/teaching records.
Reading IDs are server-owned, expire after ten minutes for attachment, and are checked against shape, thickness,
vision revision and current Image reference/session. Historical attached readings remain stored with their original timestamps.
Raw photographs remain separate. Keep the same item in place between geometry sampling and frequency verification.

## Standalone camera/geometry checker

From the project root, with Image service already running and its empty reference captured:
```powershell
py .\service\image-service\geometry_check.py --shape coin
py .\service\image-service\geometry_check.py --shape bar --height-mm 2.1
```
This checker calls only Image 8003. It prints geometry JSON; it does not read the scale, zero it or run frequencies.
The HMI adds the averaged mass and density comparison separately.

Technical references:
- https://realsenseai.github.io/librealsense/python_docs/_generated/pyrealsense2.html
- https://github.com/realsenseai/librealsense/wiki/Projection-in-RealSense-SDK-2.0
- https://www.realsenseai.com/wp-content/uploads/2019/11/RealSense_DepthQualityTesting.pdf
- https://periodic-table.rsc.org/element/79/Gold (approximately 19.3 g/cm³ at reference conditions)
