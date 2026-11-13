import json
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import scheduler
from .config import TZ, day_range
from .database import get_db
from .executor import execute_api
from .models import ApiConfig, ApiExecutionLog, ApiSchedule

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
router = APIRouter()

PAGE_SIZE = 50
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def localtime(dt, fmt="%d %b %Y %H:%M:%S"):
    return dt.astimezone(TZ).strftime(fmt) if dt else "-"


templates.env.filters["localtime"] = localtime


# ---------- Schema ----------
class ApiIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    headers: str | None = None
    body: str | None = None
    timeout: int = Field(30, ge=1, le=300)
    is_active: bool = True
    schedules: list[str] = []

    @field_validator("url")
    @classmethod
    def v_url(cls, v):
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL harus diawali http:// atau https://")
        return v

    @field_validator("headers")
    @classmethod
    def v_headers(cls, v):
        if v and v.strip():
            try:
                if not isinstance(json.loads(v), dict):
                    raise ValueError
            except ValueError:
                raise ValueError("Headers harus berupa JSON object, contoh {\"Authorization\": \"Bearer x\"}")
        return v.strip() if v and v.strip() else None

    @field_validator("body")
    @classmethod
    def v_body(cls, v):
        if v and v.strip():
            try:
                json.loads(v)
            except ValueError:
                raise ValueError("Body harus berupa JSON yang valid")
        return v.strip() if v and v.strip() else None

    @field_validator("schedules")
    @classmethod
    def v_schedules(cls, v):
        for t in v:
            if not TIME_RE.match(t):
                raise ValueError(f"Format jam tidak valid: {t} (gunakan HH:MM)")
        return sorted(set(v))


def _apply(api: ApiConfig, data: ApiIn):
    api.name = data.name.strip()
    api.url = data.url
    api.method = data.method
    api.headers = data.headers
    api.body = data.body
    api.timeout = data.timeout
    api.is_active = data.is_active
    api.schedules = [ApiSchedule(time_of_day=t) for t in data.schedules]


def _get_or_404(db: Session, api_id: int) -> ApiConfig:
    api = db.get(ApiConfig, api_id)
    if not api:
        raise HTTPException(404, "API tidak ditemukan")
    return api


# ---------- Halaman ----------
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    start, end = day_range()
    today = db.query(ApiExecutionLog).filter(
        ApiExecutionLog.executed_at >= start, ApiExecutionLog.executed_at < end
    )
    total = db.query(func.count(ApiConfig.id)).scalar()
    active = db.query(func.count(ApiConfig.id)).filter(ApiConfig.is_active.is_(True)).scalar()
    stats = {
        "total": total,
        "active": active,
        "inactive": total - active,
        "today": today.count(),
        "success": today.filter(ApiExecutionLog.success.is_(True)).count(),
        "failed": today.filter(ApiExecutionLog.success.is_(False)).count(),
    }
    recent = db.query(ApiExecutionLog).order_by(ApiExecutionLog.executed_at.desc()).limit(8).all()
    return templates.TemplateResponse(
        request, "dashboard.html", {"page": "dashboard", "stats": stats, "recent": recent}
    )


@router.get("/apis", response_class=HTMLResponse)
def api_list(request: Request, db: Session = Depends(get_db)):
    apis = db.query(ApiConfig).order_by(ApiConfig.id).all()
    rows = []
    for a in apis:
        last = (
            db.query(ApiExecutionLog)
            .filter(ApiExecutionLog.api_id == a.id)
            .order_by(ApiExecutionLog.executed_at.desc())
            .first()
        )
        payload = {
            "id": a.id, "name": a.name, "url": a.url, "method": a.method,
            "headers": a.headers or "", "body": a.body or "", "timeout": a.timeout,
            "is_active": a.is_active, "schedules": [s.time_of_day for s in a.schedules],
        }
        rows.append({"api": a, "last": last, "payload": payload})
    return templates.TemplateResponse(request, "apis.html", {"page": "apis", "rows": rows})


@router.get("/logs", response_class=HTMLResponse)
def logs_page(
    request: Request,
    date_filter: str = "",
    api_id: str = "",
    status: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    q = db.query(ApiExecutionLog)
    if date_filter:
        try:
            s, e = day_range(date.fromisoformat(date_filter))
            q = q.filter(ApiExecutionLog.executed_at >= s, ApiExecutionLog.executed_at < e)
        except ValueError:
            pass
    if api_id.isdigit():
        q = q.filter(ApiExecutionLog.api_id == int(api_id))
    if status == "success":
        q = q.filter(ApiExecutionLog.success.is_(True))
    elif status == "failed":
        q = q.filter(ApiExecutionLog.success.is_(False))

    total = q.count()
    page = max(page, 1)
    items = (
        q.order_by(ApiExecutionLog.executed_at.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    )
    qs = urlencode({"date_filter": date_filter, "api_id": api_id, "status": status})
    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "page": "logs", "items": items, "total": total, "pg": page,
            "has_next": page * PAGE_SIZE < total, "qs": qs,
            "apis": db.query(ApiConfig).order_by(ApiConfig.name).all(),
            "f": {"date": date_filter, "api_id": api_id, "status": status},
        },
    )


# ---------- JSON API ----------
@router.post("/api/configs")
def create_api(data: ApiIn, db: Session = Depends(get_db)):
    api = ApiConfig()
    _apply(api, data)
    db.add(api)
    db.commit()
    scheduler.sync_api(api.id)
    return {"id": api.id}


@router.put("/api/configs/{api_id}")
def update_api(api_id: int, data: ApiIn, db: Session = Depends(get_db)):
    api = _get_or_404(db, api_id)
    _apply(api, data)
    db.commit()
    scheduler.sync_api(api_id)
    return {"id": api_id}


@router.delete("/api/configs/{api_id}")
def delete_api(api_id: int, db: Session = Depends(get_db)):
    api = _get_or_404(db, api_id)
    db.delete(api)
    db.commit()
    scheduler.sync_api(api_id)
    return {"ok": True}


@router.post("/api/configs/{api_id}/toggle")
def toggle_api(api_id: int, db: Session = Depends(get_db)):
    api = _get_or_404(db, api_id)
    api.is_active = not api.is_active
    db.commit()
    scheduler.sync_api(api_id)
    return {"is_active": api.is_active}


@router.post("/api/configs/{api_id}/run")
def run_now(api_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, api_id)
    return execute_api(api_id, "manual")


@router.get("/api/logs/{log_id}")
def log_detail(log_id: int, db: Session = Depends(get_db)):
    log = db.get(ApiExecutionLog, log_id)
    if not log:
        raise HTTPException(404, "Log tidak ditemukan")
    return {
        "api_name": log.api_name, "executed_at": localtime(log.executed_at),
        "status_code": log.status_code, "success": log.success,
        "duration_ms": log.duration_ms, "trigger": log.trigger,
        "response": log.response or "", "error_message": log.error_message or "",
    }
