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

RECENT_PROJECTS_KEY = "recent_projects"
RECENT_PROJECTS_MAX = 10
LAST_PROJECT_KEY = "last_project"
UI_THEME_KEY = "ui_theme"  # light | dark | system
DEFAULT_AUTOSAVE_ENABLED_KEY = "default_autosave_enabled"
DEFAULT_AUTOSAVE_SECONDS_KEY = "default_autosave_seconds"


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

def load_recent_projects() -> list[str]:
    cleaned, changed = prune_recent_projects()
    if changed:
        data = load_settings_raw()
        data[RECENT_PROJECTS_KEY] = cleaned
        _write_settings_raw(_config_path(), data)
    return cleaned[:RECENT_PROJECTS_MAX]


def prune_recent_projects() -> tuple[list[str], bool]:
    """
    Remove non-existent paths or folders without project.json.
    Returns (cleaned_list, changed).
    """
    data = load_settings_raw()
    items = data.get(RECENT_PROJECTS_KEY) or []
    if not isinstance(items, list):
        return [], False
    out: list[str] = []
    for x in items:
        if not isinstance(x, str):
            continue
        p = x.strip()
        if not p:
            continue
        folder = Path(p)
        if folder.exists() and (folder / "project.json").exists():
            out.append(p)
    out = out[:RECENT_PROJECTS_MAX]
    old_norm = [str(i).strip() for i in items if isinstance(i, str) and str(i).strip()]
    changed = out != old_norm[:RECENT_PROJECTS_MAX]
    return out, changed


def add_recent_project(path: str) -> None:
    p = str(path).strip()
    if not p:
        return
    # Only add valid project folder
    folder = Path(p)
    if not (folder.exists() and (folder / "project.json").exists()):
        return
    data = load_settings_raw()
    items = data.get(RECENT_PROJECTS_KEY) or []
    if not isinstance(items, list):
        items = []
    # de-dup (case-insensitive on Windows-like paths is out of scope; keep simple)
    new_items = [p] + [x for x in items if isinstance(x, str) and x != p]
    data[RECENT_PROJECTS_KEY] = new_items[:RECENT_PROJECTS_MAX]
    _write_settings_raw(_config_path(), data)


def set_last_project(path: str) -> None:
    p = str(path).strip()
    if not p:
        return
    folder = Path(p)
    if not (folder.exists() and (folder / "project.json").exists()):
        return
    data = load_settings_raw()
    data[LAST_PROJECT_KEY] = p
    _write_settings_raw(_config_path(), data)


def load_last_project() -> str | None:
    data = load_settings_raw()
    p = data.get(LAST_PROJECT_KEY)
    if not isinstance(p, str) or not p.strip():
        return None
    folder = Path(p.strip())
    if folder.exists() and (folder / "project.json").exists():
        return str(folder)
    return None


def load_ui_theme() -> str:
    """
    Returns: light | dark | system
    """
    data = load_settings_raw()
    v = data.get(UI_THEME_KEY)
    if isinstance(v, str) and v.strip().lower() in ("light", "dark", "system"):
        return v.strip().lower()
    return "system"


def save_ui_theme(theme: str) -> None:
    t = str(theme).strip().lower()
    if t not in ("light", "dark", "system"):
        t = "system"
    data = load_settings_raw()
    data[UI_THEME_KEY] = t
    _write_settings_raw(_config_path(), data)


def load_default_autosave() -> tuple[bool, int]:
    data = load_settings_raw()
    enabled = data.get(DEFAULT_AUTOSAVE_ENABLED_KEY)
    seconds = data.get(DEFAULT_AUTOSAVE_SECONDS_KEY)
    if not isinstance(enabled, bool):
        enabled = True
    if not isinstance(seconds, int) or seconds < 2 or seconds > 600:
        seconds = 10
    return enabled, seconds


def save_default_autosave(enabled: bool, seconds: int) -> None:
    e = bool(enabled)
    s = int(seconds)
    if s < 2:
        s = 2
    if s > 600:
        s = 600
    data = load_settings_raw()
    data[DEFAULT_AUTOSAVE_ENABLED_KEY] = e
    data[DEFAULT_AUTOSAVE_SECONDS_KEY] = s
    _write_settings_raw(_config_path(), data)


def _write_settings_raw(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        # Windows or restricted FS
        pass

