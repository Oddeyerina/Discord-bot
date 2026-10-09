"""Exercise dashboard authentication, configuration, and task enqueueing."""

import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import bcrypt
from fastapi.testclient import TestClient


def test_api_smoke() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "suite.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["SESSION_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
        os.environ["DISCORD_GUILD_ID"] = "123456789"
        os.environ["NEXT_PUBLIC_API_BASE_URL"] = "http://localhost:8080"
        os.environ["WEB_HOST_PORT"] = "3001"
        os.environ["WEB_ORIGIN"] = "http://localhost:3001"
        os.environ["DASHBOARD_USER"] = "admin"
        os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode()
        with closing(sqlite3.connect(database_path)) as old_database:
            old_database.execute(
                "CREATE TABLE tickets (id INTEGER PRIMARY KEY, guild_id TEXT, thread_id TEXT, "
                "panel_id INTEGER, user_id TEXT, reason_id INTEGER, status TEXT, claimed_by TEXT, "
                "created_at DATETIME, closed_at DATETIME, transcript_path TEXT)"
            )
        sys.path.insert(0, str(Path(__file__).parents[1] / "api"))
        from main import app
        from database import engine

        with TestClient(app) as client:
            preflight = client.options("/api/tickets/config", headers={
                "Origin": os.environ["WEB_ORIGIN"],
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            })
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == os.environ["WEB_ORIGIN"]
            assert client.get("/api/guild/data").status_code == 401
            assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
            assert client.post("/api/auth/login", json={"username": "admin", "password": "test-password"}).status_code == 200
            assert client.get("/api/auth/me").json()["username"] == "admin"
            sync = {"guild_id": "123456789", "channels": [{"id": "987", "name": "general", "type": "text"}],
                    "roles": [{"id": "456", "name": "Helper", "position": 1}], "emojis": []}
            assert client.post("/internal/guild-sync", json=sync).status_code == 403
            assert client.post("/internal/guild-sync", json=sync, headers={"X-Internal-Secret": os.environ["SESSION_SECRET"]}).status_code == 200
            assert client.get("/api/guild/data").json()["channels"][0]["name"] == "general"
            config = {"channel_id": "987", "embed": {"title": "Tickets"},
                      "extra_config": {"thread_name_pattern": "ticket-{username}"},
                      "reasons": [{"label": "Help", "questions": ["What happened?"]}]}
            response = client.put("/api/tickets/config", json=config)
            assert response.status_code == 200, response.text
            assert response.json()["reasons"][0]["label"] == "Help"
            with closing(sqlite3.connect(database_path)) as migrated_database:
                columns = {column[1] for column in migrated_database.execute("PRAGMA table_info(tickets)")}
                assert {"answered_at", "pinged_at"} <= columns
                migrated_database.execute(
                    "INSERT INTO tickets (guild_id, thread_id, panel_id, user_id, reason_id, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("123456789", "777", response.json()["id"], "888",
                     response.json()["reasons"][0]["id"], "open", "2026-01-01T00:00:00+00:00"),
                )
                migrated_database.commit()
            listed = client.get("/api/tickets")
            assert listed.status_code == 200, listed.text
            assert listed.json()[0]["answered_at"] is None
            assert listed.json()[0]["pinged_at"] is None
            old_reason_id = response.json()["reasons"][0]["id"]
            updated_config = {**config, "reasons": [{"id": old_reason_id, "label": "Help",
                                                       "support_role_ids": ["999"], "questions": ["What happened?"]}]}
            updated = client.put("/api/tickets/config", json=updated_config)
            assert updated.status_code == 200, updated.text
            assert updated.json()["reasons"][0]["id"] != old_reason_id
            with closing(sqlite3.connect(database_path)) as migrated_database:
                stored_roles = migrated_database.execute(
                    "SELECT support_role_ids_json FROM ticket_reasons WHERE id = ?", (old_reason_id,)
                ).fetchone()[0]
                assert stored_roles == "[]"
            response = client.post("/api/panels/tickets/publish")
            assert response.status_code == 200, response.text
            assert client.get("/api/tasks").json()[0]["status"] == "pending"
            assert client.put("/api/honeypot/config", json={"channel_id": "987", "action": "kick"}).status_code == 200
            assert client.put("/api/reaction-roles/config", json={"channel_id": "987", "embed": {},
                       "mappings": [{"emoji": "✅", "role_id": "456"}]}).status_code == 200
            assert client.put("/api/levels/config", json={"roles": [{"level": 2, "role_id": "456"}]}).status_code == 200
            assert client.put("/api/welcome/config", json={"autorole_id": "456"}).status_code == 200
            assert client.get("/api/levels/config").json()["roles"][0]["level"] == 2
            assert client.post("/api/auth/logout").status_code == 200
            assert client.get("/api/auth/me").status_code == 401
        engine.dispose()


if __name__ == "__main__":
    test_api_smoke()
    print("API smoke test passed")
