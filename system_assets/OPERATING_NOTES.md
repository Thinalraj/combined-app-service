# Project operating notes

## Asset workflow agreed with v

- Keep future model files and editable API/algorithm settings under the project-root `system_assets/`.
- Engineering → Vision Model → Scan folder → Select → Test/Validate → Save/Activate.
- Subfolders are scanned. Replacements using an installed adapter need no Python path edits.
- New input/output formats require a matching adapter. Scan does not execute arbitrary Python or deserialize every file.
- Keep service launchers unchanged; restart the affected services after applying a patch, then hard-refresh Chrome.
- Deliver small sequential patches with revision comments; preserve old workflows and saved raw photographs.
- Keep physical camera estimates separate from historical learned feature definitions until compatibility is checked.

## Model files inspected on 18 October 2026

`vision/best.pt`: the supplied best.pt checkpoint metadata specifies Ultralytics 8.4.178, task segment, bar=0 and coin=1.
Stored mask-validation metrics: precision 0.92278, recall 0.89384, mAP50 0.92293, mAP50–95 0.80352.
`vision/last.pt` is the final checkpoint of the same model family; its stored mask mAP50–95 is 0.78736.
Use best.pt as the initial deployment candidate. These are saved training-validation metrics, not a live NUC test.
The weights were inspected without installing Torch/Ultralytics here; no image inference or new training was run.

`metal/signal_plus_geometry.joblib`: loaded successfully in an isolated scikit-learn 1.6.1 environment.
It failed to deserialize under the available 1.8.0 environment (_RemainderColsList incompatibility).
Its pipeline uses numeric f1_delta_pct, f2_delta_pct, f3_delta_pct, f4_delta_pct, area_mm2, thickness_mm,
and categorical shape (Bar/Coin). The label set is [916,999], with score_threshold=0.80.
The stored pipeline drops the other exported CSV columns; a seven-column DataFrame smoke test succeeded.
The smoke test checks the interface only; invented inputs were not used to estimate accuracy.

This bundle is a KNOWN-GOLD REFERENCE matcher, not a gold/non-gold classifier or purity assay.
The stored purpose says research reference matching, scores_are_calibrated=false,
and evaluation_mode=capture_only_cv_UNVERIFIED_SPECIMEN_INDEPENDENCE.
Its training script derives area from pi*diameter²/4 for coins and width*length for bars.
Keep that formula input for this bundle. New segmentation-area estimates are separate evidence and are not substituted.
The supplied bundle uses pipeline + numeric_features, not the existing legacy RF model + 12-feature schema.
Do NOT select it as either member of the legacy Gold Standard model pair. REFERENCE-01 now supplies the dedicated reference adapter; see REFERENCE_MODEL_GUIDE.md.
The adapter rejects incomplete F1–F4 readings and unsupported shapes, reuses the stored preprocessing,
shows uncalibrated matching scores, and never translates a 916/999 match into proof of gold.
Preserve the training frequency/air-baseline/RMS-unit contract; that complete acquisition contract is not embedded in this bundle.
No uploaded weights have been changed or included in the patch.


## REFERENCE-01 operation

Place the supplied .joblib in system_assets/metal; scan, choose the reference role, test, confirm the training profile,
validate/select, then Use reference mode. Install requirements-reference.txt using View Python and restart 8001/8080.
Fresh four-frequency raw air calibration is mandatory. Signal simulator flags propagate into results and prevent physical acceptance.
The separate reference selector does not modify legacy RF pair selection or historical classifier definitions.

## FINISH-01 remaining workflow/startup fixes

See `FINAL_TEST_GUIDE.md` for normal launcher configuration, removal checks,
readiness endpoints, modular sensor tests and the final physical test sequence.
The central `runtime.json` selects hardware/signal-only simulation, Python and
scale COM port. Internal calibration remains once per Weight-service startup.
