# REFERENCE-01 — supplied known-gold 916/999 pipeline

Apply after Geometry-01. No weights, dataset or retraining are included.
This patch adds an explicit adapter for the supplied signal_plus_geometry.joblib.
It preserves legacy RF/other classifier modes; it does not silently change the active method.

## Install and select

From the project root, use the SAME Python that launches the View service:
```powershell
py -m pip install -r .\system_assets\requirements-reference.txt
```
The supplied bundle was saved with scikit-learn 1.6.1. It was loaded/tested with that version here;
it failed to deserialize under 1.8.0. Version mismatches now produce a clear error, with no estimator conversion.
Other external/legacy models may have their own version requirements. This patch does not install packages automatically.

1. Copy your file into `system_assets/metal/signal_plus_geometry.joblib` (or another subfolder/name).
2. Restart Signal 8001 and View 8080; hard-refresh Chrome. The new Signal field is required for reference inference.
3. Engineering → Vision Model → Scan folder → expand Known-gold 916/999 reference model.
4. Select the .joblib and Test model. The adapter checks actual selected inputs, shape encoder, labels and library version.
5. Confirm the displayed acquisition profile matches training: default F1–F4 = 8000/10000/15000/20000 Hz,
   amplitude 1 V peak, raw single-waveform AC-RMS change from air. Threshold defaults to 80% and cannot go below 80%.
6. Tick confirmation → Validate & select → Use reference mode. The Classifier Method dropdown also exposes this mode.
7. Run fresh four-frequency air calibration without an item, then use normal user verification or Engineering comparison.

Air captured before this patch lacks the required raw/mode provenance; run calibration again.
Use reference mode requires View acquisition=DAQ and service mode enabled. It does not force the Signal backend into hardware mode.
If Signal runs with `--simulate`, results are labelled simulation and cannot become accepted physical matches.
For physical readings, the Signal service must actually run without `--simulate`, with the WaveForms SDK/device available.
Existing launchers' simulator/hardware choice is retained; hardware-launch configuration remains a separate task.

All editable selection/profile settings live in `system_assets/reference_model.json`.
The declared profile is operator-confirmed; the serialized bundle does not contain a complete sensor calibration contract.
The profile confirmation is bound to the selected file's SHA-256. Replacing its bytes requires revalidation/confirmation/selection.
Changing the selected filename clears the confirmation checkbox. Wrong/unsupported file formats do not overwrite the selection.
Test only inspects/loads the pipeline; it does not save settings, run sensors or retrain anything.
Selecting the file and enabling the classifier method are separate explicit actions.
Compute Model becomes Check reference model in this mode; it does not fit a new model or overwrite the learned JSON classifier.

## Exact inputs and interpretation

Numeric columns, in the stored pipeline's selected order:
`f1_delta_pct, f2_delta_pct, f3_delta_pct, f4_delta_pct, area_mm2, thickness_mm`.
Categorical column: `shape`, canonical Coin/Bar.

Each frequency uses signed `100 × (raw_object_ac_rms_v − raw_air_ac_rms_v) / raw_air_ac_rms_v`.
These are native single-waveform Signal values, preserved BEFORE display CH1/CH2 gain/offset corrections.
CH2 mirroring is not used as a second independent model input. No missing frequency or baseline is imputed.
Every raw step records Hz, amplitude, sample count and simulator flag. Air/object profiles and modes must match.
Mixed simulator/hardware captures, missing metadata or incomplete readings produce Unable to determine.
Unusable model/air/profile prerequisites are rejected before spending time on a frequency sweep.

Formula area = pi × diameter²/4 for Coin; width × length for Bar (mm²). Thickness is mm.
Geometry-01's segmentation area, volume and density remain separate evidence; mask area is NOT substituted into this trained input.
The stored fitted imputer/scaler/encoder/classifier are reused. No model parameters are modified.
The new adapter accepts only its seven-column bundle, not the legacy RF pair or arbitrary .pkl/.onnx algorithms.

Outputs:
- `916 reference match` or `999 reference match`: highest uncalibrated score meets the effective threshold.
- `Unable to determine`: score below threshold or missing/incompatible data/model/profile.
- `Simulation only: ...`: a demo result; accepted=false and no physical-grade acceptance.

The effective threshold is max(0.80, configured minimum, model's saved threshold).
This is a known-gold reference matcher, not a gold/non-gold detector or purity assay.
Its scores are not calibrated probabilities of correctness. A high score can occur on an unfamiliar/non-gold object.
No trained non-gold class or validated automatic domain guard exists in this bundle.
All user records remain needs_verification=true, even when a reference match is accepted.
Gold identity is always marked unverified; purity_prediction and purity_result are null.
The supplied evaluation uses capture-only CV with unverified specimen independence, so its score is not a deployment accuracy guarantee.
The density comparison remains a separate plausibility check and never converts a reference match into proof of gold.

Engineering Validate uses all F1–F4 in this mode and displays REFERENCE MATCH/MISMATCH/COMPARISON or UNABLE TO DETERMINE.
It cannot be overwritten by the legacy brass rule. New reference comparisons are excluded from legacy brass report generation.
All other validation/classifier modes keep their existing behavior.

## Model-only checker

Uses the selected asset; no camera, scale or frequency API calls:
```powershell
py .\service\view-service\gold_reference.py
py .\service\view-service\gold_reference.py --input .\system_assets\reference_inputs.example.json
```
The example numbers are INVENTED for a software-interface smoke test, not a known sample or accuracy test.
For prediction, first validate/select the confirmed profile in Engineering. Offline output is explicitly marked offline_check=true.
Replace example values with your own fully specified readings when needed. Missing/NaN inputs are rejected before imputation.

## What was tested

The actual uploaded bundle loaded with scikit-learn 1.6.1 and accepted a seven-column DataFrame.
Adapter checks covered 80% boundary/rejection, four raw deltas, formula-area mapping, class order/model hash,
version failure, profile mismatch, missing values, simulator mixing and repeated activation without legacy replacement.
API/UI checks covered protected selection, no-sweep preflight, current/fresh calibration, user records and Engineering comparisons.
Controlled score fixtures test boundary behavior; they do not estimate the model's real-world accuracy.
No physical NUC, coil or assay validation was performed.

Persistence reference: https://scikit-learn.org/stable/model_persistence.html
