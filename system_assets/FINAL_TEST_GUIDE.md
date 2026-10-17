# FINISH-01: combined remaining fixes

Apply after REFERENCE-01 and its prerequisites. This patch does not contain
models, sample datasets, API secrets or replacement copies of the repo.

## Start the usual way

Stop all four old service processes before starting this copy. Close their
terminal tabs or use Ctrl+C; do not leave an older copy listening on the ports.
The launcher now refuses occupied ports instead of opening a second stale stack.

Edit **this one file**: `system_assets/runtime.json`:

```json
{
  "signal_mode": "hardware",
  "python_executable": "",
  "weight_port": "COM5",
  "weight_baudrate": 9600
}
```

`hardware` is the default. `simulate` simulates **Signal only**; camera and scale
still need their devices. There is no automatic hardware-to-simulator fallback.
Set the actual scale COM port on the NUC. Linux uses e.g. `/dev/ttyUSB0`.
An empty Python field uses the interpreter that launched the script. You may
put an absolute virtual-environment Python path here to use one interpreter for
all services. The checker should be run with that same Python.

In the repo terminal:

```powershell
python .\launch_stack.py --check
.\start_all.bat
```

`start_backend_services.bat` starts all four services without Chrome, as before.
`start_all.bat 192.168.1.50` retains the alternate HMI target option. Windows
Terminal keeps one service per tab; without it, separate console windows open.
The kiosk opens after all four patched processes answer from this repo/Python.
It does not wait for model setup or metrology calibration. If startup times out,
read the failed tab, fix it, and use `launch_chrome.bat` once services are ready.
On Linux/macOS: `bash start_all.sh`; Ctrl+C stops that launch's child processes.

Dependency presence checks do not validate device drivers, DLL loading, USB
permissions, Torch compatibility or inference. Install the existing service
requirements in the selected Python plus the reference requirements:

```powershell
python -m pip install -r .\system_assets\requirements-reference.txt
```

The .pt additionally needs your working Torch/Ultralytics installation. The
RealSense camera needs pyrealsense2 and its device/driver support; the ADP2230
needs the WaveForms SDK. Missing components produce explicit errors.

## Model files and setup order

1. Copy `best.pt` to `system_assets/vision/best.pt` and
   `signal_plus_geometry.joblib` to `system_assets/metal/`.
2. Engineering > Vision Model / System Assets > Scan. Select/validate/enable the
   segmentation file. Acceptance stays at 80%; count candidates at the lower
   configured detection floor. Check ROI with a coin/bar fully inside it.
3. Select the **reference** joblib, Test, confirm its declared acquisition
   profile, Validate & Select, then Use Reference Mode. Read REFERENCE_MODEL_GUIDE.md.
4. With the entire support empty and the camera fixed, capture its empty-support
   reference. Repeat after moving the camera/tray or restarting Image service.
5. Prepare Empty Scale. Internal TST3/C3 runs once this Weight-service startup
   when supported; ordinary zero/residual checks still run for each new item.
   Unsupported/skipped internal operations show a readiness warning, not success.
6. Fresh electrical air calibration at F1-F4: 8/10/15/20 kHz, the confirmed
   amplitude and raw-RMS definition. Old/missing/simulated baselines do not pass.
7. Engineering > System Readiness. Resolve failures; inspect warnings. This
   read-only report does not open the scale, capture images, drive the generator,
   deserialize models, or recalibrate. It checks previously confirmed files and
   status metadata. Then perform the physical tests below.

The signal service acquires **one native scope waveform**. Legacy HMI CH2 is a
mirrored display, not another independent sensor channel. The new reference
adapter uses the four raw RMS values once; its input definition is unchanged.

## Modular diagnostics

Run from the repo root; paths also work from elsewhere when fully qualified.

```powershell
python .\system_check.py
python .\system_check.py --only models
python .\system_check.py --only weight
python .\system_check.py --only weight --read
python .\system_check.py --only camera --read
python .\system_check.py --only signal
python .\system_check.py --only signal --read
```

Without `--read`, checks use status/configuration only. A nonzero exit status
means attention is needed. `--json` prints a machine-readable passive report.
With `--read`, only the chosen sensor is exercised: five stable scale readings,
one camera diagnostic frame, or three readings at each of the four frequencies.
**Signal --read drives 1 V peak output** and requests stop even after failure.
Close live acquisition/teaching/verification first; do not run two clients on the
same generator. This diagnostic never saves air calibration or classification.
If a stop request fails, inspect/stop the physical generator before continuing.

Existing separate tools remain available:

| Tool | Purpose |
| --- | --- |
| `service/image-service/camera_debug.py` | Camera-only GUI; `--headless` prints diagnostics |
| `service/image-service/yolo_preview.py` | Segmentation-only image/live GUI or headless checker |
| `service/image-service/geometry_check.py` | Geometry-only measurement using Image service |
| `service/weight-service/scale_preparation.py` | Scale-only status; preparation needs explicit flags |
| `service/view-service/gold_reference.py` | Selected joblib schema/offline reference checker |

## Physical acceptance tests

Use available known coins/bars; no retraining is needed for these checks.

1. Confirm real Signal mode and all four frequencies. Known-gold reference output
   must stay labelled 916/999 **reference match**, never certified purity or
   gold/non-gold identification. Below 80% stays unable to determine.
2. Compare scale readings to a known mass and area/thickness to caliper readings.
   Repeat a few times. Note depth unavailable on shallow/reflective surfaces;
   use measured manual thickness. Compare density with the configured reference,
   treating its tolerance as an engineering setting, not a validated assay limit.
3. Place no object, two objects, a partially clipped object, and a low-confidence
   object. Gates/warnings must match. A coin/bar model cannot see all foreign
   objects or items outside ROI; visual inspection is mandatory.
4. Complete one user test and one teaching/validation capture. Verify saved raw
   photo, sidecar overlays, F1-F4, input features and geometry evidence remain
   attached to the correct record. Raw JPEG pixels must stay clean.
5. On results/removal: leave the item on the pan and press Another Item/Item
   Removed. It must refuse. Remove it: three clear batches plus the visual tick
   enable confirmation; a final fresh check runs on click. Reinserting an object,
   negative zero drift, unstable readings, a stale/saved image, or an enabled-model
   failure must prevent confirmation. No removal check sends tare/zero commands.
6. Another Item returns to the separate empty-pan preparation gate. Internal
   calibration must be reused this startup; restart Weight service and confirm
   it becomes due again. Explicit Engineering repeat remains available after moves.
7. Unplug a sensor, recover it, navigate Back/History, and log out of Engineering.
   A failed service must never turn into "empty", a real result, or a PIN bypass.
   On unavailable history, the UI no longer invents demo gold records.

The provided reference joblib only compares known-gold 916/999 captures. Reliable
gold-versus-non-gold detection still needs an appropriate negative-class model
and validation. Density alone cannot supply that missing classifier.

## Added API/status fields

- `GET /status` on 8001/8002/8003: FINISH-01 runtime identity (root, Python,
  PID/build), mode and relevant passive state. Signal adds four supported Hz
  values, operation_busy, physical_input_count=1 and the CH2 explanation.
- `GET /api/status` on 8080: actual configured acquisition mode and runtime
  identity instead of a constant `demo` string.
- `GET /api/calibration/readiness`: protected Engineering report; no active reads.
- `GET /api/verification/removal/check`: public read-only scale/camera snapshot,
  raw image + optional overlay, and `removal` evidence. It does not confirm by
  itself. Errors are unknown; zero candidates are not proof of an empty pan.
- Signal acquisitions reject overlap with HTTP 409; explicit `/sine/stop` remains
  available during a running acquisition. It interrupts the acquisition; retry
  only after operation_busy clears. The lock covers each request, not a complete
  multi-request four-frequency sweep, so keep one acquisition client at a time.
