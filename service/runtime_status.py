"""FINISH-01: passive process identity; importing this never opens a sensor."""
import os
from pathlib import Path
import sys

BUILD = "NUC-03"


def identity(service):
    return {"build": BUILD, "service": service, "pid": os.getpid(),
            "project_root": str(Path(__file__).resolve().parent.parent),
            "python": sys.executable, "python_version": sys.version.split()[0]}
