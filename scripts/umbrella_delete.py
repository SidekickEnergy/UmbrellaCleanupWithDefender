import os
import json
import time
import requests
from typing import List

from dotenv import load_dotenv

load_dotenv()


UMBRELLA_CLIENT_ID = os.environ.get("UMBRELLA_CLIENT_ID")
UMBRELLA_CLIENT_SECRET = os.environ.get("UMBRELLA_CLIENT_SECRET")
UMB_OAUTH_URL = "https://api.umbrella.com/auth/v2/token"
UMB_API_URL = "https://api.umbrella.com/policies/v2/destinationlists"


# ---------------------------- AUTHENTICATION ---------------------------- #

def get_umbrella_token() -> str:
    if not UMBRELLA_CLIENT_ID or not UMBRELLA_CLIENT_SECRET:
        raise SystemExit("Missing Umbrella credentials in .env")

    resp = requests.post(
        UMB_OAUTH_URL,
        auth=(UMBRELLA_CLIENT_ID, UMBRELLA_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10
    )

    if resp.status_code != 200:
        raise SystemExit(f"Failed to obtain Umbrella token: {resp.text}")

    return resp.json().get("access_token")


# ---------------------------- DELETE OPERATIONS ---------------------------- #

def delete_destinations(list_id: int, ids: List[int], token: str, batch_size: int = 100):
    """
    Cisco Umbrella supports batch delete in chunks of <= 100.
    This function splits IDs into batches and deletes them with progress logging.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    total = len(ids)
    deleted = 0
    failures = []

    print(f"\nStarting deletion of {total} destinations...\n")

    for i in range(0, total, batch_size):
        chunk = ids[i:i + batch_size]
        payload = chunk

        url = f"{UMB_API_URL}/{list_id}/destinations/remove"

        resp = requests.delete(
            url,
            headers=headers,
            data=json.dumps(payload)  # IMPORTANT: send raw JSON array
        )

        if resp.status_code in (200, 202, 204):
            deleted += len(chunk)
            print(f"[{deleted}/{total}] Deleted batch of {len(chunk)}")
        else:
            print(f"[ERROR] Failed deleting batch {chunk}: {resp.text}")
            failures.extend(chunk)

        time.sleep(0.2)  # Avoid hammering the API

    return deleted, failures


# ---------------------------- HIGH-LEVEL WRAPPER ---------------------------- #

def run_umbrella_delete(list_id, id_json_path, list_name=None, dry_run=True):
    """
    High-level workflow for deleting Umbrella destinations.
    Can be run interactively or called from main.py.
    """

    if not os.path.exists(id_json_path):
        raise SystemExit(f"File not found: {id_json_path}")

    with open(id_json_path, "r", encoding="utf-8") as f:
        ids = json.load(f)

    print(f"Loaded {len(ids)} Umbrella destination IDs to delete")
    print(f"List ID: {list_id}")
    if list_name:
        print(f"List Name: {list_name}")
    print(f"Deletion mode: {'DRY RUN' if dry_run else 'LIVE DELETE'}")


    if not dry_run:
        confirm = input("\nAre you ABSOLUTELY SURE you want to delete these destinations? (y/n): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Deletion cancelled.")
            return None

    token = get_umbrella_token()

    if dry_run:
        print("\n[DRY RUN] Would delete the following IDs:")
        print(ids)
        print("\nDry run complete.")
        return "DRY_RUN"


    # Perform actual deletion
    deleted, failures = delete_destinations(list_id, ids, token)

    print("\n=== Deletion Summary ===")
    print(f"Successfully deleted: {deleted}")
    print(f"Failed: {len(failures)}")

    if failures:
        fail_path = os.path.splitext(id_json_path)[0] + "_failed.json"
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2)
        print(f"Failed deletions saved to: {fail_path}")

    return deleted


# ---------------------------- CLI Execution ---------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Delete Umbrella destinations based on ID list JSON.")
    parser.add_argument("--list-id", required=True, type=int, help="Umbrella destination list ID")
    parser.add_argument("--file", required=True, help="Path to JSON file containing destination IDs")
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without performing them")

    args = parser.parse_args()

    run_umbrella_delete(args.list_id, args.file, dry_run=args.dry_run)
