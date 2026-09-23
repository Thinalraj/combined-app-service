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

The HMI is available at `http://127.0.0.1:8080`.
