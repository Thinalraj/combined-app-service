"""REV 2026-10-02 / RATES-01: isolated, read-only reference-price service.

Gold API: USD per troy ounce. Frankfurter: daily USD/MYR reference FX.
No sensor access, third-party packages, API keys, or jewellery retail markup.
RATES-02: daily midnight MYT updates, manual override and persistent quotes.
RATES-LIST-01: include platinum; validate cached values and retain cooldown
across restarts. Quotes are estimates of metal content, not jewellery prices.
"""
import copy
import json
import math
import threading
import time
import urllib.request
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from system_assets import api_config


def optional_currency(data, field):
    try:
        return mapped(data, field)
    except KeyError:
        return "USD"  # Existing Gold API response omits currency; adapter declares USD.


def mapped(data, field):
    """ASSETS-01: dot paths allow nested JSON without changing the parser."""
    for key in field.split("."):
        data = data[key]
    return data


TROY_OUNCE_G = 31.1034768
REFRESH_SECONDS = 86400
QUOTE_MAX_AGE_SECONDS = 26 * 3600
MYT = timezone(timedelta(hours=8))
MANUAL_COOLDOWN_SECONDS = 60
METALS = ("XAU", "XAG", "XPT", "XPD")


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ThinalReferenceRates/1.0"})
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read(65536))


def positive(value):
    if isinstance(value, bool):
        raise ValueError("Invalid price")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Invalid price")
    return value


def quote_time(value):
    if not isinstance(value, str):
        raise ValueError("Invalid quote timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Quote timestamp needs a timezone")
    return result.timestamp()


class MetalRates:
    def __init__(self, fetch=get_json, clock=time.time, monotonic=time.monotonic, cache_path=None):
        self.fetch, self.clock, self.monotonic = fetch, clock, monotonic
        self.lock = threading.Lock()
        self.quotes = {}
        self.errors = {}
        self.fx = None
        self.busy = False
        self.last_attempt = None
        self.attempt_day = None
        self.last_attempt_at = None
        self.cache_path = Path(cache_path) if cache_path else None
        # RATES-02: reuse saved quotes/attempt date after a normal service restart.
        if self.cache_path:
            try:
                saved = json.loads(self.cache_path.read_text(encoding="utf-8"))
                quotes = saved["quotes"]
                if not isinstance(quotes, dict):
                    raise ValueError("Invalid saved quotes")
                for symbol, quote in quotes.items():
                    if symbol not in METALS or not isinstance(quote, dict):
                        raise ValueError("Invalid saved metal")
                    quote["myr_per_g"] = positive(quote["myr_per_g"])
                    quote["timestamp"] = positive(quote["timestamp"])
                    if abs(quote_time(quote["updated_at"]) - quote["timestamp"]) > 1:
                        raise ValueError("Saved quote timestamps disagree")
                    if float(quote["timestamp"]) > self.clock() + 300:
                        raise ValueError("Saved quote timestamp is in the future")
                    date.fromisoformat(quote["fx_date"])
                    quote.setdefault("failed", False)
                attempt_day = saved.get("attempt_day")
                if attempt_day is not None:
                    date.fromisoformat(attempt_day)
                self.quotes = quotes
                self.fx = saved.get("fx")
                self.attempt_day = attempt_day
                self.errors = saved.get("errors", {}) if isinstance(saved.get("errors", {}), dict) else {}
                attempted = saved.get("last_attempt_at")
                if isinstance(attempted, (int, float)) and math.isfinite(attempted):
                    elapsed = max(0, self.clock() - attempted)
                    self.last_attempt = self.monotonic() - elapsed
                    self.last_attempt_at = attempted
            except (OSError, ValueError, KeyError, TypeError):
                pass

    def _save(self):
        if not self.cache_path:
            return
        try:
            temporary = self.cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"quotes": self.quotes, "fx": self.fx,
                "attempt_day": self.attempt_day, "last_attempt_at": self.last_attempt_at,
                "errors": self.errors}), encoding="utf-8")
            temporary.replace(self.cache_path)
            self.errors.pop("CACHE", None)
        except OSError as exc:
            self.errors["CACHE"] = "Unable to save rates: " + str(exc)

    def start_daily_scheduler(self):
        # RATES-02: backend owns the schedule even when the home screen is closed.
        # Run one service process; multiple independent workers have separate locks.
        def schedule():
            while True:
                self.snapshot()
                now = datetime.fromtimestamp(self.clock(), MYT)
                midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                threading.Event().wait(max(1, (midnight - now).total_seconds()))
        threading.Thread(target=schedule, daemon=True).start()

    def _refresh(self):
        try:
            config = api_config()
            fx_source, metal_source = config["fx"], config["metals"]
            now = self.clock()
            with self.lock:
                fx = copy.deepcopy(self.fx)
            # RATES-02: each update fetches the latest daily reference FX.
            data = self.fetch(fx_source["url"])
            if mapped(data, fx_source["base_field"]).upper() != "USD" or mapped(data, fx_source["quote_field"]).upper() != "MYR":
                raise ValueError("Wrong FX pair")
            fx_date = date.fromisoformat(mapped(data, fx_source["date_field"]))
            age = (datetime.fromtimestamp(now, timezone.utc).date() - fx_date).days
            if not 0 <= age <= 7:
                raise ValueError("FX reference is too old")
            fx = {"rate": positive(mapped(data, fx_source["rate_field"])), "date": fx_date.isoformat(), "fetched_at": now}
            with self.lock:
                self.fx = fx
                self.errors.pop("FX", None)
            for symbol in METALS:
                try:
                    data = self.fetch(metal_source["url"].replace("{symbol}", symbol))
                    if mapped(data, metal_source["symbol_field"]) != symbol or optional_currency(data, metal_source["currency_field"]) != "USD":
                        raise ValueError("Wrong metal or currency")
                    price = positive(mapped(data, metal_source["price_field"])) * fx["rate"] / TROY_OUNCE_G
                    timestamp = quote_time(mapped(data, metal_source["time_field"]))
                    if timestamp > self.clock() + 300:
                        raise ValueError("Quote timestamp is in the future")
                    with self.lock:
                        previous = self.quotes.get(symbol)
                        if previous and timestamp < previous["timestamp"]:
                            raise ValueError("Quote timestamp went backwards")
                        # Repeated provider timestamps are not a new trend sample.
                        change = previous.get("change_pct") if previous else None
                        baseline = previous.get("baseline_at") if previous else None
                        if previous and timestamp > previous["timestamp"]:
                            change = (price / previous["myr_per_g"] - 1) * 100
                            baseline = previous["updated_at"]
                        self.quotes[symbol] = {
                            "myr_per_g": price, "updated_at": mapped(data, metal_source["time_field"]),
                            "timestamp": timestamp, "fx_date": fx["date"],
                            "change_pct": change, "baseline_at": baseline, "failed": False,
                        }
                        self.errors.pop(symbol, None)
                except Exception as exc:
                    with self.lock:
                        self.errors[symbol] = str(exc)
                        if symbol in self.quotes:
                            self.quotes[symbol]["failed"] = True
        except Exception as exc:
            with self.lock:
                self.errors["FX"] = str(exc)
                for item in self.quotes.values():
                    item["failed"] = True
        finally:
            with self.lock:
                self.busy = False
                self._save()

    def snapshot(self, manual=False):
        # Respond immediately; network timeouts never block the touchscreen.
        with self.lock:
            now = self.monotonic()
            today = datetime.fromtimestamp(self.clock(), MYT).date().isoformat()
            cooldown = max(0, MANUAL_COOLDOWN_SECONDS - (now - self.last_attempt)) if self.last_attempt is not None else 0
            # Daily attempts include failures: no hidden repeated provider calls.
            # A manual update overrides the daily gate after the cooldown.
            if not self.busy and (self.attempt_day != today or (manual and cooldown == 0)):
                self.busy = True
                self.last_attempt = now
                self.last_attempt_at = self.clock()
                self.attempt_day = today
                self._save()
                cooldown = MANUAL_COOLDOWN_SECONDS
                threading.Thread(target=self._refresh, daemon=True).start()
            result = copy.deepcopy(self.quotes)
            pending = self.busy
            errors = dict(self.errors)
        for item in result.values():
            fx_age = (datetime.fromtimestamp(self.clock(), timezone.utc).date() - date.fromisoformat(item["fx_date"])).days
            item["stale"] = bool(item.pop("failed")) or self.clock() - item.pop("timestamp") > QUOTE_MAX_AGE_SECONDS or not 0 <= fx_age <= 7
        return {"currency": "MYR", "unit": "g", "pending": pending,
                "source": "Gold API + Frankfurter", "metals": result, "errors": errors,
                "trend_basis": "since previous update", "refresh_seconds": REFRESH_SECONDS,
                "schedule": "00:00 Asia/Kuala_Lumpur", "manual_retry_after": math.ceil(cooldown),
                "last_attempt_at": self.last_attempt_at,
                "metals_requested": list(METALS), "provider_calls_per_full_refresh": len(METALS) + 1}


if __name__ == "__main__":
    # Standalone network checker: starts no Flask server and touches no sensors.
    rates = MetalRates()
    result = rates.snapshot()
    deadline = time.monotonic() + 45
    while result["pending"] and time.monotonic() < deadline:
        time.sleep(0.05)
        result = rates.snapshot()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if len(result["metals"]) == len(METALS) and not any(q["stale"] for q in result["metals"].values()) else 1)
