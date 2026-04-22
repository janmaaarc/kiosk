"""Tests for authenticated admin routes."""

import pytest


def test_dashboard_loads(auth_client):
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200


def test_rooms_list(auth_client):
    resp = auth_client.get("/rooms")
    assert resp.status_code == 200


def test_add_room_get(auth_client):
    resp = auth_client.get("/add_room")
    assert resp.status_code == 200


def test_add_room_post(auth_client):
    resp = auth_client.post(
        "/add_room",
        data={
            "building": "IT Building",
            "floor": "2",
            "room": "Room 201",
            "description": "Test room",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_edit_room_nonexistent(auth_client):
    resp = auth_client.get("/edit_room/999999")
    assert resp.status_code == 404



def test_delete_room_post(auth_client):
    auth_client.post(
        "/add_room",
        data={
            "building": "IT Building",
            "floor": "1",
            "room": "Room 101",
            "description": "To delete",
        },
        follow_redirects=True,
    )
    import kiosk_app.db as db_module
    with db_module.db_connection() as conn:
        room = conn.execute(
            "SELECT id FROM rooms WHERE room = ?", ("Room 101",)
        ).fetchone()
    if room:
        resp = auth_client.post(f"/delete_room/{room['id']}", follow_redirects=True)
        assert resp.status_code == 200
