"""Tests for public (unauthenticated) kiosk routes."""

import pytest


@pytest.mark.parametrize("path", [
    "/",
    "/menu",
    "/faculty",
    "/profile",
    "/about",
    "/announcements",
    "/events",
    "/office-selection",
    "/campus_map",
])
def test_public_pages_return_200(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"status": "ok"}


def test_healthz_content_type(client):
    resp = client.get("/healthz")
    assert resp.content_type.startswith("application/json")


def test_menu_contains_nav_links(client):
    resp = client.get("/menu")
    html = resp.data.decode()
    assert "/faculty" in html
    assert "/campus" in html
    assert "/announcements" in html


def test_search_get(client):
    resp = client.get("/search")
    assert resp.status_code == 200


def test_search_post_no_result(client):
    resp = client.post("/search", data={"room": "NONEXISTENT999"})
    assert resp.status_code == 200


def test_api_rooms_empty_query(client):
    resp = client.get("/api/rooms?q=")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_api_rooms_with_query(client):
    resp = client.get("/api/rooms?q=lab")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_404_returns_html(client):
    resp = client.get("/does-not-exist-xyz")
    assert resp.status_code == 404
    assert b"html" in resp.data.lower()


def test_kiosk_scripts_injected(client):
    resp = client.get("/menu")
    html = resp.data.decode()
    assert "kiosk-scale.js" in html
    assert "kiosk-idle.js" in html


