"""GEOMETRY-01: server-owned geometry evidence and separate density plausibility.

No learned feature inputs or purity labels are changed by these estimates.
"""
import math


def density_check(geometry, weight):
    result={"available":False,"mass_g":None,"density_g_cm3":None,"deviation_pct":None,
            "reference_g_cm3":geometry["settings"]["pure_gold_density_g_cm3"],
            "tolerance_pct":geometry["settings"]["density_tolerance_pct"],
            "verdict":"unavailable","note":"Pure-gold reference only; does not identify gold or determine 916/999 purity."}
    if not weight.get("ok") or weight.get("stable") is not True:
        result["message"]="Stable averaged mass unavailable";return result
    mass=weight.get("weight_g");volume=geometry.get("volume_mm3")
    if not isinstance(mass,(int,float)) or not math.isfinite(mass) or mass<=0:
        result["message"]="Positive stable mass required";return result
    result["mass_g"]=float(mass)
    if not isinstance(volume,(int,float)) or not math.isfinite(volume) or volume<=0:
        result["message"]="Volume unavailable; use known thickness";return result
    density=mass*1000/volume
    deviation=100*(density/result["reference_g_cm3"]-1)
    verdict="within_reference_tolerance" if abs(deviation)<=result["tolerance_pct"] else "outside_reference_tolerance"
    return {**result,"available":True,"density_g_cm3":density,"deviation_pct":deviation,
            "verdict":verdict,"message":"Within pure-gold reference tolerance" if verdict.startswith("within") else "Outside pure-gold reference tolerance; verify dimensions/material"}
