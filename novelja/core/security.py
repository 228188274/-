from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import keyring
from platformdirs import user_config_dir


APP_SERVICE = "novelja"


def _config_path() -> Path:
    root = Path(user_config_dir(appname="novelja", appauthor="novelja"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


@dataclass
class AiSettings:
    provider: str = "deepseek"
    model: str = ""
    base_url: str = ""


def save_api_key(provider: str, api_key: str) -> None:
    """
    Prefer OS keyring. If unavailable, fall back to local config file (permissions 0600).
    """
    provider = provider.strip().lower()
    try:
        keyring.set_password(APP_SERVICE, f"api_key:{provider}", api_key)
        return
    except Exception:
        # Fallback: settings.json (local-only). Still excluded from project export by design.
        path = _config_path()
        data = load_settings_raw()
        data.setdefault("api_keys", {})[provider] = api_key
        _write_settings_raw(path, data)


def load_api_key(provider: str) -> str | None:
    provider = provider.strip().lower()
    try:
        v = keyring.get_password(APP_SERVICE, f"api_key:{provider}")
        if v:
            return v
    except Exception:
        pass
    data = load_settings_raw()
    return (data.get("api_keys") or {}).get(provider)


def save_ai_settings(settings: AiSettings) -> None:
    path = _config_path()
    data = load_settings_raw()
    data["ai"] = {
        "provider": settings.provider,
        "model": settings.model,
        "base_url": settings.base_url,
    }
    _write_settings_raw(path, data)


def load_ai_settings() -> AiSettings:
    data = load_settings_raw()
    ai = data.get("ai") or {}
    return AiSettings(
        provider=str(ai.get("provider") or "deepseek"),
        model=str(ai.get("model") or ""),
        base_url=str(ai.get("base_url") or ""),
    )


def load_settings_raw() -> dict:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_settings_raw(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        # Windows or restricted FS
        pass

