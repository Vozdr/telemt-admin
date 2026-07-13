from typing import Any

from fastapi import APIRouter, Depends, HTTPException


def create_api_router(ctx: Any) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/i18n")
    def api_i18n_list(_: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        return {"locales": ctx.available_locales(), "default": ctx.DEFAULT_LANG}

    @router.get("/i18n/{lang}")
    def api_i18n(lang: str, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        lang = "".join(ch for ch in lang if ch.isalnum() or ch in {"_", "-"})
        path = ctx.LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            path = ctx.LOCALES_DIR / f"{ctx.DEFAULT_LANG}.json"
        if not path.exists():
            path = ctx.LOCALES_DIR / "en.json"
        return ctx.json.loads(path.read_text(encoding="utf-8"))

    @router.get("/users")
    def api_users(_: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        try:
            text = ctx.read_config()
        except HTTPException as exc:
            return ctx.empty_users_payload(str(exc.detail))
        metrics_snapshot = ctx.read_metrics()
        users = ctx.list_users(metrics_snapshot=metrics_snapshot)
        _, _, _, metrics_available = metrics_snapshot
        config = ctx.telemt_config_info(text)
        config_writable, _ = ctx.probe_config_write()
        return {
            "users": [ctx.user_table_payload(u) for u in users],
            "domain": config["endpoint"],
            "public_host": config["public_host"],
            "public_port": config["public_port"],
            "config_writable": config_writable,
            "metrics": {"enabled": ctx.ENABLE_METRICS, "url": ctx.METRICS_URL, "available": metrics_available},
            "default_lang": ctx.DEFAULT_LANG,
            "default_theme": ctx.DEFAULT_THEME,
            "updated_at": ctx.now_local().isoformat(timespec="seconds"),
        }

    @router.get("/users/{name}")
    def api_user_detail(name: str, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        return {"user": ctx.user_detail_payload(ctx.find_user(name, include_stats=False))}

    @router.get("/users/{name}/link")
    def api_user_link(name: str, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        return ctx.user_link_payload(ctx.find_user(name, include_stats=False, include_link=True))

    @router.get("/telemt/config")
    def api_telemt_config(_: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        config_writable, _ = ctx.probe_config_write()
        try:
            result = ctx.telemt_config_info(ctx.read_config())
            result["config_writable"] = config_writable
            return result
        except HTTPException as exc:
            return {"error": str(exc.detail), "endpoint": "", "public_host": "", "public_port": 443, "config_writable": config_writable}

    @router.post("/telemt/config/settings")
    def api_update_telemt_config(data: ctx.ConfigSettingsInput, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        ctx.ensure_config_writable()
        return {"ok": True, "config": ctx.update_config_settings(data.changes)}

    @router.get("/users/{name}/stats")
    def api_user_stats(name: str, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        user = ctx.find_user(name, include_stats=False)
        if not ctx.ENABLE_METRICS:
            return {"user": user.name, "metrics": []}
        _, raw, _, available = ctx.read_metrics()
        if not available:
            return {"user": user.name, "metrics": []}
        rows = [item for item in raw if item["labels"].get("user") == name]
        return {"user": user.name, "metrics": rows}

    @router.get("/telemt/stats")
    def api_telemt_stats(_: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        if not ctx.ENABLE_METRICS:
            return {"metrics": []}
        _, _, raw, available = ctx.read_metrics()
        if not available:
            return {"metrics": []}
        return {"metrics": raw}

    @router.post("/users/add")
    def api_add_user(data: ctx.UserInput, _: None = Depends(ctx.require_auth)) -> dict[str, bool]:
        ctx.ensure_config_writable()
        if not data.secret:
            data.secret = ctx.generated_secret()
        ctx.upsert_user(data)
        return {"ok": True}

    @router.put("/users/{name}")
    def api_update_user(name: str, data: ctx.UserInput, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        ctx.ensure_config_writable()
        ctx.upsert_user(data, old_name=name)
        return {"ok": True}

    @router.post("/users/{name}/secret")
    def api_rotate_secret(name: str, data: ctx.SecretInput, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        ctx.ensure_config_writable()
        user = ctx.find_user(name, include_stats=False)
        new_secret = ctx.validate_secret(data.secret or ctx.generated_secret())
        ctx.upsert_user(ctx.UserInput(name=user.name, secret=new_secret, limit=user.limit, comment=user.comment, blocked=user.blocked), old_name=name)
        return {"ok": True}

    @router.post("/users/{name}/blocked")
    def api_toggle_user(name: str, data: ctx.ToggleInput, _: None = Depends(ctx.require_auth)) -> dict[str, Any]:
        ctx.ensure_config_writable()
        user = ctx.find_user(name, include_stats=False)
        ctx.upsert_user(ctx.UserInput(name=user.name, secret=user.secret, limit=user.limit, comment=user.comment, blocked=data.blocked), old_name=name)
        return {"ok": True}

    @router.delete("/users/{name}")
    def api_delete_user(name: str, _: None = Depends(ctx.require_auth)) -> dict[str, bool]:
        ctx.ensure_config_writable()
        ctx.validate_name(name)
        text = ctx.read_config()
        lines = text.splitlines()
        if name not in ctx.parse_assignments(lines, "access.users"):
            raise HTTPException(404, "Пользователь не найден.")
        ctx.remove_key(lines, "access.user_max_unique_ips", name)
        ctx.remove_user_with_meta(lines, name)
        ctx.write_config("\n".join(lines).rstrip() + "\n")
        return {"ok": True}

    return router
