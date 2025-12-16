from datetime import datetime, timezone

def parse_timestamp(value):
    """
    Universal timestamp parser for ALL scripts.
    Always returns timezone-aware UTC datetime.
    Returns None if parsing fails.
    """
    if not value:
        return None

    v = str(value).strip()

    # --- ISO formats (Defender style) ---
    if "T" in v:
        try:
            v_norm = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v_norm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except:
            pass

    # --- Standard CSV format: YYYY-MM-DD HH:MM:SS ---
    try:
        dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except:
        pass

    return None
