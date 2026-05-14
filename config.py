import os

def get(key: str):
    env_map = {
        "application_channel_id":      "APPLICATION_CHANNEL_ID",
        "application_webhook_secret":  "APP_WEBHOOK_SECRET",
        "suggestions_channel_id":      "SUGGESTIONS_CHANNEL_ID",
        "events_channel_id":           "EVENTS_CHANNEL_ID",
        "staff_role_id":               "STAFF_ROLE_ID",
        "admin_role_id":               "ADMIN_ROLE_ID",
        "relay_secret":                "RELAY_SECRET",
        "announcement_channel_id":     "ANNOUNCEMENT_CHANNEL_ID",
    }
    env_key = env_map.get(key)
    if env_key:
        return os.environ.get(env_key)
    return None

def set_value(key: str, value) -> None:
    print(f"[Config] set_value called for '{key}' — use Railway environment variables to persist this value.")

def load() -> dict:
    return {k: get(k) for k in [
        "application_channel_id",
        "application_webhook_secret",
        "suggestions_channel_id",
        "events_channel_id",
        "staff_role_id",
        "admin_role_id",
        "relay_secret",
        "announcement_channel_id",
    ]}

def save(cfg: dict) -> None:
    print("[Config] save() called — use Railway environment variables to persist config.")
