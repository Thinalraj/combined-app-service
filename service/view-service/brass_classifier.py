from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BrassModelParams:
    rmin: float = 0.0
    rspan: float = 111.195123
    k: float = 28.201596
    alpha: float = 1.502013
    d: float = 0.530768
    sa0: float = 16.7641
    t0: float = 0.2700
    min_coverage_pct: float = 10.39
    max_coverage_pct: float = 127.32
    min_thickness_mm: float = 0.127
    max_thickness_mm: float = 1.63
    model_name: str = "zero_floor_brass_bar_ch1_f1_v1"


@dataclass(frozen=True)
class BrassSurfaceParams:
    rmin: float
    rspan: float
    k: float
    alpha: float
    d: float
    rmse: float
    r2: float
    name: str


SA0 = 16.7641
T0 = 0.2700
CH2_F1_PARAMS = BrassSurfaceParams(
    rmin=10.333544,
    rspan=43.971248,
    k=18.788119,
    alpha=1.966935,
    d=0.520747,
    rmse=2.052735,
    r2=0.970476,
    name="ch2_f1",
)
CH2_F3_PARAMS = BrassSurfaceParams(
    rmin=9.145910,
    rspan=33.712040,
    k=11464.800139,
    alpha=4.980760,
    d=10.000000,
    rmse=3.822410,
    r2=0.864565,
    name="ch2_f3",
)
CH2_F1_F3_MODEL_NAME = "brass_ch2_f1_ch2_f3_two_feature_v1"
CH2_F1_F3_COVERAGE_RANGE = (10.3938, 337.4890)
CH2_F1_F3_THICKNESS_RANGE = (0.127, 1.63)
CH1_F1_RULE_PARAMS = BrassSurfaceParams(
    rmin=11.106073,
    rspan=54.383265,
    k=17.029083,
    alpha=1.814923,
    d=1.237633,
    rmse=1.391995,
    r2=0.989317,
    name="ch1_f1",
)
CH1_F3_RULE_PARAMS = BrassSurfaceParams(
    rmin=2.631621,
    rspan=50.457250,
    k=124.767450,
    alpha=2.997713,
    d=1.165455,
    rmse=2.660972,
    r2=0.969638,
    name="ch1_f3",
)
CH1_F1_CH1_F3_MODEL_NAME = "brass_ch1_f1_ch1_f3_fuzzy_v1"
CH1_F1_CH2_F3_MODEL_NAME = "brass_ch1_f1_ch2_f3_fuzzy_v1"


def _validate_positive(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _validate_finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def validate_inputs(
    coverage_pct: float,
    thickness_mm: float,
    measured_ch2_f1_abs_delta_pct: float,
    measured_ch2_f3_abs_delta_pct: float,
) -> tuple[float, float, float, float]:
    """Validate inputs for the CH2 F1/F3 two-feature brass classifier."""
    return (
        _validate_positive("coverage_pct", float(coverage_pct)),
        _validate_positive("thickness_mm", float(thickness_mm)),
        _validate_finite("measured_ch2_f1_abs_delta_pct", float(measured_ch2_f1_abs_delta_pct)),
        _validate_finite("measured_ch2_f3_abs_delta_pct", float(measured_ch2_f3_abs_delta_pct)),
    )


def brass_surface(
    coverage_pct: float,
    thickness_mm: float,
    rmin: float,
    rspan: float,
    k: float,
    alpha: float,
    d: float,
    sa0: float = SA0,
    t0: float = T0,
) -> float:
    """Evaluate the continuous saturating brass response surface."""
    coverage_pct = _validate_positive("coverage_pct", float(coverage_pct))
    thickness_mm = _validate_positive("thickness_mm", float(thickness_mm))
    denominator = 1.0 - math.exp(-t0 / d)
    if denominator <= 0:
        raise ValueError("invalid model parameter: t0/d produces zero thickness denominator")
    thickness_term = (1.0 - math.exp(-thickness_mm / d)) / denominator
    x_value = ((coverage_pct / sa0) ** alpha) * thickness_term
    return rmin + rspan * x_value / (k + x_value)


def _predict_surface(params: BrassSurfaceParams, coverage_pct: float, thickness_mm: float) -> float:
    return brass_surface(
        coverage_pct,
        thickness_mm,
        rmin=params.rmin,
        rspan=params.rspan,
        k=params.k,
        alpha=params.alpha,
        d=params.d,
    )


def _primary_membership(z_value: float) -> float:
    if z_value <= 1.5:
        return 1.0
    if z_value <= 2.5:
        return max(0.0, 2.5 - z_value)
    return 0.0


def _secondary_membership(z_value: float) -> float:
    if z_value <= 2.5:
        return 1.0
    if z_value <= 3.5:
        return max(0.0, 3.5 - z_value)
    return 0.0


def _fuzzy_label(mu_brass: float) -> tuple[str, str]:
    if mu_brass >= 0.75:
        return ("brass", "high")
    if mu_brass >= 0.40:
        return ("brass_like_uncertain", "medium")
    return ("not_brass", "low")


def _residual_direction(residual: float) -> str:
    if residual > 0:
        return "response is stronger than brass model"
    if residual < 0:
        return "response is weaker than brass model"
    return "response matches brass model"


def _within_geometry_range(coverage_pct: float, thickness_mm: float) -> bool:
    return (
        CH2_F1_F3_COVERAGE_RANGE[0] <= coverage_pct <= CH2_F1_F3_COVERAGE_RANGE[1]
        and CH2_F1_F3_THICKNESS_RANGE[0] <= thickness_mm <= CH2_F1_F3_THICKNESS_RANGE[1]
    )


def _fuzzy_rule_result(
    coverage_pct: float,
    thickness_mm: float,
    measured_primary: float,
    measured_secondary: float,
    primary_params: BrassSurfaceParams,
    secondary_params: BrassSurfaceParams,
    model_name: str,
    primary_key: str,
    secondary_key: str,
) -> dict[str, Any]:
    coverage_pct = _validate_positive("coverage_pct", float(coverage_pct))
    thickness_mm = _validate_positive("thickness_mm", float(thickness_mm))
    measured_primary = _validate_finite(primary_key, float(measured_primary))
    measured_secondary = _validate_finite(secondary_key, float(measured_secondary))

    predicted_primary = _predict_surface(primary_params, coverage_pct, thickness_mm)
    predicted_secondary = _predict_surface(secondary_params, coverage_pct, thickness_mm)
    residual_primary = measured_primary - predicted_primary
    residual_secondary = measured_secondary - predicted_secondary
    z_primary = abs(residual_primary) / primary_params.rmse
    z_secondary = abs(residual_secondary) / secondary_params.rmse
    mu_primary = _primary_membership(z_primary)
    mu_secondary = _secondary_membership(z_secondary)
    mu_brass = mu_primary * mu_secondary
    label, confidence = _fuzzy_label(mu_brass)
    within_range = _within_geometry_range(coverage_pct, thickness_mm)
    warning = None if within_range else "Input is outside calibrated geometry range. Prediction is extrapolated."

    return {
        "model_name": model_name,
        "label": label,
        "confidence": confidence,
        "mu_brass": mu_brass,
        "within_calibrated_range": within_range,
        "warning": warning,
        "coverage_pct": coverage_pct,
        "thickness_mm": thickness_mm,
        f"measured_{primary_key}": measured_primary,
        f"predicted_{primary_key}": predicted_primary,
        f"residual_{primary_key}": residual_primary,
        f"z_{primary_key}": z_primary,
        f"mu_{primary_key}": mu_primary,
        f"residual_direction_{primary_key}": _residual_direction(residual_primary),
        f"measured_{secondary_key}": measured_secondary,
        f"predicted_{secondary_key}": predicted_secondary,
        f"residual_{secondary_key}": residual_secondary,
        f"z_{secondary_key}": z_secondary,
        f"mu_{secondary_key}": mu_secondary,
        f"residual_direction_{secondary_key}": _residual_direction(residual_secondary),
        "surface_params": {
            "primary": asdict(primary_params),
            "secondary": asdict(secondary_params),
            "sa0": SA0,
            "t0": T0,
        },
        "calibrated_range": {
            "coverage_pct": list(CH2_F1_F3_COVERAGE_RANGE),
            "thickness_mm": list(CH2_F1_F3_THICKNESS_RANGE),
        },
    }


def classify_brass_ch1_f1_ch1_f3(
    coverage_pct: float,
    thickness_mm: float,
    measured_ch1_f1_abs_delta_pct: float,
    measured_ch1_f3_abs_delta_pct: float,
) -> dict[str, Any]:
    return _fuzzy_rule_result(
        coverage_pct,
        thickness_mm,
        measured_ch1_f1_abs_delta_pct,
        measured_ch1_f3_abs_delta_pct,
        CH1_F1_RULE_PARAMS,
        CH1_F3_RULE_PARAMS,
        CH1_F1_CH1_F3_MODEL_NAME,
        "ch1f1",
        "ch1f3",
    )


def classify_brass_ch1_f1_ch2_f3(
    coverage_pct: float,
    thickness_mm: float,
    measured_ch1_f1_abs_delta_pct: float,
    measured_ch2_f3_abs_delta_pct: float,
) -> dict[str, Any]:
    return _fuzzy_rule_result(
        coverage_pct,
        thickness_mm,
        measured_ch1_f1_abs_delta_pct,
        measured_ch2_f3_abs_delta_pct,
        CH1_F1_RULE_PARAMS,
        CH2_F3_PARAMS,
        CH1_F1_CH2_F3_MODEL_NAME,
        "ch1f1",
        "ch2f3",
    )


def classify_brass_ch2_f1_f3(
    coverage_pct: float,
    thickness_mm: float,
    measured_ch2_f1_abs_delta_pct: float,
    measured_ch2_f3_abs_delta_pct: float,
) -> dict[str, Any]:
    """Classify flat brass compatibility using CH2 F1 and CH2 F3 residuals.

    The two residuals are normalized by each fitted model RMSE and combined as
    a Euclidean distance. Diagnostic normalized residuals are returned
    separately so weak CH2 F3 behavior is visible.
    """
    coverage_pct, thickness_mm, measured_ch2_f1, measured_ch2_f3 = validate_inputs(
        coverage_pct,
        thickness_mm,
        measured_ch2_f1_abs_delta_pct,
        measured_ch2_f3_abs_delta_pct,
    )
    pred_ch2_f1 = _predict_surface(CH2_F1_PARAMS, coverage_pct, thickness_mm)
    pred_ch2_f3 = _predict_surface(CH2_F3_PARAMS, coverage_pct, thickness_mm)
    residual_ch2_f1 = measured_ch2_f1 - pred_ch2_f1
    residual_ch2_f3 = measured_ch2_f3 - pred_ch2_f3
    norm_residual_ch2_f1 = residual_ch2_f1 / CH2_F1_PARAMS.rmse
    norm_residual_ch2_f3 = residual_ch2_f3 / CH2_F3_PARAMS.rmse
    distance = math.sqrt((norm_residual_ch2_f1 ** 2) + (norm_residual_ch2_f3 ** 2))

    if distance <= 2.0:
        label = "brass"
        confidence = "high"
    elif distance <= 3.0:
        label = "brass_like"
        confidence = "medium"
    else:
        label = "not_brass_or_outlier"
        confidence = "low"

    within_calibrated_range = (
        CH2_F1_F3_COVERAGE_RANGE[0] <= coverage_pct <= CH2_F1_F3_COVERAGE_RANGE[1]
        and CH2_F1_F3_THICKNESS_RANGE[0] <= thickness_mm <= CH2_F1_F3_THICKNESS_RANGE[1]
    )
    warning = None
    if not within_calibrated_range:
        warning = "Input is outside calibrated geometry range. Prediction is extrapolated."

    return {
        "model_name": CH2_F1_F3_MODEL_NAME,
        "label": label,
        "confidence": confidence,
        "two_feature_distance": distance,
        "within_calibrated_range": within_calibrated_range,
        "warning": warning,
        "coverage_pct": coverage_pct,
        "thickness_mm": thickness_mm,
        "measured_ch2_f1": measured_ch2_f1,
        "predicted_ch2_f1": pred_ch2_f1,
        "residual_ch2_f1": residual_ch2_f1,
        "norm_residual_ch2_f1": norm_residual_ch2_f1,
        "measured_ch2_f3": measured_ch2_f3,
        "predicted_ch2_f3": pred_ch2_f3,
        "residual_ch2_f3": residual_ch2_f3,
        "norm_residual_ch2_f3": norm_residual_ch2_f3,
        "surface_params": {
            "ch2_f1": asdict(CH2_F1_PARAMS),
            "ch2_f3": asdict(CH2_F3_PARAMS),
            "sa0": SA0,
            "t0": T0,
        },
        "calibrated_range": {
            "coverage_pct": list(CH2_F1_F3_COVERAGE_RANGE),
            "thickness_mm": list(CH2_F1_F3_THICKNESS_RANGE),
        },
    }


def predict_brass_ch1_f1(
    coverage_pct: float,
    thickness_mm: float,
    params: BrassModelParams | None = None,
) -> float:
    """Return the continuous CH1 F1 brass response predicted by the fitted surface.

    This function evaluates the mathematical response surface directly for the
    provided coverage and thickness. It does not use calibration-point lookup,
    contour-image lookup, or graph interpolation.
    """
    params = params or BrassModelParams()
    coverage_pct = _validate_positive("coverage_pct", float(coverage_pct))
    thickness_mm = _validate_positive("thickness_mm", float(thickness_mm))

    denominator = 1.0 - math.exp(-params.t0 / params.d)
    if denominator <= 0:
        raise ValueError("invalid model parameter: t0/d produces zero thickness denominator")

    thickness_term = (1.0 - math.exp(-thickness_mm / params.d)) / denominator
    x_value = ((coverage_pct / params.sa0) ** params.alpha) * thickness_term
    return params.rmin + params.rspan * x_value / (params.k + x_value)


def residual_to_brass(
    coverage_pct: float,
    thickness_mm: float,
    measured_response: float,
    params: BrassModelParams | None = None,
) -> float:
    """Return measured_response minus the continuous predicted brass response."""
    measured_response = _validate_finite("measured_response", float(measured_response))
    predicted = predict_brass_ch1_f1(coverage_pct, thickness_mm, params)
    return measured_response - predicted


def calculate_session_scale(
    reference_coverage_pct: float,
    reference_thickness_mm: float,
    measured_reference_response: float,
    params: BrassModelParams | None = None,
) -> float:
    """Return a multiplicative session scale from a known brass reference sample.

    The scale is applied only to the model span above Rmin:

    ``predicted_session = Rmin + session_scale * (predicted_brass - Rmin)``
    """
    params = params or BrassModelParams()
    measured_reference_response = _validate_finite(
        "measured_reference_response",
        float(measured_reference_response),
    )
    predicted_reference = predict_brass_ch1_f1(reference_coverage_pct, reference_thickness_mm, params)
    denominator = predicted_reference - params.rmin
    if abs(denominator) <= 1e-12:
        raise ValueError("reference prediction is too close to Rmin to calculate session_scale")
    return (measured_reference_response - params.rmin) / denominator


def _apply_session_scale(
    predicted_brass: float,
    session_scale: float | None,
    params: BrassModelParams,
) -> float:
    if session_scale is None:
        return predicted_brass
    session_scale = _validate_finite("session_scale", float(session_scale))
    return params.rmin + session_scale * (predicted_brass - params.rmin)


def classify_brass(
    coverage_pct: float,
    thickness_mm: float,
    ch1_f1_abs_delta_pct: float,
    strict_tolerance: float = 1.5,
    practical_tolerance: float = 2.5,
    params: BrassModelParams | None = None,
    session_scale: float | None = None,
) -> dict[str, Any]:
    """Classify a flat brass-bar-compatible sample against the response surface.

    The classifier evaluates the fitted equation for every input sample, then
    classifies by residual tolerance:

    * |residual| <= strict_tolerance: brass, high confidence
    * |residual| <= practical_tolerance: brass, medium confidence
    * otherwise: not_brass, low confidence

    This binary classifier is intended for flat bar samples only.
    """
    params = params or BrassModelParams()
    coverage_pct = _validate_positive("coverage_pct", float(coverage_pct))
    thickness_mm = _validate_positive("thickness_mm", float(thickness_mm))
    measured = _validate_finite("ch1_f1_abs_delta_pct", float(ch1_f1_abs_delta_pct))
    strict_tolerance = _validate_positive("strict_tolerance", float(strict_tolerance))
    practical_tolerance = _validate_positive("practical_tolerance", float(practical_tolerance))
    if strict_tolerance > practical_tolerance:
        raise ValueError("strict_tolerance must be less than or equal to practical_tolerance")

    unscaled_predicted = predict_brass_ch1_f1(coverage_pct, thickness_mm, params)
    predicted = _apply_session_scale(unscaled_predicted, session_scale, params)
    residual = measured - predicted
    abs_residual = abs(residual)
    if abs_residual <= strict_tolerance:
        label = "brass"
        confidence = "high"
        tolerance_used = strict_tolerance
    elif abs_residual <= practical_tolerance:
        label = "brass"
        confidence = "medium"
        tolerance_used = practical_tolerance
    else:
        label = "not_brass"
        confidence = "low"
        tolerance_used = practical_tolerance

    within_calibrated_range = (
        params.min_coverage_pct <= coverage_pct <= params.max_coverage_pct
        and params.min_thickness_mm <= thickness_mm <= params.max_thickness_mm
    )
    warning = None
    if not within_calibrated_range:
        warning = "Input is outside calibrated range; result is extrapolated."

    result = {
        "label": label,
        "confidence": confidence,
        "predicted_brass": predicted,
        "unscaled_predicted_brass": unscaled_predicted,
        "measured_response": measured,
        "predicted_ch1_f1": predicted,
        "measured_ch1_f1": measured,
        "residual": residual,
        "abs_residual": abs_residual,
        "strict_tolerance": strict_tolerance,
        "practical_tolerance": practical_tolerance,
        "tolerance_used": tolerance_used,
        "within_calibrated_range": within_calibrated_range,
        "warning": warning,
        "model_name": params.model_name,
        "session_scale": session_scale,
        "model_params": asdict(params),
        "coverage_pct": coverage_pct,
        "thickness_mm": thickness_mm,
        "calibrated_range": {
            "coverage_pct": [params.min_coverage_pct, params.max_coverage_pct],
            "thickness_mm": [params.min_thickness_mm, params.max_thickness_mm],
        },
        "warnings": [warning] if warning else [],
    }
    return result


def classify_brass_with_session_scale(
    coverage_pct: float,
    thickness_mm: float,
    ch1_f1_abs_delta_pct: float,
    strict_tolerance: float = 1.5,
    practical_tolerance: float = 2.5,
    params: BrassModelParams | None = None,
    session_scale: float | None = None,
) -> dict[str, Any]:
    """Classify brass compatibility with an optional session scale correction."""
    return classify_brass(
        coverage_pct,
        thickness_mm,
        ch1_f1_abs_delta_pct,
        strict_tolerance=strict_tolerance,
        practical_tolerance=practical_tolerance,
        params=params,
        session_scale=session_scale,
    )


def generate_response_map(
    coverage_min: float = 0.1,
    coverage_max: float = 100.0,
    thickness_min: float = 0.127,
    thickness_max: float = 1.63,
    n: int = 200,
    params: BrassModelParams | None = None,
) -> list[dict[str, float]]:
    """Generate calculated surface points for plotting or visualization only.

    Classification should call :func:`classify_brass`, which evaluates the same
    continuous equation for the single measured sample.
    """
    params = params or BrassModelParams()
    coverage_min = _validate_positive("coverage_min", float(coverage_min))
    coverage_max = _validate_positive("coverage_max", float(coverage_max))
    thickness_min = _validate_positive("thickness_min", float(thickness_min))
    thickness_max = _validate_positive("thickness_max", float(thickness_max))
    if coverage_min > coverage_max:
        raise ValueError("coverage_min must be less than or equal to coverage_max")
    if thickness_min > thickness_max:
        raise ValueError("thickness_min must be less than or equal to thickness_max")
    if not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer greater than or equal to 2")

    coverage_step = (coverage_max - coverage_min) / (n - 1)
    thickness_step = (thickness_max - thickness_min) / (n - 1)
    points: list[dict[str, float]] = []
    for coverage_index in range(n):
        coverage_pct = coverage_min + coverage_step * coverage_index
        for thickness_index in range(n):
            thickness_mm = thickness_min + thickness_step * thickness_index
            points.append(
                {
                    "coverage_pct": coverage_pct,
                    "thickness_mm": thickness_mm,
                    "predicted_brass": predict_brass_ch1_f1(coverage_pct, thickness_mm, params),
                }
            )
    return points


def main() -> None:
    parser = argparse.ArgumentParser(description="Binary brass compatibility classifier using CH1 F1 response.")
    parser.add_argument("--coverage", type=float, required=True, help="Sample coverage percentage")
    parser.add_argument("--thickness", type=float, required=True, help="Sample thickness in mm")
    parser.add_argument("--response", type=float, required=True, help="Measured CH1 F1 absolute delta percentage")
    parser.add_argument("--session-scale", type=float, default=None, help="Optional session scale correction")
    args = parser.parse_args()
    result = classify_brass(args.coverage, args.thickness, args.response, session_scale=args.session_scale)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
