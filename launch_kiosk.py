"""NUC-03: supervise one dedicated Chrome instance; Exit closes only that tree.

No Flask/SDK imports required. Does not stop any backend service or personal
Chrome window. Each launch gets a unique profile so Chrome cannot forward the
launch to an existing process and silently abandon our process handle.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"service"))
from kiosk_control import control_path


def close_owned_browser(child):
    if child.poll() is not None:
        return
    if os.name == "nt":
        # PID belongs to our live Popen handle, not to a stale file or client.
        subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    else:
        child.terminate()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target",default="127.0.0.1")
    args=parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9.-]+",args.target):
        raise ValueError("Use a hostname or IPv4 address")
    candidates=[Path(os.environ.get(key,""))/suffix for key,suffix in
        (("ProgramFiles","Google/Chrome/Application/chrome.exe"),
         ("ProgramFiles(x86)","Google/Chrome/Application/chrome.exe"),
         ("LOCALAPPDATA","Google/Chrome/Application/chrome.exe"))]
    executable=next((p for p in candidates if p.is_file()),None)
    if executable is None:
        raise FileNotFoundError("Chrome not found; open http://"+args.target+":8080 manually")
    token=secrets.token_urlsafe(32)
    state=control_path(ROOT)
    exit_path=state.with_suffix(".exit")
    # OS locks are released even after a crash/power loss. Stale JSON is safe
    # to replace only after acquiring this copy's supervisor lock.
    lock_file=state.with_suffix(".lock").open("a+b")
    lock_file.seek(0); lock_file.write(b"0"); lock_file.flush(); lock_file.seek(0)
    try:
        if os.name=="nt":
            import msvcrt
            msvcrt.locking(lock_file.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        raise RuntimeError("A kiosk from this folder is already open. Use its Exit button first.")
    child=None
    try:
        with state.open("w",encoding="utf-8") as f:
            json.dump({"token":token,"supervisor_pid":os.getpid()},f)
        exit_path.unlink(missing_ok=True)
        # Persistent profile directory survives neither this process nor its
        # unique launch. No personal Chrome profile is opened or modified.
        with tempfile.TemporaryDirectory(prefix="afis-kiosk-profile-",ignore_cleanup_errors=True) as profile:
            child=subprocess.Popen([str(executable),"--kiosk","--start-fullscreen","--new-window",
                "--no-first-run","--disable-session-crashed-bubble","--user-data-dir="+profile,
                "http://"+args.target+":8080/#kiosk="+token])
            while child.poll() is None:
                try:
                    close_requested=exit_path.read_text(encoding="utf-8")==token
                except OSError:
                    close_requested=False
                if close_requested:
                    time.sleep(.75) # Let the HTTP response reach the browser.
                    close_owned_browser(child)
                    break
                time.sleep(.25)
    finally:
        if child is not None:
            close_owned_browser(child)
        state.unlink(missing_ok=True)
        exit_path.unlink(missing_ok=True)
        lock_file.close()


if __name__=="__main__":
    main()
