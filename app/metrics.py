from __future__ import annotations

import re
import urllib.request
from typing import Any

from settings import ENABLE_METRICS, METRICS_URL


def parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', raw):
        labels[part[0]] = bytes(part[1], "utf-8").decode("unicode_escape")
    return labels


def read_metrics() -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    if not ENABLE_METRICS:
        return {}, [], [], False
    try:
        with urllib.request.urlopen(METRICS_URL, timeout=3) as response:
            text = response.read().decode("utf-8", "replace")
    except Exception:
        return {}, [], [], False

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
    return per_user, raw_user, raw_global, bool(raw_user or raw_global)


def user_table_stats(metrics: dict[str, float]) -> dict[str, Any]:
    return {
        "connections_current": int(metrics.get("telemt_user_connections_current", 0)),
        "bytes_from_client": int(metrics.get("telemt_user_octets_from_client", 0)),
        "bytes_to_client": int(metrics.get("telemt_user_octets_to_client", 0)),
        "unique_ips_limit": int(metrics.get("telemt_user_unique_ips_limit", 0)),
        "available": bool(metrics),
    }
