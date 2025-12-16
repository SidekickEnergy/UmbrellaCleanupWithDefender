
# Cisco Umbrella Destination Cleanup Tool

  

This project provides an end-to-end, safe, and auditable workflow for identifying and cleaning up old destination entries (domains / URLs) in Cisco Umbrella destination lists, using Microsoft Defender for Endpoint telemetry as an additional validation signal.

  

The tool is designed for security teams who want to reduce noise, legacy blocks, and stale indicators in Umbrella — without risking accidental removal of still-relevant entries.

  

## Key Features
 - Export any Umbrella destination list
 - Filter entries by age (e.g. “created at least 180 days ago”)
 - Optional cross-check against Microsoft Defender
 - Identify safe deletion candidates
 - Dry-run mode before any destructive action
 - CSV + JSON outputs for auditing
 - Batch-safe Umbrella API deletion
   
## Requirements

  

 - Python 3.10+
 - Cisco Umbrella API credentials
 - Microsoft Defender for Endpoint API credentials
 - Defender Advanced Hunting permissions

  
**Install dependencies:**

    pip install -r requirements.txt

  
### Environment Variables

  

The project uses a .env file for configuration.
  

Example .env (values shown are placeholders):

  


## Usage

  

Activate your virtual environment and run:

  

    python main.py

  
  

The script will guide you interactively through the entire process.

  
### Safety Guarantees

  

 - No deletion without explicit confirmation
 - Dry-run supported and recommended
 - Double confirmation before live deletion
 - Batch size capped to Umbrella API limits
 - Consistent UTC timestamp handling
 - Deletion payload matches official Umbrella API spec

### API References

**Cisco Umbrella Destination Lists API:**

https://developer.cisco.com/docs/cloud-security/umbrella-api-api-reference-policies-destination-lists-api/

  

**Microsoft Defender Advanced Hunting API:**

https://learn.microsoft.com/en-us/microsoft-365/security/defender/advanced-hunting-overview

  
