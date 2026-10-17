# Model folder and adapter contract

One root: `<combined-app-service>/system_assets/`. Keep the complete project together when copying to the NUC.
Image and View services resolve this root from their source locations, independent of the terminal working directory.
If services are deployed on different computers, keep matching asset paths/files on both; folder sync is not automatic.

- `vision/`: put your coin/bar segmentation `.pt` here. Arbitrary filenames and deeper subfolders are supported.
- `metal/`: put trusted `.joblib` bundles here (the extension is .joblib, not .jolib).
- `algorithms/classifier_model.json`: the existing built-in trained JSON classifier. Compute Model reads/writes here.
- `vision_settings.json`: active vision file path, enabled flag, ROI, confidence thresholds and image size. Created on Save.
- `model_registry.json`: selected gold and purity file paths. Created/updated on activation.
- `api_sources.json`: service addresses and market-provider mappings. Created on first View startup.
- `API_REFERENCE.md`: APIs, fields, units, examples and complete installed route inventory.

On first startup known legacy gold/purity .joblib files and classifier_model.json are copied into the new root if their
central target is missing. Existing originals are retained. Existing central files are never overwritten by migration.
Model weights are not included in this patch. If migration finds none, use your own compatible files.

## Engineering workflow

Open Engineering → Vision Model. Scan folder → select → Test model → Save for YOLO.
Enable YOLO only after placing the trained weights; leave disabled to retain the existing manual/OpenCV workflow.
Default acceptance 80%; detection floor 25% counts weaker candidates without accepting their labels.
ROI/confidence controls remain behind Engineering login. No training is started by selecting a file.

For gold/purity: expand Gold / purity models, select both, Validate & activate pair.
Choose the existing Gold Standard classifier separately. Both files must match its adapter.
Changing a model role never retrains it or translates its feature meaning.
Replacing a selected file in place is supported: YOLO reloads when size/mtime changes, frequency models reload on use.
For deployment use a new filename then select it, so a running request cannot read a half-copied file.

## Supported vision adapter

Ultralytics local segment weights, exactly two classes: `coin` and `bar` (either class-ID order).
Detection-only/classification weights and other class sets are rejected. Image service requires `ultralytics` in its Python.
Predicted labels and mask polygons are separate metadata; raw JPEG pixels stay unchanged.
Confidence below 80% yields Unknown; no/multiple objects or ROI-edge masks block user progression.
Coin/bar candidates alone cannot detect every unrelated object. This patch does not infer gold content from appearance.

## Supported metal adapter: frequency_rf_v1

A trusted joblib serialized dictionary containing `model`, a fitted classifier with `.predict(X)` and class labels
in `model.classes_` or bundle `labels`. Gold gate must include class `Gold` (case-insensitive); all other gate labels
follow the existing non-gold path. Purity labels retain the existing classifier's display behavior (e.g. 916, 999).
Input X has shape `[number_of_samples, 12]` with this exact feature order:

```json
[
  "f1_delta_ch1",
  "f1_delta_ch2",
  "f2_delta_ch1",
  "f2_delta_ch2",
  "f3_delta_ch1",
  "f3_delta_ch2",
  "f1_delta_pct",
  "f2_delta_pct",
  "f3_delta_pct",
  "weight_g",
  "thickness_mm",
  "contact_area_ratio"
]
```

Declare this order in bundle `feature_names`, fitted model `feature_names_in_`, or an adjacent
`your_model.joblib.json` sidecar. Sidecar example:

```json
{
  "adapter": "frequency_rf_v1",
  "feature_names": [
    "f1_delta_ch1",
    "f1_delta_ch2",
    "f2_delta_ch1",
    "f2_delta_ch2",
    "f3_delta_ch1",
    "f3_delta_ch2",
    "f1_delta_pct",
    "f2_delta_pct",
    "f3_delta_pct",
    "weight_g",
    "thickness_mm",
    "contact_area_ratio"
  ]
}
```

Migration writes a feature sidecar for each known legacy bundle it copies. Every selected file, including the
central default names, must declare its feature order. Wrong order/count/adapter is rejected before activation.

Deltas are measured channel RMS minus that frequency's air baseline in the capture's RMS units (ADP2230 currently volts).
Delta_pct averages the two channels' percent change relative to air. weight_g is grams, thickness_mm is mm;
contact_area_ratio is dimensionless. Preserve original training units, frequency plan, calibration and geometry meaning.
A matching shape/count does not prove unit/frequency compatibility or model accuracy. Validate with known samples.

The legacy adapter uses F1/F2/F3. F4 is still captured and stored, but is not silently inserted into a model trained on 12 inputs.
A four-frequency gold_model_trial bundle needs its own adapter, plus its exact feature-building/preprocessing/label contract.
This patch cannot infer that contract from a .joblib extension. Do not relabel a different model as frequency_rf_v1.

## Other files and future adapters

Scan discovers `.pt`, `.joblib`, `.pkl`, `.onnx`, `.json`, `.py` recursively. Only the two adapters above are runnable through
these selectors. Other files show as stored with no automatic execution; Python scripts are never imported by a scan.
New weights using an installed adapter need only copy + select. A new algorithm/input/output format requires one adapter
implementation; after that, compatible replacement files can use the same folder/select workflow.
A bare model cannot describe camera calibration, units, feature extraction or output meaning automatically.

## Standalone checker (no scale or signal)

From the project root, after putting weights in `system_assets/vision/best.pt`:
```powershell
py .\service\image-service\yolo_preview.py --model vision/best.pt --image "D:\photos\coin.jpg"
```
For a live checker using the already-running Image service on 8003:
```powershell
py .\service\image-service\yolo_preview.py --model vision/best.pt --count 20
```
Add `--headless` for JSON-only output. GUI: Q/Esc closes. The path is relative to system_assets even for this checker.
Camera diagnostics remain available separately in `service/image-service/camera_debug.py`.

## Subsequent additions

GEOMETRY-01 adds separate projected area/height/prism-volume and density-plausibility evidence.
See GEOMETRY_GUIDE.md. The learned classifiers still receive their historical geometry definitions.
The supplied signal_plus_geometry.joblib has now been inspected: see OPERATING_NOTES.md for exact features,
scikit-learn 1.6.1 compatibility, known-gold-only scope and the dedicated adapter still required.
Continuous item-removal confirmation and a valid gold/non-gold classifier remain separate work.


## REFERENCE-01: supplied pipeline adapter now available

A third explicit .joblib role, reference, is available in recursive discovery. It uses its own reference_model.json;
the existing gold/purity RF registry stays intact. See REFERENCE_MODEL_GUIDE.md for the supported pipeline bundle,
profile/hash binding, seven-column inputs, scikit-learn 1.6.1 requirement and known-gold-only scope.
This is an additional installed adapter; .onnx/.pkl/arbitrary Python formats still are not executed automatically.
