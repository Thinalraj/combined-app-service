"""NUC-02: requested minimums; scores are uncalibrated, not purity or accuracy."""
import math
MIN_CONFIDENCE = .90


def valid_score(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and MIN_CONFIDENCE<=value<=1


def combined_eligibility(prediction, detection, shape=None):
    """Do not let a disabled/missing shape detector pass the reference decision."""
    if not prediction or not prediction.get("reference_only"):
        return prediction
    detection=detection or {}
    vision_ok=(detection.get("eligible") is True and detection.get("count")==1 and
               valid_score(detection.get("confidence")) and
               isinstance(detection.get("capture_age_ms"),(int,float)) and 0<=detection["capture_age_ms"]<=5000)
    score=prediction.get("score",0)
    if shape is not None:
        vision_ok = vision_ok and detection.get("label")==str(shape).lower()
    reference_ok=(prediction.get("accepted") is True and valid_score(score))
    result={**prediction,"eligibility":{"eligible":vision_ok and reference_ok,
        "vision_pass":vision_ok,"reference_pass":reference_ok,"minimum_pct":90,
        "vision_confidence_pct":100*detection["confidence"] if isinstance(detection.get("confidence"),(int,float)) else None,
        "reference_score_pct":100*score if isinstance(score,(int,float)) else None}}
    if not result["eligibility"]["eligible"]:
        result.update(accepted=False,uncertain=True,reference_grade=None,prediction="Unable to determine",result_type="unknown",
            decision_message="Not eligible: both shape detection and reference score must reach 90%. Gold identity and purity remain unverified.")
    return result
