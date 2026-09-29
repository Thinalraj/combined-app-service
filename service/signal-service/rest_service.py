"""
FastAPI backend for Digilent ADP2230
=====================================

Endpoints
---------
POST /api/start
    Start sine wave.
    JSON:
    {
        "frequency": 10000,
        "amplitude": 1.0
    }

POST /api/stop
    Stop sine wave and close ADP2230.

GET /api/measurement
    Get one measurement while sine wave is running.

POST /api/sample
    Get N measurements with interval T.
    JSON:
    {
        "number_of_samples": 30,
        "interval": 0.1
    }

Run:
    python fast-api-signal.py

Server:
    http://127.0.0.1:8001

Swagger:
    http://127.0.0.1:8001/docs
"""

from __future__ import annotations

import math
import os
import sys
import time
import threading

import numpy as np
import uvicorn

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ============================================================
# CONFIGURATION
# ============================================================

WAVEFORMS_SDK_ROOT = r"C:\Program Files\Digilent\WaveFormsSDK"

HOST = "127.0.0.1"
PORT = 8001


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="ADP2230 Signal API",
    version="1.0.0",
)


# ============================================================
# REQUEST MODELS
# ============================================================

class StartRequest(BaseModel):
    frequency: float
    amplitude: float


class SampleRequest(BaseModel):
    number_of_samples: int
    interval: float


# ============================================================
# WAVEFORMS SDK SETUP
# ============================================================

def configure_waveforms_sdk():

    sdk_root = os.environ.get(
        "WAVEFORMS_SDK_ROOT",
        WAVEFORMS_SDK_ROOT,
    )

    sdk_python = os.path.join(
        sdk_root,
        "samples",
        "py",
    )

    sdk_lib = os.path.join(
        sdk_root,
        "lib",
        "x64",
    )

    if not os.path.isdir(sdk_lib):
        sdk_lib = os.path.join(
            sdk_root,
            "lib",
        )

    if sdk_python not in sys.path:
        sys.path.insert(
            0,
            sdk_python,
        )

    if os.path.isdir(sdk_lib):

        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(
                sdk_lib
            )

        os.environ["PATH"] = (
            sdk_lib
            + os.pathsep
            + os.environ.get(
                "PATH",
                "",
            )
        )


# ============================================================
# SIGNAL PROCESSING
# ============================================================

def calculate_measurement(
    samples: list[float],
    sample_rate: float,
) -> dict:

    if not samples:
        raise ValueError(
            "No ADC samples acquired"
        )

    values = np.asarray(
        samples,
        dtype=float,
    )

    # --------------------------------------------------------
    # DC component
    # --------------------------------------------------------

    dc = float(
        np.mean(values)
    )

    # Remove DC
    ac = values - dc

    # --------------------------------------------------------
    # AC RMS
    # --------------------------------------------------------

    rms = float(
        np.sqrt(
            np.mean(ac ** 2)
        )
    )

    # --------------------------------------------------------
    # Peak amplitude
    # --------------------------------------------------------

    peak = float(
        np.max(
            np.abs(ac)
        )
    )

    # --------------------------------------------------------
    # Peak-to-peak
    # --------------------------------------------------------

    p2p = float(
        np.max(values)
        - np.min(values)
    )

    # --------------------------------------------------------
    # Frequency using FFT
    # --------------------------------------------------------

    spectrum = np.abs(
        np.fft.rfft(ac)
    )

    spectrum[0] = 0.0

    peak_bin = int(
        np.argmax(spectrum)
    )

    frequency = (
        peak_bin
        * sample_rate
        / len(ac)
    )

    # Parabolic interpolation
    if 0 < peak_bin < len(spectrum) - 1:

        left = spectrum[peak_bin - 1]
        center = spectrum[peak_bin]
        right = spectrum[peak_bin + 1]

        denominator = (
            left
            - 2 * center
            + right
        )

        if denominator != 0:

            correction = (
                0.5
                * (left - right)
                / denominator
            )

            frequency = (
                (peak_bin + correction)
                * sample_rate
                / len(ac)
            )

    return {
        "ac_rms_v": rms,
        "peak_amplitude_v": peak,
        "peak_to_peak_v": p2p,
        "frequency_hz": float(frequency),
        "dc_v": dc,
    }


# ============================================================
# ADP2230 HARDWARE
# ============================================================

class WaveFormsADP2230:

    def __init__(self):

        configure_waveforms_sdk()

        from ctypes import (
            byref,
            c_double,
            c_int,
            cdll,
            create_string_buffer,
        )

        from dwfconstants import (
            DwfStateDone,
            hdwfNone,
        )

        self.c_double = c_double
        self.c_int = c_int
        self.byref = byref

        self.DwfStateDone = DwfStateDone
        self.hdwfNone = hdwfNone

        self.dwf = cdll.dwf

        # ----------------------------------------------------
        # WaveForms version
        # ----------------------------------------------------

        version = create_string_buffer(16)

        self.dwf.FDwfGetVersion(
            version
        )

        self.version = version.value.decode(
            errors="ignore"
        )

        # ----------------------------------------------------
        # Detect device
        # ----------------------------------------------------

        devices = c_int()

        self.dwf.FDwfEnum(
            c_int(0),
            byref(devices),
        )

        if devices.value == 0:
            raise RuntimeError(
                "No WaveForms device detected"
            )

        # ----------------------------------------------------
        # Open first device
        # ----------------------------------------------------

        self.hdwf = c_int()

        self.dwf.FDwfDeviceOpen(
            c_int(0),
            byref(self.hdwf),
        )

        if self.hdwf.value == hdwfNone.value:
            raise RuntimeError(
                "Could not open ADP2230"
            )

        # ----------------------------------------------------
        # Disable automatic configuration
        # ----------------------------------------------------

        self.dwf.FDwfDeviceAutoConfigureSet(
            self.hdwf,
            c_int(0),
        )

        # ----------------------------------------------------
        # Analog input configuration
        #
        # Same configuration as working example:
        #
        # 100 kHz
        # +/- 4 V range
        # 1000 samples
        # ----------------------------------------------------

        self.dwf.FDwfAnalogInFrequencySet(
            self.hdwf,
            c_double(100_000),
        )

        self.dwf.FDwfAnalogInChannelRangeSet(
            self.hdwf,
            c_int(-1),
            c_double(4),
        )

        self.dwf.FDwfAnalogInBufferSizeSet(
            self.hdwf,
            c_int(1000),
        )

        self.dwf.FDwfAnalogInConfigure(
            self.hdwf,
            c_int(1),
            c_int(0),
        )

        # Allow analog input to stabilize
        time.sleep(2)

    # ========================================================
    # START SINE
    # ========================================================

    def start_sine(
        self,
        frequency: float,
        amplitude: float,
    ):

        # Enable WaveGen channel 1
        self.dwf.FDwfAnalogOutEnableSet(
            self.hdwf,
            self.c_int(0),
            self.c_int(1),
        )

        # Function = sine
        self.dwf.FDwfAnalogOutFunctionSet(
            self.hdwf,
            self.c_int(0),
            self.c_int(1),
        )

        # Set frequency
        self.dwf.FDwfAnalogOutFrequencySet(
            self.hdwf,
            self.c_int(0),
            self.c_double(frequency),
        )

        # Set amplitude (V peak)
        self.dwf.FDwfAnalogOutAmplitudeSet(
            self.hdwf,
            self.c_int(0),
            self.c_double(amplitude),
        )

        # Start output
        self.dwf.FDwfAnalogOutConfigure(
            self.hdwf,
            self.c_int(0),
            self.c_int(1),
        )

    # ========================================================
    # ACQUIRE
    # ========================================================

    def acquire(self):

        from ctypes import c_double

        count = 1000

        # Start fresh ADC acquisition
        self.dwf.FDwfAnalogInConfigure(
            self.hdwf,
            self.c_int(1),
            self.c_int(1),
        )

        state = self.c_int()

        # Wait until acquisition is complete
        while True:

            self.dwf.FDwfAnalogInStatus(
                self.hdwf,
                self.c_int(1),
                self.byref(state),
            )

            if (
                state.value
                == self.DwfStateDone.value
            ):
                break

            time.sleep(0.01)

        # ----------------------------------------------------
        # Read Analog In Channel 1
        # SDK index 0 = Channel 1
        # ----------------------------------------------------

        buffer = (
            c_double * count
        )()

        self.dwf.FDwfAnalogInStatusData(
            self.hdwf,
            self.c_int(0),
            buffer,
            count,
        )

        # ----------------------------------------------------
        # Actual ADC sample rate
        # ----------------------------------------------------

        actual_rate = self.c_double()

        self.dwf.FDwfAnalogInFrequencyGet(
            self.hdwf,
            self.byref(actual_rate),
        )

        return (
            list(buffer),
            actual_rate.value,
        )

    # ========================================================
    # STOP
    # ========================================================

    def stop_sine(self):

        self.dwf.FDwfAnalogOutReset(
            self.hdwf,
            self.c_int(0),
        )

        self.dwf.FDwfDeviceCloseAll()


# ============================================================
# CONTROLLER
# ============================================================

class Controller:

    def __init__(self):

        self.instrument = None

        self.lock = threading.Lock()

        self.running = False

        self.frequency = None
        self.amplitude = None

    # --------------------------------------------------------
    # Start
    # --------------------------------------------------------

    def start(
        self,
        frequency: float,
        amplitude: float,
    ):

        if frequency <= 0:
            raise ValueError(
                "Frequency must be greater than 0 Hz"
            )

        if not 0 <= amplitude <= 5:
            raise ValueError(
                "Amplitude must be between 0 and 5 V peak"
            )

        with self.lock:

            if self.running:
                raise RuntimeError(
                    "Signal is already running. "
                    "Stop the signal before starting another frequency."
                )

            self.instrument = (
                WaveFormsADP2230()
            )

            self.instrument.start_sine(
                frequency,
                amplitude,
            )

            self.frequency = frequency
            self.amplitude = amplitude

            self.running = True

        return {
            "status": "running",
            "frequency": frequency,
            "amplitude": amplitude,
        }

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    def stop(self):

        with self.lock:

            if self.instrument is not None:

                self.instrument.stop_sine()

                self.instrument = None

            self.running = False

            old_frequency = self.frequency

            self.frequency = None
            self.amplitude = None

        return {
            "status": "stopped",
            "frequency": old_frequency,
        }

    # --------------------------------------------------------
    # Single measurement
    # --------------------------------------------------------

    def measurement(self):

        if not self.running:
            raise RuntimeError(
                "Signal is not running. "
                "Call /api/start first."
            )

        with self.lock:

            samples, sample_rate = (
                self.instrument.acquire()
            )

        result = calculate_measurement(
            samples,
            sample_rate,
        )

        return {
            "frequency_set_hz": self.frequency,
            "amplitude_set_v": self.amplitude,
            "adc_sample_rate_hz": sample_rate,
            "adc_points": len(samples),
            **result,
        }

    # --------------------------------------------------------
    # N measurements
    # --------------------------------------------------------

    def sample(
        self,
        number_of_samples: int,
        interval: float,
    ):

        if not self.running:
            raise RuntimeError(
                "Signal is not running. "
                "Call /api/start first."
            )

        if number_of_samples < 1:
            raise ValueError(
                "number_of_samples must be at least 1"
            )

        if number_of_samples > 1000:
            raise ValueError(
                "Maximum number_of_samples is 1000"
            )

        if interval < 0:
            raise ValueError(
                "Interval cannot be negative"
            )

        results = []

        # ----------------------------------------------------
        # Acquire N measurements
        # ----------------------------------------------------

        for index in range(
            number_of_samples
        ):

            with self.lock:

                samples, sample_rate = (
                    self.instrument.acquire()
                )

            measurement = (
                calculate_measurement(
                    samples,
                    sample_rate,
                )
            )

            measurement[
                "sample_number"
            ] = index + 1

            results.append(
                measurement
            )

            # Wait between measurements
            if (
                index + 1
                < number_of_samples
            ):
                time.sleep(interval)

        # ----------------------------------------------------
        # Statistics
        # ----------------------------------------------------

        statistics = {}

        metrics = [
            "ac_rms_v",
            "peak_amplitude_v",
            "peak_to_peak_v",
            "frequency_hz",
            "dc_v",
        ]

        for metric in metrics:

            values = np.array(
                [
                    row[metric]
                    for row in results
                ],
                dtype=float,
            )

            statistics[metric] = {
                "mean": float(
                    np.mean(values)
                ),
                "std": float(
                    np.std(values)
                ),
                "min": float(
                    np.min(values)
                ),
                "max": float(
                    np.max(values)
                ),
            }

        return {
            "frequency_set_hz":
                self.frequency,

            "amplitude_set_v":
                self.amplitude,

            "number_of_samples":
                number_of_samples,

            "interval_s":
                interval,

            "measurements":
                results,

            "statistics":
                statistics,
        }


# ============================================================
# CONTROLLER INSTANCE
# ============================================================

controller = Controller()


# ============================================================
# API
# ============================================================

@app.post("/api/start")
def api_start(
    request: StartRequest
):

    try:

        return controller.start(
            request.frequency,
            request.amplitude,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.post("/api/stop")
def api_stop():

    try:

        return controller.stop()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.get("/api/measurement")
def api_measurement():

    try:

        return controller.measurement()

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.post("/api/sample")
def api_sample(
    request: SampleRequest
):

    try:

        return controller.sample(
            request.number_of_samples,
            request.interval,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "service": "ADP2230 Signal API",
        "status": "online",
        "port": PORT,
        "signal_running":
            controller.running,
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
        )

    finally:

        if controller.instrument is not None:

            try:
                controller.stop()

            except Exception:
                pass