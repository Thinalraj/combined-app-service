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
