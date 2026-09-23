from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy.optimize import curve_fit
except Exception:  # pragma: no cover - exercised only when scipy is absent
    curve_fit = None


SA0 = 16.7641
T0 = 0.2700
COIL_AREA_MM2 = math.pi * (35.0 ** 2)
COVERAGE_RANGE = (10.3938, 337.4890)
THICKNESS_RANGE = (0.127, 1.63)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "latest_rule_based_ch1f1_ch1f3_20260628"


@dataclass(frozen=True)
class SurfaceParams:
    rmin: float
    rspan: float
    k: float
    alpha: float
    d: float
    rmse: float
    r2: float
    source: str


FALLBACK_CH1_F1 = SurfaceParams(
    rmin=11.106073,
    rspan=54.383265,
    k=17.029083,
    alpha=1.814923,
    d=1.237633,
    rmse=1.391995,
    r2=0.989317,
    source="fallback",
)
FALLBACK_CH1_F3 = SurfaceParams(
    rmin=2.631621,
    rspan=50.457250,
    k=124.767450,
    alpha=2.997713,
    d=1.165455,
    rmse=2.660972,
    r2=0.969638,
    source="fallback",
)


REPORT_COLUMNS = [
    "id",
    "date",
    "time",
    "material",
    "width_mm",
    "length_mm",
    "thickness_mm",
    "coverage_pct",
    "measured_ch1_f1",
    "predicted_ch1_f1",
    "residual_ch1_f1",
    "z_ch1_f1",
    "ch1_f1_status",
    "measured_ch1_f3",
    "predicted_ch1_f3",
    "residual_ch1_f3",
    "z_ch1_f3",
    "ch1_f3_status",
    "label",
    "confidence",
    "within_calibrated_range",
    "warning",
    "reason",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        token = value.strip().split(" ")[0]
        try:
            parsed = float(token)
        except ValueError:
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def frequency_channel_rms(record: dict[str, Any], frequency: str, channel: str) -> float | None:
    for step in record.get("frequency_sequence") or []:
        if step.get("frequency_command") != frequency:
            continue
        channels = step.get("channels") if isinstance(step.get("channels"), dict) else {}
        return parse_float((channels.get(channel) or {}).get("rms"))
    return None


def calibration_air(calibration: dict[str, Any], frequency: str, channel: str) -> float | None:
    air = calibration.get("frequency_air") if isinstance(calibration.get("frequency_air"), dict) else {}
    return parse_float(((air.get(frequency) or {}).get(channel) or {}).get("rms"))


def compute_coverage_pct(row: dict[str, Any] | pd.Series) -> float | None:
    contact_area_ratio = parse_float(row.get("contact_area_ratio"))
    if contact_area_ratio is not None and contact_area_ratio > 0:
        return contact_area_ratio * 100.0 if contact_area_ratio <= 10.0 else contact_area_ratio
    coverage_pct = parse_float(row.get("coverage_pct"))
    if coverage_pct is not None and coverage_pct > 0:
        return coverage_pct
    width_mm = parse_float(row.get("width_mm"))
    length_mm = parse_float(row.get("length_mm"))
    if width_mm is None or length_mm is None:
        return None
    return (width_mm * length_mm / COIL_AREA_MM2) * 100.0


def brass_surface(
    coverage_pct: float | np.ndarray,
    thickness_mm: float | np.ndarray,
    rmin: float,
    rspan: float,
    k: float,
    alpha: float,
    d: float,
) -> float | np.ndarray:
    coverage = np.asarray(coverage_pct, dtype=float)
    thickness = np.asarray(thickness_mm, dtype=float)
    thickness_term = (1.0 - np.exp(-thickness / d)) / (1.0 - np.exp(-T0 / d))
    x_value = ((coverage / SA0) ** alpha) * thickness_term
    return rmin + rspan * x_value / (k + x_value)


def load_latest_training_data(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    calibration = load_json(data_dir / "calibration_latest.json")
    records = load_json(data_dir / "teaching_library_latest.json")
    rows: list[dict[str, Any]] = []
    for record in records:
        material = str(record.get("material") or record.get("material_base") or "")
        coverage_pct = compute_coverage_pct(record)
        f1_air = calibration_air(calibration, "f1", "ch1")
        f3_air = calibration_air(calibration, "f3", "ch1")
        f1_rms = frequency_channel_rms(record, "f1", "ch1")
        f3_rms = frequency_channel_rms(record, "f3", "ch1")
        ch1_f1_abs = abs((f1_rms - f1_air) / f1_air * 100.0) if f1_rms is not None and f1_air else None
        ch1_f3_abs = abs((f3_rms - f3_air) / f3_air * 100.0) if f3_rms is not None and f3_air else None
        rows.append(
            {
                "id": record.get("id"),
                "date": record.get("date"),
                "time": record.get("time"),
                "material": material or None,
                "width_mm": parse_float(record.get("width_mm")),
                "length_mm": parse_float(record.get("length_mm")),
                "thickness_mm": parse_float(record.get("thickness_mm")),
                "coverage_pct": coverage_pct,
                "ch1_f1_abs_delta_pct": ch1_f1_abs,
                "ch1_f3_abs_delta_pct": ch1_f3_abs,
            }
        )
    return pd.DataFrame(rows)


def load_latest_measurement_data(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    calibration = load_json(data_dir / "calibration_latest.json")
    records = load_json(data_dir / "measurements_latest.json")
    rows: list[dict[str, Any]] = []
    for record in records:
        features = record.get("classifier_features") if isinstance(record.get("classifier_features"), dict) else {}
        brass_model = (
            record.get("classifier_result", {}).get("brass_model", {})
            if isinstance(record.get("classifier_result"), dict)
            else {}
        )
        coverage_pct = compute_coverage_pct(record)
        f1_air = calibration_air(calibration, "f1", "ch1")
        f3_air = calibration_air(calibration, "f3", "ch1")
        f1_rms = frequency_channel_rms(record, "f1", "ch1")
        f3_rms = frequency_channel_rms(record, "f3", "ch1")
        f1_delta = parse_float(features.get("f1_ch1_delta_pct"))
        f3_delta = parse_float(features.get("f3_ch1_delta_pct"))
        ch1_f1_abs = abs(f1_delta) if f1_delta is not None else None
        ch1_f3_abs = abs(f3_delta) if f3_delta is not None else None
        if ch1_f1_abs is None and f1_rms is not None and f1_air:
            ch1_f1_abs = abs((f1_rms - f1_air) / f1_air * 100.0)
        if ch1_f3_abs is None and f3_rms is not None and f3_air:
            ch1_f3_abs = abs((f3_rms - f3_air) / f3_air * 100.0)
        if ch1_f1_abs is None:
            ch1_f1_abs = parse_float(brass_model.get("measured_ch1_f1"))
        rows.append(
            {
                "id": record.get("id"),
                "date": record.get("date"),
                "time": record.get("time"),
                "material": record.get("material") or record.get("material_base") or record.get("expected_material"),
                "result": record.get("result"),
                "width_mm": parse_float(record.get("width_mm")),
                "length_mm": parse_float(record.get("length_mm")),
                "thickness_mm": parse_float(record.get("thickness_mm")),
                "coverage_pct": coverage_pct,
                "ch1_f1_abs_delta_pct": ch1_f1_abs,
                "ch1_f3_abs_delta_pct": ch1_f3_abs,
            }
        )
    return pd.DataFrame(rows)


def _surface_model(xdata: tuple[np.ndarray, np.ndarray], rmin: float, rspan: float, k: float, alpha: float, d: float) -> np.ndarray:
    coverage_pct, thickness_mm = xdata
    return brass_surface(coverage_pct, thickness_mm, rmin, rspan, k, alpha, d)


def fit_surface_if_needed(training_df: pd.DataFrame, feature: str, fallback: SurfaceParams) -> SurfaceParams:
    brass = training_df[
        training_df["material"].fillna("").str.lower().str.contains("brass")
        & training_df[["coverage_pct", "thickness_mm", feature]].notna().all(axis=1)
    ].copy()
    if curve_fit is None or len(brass) < 6:
        return fallback
    coverage = brass["coverage_pct"].to_numpy(dtype=float)
    thickness = brass["thickness_mm"].to_numpy(dtype=float)
    observed = brass[feature].to_numpy(dtype=float)
    try:
        popt, _ = curve_fit(
            _surface_model,
            (coverage, thickness),
            observed,
            p0=[fallback.rmin, fallback.rspan, fallback.k, fallback.alpha, fallback.d],
            bounds=([0.0, 0.001, 0.001, 0.1, 0.05], [100.0, 500.0, 100000.0, 8.0, 20.0]),
            maxfev=20000,
        )
    except Exception:
        return fallback
    predicted = _surface_model((coverage, thickness), *popt)
    residuals = observed - predicted
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    return SurfaceParams(
        rmin=float(popt[0]),
        rspan=float(popt[1]),
        k=float(popt[2]),
        alpha=float(popt[3]),
        d=float(popt[4]),
        rmse=rmse if rmse > 1e-9 else fallback.rmse,
        r2=r2,
        source=f"fitted_latest_training_n{len(brass)}",
    )


def validate_row(row: pd.Series) -> list[str]:
    missing: list[str] = []
    for key in ["coverage_pct", "thickness_mm", "ch1_f1_abs_delta_pct", "ch1_f3_abs_delta_pct"]:
        value = parse_float(row.get(key))
        if value is None:
            missing.append(key)
    coverage_pct = parse_float(row.get("coverage_pct"))
    thickness_mm = parse_float(row.get("thickness_mm"))
    if coverage_pct is None or coverage_pct <= 0:
        missing.append("coverage_pct_positive")
    if thickness_mm is None or thickness_mm <= 0:
        missing.append("thickness_mm_positive")
    return missing


def classify_rule_based_ch1f1_ch1f3(
    row: pd.Series,
    ch1_f1_params: SurfaceParams,
    ch1_f3_params: SurfaceParams,
) -> dict[str, Any]:
    missing = validate_row(row)
    base = {key: row.get(key) for key in ["id", "date", "time", "material", "width_mm", "length_mm", "thickness_mm", "coverage_pct"]}
    if missing:
        return {
            **base,
            "measured_ch1_f1": row.get("ch1_f1_abs_delta_pct"),
            "measured_ch1_f3": row.get("ch1_f3_abs_delta_pct"),
            "label": "skipped",
            "confidence": "none",
            "within_calibrated_range": False,
            "warning": f"Skipped row because required fields are missing or invalid: {', '.join(sorted(set(missing)))}",
            "reason": "Missing required CH1 F1/F3 measurement or valid geometry.",
        }

    coverage_pct = float(row["coverage_pct"])
    thickness_mm = float(row["thickness_mm"])
    measured_f1 = float(row["ch1_f1_abs_delta_pct"])
    measured_f3 = float(row["ch1_f3_abs_delta_pct"])
    pred_f1 = float(brass_surface(coverage_pct, thickness_mm, ch1_f1_params.rmin, ch1_f1_params.rspan, ch1_f1_params.k, ch1_f1_params.alpha, ch1_f1_params.d))
    pred_f3 = float(brass_surface(coverage_pct, thickness_mm, ch1_f3_params.rmin, ch1_f3_params.rspan, ch1_f3_params.k, ch1_f3_params.alpha, ch1_f3_params.d))
    residual_f1 = measured_f1 - pred_f1
    residual_f3 = measured_f3 - pred_f3
    z_f1 = abs(residual_f1) / ch1_f1_params.rmse
    z_f3 = abs(residual_f3) / ch1_f3_params.rmse

    if z_f1 <= 1.5 and z_f3 <= 3.5:
        label = "brass"
        confidence = "high"
        f1_status = "strong_primary_match"
        f3_status = "does_not_contradict"
        reason = "CH1 F1 is a strong primary match and CH1 F3 does not strongly contradict brass."
    elif z_f1 <= 2.5 and z_f3 <= 2.5:
        label = "brass_like"
        confidence = "medium"
        f1_status = "possible_primary_match"
        f3_status = "supports_brass"
        reason = "CH1 F1 is within possible brass range and CH1 F3 supports the brass response."
    elif z_f1 <= 2.5 and z_f3 <= 3.5:
        label = "uncertain"
        confidence = "low"
        f1_status = "possible_primary_match"
        f3_status = "weak_or_suspicious_confirmation"
        reason = "CH1 F1 is possible brass, but CH1 F3 is not clean enough for confident classification."
    else:
        label = "not_brass"
        confidence = "low"
        f1_status = "primary_mismatch" if z_f1 > 2.5 else "primary_possible"
        f3_status = "strong_high_frequency_contradiction" if z_f3 > 3.5 else "secondary_not_decisive"
        reason = "CH1 F1 primary response does not match brass surface, or CH1 F3 strongly contradicts the brass high-frequency response."

    within_range = (
        COVERAGE_RANGE[0] <= coverage_pct <= COVERAGE_RANGE[1]
        and THICKNESS_RANGE[0] <= thickness_mm <= THICKNESS_RANGE[1]
    )
    warning = None if within_range else "Input is outside calibrated geometry range. Prediction is extrapolated."
    return {
        **base,
        "measured_ch1_f1": measured_f1,
        "predicted_ch1_f1": pred_f1,
        "residual_ch1_f1": residual_f1,
        "z_ch1_f1": z_f1,
        "ch1_f1_status": f1_status,
        "measured_ch1_f3": measured_f3,
        "predicted_ch1_f3": pred_f3,
        "residual_ch1_f3": residual_f3,
        "z_ch1_f3": z_f3,
        "ch1_f3_status": f3_status,
        "label": label,
        "confidence": confidence,
        "within_calibrated_range": within_range,
        "warning": warning,
        "reason": reason,
    }


def save_reports(
    results_df: pd.DataFrame,
    skipped_df: pd.DataFrame,
    training_df: pd.DataFrame,
    measurement_df: pd.DataFrame,
    ch1_f1_params: SurfaceParams,
    ch1_f3_params: SurfaceParams,
    output_dir: Path,
) -> dict[str, Path | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "latest_rule_based_ch1f1_ch1f3_classifier_results.csv"
    summary_path = output_dir / "latest_rule_based_ch1f1_ch1f3_classifier_summary.md"
    confusion_path = output_dir / "latest_rule_based_ch1f1_ch1f3_classifier_confusion_matrix.csv"
    plot_path = output_dir / "latest_rule_based_ch1f1_ch1f3_classifier_plot.png"
    skipped_path = output_dir / "latest_rule_based_ch1f1_ch1f3_classifier_skipped_rows.csv"

    for column in REPORT_COLUMNS:
        if column not in results_df.columns:
            results_df[column] = np.nan
    results_df[REPORT_COLUMNS].to_csv(results_path, index=False)
    skipped_df.to_csv(skipped_path, index=False)

    labelled = results_df[results_df["material"].notna() & (results_df["material"].astype(str).str.strip() != "")]
    if not labelled.empty:
        confusion = pd.crosstab(labelled["material"], labelled["label"])
        confusion.to_csv(confusion_path)
    else:
        confusion_path = None

    plot_df = results_df[results_df["label"] != "skipped"].copy()
    if not plot_df.empty:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
        colors = {"brass": "#1f9d55", "brass_like": "#3b82f6", "uncertain": "#f59e0b", "not_brass": "#ef4444"}
        markers = ["o", "s", "^", "D", "P", "X", "v", "*"]
        material_values = sorted([str(v) for v in plot_df["material"].dropna().unique()])
        marker_map = {material: markers[index % len(markers)] for index, material in enumerate(material_values)}
        for label, group in plot_df.groupby("label"):
            if material_values:
                for material, material_group in group.groupby(group["material"].fillna("Unknown")):
                    ax.scatter(
                        material_group["z_ch1_f1"],
                        material_group["z_ch1_f3"],
                        label=f"{label} / {material}",
                        c=colors.get(label, "#6b7280"),
                        marker=marker_map.get(str(material), "o"),
                        edgecolors="black",
                        linewidths=0.4,
                        alpha=0.82,
                    )
            else:
                ax.scatter(group["z_ch1_f1"], group["z_ch1_f3"], label=label, c=colors.get(label, "#6b7280"), alpha=0.82)
        ax.axvline(1.5, color="#111827", linestyle="--", linewidth=1)
        ax.axvline(2.5, color="#111827", linestyle="-.", linewidth=1)
        ax.axhline(2.5, color="#111827", linestyle="-.", linewidth=1)
        ax.axhline(3.5, color="#111827", linestyle="--", linewidth=1)
        ax.set_xlabel("z_ch1_f1 primary residual")
        ax.set_ylabel("z_ch1_f3 confirmation residual")
        ax.set_title("Rule-Based CH1 F1 / CH1 F3 Brass Classifier")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7, loc="best")
        fig.tight_layout()
        fig.savefig(plot_path)
        plt.close(fig)

    label_counts = results_df["label"].value_counts(dropna=False)
    material_prediction = (
        pd.crosstab(labelled["material"], labelled["label"]).to_markdown()
        if not labelled.empty
        else "No true material labels were available in the measurement rows."
    )
    aluminium = results_df[
        results_df["material"].fillna("").str.lower().str.contains("aluminium")
        | (
            results_df["width_mm"].between(26.0, 30.0, inclusive="both")
            & results_df["length_mm"].between(26.0, 30.0, inclusive="both")
            & results_df["thickness_mm"].between(0.3, 0.5, inclusive="both")
        )
    ]
    if aluminium.empty:
        aluminium_text = "No aluminium-labelled or 28x28x0.4-like measurement rows were found."
    else:
        aluminium_counts = aluminium["label"].value_counts().to_dict()
        evaluated_aluminium = aluminium[aluminium["label"] != "skipped"]
        if aluminium_counts.get("brass", 0) or aluminium_counts.get("brass_like", 0):
            aluminium_status = "Some aluminium-like rows were classified as brass/brass_like."
        elif aluminium_counts.get("uncertain", 0):
            aluminium_status = "Aluminium-like rows moved to uncertain."
        elif not evaluated_aluminium.empty and (evaluated_aluminium["label"] == "not_brass").all():
            aluminium_status = "Aluminium-like rows were correctly rejected as not_brass."
        else:
            aluminium_status = "Aluminium-like rows could not be evaluated because required CH1 F3 readings are missing."
        aluminium_text = f"{aluminium_status}\n\n{aluminium[['id','material','width_mm','length_mm','thickness_mm','label','confidence','z_ch1_f1','z_ch1_f3']].to_markdown(index=False)}"

    summary = f"""# Rule-Based CH1 F1 / CH1 F3 Brass Classifier Report

## Data
- Training rows loaded: {len(training_df)}
- Measurement rows loaded: {len(measurement_df)}
- Measurement rows tested: {len(results_df)}
- Skipped rows: {len(skipped_df)}

## Fitted / Loaded Surfaces

### CH1 F1
```json
{json.dumps(asdict(ch1_f1_params), indent=2)}
```

### CH1 F3
```json
{json.dumps(asdict(ch1_f3_params), indent=2)}
```

## Count By Predicted Label
{label_counts.to_markdown()}

## Count By Material And Predicted Label
{material_prediction}

## Aluminium Near 28 x 28 x 0.4 mm Check
{aluminium_text}

## Output Files
- `{results_path.name}`
- `{skipped_path.name}`
{f"- `{confusion_path.name}`" if confusion_path else "- Confusion matrix not generated because true material labels were unavailable."}
- `{plot_path.name}`
"""
    summary_path.write_text(summary, encoding="utf-8")
    return {
        "results": results_path,
        "summary": summary_path,
        "confusion": confusion_path,
        "plot": plot_path,
        "skipped": skipped_path,
    }


def run_latest_classifier_test(data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or data_dir
    training_df = load_latest_training_data(data_dir)
    measurement_df = load_latest_measurement_data(data_dir)
    ch1_f1_params = fit_surface_if_needed(training_df, "ch1_f1_abs_delta_pct", FALLBACK_CH1_F1)
    ch1_f3_params = fit_surface_if_needed(training_df, "ch1_f3_abs_delta_pct", FALLBACK_CH1_F3)
    rows = [classify_rule_based_ch1f1_ch1f3(row, ch1_f1_params, ch1_f3_params) for _, row in measurement_df.iterrows()]
    results_df = pd.DataFrame(rows)
    skipped_df = results_df[results_df["label"] == "skipped"].copy()
    paths = save_reports(results_df, skipped_df, training_df, measurement_df, ch1_f1_params, ch1_f3_params, output_dir)
    return {
        "training_rows": len(training_df),
        "measurement_rows": len(measurement_df),
        "tested_rows": len(results_df),
        "skipped_rows": len(skipped_df),
        "label_counts": results_df["label"].value_counts().to_dict(),
        "paths": paths,
    }


if __name__ == "__main__":
    result = run_latest_classifier_test()
    print(f"Total measurement rows tested: {result['tested_rows']}")
    print("Count by predicted label:")
    for label, count in result["label_counts"].items():
        print(f"  {label}: {count}")
    print("Generated files:")
    for key, path in result["paths"].items():
        if path is not None:
            print(f"  {key}: {path}")
