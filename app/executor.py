import json
import time

import httpx

from .config import MAX_RESPONSE_CHARS, now_tz
from .database import SessionLocal
from .models import ApiConfig, ApiExecutionLog


def execute_api(api_id: int, trigger: str = "scheduler") -> dict | None:
    """Jalankan satu API dan simpan hasilnya. Tidak pernah melempar exception."""
    try:
        with SessionLocal() as db:
            api = db.get(ApiConfig, api_id)
            if not api:
                return None

            log = ApiExecutionLog(
                api_id=api.id, api_name=api.name, trigger=trigger, executed_at=now_tz()
            )
            start = time.perf_counter()
            try:
                headers = json.loads(api.headers) if api.headers and api.headers.strip() else {}
                body = json.loads(api.body) if api.body and api.body.strip() else None
                kwargs = {"headers": headers}
                if body is not None:
                    kwargs["json"] = body
                with httpx.Client(timeout=api.timeout, follow_redirects=True) as client:
                    r = client.request(api.method, api.url, **kwargs)
                log.status_code = r.status_code
                log.response = r.text[:MAX_RESPONSE_CHARS]
                log.success = 200 <= r.status_code < 300
                if not log.success:
                    log.error_message = f"HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001
                log.success = False
                log.error_message = f"{type(e).__name__}: {e}"
            log.duration_ms = int((time.perf_counter() - start) * 1000)

            db.add(log)
            db.commit()
            return {
                "log_id": log.id,
                "success": log.success,
                "status_code": log.status_code,
                "duration_ms": log.duration_ms,
                "error": log.error_message,
            }
    except Exception as e:  # noqa: BLE001
        print(f"[executor] gagal menjalankan API {api_id}: {e}")
        return {"success": False, "status_code": None, "duration_ms": 0, "error": str(e)}
