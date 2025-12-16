import csv
import os
import time
import math
from datetime import datetime, timedelta, timezone

import requests

from utils.defender_auth import get_defender_token
from utils.timestamps import parse_timestamp

BASE_URL = "https://api.security.microsoft.com"


def build_kql_for_domain(domain: str, days: int) -> str:
    """
    Build a simple Advanced Hunting KQL query that looks for the domain/URL
    in DeviceNetworkEvents within the last `days` days, returning the latest hit.
    """
    return f"""
DeviceNetworkEvents
| where Timestamp >= ago({days}d)
| where RemoteUrl contains "{domain}"
| top 1 by Timestamp desc
| project Timestamp
"""


def run_defender_kql(kql: str, token: str):
    """
    Execute an Advanced Hunting query and return the JSON result, or None on error.
    """
    url = f"{BASE_URL}/api/advancedhunting/run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"Query": kql}

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARNING] Defender query failed: {e}")
        return None


def get_latest_defender_observation(domain: str, days: int, token: str) -> str:
    """
    Returns the latest Defender observation timestamp for the domain, formatted as
    'YYYY-MM-DD HH:MM:SS' in UTC, or '' if no results.
    """
    kql = build_kql_for_domain(domain, days)
    result = run_defender_kql(kql, token)

    if not result:
        return ""

    rows = result.get("Results", [])
    if not rows:
        return ""

    ts_raw = rows[0].get("Timestamp", "")
    dt = parse_timestamp(ts_raw)
    if not dt:
        return ""

    return dt.strftime("%Y-%m-%d %H:%M:%S")


def load_csv(path: str):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def run_defender_crosscheck(csv_path: str, days: int) -> str:
    """
    Cross-check all destinations in the given CSV against Defender for Endpoint.

    - `csv_path` should point to an Umbrella CSV with at least columns:
        id, destination, type, comment, createdAt
    - `days` defines how far back in Defender logs to search.

    Returns:
        Path to the enriched CSV with an added 'observedInDefender' column.
    """
    print(f"\nLoaded file: {csv_path}")
    print(f"Using Defender lookback: {days} days")

    rows, fieldnames = load_csv(csv_path)

    # Ensure our new column exists in fieldnames
    if "observedInDefender" not in fieldnames:
        fieldnames = list(fieldnames) + ["observedInDefender"]

    total = len(rows)
    print(f"\nTotal rows to check in Defender: {total}")

    if total == 0:
        print("No rows to process. Skipping Defender crosscheck.")
        return csv_path

    token = get_defender_token()
    if not token:
        raise SystemExit("[!] Failed to obtain Defender token")

    print("\nBeginning Defender lookup…\n")

    enriched_rows = []
    checked_count = 0
    start_time = time.time()

    for row in rows:
        domain = row.get("destination", "").strip()

        checked_count += 1
        elapsed = time.time() - start_time
        avg_per_item = elapsed / checked_count
        remaining = avg_per_item * (total - checked_count)
        eta = math.ceil(remaining)

        print(f"[{checked_count}/{total}] {domain} — ETA: {eta}s")

        if domain:
            last_seen = get_latest_defender_observation(domain, days, token)
        else:
            last_seen = ""

        row["observedInDefender"] = last_seen
        enriched_rows.append(row)

    # Write enriched CSV
    base, ext = os.path.splitext(csv_path)
    output_path = f"{base}_with_defender.csv"

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"\nDone! Enriched CSV written to:\n{output_path}\n")
    return os.path.abspath(output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-check Umbrella destinations with Microsoft Defender.")
    parser.add_argument("--file", required=True, help="Path to Umbrella CSV file")
    parser.add_argument("--days", type=int, required=True, help="How many days back to search in Defender")
    args = parser.parse_args()

    run_defender_crosscheck(args.file, days=args.days)
