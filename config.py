import json, os

CONFIG_FILE = "config.json"

DEFAULTS = {
    "application_channel_id": None,
    "application_webhook_secret": None,
    "suggestions_channel_id": None,
    "events_channel_id": None,
    "staff_role_id": None,
    "admin_role_id": None,
    "relay_secret": None,
    "announcement_channel_id": None,
    "application_webhook_port": 5000,
}

def load() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save(DEFAULTS.copy())
    with open(CONFIG_FILE) as f:
        data = json.load(f)
    changed = False
    for k, v in DEFAULTS.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed:
        save(data)
    return data

def save(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get(key: str):
    env_map = {
        "application_webhook_secret": "APP_WEBHOOK_SECRET",
    }
    if key in env_map:
        env_val = os.environ.get(env_map[key])
        if env_val:
            return env_val
    return load().get(key)

def set_value(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)
