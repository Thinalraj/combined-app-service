"""REFERENCE-01: known-gold 916/999 reference matching; never a gold gate.

This adapter uses the supplied pipeline's original seven columns. Raw single-
waveform RMS/air values stay separate from corrected or mirrored CH1/CH2 data.
No new training, silent feature imputation, mask-area substitution or cross-
version estimator conversion is performed.
"""
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import threading
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import system_assets as assets
from acceptance_policy import MIN_CONFIDENCE

NUMERIC = ["f1_delta_pct","f2_delta_pct","f3_delta_pct","f4_delta_pct","area_mm2","thickness_mm"]
CATEGORICAL = ["shape"]
METHOD = "Known-gold 916/999 reference matching (uncalibrated score)"
DEFAULTS = {"adapter":"gold_reference_v1", "model_path":"metal/signal_plus_geometry.joblib",
            "min_score":.90,"frequency_hz":[8000,10000,15000,20000],
            "amplitude_v_peak":1.,"signal_definition":"raw_ac_rms_v_delta_pct","profile_confirmed":False,"profile_model_sha256":None}


def finite(value, name, positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or (positive and value<=0):
        raise ValueError("Invalid " + name)
    return float(value)


def configuration(value=None):
    value=assets.read_json("reference_model.json",DEFAULTS) if value is None else value
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):
        raise ValueError("Unexpected reference-model settings")
    cfg={**DEFAULTS,**value}
    if cfg["adapter"]!="gold_reference_v1" or cfg["signal_definition"]!="raw_ac_rms_v_delta_pct":
        raise ValueError("Unsupported reference adapter or signal definition")
    assets.asset_path(cfg["model_path"],".joblib")
    cfg["min_score"]=finite(cfg["min_score"],"reference threshold")
    if not .8<=cfg["min_score"]<=1:
        raise ValueError("Reference threshold must be between 0.80 and 1.00")
    cfg["min_score"]=max(MIN_CONFIDENCE,cfg["min_score"])  # NUC-02: retain old profile/hash, raise floor.
    hz=cfg["frequency_hz"]
    if not isinstance(hz,list) or len(hz)!=4 or any(isinstance(v,bool) or v not in (8000,10000,15000,20000) for v in hz) or len(set(hz))!=4:
        raise ValueError("Declare four distinct supported F1-F4 frequencies in Hz")
    cfg["amplitude_v_peak"]=finite(cfg["amplitude_v_peak"],"amplitude",positive=True)
    if cfg["amplitude_v_peak"]>5 or not isinstance(cfg["profile_confirmed"],bool):
        raise ValueError("Amplitude must be 0–5 V peak; profile confirmation must be boolean")
    digest=cfg["profile_model_sha256"]
    if digest is not None and (not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest)):
        raise ValueError("Invalid confirmed-model hash")
    return cfg


def raw_step(payload,command):
    """Preserve the native Signal API values BEFORE display/DAQ corrections."""
    stats=payload.get("statistics",{})
    rms=stats.get("ac_rms_v",{}) if isinstance(stats,dict) else {}
    return {"frequency_command":command,"frequency_hz":payload.get("frequency_hz"),
            "amplitude_v_peak":payload.get("amplitude_v"),"simulate":payload.get("simulate"),
            "ac_rms_v":rms.get("mean") if isinstance(rms,dict) else None,
            "std_v":rms.get("std_dev") if isinstance(rms,dict) else None,
            "sample_size":payload.get("sample_size"),"source":"adp2230_raw_ac_rms_v"}


def feature_row(collection,calibration,shape,area_mm2,thickness_mm,cfg,validate_geometry=True):
    if not cfg["profile_confirmed"]:
        raise ValueError("Confirm the training frequency/amplitude/raw-RMS profile in Engineering")
    if collection.get("mode")!="signal_service" or calibration.get("acquisition_mode")!="signal_service":
        raise ValueError("Raw Signal-service capture and fresh four-frequency air calibration are required")
    shape=str(shape).strip().title()
    if shape not in ("Coin","Bar"):
        raise ValueError("This reference model supports Coin and Bar only")
    # NUC-05: preflight can validate acquisition with optional geometry.
    # Actual prediction still requires real positive geometry; no dummy/imputed input.
    row={"shape":shape,"area_mm2":finite(area_mm2,"formula area",True) if validate_geometry else area_mm2,
         "thickness_mm":finite(thickness_mm,"thickness",True) if validate_geometry else thickness_mm}
    sequence=collection.get("reference_signal_sequence")
    air=calibration.get("reference_signal_sequence")
    def mapping(values):
        if not isinstance(values,list) or len(values)!=4 or any(not isinstance(v,dict) for v in values):
            raise ValueError("Missing raw F1-F4 values; run air calibration again after updating Signal/View")
        mapped={v.get("frequency_command"):v for v in values}
        if set(mapped)!={"f1","f2","f3","f4"}:
            raise ValueError("Missing or duplicate frequency slots")
        return mapped
    measured,baseline=mapping(sequence),mapping(air);modes=[];used=[]
    for index,hz in enumerate(cfg["frequency_hz"],1):
        key=f"f{index}";current,zero=measured[key],baseline[key]
        for value in (current,zero):
            if value.get("source")!="adp2230_raw_ac_rms_v" or finite(value.get("frequency_hz"),"frequency")!=hz:
                raise ValueError(key+" frequency/source differs from the selected training profile")
            if abs(finite(value.get("amplitude_v_peak"),"amplitude")-cfg["amplitude_v_peak"])>1e-6:
                raise ValueError(key+" amplitude differs from the selected training profile")
            if not isinstance(value.get("simulate"),bool):
                raise ValueError("Signal mode metadata missing; update/restart port 8001 and recalibrate")
            count=value.get("sample_size")
            if isinstance(count,bool) or not isinstance(count,int) or count<2:
                raise ValueError("Averaged signal samples are required")
            modes.append(value["simulate"])
        rms=finite(current.get("ac_rms_v"),key+" raw RMS",True)
        air_rms=finite(zero.get("ac_rms_v"),key+" air RMS",True)
        row[key+"_delta_pct"]=(rms-air_rms)/air_rms*100
        used.append({"slot":key,"frequency_hz":hz,"rms_v":rms,"air_rms_v":air_rms,
                     "delta_pct":row[key+"_delta_pct"]})
    if len(set(modes))!=1:
        raise ValueError("Air and object captures mix simulator/hardware modes; recalibrate")
    return row,{"simulation":modes[0],"frequencies":used,"area_definition":"coin pi*d^2/4; bar width*length; NOT segmentation area"}


def unavailable(message):
    return {"prediction":"Unable to determine","nearest_class":None,"result_type":"unknown",
        "accepted":False,"uncertain":True,"reference_only":True,"gold_identity_verified":False,
        "scores_are_calibrated":False,"reference_grade":None,"confidence":0.,"nearest_gap":0.,
        "distance":1.,"threshold":80.,"top_matches":[],"all_matches":[],"feature_version":1,
        "classification_method":METHOD,"decision_message":str(message),"gold_prediction":None,
        "purity_prediction":None,"material_result":"Gold identity not determined","purity_result":None}


class ReferenceModel:
    def __init__(self):
        self.lock=threading.RLock();self.key=None;self.bundle=None;self.metadata=None

    def _load(self,path):
        path=assets.asset_path(path,".joblib",must_exist=True);stat=path.stat()
        key=(str(path),stat.st_size,stat.st_mtime_ns)
        if key==self.key and self.bundle is not None:return
        try:
            import joblib
            import sklearn
            from sklearn.exceptions import InconsistentVersionWarning
            raw=path.read_bytes()
            with warnings.catch_warnings():
                warnings.simplefilter("error",InconsistentVersionWarning)
                bundle=joblib.load(io.BytesIO(raw))
        except ImportError as exc:
            raise ValueError("Reference model needs joblib, pandas and scikit-learn in View Python") from exc
        except Exception as exc:
            saved=getattr(exc,"original_sklearn_version",None)
            advice=(" Saved with scikit-learn "+saved+"; use that version and restart View.") if saved else " Check the training environment; the supplied reference file uses scikit-learn 1.6.1."
            raise ValueError("Reference model could not load."+advice+" "+str(exc)) from exc
        if not isinstance(bundle,dict) or bundle.get("numeric_features")!=NUMERIC or bundle.get("categorical_features")!=CATEGORICAL or bundle.get("labels")!=[916,999]:
            raise ValueError("Expected the gold_reference_v1 pipeline bundle with the documented seven columns")
        if bundle.get("sklearn_version")!=sklearn.__version__:
            raise ValueError("Use the model's saved scikit-learn version: "+str(bundle.get("sklearn_version")))
        pipeline=bundle.get("pipeline")
        if not callable(getattr(pipeline,"predict_proba",None)) or [int(v) for v in pipeline.classes_]!=[916,999]:
            raise ValueError("Reference model must return class scores in 916/999 order")
        preprocessor=pipeline.named_steps.get("features")
        selectors={name:list(columns) for name,_,columns in preprocessor.transformers_ if name!="remainder"}
        if selectors!={"numeric":NUMERIC,"shape":CATEGORICAL} or preprocessor.remainder!="drop":
            raise ValueError("Pipeline's actual selected inputs differ from its declared reference schema")
        categories=preprocessor.named_transformers_["shape"].categories_
        if len(categories)!=1 or set(categories[0])!={"Bar","Coin"}:
            raise ValueError("Reference shape encoder must support Bar/Coin")
        threshold=finite(bundle.get("score_threshold"),"bundle threshold")
        if not .5<threshold<=1:raise ValueError("Invalid saved reference threshold")
        self.bundle=bundle;self.key=key
        self.metadata={"adapter":"gold_reference_v1","model_file":path.relative_to(assets.ROOT).as_posix(),
            "model_sha256":hashlib.sha256(raw).hexdigest(),"numeric_features":NUMERIC,"categorical_features":CATEGORICAL,
            "labels":[916,999],"sklearn_version":sklearn.__version__,"bundle_threshold":threshold,
            "evaluation_mode":bundle.get("evaluation_mode"),"reference_only":True,"scores_are_calibrated":False}

    def validate(self,cfg):
        with self.lock:
            self._load(cfg["model_path"])
            return {"ok":True,**self.metadata,"effective_threshold":max(MIN_CONFIDENCE,cfg["min_score"],self.metadata["bundle_threshold"])}

    def predict(self,row,evidence,cfg):
        with self.lock:
            self._load(cfg["model_path"])
            if cfg.get("profile_model_sha256")!=self.metadata["model_sha256"]:
                raise ValueError("Reference file changed; reconfirm its acquisition profile and select it again")
            # Refuse missing/NaN features before the stored imputer can substitute values.
            if set(row)!=set(NUMERIC+CATEGORICAL) or row["shape"] not in ("Coin","Bar"):
                raise ValueError("Invalid reference input columns/shape")
            for name in NUMERIC:finite(row[name],name,name in ("area_mm2","thickness_mm"))
            import numpy as np
            import pandas as pd
            values=np.asarray(self.bundle["pipeline"].predict_proba(pd.DataFrame([row])),dtype=float)
            if values.shape!=(1,2) or not np.isfinite(values).all() or (values<0).any() or (values>1).any() or not np.isclose(values.sum(),1):
                raise ValueError("Reference pipeline returned invalid class scores")
            scores=values[0];best=int(np.argmax(scores));grade=[916,999][best];score=float(scores[best])
            threshold=max(MIN_CONFIDENCE,cfg["min_score"],self.metadata["bundle_threshold"])
            simulation=evidence["simulation"] is True;accepted=score>=threshold and not simulation
            prediction=f"{grade} reference match" if accepted else "Unable to determine"
            if simulation:prediction=f"Simulation only: {grade} reference match"
            top=sorted([{ "material":f"{label} reference match","match_percent":float(value)*100,
                          "distance":1-float(value)} for label,value in zip([916,999],scores)],key=lambda item:-item["match_percent"])
            for rank,item in enumerate(top,1):item["rank"]=rank
            message=("Simulation only; no physical reference decision." if simulation else
                     "Uncalibrated reference matching score below threshold." if not accepted else
                     f"{grade} reference match at uncalibrated score {score*100:.2f}%.")
            message+=" Gold identity and actual purity are not established; review independent evidence."
            return {**unavailable(message),"prediction":prediction,"nearest_class":f"{grade} reference match",
                "result_type":"simulation" if simulation else "reference_match" if accepted else "unknown",
                "accepted":accepted,"uncertain":not accepted,"reference_grade":grade if accepted else None,
                "nearest_reference_grade":grade,"confidence":score*100,"score":score,"threshold":threshold*100,
                "distance":1-score,"nearest_gap":abs(float(scores[0]-scores[1])),"top_matches":top,"all_matches":top,
                "simulation":simulation,"feature_names":NUMERIC,"categorical_features":{"shape":row["shape"]},"input_row":row,
                "feature_vector":[row[name] for name in NUMERIC],"model_version":"gold_reference_v1:"+self.metadata["model_sha256"][:16],
                "model_metadata":dict(self.metadata),"acquisition_evidence":evidence}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Reference model only: no scale/camera/frequency commands")
    parser.add_argument("--input",help="JSON file with all seven model input fields; omit to inspect model")
    args=parser.parse_args()
    try:
        cfg=configuration();model=ReferenceModel()
        result=model.validate(cfg) if not args.input else model.predict(json.loads(Path(args.input).read_text()),{"simulation":False,"source":"offline_user_supplied_features"},cfg)
        if args.input:result["offline_check"]=True
        print(json.dumps(result,indent=2,allow_nan=False))
    except Exception as exc:parser.exit(1,"Reference checker: "+str(exc)+"\n")
