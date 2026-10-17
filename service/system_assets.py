"""ASSETS-01: shared configuration root, safe discovery and explicit model roles.

Scanning only lists files. Loading a selected model happens in its own adapter.
Unknown algorithms are discoverable but never executed automatically.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent / "system_assets"
RF_FEATURE_NAMES = ['f1_delta_ch1', 'f1_delta_ch2', 'f2_delta_ch1', 'f2_delta_ch2', 'f3_delta_ch1', 'f3_delta_ch2', 'f1_delta_pct', 'f2_delta_pct', 'f3_delta_pct', 'weight_g', 'thickness_mm', 'contact_area_ratio']
ROLES = {"gold": ".joblib", "purity": ".joblib"}
DEFAULT_MODELS = {"gold": "metal/gold.joblib", "purity": "metal/purity.joblib"}
DEFAULT_API = {
    "services": {"weight": "http://127.0.0.1:8002", "vision": "http://127.0.0.1:8003", "signal": "http://127.0.0.1:8001"},
    "metals": {"url": "https://api.gold-api.com/price/{symbol}", "price_field": "price", "time_field": "updatedAt", "symbol_field": "symbol", "currency_field": "currency", "unit": "USD/troy_ounce"},
    "fx": {"url": "https://api.frankfurter.dev/v2/rate/USD/MYR", "rate_field": "rate", "date_field": "date", "base_field": "base", "quote_field": "quote", "unit": "MYR/USD"}
}


def asset_path(value, suffix=None, must_exist=False):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Use a path relative to system_assets, with / separators")
    relative = Path(value)
    path = (ROOT / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Model must be inside system_assets")
    if suffix and path.suffix.lower() != suffix:
        raise ValueError("Expected a " + suffix + " file")
    if must_exist and not path.is_file():
        raise ValueError("Asset not found: " + value)
    return path


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
            temporary = Path(out.name)
            json.dump(value, out, indent=2, allow_nan=False)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def read_json(name, default):
    path = ROOT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def model_selection():
    values = read_json("model_registry.json", DEFAULT_MODELS)
    if not isinstance(values, dict) or set(values) != set(ROLES):
        raise ValueError("model_registry.json needs gold and purity paths")
    for role, suffix in ROLES.items():
        asset_path(values[role], suffix)
    return values


def scan():
    found = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            continue
        suffix = path.suffix.lower()
        if suffix not in (".pt", ".joblib", ".pkl", ".onnx", ".json", ".py"):
            continue
        stat = path.stat()
        found.append({"path": path.relative_to(ROOT).as_posix(), "bytes": stat.st_size,
                      "candidate_roles": ["vision"] if suffix == ".pt" else ["gold", "purity", "reference"] if suffix == ".joblib" else [],
                      "status": "candidate; validation required" if suffix in (".pt", ".joblib") else "stored; no automatic execution"})
        if len(found) >= 1000:
            break
    return {"root": str(ROOT), "files": found, "selection": model_selection(), "api": api_config()}


def validate_api(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT_API):
        raise ValueError("API config needs services, metals and fx")
    for group, defaults in DEFAULT_API.items():
        section = value[group]
        if not isinstance(section, dict) or set(section) != set(defaults):
            raise ValueError("Unexpected/missing fields in " + group)
        for key, item in section.items():
            if not isinstance(item, str) or not item.strip():
                raise ValueError("API values must be nonempty strings")
            if key == "url" or group == "services":
                parsed = urlsplit(item.replace("{symbol}", "XAU"))
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                    raise ValueError("Enter an HTTP(S) URL without credentials or a fragment")
    if value["metals"]["unit"] != "USD/troy_ounce" or value["fx"]["unit"] != "MYR/USD":
        raise ValueError("The installed rate adapter requires USD/troy_ounce and MYR/USD")
    if value["metals"]["url"].count("{symbol}") != 1:
        raise ValueError("Metal URL must contain {symbol} once")
    return copy.deepcopy(value)


def api_config():
    return validate_api(read_json("api_sources.json", DEFAULT_API))


def migrate_legacy(view_dir):
    """Copy once, never overwrite selected/newer files or delete old originals."""
    candidates = {"algorithms/classifier_model.json": [view_dir / "classifier_model.json"]}
    for role in ROLES:
        name = "model_" + role + "_frequency_best_20260630_RF.joblib"
        candidates[DEFAULT_MODELS[role]] = [view_dir / name, view_dir.parent / "teaching_master_build_20260630" / name]
    for relative, sources in candidates.items():
        target = asset_path(relative)
        if not target.exists():
            for source in sources:
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    if target.suffix == ".joblib":
                        write_json(target.with_suffix(".joblib.json"), {"adapter": "frequency_rf_v1",
                            "feature_names": RF_FEATURE_NAMES, "migrated_from": source.name})
                    break


if __name__ == "__main__":
    # Standalone configuration checker: no sensor access or model deserialization.
    try:
        print(json.dumps(scan(), indent=2))
    except (ValueError, OSError) as exc:
        raise SystemExit("Assets: " + str(exc))
