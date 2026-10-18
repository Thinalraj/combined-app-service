import re
import time
import threading
import serial
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_status import identity
from system_assets import read_json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from scale_preparation import Preparation, stable_average, grams, validate_settings


# ============================================================
# CONFIGURATION
# ============================================================

# NUC-02: direct launches also read central configuration; retain env overrides.
_RUNTIME = read_json("runtime.json", {})
PORT = os.environ.get("AFIS_WEIGHT_PORT", _RUNTIME.get("weight_port", "COM5"))
BAUDRATE = int(os.environ.get("AFIS_WEIGHT_BAUD", str(_RUNTIME.get("weight_baudrate", 9600))))

READ_COMMAND = b"SI\r\n"
TARE_COMMAND = b"TI\r\n"

NUM_READINGS = 30
SAMPLE_INTERVAL = 0.1
SERIAL_TIMEOUT = 2

API_PORT = 8002


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="WKC Weighing Scale API",
    version="1.0.0"
)


# Prevent simultaneous access to COM port
serial_lock = threading.Lock()


# ============================================================
# PARSER
# ============================================================

def parse_weight(response: str):

    response = response.strip()

    if not response:
        return None, None, "No response"

    if response in ["ES", "ET", "EL"]:
        return None, None, f"General error: {response}"

    if response.startswith("S +"):
        return None, None, "Overload"

    if response.startswith("S -"):
        return None, None, "Underload"

    if response.startswith("S I"):
        return None, None, "Internal error / balance not ready"

    if response.startswith("S L"):
        return None, None, "Logical error"

    match = re.match(
        r"^S\s+([SD])\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+([A-Za-z]+)",
        response
    )

    if not match:
        return None, None, f"Unknown response: {response}"

    status = match.group(1)
    weight = float(match.group(2))
    unit = match.group(3)

    return weight, unit, status


# ============================================================
# SERIAL FUNCTIONS
# ============================================================

def open_serial():

    return serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=SERIAL_TIMEOUT
    )


def send_command(ser, command):

    ser.reset_input_buffer()

    ser.write(command)
    ser.flush()

    raw = ser.readline()

    response = raw.decode(
        "ascii",
        errors="ignore"
    ).strip()

    return response


def read_single_weight(ser):

    response = send_command(
        ser,
        READ_COMMAND
    )

    weight, unit, status = parse_weight(
        response
    )

    if weight is None:
        raise RuntimeError(status)

    source_weight, source_unit = weight, unit
    try:
        weight = grams(weight, unit)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return {
        "weight": weight,
        "unit": "g",
        "source_unit": source_unit,
        "source_weight": source_weight,
        "status": status,
        "raw": response
    }


def tare_scale(ser):

    response = send_command(
        ser,
        TARE_COMMAND
    )

    if not response.startswith(("TI S", "TI D")):
        raise RuntimeError("Tare was not acknowledged: " + response)
    return response


def read_average(ser, samples=NUM_READINGS):
    # ZERO-02: stable samples only, explicit gram conversion, real standard deviation.
    return stable_average(ser, read_single_weight, count=samples,
                          interval=SAMPLE_INTERVAL, timeout=max(20, samples * 0.5))


preparation = Preparation(open_serial, read_single_weight, serial_lock)


def require_idle_scale():
    if preparation.blocked():
        raise HTTPException(409, "Scale preparation is active or needs recovery; inspect preparation status")


@app.post("/preparation/start")
def start_preparation(payload: dict):
    try:
        started = preparation.start(payload.get("pan_empty_confirmed"),
                                    validate_settings(payload.get("settings", {})),
                                    repeat_internal=payload.get("repeat_internal") is True)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    if not started:
        return JSONResponse(preparation.snapshot(), status_code=409)
    return JSONResponse(preparation.snapshot(), status_code=202)


# FINISH-01: configuration/status only; no COM port is opened here.
@app.get("/status")
def runtime_status():
    return {"runtime":identity("weight"), "simulate":False, "port":PORT,
            "baudrate":BAUDRATE, "preparation":preparation.snapshot()}


@app.get("/preparation/status")
def preparation_status():
    return preparation.snapshot()


# ============================================================
# API ENDPOINTS
# ============================================================


# ------------------------------------------------------------
# 1. GET SINGLE WEIGHT
# ------------------------------------------------------------

@app.get("/weight")
def get_weight():
    require_idle_scale()

    with serial_lock:
        # Recheck after acquiring the lock: preparation may have started while waiting.
        require_idle_scale()

        try:

            with open_serial() as ser:

                result = read_single_weight(
                    ser
                )

                return {
                    "success": True,
                    "port": PORT,
                    **result
                }

        except serial.SerialException as e:
            preparation.device_disconnected()
            raise HTTPException(
                status_code=503,
                detail=f"Serial port error: {e}"
            )

        except RuntimeError as e:

            raise HTTPException(
                status_code=500,
                detail=str(e)
            )


# ------------------------------------------------------------
# 2. GET AVERAGE WEIGHT
# ------------------------------------------------------------

@app.get("/weight/average")
def get_average_weight(samples: int = NUM_READINGS):
    require_idle_scale()
    if not 1 <= samples <= 100:
        raise HTTPException(400, "samples must be 1 to 100")

    with serial_lock:
        # Recheck after acquiring the lock: preparation may have started while waiting.
        require_idle_scale()

        try:

            with open_serial() as ser:

                result = read_average(ser, samples=samples)

                return {
                    "success": True,
                    "port": PORT,
                    **result
                }

        except serial.SerialException as e:
            preparation.device_disconnected()
            raise HTTPException(
                status_code=503,
                detail=f"Serial port error: {e}"
            )

        except RuntimeError as e:

            raise HTTPException(
                status_code=500,
                detail=str(e)
            )


# ------------------------------------------------------------
# 3. TARE
# ------------------------------------------------------------

@app.post("/tare")
def tare():
    require_idle_scale()

    with serial_lock:
        # Recheck after acquiring the lock: preparation may have started while waiting.
        require_idle_scale()

        try:

            with open_serial() as ser:

                response = tare_scale(
                    ser
                )

                return {
                    "success": True,
                    "port": PORT,
                    "command": "TI",
                    "response": response
                }

        except serial.SerialException as e:
            preparation.device_disconnected()
            raise HTTPException(
                status_code=503,
                detail=f"Serial port error: {e}"
            )

        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

# ------------------------------------------------------------
# 4. TARE + AVERAGE
# ------------------------------------------------------------

@app.post("/tare-average")
def tare_and_average():
    require_idle_scale()

    with serial_lock:
        # Recheck after acquiring the lock: preparation may have started while waiting.
        require_idle_scale()

        try:

            with open_serial() as ser:

                tare_response = tare_scale(
                    ser
                )

                # Allow tare to settle slightly
                time.sleep(0.5)

                result = read_average(
                    ser
                )

                return {
                    "success": True,
                    "port": PORT,
                    "tare_response": tare_response,
                    **result
                }

        except serial.SerialException as e:
            preparation.device_disconnected()
            raise HTTPException(
                status_code=503,
                detail=f"Serial port error: {e}"
            )

        except RuntimeError as e:

            raise HTTPException(
                status_code=500,
                detail=str(e)
            )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {
        "service": "WKC Weighing Scale API",
        "port": PORT,
        "baudrate": BAUDRATE,
        "api_port": API_PORT
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT
    )
