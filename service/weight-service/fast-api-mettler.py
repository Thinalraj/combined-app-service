import re
import time
import threading
import serial

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


# ============================================================
# CONFIGURATION
# ============================================================

PORT = "COM5"
BAUDRATE = 9600

READ_COMMAND = b"SI\r\n"
TARE_COMMAND = b"TI\r\n"

NUM_READINGS = 30
SAMPLE_INTERVAL = 0.1
SERIAL_TIMEOUT = 2

API_PORT = 8001


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

    return {
        "weight": weight,
        "unit": unit,
        "status": status,
        "raw": response
    }


def tare_scale(ser):

    response = send_command(
        ser,
        TARE_COMMAND
    )

    return response


def read_average(ser):

    values = []
    statuses = []
    unit = None

    for _ in range(NUM_READINGS):

        try:

            result = read_single_weight(ser)

            values.append(
                result["weight"]
            )

            statuses.append(
                result["status"]
            )

            unit = result["unit"]

        except RuntimeError:
            pass

        time.sleep(
            SAMPLE_INTERVAL
        )

    if not values:
        raise RuntimeError(
            "No valid readings received"
        )

    average = sum(values) / len(values)

    return {
        "average": round(average, 3),
        "minimum": round(min(values), 3),
        "maximum": round(max(values), 3),
        "range": round(
            max(values) - min(values),
            3
        ),
        "unit": unit,
        "samples_requested": NUM_READINGS,
        "samples_valid": len(values),
        "stable_samples": statuses.count("S"),
        "dynamic_samples": statuses.count("D"),
        "samples": values
    }


# ============================================================
# API ENDPOINTS
# ============================================================


# ------------------------------------------------------------
# 1. GET SINGLE WEIGHT
# ------------------------------------------------------------

@app.get("/weight")
def get_weight():

    with serial_lock:

        try:

            with open_serial() as ser:

                result = read_single_weight(
                    ser
                )

                return {
                    "success": True,
                    **result
                }

        except serial.SerialException as e:

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
def get_average_weight():

    with serial_lock:

        try:

            with open_serial() as ser:

                result = read_average(
                    ser
                )

                return {
                    "success": True,
                    **result
                }

        except serial.SerialException as e:

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

    with serial_lock:

        try:

            with open_serial() as ser:

                response = tare_scale(
                    ser
                )

                return {
                    "success": True,
                    "command": "TI",
                    "response": response
                }

        except serial.SerialException as e:

            raise HTTPException(
                status_code=503,
                detail=f"Serial port error: {e}"
            )


# ------------------------------------------------------------
# 4. TARE + AVERAGE
# ------------------------------------------------------------

@app.post("/tare-average")
def tare_and_average():

    with serial_lock:

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
                    "tare_response": tare_response,
                    **result
                }

        except serial.SerialException as e:

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