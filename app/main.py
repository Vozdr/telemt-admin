from __future__ import annotations

import base64
import errno
import html
import io
import json
import os
import re
import secrets
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import qrcode
import qrcode.image.svg
from fastapi import Cookie, Form, Request
from fastapi import Depends, HTTPException
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field


CONFIG_PATH = Path(os.getenv("TELEMT_CONFIG", "/data/telemt/config/config.toml"))
BACKUP_DIR = Path(os.getenv("TELEMT_BACKUP_DIR", "/data/backups"))
MAX_BACKUPS = int(os.getenv("TELEMT_MAX_BACKUPS", "20"))
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
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "light").lower()
if DEFAULT_THEME not in {"light", "dark"}:
    DEFAULT_THEME = "light"
LOCALES_DIR = Path(os.getenv("LOCALES_DIR", "/app/locales"))
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
    r"(?P<value>\"(?:[^\"\\]|\\.)*\"|[0-9]+)\s*(?P<trail>#.*)?$"
)


app = FastAPI(title="TeleMT Admin")
security = HTTPBasic(auto_error=False)


def make_session_token(username: str) -> str:
    import hashlib
    import hmac
    import time

    issued = str(int(time.time()))
    payload = f"{username}:{issued}"
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def valid_session_token(token: str | None) -> bool:
    import hashlib
    import hmac
    import time

    if not token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, issued, signature = raw.rsplit(":", 2)
    except Exception:
        return False
    payload = f"{username}:{issued}"
    expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    if username != WEB_ADMIN_USER:
        return False
    return int(time.time()) - int(issued) < 60 * 60 * 24 * 30


def valid_basic(credentials: HTTPBasicCredentials | None) -> bool:
    if not credentials:
        return False
    user_ok = secrets.compare_digest(credentials.username, BASIC_ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, BASIC_ADMIN_PASS)
    return user_ok and pass_ok


def require_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),
    telemt_admin_session: str | None = Cookie(default=None),
) -> None:
    if not ENABLE_BASIC_AUTH and not ENABLE_WEB_AUTH:
        return
    if ENABLE_BASIC_AUTH and not valid_basic(credentials):
        raise HTTPException(
            status_code=401,
            detail="Basic authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if ENABLE_WEB_AUTH and not valid_session_token(telemt_admin_session):
        raise HTTPException(status_code=401, detail="Web authentication required")


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    secret: str | None = None
    limit: int = Field(default=0, ge=0, le=100000)
    comment: str = Field(default="", max_length=200)
    blocked: bool = False


class RenameInput(UserInput):
    old_name: str = Field(min_length=1, max_length=64)


class ToggleInput(BaseModel):
    blocked: bool


class SecretInput(BaseModel):
    secret: str | None = None


@dataclass
class UserRecord:
    name: str
    secret: str
    limit: int
    comment: str
    blocked: bool
    added_at: str
    updated_at: str
    blocked_at: str
    stats: dict[str, Any]
    link: str
    qr: str


def read_config() -> str:
    if not CONFIG_PATH.exists():
        raise HTTPException(500, f"Файл конфигурации не найден: {CONFIG_PATH}")
    return CONFIG_PATH.read_text(encoding="utf-8")


def make_backup() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(CONFIG_PATH, BACKUP_DIR / f"config.toml.{stamp}.bak")
    backups = sorted(BACKUP_DIR.glob("config.toml.*.bak"), key=lambda p: p.stat().st_mtime)
    for old in backups[:-MAX_BACKUPS]:
        old.unlink(missing_ok=True)


def write_config(text: str) -> None:
    make_backup()
    tmp = CONFIG_PATH.with_suffix(".toml.tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        tmp.replace(CONFIG_PATH)
    except OSError as exc:
        if exc.errno != errno.EBUSY:
            raise
        # Some container filesystems, notably MikroTik containers bind mounts,
        # reject atomic rename over a mounted/busy config file. Keep those
        # deployments working by updating the existing inode in place.
        with CONFIG_PATH.open("w", encoding="utf-8") as target:
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        tmp.unlink(missing_ok=True)


def ensure_metrics_listen() -> None:
    if not ENABLE_METRICS or not AUTO_FIX_METRICS_LISTEN or not CONFIG_PATH.exists():
        return
    text = CONFIG_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    changed = False
    for idx, line in enumerate(lines):
        if re.match(r"^\s*metrics_listen\s*=", line):
            current = parse_value(line.split("=", 1)[1].split("#", 1)[0].strip())
            if current.startswith("127.0.0.1:") or current.startswith("localhost:"):
                suffix = ""
                if "#" in line:
                    suffix = " #" + line.split("#", 1)[1]
                lines[idx] = f'metrics_listen = "{TELEMT_METRICS_LISTEN}"{suffix}'
                changed = True
            break
    if changed:
        write_config("\n".join(lines).rstrip() + "\n")


@app.on_event("startup")
def startup_checks() -> None:
    ensure_metrics_listen()
    if not ENABLE_BASIC_AUTH and not ENABLE_WEB_AUTH:
        print("WARNING: TeleMT Admin authentication is disabled. Do not expose it to untrusted networks.", flush=True)
    if ENABLE_BASIC_AUTH and BASIC_ADMIN_USER == "admin" and BASIC_ADMIN_PASS == "admin":
        print("WARNING: TeleMT Admin Basic Auth is using default credentials admin/admin.", flush=True)
    if ENABLE_WEB_AUTH and WEB_ADMIN_USER == "admin" and WEB_ADMIN_PASS == "admin":
        print("WARNING: TeleMT Admin web login is using default credentials admin/admin.", flush=True)


def section_bounds(lines: list[str], section: str) -> tuple[int | None, int | None]:
    start = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m and m.group(1) == section:
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if SECTION_RE.match(lines[j]):
            end = j
            break
    return start, end


def ensure_section(lines: list[str], section: str) -> tuple[int, int]:
    start, end = section_bounds(lines, section)
    if start is not None and end is not None:
        return start, end
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend([f"[{section}]"])
    return len(lines) - 1, len(lines)


def clean_comment(comment: str) -> str:
    return " ".join(comment.replace("\n", " ").replace("\r", " ").strip().split())


def quote_comment(comment: str) -> str:
    comment = clean_comment(comment)
    return f" # {comment}" if comment else ""


def parse_value(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return bytes(raw[1:-1], "utf-8").decode("unicode_escape")
    return raw


def parse_assignments(lines: list[str], section: str) -> dict[str, dict[str, Any]]:
    start, end = section_bounds(lines, section)
    result: dict[str, dict[str, Any]] = {}
    if start is None or end is None:
        return result
    pending_meta: dict[str, str] | None = None
    pending_meta_line: int | None = None
    for idx in range(start + 1, end):
        meta = META_RE.match(lines[idx])
        if meta:
            pending_meta = {
                "user": meta.group("user") or "",
                "added_at": meta.group("added_at") or "",
                "updated_at": meta.group("updated_at") or "",
                "blocked_at": meta.group("blocked_at") or "",
            }
            pending_meta_line = idx
            continue
        m = ASSIGN_RE.match(lines[idx])
        if not m:
            pending_meta = None
            pending_meta_line = None
            continue
        key = m.group("key")
        trail = (m.group("trail") or "").strip()
        comment = trail[1:].strip() if trail.startswith("#") else ""
        metadata = pending_meta if pending_meta and pending_meta.get("user") == key else {}
        result[key] = {
            "line": idx,
            "meta_line": pending_meta_line if metadata else None,
            "value": parse_value(m.group("value")),
            "blocked": bool(m.group("comment")),
            "comment": comment,
            "added_at": metadata.get("added_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "blocked_at": metadata.get("blocked_at", ""),
        }
        pending_meta = None
        pending_meta_line = None
    return result


def get_setting(text: str, section: str, key: str, default: str = "") -> str:
    lines = text.splitlines()
    start, end = section_bounds(lines, section)
    if start is None or end is None:
        return default
    for line in lines[start + 1 : end]:
        m = ASSIGN_RE.match(line)
        if m and m.group("key") == key:
            return parse_value(m.group("value"))
    return default


def get_top_level_setting(text: str, key: str, default: str = "") -> str:
    for line in text.splitlines():
        if SECTION_RE.match(line):
            break
        m = ASSIGN_RE.match(line)
        if m and m.group("key") == key:
            return parse_value(m.group("value"))
    return default


def get_any_setting(text: str, key: str, default: str = "") -> str:
    for line in text.splitlines():
        m = ASSIGN_RE.match(line)
        if m and m.group("key") == key:
            return parse_value(m.group("value"))
    return default


def telemt_public_host(text: str) -> str:
    return (
        get_top_level_setting(text, "public_host")
        or get_any_setting(text, "public_host")
        or get_setting(text, "censorship", "tls_domain")
        or "telemt.example.com"
    )


def telemt_public_port(text: str) -> int:
    raw = get_top_level_setting(text, "public_port") or get_any_setting(text, "public_port", "443")
    try:
        return int(raw)
    except ValueError:
        return 443


def telemt_endpoint(host: str, port: int) -> str:
    return f"{host}:{port}"


def telemt_config_info(text: str) -> dict[str, Any]:
    host = telemt_public_host(text)
    port = telemt_public_port(text)
    users = parse_assignments(text.splitlines(), "access.users")
    limits = parse_assignments(text.splitlines(), "access.user_max_unique_ips")
    blocked = sum(1 for item in users.values() if item.get("blocked"))
    return {
        "public_host": host,
        "public_port": port,
        "endpoint": telemt_endpoint(host, port),
        "server": {
            "listen": get_setting(text, "server", "listen", ""),
            "metrics_listen": get_setting(text, "server", "metrics_listen", ""),
        },
        "censorship": {
            "tls_domain": get_setting(text, "censorship", "tls_domain", ""),
            "mask_host": get_setting(text, "censorship", "mask_host", ""),
        },
        "access": {
            "users": len(users),
            "blocked_users": blocked,
            "limited_users": len(limits),
        },
        "admin": {
            "metrics_enabled": ENABLE_METRICS,
            "metrics_url": METRICS_URL,
            "auto_fix_metrics_listen": AUTO_FIX_METRICS_LISTEN,
        },
    }


def validate_name(name: str) -> None:
    if not NAME_RE.match(name):
        raise HTTPException(400, "Имя может содержать только латиницу, цифры, '_' и '-'.")


def validate_secret(secret: str) -> str:
    secret = secret.lower()
    if not SECRET_RE.match(secret):
        raise HTTPException(400, "Secret должен быть 32 hex-символа.")
    return secret


def generated_secret() -> str:
    return secrets.token_hex(16)


def domain_hex(domain: str) -> str:
    return domain.encode("utf-8").hex()


def make_link(secret: str, host: str, port: int, tls_domain: str) -> str:
    sni_domain = tls_domain or host
    return f"tg://proxy?server={host}&port={port}&secret=ee{secret}{domain_hex(sni_domain)}"


def make_qr_data_uri(link: str) -> str:
    img = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', raw):
        labels[part[0]] = bytes(part[1], "utf-8").decode("unicode_escape")
    return labels


def read_metrics() -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not ENABLE_METRICS:
        return {}, [], []
    try:
        with urllib.request.urlopen(METRICS_URL, timeout=3) as response:
            text = response.read().decode("utf-8", "replace")
    except Exception:
        return {}, [], []

    per_user: dict[str, dict[str, float]] = {}
    raw_user: list[dict[str, Any]] = []
    raw_global: list[dict[str, Any]] = []
    metric_re = re.compile(r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>[-+0-9.eE]+)$")
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = metric_re.match(line)
        if not m:
            continue
        labels = parse_labels(m.group("labels") or "")
        try:
            value = float(m.group("value"))
        except ValueError:
            continue
        name = m.group("name")
        user = labels.get("user")
        item = {"name": name, "labels": labels, "value": value}
        if user:
            per_user.setdefault(user, {})[name] = value
            raw_user.append(item)
        else:
            raw_global.append(item)
    return per_user, raw_user, raw_global


def user_stats(metrics: dict[str, float]) -> dict[str, Any]:
    rx = int(metrics.get("telemt_user_octets_from_client", 0))
    tx = int(metrics.get("telemt_user_octets_to_client", 0))
    return {
        "connections_total": int(metrics.get("telemt_user_connections_total", 0)),
        "connections_current": int(metrics.get("telemt_user_connections_current", 0)),
        "bytes_from_client": rx,
        "bytes_to_client": tx,
        "bytes_total": rx + tx,
        "msgs_from_client": int(metrics.get("telemt_user_msgs_from_client", 0)),
        "msgs_to_client": int(metrics.get("telemt_user_msgs_to_client", 0)),
        "unique_ips_current": int(metrics.get("telemt_user_unique_ips_current", 0)),
        "unique_ips_recent_window": int(metrics.get("telemt_user_unique_ips_recent_window", 0)),
        "unique_ips_limit": int(metrics.get("telemt_user_unique_ips_limit", 0)),
        "unique_ips_utilization": float(metrics.get("telemt_user_unique_ips_utilization", 0)),
        "available": bool(metrics),
    }


def latest_metric(metrics: list[dict[str, Any]], name: str, labels: dict[str, str] | None = None) -> float:
    labels = labels or {}
    value = 0.0
    for item in metrics:
        if item["name"] != name:
            continue
        if all(item["labels"].get(k) == v for k, v in labels.items()):
            value = float(item["value"])
    return value


def global_stats(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "uptime_seconds": latest_metric(metrics, "telemt_uptime_seconds"),
        "connections_total": latest_metric(metrics, "telemt_connections_total"),
        "connections_bad_total": latest_metric(metrics, "telemt_connections_bad_total"),
        "handshake_timeouts_total": latest_metric(metrics, "telemt_handshake_timeouts_total"),
        "user_entries": latest_metric(metrics, "telemt_stats_user_entries"),
        "user_telemetry_enabled": latest_metric(metrics, "telemt_telemetry_user_enabled"),
        "buffer_in_use": latest_metric(metrics, "telemt_buffer_pool_buffers_total", {"kind": "in_use"}),
        "buffer_allocated": latest_metric(metrics, "telemt_buffer_pool_buffers_total", {"kind": "allocated"}),
        "upstream_connect_attempts": latest_metric(metrics, "telemt_upstream_connect_attempt_total"),
        "upstream_connect_success": latest_metric(metrics, "telemt_upstream_connect_success_total"),
        "upstream_connect_fail": latest_metric(metrics, "telemt_upstream_connect_fail_total"),
        "enabled": ENABLE_METRICS,
        "available": bool(metrics),
    }


def line_for_user(name: str, secret: str, comment: str, blocked: bool) -> str:
    prefix = "# " if blocked else ""
    return f'{prefix}{name} = "{secret}"{quote_comment(comment)}'


def line_for_meta(name: str, added_at: str = "", updated_at: str = "", blocked_at: str = "") -> str | None:
    parts = [f"user={name}"]
    if added_at:
        parts.append(f"added_at={added_at}")
    if updated_at:
        parts.append(f"updated_at={updated_at}")
    if blocked_at:
        parts.append(f"blocked_at={blocked_at}")
    if len(parts) == 1:
        return None
    return "# telemt-admin: " + " ".join(parts)


def line_for_limit(name: str, limit: int, comment: str, blocked: bool) -> str:
    prefix = "# " if blocked else ""
    return f"{prefix}{name} = {limit}"


def remove_key(lines: list[str], section: str, name: str) -> None:
    items = parse_assignments(lines, section)
    item = items.get(name)
    if item:
        lines.pop(item["line"])


def remove_user_with_meta(lines: list[str], name: str) -> int | None:
    users = parse_assignments(lines, "access.users")
    item = users.get(name)
    if not item:
        return None
    line = item["line"]
    meta_line = item.get("meta_line")
    insert_at = meta_line if meta_line is not None else line
    lines.pop(line)
    if meta_line is not None:
        lines.pop(meta_line)
    return insert_at


def insert_user_with_meta(lines: list[str], index: int, name: str, secret: str, comment: str, blocked: bool, added_at: str, updated_at: str, blocked_at: str) -> None:
    meta = line_for_meta(name, added_at, updated_at, blocked_at)
    insert_lines = [line_for_user(name, secret, comment, blocked)]
    if meta:
        insert_lines.insert(0, meta)
    for offset, line in enumerate(insert_lines):
        lines.insert(index + offset, line)


def upsert_user(data: UserInput, old_name: str | None = None) -> None:
    validate_name(data.name)
    if old_name:
        validate_name(old_name)
    secret = validate_secret(data.secret or generated_secret())
    comment = clean_comment(data.comment)

    text = read_config()
    lines = text.splitlines()
    ensure_section(lines, "access.users")
    ensure_section(lines, "access.user_max_unique_ips")
    users = parse_assignments(lines, "access.users")

    target_exists = data.name in users and data.name != old_name
    if target_exists:
        raise HTTPException(409, "Пользователь с таким именем уже есть.")

    source_name = old_name or data.name
    source_item = users.get(source_name)
    if old_name and old_name != data.name:
        remove_key(lines, "access.user_max_unique_ips", old_name)
        insert_at = remove_user_with_meta(lines, old_name)
    elif old_name and old_name not in users:
        raise HTTPException(404, "Пользователь не найден.")
    elif source_item:
        insert_at = remove_user_with_meta(lines, data.name)
    else:
        _, end = ensure_section(lines, "access.users")
        insert_at = end

    if insert_at is None:
        _, insert_at = ensure_section(lines, "access.users")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    added_at = source_item.get("added_at", "") if source_item else now
    updated_at = now if source_item else ""
    was_blocked = bool(source_item and source_item.get("blocked"))
    old_blocked_at = source_item.get("blocked_at", "") if source_item else ""
    blocked_at = old_blocked_at if data.blocked and was_blocked else ""
    if data.blocked and not blocked_at:
        blocked_at = now
    insert_user_with_meta(lines, insert_at, data.name, secret, comment, data.blocked, added_at, updated_at, blocked_at)

    remove_key(lines, "access.user_max_unique_ips", data.name)
    if data.limit > 0:
        _, end = ensure_section(lines, "access.user_max_unique_ips")
        lines.insert(end, line_for_limit(data.name, data.limit, comment, data.blocked))

    write_config("\n".join(lines).rstrip() + "\n")


def list_users() -> list[UserRecord]:
    text = read_config()
    host = telemt_public_host(text)
    port = telemt_public_port(text)
    tls_domain = get_setting(text, "censorship", "tls_domain", host)
    lines = text.splitlines()
    users = parse_assignments(lines, "access.users")
    limits = parse_assignments(lines, "access.user_max_unique_ips")
    metrics, _, _ = read_metrics()
    result: list[UserRecord] = []
    for name in sorted(users):
        u = users[name]
        limit_item = limits.get(name)
        blocked = bool(u["blocked"] or (limit_item and limit_item["blocked"]))
        limit = int(limit_item["value"]) if limit_item and str(limit_item["value"]).isdigit() else 0
        comment = u["comment"]
        secret = validate_secret(str(u["value"]))
        link = make_link(secret, host, port, tls_domain)
        stats = user_stats(metrics.get(name, {}))
        result.append(UserRecord(name, secret, limit, comment, blocked, u["added_at"], u["updated_at"], u["blocked_at"], stats, link, make_qr_data_uri(link)))
    return result


def find_user(name: str) -> UserRecord:
    validate_name(name)
    for user in list_users():
        if user.name == name:
            return user
    raise HTTPException(404, "Пользователь не найден.")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/i18n/{lang}")
def api_i18n(lang: str) -> dict[str, Any]:
    lang = re.sub(r"[^a-zA-Z0-9_-]", "", lang) or DEFAULT_LANG
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / f"{DEFAULT_LANG}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))


LOGIN_PAGE = """
<!doctype html>
<html lang="en" data-theme="__DEFAULT_THEME__">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleMT Admin Login</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef3f5;
      --panel: #ffffff;
      --ink: #17212b;
      --muted: #52616e;
      --line: #d7e0e6;
      --control: #ffffff;
      --accent: #147d78;
      --accent-dark: #0e5e5a;
      --danger: #b72d3a;
      --shadow: rgba(16, 31, 45, .12);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #11181f;
      --panel: #18222b;
      --ink: #e8eef2;
      --muted: #a9b7c3;
      --line: #31414f;
      --control: #121b23;
      --accent: #35aaa2;
      --accent-dark: #69c9c2;
      --danger: #ff7883;
      --shadow: rgba(0, 0, 0, .34);
    }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg); color: var(--ink); }
    .top-controls { position: fixed; top: 16px; right: 16px; display: flex; gap: 8px; align-items: center; }
    select { height: 34px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 9px; font: inherit; }
    form { width: min(360px, calc(100vw - 32px)); background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; box-shadow: 0 18px 48px var(--shadow); }
    h1 { margin: 0 0 18px; font-size: 24px; letter-spacing: 0; }
    label { display: block; margin: 0 0 6px; color: var(--muted); font-size: 13px; }
    input { width: 100%; height: 38px; border: 1px solid var(--line); border-radius: 7px; padding: 0 10px; font: inherit; box-sizing: border-box; background: var(--control); color: var(--ink); }
    .field { margin-bottom: 14px; }
    button { width: 100%; height: 40px; border: 1px solid var(--accent); border-radius: 7px; background: var(--accent); color: #fff; font: inherit; cursor: pointer; }
    button:hover { background: var(--accent-dark); }
    .error { margin-bottom: 12px; color: var(--danger); font-size: 13px; }
  </style>
</head>
<body>
  <div class="top-controls">
    <select id="loginLangSelect" title="Language">
      <option value="en">EN</option>
      <option value="ru">RU</option>
    </select>
    <select id="loginThemeSelect" data-i18n-title="theme.theme" title="Theme">
      <option value="light" data-i18n="theme.light">Light</option>
      <option value="dark" data-i18n="theme.dark">Dark</option>
    </select>
  </div>
  <form method="post" action="login">
    <h1>TeleMT Admin</h1>
    {error}
    <div class="field"><label data-i18n="login.username">Username</label><input name="username" autocomplete="username" required autofocus></div>
    <div class="field"><label data-i18n="login.password">Password</label><input name="password" type="password" autocomplete="current-password" required></div>
    <button type="submit" data-i18n="login.signIn">Sign in</button>
  </form>
  <script>
    const defaultLang = "__DEFAULT_LANG__";
    const defaultTheme = "__DEFAULT_THEME__";
    const langSelect = document.getElementById("loginLangSelect");
    const themeSelect = document.getElementById("loginThemeSelect");
    let i18n = {};
    function t(key) { return i18n[key] || key; }
    function applyI18n() {
      document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
      document.querySelectorAll("[data-i18n-title]").forEach(el => { el.title = t(el.dataset.i18nTitle); });
      document.documentElement.lang = langSelect.value || "en";
    }
    async function loadI18n(lang) {
      const res = await fetch(`api/i18n/${encodeURIComponent(lang)}`, { credentials: "same-origin" });
      i18n = await res.json();
      localStorage.setItem("telemtAdmin.lang", lang);
      langSelect.value = lang;
      applyI18n();
    }
    function setTheme(theme) {
      const safeTheme = theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = safeTheme;
      themeSelect.value = safeTheme;
      localStorage.setItem("telemtAdmin.theme", safeTheme);
    }
    langSelect.onchange = () => loadI18n(langSelect.value);
    themeSelect.onchange = () => setTheme(themeSelect.value);
    setTheme(localStorage.getItem("telemtAdmin.theme") || defaultTheme);
    loadI18n(localStorage.getItem("telemtAdmin.lang") || defaultLang).catch(() => {});
  </script>
</body>
</html>
"""


def render_login_page(error: bool = False) -> str:
    error_html = '<div class="error" data-i18n="login.invalid">Invalid username or password</div>' if error else ""
    return (
        LOGIN_PAGE
        .replace("__DEFAULT_LANG__", DEFAULT_LANG)
        .replace("__DEFAULT_THEME__", DEFAULT_THEME)
        .replace("{error}", error_html)
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(credentials: HTTPBasicCredentials | None = Depends(security)):
    if ENABLE_BASIC_AUTH and not valid_basic(credentials):
        raise HTTPException(
            status_code=401,
            detail="Basic authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not ENABLE_WEB_AUTH:
        return RedirectResponse("./")
    return render_login_page()


@app.post("/login")
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    credentials: HTTPBasicCredentials | None = Depends(security),
):
    if ENABLE_BASIC_AUTH and not valid_basic(credentials):
        raise HTTPException(
            status_code=401,
            detail="Basic authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not ENABLE_WEB_AUTH:
        return RedirectResponse("./", status_code=303)
    if secrets.compare_digest(username, WEB_ADMIN_USER) and secrets.compare_digest(password, WEB_ADMIN_PASS):
        response = RedirectResponse("./", status_code=303)
        response.set_cookie("telemt_admin_session", make_session_token(username), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
        return response
    return HTMLResponse(render_login_page(error=True), status_code=401)


@app.get("/logout")
def logout():
    response = RedirectResponse("login", status_code=303)
    response.delete_cookie("telemt_admin_session")
    return response


def render_index_page() -> str:
    return (
        PAGE
        .replace("__DEFAULT_LANG__", DEFAULT_LANG)
        .replace("__DEFAULT_THEME__", DEFAULT_THEME)
        .replace("__WEB_AUTH_ENABLED__", "true" if ENABLE_WEB_AUTH else "false")
        .replace("__WEB_AUTH_HIDDEN__", "" if ENABLE_WEB_AUTH else "hidden")
    )


@app.get("/api/users")
def api_users(_: None = Depends(require_auth)) -> dict[str, Any]:
    text = read_config()
    users = list_users()
    metrics_available = any(user.stats.get("available") for user in users)
    config = telemt_config_info(text)
    return {
        "users": [u.__dict__ for u in users],
        "domain": config["endpoint"],
        "public_host": config["public_host"],
        "public_port": config["public_port"],
        "config": config,
        "metrics": {"enabled": ENABLE_METRICS, "url": METRICS_URL, "available": metrics_available},
        "default_lang": DEFAULT_LANG,
        "default_theme": DEFAULT_THEME,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/telemt/config")
def api_telemt_config(_: None = Depends(require_auth)) -> dict[str, Any]:
    return telemt_config_info(read_config())


@app.get("/api/users/{name}/stats")
def api_user_stats(name: str, _: None = Depends(require_auth)) -> dict[str, Any]:
    user = find_user(name)
    if not ENABLE_METRICS:
        return {"user": user.name, "summary": user_stats({}), "metrics": []}
    metrics, raw, _ = read_metrics()
    rows = [item for item in raw if item["labels"].get("user") == name]
    return {"user": user.name, "summary": user_stats(metrics.get(name, {})), "metrics": rows}


@app.get("/api/telemt/stats")
def api_telemt_stats(_: None = Depends(require_auth)) -> dict[str, Any]:
    if not ENABLE_METRICS:
        return {"summary": global_stats([]), "metrics": []}
    _, _, raw = read_metrics()
    return {"summary": global_stats(raw), "metrics": raw}


@app.post("/api/users")
def api_create_user(data: UserInput, _: None = Depends(require_auth)) -> dict[str, Any]:
    if not data.secret:
        data.secret = generated_secret()
    upsert_user(data)
    return {"ok": True, "user": find_user(data.name).__dict__}


@app.put("/api/users/{name}")
def api_update_user(name: str, data: UserInput, _: None = Depends(require_auth)) -> dict[str, Any]:
    upsert_user(data, old_name=name)
    return {"ok": True, "user": find_user(data.name).__dict__}


@app.post("/api/users/{name}/secret")
def api_rotate_secret(name: str, data: SecretInput, _: None = Depends(require_auth)) -> dict[str, Any]:
    user = find_user(name)
    new_secret = validate_secret(data.secret or generated_secret())
    upsert_user(UserInput(name=user.name, secret=new_secret, limit=user.limit, comment=user.comment, blocked=user.blocked), old_name=name)
    return {"ok": True, "user": find_user(name).__dict__}


@app.post("/api/users/{name}/blocked")
def api_toggle_user(name: str, data: ToggleInput, _: None = Depends(require_auth)) -> dict[str, Any]:
    user = find_user(name)
    upsert_user(UserInput(name=user.name, secret=user.secret, limit=user.limit, comment=user.comment, blocked=data.blocked), old_name=name)
    return {"ok": True, "user": find_user(name).__dict__}


@app.delete("/api/users/{name}")
def api_delete_user(name: str, _: None = Depends(require_auth)) -> dict[str, bool]:
    validate_name(name)
    text = read_config()
    lines = text.splitlines()
    if name not in parse_assignments(lines, "access.users"):
        raise HTTPException(404, "Пользователь не найден.")
    remove_key(lines, "access.user_max_unique_ips", name)
    remove_user_with_meta(lines, name)
    write_config("\n".join(lines).rstrip() + "\n")
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    telemt_admin_session: str | None = Cookie(default=None),
):
    if not ENABLE_BASIC_AUTH and not ENABLE_WEB_AUTH:
        return render_index_page()
    if ENABLE_BASIC_AUTH and not valid_basic(credentials):
        raise HTTPException(
            status_code=401,
            detail="Basic authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if ENABLE_WEB_AUTH and valid_session_token(telemt_admin_session):
        return render_index_page()
    if ENABLE_WEB_AUTH:
        return RedirectResponse("login", status_code=303)
    return render_index_page()


PAGE = r"""
<!doctype html>
<html lang="ru" data-theme="__DEFAULT_THEME__">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleMT Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef3f5;
      --panel: #ffffff;
      --ink: #17212b;
      --muted: #64717f;
      --line: #d7e0e6;
      --accent: #147d78;
      --accent-dark: #0e5e5a;
      --danger: #b72d3a;
      --warn: #a56a00;
      --ok: #1d7a46;
      --control: #ffffff;
      --soft: #f8fafb;
      --soft-2: #fbfcfd;
      --accent-soft: #f0fbf9;
      --blocked-bg: #f7f8f9;
      --hover: #edf4f6;
      --line-strong: #a8bac6;
      --tooltip-bg: #111f2a;
      --tooltip-ink: #ffffff;
      --shadow: rgba(16, 31, 45, .26);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #11181f;
      --panel: #18222b;
      --ink: #e8eef2;
      --muted: #a9b7c3;
      --line: #31414f;
      --accent: #35aaa2;
      --accent-dark: #69c9c2;
      --danger: #ff7883;
      --warn: #f1b861;
      --ok: #6fd098;
      --control: #121b23;
      --soft: #141e27;
      --soft-2: #16212a;
      --accent-soft: #132a2a;
      --blocked-bg: #151d25;
      --hover: #20303b;
      --line-strong: #587080;
      --tooltip-bg: #e8eef2;
      --tooltip-ink: #11181f;
      --shadow: rgba(0, 0, 0, .42);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink); }
    .shell { max-width: 1180px; margin: 0 auto; padding: 26px 18px 42px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
    .title-row { display: flex; align-items: center; gap: 10px; }
    .top-actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
    .lang-select { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    h1 { margin: 0; font-size: 26px; line-height: 1.1; letter-spacing: 0; }
    .subtitle { margin-top: 6px; color: var(--muted); font-size: 14px; }
    .subtitle button { height: auto; min-height: 0; border: 0; background: transparent; padding: 0; color: var(--accent-dark); font-weight: 700; vertical-align: baseline; }
    .subtitle button:hover { border: 0; text-decoration: underline; }
    .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: space-between; margin-top: 14px; }
    .toolbar-side { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .toolbar-stack { display: grid; gap: 6px; justify-items: end; }
    .toolbar-updated { color: var(--muted); font-size: 12px; min-height: 16px; }
    button, a.button-link { height: 38px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 12px; font: inherit; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }
    button:hover, a.button-link:hover { border-color: var(--line-strong); }
    button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
    button.primary:hover { background: var(--accent-dark); }
    button.danger { color: var(--danger); }
    button.icon, a.button-link.icon { width: 34px; height: 34px; padding: 0; display: inline-grid; place-items: center; }
    button.icon.large { width: 42px; height: 38px; font-size: 18px; }
    button.header-stat { width: 34px; height: 32px; border-radius: 7px; color: var(--accent-dark); background: var(--accent-soft); border-color: var(--line); font-size: 15px; }
    button.header-stat:hover { background: var(--hover); border-color: var(--line-strong); }
    button.mini { width: 22px; height: 22px; padding: 0; display: inline-grid; place-items: center; border: 0; border-radius: 5px; background: transparent; color: var(--muted); font-size: 13px; line-height: 1; }
    button.mini:hover { background: var(--hover); color: var(--accent-dark); border: 0; }
    button.qr-mini { width: auto; min-width: 28px; height: 22px; padding: 0 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--soft-2); color: var(--ink); font-size: 11px; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; }
    button.qr-mini:hover { background: var(--hover); border-color: var(--line-strong); color: var(--accent-dark); }
    select { height: 38px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 10px; font: inherit; }
    .statusbar { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .metric.filter { cursor: pointer; transition: .16s ease; }
    .metric.filter:hover { border-color: #9fb5bf; transform: translateY(-1px); }
    .metric.active { border-color: #45a39d; box-shadow: 0 0 0 2px rgba(20, 125, 120, .14); background: var(--accent-soft); }
    .metric b { display: block; font-size: 24px; line-height: 1.1; }
    .metric span { display: block; color: var(--muted); margin-top: 6px; font-size: 13px; }
    .table-wrap { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: middle; font-size: 14px; }
    th { background: var(--soft); color: var(--muted); font-weight: 600; }
    th.sortable { cursor: pointer; user-select: none; }
    th.sortable:hover { color: var(--accent-dark); }
    th.sortable::after { content: "↕"; margin-left: 6px; color: #9aa7b1; font-size: 11px; }
    th.sortable.sort-asc::after { content: "↑"; color: var(--accent); }
    th.sortable.sort-desc::after { content: "↓"; color: var(--accent); }
    tr:last-child td { border-bottom: 0; }
    tr.blocked { color: var(--muted); background: var(--blocked-bg); }
    .name-row { display: flex; align-items: center; gap: 7px; min-width: 0; }
    .name { border: 0; background: transparent; height: auto; padding: 0; color: var(--ink); font-weight: 700; overflow-wrap: anywhere; text-align: left; min-width: 0; }
    .name:hover { color: var(--accent-dark); border: 0; text-decoration: underline; }
    .comment { color: var(--muted); overflow-wrap: anywhere; max-width: 260px; line-height: 1.35; }
    .pill { display: inline-flex; align-items: center; height: 24px; border-radius: 999px; padding: 0 9px; font-size: 12px; border: 1px solid var(--line); background: var(--control); white-space: nowrap; }
    .pill small { display: block; font-size: 11px; line-height: 1.15; opacity: .78; }
    .pill.ok { color: var(--ok); border-color: var(--line); background: var(--accent-soft); }
    .pill.off { height: auto; min-height: 30px; align-items: flex-start; flex-direction: column; justify-content: center; gap: 1px; color: var(--muted); background: var(--soft); white-space: normal; }
    .stat-cell { color: var(--muted); font-size: 13px; }
    td.stat-td { padding-top: 2px; padding-bottom: 2px; }
    .stat-button { height: auto; min-height: 24px; border: 0; border-radius: 5px; background: transparent; padding: 2px 4px; color: var(--ink); font-size: 13px; line-height: 1.25; text-align: left; }
    .stat-button:hover { background: var(--hover); border: 0; color: var(--accent-dark); }
    .stat-button small { display: block; margin-top: 2px; color: var(--muted); font-size: 12px; white-space: nowrap; }
    .date-cell { color: var(--ink); font-size: 13px; line-height: 1.35; }
    .date-cell small { display: block; color: var(--muted); margin-top: 2px; }
    .date-help { position: relative; display: inline-flex; align-items: center; min-height: 22px; border-bottom: 1px dotted #9aa7b1; cursor: help; }
    .date-help .tip { position: absolute; left: 0; bottom: calc(100% + 8px); min-width: 220px; max-width: 280px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 7px; background: var(--tooltip-bg); color: var(--tooltip-ink); font-size: 12px; line-height: 1.35; box-shadow: 0 10px 28px rgba(15, 30, 42, .22); opacity: 0; transform: translateY(4px); pointer-events: none; transition: .14s ease; z-index: 10; }
    .date-help .tip::after { content: ""; position: absolute; left: 16px; top: 100%; border: 6px solid transparent; border-top-color: var(--tooltip-bg); }
    .date-help:hover .tip { opacity: 1; transform: translateY(0); }
    .status-cell { display: flex; align-items: center; gap: 7px; }
    .empty { padding: 38px 18px; text-align: center; color: var(--muted); }
    dialog { width: min(620px, calc(100vw - 26px)); border: 1px solid var(--line); border-radius: 8px; padding: 0; box-shadow: 0 24px 80px var(--shadow); background: var(--panel); color: var(--ink); }
    dialog::backdrop { background: rgba(20, 31, 42, .46); }
    .modal-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--line); }
    .modal-head h2 { margin: 0; font-size: 18px; letter-spacing: 0; }
    .modal-body { padding: 18px; }
    .modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--line); background: var(--soft); }
    label { display: block; color: var(--muted); font-size: 13px; margin: 0 0 6px; }
    input, textarea { width: 100%; border: 1px solid var(--line); border-radius: 7px; padding: 10px 11px; font: inherit; color: var(--ink); background: var(--control); }
    textarea { min-height: 76px; resize: vertical; }
    .grid { display: grid; grid-template-columns: 1fr 140px; gap: 14px; }
    .field { margin-bottom: 14px; }
    .checkline { display: flex; gap: 9px; align-items: center; }
    .checkline input { width: auto; }
    .secret-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
    .link-box { display: grid; gap: 12px; justify-items: center; }
    .stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
    .stats-controls { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
    .stats-control-side { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .stat-card { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: var(--soft-2); }
    .stat-card b { display: block; font-size: 18px; line-height: 1.2; }
    .stat-card span { display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }
    .metric-list { max-height: 320px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    .metric-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 9px 10px; border-bottom: 1px solid var(--line); font-size: 13px; }
    .metric-row:last-child { border-bottom: 0; }
    .metric-row code { color: var(--muted); overflow-wrap: anywhere; }
    .stats-updated { color: var(--muted); font-size: 12px; margin: -4px 0 12px; }
    .config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .config-item { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: var(--soft-2); min-width: 0; }
    .config-item span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 4px; }
    .config-item b, .config-item code { display: block; color: var(--ink); font-size: 14px; overflow-wrap: anywhere; }
    .qr { width: 220px; height: 220px; image-rendering: crisp-edges; border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
    .copy-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; width: 100%; }
    .toast { position: fixed; right: 18px; bottom: 18px; background: #13212c; color: #fff; padding: 11px 13px; border-radius: 7px; opacity: 0; transform: translateY(8px); transition: .18s ease; pointer-events: none; }
    .toast.show { opacity: 1; transform: translateY(0); }
    @media (max-width: 780px) {
      header { align-items: stretch; flex-direction: column; }
      .statusbar { grid-template-columns: 1fr 1fr; }
      table, thead, tbody, th, td, tr { display: block; }
      thead { display: none; }
      tr { border-bottom: 1px solid var(--line); padding: 12px; }
      td { border: 0; padding: 5px 0; }
      .status-cell { justify-content: flex-start; }
      .grid { grid-template-columns: 1fr; }
      .copy-row { grid-template-columns: 1fr; }
      .stats-grid { grid-template-columns: 1fr 1fr; }
      .config-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <div class="title-row">
          <h1 data-i18n="app.title">TeleMT Admin</h1>
          <button type="button" class="header-stat" id="telemtStatsBtn" data-i18n-title="button.globalStats" title="Общая статистика TeleMT">▥</button>
        </div>
        <div class="subtitle" id="subtitle" data-i18n="app.loading">Загрузка пользователей...</div>
      </div>
      <div class="top-actions">
        <div class="lang-select">
          <span>🌐</span>
          <select id="langSelect" title="Language">
            <option value="en">🇺🇸 EN</option>
            <option value="ru">🇷🇺 RU</option>
          </select>
        </div>
        <select id="themeSelect" data-i18n-title="theme.theme" title="Theme">
          <option value="light" data-i18n="theme.light">Light</option>
          <option value="dark" data-i18n="theme.dark">Dark</option>
        </select>
        <a class="button-link icon" id="logoutBtn" href="logout" data-i18n-title="common.logout" title="Logout" __WEB_AUTH_HIDDEN__>↪</a>
      </div>
    </header>

    <section class="statusbar">
      <div class="metric filter active" data-filter="all"><b id="mTotal">0</b><span data-i18n="filters.total">Всего пользователей</span></div>
      <div class="metric filter" data-filter="active"><b id="mActive">0</b><span data-i18n="filters.active">Активны</span></div>
      <div class="metric filter" data-filter="blocked"><b id="mBlocked">0</b><span data-i18n="filters.blocked">Заблокированы</span></div>
      <div class="metric filter" data-filter="limited"><b id="mLimited">0</b><span data-i18n="filters.limited">С лимитом IP</span></div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="sortable" data-sort="name" style="width: 19%" data-i18n="table.user">Пользователь</th>
            <th class="sortable" data-sort="comment" data-i18n="table.comment">Комментарий</th>
            <th class="sortable" data-sort="stats" style="width: 120px" data-i18n="table.stats">Статистика</th>
            <th class="sortable" data-sort="added" style="width: 155px" data-i18n="table.added">Добавлен</th>
            <th class="sortable" data-sort="limit" style="width: 110px" data-i18n="table.limit">Лимит IP</th>
            <th class="sortable" data-sort="status" style="width: 150px" data-i18n="table.status">Статус</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <div class="empty" id="empty" hidden data-i18n="table.empty">Пользователей пока нет.</div>
    </section>

    <div class="toolbar">
      <div class="toolbar-side">
        <button type="button" class="primary icon large" id="addBtn" data-i18n-title="common.add" title="Добавить">＋</button>
      </div>
      <div class="toolbar-stack">
        <div class="toolbar-side">
          <label for="refreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="refreshInterval">
            <option value="0" data-i18n="time.off">off</option>
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon large" id="refreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
        <div class="toolbar-updated" id="updatedAt"></div>
      </div>
    </div>
  </div>

  <dialog id="editDialog">
    <form method="dialog" id="editForm">
      <div class="modal-head">
        <h2 id="editTitle" data-i18n="modal.addUser">Добавить пользователя</h2>
        <button type="button" class="icon" data-close="editDialog" data-i18n-title="common.close" title="Закрыть">×</button>
      </div>
      <div class="modal-body">
        <div class="grid">
          <div class="field">
            <label for="name" data-i18n="form.name">Имя</label>
            <input id="name" name="name" autocomplete="off" required pattern="[A-Za-z0-9_-]{1,64}">
          </div>
          <div class="field">
            <label for="limit" data-i18n="form.limit">Лимит IP</label>
            <input id="limit" name="limit" type="number" min="0" max="100000" value="0">
          </div>
        </div>
        <div class="field">
          <label for="secret" data-i18n="form.secret">Secret</label>
          <div class="secret-row">
            <input id="secret" name="secret" autocomplete="off" pattern="[0-9a-fA-F]{32}">
            <button type="button" id="genSecret" data-i18n="form.generate">Сгенерировать</button>
          </div>
        </div>
        <div class="field">
          <label for="comment" data-i18n="form.comment">Комментарий</label>
          <textarea id="comment" name="comment"></textarea>
        </div>
        <label class="checkline"><input id="blocked" name="blocked" type="checkbox"> <span data-i18n="form.blocked">Заблокирован</span></label>
      </div>
      <div class="modal-foot">
        <button type="button" class="danger" id="deleteBtn" hidden data-i18n="common.delete">Удалить</button>
        <button type="button" data-close="editDialog" data-i18n="common.cancel">Отмена</button>
        <button type="submit" class="primary" data-i18n="common.save">Сохранить</button>
      </div>
    </form>
  </dialog>

  <dialog id="linkDialog">
    <div class="modal-head">
      <h2 id="linkTitle" data-i18n="modal.link">Ссылка</h2>
      <button type="button" class="icon" data-close="linkDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="link-box">
        <img class="qr" id="qr" alt="QR код">
        <div class="copy-row">
          <input id="linkText" readonly>
          <button type="button" id="copyBtn" data-i18n="common.copy">Скопировать</button>
        </div>
      </div>
    </div>
  </dialog>

  <dialog id="statsDialog">
    <div class="modal-head">
      <h2 id="statsTitle" data-i18n="modal.userStats">Статистика</h2>
      <button type="button" class="icon" data-close="statsDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="stats-controls">
        <div class="stats-updated" id="statsUpdated">Обновление...</div>
        <div class="stats-control-side">
          <label for="statsRefreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="statsRefreshInterval">
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="5000" selected data-i18n="time.5s">5s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="30000" data-i18n="time.30s">30s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon" id="statsRefreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
      </div>
      <div class="stats-grid" id="statsCards"></div>
      <div class="metric-list" id="statsMetrics"></div>
    </div>
  </dialog>

  <dialog id="telemtStatsDialog">
    <div class="modal-head">
      <h2 data-i18n="modal.globalStats">Общая статистика TeleMT</h2>
      <button type="button" class="icon" data-close="telemtStatsDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="stats-controls">
        <div class="stats-updated" id="telemtStatsUpdated">Обновление...</div>
        <div class="stats-control-side">
          <label for="telemtStatsRefreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="telemtStatsRefreshInterval">
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="5000" selected data-i18n="time.5s">5s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="30000" data-i18n="time.30s">30s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon" id="telemtStatsRefreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
      </div>
      <div class="stats-grid" id="telemtStatsCards"></div>
      <div class="metric-list" id="telemtStatsMetrics"></div>
    </div>
  </dialog>

  <dialog id="configDialog">
    <div class="modal-head">
      <h2 data-i18n="modal.telemtConfig">Настройки TeleMT</h2>
      <button type="button" class="icon" data-close="configDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="config-grid" id="configGrid"></div>
    </div>
  </dialog>

  <div class="toast" id="toast"></div>

  <script>
    const state = { users: [], domain: "", config: null, metrics: { enabled: true, available: false, url: "" }, updatedAt: "", editing: null, filter: "all", sortKey: "added", sortDir: "desc", refreshTimer: null, statsUser: null, statsTimer: null, telemtStatsTimer: null, lang: localStorage.getItem("telemtAdmin.lang") || "", theme: localStorage.getItem("telemtAdmin.theme") || "__DEFAULT_THEME__", i18n: {}, webAuthEnabled: "__WEB_AUTH_ENABLED__" === "true" };
    const $ = (id) => document.getElementById(id);

    function t(key, params = {}) {
      let text = state.i18n[key] || key;
      for (const [name, value] of Object.entries(params)) {
        text = text.replace(`{${name}}`, value);
      }
      return text;
    }

    async function loadI18n(lang) {
      const res = await fetch(`api/i18n/${encodeURIComponent(lang)}`, { credentials: "same-origin" });
      state.i18n = await res.json();
      state.lang = lang;
      localStorage.setItem("telemtAdmin.lang", lang);
      $("langSelect").value = lang;
      applyI18n();
    }

    function applyI18n() {
      document.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
      });
      document.querySelectorAll("[data-i18n-title]").forEach(el => {
        el.title = t(el.dataset.i18nTitle);
      });
      document.documentElement.lang = state.lang || "en";
      render();
    }

    function setTheme(theme) {
      const safeTheme = theme === "dark" ? "dark" : "light";
      state.theme = safeTheme;
      document.documentElement.dataset.theme = safeTheme;
      $("themeSelect").value = safeTheme;
      localStorage.setItem("telemtAdmin.theme", safeTheme);
    }

    function toast(text) {
      const el = $("toast");
      el.textContent = text;
      el.classList.add("show");
      setTimeout(() => el.classList.remove("show"), 1800);
    }

    async function request(url, options = {}) {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options
      });
      if (!res.ok) {
        let msg = t("common.error");
        try { msg = (await res.json()).detail || msg; } catch (_) {}
        throw new Error(msg);
      }
      return res.json();
    }

    function randomSecret() {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    }

    async function load() {
      const data = await request("api/users");
      state.users = data.users;
      state.domain = data.domain;
      state.config = data.config || null;
      state.metrics = data.metrics || { enabled: true, available: false, url: "" };
      state.updatedAt = data.updated_at;
      const metricsText = !state.metrics.enabled ? t("metrics.off") : (state.metrics.available ? t("metrics.on") : t("metrics.down"));
      $("subtitle").innerHTML = `${esc(t("app.domain"))}: <button type="button" id="configLink">${esc(data.domain)}</button>. ${esc(t("app.metrics"))}: ${esc(metricsText)}.`;
      $("configLink").onclick = showConfig;
      $("updatedAt").textContent = `${t("app.updated")}: ${formatFullDate(data.updated_at)}`;
      $("telemtStatsBtn").hidden = !state.metrics.enabled;
      render();
    }

    function filteredUsers() {
      if (state.filter === "active") return state.users.filter(u => !u.blocked);
      if (state.filter === "blocked") return state.users.filter(u => u.blocked);
      if (state.filter === "limited") return state.users.filter(u => u.limit > 0);
      return state.users;
    }

    function sortValue(u, key) {
      if (key === "name") return u.name.toLowerCase();
      if (key === "comment") return (u.comment || "").toLowerCase();
      if (key === "stats") return "";
      if (key === "added") return u.added_at || "";
      if (key === "limit") return Number(u.limit || 0);
      if (key === "status") return u.blocked ? 1 : 0;
      return "";
    }

    function sortedUsers(users) {
      const dir = state.sortDir === "asc" ? 1 : -1;
      return [...users].sort((a, b) => {
        const av = sortValue(a, state.sortKey);
        const bv = sortValue(b, state.sortKey);
        if (typeof av === "number" || typeof bv === "number") return (Number(av) - Number(bv)) * dir;
        return String(av).localeCompare(String(bv), "ru", { numeric: true, sensitivity: "base" }) * dir;
      });
    }

    function formatDate(value) {
      if (!value) return "N/A";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "N/A";
      return date.toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" });
    }

    function formatFullDate(value) {
      if (!value) return "N/A";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "N/A";
      return date.toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US");
    }

    function formatBytes(bytes) {
      if (!Number.isFinite(Number(bytes))) return "N/A";
      const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
      let value = Number(bytes);
      let unit = 0;
      while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit += 1;
      }
      return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
    }

    function formatNumber(value) {
      return Number(value || 0).toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US");
    }

    function formatDuration(seconds) {
      seconds = Math.max(0, Math.floor(Number(seconds || 0)));
      const d = Math.floor(seconds / 86400);
      const h = Math.floor((seconds % 86400) / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      if (d > 0) return `${d} д ${h} ч`;
      if (h > 0) return `${h} ч ${m} мин`;
      return `${m} мин`;
    }

    function statLine(stats) {
      if (!state.metrics.enabled) return "—";
      if (!stats || !stats.available) return "N/A";
      return `${formatNumber(stats.connections_current)} ${t("stats.activeShort")}<small>↑ ${formatBytes(stats.bytes_from_client)}/↓ ${formatBytes(stats.bytes_to_client)}</small>`;
    }

    function esc(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }

    function render() {
      const rows = $("rows");
      rows.innerHTML = "";
      const visible = sortedUsers(filteredUsers());
      $("empty").hidden = visible.length > 0;
      const active = state.users.filter(u => !u.blocked).length;
      const blocked = state.users.length - active;
      const limited = state.users.filter(u => u.limit > 0).length;
      $("mTotal").textContent = state.users.length;
      $("mActive").textContent = active;
      $("mBlocked").textContent = blocked;
      $("mLimited").textContent = limited;
      document.querySelectorAll(".metric.filter").forEach(el => {
        el.classList.toggle("active", el.dataset.filter === state.filter);
      });
      document.querySelectorAll("th.sortable").forEach(th => {
        th.classList.toggle("sort-asc", th.dataset.sort === state.sortKey && state.sortDir === "asc");
        th.classList.toggle("sort-desc", th.dataset.sort === state.sortKey && state.sortDir === "desc");
      });

      for (const u of visible) {
        const tr = document.createElement("tr");
        if (u.blocked) tr.className = "blocked";
        tr.innerHTML = `
          <td><div class="name-row"><button class="name" data-act="edit"></button><button class="qr-mini" title="Показать QR и ссылку" data-act="link">qr</button></div></td>
          <td><div class="comment"></div></td>
          <td class="stat-td"><button class="stat-button" data-act="stats"></button></td>
          <td><div class="date-cell"></div></td>
          <td><span class="pill"></span></td>
          <td><div class="status-cell"><button class="mini" title="${u.blocked ? t("status.enable") : t("status.disable")}" data-act="toggle">${u.blocked ? "▶" : "II"}</button><span class="pill ${u.blocked ? "off" : "ok"}">${u.blocked ? t("status.blocked") : t("status.active")}</span></div></td>`;
        tr.querySelector(".name").textContent = u.name;
        tr.querySelector(".comment").textContent = u.comment || "—";
        tr.querySelector(".stat-button").innerHTML = statLine(u.stats);
        tr.querySelector(".date-cell").innerHTML = `<span class="date-help">${esc(formatDate(u.added_at))}<span class="tip">${esc(t("date.lastChanged"))}: ${esc(formatDate(u.updated_at))}</span></span>`;
        tr.querySelector("td:nth-child(5) .pill").textContent = u.limit > 0 ? `${u.limit} IP` : t("table.noLimit");
        if (u.blocked && u.blocked_at) {
          tr.querySelector(".status-cell .pill").innerHTML = `${esc(t("status.blocked"))}<small>${esc(formatDate(u.blocked_at))}</small>`;
        }
        tr.querySelector('[data-act="link"]').onclick = () => showLink(u);
        tr.querySelector('[data-act="stats"]').disabled = !state.metrics.enabled;
        tr.querySelector('[data-act="stats"]').onclick = () => state.metrics.enabled && showStats(u);
        tr.querySelector('[data-act="edit"]').onclick = () => editUser(u);
        tr.querySelector('[data-act="toggle"]').onclick = () => toggleUser(u);
        rows.appendChild(tr);
      }
    }

    function openDialog(id) { $(id).showModal(); }
    function closeDialog(id) { $(id).close(); }

    function addUser() {
      state.editing = null;
      $("editTitle").textContent = t("modal.addUser");
      $("deleteBtn").hidden = true;
      $("name").value = "";
      $("limit").value = "0";
      $("secret").value = randomSecret();
      $("comment").value = "";
      $("blocked").checked = false;
      openDialog("editDialog");
    }

    function editUser(u) {
      state.editing = u.name;
      $("editTitle").textContent = `${t("modal.editUser")}: ${u.name}`;
      $("deleteBtn").hidden = false;
      $("name").value = u.name;
      $("limit").value = u.limit;
      $("secret").value = u.secret;
      $("comment").value = u.comment || "";
      $("blocked").checked = u.blocked;
      openDialog("editDialog");
    }

    function formPayload() {
      return {
        name: $("name").value.trim(),
        secret: $("secret").value.trim().toLowerCase(),
        limit: Number($("limit").value || 0),
        comment: $("comment").value.trim(),
        blocked: $("blocked").checked
      };
    }

    async function saveUser(ev) {
      ev.preventDefault();
      const payload = formPayload();
      const url = state.editing ? `api/users/${encodeURIComponent(state.editing)}` : "api/users";
      const method = state.editing ? "PUT" : "POST";
      await request(url, { method, body: JSON.stringify(payload) });
      closeDialog("editDialog");
      toast(t("common.saved"));
      await load();
    }

    function showLink(u) {
      $("linkTitle").textContent = `${t("modal.link")}: ${u.name}`;
      $("qr").src = u.qr;
      $("linkText").value = u.link;
      openDialog("linkDialog");
    }

    function stopStatsRefresh() {
      if (state.statsTimer) clearInterval(state.statsTimer);
      state.statsTimer = null;
      state.statsUser = null;
    }

    function restartStatsRefresh() {
      if (state.statsTimer) clearInterval(state.statsTimer);
      state.statsTimer = null;
      if (state.statsUser && $("statsDialog").open) {
        const interval = Number($("statsRefreshInterval").value || 5000);
        localStorage.setItem("telemtAdmin.userStatsInterval", String(interval));
        state.statsTimer = setInterval(() => refreshStatsModal(state.statsUser).catch(err => toast(err.message)), interval);
      }
    }

    async function refreshStatsModal(name) {
      const data = await request(`api/users/${encodeURIComponent(name)}/stats`);
      if (state.statsUser !== name || !$("statsDialog").open) return;
      const s = data.summary || {};
      $("statsUpdated").textContent = `${t("stats.updated")}: ${new Date().toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US")}`;
      const cards = [
        [formatNumber(s.connections_current), t("stats.activeConnections")],
        [formatNumber(s.connections_total), t("stats.totalConnections")],
        [formatBytes(s.bytes_from_client), t("stats.fromClient")],
        [formatBytes(s.bytes_to_client), t("stats.toClient")],
        [formatNumber(s.unique_ips_current), t("stats.ipNow")],
        [formatNumber(s.unique_ips_recent_window), t("stats.ipWindow")],
        [s.unique_ips_limit ? formatNumber(s.unique_ips_limit) : "∞", t("stats.limit")]
      ];
      $("statsCards").innerHTML = cards.map(([value, label]) => `<div class="stat-card"><b>${esc(value)}</b><span>${esc(label)}</span></div>`).join("");
      if (!data.metrics.length) {
        $("statsMetrics").innerHTML = `<div class="empty">${esc(t("stats.noMetrics"))}</div>`;
        return;
      }
      $("statsMetrics").innerHTML = data.metrics
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(item => `<div class="metric-row"><code>${esc(item.name)}</code><b>${esc(Number(item.value).toLocaleString("ru-RU"))}</b></div>`)
        .join("");
    }

    async function showStats(u) {
      stopStatsRefresh();
      state.statsUser = u.name;
      $("statsTitle").textContent = `${t("modal.userStats")}: ${u.name}`;
      $("statsUpdated").textContent = `${t("stats.updated")}...`;
      $("statsCards").innerHTML = `<div class="stat-card"><b>...</b><span>${esc(t("stats.loading"))}</span></div>`;
      $("statsMetrics").innerHTML = "";
      openDialog("statsDialog");
      await refreshStatsModal(u.name);
      restartStatsRefresh();
    }

    function stopTelemtStatsRefresh() {
      if (state.telemtStatsTimer) clearInterval(state.telemtStatsTimer);
      state.telemtStatsTimer = null;
    }

    function restartTelemtStatsRefresh() {
      if (state.telemtStatsTimer) clearInterval(state.telemtStatsTimer);
      state.telemtStatsTimer = null;
      if ($("telemtStatsDialog").open) {
        const interval = Number($("telemtStatsRefreshInterval").value || 5000);
        localStorage.setItem("telemtAdmin.globalStatsInterval", String(interval));
        state.telemtStatsTimer = setInterval(() => refreshTelemtStatsModal().catch(err => toast(err.message)), interval);
      }
    }

    async function refreshTelemtStatsModal() {
      const data = await request("api/telemt/stats");
      if (!$("telemtStatsDialog").open) return;
      const s = data.summary || {};
      $("telemtStatsUpdated").textContent = `${t("stats.updated")}: ${new Date().toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US")}`;
      const cards = [
        [formatDuration(s.uptime_seconds), t("stats.uptime")],
        [formatNumber(s.connections_total), t("stats.totalConnections")],
        [formatNumber(s.connections_bad_total), t("stats.badConnections")],
        [formatNumber(s.handshake_timeouts_total), t("stats.handshakeTimeout")],
        [formatNumber(s.user_entries), t("stats.userEntries")],
        [s.user_telemetry_enabled ? "on" : "off", t("stats.userTelemetry")],
        [`${formatNumber(s.buffer_in_use)} / ${formatNumber(s.buffer_allocated)}`, t("stats.buffers")],
        [`${formatNumber(s.upstream_connect_success)} / ${formatNumber(s.upstream_connect_fail)}`, t("stats.upstream")]
      ];
      $("telemtStatsCards").innerHTML = cards.map(([value, label]) => `<div class="stat-card"><b>${esc(value)}</b><span>${esc(label)}</span></div>`).join("");
      if (!data.metrics.length) {
        $("telemtStatsMetrics").innerHTML = `<div class="empty">${esc(t("stats.globalNoMetrics"))}</div>`;
        return;
      }
      $("telemtStatsMetrics").innerHTML = data.metrics
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(item => {
          const labels = Object.entries(item.labels || {}).map(([k, v]) => `${k}="${v}"`).join(", ");
          const name = labels ? `${item.name}{${labels}}` : item.name;
          return `<div class="metric-row"><code>${esc(name)}</code><b>${esc(Number(item.value).toLocaleString("ru-RU"))}</b></div>`;
        })
        .join("");
    }

    async function showTelemtStats() {
      stopTelemtStatsRefresh();
      $("telemtStatsUpdated").textContent = `${t("stats.updated")}...`;
      $("telemtStatsCards").innerHTML = `<div class="stat-card"><b>...</b><span>${esc(t("stats.loading"))}</span></div>`;
      $("telemtStatsMetrics").innerHTML = "";
      openDialog("telemtStatsDialog");
      await refreshTelemtStatsModal();
      restartTelemtStatsRefresh();
    }

    function configItem(label, value) {
      const display = value === "" || value === null || value === undefined ? "N/A" : value;
      return `<div class="config-item"><span>${esc(label)}</span><code>${esc(display)}</code></div>`;
    }

    async function showConfig() {
      const data = await request("api/telemt/config");
      state.config = data;
      const rows = [
        [t("config.publicEndpoint"), data.endpoint],
        [t("config.publicHost"), data.public_host],
        [t("config.publicPort"), data.public_port],
        [t("config.serverListen"), data.server?.listen],
        [t("config.metricsListen"), data.server?.metrics_listen],
        [t("config.tlsDomain"), data.censorship?.tls_domain],
        [t("config.maskHost"), data.censorship?.mask_host],
        [t("config.metricsUrl"), data.admin?.metrics_url],
        [t("config.metricsEnabled"), data.admin?.metrics_enabled ? t("common.yes") : t("common.no")],
        [t("config.autoFixMetrics"), data.admin?.auto_fix_metrics_listen ? t("common.yes") : t("common.no")],
        [t("config.users"), data.access?.users],
        [t("config.blockedUsers"), data.access?.blocked_users],
        [t("config.limitedUsers"), data.access?.limited_users]
      ];
      $("configGrid").innerHTML = rows.map(([label, value]) => configItem(label, value)).join("");
      openDialog("configDialog");
    }

    async function toggleUser(u) {
      await request(`api/users/${encodeURIComponent(u.name)}/blocked`, {
        method: "POST",
        body: JSON.stringify({ blocked: !u.blocked })
      });
      toast(u.blocked ? t("toast.enabled") : t("toast.blocked"));
      await load();
    }

    async function deleteUser(u) {
      if (!confirm(t("confirm.delete", { name: u.name }))) return;
      await request(`api/users/${encodeURIComponent(u.name)}`, { method: "DELETE" });
      closeDialog("editDialog");
      toast(t("common.deleted"));
      await load();
    }

    $("addBtn").onclick = addUser;
    $("refreshBtn").onclick = load;
    $("telemtStatsBtn").onclick = showTelemtStats;
    $("statsRefreshBtn").onclick = () => state.statsUser && refreshStatsModal(state.statsUser).catch(err => toast(err.message));
    $("telemtStatsRefreshBtn").onclick = () => refreshTelemtStatsModal().catch(err => toast(err.message));
    $("statsRefreshInterval").onchange = restartStatsRefresh;
    $("telemtStatsRefreshInterval").onchange = restartTelemtStatsRefresh;
    $("langSelect").onchange = () => loadI18n($("langSelect").value).then(load).catch(err => toast(err.message));
    $("themeSelect").onchange = () => setTheme($("themeSelect").value);
    $("refreshInterval").onchange = () => {
      if (state.refreshTimer) clearInterval(state.refreshTimer);
      const interval = Number($("refreshInterval").value);
      localStorage.setItem("telemtAdmin.tableInterval", String(interval));
      state.refreshTimer = interval ? setInterval(() => load().catch(err => toast(err.message)), interval) : null;
    };
    document.querySelectorAll(".metric.filter").forEach(el => {
      el.addEventListener("click", () => {
        state.filter = el.dataset.filter;
        render();
      });
    });
    document.querySelectorAll("th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (state.sortKey === key) {
          state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        } else {
          state.sortKey = key;
          state.sortDir = "asc";
        }
        render();
      });
    });
    $("editForm").addEventListener("submit", saveUser);
    $("genSecret").onclick = () => { $("secret").value = randomSecret(); };
    $("deleteBtn").onclick = () => state.editing && deleteUser({ name: state.editing });
    $("copyBtn").onclick = async () => {
      await navigator.clipboard.writeText($("linkText").value);
      toast(t("common.copied"));
    };
    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => closeDialog(btn.dataset.close));
    });
    document.querySelectorAll("dialog").forEach(dialog => {
      dialog.addEventListener("click", (ev) => {
        if (ev.target === dialog) dialog.close();
      });
      dialog.addEventListener("close", () => {
        if (dialog.id === "statsDialog") stopStatsRefresh();
        if (dialog.id === "telemtStatsDialog") stopTelemtStatsRefresh();
      });
    });
    function restoreUiPrefs() {
      $("refreshInterval").value = localStorage.getItem("telemtAdmin.tableInterval") || "0";
      $("statsRefreshInterval").value = localStorage.getItem("telemtAdmin.userStatsInterval") || "5000";
      $("telemtStatsRefreshInterval").value = localStorage.getItem("telemtAdmin.globalStatsInterval") || "5000";
      $("logoutBtn").hidden = !state.webAuthEnabled;
      $("refreshInterval").dispatchEvent(new Event("change"));
    }

    async function boot() {
      setTheme(state.theme);
      const preferred = state.lang || "__DEFAULT_LANG__";
      await loadI18n(preferred);
      restoreUiPrefs();
      await load();
    }

    boot().catch(err => toast(err.message));
  </script>
</body>
</html>
"""
