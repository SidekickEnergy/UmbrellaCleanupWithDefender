# Cisco Umbrella Destination Cleanup Tool

A Python-based tool for safely identifying and removing stale domains and URLs from Cisco Umbrella destination lists, using Microsoft Defender for Endpoint telemetry as validation.

Designed for security teams who want to clean up legacy blocks without breaking active protections.

✨ Features

Export any Umbrella destination list

Filter entries by age (e.g. “created ≥ 180 days ago”)

Optional Defender cross-check

Identify safe deletion candidates

Dry-run support before deletion

Batch-safe Umbrella API deletion

CSV + JSON outputs for auditability

Uses .env for secrets

🧠 Workflow

Select Umbrella destination list

Filter out recently created entries

(Optional) Cross-check remaining entries against Defender

Identify deletion candidates

Dry-run deletion

(Optional) Perform live deletion

All thresholds are defined once and reused consistently.

📁 Structure
Umbrella clean-up/
├── main.py
├── scripts/
│   ├── umbrella_list_overview.py
│   ├── defender_crosscheck.py
│   ├── destination_cleanup_selector.py
│   └── umbrella_delete.py
├── utils/
│   ├── defender_auth.py
│   └── timestamps.py
├── .env
├── requirements.txt
└── README.md

🔧 Requirements

Python 3.10+

Cisco Umbrella API credentials

Microsoft Defender for Endpoint API access

Install dependencies:

pip install -r requirements.txt

🔐 Environment Variables

Create a .env file (template without secrets is committed):

# Cisco Umbrella
UMBRELLA_CLIENT_ID=
UMBRELLA_CLIENT_SECRET=

# Microsoft Defender
DEFENDER_TENANT_ID=
DEFENDER_CLIENT_ID=
DEFENDER_CLIENT_SECRET=
DEFENDER_SCOPE=https://api.security.microsoft.com/.default


⚠️ Never commit real secrets.

▶️ Usage
python main.py


The script runs interactively and guides you through the full cleanup process.

🧪 Safety

No deletion without confirmation

Dry-run supported and recommended

Double confirmation for live deletion

Payloads match official Umbrella API specs

UTC timestamps handled consistently

📚 References

Cisco Umbrella API
https://developer.cisco.com/docs/cloud-security/

Microsoft Defender Advanced Hunting
https://learn.microsoft.com/microsoft-365/security/defender/
