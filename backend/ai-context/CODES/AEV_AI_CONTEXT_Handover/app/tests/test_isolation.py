import json
from fastapi.testclient import TestClient
from app.main import app

USER1_KEY = "test-isolation-user1-" + ("1" * 40)
USER2_KEY = "test-isolation-user2-" + ("2" * 40)

client = TestClient(app)


def test_user_memory_isolation(monkeypatch):
    # The integration test writes to the configured database; run only against a dedicated test DB.
    monkeypatch.setenv("AEV_API_KEYS_JSON", json.dumps({
        USER1_KEY: {"user_id": "isolation_user_1", "role": "user"},
        USER2_KEY: {"user_id": "isolation_user_2", "role": "user"},
    }))
    user1_headers = {"Authorization": f"Bearer {USER1_KEY}"}
    user2_headers = {"Authorization": f"Bearer {USER2_KEY}"}

    create_response = client.post(
        "/memory",
        headers=user1_headers,
        json={
            "user_id": "isolation_user_1",
            "conversation": "Private memory belonging to User 1",
            "memory_type": "preference",
        },
    )
    assert create_response.status_code == 200
    memory_id = create_response.json()["id"]

    update_response = client.put(
        f"/memory/{memory_id}",
        headers=user2_headers,
        json={
            "user_id": "isolation_user_2",
            "conversation": "Trying to modify another user's memory",
        },
    )
    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Memory not found for this user"

    delete_response = client.request(
        "DELETE",
        f"/memory/{memory_id}",
        headers=user2_headers,
        json={"user_id": "isolation_user_2"},
    )
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Memory not found for this user"

    owner_response = client.get(
        "/memory/user/isolation_user_1",
        headers=user1_headers,
    )
    assert owner_response.status_code == 200
    assert any(memory["id"] == memory_id for memory in owner_response.json())

    # A different principal cannot even list the owner's memory collection.
    cross_read = client.get("/memory/user/isolation_user_1", headers=user2_headers)
    assert cross_read.status_code == 403
