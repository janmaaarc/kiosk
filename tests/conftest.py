"""Shared pytest fixtures for all test modules."""

import os
import sqlite3
import tempfile

import pytest
from flask_bcrypt import Bcrypt

import kiosk_app.db as db_module
from kiosk_app import create_app


@pytest.fixture()
def app(monkeypatch, tmp_path):
    """Application fixture backed by a fresh in-memory-style temp database."""
    db_file = tmp_path / "test.db"

    monkeypatch.setattr(db_module, "DATABASE_PATH", str(db_file))

    _bootstrap_db(str(db_file))

    application = create_app()
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret",
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """Client pre-logged in as admin."""
    client.post(
        "/admin",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    return client


def _bootstrap_db(path: str) -> None:
    bcrypt = Bcrypt()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        );
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT, floor TEXT, room TEXT, description TEXT,
            pos_left INTEGER DEFAULT 0, pos_top INTEGER DEFAULT 0,
            pos_width INTEGER DEFAULT 10, pos_height INTEGER DEFAULT 10,
            office_key TEXT, room_color TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, image TEXT, desc TEXT,
            date TEXT, time TEXT, details TEXT,
            published_at TEXT DEFAULT (datetime('now')), expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, thumbnail TEXT, file TEXT,
            published_at TEXT DEFAULT (datetime('now')), expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS offices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            image TEXT, location TEXT, hours TEXT, desc TEXT,
            files TEXT DEFAULT '[]', building_url TEXT,
            published_at TEXT DEFAULT (datetime('now')), expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS building_floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT NOT NULL, floor_number INTEGER NOT NULL,
            floor_label TEXT NOT NULL, floor_image TEXT,
            UNIQUE(building, floor_number)
        );
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, department TEXT, position TEXT,
            photo TEXT, schedule_image TEXT, room TEXT, building TEXT,
            office_key TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, role TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    pw = bcrypt.generate_password_hash("admin123").decode()
    conn.execute(
        "INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)",
        ("admin", pw),
    )
    conn.commit()
    conn.close()
