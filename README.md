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

On Windows, double-click `start_all.bat`.

The HMI is available at `http://127.0.0.1:8080`.
