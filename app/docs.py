from __future__ import annotations

import re
import urllib.request
from typing import Any

from settings import DOCS_CACHE_DIR, DOCS_FETCH_TIMEOUT, DOCS_URLS, DOC_META, ENABLE_DOCS_FETCH


def clean_markdown_text(value: str) -> str:
    value = re.sub(r"```.*?```", "", value, flags=re.S)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = value.replace("✔", "yes").replace("✘", "no")
    return " ".join(value.split()).strip()


def normalize_config_params_markdown(text: str) -> str:
    text = re.sub(r"```toml\s*(.*?)\s*```", lambda m: "\n```toml\n" + m.group(1).strip() + "\n```\n", text, flags=re.S)
    text = re.sub(r"(?<!^)\s+(#{1,2}\s+)", r"\n\1", text)
    text = re.sub(r"\s+(-\s+\*\*(?:Constraints / validation|Ограничения / валидация|Description|Описание|Example|Пример|Runtime behavior|Поведение во время выполнения)\*\*:)", r"\n\1", text)
    text = re.sub(r"\s+(\|\s*(?:Key|Ключ)\s*\|)", r"\n\1", text)
    text = re.sub(r"\s+(\|\s*---)", r"\n\1", text)
    text = re.sub(r"\s+(\|\s*\[?`)", r"\n\1", text)
    return text


def docs_section_name(raw: str) -> str | None:
    raw = raw.strip()
    if raw.lower() in {"top-level keys", "top level keys"}:
        return ""
    m = re.fullmatch(r"\[([^\]]+)\]", raw)
    if m:
        return m.group(1)
    return None


def doc_key_id(section: str, key: str) -> str:
    return f"{section}.{key}" if section else key


def parse_doc_table_key(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"`([^`]+)`", raw)
    if m:
        return m.group(1).strip()
    raw = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
    return raw.strip()


def parse_config_params_doc(text: str) -> dict[str, dict[str, Any]]:
    text = normalize_config_params_markdown(text)
    rows: dict[str, dict[str, Any]] = {}
    section = ""
    for line in text.splitlines():
        heading = re.match(r"^#\s+(.+?)\s*$", line)
        if heading:
            parsed = docs_section_name(heading.group(1))
            if parsed is not None:
                section = parsed
            continue
        if not line.startswith("|") or "---" in line or " Key " in line or " Ключ " in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        key = parse_doc_table_key(cells[0])
        if not key or key.lower() in {"key", "ключ"}:
            continue
        full_id = doc_key_id(section, key)
        rows.setdefault(full_id, {})
        rows[full_id].update(
            {
                "id": full_id,
                "section": section or "top-level",
                "key": key,
                "type": clean_markdown_text(cells[1]),
                "default": clean_markdown_text(cells[2]),
                "default_defined": clean_markdown_text(cells[2]) not in {"", "—", "-"},
                "hot_reload": "✔" in cells[3],
                "known": True,
            }
        )
    current_section = ""
    headings = list(re.finditer(r"^(#{1,2})\s+(.+?)\s*$", text, flags=re.M))
    for idx, match in enumerate(headings):
        level = len(match.group(1))
        title = match.group(1).strip()
        title = match.group(2).strip()
        start = match.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        block = text[start:end]
        if level == 1:
            parsed = docs_section_name(title)
            if parsed is not None:
                current_section = parsed
            continue
        full_id = doc_key_id(current_section, title)
        desc = re.search(
            r"-\s+\*\*(?:Description|Описание)\*\*:\s*(.*?)(?=\n-\s+\*\*(?:Constraints / validation|Ограничения / валидация|Description|Описание|Example|Пример|Runtime behavior|Поведение во время выполнения)\*\*:|\n##\s+|\n#\s+|\Z)",
            block,
            flags=re.S,
        )
        if not desc:
            continue
        rows.setdefault(full_id, {"id": full_id, "section": "top-level", "key": title, "known": True})
        rows[full_id]["section"] = current_section or "top-level"
        rows[full_id]["key"] = title
        rows[full_id]["description"] = clean_markdown_text(desc.group(1))
    return rows


def load_config_params_docs() -> None:
    if not ENABLE_DOCS_FETCH:
        print("telemt config docs fetch - skipped", flush=True)
        return
    DOCS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for lang, url in DOCS_URLS.items():
        path = DOCS_CACHE_DIR / f"CONFIG_PARAMS.{lang}.md"
        try:
            with urllib.request.urlopen(url, timeout=DOCS_FETCH_TIMEOUT) as response:
                path.write_bytes(response.read())
            text = path.read_text(encoding="utf-8")
            DOC_META[lang] = parse_config_params_doc(text)
            print(f"telemt config docs {lang} - OK ({len(DOC_META[lang])} keys)", flush=True)
        except Exception as exc:
            print(f"telemt config docs {lang} - Error! {exc}", flush=True)
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8")
                    DOC_META[lang] = parse_config_params_doc(text)
                    print(f"telemt config docs {lang} - loaded cached copy ({len(DOC_META[lang])} keys)", flush=True)
                except Exception as cache_exc:
                    print(f"telemt config docs {lang} cache - Error! {cache_exc}", flush=True)

