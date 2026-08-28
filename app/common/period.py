from datetime import datetime, timezone


def get_current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")
