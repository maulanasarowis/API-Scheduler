import os
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:password@localhost:5432/api_scheduler",
)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
TZ = ZoneInfo(TIMEZONE)
MAX_RESPONSE_CHARS = 20000


def now_tz() -> datetime:
    return datetime.now(TZ)


def day_range(d: date | None = None) -> tuple[datetime, datetime]:
    d = d or now_tz().date()
    start = datetime.combine(d, time.min, tzinfo=TZ)
    return start, start + timedelta(days=1)
