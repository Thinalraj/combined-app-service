import re
import time
import threading
from contextlib import asynccontextmanager

import serial
from fastapi import FastAPI, HTTPException


# ============================================================
# CONFIGURATION
# ============================================================

PORT = "COM11"
BAUDRATE = 9600

READ_COMMAND = b"SI\r\n"
TARE_COMMAND = b"TI\r\n"
ZERO_COMMAND = b"ZI\r\n"

NUM_READINGS = 30
SAMPLE_INTERVAL = 0.1
SERIAL_TIMEOUT = 2
WRITE_TIMEOUT = 2

# Reconnect once if the serial link breaks while the program is running.
SERIAL_RETRY_COUNT = 1
SERIAL_RETRY_DELAY = 0.25

# At Windows/login startup the USB serial device may take a moment to appear.
STARTUP_RETRY_COUNT = 10
STARTUP_RETRY_DELAY = 1.0

API_PORT = 8002


# ============================================================
# SINGLETON SERIAL MANAGER
# ============================================================

class SerialManager:
    """
    Owns exactly one serial connection for this FastAPI process.

    The connection is opened when FastAPI starts, remains open for the
    lifetime of the process, and is closed only on shutdown.

    If the USB/serial connection is lost later, reconnect() can rebuild it.
    """

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.connection = None

    @property
    def connected(self) -> bool:
        return (
            self.connection is not None
            and self.connection.is_open
        )

    def connect(self):
        """Open the COM port if it is not already open."""
        if self.connected:
            return self.connection

        self.close()

        self.connection = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=SERIAL_TIMEOUT,
            write_timeout=WRITE_TIMEOUT,
        )

        self.connection.reset_input_buffer()
        self.connection.reset_output_buffer()

        return self.connection

    def close(self):
        """Close and forget the current serial connection."""
        connection = self.connection
        self.connection = None

        if connection is not None:
            try:
                if connection.is_open:
                    connection.close()
            except (serial.SerialException, OSError):
                pass

    def reconnect(self):
        """Discard the old handle and open a fresh one."""
        self.close()
        time.sleep(SERIAL_RETRY_DELAY)
        return self.connect()


# Exactly ONE serial-manager instance exists in this process.
serial_manager = SerialManager(PORT, BAUDRATE)

# Prevent simultaneous scale commands from multiple HTTP requests.
serial_lock = threading.Lock()


class SerialUnavailableError(Exception):
    """Raised when the serial connection cannot be used or recovered."""


# ============================================================
# SERIAL OPERATION WRAPPER
# ============================================================

def run_serial_operation(operation):
    """
    Run one scale operation through the singleton serial connection.

    Normal case:
        use the connection that was opened during FastAPI startup.

    Recovery case:
        if the USB/COM connection breaks, close the stale handle,
        reconnect, and retry the operation once.
    """
    last_error = None

    for attempt in range(SERIAL_RETRY_COUNT + 1):
        try:
            ser = serial_manager.connect()
            return operation(ser)

        except (serial.SerialException, OSError) as exc:
            last_error = exc
            serial_manager.close()

            if attempt < SERIAL_RETRY_COUNT:
                time.sleep(SERIAL_RETRY_DELAY)

    raise SerialUnavailableError(str(last_error))


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Open COM11 once when FastAPI launches and keep it open.

    Startup retries are useful because Windows may need a few seconds to
    enumerate a USB-serial adapter after login/boot.
    """
    last_error = None

    for attempt in range(1, STARTUP_RETRY_COUNT + 1):
        try:
            with serial_lock:
                serial_manager.connect()

            print(
                f"[SERIAL] Connected to {PORT} at {BAUDRATE} baud "
                f"(startup attempt {attempt})."
            )
            last_error = None
            break

        except (serial.SerialException, OSError) as exc:
            last_error = exc
            print(
                f"[SERIAL] Startup connection attempt "
                f"{attempt}/{STARTUP_RETRY_COUNT} failed: {exc}"
            )

            if attempt < STARTUP_RETRY_COUNT:
                time.sleep(STARTUP_RETRY_DELAY)

    if last_error is not None:
        # Fail startup instead of running a scale service with no scale.
        raise RuntimeError(
            f"Could not open {PORT} after {STARTUP_RETRY_COUNT} attempts: "
            f"{last_error}"
        )

    try:
        yield
    finally:
        with serial_lock:
            serial_manager.close()

        print(f"[SERIAL] {PORT} closed.")


app = FastAPI(
    title="WKC Weighing Scale API",
    version="1.3.0",
    lifespan=lifespan,
)


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
        response,
    )

    if not match:
        return None, None, f"Unknown response: {response}"

    status = match.group(1)
    weight = float(match.group(2))
    unit = match.group(3)

    return weight, unit, status


# ============================================================
# SCALE COMMANDS
# ============================================================

def send_command(ser, command):
    # Clear stale input before sending a fresh MT-SICS command.
    ser.reset_input_buffer()

    ser.write(command)
    ser.flush()

    raw = ser.readline()

    return raw.decode(
        "ascii",
        errors="ignore",
    ).strip()


def read_single_weight(ser):
    response = send_command(ser, READ_COMMAND)
    weight, unit, status = parse_weight(response)

    if weight is None:
        raise RuntimeError(status)

    return {
        "weight": weight,
        "unit": unit,
        "status": status,
        "raw": response,
    }


def tare_scale(ser):
    return send_command(ser, TARE_COMMAND)


def zero_scale(ser):
    return send_command(ser, ZERO_COMMAND)


def read_average(ser):
    values = []
    statuses = []
    unit = None

    for _ in range(NUM_READINGS):
        try:
            result = read_single_weight(ser)
            values.append(result["weight"])
            statuses.append(result["status"])
            unit = result["unit"]

        except RuntimeError:
            # Ignore an individual invalid/non-weight reply while averaging.
            # Serial I/O errors still propagate to run_serial_operation().
            pass

        time.sleep(SAMPLE_INTERVAL)

    if not values:
        raise RuntimeError("No valid readings received")

    average = sum(values) / len(values)

    return {
        "average": round(average, 3),
        "minimum": round(min(values), 3),
        "maximum": round(max(values), 3),
        "range": round(max(values) - min(values), 3),
        "unit": unit,
        "samples_requested": NUM_READINGS,
        "samples_valid": len(values),
        "stable_samples": statuses.count("S"),
        "dynamic_samples": statuses.count("D"),
        "samples": values,
    }


# ============================================================
# ERROR HELPERS
# ============================================================

def serial_http_error(exc):
    return HTTPException(
        status_code=503,
        detail=(
            f"Serial port error on {PORT}: {exc}. "
            "Close APW-Link or any other program using the scale."
        ),
    )


# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/weight")
def get_weight():
    with serial_lock:
        try:
            result = run_serial_operation(read_single_weight)

            return {
                "success": True,
                **result,
            }

        except SerialUnavailableError as exc:
            raise serial_http_error(exc)

        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))


@app.get("/weight/average")
def get_average_weight():
    with serial_lock:
        try:
            result = run_serial_operation(read_average)

            return {
                "success": True,
                **result,
            }

        except SerialUnavailableError as exc:
            raise serial_http_error(exc)

        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))


@app.post("/tare")
def tare():
    with serial_lock:
        try:
            response = run_serial_operation(tare_scale)

            return {
                "success": True,
                "command": "TI",
                "response": response,
            }

        except SerialUnavailableError as exc:
            raise serial_http_error(exc)


@app.post("/zero")
def zero():
    with serial_lock:
        try:
            response = run_serial_operation(zero_scale)

            return {
                "success": True,
                "command": "ZI",
                "response": response,
            }

        except SerialUnavailableError as exc:
            raise serial_http_error(exc)


@app.post("/tare-average")
def tare_and_average():
    def operation(ser):
        tare_response = tare_scale(ser)

        # Allow tare to settle slightly before collecting measurements.
        time.sleep(0.5)

        result = read_average(ser)
        return tare_response, result

    with serial_lock:
        try:
            tare_response, result = run_serial_operation(operation)

            return {
                "success": True,
                "tare_response": tare_response,
                **result,
            }

        except SerialUnavailableError as exc:
            raise serial_http_error(exc)

        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# HEALTH / CONNECTION STATUS
# ============================================================

@app.get("/")
def root():
    return {
        "service": "WKC Weighing Scale API",
        "version": "1.3.0",
        "port": PORT,
        "baudrate": BAUDRATE,
        "api_port": API_PORT,
        "serial_connected": serial_manager.connected,
    }


@app.get("/serial/status")
def serial_status():
    return {
        "port": PORT,
        "connected": serial_manager.connected,
        "note": (
            "FastAPI owns the COM port and keeps it open."
            if serial_manager.connected
            else "Serial connection is currently unavailable."
        ),
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn

    # IMPORTANT:
    # Keep exactly one worker because COM11 is an exclusive physical resource.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        workers=1,
    )
