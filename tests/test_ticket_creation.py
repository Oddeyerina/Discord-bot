"""Check private-thread membership and ticket message order without Discord I/O."""

import asyncio
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import discord


class FakeThread:
    id = 777
    mention = "<#777>"

    def __init__(self) -> None:
        self.members: list[int] = []
        self.messages: list[dict] = []

    async def add_user(self, member: object) -> None:
        self.members.append(member.id)

    async def send(self, content: str | None = None, **kwargs: object) -> None:
        self.messages.append({"content": content, **kwargs})


class FakeTextChannel:
    def __init__(self) -> None:
        self.thread = FakeThread()
        self.thread_type: discord.ChannelType | None = None
        self.created = 0

    async def create_thread(self, **kwargs: object) -> FakeThread:
        self.created += 1
        self.thread_type = kwargs["type"]
        return self.thread


async def test_creation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "ticket.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["DISCORD_TOKEN"] = "test-token"
        os.environ["DISCORD_GUILD_ID"] = "123456789"
        os.environ["SESSION_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
        sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))
        import cogs.tickets as tickets

        with closing(sqlite3.connect(database_path)) as db:
            db.execute("CREATE TABLE panels (id INTEGER PRIMARY KEY, guild_id TEXT, channel_id TEXT, extra_config_json TEXT)")
            db.execute("CREATE TABLE ticket_reasons (id INTEGER PRIMARY KEY, panel_id INTEGER, active INTEGER, "
                       "label TEXT, support_role_ids_json TEXT, questions_json TEXT)")
            db.execute("CREATE TABLE tickets (id INTEGER PRIMARY KEY, guild_id TEXT, thread_id TEXT, "
                       "panel_id INTEGER, user_id TEXT, reason_id INTEGER, priority_id INTEGER, status TEXT, created_at DATETIME)")
            db.execute("CREATE TABLE ticket_priorities (id INTEGER PRIMARY KEY, guild_id TEXT, active INTEGER, "
                       "position INTEGER, label TEXT, emoji TEXT, color TEXT)")
            db.execute("CREATE TABLE ticket_first_replies (ticket_id INTEGER PRIMARY KEY, guild_id TEXT, message_id TEXT)")
            db.execute("CREATE TABLE ticket_autoresponses (id INTEGER PRIMARY KEY, guild_id TEXT, panel_id INTEGER, "
                       "trigger_keyword TEXT, response_text TEXT, position INTEGER, enabled INTEGER)")
            db.execute("INSERT INTO panels VALUES (1, '123456789', '999', '{}')")
            db.execute("INSERT INTO ticket_reasons VALUES (2, 1, 1, 'Help', '[\"456\", \"457\"]', '[\"First?\", \"Second?\"]')")
            db.commit()

        original_channel = tickets.discord.TextChannel
        tickets.discord.TextChannel = FakeTextChannel
        try:
            channel = FakeTextChannel()
            opener = SimpleNamespace(id=888, name="opener", mention="<@888>")
            support = SimpleNamespace(id=555, bot=False)
            second_support = SimpleNamespace(id=556, bot=False)
            roles = {456: SimpleNamespace(id=456, members=[support]),
                     457: SimpleNamespace(id=457, members=[support, second_support])}
            chunked: list[bool] = []

            async def chunk(*, cache: bool) -> None:
                chunked.append(cache)

            guild = SimpleNamespace(get_channel=lambda _: channel, get_role=roles.get, chunk=chunk)

            class Response:
                picker: object | None = None

                async def defer(self, *, ephemeral: bool) -> None:
                    assert ephemeral

                async def send_message(self, _: str, *, view: object, ephemeral: bool) -> None:
                    assert ephemeral
                    self.picker = view

            class Followup:
                messages: list[str] = []

                async def send(self, _: str, *, ephemeral: bool) -> None:
                    assert ephemeral
                    self.messages.append(_)

            followup = Followup()
            interaction = SimpleNamespace(data={"values": ["2"]}, guild=guild, user=opener,
                                          response=Response(), followup=followup)
            await tickets.Tickets(None).create_ticket(interaction, "ticket:reason:1")
            assert channel.thread_type == discord.ChannelType.private_thread
            assert channel.thread.members == [888, 555, 556]
            messages = channel.thread.messages
            assert messages[0]["embed"].title == "Ticket"
            assert [message["content"] for message in messages[1:3]] == ["First?", "Second?"]
            assert messages[3]["view"].children[0].custom_id == "ticket:done"
            assert chunked == [True]
            await tickets.Tickets(None).create_ticket(interaction, "ticket:reason:1")
            assert channel.created == 1
            assert "already have an open ticket" in followup.messages[-1]
            with closing(sqlite3.connect(database_path)) as db:
                db.execute("INSERT INTO ticket_priorities VALUES (3, '123456789', 1, 0, 'High', NULL, '#ff0000')")
                db.commit()
            second = SimpleNamespace(data={"values": ["2"]}, guild=guild,
                                     user=SimpleNamespace(id=889, name="second", mention="<@889>"),
                                     response=Response(), followup=Followup())
            await tickets.Tickets(None).create_ticket(second, "ticket:reason:1")
            assert second.response.picker.children[0].custom_id == "ticket:priority-create:1:2"
            assert channel.created == 1
            second.data = {"values": ["3"]}
            await tickets.Tickets(None).create_ticket(second, "ticket:priority-create:1:2")
            assert channel.created == 2
            assert channel.thread.messages[-4]["embed"].fields[0].value == "High"
            with closing(sqlite3.connect(database_path)) as db:
                assert db.execute("SELECT priority_id FROM tickets WHERE user_id = '889'").fetchone()[0] == 3
                db.execute("INSERT INTO ticket_autoresponses VALUES (1, '123456789', 1, 'billing', 'Check your receipt.', 0, 1)")
                db.commit()
            first_answer = SimpleNamespace(id=900, guild=SimpleNamespace(id=123456789),
                                           channel=channel.thread, author=SimpleNamespace(id=888, bot=False),
                                           content="I need billing help")
            cog = tickets.Tickets(None)
            await cog.on_message(first_answer)
            assert channel.thread.messages[-1]["content"] == "Check your receipt."
            second_answer = SimpleNamespace(id=901, guild=first_answer.guild, channel=channel.thread,
                                            author=first_answer.author, content="billing again")
            count = len(channel.thread.messages)
            await cog.on_message(second_answer)
            assert len(channel.thread.messages) == count
        finally:
            tickets.discord.TextChannel = original_channel


if __name__ == "__main__":
    asyncio.run(test_creation())
    print("Private ticket creation passed")
