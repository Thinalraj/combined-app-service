# Combined App Service

This repository contains the HMI view service and its three backend services.

| Service | Port |
|---|---:|
| Signal | 8001 |
| Weight | 8002 |
| Image | 8003 |
| View/HMI | 8080 |

Run the complete stack on macOS/Linux with:

```bash
./start_all.sh
```

On Windows, install Windows Terminal, then run `start_all.bat`. It opens one
Windows Terminal window with one tab per service and launches Chrome in kiosk
full-screen mode at `http://127.0.0.1:8080`.

To launch only the backend services, run `start_backend_services.bat`.

To open the HMI on another host, pass its IP address:

```bat
start_all.bat 192.168.1.50
```

To launch only Chrome against an already-running view service:

```bat
launch_chrome.bat 192.168.1.50
```

The hamburger menu includes an Exit button and asks for confirmation before
attempting to close the kiosk window.

The Chrome launcher uses a separate kiosk profile so an already-open personal
Chrome session cannot consume and ignore the kiosk flags.

The HMI is available at `http://127.0.0.1:8080`.

## FINISH-01 startup and final checks

Normal launchers now use `launch_stack.py` and `system_assets/runtime.json`.
Default Signal mode is hardware; simulation must be explicit. Occupied ports
are rejected. Read `system_assets/FINAL_TEST_GUIDE.md` before the first hardware
trial. `python system_check.py` and Engineering > System Readiness run passive
checks; use an explicit `--only SENSOR --read` for an individual sensor test.

NUC-02 workflow fixes: read `system_assets/NUC_02_FIX_GUIDE.md` for startup-zero
reuse/skip, manual removal, same-frame mask geometry and the 90% reference gates.
These instructions supersede the older per-item zero/mandatory empty-reference
sequence for user verification.

NUC Workflow 03: see [apply order and hardware smoke test](system_assets/NUC_03_FIX_GUIDE.md). Apply after Workflow 02. Customer detection, removal and kiosk Exit changes preserve central model/hardware configuration.
