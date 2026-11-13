import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import TIMEZONE, now_tz
from .database import SessionLocal
from .executor import execute_api
from .models import ApiConfig

scheduler = BackgroundScheduler(
    timezone=TIMEZONE,
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
)

_lock = threading.Lock()
_done: set[tuple] = set()  # (api_id, tanggal, jam) yang sudah dijalankan


def _prefix(api_id: int) -> str:
    return f"api{api_id}@"


def run_scheduled(api_id: int, slot: str):
    """Dipanggil APScheduler. Slot yang sama pada hari yang sama hanya jalan sekali."""
    key = (api_id, now_tz().date().isoformat(), slot)
    with _lock:
        if key in _done:
            return
        _done.add(key)
        if len(_done) > 2000:
            _done.clear()
            _done.add(key)
    execute_api(api_id, "scheduler")


def sync_api(api_id: int):
    """Terapkan ulang jadwal satu API dari database (langsung, tanpa restart)."""
    for job in scheduler.get_jobs():
        if job.id.startswith(_prefix(api_id)):
            job.remove()
    with SessionLocal() as db:
        api = db.get(ApiConfig, api_id)
        if not api or not api.is_active:
            return
        for s in api.schedules:
            hour, minute = map(int, s.time_of_day.split(":"))
            scheduler.add_job(
                run_scheduled,
                CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                args=[api_id, s.time_of_day],
                id=f"{_prefix(api_id)}{s.time_of_day}",
                replace_existing=True,
            )


def sync_all():
    for job in scheduler.get_jobs():
        job.remove()
    with SessionLocal() as db:
        ids = [i for (i,) in db.query(ApiConfig.id).filter(ApiConfig.is_active.is_(True))]
    for i in ids:
        sync_api(i)


def start():
    if not scheduler.running:
        scheduler.start()
    sync_all()


def stop():
    if scheduler.running:
        scheduler.shutdown(wait=False)
