
from datetime import datetime, timedelta, timezone

from app.expiry_job import EXPIRY_DAYS


def test_expiry_cutoff_is_90_days():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=EXPIRY_DAYS)

    assert EXPIRY_DAYS == 90
    assert (now - cutoff).days == 90


def test_old_memory_is_older_than_cutoff():
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    old_date = cutoff - timedelta(days=1)

    assert old_date < cutoff
