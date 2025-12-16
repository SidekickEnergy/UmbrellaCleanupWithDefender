import csv
import os
import json
from datetime import datetime, timedelta, timezone

from utils.timestamps import parse_timestamp


def load_csv(path: str):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def run_cleanup_selector(csv_path: str, created_days: int, defender_days: int | None) -> tuple[str, str]:
    """
    Identify cleanup candidates based on:
      - created at least `created_days` days ago (already enforced by pre-filter)
      - AND (if defender_days is not None) not observed in Defender within `defender_days` days.

    The CSV at `csv_path` is assumed to already have been filtered by age in a previous step,
    so this function primarily applies the Defender inactivity criterion.

    Returns:
        (cleanup_csv_path, ids_json_path)
    """
    print(f"\nLoaded CSV for cleanup selection: {csv_path}")

    rows, fieldnames = load_csv(csv_path)
    total = len(rows)

    now = datetime.now(timezone.utc)
    cutoff_created = now - timedelta(days=created_days)
    cutoff_defender = None
    if defender_days is not None:
        cutoff_defender = now - timedelta(days=defender_days)

    created_matches = 0
    defender_inactive_matches = 0
    candidates = []

    for row in rows:
        created_at = parse_timestamp(row.get("createdAt"))
        if created_at is None or created_at <= cutoff_created:
            created_matches += 1
        else:
            # Shouldn't happen if age-filtering was done correctly, but skip if it does.
            continue

        if defender_days is None:
            # No Defender crosscheck done → all aged items are candidates.
            defender_inactive_matches += 1
            candidates.append(row)
            continue

        last_seen = parse_timestamp(row.get("observedInDefender"))

        if last_seen is None or last_seen <= cutoff_defender:
            defender_inactive_matches += 1
            candidates.append(row)

    print("\nSummary (cleanup selection):")
    print(f"  Total items in CSV: {total}")
    print(f"  Created ≥ {created_days} days ago: {created_matches}")
    if defender_days is not None:
        print(f"  Not seen in Defender ≥ {defender_days} days: {defender_inactive_matches}")
    else:
        print("  Defender inactivity not evaluated (no crosscheck performed).")
    print(f"  Candidates matching criteria:     {len(candidates)}\n")

    # Export candidates
    base, ext = os.path.splitext(csv_path)
    cleanup_csv = f"{base}_to_delete.csv"
    ids_json = f"{base}_to_delete_ids.json"

    clean_fieldnames = [fn for fn in fieldnames if fn]

    cleaned_rows = []
    for row in candidates:
        cleaned = {k: row.get(k, "") for k in clean_fieldnames}
        cleaned_rows.append(cleaned)

    with open(cleanup_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    # Export ID list for deletion
    id_list = [int(row["id"]) for row in candidates if row.get("id")]
    with open(ids_json, "w", encoding="utf-8") as f:
        json.dump(id_list, f, indent=2)

    print(f"Exported cleanup candidate CSV → {cleanup_csv}")
    print(f"Exported ID list for Umbrella deletion → {ids_json}\n")

    return os.path.abspath(cleanup_csv), os.path.abspath(ids_json)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Identify Umbrella cleanup candidates.")
    parser.add_argument("--file", required=True, help="Path to CSV (age-filtered or enriched)")
    parser.add_argument("--created-days", type=int, required=True, help="Minimum age in days for deletion candidates")
    parser.add_argument("--defender-days", type=int, help="Minimum Defender inactivity in days (optional)")
    args = parser.parse_args()

    run_cleanup_selector(args.file, created_days=args.created_days, defender_days=args.defender_days)
