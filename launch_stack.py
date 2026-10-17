"""FINISH-01: normal launcher with one Python, explicit mode and port checks.

Uses Windows Terminal tabs when available, separate consoles otherwise.
On Linux/macOS, Ctrl+C stops the four child processes started by this launcher.
This never kills an existing service or changes model/calibration/settings files.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
PORTS={"signal":8001,"weight":8002,"vision":8003,"view":8080}
MODULES={"signal":["fastapi","uvicorn","numpy","tkinter"],"weight":["serial","fastapi","uvicorn"],
         "vision":["pyrealsense2","cv2","numpy","fastapi","uvicorn"],"view":["flask","numpy","scipy","serial","pandas","joblib","sklearn"]}


def runtime():
    cfg=json.loads((ROOT/"system_assets/runtime.json").read_text(encoding="utf-8"))
    if not isinstance(cfg,dict) or set(cfg)!={"signal_mode","python_executable","weight_port","weight_baudrate"}:
        raise ValueError("runtime.json needs signal_mode, python_executable, weight_port and weight_baudrate")
    if cfg["signal_mode"] not in ("hardware","simulate"):raise ValueError("signal_mode must be hardware or simulate")
    if not isinstance(cfg["python_executable"],str):raise ValueError("python_executable must be a string; empty uses current Python")
    if not isinstance(cfg["weight_port"],str) or not cfg["weight_port"].strip():raise ValueError("Set a nonempty weight_port")
    if isinstance(cfg["weight_baudrate"],bool) or not isinstance(cfg["weight_baudrate"],int) or not 300<=cfg["weight_baudrate"]<=921600:raise ValueError("Invalid weight_baudrate")
    return cfg


def python_for(cfg):
    value=cfg["python_executable"] or sys.executable
    if cfg["python_executable"] and not Path(value).is_absolute():raise ValueError("python_executable must be an absolute Python path or empty")
    if not Path(value).is_file():raise ValueError("Python executable not found: "+value)
    return str(Path(value).resolve())


def command(service,cfg,python):
    folder=ROOT/"service"/("image-service" if service=="vision" else service+"-service")
    args={"signal":["rest_service.py"]+(["--simulate"] if cfg["signal_mode"]=="simulate" else []),
          "weight":["fast-api-mettler.py"],"vision":["-m","uvicorn","api:app","--host","0.0.0.0","--port","8003"],"view":["app.py"]}[service]
    return [python,*args],folder


def busy_ports():
    busy=[]
    for port in PORTS.values():
        # Binding catches listeners bound to loopback, wildcard and reserved ports.
        try:
            with socket.socket() as probe:probe.bind(("127.0.0.1",port))
        except OSError:busy.append(port)
    return busy


def dependencies(python):
    modules=sorted({m for names in MODULES.values() for m in names})
    code="import importlib.util,json; print(json.dumps([m for m in "+repr(modules)+" if importlib.util.find_spec(m) is None]))"
    result=subprocess.run([python,"-c",code],text=True,capture_output=True,timeout=20,check=True)
    return json.loads(result.stdout.strip())


def wait_ready(python, timeout=35):
    # Use the selected Python to avoid checking against a different virtual env.
    script='''import json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'service'))
from runtime_status import BUILD
for name,port in [('signal',8001),('weight',8002),('vision',8003),('view',8080)]:
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+('/api/status' if name=='view' else '/status'),timeout=1) as r: data=json.load(r)
 runtime=data.get('runtime',{})
 assert runtime.get('build')==BUILD and runtime.get('service')==name
 assert Path(runtime.get('project_root','')).resolve()==Path(sys.argv[1]).resolve()
 assert Path(runtime.get('python','')).resolve()==Path(sys.executable).resolve()
'''
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            result=subprocess.run([python,"-c",script,str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=6)
            if result.returncode==0:return True
        except subprocess.TimeoutExpired:pass
        time.sleep(1)
    return False


def chrome(target):
    if not re.fullmatch(r"[A-Za-z0-9.-]+",target):raise ValueError("Target must be a hostname or IPv4 address")
    candidates=[Path(os.environ.get(key,""))/suffix for key,suffix in
        (("ProgramFiles","Google/Chrome/Application/chrome.exe"),("ProgramFiles(x86)","Google/Chrome/Application/chrome.exe"),("LOCALAPPDATA","Google/Chrome/Application/chrome.exe"))]
    executable=next((p for p in candidates if p.is_file()),None)
    if executable is None:
        print("Chrome not found. Open http://"+target+":8080 manually.");return
    profile=Path(os.environ.get("LOCALAPPDATA",str(ROOT)))/"CombinedAppKioskProfile"
    subprocess.Popen([str(executable),"--kiosk","--start-fullscreen","--new-window","--no-first-run","--disable-session-crashed-bubble","--user-data-dir="+str(profile),"http://"+target+":8080"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signal-mode",choices=["hardware","simulate"],help="Override runtime.json for this launch only")
    parser.add_argument("--service",choices=list(PORTS),help=argparse.SUPPRESS)
    parser.add_argument("--kiosk",action="store_true")
    parser.add_argument("--target",default="127.0.0.1")
    parser.add_argument("--check",action="store_true",help="Check local dependencies/configuration/ports; do not start anything")
    args=parser.parse_args();cfg=runtime()
    if args.signal_mode:cfg["signal_mode"]=args.signal_mode
    python=python_for(cfg)
    env={**os.environ,"AFIS_WEIGHT_PORT":cfg["weight_port"],"AFIS_WEIGHT_BAUD":str(cfg["weight_baudrate"])}
    if args.service:
        cmd,folder=command(args.service,cfg,python)
        print(f"FINISH-01 {args.service} :{PORTS[args.service]} | {ROOT} | {python} | Signal mode={cfg['signal_mode']}",flush=True)
        child=subprocess.Popen(cmd,cwd=folder,env=env)
        while True:
            try:
                code=child.wait();break
            except KeyboardInterrupt:
                # Windows delivers Ctrl+C to the service too. Allow its cleanup;
                # do not kill it before the generator's shutdown hook can run.
                print("Waiting for service cleanup...",flush=True)
        if os.name=="nt":
            try:input("Service stopped. Read the output above; press Enter to close this tab.")
            except (EOFError,KeyboardInterrupt):pass
        return code
    print(f"Project: {ROOT}\nPython: {python}\nSignal: {cfg['signal_mode']}\nScale: {cfg['weight_port']} @ {cfg['weight_baudrate']}",flush=True)
    if cfg["signal_mode"]=="simulate":print("SIGNAL DEMO ONLY. Camera and scale still require real devices. Results cannot be accepted as physical tests.",flush=True)
    missing=dependencies(python)
    if missing:
        raise ValueError("Missing Python modules: "+", ".join(missing)+". Install with this Python before launching. Reference extras: system_assets/requirements-reference.txt")
    busy=busy_ports()
    if busy:raise ValueError("Ports already occupied/unavailable: "+", ".join(map(str,busy))+". Stop the previous services first; no existing processes were killed.")
    if args.check:print("Configuration, dependency presence and port checks passed. No hardware was opened and no model was loaded.");return 0
    children=[]
    if os.name=="nt":
        runner=[python,str(ROOT/"launch_stack.py"),"--signal-mode",cfg["signal_mode"]]
        if shutil.which("wt.exe"):
            cmd=["wt.exe","-w","new"]
            for index,service in enumerate(PORTS):
                if index:cmd.append(";")
                cmd += ["new-tab","--title",f"{service} {PORTS[service]}","-d",str(ROOT),*runner,"--service",service]
            subprocess.run(cmd,check=True,env=env)
        else:
            for service in PORTS:
                subprocess.Popen([*runner,"--service",service],cwd=ROOT,env=env,creationflags=subprocess.CREATE_NEW_CONSOLE)
        if not wait_ready(python):
            print("Services did not all become ready from this copy. Read the failing service tab; Chrome was not opened. Run system_check.py for details.");return 1
        if args.kiosk:chrome(args.target)
        print("Services running: http://127.0.0.1:8080. Engineering > System Readiness shows remaining setup.");return 0
    try:
        for service in PORTS:
            cmd,folder=command(service,cfg,python);children.append(subprocess.Popen(cmd,cwd=folder,env=env))
        if not wait_ready(python):print("Startup incomplete. Check service errors and system_check.py.");return 1
        print("Stack ready at http://127.0.0.1:8080. Ctrl+C stops this launch.",flush=True)
        while all(child.poll() is None for child in children):time.sleep(.5)
        return 1
    except KeyboardInterrupt:return 0
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait()


if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print("STARTUP FAILED: "+str(exc),file=sys.stderr);raise SystemExit(1)
