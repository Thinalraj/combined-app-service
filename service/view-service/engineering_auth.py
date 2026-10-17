"""ACCESS-01: server-owned engineering login for the view/HMI service.

One local Flask process owns the sessions. Restarting it revokes every login.
This does not authenticate the separate sensor services on ports 8001-8003.
"""
import hmac
import os
import secrets
import threading
import time

from flask import jsonify, request


def install_engineering_auth(app, default_pin):
    pin = os.environ.get("ENGINEERING_PIN", default_pin)
    cookie = "engineering_session"
    lifetime = 30 * 60
    sessions, attempts = {}, {}
    lock = threading.RLock()
    private_files = {"calibration.json", "teaching_library.json", "daq_offset.json", "vision_yolo_settings.json"}

    def authenticated():
        now = time.monotonic()
        with lock:
            for token in list(sessions):
                if sessions[token] <= now:
                    del sessions[token]
            return sessions.get(request.cookies.get(cookie, ""), 0) > now

    def protected():
        path = request.path.rstrip("/")
        prefixes = ("/api/calibration", "/api/teaching", "/api/classifier",
                    "/api/validation-results", "/api/daq")
        return (any(path == p or path.startswith(p + "/") for p in prefixes)
                or (path == "/api/settings" and request.method != "GET")
                or (request.endpoint == "static_files"
                    and (request.view_args or {}).get("filename") in private_files))

    @app.before_request
    def engineering_gate():
        # Reject browser requests originating from another site, including LAN pages.
        relevant = protected() or request.path.startswith("/api/engineering/")
        if relevant and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if (request.headers.get("Sec-Fetch-Site") == "cross-site"
                    or (origin and origin != request.host_url.rstrip("/"))):
                return jsonify(error="cross_origin_request"), 403
        if protected() and not authenticated():
            return jsonify(error="engineering_login_required"), 401

    @app.after_request
    def engineering_no_cache(response):
        if protected() or request.path.startswith("/api/engineering/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/engineering/login")
    def engineering_login():
        if not request.is_json:
            return jsonify(error="json_required"), 415
        now = time.monotonic()
        address = request.remote_addr or "local"
        payload = request.get_json(silent=True) or {}
        entered = payload.get("pin", "") if isinstance(payload, dict) else ""
        with lock:
            sessions.pop(request.cookies.get(cookie, ""), None)
            # Five failed attempts per minute; expired entries are discarded.
            for key in list(attempts):
                attempts[key] = [t for t in attempts[key] if now - t < 60]
                if not attempts[key]:
                    del attempts[key]
            if len(attempts.get(address, [])) >= 5:
                return jsonify(error="too_many_attempts", retry_after_seconds=60), 429
            if not isinstance(entered, str) or not hmac.compare_digest(entered.encode(), pin.encode()):
                attempts.setdefault(address, []).append(now)
                return jsonify(error="invalid_pin"), 403
            attempts.pop(address, None)
            token = secrets.token_urlsafe(32)
            sessions[token] = now + lifetime
        response = jsonify(authenticated=True, expires_in_seconds=lifetime)
        response.set_cookie(cookie, token, max_age=lifetime, httponly=True,
                            samesite="Strict", secure=request.is_secure, path="/")
        return response

    @app.get("/api/engineering/session")
    def engineering_session():
        return jsonify(authenticated=authenticated())

    @app.post("/api/engineering/logout")
    def engineering_logout():
        with lock:
            sessions.pop(request.cookies.get(cookie, ""), None)
        response = jsonify(authenticated=False)
        response.delete_cookie(cookie, path="/", samesite="Strict")
        return response
