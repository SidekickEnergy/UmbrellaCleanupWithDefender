# Umbrella destination list exporter

This small utility fetches destination lists from an Umbrella-style API and exports the destinations (domains/URLs and creation timestamps) to CSV or Excel.

Files added:

- `scripts/export_umbrella_list.py` — main script
- `requirements.txt` — Python dependencies
- `config_template.json` — example config file

Quick start

1. Create a config file (use `config_template.json` as a starting point). You must provide `lists_url` and `destinations_url_template` and any required `headers` for authentication. The template is pre-filled for Cisco Umbrella API v2.

2. Create a virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run the script:

```powershell
python .\scripts\export_umbrella_list.py --config .\config.json --output destinations.csv
```


Notes

- This repository is configured to call Cisco Umbrella API v2 destination lists by default (the template uses `https://api.umbrella.com/policies/v2/destinationlists`). Umbrella v2 uses page & limit pagination (defaults to limit=100, max=100); the script detects and uses page-based pagination for these endpoints.
- Authentication: Umbrella supports OAuth2 client credentials and Umbrella API keys. The simplest option for this script is to obtain a bearer token and place it in `config.json` under `headers.Authorization` as `Bearer <TOKEN>`. You can also implement the client credentials flow externally and supply the token in the config.
- The script expects the lists endpoint to return a JSON array under `data` or `items`, or a top-level list. Each list should contain an `id` field. The destinations endpoint returns paginated `data` with destination objects.
- Field mapping: the exporter looks for `destination`, `domain`, `url`, or `value` for the destination value and `created_at`, `createdAt`, `created`, `dateCreated` for timestamps. If Umbrella uses different fields in your org, update the script or supply a sample response and I will adapt the extractor.

If you want, I can wire the script to implement the OAuth2 client credentials flow (fetch token automatically from Umbrella) — tell me if you prefer the script to manage token acquisition or if you will provide a long-lived token in the config.
