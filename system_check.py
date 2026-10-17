"""FINISH-01: passive readiness, or one explicitly chosen sensor read.

Run from any directory: py <repo>/system_check.py [--only weight --read]
Standard library only. No model deserialization, fitting, tare or internal test.
Signal --read is the sole active test: it produces a short electrical sweep
at F1-F4 and always requests stop; use only with the sensing rig connected.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT / "service"))
import system_assets as assets
from runtime_status import BUILD

NOTE = "Passive status/file checks are not hardware qualification or a gold assay. Model loading/inference and physical accuracy must be tested separately."


def get_json(url, timeout=3., method="GET", payload=None):
    req=urllib.request.Request(url,data=None if payload is None else json.dumps(payload).encode(),
        headers={"Accept":"application/json","Content-Type":"application/json"},method=method)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        value=json.load(response)
    if not isinstance(value,dict):raise ValueError("Expected a JSON object from "+url)
    return value


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build_report(only="all", include_view=True, view_url="http://127.0.0.1:8080", fetch=get_json):
    checks=[]
    def add(name,state,message,details=None):
        checks.append({"name":name,"state":state,"message":message,**({"details":details} if details is not None else {})})
    try:services=assets.api_config()["services"]
    except (ValueError,OSError) as exc:
        return {"checks":[{"name":"API configuration","state":"fail","message":str(exc)}],"ready_for_trial":False,"note":NOTE}
    chosen={k:services[k] for k in ("signal","weight","vision") if only in ("all",k) or (only=="camera" and k=="vision")}
    if only=="all" and include_view:chosen["view"]=view_url
    def probe(item):
        name,url=item
        try:return name,fetch(url.rstrip("/")+("/api/status" if name=="view" else "/status")),None
        except Exception as exc:return name,None,str(exc)
    with ThreadPoolExecutor(max_workers=4) as pool:
        probed=list(pool.map(probe,chosen.items()))
    for name,value,error in probed:
        if error:
            add(name+" service","fail",error);continue
        runtime=value.get("runtime",{})
        runtime=runtime if isinstance(runtime,dict) else {}
        same_root=isinstance(runtime.get("project_root"),str) and os.path.normcase(os.path.realpath(runtime["project_root"]))==os.path.normcase(str(ROOT.resolve()))
        same_python=isinstance(runtime.get("python"),str) and os.path.normcase(os.path.realpath(runtime["python"]))==os.path.normcase(os.path.realpath(sys.executable))
        identity_ok=runtime.get("build")==BUILD and runtime.get("service")==name and same_root and same_python
        add(name+" service","pass" if identity_ok else "fail",
            "Correct patched process, repository and Python" if identity_ok else "Wrong/old service copy or different Python; stop that process and launch this copy",runtime or value)
        if name=="signal":
            add("Signal mode","pass" if value.get("simulate") is False else "fail","Hardware selected" if value.get("simulate") is False else "Signal is simulated or mode metadata is missing")
            add("Signal inputs","pass" if value.get("physical_input_count")==1 else "warn","One acquired scope waveform; legacy HMI CH2 mirrors it. The reference model uses raw F1-F4 once.")
            add("F1-F4 support","pass" if value.get("allowed_frequencies_hz")==[8000,10000,15000,20000] else "fail","Required frequencies: 8000 / 10000 / 15000 / 20000 Hz")
            add("Signal idle","pass" if value.get("running") is False and not value.get("operation_busy") else "fail","Idle; hardware connection is tested only by acquisition" if value.get("running") is False else "Generator active; finish/stop the current operation before testing")
        elif name=="weight":
            prep=value.get("preparation",{});internal=prep.get("startup_internal") or {}
            add("Scale startup internal operation","pass" if internal.get("status")=="completed" else "warn",
                "Completed once this service startup" if internal.get("status")=="completed" else "Not completed, unsupported, or skipped: inspect Prepare Empty Scale",internal)
            good=prep.get("state")=="ready" and prep.get("result",{}).get("zero_verified") is True and not prep.get("needs_recovery")
            add("Scale preparation","pass" if good else "fail","Verified preparation exists; no current mass was sampled" if good else "Complete/recover empty-pan preparation",{"port":value.get("port"),"baudrate":value.get("baudrate"),"state":prep.get("state"),"id":prep.get("id")})
        elif name=="vision":
            add("Camera process","pass" if value.get("camera_running") is True else "fail","Camera opened; no new image acquired by this check",value.get("metadata"))
            try:
                geometry=fetch(services["vision"].rstrip("/")+"/geometry/status")
                add("Empty support reference","pass" if geometry.get("reference_for_current_session") is True else "fail",
                    "Reference belongs to current camera session; recapture if the camera/tray moved" if geometry.get("reference_for_current_session") is True else "Capture an empty-support reference in Engineering",geometry.get("reference"))
            except Exception as exc:add("Empty support reference","fail",str(exc))
        elif name=="view":
            add("HMI acquisition","pass" if value.get("acquisition_mode")=="daq" else "fail","DAQ mode required for the real reference workflow",{"acquisition_mode":value.get("acquisition_mode")})
    if only in ("all","models"):
        try:
            vision=read_json(assets.ROOT/"vision_settings.json",{})
            path=assets.asset_path(vision.get("model_path","vision/coin_bar_seg.pt"),".pt")
            good=vision.get("enabled") is True and path.is_file()
            add("Segmentation asset","pass" if good else "fail","Selected local file present; validate/test in Engineering" if good else "Copy .pt into system_assets/vision, scan, validate and enable YOLO",{"model_path":vision.get("model_path"),"enabled":vision.get("enabled"),"accept_confidence":vision.get("acceptance_confidence")})
            for package in ("torch","ultralytics"):
                add(package,"pass" if importlib.util.find_spec(package) is not None else "fail","Module present; inference compatibility untested" if importlib.util.find_spec(package) is not None else "Install in the service Python before testing the .pt")
        except Exception as exc:add("Segmentation asset","fail",str(exc))
        try:
            cfg=read_json(assets.ROOT/"reference_model.json",{})
            path=assets.asset_path(cfg.get("model_path","metal/signal_plus_geometry.joblib"),".joblib",True)
            good=cfg.get("profile_confirmed") is True and cfg.get("profile_model_sha256")==hashlib.sha256(path.read_bytes()).hexdigest()
            add("Reference asset/profile","pass" if good else "fail","File matches previously validated/confirmed model hash" if good else "Validate/select the joblib and confirm its acquisition profile",{"model_path":cfg.get("model_path"),"threshold":cfg.get("min_score")})
            version=importlib.metadata.version("scikit-learn")
            add("Reference dependencies","pass" if version=="1.6.1" else "fail","scikit-learn "+version+"; supplied model requires 1.6.1")
            for package in ("pandas","joblib"):
                add(package,"pass","Installed "+importlib.metadata.version(package))
            sys.path.insert(0,str(ROOT/"service/view-service"))
            from gold_reference import configuration,feature_row
            cfg=configuration(cfg)
            cal=read_json(ROOT/"service/view-service/calibration.json",{})
            _,proof=feature_row({"mode":cal.get("acquisition_mode"),"reference_signal_sequence":cal.get("reference_signal_sequence")},cal,"Coin",1.,1.,cfg)
            add("Raw F1-F4 air calibration","fail" if proof["simulation"] else "pass","Simulated baseline: recalibrate with hardware" if proof["simulation"] else "Four real raw-RMS air values match the selected profile")
            settings=read_json(ROOT/"service/view-service/settings.json",{})
            matches=settings.get("service_mode_enabled",True) is True and settings.get("classifier_algorithm")=="gold_reference_v1" and settings.get("acquisition_mode")=="daq" and [v*1000 for v in settings.get("multi_frequencies_khz",[])]==cfg["frequency_hz"]
            add("Reference workflow settings","pass" if matches else "fail","Select reference mode, DAQ + services and matching F1-F4 slots")
        except Exception as exc:add("Reference setup","fail",str(exc))
    return {"checks":checks,"ready_for_trial":all(c["state"]=="pass" for c in checks),"note":NOTE,
            "channel_note":"One native acquired scope waveform. Legacy HMI CH2 mirrors it; reference model uses raw F1-F4 once."}


def sensor_read(only, fetch=get_json):
    services=assets.api_config()["services"]
    if only not in ("signal","weight","camera"):raise ValueError("--read requires --only signal, weight or camera")
    name="vision" if only=="camera" else only
    status=fetch(services[name].rstrip("/")+"/status")
    if status.get("runtime",{}).get("build")!=BUILD:
        raise ValueError("Restart the selected sensor service with FINISH-01 before the active test")
    if only=="weight":
        value=fetch(services["weight"].rstrip("/")+"/weight/average?samples=5",timeout=25.)
        if value.get("success") is not True or value.get("samples_valid")!=5 or value.get("stable_samples")!=5 or value.get("unit")!="g":raise ValueError("Five stable gram readings were not returned")
        return value
    if only=="camera":return fetch(services["vision"].rstrip("/")+"/camera/debug",timeout=10.)
    url=services["signal"].rstrip("/")
    if status.get("running") is not False or status.get("operation_busy"):raise ValueError("Signal is already active or status is unknown; close other acquisitions first")
    readings=[]
    try:
        for hz in (8000,10000,15000,20000):
            readings.append(fetch(url+f"/measurement/average?frequency_hz={hz}&sample_size=3&interval_s=0&amplitude_v=1",timeout=20.))
    finally:
        # If the HTTP response was lost, never assume the output stopped by itself.
        stopped=fetch(url+"/sine/stop",timeout=5.,method="POST",payload={})
        if stopped.get("running") is not False:raise RuntimeError("Signal stop not confirmed; inspect/stop the physical generator")
    for hz,value in zip((8000,10000,15000,20000),readings):
        rms=value.get("statistics",{}).get("ac_rms_v",{}).get("mean")
        if value.get("frequency_hz")!=hz or not isinstance(value.get("simulate"),bool) or not isinstance(rms,(int,float)) or not math.isfinite(rms) or rms<=0:
            raise ValueError("Incomplete/invalid Signal measurement response")
    return {"simulation":any(v["simulate"] for v in readings),"readings":readings,"note":"Diagnostic only; this does not save an air calibration"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only",choices=["all","signal","weight","camera","models"],default="all")
    parser.add_argument("--read",action="store_true",help="Explicit sensor test. Signal generates 1 V peak at four frequencies; stop other acquisitions first")
    parser.add_argument("--json",action="store_true",help="Print JSON to stdout")
    parser.add_argument("--view-url",default="http://127.0.0.1:8080")
    args=parser.parse_args()
    try:
        if args.read:
            result=sensor_read(args.only);print(json.dumps(result,indent=2));return 0
        result=build_report(args.only,view_url=args.view_url)
        if args.json:print(json.dumps(result,indent=2))
        else:
            for check in result["checks"]:print(f'{check["state"].upper():4}  {check["name"]}: {check["message"]}')
            print("\n"+result["note"])
            if result.get("channel_note"):print(result["channel_note"])
        return 0 if result["ready_for_trial"] else 1
    except Exception as exc:
        print("CHECK FAILED: "+str(exc),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
