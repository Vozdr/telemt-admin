from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(os.getenv("TELEMT_CONFIG", "/data/telemt/config/config.toml"))
BACKUP_DIR = Path(os.getenv("TELEMT_BACKUP_DIR", "/data/backups"))
MAX_BACKUPS = int(os.getenv("TELEMT_MAX_BACKUPS", "20"))
APP_VERSION = os.getenv("TELEMT_ADMIN_VERSION", "dev")
DEV_VERSION = os.getenv("TELEMT_ADMIN_DEV_VERSION", "1.4.2")
DISPLAY_VERSION = f"{DEV_VERSION} dev" if APP_VERSION == "dev" else APP_VERSION
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR")
GITHUB_URL = "https://github.com/Vozdr/telemt-admin/"
READ_ONLY = os.getenv("READ_ONLY", "no").lower() in {"1", "true", "yes", "on"}
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "yes").lower() not in {"0", "false", "no", "off"}
TELEMT_METRICS_LISTEN = os.getenv("TELEMT_METRICS_LISTEN", "0.0.0.0:9090")
AUTO_FIX_METRICS_LISTEN = os.getenv("AUTO_FIX_METRICS_LISTEN", "yes").lower() not in {"0", "false", "no", "off"}
METRICS_URL = os.getenv("TELEMT_METRICS_URL", "http://telemt:9090/metrics")
ENABLE_BASIC_AUTH = os.getenv("ENABLE_BASIC_AUTH", "no").lower() in {"1", "true", "yes", "on"}
ENABLE_WEB_AUTH = os.getenv("ENABLE_WEB_AUTH", "yes").lower() not in {"0", "false", "no", "off"}
BASIC_ADMIN_USER = os.getenv("BASIC_ADMIN_USER") or os.getenv("ADMIN_USER") or os.getenv("XUI_ADMIN_USER") or "admin"
BASIC_ADMIN_PASS = os.getenv("BASIC_ADMIN_PASS") or os.getenv("ADMIN_PASS") or os.getenv("XUI_ADMIN_PASS") or "admin"
WEB_ADMIN_USER = os.getenv("WEB_ADMIN_USER") or os.getenv("ADMIN_USER") or os.getenv("XUI_ADMIN_USER") or "admin"
WEB_ADMIN_PASS = os.getenv("WEB_ADMIN_PASS") or os.getenv("ADMIN_PASS") or os.getenv("XUI_ADMIN_PASS") or "admin"
SESSION_SECRET = os.getenv("SESSION_SECRET") or WEB_ADMIN_PASS or BASIC_ADMIN_PASS or secrets.token_hex(16)
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "dark").lower()
if DEFAULT_THEME not in {"light", "dark"}:
    DEFAULT_THEME = "dark"
LOCALES_DIR = Path(os.getenv("LOCALES_DIR", "/app/locales"))
DOCS_CACHE_DIR = Path(os.getenv("TELEMT_DOCS_CACHE_DIR", "/tmp/telemt-admin-docs"))
ENABLE_DOCS_FETCH = os.getenv("ENABLE_DOCS_FETCH", "yes").lower() not in {"0", "false", "no", "off"}
DOCS_FETCH_TIMEOUT = int(os.getenv("TELEMT_DOCS_FETCH_TIMEOUT", "8"))
DOCS_URLS = {
    "en": os.getenv(
        "TELEMT_CONFIG_PARAMS_EN_URL",
        "https://raw.githubusercontent.com/telemt/telemt/main/docs/Config_params/CONFIG_PARAMS.en.md",
    ),
    "ru": os.getenv(
        "TELEMT_CONFIG_PARAMS_RU_URL",
        "https://raw.githubusercontent.com/telemt/telemt/main/docs/Config_params/CONFIG_PARAMS.ru.md",
    ),
}
DOCS_PUBLIC_URLS = {
    "en": os.getenv(
        "TELEMT_CONFIG_PARAMS_EN_PUBLIC_URL",
        "https://github.com/telemt/telemt/blob/main/docs/Config_params/CONFIG_PARAMS.en.md",
    ),
    "ru": os.getenv(
        "TELEMT_CONFIG_PARAMS_RU_PUBLIC_URL",
        "https://github.com/telemt/telemt/blob/main/docs/Config_params/CONFIG_PARAMS.ru.md",
    ),
}

SECRET_RE = re.compile(r"^[0-9a-fA-F]{32}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
META_RE = re.compile(
    r"^\s*#\s*telemt-admin:\s+user=(?P<user>[A-Za-z0-9_-]+)"
    r"(?:\s+added_at=(?P<added_at>\S+))?"
    r"(?:\s+updated_at=(?P<updated_at>\S+))?"
    r"(?:\s+blocked_at=(?P<blocked_at>\S+))?\s*$"
)
ASSIGN_RE = re.compile(
    r"^(?P<prefix>\s*)(?P<comment>#\s*)?(?P<key>[A-Za-z0-9_-]+)\s*=\s*"
    r"(?P<value>.+?)\s*(?P<trail>#.*)?$"
)
ASSIGN_ANY_RE = re.compile(r"^\s*(?P<key>[A-Za-z0-9_-]+)\s*=\s*(?P<value>.+?)\s*(?:#.*)?$")
DOC_META: dict[str, dict[str, dict[str, Any]]] = {"en": {}, "ru": {}}
