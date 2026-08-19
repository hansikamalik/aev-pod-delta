from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_user_memory_isolation():
    # Create memory for User 1
    create_response = client.post(
        "/memory",
        json={
            "user_id": "isolation_user_1",
            "conversation": "Private memory belonging to User 1",
            "memory_type": "preference"
        }
    )

    assert create_response.status_code == 200

    memory_id = create_response.json()["id"]

    # User 2 attempts to update User 1's memory
    update_response = client.put(
        f"/memory/{memory_id}",
        json={
            "user_id": "isolation_user_2",
            "conversation": "Trying to modify another user's memory"
        }
    )

    assert update_response.status_code == 404
    assert (
        update_response.json()["detail"]
        == "Memory not found for this user"
    )

    # User 2 attempts to delete User 1's memory
    delete_response = client.request(
        "DELETE",
        f"/memory/{memory_id}",
        json={
            "user_id": "isolation_user_2"
        }
    )

    assert delete_response.status_code == 404
    assert (
        delete_response.json()["detail"]
        == "Memory not found for this user"
    )

    # Verify User 1 can still see their memory
    owner_response = client.get(
        "/memory/user/isolation_user_1"
    )

    assert owner_response.status_code == 200

    owner_memories = owner_response.json()

    assert any(
        memory["id"] == memory_id
        for memory in owner_memories
    )

    print("ISOLATION TEST PASSED")