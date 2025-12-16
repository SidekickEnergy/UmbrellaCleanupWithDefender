from dotenv import load_dotenv
load_dotenv()  # Make Umbrella credentials available

import os
import csv
import requests
import math
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone
from utils.timestamps import parse_timestamp

BASE_URL = "https://api.umbrella.com"
TOKEN_URL = f"{BASE_URL}/auth/v2/token"


class UmbrellaAPI:
    def __init__(self, client_id: str, client_secret: str, verbose=True):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.verbose = verbose

    # --------------------------
    # TOKEN HANDLING
    # --------------------------
    def get_token(self):
        if self.verbose:
            print("[DEBUG] Requesting OAuth token…")

        auth = HTTPBasicAuth(self.client_id, self.client_secret)
        client = BackendApplicationClient(client_id=self.client_id)
        oauth = OAuth2Session(client=client)
        self.token = oauth.fetch_token(token_url=TOKEN_URL, auth=auth)

        if self.verbose:
            print("[DEBUG] Token acquired.")
            print("[DEBUG] Token expires_in:", self.token.get("expires_in"))
        return self.token

    def _headers(self):
        if self.token is None:
            self.get_token()
        return {
            "Authorization": f"Bearer {self.token['access_token']}",
            "Content-Type": "application/json"
        }

    # --------------------------
    # HTTP GET (with verbose)
    # --------------------------
    def get(self, endpoint: str):
        url = f"{BASE_URL}/{endpoint}"
        if self.verbose:
            print(f"[DEBUG] GET {url}")

        resp = requests.get(url, headers=self._headers())

        if self.verbose:
            print(f"[DEBUG] Response {resp.status_code}")

        resp.raise_for_status()
        return resp.json()

    # --------------------------
    # LISTS + DESTINATIONS
    # --------------------------
    def list_destination_lists(self) -> list:
        if self.verbose:
            print("[DEBUG] Fetching destination lists…")

        data = self.get("policies/v2/destinationlists")
        lists = data.get("data", [])

        if self.verbose:
            print(f"[DEBUG] Retrieved {len(lists)} destination lists.")

        return lists

    def list_destinations(self, list_id: int) -> list:
        """Fetch all destinations for a list using correct metadata structure (page-based pagination)."""

        # Step 1: Fetch metadata for this destination list
        meta_endpoint = f"policies/v2/destinationlists/{list_id}"
        if self.verbose:
            print(f"[DEBUG] GET metadata: {BASE_URL}/{meta_endpoint}")

        meta_resp = self.get(meta_endpoint)

        total = meta_resp.get("data", {}).get("meta", {}).get("destinationCount")

        if total is None:
            print("[WARNING] destinationCount missing in metadata! Falling back to single-page fetch.")
            total = 0  # will just do one page

        if self.verbose:
            print(f"[DEBUG] destinationCount = {total}")

        # Step 2: Calculate number of pages
        limit = 100
        num_pages = max(1, math.ceil(total / limit)) if total else 1

        if self.verbose:
            print(f"[DEBUG] Will fetch {num_pages} page(s) at limit={limit}")

        all_results = []

        # Step 3: Perform page-based fetch
        for page in range(1, num_pages + 1):
            endpoint = (
                f"policies/v2/destinationlists/{list_id}/destinations"
                f"?limit={limit}&page={page}"
            )

            if self.verbose:
                print(f"[DEBUG] GET page {page}/{num_pages}: {BASE_URL}/{endpoint}")

            resp = requests.get(f"{BASE_URL}/{endpoint}", headers=self._headers())
            resp.raise_for_status()

            chunk = resp.json().get("data", [])
            all_results.extend(chunk)

            if self.verbose:
                print(f"[DEBUG] Retrieved {len(chunk)} items (running total: {len(all_results)})")

            # Safety: stop early if we’ve reached or exceeded expected total
            if total and len(all_results) >= total:
                if self.verbose:
                    print("[DEBUG] Reached expected total count. Stopping.")
                break

        return all_results



def clean_comment(text):
    """Sanitize comment to avoid breaking CSV structure."""
    if not text:
        return ""
    return (
        text.replace("\t", "\\t")     # Replace tabs with literal "\t"
            .replace("\n", "\\n")     # Replace newlines
            .replace("\r", "")        # Remove CR
            .strip()
    )


def export_to_csv(destinations: list, filename: str):
    if not destinations:
        print("No destinations to export.")
        return

    # -----------------------------------------------
    # 1. Determine ALL keys that appear in ANY row
    # -----------------------------------------------
    all_keys = sorted({key for row in destinations for key in row.keys()})

    # Ensure stable essential fields are first if they exist
    preferred_order = ["id", "destination", "type", "comment", "createdAt"]
    all_keys = preferred_order + [k for k in all_keys if k not in preferred_order]

    print(f"[DEBUG] CSV Columns: {all_keys}")

    # -----------------------------------------------
    # 2. Normalize and sanitize every row
    # -----------------------------------------------
    normalized_rows = []

    for row in destinations:
        norm = {}

        # Guarantee all keys exist
        for key in all_keys:
            value = row.get(key, "")

            # Field-specific cleaning
            if key == "comment":
                value = clean_comment(value)

            elif key in ("createdAt", "modifiedAt"):
                dt = None

                # Case: Umbrella returns UNIX epoch seconds
                try:
                    dt = datetime.fromtimestamp(int(value), tz=timezone.utc)
                except:
                    dt = parse_timestamp(value)

                if dt:
                    value = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    value = ""


            elif key == "id":
                value = str(value) if value is not None else ""

            elif isinstance(value, str):
                # Strip stray spaces (common with Umbrella API)
                value = value.strip()

            norm[key] = value

        normalized_rows.append(norm)

    # -----------------------------------------------
    # 3. Write CSV using safe quoting rules
    # -----------------------------------------------
    print(f"[DEBUG] Writing CSV → {filename}")

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=all_keys,
            quoting=csv.QUOTE_ALL,   # FULL safety
            escapechar="\\",         # Handles edge cases
        )
        writer.writeheader()
        writer.writerows(normalized_rows)

    print("[DEBUG] CSV export complete.\n")


def choose_list_interactively(umbrella: UmbrellaAPI):
    lists = umbrella.list_destination_lists()

    if not lists:
        print("No destination lists found.")
        return None

    print("\n=== Cisco Umbrella Destination Lists ===\n")
    for i, lst in enumerate(lists, start=1):
        print(f"[{i}]  {lst['name']}  (ID: {lst['id']})")

    print("\n-------------------------------------")
    chosen = input("Enter the number of the destination list to export: ").strip()

    try:
        index = int(chosen)
        if 1 <= index <= len(lists):
            return lists[index - 1]
    except ValueError:
        pass

    print("Invalid selection.")
    return None

def run_umbrella_export(verbose: bool = True) -> str:
    """
    Run the full Umbrella export flow:
    - Authenticate using env vars
    - Let user pick a destination list
    - Fetch all destinations
    - Export to CSV

    Returns:
        Absolute path to the generated CSV file.
    """
    client_id = os.environ.get("UMBRELLA_CLIENT_ID")
    client_secret = os.environ.get("UMBRELLA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise SystemExit("ERROR: Please set UMBRELLA_CLIENT_ID and UMBRELLA_CLIENT_SECRET.")

    umbrella = UmbrellaAPI(client_id, client_secret, verbose=verbose)

    selected_list = choose_list_interactively(umbrella)
    if not selected_list:
        raise SystemExit("No list selected, aborting.")

    list_id = selected_list["id"]
    name = selected_list["name"]

    print(f"\n[DEBUG] Selected list: {name} (ID: {list_id})\n")

    destinations = umbrella.list_destinations(list_id)

    safe_name = "".join(
        c for c in name if c.isalnum() or c in (" ", "_")
    ).strip().replace(" ", "_")
    filename = f"{safe_name}_destinations.csv"

    export_to_csv(destinations, filename)

    # Return absolute path so main.py can use it reliably
    output_path = os.path.abspath(filename)

    # Correct triple return value
    return (
        output_path,          # full path to CSV
        selected_list["id"],  # Umbrella list ID
        selected_list["name"] # Umbrella list name
    )


if __name__ == "__main__":
    # Allow running directly
    run_umbrella_export(verbose=True)

