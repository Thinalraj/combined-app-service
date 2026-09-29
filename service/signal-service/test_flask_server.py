from flask import Flask, render_template_string, request, jsonify
import requests

app = Flask(__name__)

# FastAPI backend
API_BASE = "http://127.0.0.1:8001"


HTML = """
<!DOCTYPE html>
<html>

<head>
    <title>ADP2230 API Test Client</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f5f5f5;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        h1 {
            margin-bottom: 5px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 25px;
        }

        label {
            display: block;
            margin-top: 12px;
            margin-bottom: 5px;
            font-weight: bold;
        }

        input {
            padding: 9px;
            width: 180px;
            font-size: 15px;
        }

        button {
            padding: 10px 18px;
            margin: 10px 5px 5px 0;
            font-size: 15px;
            cursor: pointer;
        }

        #status {
            font-weight: bold;
            margin-top: 10px;
        }

        #result {
            background: #111;
            color: #eee;
            padding: 15px;
            min-height: 150px;
            max-height: 500px;
            overflow: auto;
            white-space: pre-wrap;
            border-radius: 5px;
        }
    </style>
</head>


<body>

<h1>ADP2230 API Test Client</h1>

<div class="subtitle">
    Flask Client → FastAPI Backend → ADP2230
</div>


<!-- ===================================================== -->
<!-- SIGNAL CONTROL -->
<!-- ===================================================== -->

<div class="card">

    <h2>Signal Control</h2>

    <label>Frequency (Hz)</label>

    <input
        id="frequency"
        type="number"
        value="10000"
    >


    <label>Amplitude (V peak)</label>

    <input
        id="amplitude"
        type="number"
        value="1.0"
        step="0.1"
    >


    <br><br>


    <button onclick="startSignal()">
        Start Signal
    </button>


    <button onclick="stopSignal()">
        Stop Signal
    </button>

</div>


<!-- ===================================================== -->
<!-- SINGLE MEASUREMENT -->
<!-- ===================================================== -->

<div class="card">

    <h2>Single Measurement</h2>

    <button onclick="measurement()">
        Get Measurement
    </button>

</div>


<!-- ===================================================== -->
<!-- SAMPLE -->
<!-- ===================================================== -->

<div class="card">

    <h2>N Sample Measurement</h2>


    <label>Number of Samples</label>

    <input
        id="number_of_samples"
        type="number"
        value="30"
        min="1"
    >


    <label>Interval (seconds)</label>

    <input
        id="interval"
        type="number"
        value="0.1"
        step="0.1"
        min="0"
    >


    <br><br>


    <button onclick="sample()">
        Start Sampling
    </button>

</div>


<!-- ===================================================== -->
<!-- RESULT -->
<!-- ===================================================== -->

<div class="card">

    <h2>API Response</h2>

    <div id="status">
        Ready
    </div>

    <pre id="result">Waiting for command...</pre>

</div>


<script>

const result =
    document.getElementById("result");

const status =
    document.getElementById("status");


function showWorking(message) {

    status.innerText = message;

    result.innerText =
        "Waiting for API response...";

}


function showResult(data) {

    status.innerText = "Complete";

    result.innerText =
        JSON.stringify(
            data,
            null,
            2
        );

}


function showError(error) {

    status.innerText = "ERROR";

    result.innerText =
        error;

}


// ========================================================
// START
// ========================================================

async function startSignal() {

    showWorking(
        "Starting signal..."
    );

    const frequency =
        Number(
            document.getElementById(
                "frequency"
            ).value
        );

    const amplitude =
        Number(
            document.getElementById(
                "amplitude"
            ).value
        );


    try {

        const response =
            await fetch(
                "/client/start",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            frequency:
                                frequency,

                            amplitude:
                                amplitude
                        })
                }
            );


        const data =
            await response.json();


        showResult(data);

    }

    catch(error) {

        showError(error);

    }

}


// ========================================================
// STOP
// ========================================================

async function stopSignal() {

    showWorking(
        "Stopping signal..."
    );

    try {

        const response =
            await fetch(
                "/client/stop",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        showResult(data);

    }

    catch(error) {

        showError(error);

    }

}


// ========================================================
// SINGLE MEASUREMENT
// ========================================================

async function measurement() {

    showWorking(
        "Acquiring measurement..."
    );

    try {

        const response =
            await fetch(
                "/client/measurement"
            );


        const data =
            await response.json();


        showResult(data);

    }

    catch(error) {

        showError(error);

    }

}


// ========================================================
// N SAMPLE
// ========================================================

async function sample() {

    const numberOfSamples =
        Number(
            document.getElementById(
                "number_of_samples"
            ).value
        );


    const interval =
        Number(
            document.getElementById(
                "interval"
            ).value
        );


    showWorking(
        "Sampling " +
        numberOfSamples +
        " measurements..."
    );


    try {

        const response =
            await fetch(
                "/client/sample",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            number_of_samples:
                                numberOfSamples,

                            interval:
                                interval

                        })
                }
            );


        const data =
            await response.json();


        showResult(data);

    }

    catch(error) {

        showError(error);

    }

}

</script>


</body>

</html>
"""


# ============================================================
# WEB PAGE
# ============================================================

@app.route("/")
def index():

    return render_template_string(
        HTML
    )


# ============================================================
# START SIGNAL
# ============================================================

@app.route(
    "/client/start",
    methods=["POST"]
)
def client_start():

    try:

        data = request.get_json()

        response = requests.post(
            f"{API_BASE}/api/start",
            json={
                "frequency":
                    data["frequency"],

                "amplitude":
                    data["amplitude"],
            },
            timeout=10,
        )

        return (
            jsonify(response.json()),
            response.status_code
        )

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# STOP SIGNAL
# ============================================================

@app.route(
    "/client/stop",
    methods=["POST"]
)
def client_stop():

    try:

        response = requests.post(
            f"{API_BASE}/api/stop",
            timeout=10,
        )

        return (
            jsonify(response.json()),
            response.status_code
        )

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# SINGLE MEASUREMENT
# ============================================================

@app.route(
    "/client/measurement",
    methods=["GET"]
)
def client_measurement():

    try:

        response = requests.get(
            f"{API_BASE}/api/measurement",
            timeout=10,
        )

        return (
            jsonify(response.json()),
            response.status_code
        )

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# N SAMPLE
# ============================================================

@app.route(
    "/client/sample",
    methods=["POST"]
)
def client_sample():

    try:

        data = request.get_json()

        number_of_samples = int(
            data["number_of_samples"]
        )

        interval = float(
            data["interval"]
        )

        # Allow enough time for the complete sampling operation.
        #
        # Example:
        # 30 samples × 0.1 s ≈ 3 seconds
        #
        timeout = max(
            30,
            number_of_samples
            * interval
            + 20
        )

        response = requests.post(
            f"{API_BASE}/api/sample",

            json={
                "number_of_samples":
                    number_of_samples,

                "interval":
                    interval,
            },

            timeout=timeout,
        )

        return (
            jsonify(response.json()),
            response.status_code
        )

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )