
import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import (
    app,
    get_db,
    Asset,
    _scope_asset_query,
    _asset_for_principal_or_404,
)


def test_asset_query_is_scoped_to_owner_and_tenant():
    query = MagicMock()
    filtered_query = MagicMock()
    query.filter.return_value = filtered_query

    principal = {
        "user_id": "user_a",
        "tenant_id": "tenant_a",
        "role": "user",
    }

    result = _scope_asset_query(query, principal)

    assert result is filtered_query
    query.filter.assert_called_once()

    conditions = query.filter.call_args.args
    assert len(conditions) == 2
    assert "owner_user_id" in str(conditions[0])
    assert "tenant_id" in str(conditions[1])


def test_asset_query_rejects_missing_tenant():
    query = MagicMock()
    principal = {
        "user_id": "user_a",
        "role": "user",
    }

    with pytest.raises(HTTPException) as exc:
        _scope_asset_query(query, principal)

    assert exc.value.status_code == 403
    query.filter.assert_not_called()


def test_admin_asset_query_is_not_restricted():
    query = MagicMock()
    principal = {
        "user_id": "admin",
        "role": "admin",
    }

    result = _scope_asset_query(query, principal)

    assert result is query
    query.filter.assert_not_called()


def test_asset_query_filter_uses_correct_owner_and_tenant():
    query = MagicMock()
    query.filter.return_value = query

    principal = {
        "user_id": "user_a",
        "tenant_id": "tenant_a",
        "role": "user",
    }

    _scope_asset_query(query, principal)

    conditions = query.filter.call_args.args

    assert len(conditions) == 2
    assert "owner_user_id" in str(conditions[0])
    assert "tenant_id" in str(conditions[1])


def test_cross_tenant_asset_query_returns_no_other_tenant_assets():
    query = MagicMock()
    query.filter.return_value = query

    principal = {
        "user_id": "user_b",
        "tenant_id": "tenant_b",
        "role": "user",
    }

    result = _scope_asset_query(query, principal)

    assert result is query

    conditions = query.filter.call_args.args
    assert len(conditions) == 2
    assert "owner_user_id" in str(conditions[0])
    assert "tenant_id" in str(conditions[1])


def test_cross_tenant_asset_summary_returns_404(monkeypatch):
    user_b_key = "test-user-b-" + ("b" * 40)

    monkeypatch.setenv(
        "AEV_API_KEYS_JSON",
        json.dumps({
            user_b_key: {
                "user_id": "user_b",
                "tenant_id": "tenant_b",
                "role": "user",
            },
        }),
    )
    monkeypatch.setenv("AEV_DATA_SOURCE", "database")

    class FakeQuery:
        def filter(self, *conditions):
            self.conditions = conditions
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, model):
            return FakeQuery()

    fake_db = FakeDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(
            "/copilot/asset-summary/123",
            headers={"Authorization": f"Bearer {user_b_key}"},
        )

        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_asset_lookup_applies_both_tenant_filters():
    fake_query = MagicMock()
    fake_query.filter.return_value = fake_query
    fake_query.first.return_value = None

    fake_db = MagicMock()
    fake_db.query.return_value = fake_query

    principal = {
        "user_id": "user_b",
        "tenant_id": "tenant_b",
        "role": "user",
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("AEV_DATA_SOURCE", "database")

        with pytest.raises(HTTPException) as exc:
            _asset_for_principal_or_404(123, fake_db, principal)

    assert exc.value.status_code == 404
    assert fake_query.filter.call_count == 2

    conditions = [
        condition
        for call in fake_query.filter.call_args_list
        for condition in call.args
    ]

    assert len(conditions) == 3
    assert str(conditions[1].left) == "assets.owner_user_id"
    assert str(conditions[2].left) == "assets.tenant_id"
