from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)

API_BASE = "http://127.0.0.1:8002"


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>WKC Scale Test</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 40px auto;
        }

        button {
            padding: 12px 20px;
            margin: 8px;
            font-size: 16px;
            cursor: pointer;
        }

        pre {
            background: #f2f2f2;
            padding: 15px;
            border-radius: 6px;
            white-space: pre-wrap;
        }

        h1 {
            margin-bottom: 5px;
        }

        .status {
            margin-top: 20px;
        }
    </style>
</head>

<body>

    <h1>WKC Scale Test Panel</h1>

    <p>
        FastAPI server:
        <b>{{ api_base }}</b>
    </p>

    <hr>

    <button onclick="callApi('GET', '/weight')">
        Get Single Weight
    </button>

    <button onclick="callApi('GET', '/weight/average')">
        Get Average Weight
    </button>

    <button onclick="callApi('POST', '/tare')">
        Tare
    </button>

    <button onclick="callApi('POST', '/zero')">
        Zero
    </button>

    <button onclick="callApi('POST', '/tare-average')">
        Tare + Average
    </button>

    <button onclick="callApi('GET', '/serial/status')">
        Serial Status
    </button>

    <div class="status">
        <h3>Response</h3>
        <pre id="result">Press a button to test the scale server.</pre>
    </div>

<script>

let requestInProgress = false;

async function callApi(method, endpoint) {
    const result = document.getElementById("result");

    // Avoid accidental double-clicks from sending overlapping operations.
    if (requestInProgress) {
        result.textContent = "A scale request is already in progress...";
        return;
    }

    requestInProgress = true;
    result.textContent = "Requesting " + endpoint + "...";

    try {
        const response = await fetch(
            "/proxy?method=" + method +
            "&endpoint=" + encodeURIComponent(endpoint)
        );

        const data = await response.json();
        result.textContent = JSON.stringify(data, null, 2);
    }
    catch (error) {
        result.textContent = "Error:\\n" + error;
    }
    finally {
        requestInProgress = false;
    }
}

</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(
        HTML,
        api_base=API_BASE,
    )


@app.route("/proxy")
def proxy():
    method = request.args.get("method")
    endpoint = request.args.get("endpoint")

    # Only allow the known local scale API paths through this test proxy.
    allowed_endpoints = {
        "/weight",
        "/weight/average",
        "/tare",
        "/zero",
        "/tare-average",
        "/serial/status",
    }

    if endpoint not in allowed_endpoints:
        return jsonify({
            "success": False,
            "error": "Unsupported endpoint",
        }), 400

    url = API_BASE + endpoint

    try:
        if method == "GET":
            response = requests.get(url, timeout=20)
        elif method == "POST":
            response = requests.post(url, timeout=20)
        else:
            return jsonify({
                "success": False,
                "error": "Unsupported method",
            }), 400

        try:
            data = response.json()
        except Exception:
            data = {
                "raw_response": response.text,
            }

        return jsonify({
            "http_status": response.status_code,
            "endpoint": endpoint,
            "data": data,
        })

    except requests.exceptions.RequestException as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 502


if __name__ == "__main__":
    # Disable Flask's development reloader so this BAT-launched service has
    # exactly one frontend process.
    app.run(
        host="0.0.0.0",
        port=5005,
        debug=False,
        use_reloader=False,
    )
