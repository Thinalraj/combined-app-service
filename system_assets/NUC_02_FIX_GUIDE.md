# NUC-02: verification workflow, mask geometry and 90% gates

Based on `nuc-testing-v1` commit `d3a7541c4ca020ccf52f21a2eaf313ae1c20e965`.
This incremental patch contains code and this guide, not models or a replacement
repo. It does not replace runtime.json, vision_settings.json, reference_model.json,
API addresses, calibration, datasets or saved photos. Keep your NUC's COM11 and ROI.

## Apply and restart

Stop all four testing services with Ctrl+C. From the NUC's testing repo:

```powershell
cd "$env:USERPROFILE\Documents\combined-app-service-nuc-test"
git apply --check "$env:USERPROFILE\Downloads\thinal_nuc_workflow_02.patch"
```

If that check succeeds silently:

```powershell
git apply "$env:USERPROFILE\Downloads\thinal_nuc_workflow_02.patch"
```

If it fails, keep the local NUC fixes and provide the exact error; do not force
or reset the repo. A separate uncommitted zero-recovery patch may overlap.

The troubleshooting log identifies the balance adapter as **COM11**, while COM5
was the disconnected old adapter. Check `system_assets/runtime.json` has COM11.
NUC-02 also makes a directly launched Weight service read that file instead of
falling straight back to COM5. Environment overrides are still supported.
Restart ALL services through `start_all.bat`, then hard-refresh Chrome. Runtime
build is now NUC-02, so System Readiness will identify old processes. Changing
COM settings cannot change a process that is already running. Keep the old stack
closed; the conflicting Touch Injector task was handled separately in your log.
No additional packages or retraining are needed for this patch.

## Verification sequence

- If this Weight-service startup already has a verified preparation, Start and
  Another Item reuse it. Reuse only reads status: it sends no tare/zero/internal
  commands. A reported disconnect invalidates reuse of the internal-test latch.
- If preparation is not ready, the preparation page offers **Skip preparation /
  use current scale**. Skip does not make a scale error valid; weighing still
  needs the functioning balance. Density is unavailable without a verified zero.
- To prepare again after moving the balance or investigating drift, use
  Engineering > Load Cell > Prepare. The pan-empty confirmation is retained.
  Auto internal mode now tries TST3 only; it does not substitute C3 adjustment.
  Explicit Engineering Adjust remains available. An unsupported test is reported.
- On results, the physical-empty checkbox stays usable and is not cleared by
  failed polls. Normal removal still uses clear readings and a final fresh check.
  If that fails, explicitly select **Continue using my visual check** as well.
  This is manual confirmation, not sensor proof, and does not send a zero command.
- Home always returns Home. It does not claim the sensors confirmed removal.
  Another Item resets item data and reuses the startup preparation when valid.

## Camera controls and masks

Back to live camera and Back to measurement controls are available in the shared
preview. A captured/measured photo is frozen; return Live to resume the placement
detection gate. Snap/download still preserves the raw image.

Coin/bar dimensions now call segmentation metrology instead of the old OpenCV
`/size` bounding-box route when YOLO is enabled. The measured frame is displayed
with a filled, even-odd mask overlay, preserving holes. Raw JPEG pixels stay clean.
The displayed Working footprint is the physical mask area when available; the
separate Model formula area remains visible because the supplied joblib was
trained on pi*d^2/4 or width*length. Its feature meaning is not silently changed.
Bar width/length come from the rotated projected mask boundary, not the full image
or an axis-aligned image box; coin diameter is area-equivalent. Values are shown
compactly but transmitted at their stored precision.

## Height, volume and density

The Image service uses the SAME fresh frames for mask, aligned depth and camera
intrinsics. It averages 5 frames by default (existing 3/5/7 setting is respected).
It fits the visible flat support outside the dilated object mask, then measures
object height above that plane. A saved empty-support reference is optional;
a missing/restarted reference no longer automatically causes the reported 503.
A current matching empty reference is still used to detect an inconsistent plane.

Set ROI to the **top coil/support platform**, excluding the table/balance below.
The ROI format remains `[x,y,width,height]`, e.g. your central 70% setting
`[0.15,0.15,0.70,0.70]`. The correct crop depends on which surface is visible;
there must be enough flat background around the object. Fit quality, valid depth,
movement, repeatability and shallow/noisy-height checks remain enforced.

- Usable support + top depth: physical mask area, height, dimensions and A*h volume.
- Support depth unusable but flat object-top depth usable: physical footprint and
  dimensions; thickness/volume need a known manual thickness.
- Both depth planes unusable: pixel mask/preview only; no invented mm dimensions
  or volume. Enter independently measured dimensions. Entered thickness alone
  cannot convert an uncalibrated pixel mask into physical area.
- Multiple/no/low-score detections, moving objects or a camera/SDK error can still
  fail the measurement. These are not converted into successful geometry.

Density is mass_g * 1000 / volume_mm3, from a stable averaged mass and usable volume.
It is attached to the record and shown on dimensions/results, including outside-
tolerance messages. Pure-gold reference/tolerance remain your configured values
(19.32 g/cm3 and 10% default). This is a flat-prism plausibility check, not a gold
identity/purity assay. Validate dimensions against a caliper/known standard on NUC.

## Both scores at least 90%

The effective YOLO acceptance and reference-score floors are now 90%, including
old saved 80% configurations. Higher configured thresholds stay higher. Existing
ROI, selected model, acquisition profile, model hash and air readings are retained.
No new air calibration is needed solely because this confidence floor changed.

A reference result needs one fresh matching shape above its gate AND the joblib
score above its gate. The example 999/84.01% result becomes Unable to determine /
not eligible. Disabled/missing YOLO cannot give an eligible reference result.
Density cannot override a failed confidence gate. Even a passing pair remains a
known-gold reference comparison; gold identity and actual purity are not established.
Look at `classifier_result.eligibility` and `geometry_evidence.density_check` in
saved records for the separate decisions. Old historical results are not rewritten.

## Quick NUC acceptance checks

1. Confirm startup/status reports COM11, correct repo/Python and NUC-02 on all four
   processes. Perform one empty-pan preparation if needed, then a known-mass read.
2. Start and finish two user tests: Another Item must not start another internal
   operation or zero. Skip and manual removal must not send those commands either.
3. With a flat coin/bar inside the platform ROI, automatic dimensions should show
   the actual mask, physical footprint, width/length and height when depth supports
   it. Check with a caliper. Test known manual thickness and missing-depth behavior.
4. Check Back to live / measurement controls after a captured photo. Confirm a
   failed removal poll leaves the physical checkbox ticked and usable.
5. A shape or model score below 90% must not produce an eligible reference match.
   Inspect density messages separately; neither a high score nor density proves gold.

Automated checks covered synthetic calibrated masks/depth (including an L-mask
smaller than its box), repeated height/volume, depth fallbacks, fresh-session
evidence, 90% boundaries and the 84% example, no-actuation reuse/skip/manual flow,
UI controls, port configuration and TST3-only Auto behavior. Actual NUC camera,
scale, coil accuracy and screen layout remain physical tests for your setup.
