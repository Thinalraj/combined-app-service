# Metal Purity Detector HMI Prototype

Flask-backed 800x480 touchscreen prototype for the Raspberry Pi HMI.

## Files

- `index.html` - main HMI page
- `styles.css` - black instrument-style theme
- `app.js` - screen flow and simulated measurement behavior
- `app.py` - Flask backend for serving the HMI and measurement history API
- `measurements.json` - demo measurement history records
- `calibration.json` - latest empty-air calibration record
- `teaching_library.json` - demo reference-library teaching records
- `requirements.txt` - Python dependency list
- `assets/` - optional transparent PNG carousel assets
- `systemd/` - systemd service files for Raspberry Pi autostart
- `install_services.sh` - installs and starts DanFishel AFiS services
- `uninstall_services.sh` - removes DanFishel AFiS services

## Carousel Assets

Drop transparent 128x128 PNG images into `assets/` using these names:

```text
gold-24k.png
gold-22k.png
gold-18k.png
silver-999.png
silver-925.png
palladium.png
```

The HMI will use the PNG when present. If an image is missing, the CSS bar fallback remains visible.

For Raspberry Pi display performance, the current HMI references optimized `*-display.png` copies generated from the original PNGs.

## Run On Raspberry Pi

Copy the folder to the Pi, then run from inside the folder:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Open Chromium:

```bash
chromium-browser --kiosk http://localhost:8080
```

If your Pi command is different, try:

```bash
chromium --kiosk http://localhost:8080
```

You can also open `index.html` directly in Chromium for a quick check.

## Install Services On Raspberry Pi

This package is configured for:

```text
/home/agtpi/Desktop/app2
```

After copying the folder there:

```bash
cd /home/agtpi/Desktop/app2
python3 -m pip install -r requirements.txt
chmod +x install_services.sh uninstall_services.sh
./install_services.sh
```

## Current Flow

```text
Home
  -> Place Object
  -> Enter Weight
  -> Select Shape
  -> Measuring Progress
  -> Result
  -> Engineering / Details
```

The measurement and engineering values are simulated for now. Later they can be connected to the Python backend and ESP32 serial data.

## Data Storage

This prototype uses Flask and stores demo measurement history in `measurements.json`.

For quick demos, completed simulated measurements are saved to `measurements.json`, and password-protected delete also updates that file.

Calibration saves one latest empty-air baseline into `calibration.json`.

For calibration POC, Flask directly reads:

```text
/dev/ttyUSB0
/dev/ttyUSB1
```

for 10 seconds and groups packets by JSON `device` label. Supported labels include `primary_voltage`, `primary_current`, `secondary_voltage`, and typo fallback `secondary_volatge`.

Teaching mode saves known reference samples into `teaching_library.json`. It collects `/dev/ttyUSB0` and `/dev/ttyUSB1` for 5 seconds, then records material, purity, shape, weight, CH1/CH2 RMS mean, CH1/CH2 standard deviation, CH2/CH1 ratio, and CH1/CH2 deltas compared to the latest calibration baseline.

For production, replace the JSON file with SQLite while keeping the same API shape.

## REST API

```text
GET  /api/status
GET  /api/history
POST /api/history
POST /api/history/<id>/delete
GET  /api/calibration
POST /api/calibration/start
GET  /api/teaching
POST /api/teaching
POST /api/teaching/<id>/delete
```

## Signal Service Engineering (2026-09 update)

Engineering -> Signal Service uses the ADP2230 FastAPI service at `http://127.0.0.1:8001`.

Fixed engineering presets:

```text
F1 = 8 kHz
F2 = 10 kHz
F3 = 15 kHz
F4 = 20 kHz
Amplitude = 1.0 V peak = 2.0 V peak-to-peak (zero offset sine)
```

View-service proxy API:

```text
GET  /api/signal/status
POST /api/signal/start                {"preset":"f1"}
POST /api/signal/stop
GET  /api/signal/measurement
POST /api/signal/sample               {"number_of_samples":30,"interval":0.1}
GET  /api/signal/air-calibration
POST /api/signal/air-calibration/run
```

Air calibration runs F1 -> F4 sequentially, collects 30 measurements per frequency, and stores the complete raw measurements plus service statistics in `private_data/signal_air_calibration.json`. The file is not in the Flask static allowlist. Writes use a temporary file + `os.replace()` and keep the prior record as `signal_air_calibration.previous.json`.

The signal service currently acquires one WaveForms Analog In channel. The new engineering calibration therefore stores the signal-service metrics directly and does not fabricate a second channel.

## Teaching F1-F4 signal capture

New teaching records use the Signal Service API after the dimension/vision step. The capture order is fixed at F1 8 kHz, F2 10 kHz, F3 15 kHz, and F4 20 kHz with 1.0 V peak output. Each frequency is sampled 30 times at 0.1 s intervals. The full per-sample response and summary statistics are stored inside the unique teaching record in `teaching_library.json` under `signal_capture`, together with flattened `signal_features` and the material-vs-air `air_comparison` when an air calibration exists. Teaching History renders all four frequency summaries and the unique record ID.
