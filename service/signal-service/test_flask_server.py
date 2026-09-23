"""Small Flask test server for exercising the measurement request sequence.

This always uses the simulated ADP2230 and is intended for API/client testing
without WaveForms hardware. It mirrors the production REST endpoints.
"""
from flask import Flask, jsonify, request, render_template_string

from rest_service import Controller

app = Flask(__name__)
controller = Controller(simulate=True)


@app.get("/")
def index():
    return render_template_string("""
<!doctype html>
<title>Signal Service Test</title>
<style>
body { font: 18px Arial; max-width: 700px; margin: 40px auto; padding: 0 20px; }
label { display: block; margin: 16px 0 6px; font-weight: bold; }
input, button { font: inherit; padding: 12px; margin-right: 8px; }
button { cursor: pointer; }
#result { white-space: pre-wrap; background: #f2f2f2; padding: 16px; margin-top: 20px; }
</style>
<h1>ADP2230 Signal Service Test</h1>
<p>Allowed frequencies: 8000, 10000, 15000, or 20000 Hz. Amplitude: 0–5 V peak.</p>
<label for="frequency">Frequency (Hz)</label>
<input id="frequency" type="number" value="10000" min="8000" max="20000" step="1000">
<label for="amplitude">Amplitude (V peak)</label>
<input id="amplitude" type="number" value="1.0" min="0" max="5" step="0.1">
<p>
  <button onclick="startSignal()">1. Start Sine</button>
  <button onclick="measureSignal()">2. Get Measurement</button>
  <button onclick="stopSignal()">3. Stop Sine</button>
</p>
<pre id="result">Ready.</pre>
<script>
const result = document.getElementById('result');
const values = () => ({ frequency_hz: Number(document.getElementById('frequency').value), amplitude_v: Number(document.getElementById('amplitude').value) });
async function call(url, options) {
  result.textContent = 'Working...';
  const response = await fetch(url, options);
  const data = await response.json();
  result.textContent = JSON.stringify(data, null, 2);
}
function startSignal() { call('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(values())}); }
function measureSignal() { call('/api/measurement', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(values())}); }
function stopSignal() { call('/api/stop', {method:'POST'}); }
</script>
""")


def request_values():
    payload = request.get_json(silent=True) or request.form
    return int(payload.get("frequency_hz", 10000)), float(payload.get("amplitude_v", 1.0))


@app.post("/api/start")
def api_start():
    try:
        frequency_hz, amplitude_v = request_values()
        from rest_service import StartRequest
        return jsonify(controller.start(StartRequest(frequency_hz=frequency_hz, amplitude_v=amplitude_v)))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/measurement")
def api_measurement():
    try:
        frequency_hz, amplitude_v = request_values()
        return jsonify(controller.read_frequency(frequency_hz, amplitude_v))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/stop")
def api_stop():
    try:
        return jsonify(controller.stop())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/status")
def status():
    return jsonify(controller.status())


@app.get("/measurement/<int:frequency_hz>")
def measurement(frequency_hz: int):
    amplitude = float(request.args.get("amplitude_v", 1.0))
    try:
        return jsonify(controller.read_frequency(frequency_hz, amplitude))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/measurement/average")
def average():
    try:
        result = controller.average_frequency(
            int(request.args["frequency_hz"]),
            int(request.args["sample_size"]),
            float(request.args["interval_s"]),
            float(request.args.get("amplitude_v", 1.0)),
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
