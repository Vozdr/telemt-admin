from __future__ import annotations

import errno
import html
import json
import os
import re
import secrets
import shutil
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from fastapi import FastAPI

from api import create_api_router
from auth import *
from config_specs import CONFIG_SPECS
from docs import *
from links import *
from metrics import *
from models import *
from pages import create_pages_router
from settings import *
from views import LOGIN_PAGE, PAGE


app = FastAPI(title="TeleMT Admin")


def validate_config_text(text: str) -> None:
    if not text.strip():
        raise ValueError("TeleMT config is empty")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"TeleMT config is not valid TOML: {exc}") from exc
    server = data.get("server")
    if not isinstance(server, dict):
        raise ValueError("TeleMT config does not contain [server]")
    if "port" not in server and "listeners" not in server:
        raise ValueError("TeleMT config does not contain server port/listeners")
    if not any(isinstance(data.get(section), dict) for section in ("general", "censorship", "access")):
        raise ValueError("TeleMT config does not contain expected TeleMT sections")


def read_config() -> str:
    if not CONFIG_PATH.exists():
        raise HTTPException(500, f"Файл конфигурации не найден: {CONFIG_PATH}")
    text = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        validate_config_text(text)
    except ValueError as exc:
        raise HTTPException(500, str(exc)) from exc
    return text


def probe_config_read() -> tuple[bool, str]:
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        validate_config_text(text)
        return True, "OK"
    except Exception as exc:
        return False, str(exc)


def probe_config_write() -> tuple[bool, str]:
    if READ_ONLY:
        return False, "READ_ONLY is enabled"
    try:
        with CONFIG_PATH.open("r+", encoding="utf-8"):
            pass
        return True, "OK"
    except Exception as exc:
        return False, str(exc)


def ensure_config_writable() -> None:
    ok, detail = probe_config_write()
    if not ok:
        raise HTTPException(503, f"TeleMT config is read-only: {detail}")


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


def startup_config_lines() -> list[tuple[str, Any]]:
    lines: list[tuple[str, Any]] = [
        ("TELEMT_ADMIN_VERSION", APP_VERSION),
        ("LOG_LEVEL", LOG_LEVEL),
        ("TELEMT_CONFIG", str(CONFIG_PATH)),
        ("TELEMT_BACKUP_DIR", str(BACKUP_DIR)),
        ("TELEMT_MAX_BACKUPS", MAX_BACKUPS),
        ("READ_ONLY", READ_ONLY),
        ("ENABLE_METRICS", ENABLE_METRICS),
        ("ENABLE_WEB_AUTH", ENABLE_WEB_AUTH),
        ("ENABLE_BASIC_AUTH", ENABLE_BASIC_AUTH),
        ("DEFAULT_LANG", DEFAULT_LANG),
        ("DEFAULT_THEME", DEFAULT_THEME),
        ("LOCALES_DIR", str(LOCALES_DIR)),
        ("ENABLE_DOCS_FETCH", ENABLE_DOCS_FETCH),
        ("TELEMT_DOCS_CACHE_DIR", str(DOCS_CACHE_DIR)),
        ("TZ", os.getenv("TZ", "")),
    ]
    if ENABLE_WEB_AUTH:
        lines.extend([("WEB_ADMIN_USER", WEB_ADMIN_USER), ("WEB_ADMIN_PASS", "<hidden>" if WEB_ADMIN_PASS else "<empty>")])
    if ENABLE_BASIC_AUTH:
        lines.extend([("BASIC_ADMIN_USER", BASIC_ADMIN_USER), ("BASIC_ADMIN_PASS", "<hidden>" if BASIC_ADMIN_PASS else "<empty>")])
    if ENABLE_METRICS:
        lines.extend(
            [
                ("TELEMT_METRICS_URL", METRICS_URL),
                ("TELEMT_METRICS_LISTEN", TELEMT_METRICS_LISTEN),
                ("AUTO_FIX_METRICS_LISTEN", AUTO_FIX_METRICS_LISTEN),
            ]
        )
    if ENABLE_WEB_AUTH:
        lines.append(("SESSION_SECRET", "<hidden>" if SESSION_SECRET else "<empty>"))
    return lines


def print_startup_config() -> None:
    print(f"TeleMT Admin {APP_VERSION} starting", flush=True)
    print(GITHUB_URL, flush=True)
    for key, value in startup_config_lines():
        print(f"TELEMT_ADMIN: {key}={value}", flush=True)
    read_ok, read_detail = probe_config_read()
    print(f"read config telemt - {'OK' if read_ok else 'Error!'}", flush=True)
    if not read_ok:
        print(f"read config telemt error: {read_detail}", flush=True)
        print("write to config telemt - skipped (config is not readable)", flush=True)
        print("telemt admin started in limited diagnostic mode", flush=True)
        return
    write_ok, write_detail = probe_config_write()
    if READ_ONLY:
        print("write to config telemt - skipped (READ_ONLY=True)", flush=True)
    else:
        print(f"write to config telemt - {'OK' if write_ok else 'Error!'}", flush=True)
    if not write_ok:
        if not READ_ONLY:
            print(f"write to config telemt error: {write_detail}", flush=True)
        print("telemt admin working in read only mode", flush=True)
    if ENABLE_METRICS:
        _, _, _, metrics_available = read_metrics()
        print(f"check metrics available - {'OK' if metrics_available else 'Error!'}", flush=True)




@app.on_event("startup")
def startup_checks() -> None:
    print_startup_config()
    load_config_params_docs()
    try:
        ensure_metrics_listen()
    except Exception as exc:
        print(f"WARNING: failed to auto-fix TeleMT metrics listen: {exc}", flush=True)
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


def configured_timezone() -> timezone | None:
    raw = os.getenv("TZ", "").strip()
    if not raw:
        return None
    if raw.upper() == "UTC":
        return timezone.utc
    match = re.fullmatch(r"UTC?([+-]\d{1,2})(?::?(\d{2}))?", raw, flags=re.IGNORECASE)
    if not match:
        match = re.fullmatch(r"([+-]\d{1,2})(?::?(\d{2}))?", raw)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2) or "0")
    if abs(hours) > 23 or minutes > 59:
        return None
    sign = 1 if hours >= 0 else -1
    return timezone(timedelta(hours=hours, minutes=sign * minutes), raw)


def now_local() -> datetime:
    tz = configured_timezone()
    if tz is not None:
        return datetime.now(tz)
    return datetime.now().astimezone()


def parse_toml_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return bytes(raw[1:-1], "utf-8").decode("unicode_escape")
    if raw in {"true", "false"}:
        return raw == "true"
    if raw.startswith("[") and raw.endswith("]"):
        items = []
        for item in raw[1:-1].split(","):
            item = item.strip()
            if item:
                items.append(parse_toml_scalar(item))
        return items
    try:
        return int(raw)
    except ValueError:
        return raw


def parse_section_settings(lines: list[str], section: str) -> dict[str, Any]:
    start, end = section_bounds(lines, section)
    result: dict[str, Any] = {}
    if start is None or end is None:
        return result
    for line in lines[start + 1 : end]:
        m = ASSIGN_ANY_RE.match(line)
        if m:
            result[m.group("key")] = parse_toml_scalar(m.group("value"))
    return result


def parse_top_level_settings(lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in lines:
        if SECTION_RE.match(line):
            break
        m = ASSIGN_ANY_RE.match(line)
        if m:
            result[m.group("key")] = parse_toml_scalar(m.group("value"))
    return result


def config_sections(text: str) -> dict[str, dict[str, Any]]:
    lines = text.splitlines()
    sections: dict[str, dict[str, Any]] = {"": parse_top_level_settings(lines)}
    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1)
            sections.setdefault(section, parse_section_settings(lines, section))
    return sections


def stringify_config_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


SENSITIVE_CONFIG_SECTIONS = {
    "access.users",
    "access.user_max_tcp_conns",
    "access.user_expirations",
    "access.user_data_quota",
    "access.user_max_unique_ips",
    "access.user_source_deny",
    "access.user_rate_limits",
    "access.cidr_rate_limits",
}


def sensitive_config_key(key: str) -> bool:
    return bool(re.search(r"(secret|password|token|key|auth_header)", key, re.IGNORECASE))


def default_defined(value: Any) -> bool:
    return value not in {"", None, "—", "-"}


def doc_meta_for(item: ConfigSpec) -> dict[str, dict[str, Any]]:
    return {lang: DOC_META.get(lang, {}).get(item.id, {}) for lang in ("en", "ru")}


def setting_descriptions(full_id: str) -> dict[str, str]:
    return {
        "en": str(DOC_META.get("en", {}).get(full_id, {}).get("description") or ""),
        "ru": str(DOC_META.get("ru", {}).get(full_id, {}).get("description") or ""),
    }


def telemt_settings_catalog(text: str) -> list[dict[str, Any]]:
    sections = config_sections(text)
    known = {(item.section, item.key) for item in CONFIG_SPECS}
    known_ids = {item.id for item in CONFIG_SPECS}
    rows: list[dict[str, Any]] = []
    for item in CONFIG_SPECS:
        docs = doc_meta_for(item)
        doc_en = docs.get("en", {})
        section_values = sections.get(item.section, {})
        configured = item.key in section_values
        value = section_values.get(item.key)
        default_value = doc_en.get("default", item.default)
        kind = doc_en.get("type", item.kind)
        has_default = bool(doc_en.get("default_defined", default_defined(default_value)))
        rows.append(
            {
                "id": item.id,
                "section": item.section or "top-level",
                "key": item.key,
                "type": stringify_config_value(kind),
                "default": stringify_config_value(default_value),
                "default_defined": has_default,
                "value": "<hidden>" if configured and sensitive_config_key(item.key) else stringify_config_value(value) if configured else "",
                "configured": configured,
                "hot_reload": bool(doc_en.get("hot_reload", item.hot_reload)),
                "editable": item.editable,
                "choices": list(item.choices),
                "description": {
                    "en": str(docs.get("en", {}).get("description") or ""),
                    "ru": str(docs.get("ru", {}).get("description") or ""),
                },
                "docs_anchor": item.key,
                "known": True,
            }
        )
    for full_id, doc in DOC_META.get("en", {}).items():
        if full_id in known_ids:
            continue
        section = str(doc.get("section") or "top-level")
        section_key = "" if section == "top-level" else section
        if section_key in SENSITIVE_CONFIG_SECTIONS:
            continue
        key = str(doc.get("key") or "")
        if not key or sensitive_config_key(key):
            continue
        if section_key in sections and key in sections[section_key]:
            continue
        default_value = str(doc.get("default") or "")
        rows.append(
            {
                "id": full_id,
                "section": section,
                "key": key,
                "type": str(doc.get("type") or "unknown"),
                "default": default_value,
                "default_defined": bool(doc.get("default_defined")),
                "value": "",
                "configured": False,
                "hot_reload": bool(doc.get("hot_reload")),
                "editable": False,
                "choices": [],
                "description": setting_descriptions(full_id),
                "docs_anchor": key,
                "known": True,
            }
        )
    for section, values in sections.items():
        if section in SENSITIVE_CONFIG_SECTIONS:
            continue
        for key, value in values.items():
            if (section, key) in known:
                continue
            if sensitive_config_key(key):
                value = "<hidden>"
            rows.append(
                {
                    "id": f"{section}.{key}" if section else key,
                    "section": section or "top-level",
                    "key": key,
                    "type": "unknown",
                    "default": "",
                    "default_defined": False,
                    "value": stringify_config_value(value),
                    "configured": True,
                    "hot_reload": False,
                    "editable": False,
                    "choices": [],
                    "description": setting_descriptions(f"{section}.{key}" if section else key),
                    "docs_anchor": key,
                    "known": False,
                }
            )
    return rows


def normalize_config_section(section: str) -> str:
    section = (section or "").strip()
    return "" if section in {"", "top-level"} else section


def config_change_id(section: str, key: str) -> str:
    section = normalize_config_section(section)
    return f"{section}.{key}" if section else key


def validate_config_setting_target(text: str, section: str, key: str) -> None:
    section = normalize_config_section(section)
    if section in SENSITIVE_CONFIG_SECTIONS:
        raise HTTPException(403, "This config section is managed separately.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise HTTPException(400, "Invalid config key.")
    if section and not re.fullmatch(r"[A-Za-z0-9_.-]+", section):
        raise HTTPException(400, "Invalid config section.")
    allowed = {item["id"] for item in telemt_settings_catalog(text)}
    if config_change_id(section, key) not in allowed:
        raise HTTPException(400, "Unknown config key.")


def toml_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def parse_toml_inline(value: str) -> Any:
    try:
        return tomllib.loads(f"v = {value}")["v"]
    except Exception as exc:
        raise HTTPException(400, f"Invalid TOML value: {exc}") from exc


def render_toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(render_toml_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return toml_string(value)


def normalize_array_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    raw = "" if value is None else str(value).strip()
    if not raw:
        return []
    if raw.startswith("["):
        parsed = parse_toml_inline(raw)
        if not isinstance(parsed, list):
            raise HTTPException(400, "Value must be an array.")
        return parsed
    parts = [part.strip() for part in raw.split(",")] if "," in raw else [raw]
    result: list[Any] = []
    for part in parts:
        if not part:
            continue
        try:
            result.append(parse_toml_inline(part))
        except HTTPException:
            result.append(part.strip("\"'"))
    return result


def infer_config_input_kind(type_name: str, value: Any) -> str:
    kind = (type_name or "").lower()
    if any(token in kind for token in ("bool", "boolean")):
        return "boolean"
    if any(token in kind for token in ("array", "list", "vec", "[]")):
        return "array"
    if any(token in kind for token in ("float", "double", "f32", "f64")):
        return "float"
    if any(token in kind for token in ("int", "uint", "usize", "u16", "u32", "u64", "i16", "i32", "i64")):
        return "integer"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, list):
        return "array"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "string"


def render_config_value(type_name: str, value: Any) -> str:
    kind = infer_config_input_kind(type_name, value)
    if kind == "boolean":
        if isinstance(value, bool):
            return "true" if value else "false"
        raw = str(value).strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return "true"
        if raw in {"0", "false", "no", "off"}:
            return "false"
        raise HTTPException(400, "Boolean value expected.")
    if kind == "integer":
        try:
            return str(int(str(value).strip()))
        except Exception as exc:
            raise HTTPException(400, "Integer value expected.") from exc
    if kind == "float":
        try:
            return str(float(str(value).strip()))
        except Exception as exc:
            raise HTTPException(400, "Number value expected.") from exc
    if kind == "array":
        return render_toml_scalar(normalize_array_value(value))
    return toml_string(value)


def set_config_value(lines: list[str], section: str, key: str, rendered_value: str) -> None:
    section = normalize_config_section(section)
    new_line = f"{key} = {rendered_value}"
    if not section:
        first_section = next((idx for idx, line in enumerate(lines) if SECTION_RE.match(line)), len(lines))
        for idx in range(first_section):
            m = ASSIGN_ANY_RE.match(lines[idx])
            if m and m.group("key") == key:
                lines[idx] = new_line
                return
        lines.insert(first_section, new_line)
        return

    start, end = ensure_section(lines, section)
    for idx in range(start + 1, end):
        m = ASSIGN_ANY_RE.match(lines[idx])
        if m and m.group("key") == key:
            lines[idx] = new_line
            return
    lines.insert(end, new_line)


def delete_config_value(lines: list[str], section: str, key: str) -> None:
    section = normalize_config_section(section)
    if not section:
        end = next((idx for idx, line in enumerate(lines) if SECTION_RE.match(line)), len(lines))
        for idx in range(end):
            m = ASSIGN_ANY_RE.match(lines[idx])
            if m and m.group("key") == key:
                lines.pop(idx)
                return
        return
    start, end = section_bounds(lines, section)
    if start is None or end is None:
        return
    for idx in range(start + 1, end):
        m = ASSIGN_ANY_RE.match(lines[idx])
        if m and m.group("key") == key:
            lines.pop(idx)
            return


def update_config_settings(changes: list[ConfigSettingChange]) -> dict[str, Any]:
    if not changes:
        return telemt_config_info(read_config())
    text = read_config()
    lines = text.splitlines()
    for change in changes:
        section = normalize_config_section(change.section)
        key = change.key.strip()
        validate_config_setting_target(text, section, key)
        action = change.action.strip().lower()
        if action == "delete":
            delete_config_value(lines, section, key)
        elif action == "set":
            set_config_value(lines, section, key, render_config_value(change.type, change.value))
        else:
            raise HTTPException(400, "Invalid config action.")
    new_text = "\n".join(lines).rstrip() + "\n"
    try:
        validate_config_text(new_text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    write_config(new_text)
    return telemt_config_info(new_text)


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
        or ""
    )


def telemt_public_port(text: str) -> int:
    raw = get_top_level_setting(text, "public_port") or get_any_setting(text, "public_port", "443")
    try:
        return int(raw)
    except ValueError:
        return 443


def telemt_endpoint(host: str, port: int) -> str:
    if not host:
        return ""
    return f"{host}:{port}"


def telemt_config_info(text: str) -> dict[str, Any]:
    host = telemt_public_host(text)
    port = telemt_public_port(text)
    lines = text.splitlines()
    users = parse_assignments(lines, "access.users")
    limits = parse_assignments(lines, "access.user_max_unique_ips")
    blocked = sum(1 for item in users.values() if item.get("blocked"))
    general = parse_section_settings(lines, "general")
    modes = parse_section_settings(lines, "general.modes")
    server = parse_section_settings(lines, "server")
    server_api = parse_section_settings(lines, "server.api")
    censorship = parse_section_settings(lines, "censorship")
    return {
        "public_host": host,
        "public_port": port,
        "endpoint": telemt_endpoint(host, port),
        "server": {
            "listen": server.get("listen", ""),
            "metrics_listen": server.get("metrics_listen", ""),
        },
        "general": {
            "prefer_ipv6": general.get("prefer_ipv6", ""),
            "fast_mode": general.get("fast_mode", ""),
            "use_middle_proxy": general.get("use_middle_proxy", ""),
        },
        "modes": [name for name, enabled in modes.items() if enabled is True],
        "server_api": server_api,
        "censorship": {
            key: value
            for key, value in censorship.items()
            if not re.search(r"(secret|password|token|key)", key, re.IGNORECASE)
        },
        "access": {
            "users": len(users),
            "blocked_users": blocked,
            "limited_users": len(limits),
        },
        "settings": telemt_settings_catalog(text),
        "admin": {
            "metrics_enabled": ENABLE_METRICS,
            "metrics_url": METRICS_URL,
            "auto_fix_metrics_listen": AUTO_FIX_METRICS_LISTEN,
        },
        "docs": DOCS_PUBLIC_URLS,
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
    now = now_local().isoformat(timespec="seconds")
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


def list_users(include_stats: bool = True, include_link: bool = False, metrics_snapshot: tuple[dict[str, dict[str, float]], dict[str, float], list[dict[str, Any]], bool] | None = None) -> list[UserRecord]:
    text = read_config()
    host = telemt_public_host(text)
    port = telemt_public_port(text)
    tls_domain = get_setting(text, "censorship", "tls_domain", host)
    lines = text.splitlines()
    users = parse_assignments(lines, "access.users")
    limits = parse_assignments(lines, "access.user_max_unique_ips")
    metrics: dict[str, dict[str, float]] = {}
    metrics_available = False
    if include_stats:
        metrics, _, _, metrics_available = metrics_snapshot if metrics_snapshot is not None else read_metrics()
    result: list[UserRecord] = []
    for name in sorted(users):
        u = users[name]
        limit_item = limits.get(name)
        blocked = bool(u["blocked"] or (limit_item and limit_item["blocked"]))
        limit = int(limit_item["value"]) if limit_item and str(limit_item["value"]).isdigit() else 0
        comment = u["comment"]
        secret = validate_secret(str(u["value"]))
        link = make_link(secret, host, port, tls_domain) if include_link and host else ""
        stats = user_table_stats(metrics.get(name, {})) if metrics_available else user_table_stats({})
        qr = make_qr_data_uri(link) if include_link and link else ""
        result.append(UserRecord(name, secret, limit, comment, blocked, u["added_at"], u["updated_at"], u["blocked_at"], stats, link, qr))
    return result


def user_table_payload(user: UserRecord) -> dict[str, Any]:
    return {
        "name": user.name,
        "limit": user.limit,
        "comment": user.comment,
        "blocked": user.blocked,
        "added_at": user.added_at,
        "updated_at": user.updated_at,
        "blocked_at": user.blocked_at,
        "stats": user.stats,
    }


def user_detail_payload(user: UserRecord) -> dict[str, Any]:
    return {
        "name": user.name,
        "secret": user.secret,
        "limit": user.limit,
        "comment": user.comment,
        "blocked": user.blocked,
        "added_at": user.added_at,
        "updated_at": user.updated_at,
        "blocked_at": user.blocked_at,
    }


def user_link_payload(user: UserRecord) -> dict[str, Any]:
    return {
        "name": user.name,
        "link": user.link,
        "qr": user.qr,
    }


def empty_users_payload(config_read_error: str) -> dict[str, Any]:
    config_writable, _ = probe_config_write()
    return {
        "users": [],
        "domain": "",
        "public_host": "",
        "public_port": 443,
        "config": None,
        "config_read_error": config_read_error,
        "config_writable": config_writable,
        "metrics": {"enabled": ENABLE_METRICS, "url": METRICS_URL, "available": False},
        "default_lang": DEFAULT_LANG,
        "default_theme": DEFAULT_THEME,
        "updated_at": now_local().isoformat(timespec="seconds"),
    }


def find_user(name: str, include_stats: bool = True, include_link: bool = False) -> UserRecord:
    validate_name(name)
    for user in list_users(include_stats=include_stats, include_link=include_link):
        if user.name == name:
            return user
    raise HTTPException(404, "Пользователь не найден.")


def available_locales() -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if LOCALES_DIR.exists():
        for path in sorted(LOCALES_DIR.glob("*.json")):
            code = re.sub(r"[^a-zA-Z0-9_-]", "", path.stem)
            if not code:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            result.append(
                {
                    "code": code,
                    "name": str(data.get("language.name") or code),
                    "native_name": str(data.get("language.nativeName") or data.get("language.name") or code),
                }
            )
    if not result:
        result.append({"code": "en", "name": "English", "native_name": "English"})
    return result


def render_login_page(error: bool = False) -> str:
    error_html = '<div class="error" data-i18n="login.invalid">Invalid username or password</div>' if error else ""
    return (
        LOGIN_PAGE
        .replace("__DEFAULT_LANG__", DEFAULT_LANG)
        .replace("__DEFAULT_THEME__", DEFAULT_THEME)
        .replace("{error}", error_html)
    )


def render_index_page() -> str:
    page = PAGE
    metrics_ui_enabled = False
    read_only_ui = READ_ONLY or not probe_config_write()[0]
    if ENABLE_METRICS:
        try:
            _, _, _, metrics_ui_enabled = read_metrics()
        except Exception:
            metrics_ui_enabled = False
    if not metrics_ui_enabled:
        start = page.find('  <dialog id="statsDialog">')
        end = page.find('  <dialog id="configDialog">')
        if start != -1 and end != -1 and start < end:
            page = page[:start] + page[end:]
    return (
        page
        .replace("__APP_VERSION__", DISPLAY_VERSION)
        .replace("__DEFAULT_LANG__", DEFAULT_LANG)
        .replace("__DEFAULT_THEME__", DEFAULT_THEME)
        .replace("__WEB_AUTH_ENABLED__", "true" if ENABLE_WEB_AUTH else "false")
        .replace("__WEB_AUTH_HIDDEN__", "" if ENABLE_WEB_AUTH else "hidden")
        .replace("__METRICS_ENABLED__", "true" if ENABLE_METRICS else "false")
        .replace(
            "__USER_TOGGLE_BUTTON__",
            "" if read_only_ui else '<button class="mini" title="${u.blocked ? t("status.enable") : t("status.disable")}" data-act="toggle">${u.blocked ? "▶" : "II"}</button>',
        )
        .replace(
            "__USER_TOGGLE_BINDING__",
            "" if read_only_ui else """const toggleBtn = tr.querySelector('[data-act="toggle"]');
        if (toggleBtn) {
          toggleBtn.hidden = !state.configWritable;
          toggleBtn.style.display = state.configWritable ? "" : "none";
          toggleBtn.disabled = !state.configWritable;
          if (state.configWritable) toggleBtn.onclick = () => toggleUser(u, toggleBtn);
        }""",
        )
        .replace(
            "__USER_GEN_SECRET_BUTTON__",
            "" if read_only_ui else '<button type="button" id="genSecret" data-i18n="form.generate">Сгенерировать</button>',
        )
        .replace(
            "__USER_DELETE_BUTTON__",
            "" if read_only_ui else '<button type="button" class="danger" id="deleteBtn" hidden data-i18n="common.delete">Удалить</button>',
        )
        .replace(
            "__USER_SAVE_BUTTON__",
            "" if read_only_ui else '<button type="submit" class="primary" id="saveBtn" data-i18n="common.save">Сохранить</button>',
        )
        .replace(
            "__CONFIG_RESET_BUTTON__",
            "" if read_only_ui else '<button type="button" id="configResetBtn" data-i18n="common.cancel">Cancel</button>',
        )
        .replace(
            "__METRICS_BUTTON__",
            '<button type="button" class="qr-mini header-stat" id="telemtStatsBtn" data-i18n="button.globalStatsShort" data-i18n-title="button.globalStats" title="Общая статистика TeleMT">stat</button>'
            if metrics_ui_enabled
            else "",
        )
    )


app.include_router(create_pages_router(sys.modules[__name__]))
app.include_router(create_api_router(sys.modules[__name__]))

