# API reference — ASSETS-01 / YOLO-01

Default addresses: View/HMI `http://127.0.0.1:8080`, Signal `:8001`, Weight `:8002`, Image `:8003`.
The browser calls HMI routes; the HMI calls sensor services. JSON requests use `Content-Type: application/json`.
The three sensor base URLs and external-provider URLs/field mappings are read from `system_assets/api_sources.json`.
That file is created on first View startup, importing saved service addresses when available.
Edit it directly or use Engineering → Vision Model → API sources and formats. No Python path edit is needed.
Internal route names below are the installed protocol: changing a sensor route requires a compatible service/adapter.

## External metal prices

`GET https://api.gold-api.com/price/{symbol}` with XAU=gold, XAG=silver, XPT=platinum, XPD=palladium.
Expected JSON object (illustrative values, not a current quotation):
```json
{"symbol":"XAU","price":2000.0,"updatedAt":"2026-10-17T00:00:00Z"}
```
Extract `price`: positive finite numeric USD per troy ounce; `updatedAt`: timezone-aware ISO-8601 string;
`symbol`: requested metal string. If a `currency` field exists it must say USD; otherwise the installed adapter assumes USD.
Other provider fields are ignored. Default mappings: `price_field=price`, `time_field=updatedAt`,
`symbol_field=symbol`, `currency_field=currency`. Nested object paths such as `data.price` are supported (no array indexes).

`GET https://api.frankfurter.dev/v2/rate/USD/MYR`:
```json
{"date":"2026-10-16","base":"USD","quote":"MYR","rate":4.0}
```
Extract `rate`: positive finite MYR per USD; `date`: YYYY-MM-DD; check `base=USD`, `quote=MYR`.
Default mappings: `rate_field=rate`, `date_field=date`, `base_field=base`, `quote_field=quote`.
The adapter rejects a different pair, nonpositive values, FX older than seven days, future or backwards metal timestamps.
Provider errors retain previous quotes and mark them stale; missing data is never made into a zero price.

Conversion: `MYR/g = USD/troy_ounce × MYR/USD ÷ 31.1034768`.
The UI estimates alloy content using 0.999/0.916/0.750 for gold and 0.999/0.925 for silver; platinum/palladium use spot metal values.
These are content estimates; premiums, workmanship and tax are excluded.
A full refresh makes five provider requests (one FX plus four metals). The service attempts daily at 00:00 Malaysia time,
and on first access/start if today's attempt has not happened. Manual refresh has a 60-second cooldown, including failed attempts.
Reference FX is daily, so a midnight refresh need not return a new business-day FX observation.
Official provider references: https://gold-api.com/docs and https://frankfurter.dev/ .

HMI `GET /api/metal-rates`: reads cached state; may queue today's scheduled attempt, never waits for external network.
`POST /api/metal-rates/refresh`: requests a manual update. Both return JSON:
```json
{"currency":"MYR","unit":"g","pending":false,"metals":{"XAU":{"myr_per_g":257.20,"updated_at":"2026-10-17T00:00:00Z","fx_date":"2026-10-16","change_pct":0.2,"baseline_at":"2026-10-16T00:00:00Z","stale":false}},"errors":{},"manual_retry_after":0}
```
Extract `metals.<symbol>.myr_per_g` only with `stale` and timestamp shown. `change_pct` is percent since the previous
stored quote, not a historical daily-return series; it may be null. `pending` means refresh is running.
`errors` is keyed by metal/FX/cache; `manual_retry_after` is seconds. The response also contains schedule/source metadata.

## Signal (8001)

- `POST /sine/start`: `{ "frequency_hz":8000, "amplitude_v":1.0 }`; supported Hz: 8000,10000,15000,20000.
- `GET /measurement/average?frequency_hz=8000&sample_size=30&interval_s=0.05&amplitude_v=1` starts, samples, then stops.
  Extract `statistics.ac_rms_v.mean` and `.std_dev` (volts), `frequency_hz` (Hz), `sample_size` (integer).
  Other statistics include peak amplitude and peak-to-peak volts. Each statistic contains mean/min/max/std_dev/plus_minus.
- `GET /status`: `{running:boolean, frequency_hz:number|null, amplitude_v:number|null, simulate:boolean}`.
  Check `simulate`; simulator output must not be reported as a physical capture.
- `POST /measurement`: one acquisition of the currently running sine; extract `ac_rms_v`, `frequency_hz`,
  `sample_rate_hz`, `sample_count`. `POST /sine/stop` stops output.
- F1/F2/F3/F4 are slots in the saved frequency plan, not fixed frequencies. Keep `frequency_hz` with every record.

## Weight (8002)

`GET /weight/average?samples=10`: stable samples converted to grams. Returned stable-average fields: `average`, `std_g`, `minimum`, `maximum`, `range`, `samples`, `samples_requested`, `samples_valid`, `stable_samples`, `dynamic_samples`, `discarded_readings`, `unit`, `source_unit`.
Use the averaged gram value and its spread, with the explicit unit; errors return non-2xx.
`GET /weight` returns one instrument reading; do not treat a dynamic/unstable reading as a stable result.
`POST /preparation/start` body: `{ "pan_empty_confirmed":true, "settings":{}, "repeat_internal":false }`.
Returns 202 and job state; poll `GET /preparation/status`. A conflicting active job returns 409.
The HMI public equivalents are `/api/load-cell/preparation/start` and `/api/load-cell/preparation/status`.
Internal startup check runs once per Weight-service process, then explicit zero and residual checks run each cycle.
Only protected `/api/calibration/scale/prepare` accepts the Engineering repeat action. Inspect success/status/errors;
never infer success just because the request returned. Instrument deviation units are device-defined; residual grams are separate.
Legacy tare routes operate the instrument; new HMI workflows use preparation instead.

## Image and YOLO (8003)

`GET /image`: current JPEG bytes (not JSON). `GET /image/frame?type=coin&annotations=true`:
`{raw_jpeg_base64:string, annotation:object}` from one camera frame. Decode base64 to JPEG.
`annotation.image` describes dimensions; `objects[].polygons[]` has `role` outer/hole and normalized `[x,y]` points.
`GET /image/bundle` returns the last frozen measurement bundle; it is not live.
`GET /camera/debug` provides camera intrinsics/depth diagnostics. Scene range is distance to camera, not object thickness.
`GET /size?type=coin` uses the existing OpenCV measurement algorithm. YOLO-01 does not change numerical dimensions.

`POST /yolo/validate` and `POST /yolo/frame` accept `{ "settings": { ...vision_settings.json... }, "debug":false }`.
Validate checks a local .pt's task/classes. Frame returns a raw JPEG, separate annotation, and `detection`:
```json
{"state":"single_object","eligible":true,"count":1,"label":"coin","confidence":0.93,"bbox_xywhn":[0.5,0.5,0.3,0.3],"capture_age_ms":120,"revision":"...","roi_xywhn":[0,0,1,1]}
```
States: single_object, no_objects, multiple_objects, unknown, roi_edge. HTTP 503 means unavailable, not no_objects.
`bbox_xywhn` is normalized centre x/y, width/height in the full image. ROI is normalized left/top/width/height.
`annotation.objects[]` includes `predicted_label`, `label` (unknown if rejected), `confidence` (0..1), `accepted`,
`mask_area_px` (pixel count, not mm²), model_class_id and canonical class_id (bar=0, coin=1; null if rejected).
Polygon points use full-image coordinates even when inference crops the ROI. Holes remain separate in JSON/SVG.
The count is of coin/bar candidates above the detection floor, inside ROI; it cannot count every possible foreign object.
One eligible object requires confidence at least 80%, usable mask and no ROI-edge contact.
HMI Place Continue requires three fresh consistent frames; server rechecks a fresh frame before a signal sweep.
No detections do not prove the scale pan is empty. This is shape detection, not gold/purity recognition.

HMI public proxy: `GET /api/vision/yolo/frame`; protected diagnostics: `GET /api/calibration/vision/frame?debug=1`.
`GET /api/vision/yolo/status` returns enabled/confidence/ROI/revision, omitting the model path.
`GET/POST /api/calibration/vision/settings` loads/saves settings; saving enabled=true validates the Image-service model first.
`POST /api/calibration/vision/validate` tests draft settings without saving.
`POST /api/verification/image/capture` saves an evidence JPEG + JSON + HTML; body may contain shape and detector=yolo.
A failed detector can still save a raw photo with `warning`; it cannot pass the vision gate.
Automatic labels are unreviewed; do not use verification photos as known gold labels.

## Assets and model selection (HMI 8080, Engineering login required)

`GET /api/calibration/assets`: recursive scan (up to 1000 candidate files) returns
`{root:string, files:[{path,bytes,candidate_roles,status}], selection:{gold,purity}, api:object}`.
Scanning does not deserialize models or run Python. Candidates are not validated just because their extension matches.
`POST /api/calibration/assets/models`: `{ "gold":"metal/my_gold.joblib", "purity":"metal/my_purity.joblib" }`.
Both must pass the existing frequency adapter before one atomic registry replacement. No partial activation.
This selects files for Gold Standard mode; choose that classifier mode separately in its existing menu.
`GET/POST /api/calibration/assets/api`: configuration object below. Saving validates shape/units/URLs, not provider availability.
`GET /api/calibration/assets/reference`: this Markdown text.
`POST /api/engineering/login` body `{pin:string}` sets an HttpOnly session cookie; use the same session for protected calls.
`GET /api/engineering/session`, `POST /api/engineering/logout`. Expired/missing login returns 401 on protected routes.
Sensor services 8001–8003 do not inherit HMI authentication. Use HMI routes for browser controls.

## Configuration example

Created automatically as `api_sources.json`; endpoints and mappings are editable in Engineering:

```json
{
  "services": {
    "weight": "http://127.0.0.1:8002",
    "vision": "http://127.0.0.1:8003",
    "signal": "http://127.0.0.1:8001"
  },
  "metals": {
    "url": "https://api.gold-api.com/price/{symbol}",
    "price_field": "price",
    "time_field": "updatedAt",
    "symbol_field": "symbol",
    "currency_field": "currency",
    "unit": "USD/troy_ounce"
  },
  "fx": {
    "url": "https://api.frankfurter.dev/v2/rate/USD/MYR",
    "rate_field": "rate",
    "date_field": "date",
    "base_field": "base",
    "quote_field": "quote",
    "unit": "MYR/USD"
  }
}
```

## Complete installed route inventory

Tables list every explicitly declared route in this patched source; handler names identify the exact code contract.
Automatic FastAPI `/docs`, `/redoc`, `/openapi.json` supplement the sensor schemas.

### HMI (8080)

| Method | Path | Handler |
|---|---|---|
| GET | `/` | `index` |
| GET | `/<path:filename>` | `static_files` |
| GET | `/api/calibration` | `get_calibration` |
| GET | `/api/calibration/assets` | `assets_scan_api` |
| GET | `/api/calibration/assets/api` | `assets_api_get` |
| GET | `/api/calibration/assets/reference` | `assets_reference` |
| GET | `/api/calibration/camera/frame` | `get_camera_debug_frame` |
| GET | `/api/calibration/vision/frame` | `yolo_frame_api` |
| GET | `/api/calibration/vision/settings` | `yolo_settings_api` |
| GET | `/api/classifier/status` | `get_classifier_status` |
| GET | `/api/history` | `get_history` |
| GET | `/api/history/<record_id>` | `get_history_record` |
| GET | `/api/load-cell/average` | `get_load_cell_average` |
| GET | `/api/load-cell/latest` | `get_load_cell_latest` |
| GET | `/api/load-cell/preparation/status` | `scale_preparation_status_api` |
| GET | `/api/metal-rates` | `get_metal_rates` |
| GET | `/api/sensors/latest` | `get_latest_sensors` |
| GET | `/api/settings` | `get_settings` |
| GET | `/api/status` | `status` |
| GET | `/api/teaching` | `get_teaching_records` |
| GET | `/api/teaching/image/<path:filename>` | `teaching_image_api` |
| GET | `/api/validation-results` | `get_validation_results` |
| GET | `/api/verification/image/<path:filename>` | `verification_image_api` |
| GET | `/api/vision/image/detected` | `get_vision_detected_image` |
| GET | `/api/vision/image/frame` | `get_vision_image_frame` |
| GET | `/api/vision/image/live` | `get_vision_live_image` |
| GET | `/api/vision/size` | `get_vision_size` |
| GET | `/api/vision/yolo/frame` | `yolo_frame_api` |
| GET | `/api/vision/yolo/status` | `yolo_status_api` |
| POST | `/api/calibration/assets/api` | `assets_api_save` |
| POST | `/api/calibration/assets/models` | `assets_models_api` |
| POST | `/api/calibration/scale/prepare` | `start_scale_preparation_api` |
| POST | `/api/calibration/start` | `start_calibration` |
| POST | `/api/calibration/validate` | `validate_calibration` |
| POST | `/api/calibration/vision/settings` | `save_yolo_settings_api` |
| POST | `/api/calibration/vision/validate` | `test_yolo_model_api` |
| POST | `/api/classifier/train` | `train_classifier` |
| POST | `/api/daq/frequency` | `set_daq_frequency` |
| POST | `/api/history` | `add_history_record` |
| POST | `/api/history/<record_id>/delete` | `delete_history_record` |
| POST | `/api/load-cell/preparation/start` | `start_scale_preparation_api` |
| POST | `/api/load-cell/zero` | `zero_load_cell` |
| POST | `/api/measurement/verify` | `verify_measurement` |
| POST | `/api/metal-rates/refresh` | `refresh_metal_rates` |
| POST | `/api/sensors/update` | `update_latest_sensors` |
| POST | `/api/settings` | `update_settings` |
| POST | `/api/teaching` | `add_teaching_record` |
| POST | `/api/teaching/<record_id>/delete` | `delete_teaching_record` |
| POST | `/api/teaching/image/capture` | `capture_photo_api` |
| POST | `/api/teaching/validate` | `validate_teaching_sample` |
| POST | `/api/verification/image/capture` | `capture_photo_api` |

### Engineering session (8080)

| Method | Path | Handler |
|---|---|---|
| GET | `/api/engineering/session` | `engineering_session` |
| POST | `/api/engineering/login` | `engineering_login` |
| POST | `/api/engineering/logout` | `engineering_logout` |

### Image (8003)

| Method | Path | Handler |
|---|---|---|
| GET | `/camera/debug` | `get_camera_debug` |
| GET | `/image` | `get_image` |
| GET | `/image/bundle` | `get_image_bundle` |
| GET | `/image/detected` | `get_detected_image` |
| GET | `/image/frame` | `get_image_frame` |
| GET | `/settings` | `get_settings` |
| GET | `/size` | `get_size` |
| POST | `/aoi` | `save_aoi` |
| POST | `/yolo/frame` | `get_yolo_frame` |
| POST | `/yolo/validate` | `validate_yolo_model` |

### Weight (8002)

| Method | Path | Handler |
|---|---|---|
| GET | `/` | `root` |
| GET | `/preparation/status` | `preparation_status` |
| GET | `/weight` | `get_weight` |
| GET | `/weight/average` | `get_average_weight` |
| POST | `/preparation/start` | `start_preparation` |
| POST | `/tare` | `tare` |
| POST | `/tare-average` | `tare_and_average` |

### Signal (8001)

| Method | Path | Handler |
|---|---|---|
| GET | `/measurement/average` | `single_frequency_average` |
| GET | `/measurement/{frequency_hz}` | `single_frequency` |
| GET | `/status` | `status` |
| POST | `/measurement` | `measurement` |
| POST | `/measurements/sample` | `sample` |
| POST | `/sine/start` | `start` |
| POST | `/sine/stop` | `stop` |


## GEOMETRY-01 additions (18 October 2026)

| Service | Method/path | JSON / purpose |
|---|---|---|
| Image 8003 | GET /geometry/status | settings, reference metadata, reference_for_current_session |
| Image 8003 | POST /geometry/settings | geometry settings object → validated/saved settings |
| Image 8003 | POST /geometry/reference | {settings: YOLO settings, empty_confirmed:true} → fitted support reference |
| Image 8003 | POST /geometry/measure | {settings: YOLO settings, shape:"coin"/"bar", manual_height_mm:number|null} → averaged geometry |
| HMI 8080 protected | GET /api/calibration/geometry | proxy status |
| HMI 8080 protected | POST /api/calibration/geometry/settings | protected validated settings proxy |
| HMI 8080 protected | POST /api/calibration/geometry/reference | {empty_confirmed:true}; server supplies YOLO settings |
| HMI 8080 public | POST /api/vision/geometry/measure | {shape:"Coin"/"Bar", manual_height_mm:number|null}; server supplies settings and adds mass/density |

Read `area_mm2`, `area_std_mm2`, `area_cv_pct`, `area_reference`, `height_mm`, `height_std_mm`, `height_source`,
`volume_mm3`, `volume_std_mm3`, `samples`, `warnings`, `first_frame_at`, `last_frame_at`, `reference_id`.
Null height/volume means unavailable; do not turn it into zero. area_reference=support_plane_projection means area needs
known height to refine. A successful partial area-only result is possible and is explicitly labelled.
HMI returns 201 with reading_id, mass_measurement and density_check, or non-2xx with error/message.
Density units are g/cm³, volume mm³, heights mm, areas mm², score 0–1 and deviations percent.
Send only geometry_reading_id alongside the usual verification/teaching request to attach server-owned evidence.
Do not submit browser-computed density/geometry values as if they were a completed camera check.
See GEOMETRY_GUIDE.md for assumptions, limits and quality settings; OPERATING_NOTES.md records the supplied models' contracts.


## REFERENCE-01 additions

| HMI 8080, Engineering login required | Purpose |
|---|---|
| GET /api/calibration/assets/reference-model | Current reference_model.json selection/profile |
| POST /api/calibration/assets/reference-model/test | Validate draft selection; do not save or run sensors |
| POST /api/calibration/assets/reference-model | Validate/save selection; bind confirmed profile to model hash |
| POST /api/settings with {"classifier_algorithm":"gold_reference_v1"} | Use the selected reference pipeline after profile/file checks |
| GET /api/classifier/status | Includes reference_ready, reference_model metadata and setup warnings |
| POST /api/classifier/train in reference mode | Check external model only; no fitting/retraining |

Selection body is the reference_model.json object: adapter, model_path (asset-relative .joblib), min_score (0.80–1),
frequency_hz (F1–F4 Hz), amplitude_v_peak, signal_definition=raw_ac_rms_v_delta_pct, profile_confirmed,
and profile_model_sha256 (null until server saves a confirmed selection).
Validation returns {ok, settings, metadata, message}; metadata includes exact model SHA-256, labels, selected input columns,
saved runtime version, effective_threshold and reference_only=true. Incompatible versions/formats return non-2xx; selection is preserved.
POST /api/measurement/verify keeps its existing request fields and returns the normal record with classifier_result.

Read classifier_result.accepted only as acceptance of a REFERENCE MATCH. It does not establish identity/purity.
Read reference_grade (916/999 or null), nearest_reference_grade, score (0–1), threshold (percent), input_row,
reference_only=true, scores_are_calibrated=false, gold_identity_verified=false, simulation, decision_message,
model_metadata and acquisition_evidence. Never promote nearest_reference_grade into an accepted result.
Legacy confidence is retained as the matching score expressed in percent for UI compatibility.
User needs_verification stays true; purity_prediction/purity_result remain null.

Signal 8001 GET /measurement/average now additionally returns simulate:boolean from the actual controller.
The HMI preserves its native values in reference_signal_sequence, separately from corrected frequency_sequence:
{frequency_command, frequency_hz, amplitude_v_peak, simulate, ac_rms_v, std_v, sample_size, source}.
The source is adp2230_raw_ac_rms_v; volts and Hz are explicit. Fresh air calibration saves the same raw schema.
Missing mode metadata from an older Signal process fails reference inference: update/restart 8001 and recalibrate.
Engineering Validate uses all four frequencies in reference mode and returns reference-specific comparison labels.
See REFERENCE_MODEL_GUIDE.md for installation, limits and the model-only checker.

## FINISH-01 remaining workflow/startup fixes

See `FINAL_TEST_GUIDE.md` for normal launcher configuration, removal checks,
readiness endpoints, modular sensor tests and the final physical test sequence.
The central `runtime.json` selects hardware/signal-only simulation, Python and
scale COM port. Internal calibration remains once per Weight-service startup.
