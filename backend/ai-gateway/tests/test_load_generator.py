
import pytest

from app.load_generator import run_load_generator


def test_zero_requests_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=0, max_workers=1)


def test_zero_workers_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=1, max_workers=0)


def test_negative_requests_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=-1, max_workers=1)


def test_negative_workers_raise_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        run_load_generator(total_requests=1, max_workers=-1)
