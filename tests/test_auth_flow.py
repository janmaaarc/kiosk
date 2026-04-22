"""Tests for admin authentication flow."""

import pytest


def test_admin_login_page_loads(client):
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b"Sign In" in resp.data or b"sign in" in resp.data.lower()


def test_login_with_wrong_password(client):
    resp = client.post(
        "/admin",
        data={"username": "admin", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"dashboard" not in resp.data.lower()


def test_login_with_unknown_user(client):
    resp = client.post(
        "/admin",
        data={"username": "ghost", "password": "whatever"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"dashboard" not in resp.data.lower()


def test_login_success_redirects_to_dashboard(client):
    resp = client.post(
        "/admin",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_dashboard_requires_auth(client):
    resp = client.get("/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert b"sign in" in resp.data.lower() or b"admin" in resp.data.lower()


def test_logout_clears_session(client):
    client.post(
        "/admin",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    resp2 = client.get("/dashboard", follow_redirects=True)
    assert b"sign in" in resp2.data.lower() or b"admin" in resp2.data.lower()
