from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasicCredentials


def create_pages_router(ctx: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        read_ok, read_detail = ctx.probe_config_read()
        if not read_ok:
            raise HTTPException(503, f"TeleMT config read failed: {read_detail}")
        write_ok, _ = ctx.probe_config_write()
        return {"status": "ok", "config": "rw" if write_ok else "ro"}

    @router.get("/login", response_class=HTMLResponse)
    def login_page(
        credentials: HTTPBasicCredentials | None = Depends(ctx.security),
        telemt_admin_lang: str | None = Cookie(default=None),
    ):
        if ctx.ENABLE_BASIC_AUTH and not ctx.valid_basic(credentials):
            raise HTTPException(
                status_code=401,
                detail="Basic authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )
        if not ctx.ENABLE_WEB_AUTH:
            return RedirectResponse("./")
        return ctx.render_login_page(lang=telemt_admin_lang)

    @router.post("/login")
    def login_submit(
        username: str = Form(...),
        password: str = Form(...),
        credentials: HTTPBasicCredentials | None = Depends(ctx.security),
        telemt_admin_lang: str | None = Cookie(default=None),
    ):
        if ctx.ENABLE_BASIC_AUTH and not ctx.valid_basic(credentials):
            raise HTTPException(
                status_code=401,
                detail="Basic authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )
        if not ctx.ENABLE_WEB_AUTH:
            return RedirectResponse("./", status_code=303)
        if ctx.secrets.compare_digest(username, ctx.WEB_ADMIN_USER) and ctx.secrets.compare_digest(password, ctx.WEB_ADMIN_PASS):
            response = RedirectResponse("./", status_code=303)
            response.set_cookie("telemt_admin_session", ctx.make_session_token(username), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
            return response
        return HTMLResponse(ctx.render_login_page(error=True, lang=telemt_admin_lang), status_code=401)

    @router.get("/logout")
    def logout():
        response = RedirectResponse("login", status_code=303)
        response.delete_cookie("telemt_admin_session")
        return response

    @router.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        credentials: HTTPBasicCredentials | None = Depends(ctx.security),
        telemt_admin_session: str | None = Cookie(default=None),
        telemt_admin_lang: str | None = Cookie(default=None),
    ):
        if not ctx.ENABLE_BASIC_AUTH and not ctx.ENABLE_WEB_AUTH:
            return ctx.render_index_page(lang=telemt_admin_lang)
        if ctx.ENABLE_BASIC_AUTH and not ctx.valid_basic(credentials):
            raise HTTPException(
                status_code=401,
                detail="Basic authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )
        if ctx.ENABLE_WEB_AUTH and ctx.valid_session_token(telemt_admin_session):
            return ctx.render_index_page(lang=telemt_admin_lang)
        if ctx.ENABLE_WEB_AUTH:
            return RedirectResponse("login", status_code=303)
        return ctx.render_index_page(lang=telemt_admin_lang)

    return router
