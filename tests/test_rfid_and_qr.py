"""Tests for the RFID lookup, /check_rfid JSON endpoint, and /qr generator."""

import sqlite3

import kiosk_app.db as db_module


def _insert_user(app, uid: str, name: str, role: str) -> None:
    with sqlite3.connect(db_module.DATABASE_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (rfid_uid, name, role) VALUES (?, ?, ?)",
            (uid, name, role),
        )
        conn.commit()


def test_check_rfid_authorized(client, app):
    _insert_user(app, "AB12CD34", "Juan dela Cruz", "student")
    resp = client.post("/check_rfid", json={"uid": "AB12CD34"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "authorized"
    assert data["user"]["name"] == "Juan dela Cruz"
    assert data["user"]["role"] == "student"


def test_check_rfid_unauthorized(client):
    resp = client.post("/check_rfid", json={"uid": "UNKNOWN-UID"})
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "unauthorized"}


def test_check_rfid_missing_uid(client):
    resp = client.post("/check_rfid", json={})
    assert resp.status_code == 400


def test_rfid_redirect_without_uid(client):
    resp = client.get("/rfid")
    assert resp.status_code == 302
    assert "/menu" in resp.headers["Location"]


def test_rfid_unknown_uid_redirects_to_menu(client):
    resp = client.get("/rfid?uid=NOPE")
    assert resp.status_code == 302


def test_rfid_known_uid_renders_profile(client, app):
    _insert_user(app, "STAFF-1", "Maria Santos", "staff")
    resp = client.get("/rfid?uid=STAFF-1")
    assert resp.status_code == 200


def test_qr_generates_png(client):
    resp = client.get("/qr?data=hello")
    assert resp.status_code == 200
    assert resp.content_type.startswith("image/png")
    assert resp.data.startswith(b"\x89PNG")


def test_qr_rejects_missing_data(client):
    resp = client.get("/qr")
    assert resp.status_code == 400
