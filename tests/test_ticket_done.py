"""Check that Done records the answer and notifies support only once."""

import asyncio
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace


class FakeThread:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, content: str, **_: object) -> None:
        self.messages.append(content)


class FakeResponse:
    def __init__(self) -> None:
        self.disabled = False
        self.replies: list[str] = []

    async def edit_message(self, *, view: object) -> None:
        self.disabled = view.children[0].disabled

    async def send_message(self, content: str, *, ephemeral: bool) -> None:
        self.replies.append(content)

    def is_done(self) -> bool:
        return self.disabled


async def test_done() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "ticket.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["DISCORD_TOKEN"] = "test-token"
        os.environ["DISCORD_GUILD_ID"] = "123456789"
        os.environ["SESSION_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
        sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))
        import cogs.tickets as tickets

        with closing(sqlite3.connect(database_path)) as db:
            db.execute("CREATE TABLE tickets (id INTEGER PRIMARY KEY, guild_id TEXT, thread_id TEXT, "
                       "user_id TEXT, reason_id INTEGER, status TEXT, answered_at DATETIME, pinged_at DATETIME)")
            db.execute("CREATE TABLE ticket_reasons (id INTEGER PRIMARY KEY, support_role_ids_json TEXT)")
            db.execute("INSERT INTO tickets VALUES (1, '123456789', '777', '888', 2, 'open', NULL, NULL)")
            db.execute("INSERT INTO ticket_reasons VALUES (2, '[\"456\"]')")
            db.commit()

        original_thread = tickets.discord.Thread
        tickets.discord.Thread = FakeThread
        try:
            thread = FakeThread()
            role = SimpleNamespace(id=456, mention="<@&456>")
            guild = SimpleNamespace(get_role=lambda role_id: role if role_id == 456 else None)
            other = SimpleNamespace(channel=thread, channel_id=777, user=SimpleNamespace(id=999),
                                    guild=guild, response=FakeResponse())
            await tickets.Tickets(None).done(other)
            assert other.response.replies == ["Only the ticket opener can mark the answers as done."]
            assert thread.messages == []
            response = FakeResponse()
            interaction = SimpleNamespace(channel=thread, channel_id=777, user=SimpleNamespace(id=888),
                                          guild=guild, response=response)
            await tickets.Tickets(None).done(interaction)
            assert response.disabled
            assert thread.messages == ["<@&456> Ticket answers are ready for review."]
            with closing(sqlite3.connect(database_path)) as db:
                answered_at, pinged_at = db.execute(
                    "SELECT answered_at, pinged_at FROM tickets WHERE id = 1"
                ).fetchone()
                assert answered_at is not None and pinged_at is not None

            duplicate = SimpleNamespace(channel=thread, channel_id=777, user=SimpleNamespace(id=888),
                                        guild=guild, response=FakeResponse())
            await tickets.Tickets(None).done(duplicate)
            assert len(thread.messages) == 1
            assert duplicate.response.replies == ["Support has already been notified."]
        finally:
            tickets.discord.Thread = original_thread


if __name__ == "__main__":
    asyncio.run(test_done())
    print("Ticket Done idempotency passed")
