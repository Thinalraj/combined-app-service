"""NUC-03: local, token-bound request to close the owned kiosk browser only."""
import hashlib
import hmac
import json
from pathlib import Path
import tempfile


def control_path(root):
    key = hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / ("afis-kiosk-" + key + ".json")


def install_kiosk_exit(app):
    from flask import request, jsonify

    @app.post("/api/kiosk/exit")
    def kiosk_exit():
        # A LAN page cannot close another computer's kiosk. A random token is
        # passed only to the browser started by this copy of launch_kiosk.py.
        if (request.remote_addr not in ("127.0.0.1", "::1")
                or request.headers.get("Sec-Fetch-Site") == "cross-site"
                or request.headers.get("Origin") != request.host_url.rstrip("/")):
            return jsonify(message="Exit is available from the local kiosk only"), 403
        body = request.get_json(silent=True)
        token = body.get("token") if isinstance(body,dict) else None
        try:
            path = control_path(Path(__file__).resolve().parents[1])
            state = json.loads(path.read_text(encoding="utf-8"))
            expected = state["token"]
            if not isinstance(token,str) or not token or not hmac.compare_digest(token,expected):
                return jsonify(message="This tab was not opened by the current kiosk launcher"),403
            # The supervisor owns the Popen handle. The HTTP service never kills
            # processes, looks up arbitrary PIDs, or accepts a client file path.
            path.with_suffix(".exit").write_text(token,encoding="utf-8")
            return jsonify(ok=True,message="Closing this kiosk; services remain running")
        except (OSError,ValueError,KeyError,TypeError):
            return jsonify(message="Restart Chrome with launch_chrome.bat or start_all.bat"),409
