import json
import os
from datetime import datetime, timezone
import requests

API_BASE_URL = os.getenv("BOND_API_BASE_URL")
API_KEY = os.getenv("BOND_API_KEY")

MATURITIES = ["3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]

CONFIG_FILE = "countries_config.json"
OUTPUT_FILE = "yield_curves.json"


def fetch_series_latest(series_id):
    response = requests.get(
        API_BASE_URL,
        params={
            "series_id": series_id,
            "api_key": API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    obs = data.get("observations", [])
    if not obs:
        return None, None

    value = obs[0]["value"]
    date = obs[0]["date"]

    try:
        return float(value), date
    except:
        return None, date


def compute_metrics(curve):
    y2 = curve.get("2Y")
    y10 = curve.get("10Y")
    y30 = curve.get("30Y")

    slope_2s10s = round(y10 - y2, 2) if y2 and y10 else None
    slope_10s30s = round(y30 - y10, 2) if y10 and y30 else None
    inverted = slope_2s10s is not None and slope_2s10s < 0

    return {
        "slope_2s10s": slope_2s10s,
        "slope_10s30s": slope_10s30s,
        "inverted": inverted
    }


def main():
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    output = {
        "meta": {
            "lastUpdated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "BondStats Yield Curve Feed",
            "type": "sovereign_yield_curve"
        },
        "countries": {}
    }

    for key, country in config.items():
        curve = {}
        date = None

        for maturity in MATURITIES:
            series_id = country["series"].get(maturity)

            if not series_id:
                continue

            value, obs_date = fetch_series_latest(series_id)

            if value is not None:
                curve[maturity] = value

            if obs_date and not date:
                date = obs_date

        if not curve:
            continue

        output["countries"][key] = {
            "label": country["label"],
            "curve": curve,
            "metrics": compute_metrics(curve),
            "date": date
        }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print("yield_curves.json generated")


if __name__ == "__main__":
    main()
