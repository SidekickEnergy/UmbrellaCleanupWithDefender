from dotenv import load_dotenv
load_dotenv()  # Load .env variables before anything else

import os
import requests
from typing import Optional, Dict, Any

DEFAULT_SCOPE = "https://api.security.microsoft.com/.default"


def _get_env(name: str) -> str:
    """Read and strip an environment variable (returns empty string if unset)."""
    return (os.environ.get(name) or "").strip()


def get_defender_token_result() -> Dict[str, Any]:
    """
    Fetch a Microsoft 365 Defender API token using client credentials.
    Returns a dict:
      - on success: {"access_token": "<token>"}
      - on error:   {"error": "<code>", ...additional context...}
    """
    tenant_id = _get_env("DEFENDER_TENANT_ID")
    client_id = _get_env("DEFENDER_CLIENT_ID")
    client_secret = _get_env("DEFENDER_CLIENT_SECRET")
    scope = _get_env("DEFENDER_SCOPE") or DEFAULT_SCOPE

    if not tenant_id or not client_id or not client_secret:
        return {
            "error": "missing_env",
            "details": "Set DEFENDER_TENANT_ID, DEFENDER_CLIENT_ID, DEFENDER_CLIENT_SECRET",
        }

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "scope": scope,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json() or {}
        token = data.get("access_token")
        if not token:
            return {
                "error": "no_token_in_response",
                "status": resp.status_code,
                "body": resp.text[:1000],
            }
        return {"access_token": token}
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", "n/a")
        body = getattr(e.response, "text", "")
        return {"error": "http_error", "status": status, "body": body[:1000]}
    except requests.RequestException as e:
        return {"error": "network_error", "details": str(e)}


def get_defender_token() -> Optional[str]:
    """
    Backwards-compatible helper that returns only the access token string or None.
    """
    result = get_defender_token_result()
    return result.get("access_token") if isinstance(result, dict) else None


def get_defender_headers(token: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience helper to build Authorization headers.
    If token is None, tries to fetch one.
    """
    token = token or get_defender_token()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


if __name__ == "__main__":
    # Minimal self-test without printing the token
    result = get_defender_token_result()
    if result.get("access_token"):
        print("[+] Access token retrieved successfully.")
    else:
        print("[!] Failed to retrieve token:", result)
