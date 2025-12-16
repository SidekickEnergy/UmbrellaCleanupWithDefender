import os
import sys
import csv
import json
from datetime import datetime, timedelta, timezone

# Ensure package imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.timestamps import parse_timestamp
from scripts.umbrella_list_overview import run_umbrella_export
from scripts.defender_crosscheck import run_defender_crosscheck
from scripts.destination_cleanup_selector import run_cleanup_selector
from scripts.umbrella_delete import run_umbrella_delete


def ask_yes_no(question: str) -> bool:
    while True:
        ans = input(f"{question} (y/n): ").strip().lower()
        if ans in ("y", "n"):
            return ans == "y"
        print("Please enter 'y' or 'n'.")

def ask_delete_mode(question: str) -> str:
    """
    Ask user: yes (live delete), no, or dry run.
    Returns: "yes", "no", or "dry"
    """
    prompt = f"{question} (y/n/dry): "

    while True:
        ans = input(prompt).strip().lower()

        if ans in ("y", "yes"):
            return "yes"
        if ans in ("n", "no"):
            return "no"
        if ans in ("dry", "d"):
            return "dry"

        print("Please enter 'y', 'n', or 'dry'.")

def ask_int(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid integer.")


def filter_by_created_age(csv_path: str, created_days: int) -> str:
    """
    Read an Umbrella CSV and keep only rows created at least `created_days` ago.
    Writes an intermediate CSV and returns its path.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=created_days)

    print(f"\n[AGE FILTER] Using created-at cutoff: {cutoff} (≥ {created_days} days old)")

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    kept = []
    total = len(rows)
    too_new = 0

    for row in rows:
        created = parse_timestamp(row.get("createdAt"))
        if created is None or created <= cutoff:
            kept.append(row)
        else:
            too_new += 1

    base, ext = os.path.splitext(csv_path)
    output_path = f"{base}_created_gte_{created_days}d.csv"

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(kept)

    print(f"\n[AGE FILTER] Total rows: {total}")
    print(f"[AGE FILTER] Kept (≥ {created_days} days): {len(kept)}")
    print(f"[AGE FILTER] Discarded as too new: {too_new}")
    print(f"[AGE FILTER] Output written to: {output_path}\n")

    return os.path.abspath(output_path)


def extract_list_id_from_user() -> int:
    """
    Ask the user which Umbrella destination list ID to delete from.
    """
    return ask_int("Enter the Umbrella Destination List ID to delete from: ")


def main():

    print("\n=== Cisco Umbrella Cleanup Workflow ===\n")

    # ---------------------------------------------------------------
    # STEP 1 — Export Umbrella destination list
    # ---------------------------------------------------------------
    if ask_yes_no("Do you want to export a destination list from Umbrella now?"):
        umbrella_csv, list_id, list_name = run_umbrella_export(verbose=True)
    else:
        umbrella_csv = input("Enter path to an existing Umbrella destination CSV: ").strip()
        # If user supplies their own CSV, ask for metadata
        list_id = ask_int("Enter the Umbrella Destination List ID this CSV belongs to: ")
        list_name = input("Enter the Umbrella Destination List name: ").strip()


    if not os.path.exists(umbrella_csv):
        print(f"ERROR: File does not exist → {umbrella_csv}")
        return

    print(f"\n[INFO] Using Umbrella CSV: {umbrella_csv}\n")

    # ---------------------------------------------------------------
    # STEP 2 — Filter by CreatedAt age
    # ---------------------------------------------------------------
    created_days = ask_int("Created AT LEAST how many days ago should entries be to be considered? ")
    aged_csv = filter_by_created_age(umbrella_csv, created_days=created_days)

    # ---------------------------------------------------------------
    # STEP 3 — Defender Crosscheck (optional)
    # ---------------------------------------------------------------
    defender_days = None
    enriched_csv = aged_csv

    if ask_yes_no("Do you want to crosscheck the aged entries against Microsoft Defender?"):
        defender_days = ask_int("How many days back should Defender be checked (e.g. 180)?: ")
        enriched_csv = run_defender_crosscheck(aged_csv, days=defender_days)

    if not os.path.exists(enriched_csv):
        print(f"ERROR: File does not exist → {enriched_csv}")
        return

    print(f"\n[INFO] Using CSV for cleanup selection: {enriched_csv}\n")

    # ---------------------------------------------------------------
    # STEP 4 — Cleanup Candidate Selection (automatic using Option A)
    # ---------------------------------------------------------------
    cleanup_csv, cleanup_ids = run_cleanup_selector(
        enriched_csv,
        created_days=created_days,
        defender_days=defender_days,
    )

    print("\n=== STAGE 4 COMPLETE ===")
    print(f"Cleanup CSV:          {cleanup_csv}")
    print(f"Cleanup ID list:      {cleanup_ids}\n")

    if not os.path.exists(cleanup_ids):
        print("ERROR: Cleanup ID JSON missing. Cannot proceed to deletion.")
        return

    # ---------------------------------------------------------------
    # STEP 5 — Optional Deletion
    # ---------------------------------------------------------------
    import json
    count_to_delete = len(json.load(open(cleanup_ids)))

    if defender_days is not None:
        delete_message = (
            f"Do you want to delete all items created at least {created_days} days ago "
            f"and not seen in Defender for at least {defender_days} days "
            f"from the \"{list_name}\" destination list?\n"
            f"In total this will delete {count_to_delete} destinations. "
            f"I can also perform a dry run."
        )
    else:
        delete_message = (
            f"Do you want to delete all items created at least {created_days} days ago "
            f"from the \"{list_name}\" destination list?\n"
            f"In total this will delete {count_to_delete} destinations. "
            f"I can also perform a dry run."
        )

    print()  # Spacer

    mode = ask_delete_mode(delete_message)

    if mode == "no":
        print("Deletion skipped.")
        return

    # Safety confirmation only for live deletion
    if mode == "yes":
        if not ask_yes_no("Are you absolutely sure you want to delete these destinations?"):
            print("Deletion aborted.")
            return
        dry_run = False
    else:
        dry_run = True

    # Run deletion
    result = run_umbrella_delete(
        list_id=list_id,
        list_name=list_name,
        id_json_path=cleanup_ids,
        dry_run=dry_run,
    )

    # If a dry run was performed, offer the live deletion
    if result == "DRY_RUN":
        print()
        if ask_yes_no("Dry run complete. Do you want to perform the LIVE deletion now?"):
            if ask_yes_no("Are you absolutely sure?"):
                run_umbrella_delete(
                    list_id=list_id,
                    list_name=list_name,
                    id_json_path=cleanup_ids,
                    dry_run=False
                )
            else:
                print("Live deletion aborted.")




    print("\n=== FULL WORKFLOW COMPLETE ===\n")


if __name__ == "__main__":
    main()
