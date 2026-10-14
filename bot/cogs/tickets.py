import asyncio
import io
import logging
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from config import GUILD_ID
from db import DB_PATH, all_rows, connect, decoded, one
from utils.safe import safe_edit, safe_send

log = logging.getLogger(__name__)


def ticket_view(config: dict | None = None, claimed: bool = False,
                assigned: bool = False) -> discord.ui.View:
    config = config or {}
    styles = {"primary": discord.ButtonStyle.primary, "secondary": discord.ButtonStyle.secondary,
              "success": discord.ButtonStyle.success, "danger": discord.ButtonStyle.danger}
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label=str(config.get("claim_label", "Claim"))[:80],
                                    style=styles.get(config.get("claim_style"), discord.ButtonStyle.primary),
                                    custom_id="ticket:claim:claimed" if claimed else "ticket:claim",
                                    disabled=claimed))
    view.add_item(discord.ui.Button(label=str(config.get("close_label", "Close"))[:80],
                                    style=styles.get(config.get("close_style"), discord.ButtonStyle.danger),
                                    custom_id="ticket:close"))
    view.add_item(discord.ui.Button(label="Change priority", style=discord.ButtonStyle.secondary,
                                    custom_id="ticket:priority-open"))
    view.add_item(discord.ui.Button(label="Quick Reply", style=discord.ButtonStyle.secondary,
                                    custom_id="ticket:quick-open"))
    view.add_item(discord.ui.Button(label="Assign to me", style=discord.ButtonStyle.primary,
                                    custom_id="ticket:assign"))
    view.add_item(discord.ui.Button(label="Unassign", style=discord.ButtonStyle.secondary,
                                    custom_id="ticket:unassign", disabled=not assigned))
    view.add_item(discord.ui.Button(label="Add note", style=discord.ButtonStyle.secondary,
                                    custom_id="ticket:note-add"))
    view.add_item(discord.ui.Button(label="View notes", style=discord.ButtonStyle.secondary,
                                    custom_id="ticket:notes-view"))
    return view


def done_view(disabled: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Done", style=discord.ButtonStyle.success,
                                    custom_id="ticket:done", disabled=disabled))
    return view


def assignment_field(embed: discord.Embed, assigned_to: str | None,
                     claimed_by: str | None) -> None:
    for index in reversed(range(len(embed.fields))):
        if embed.fields[index].name in {"Assigned to", "Claimed by"}:
            embed.remove_field(index)
    if assigned_to:
        embed.add_field(name="Assigned to", value=f"<@{assigned_to}>", inline=False)
    elif claimed_by:
        embed.add_field(name="Claimed by", value=f"<@{claimed_by}>", inline=False)


class TicketNoteModal(discord.ui.Modal, title="Add ticket note"):
    content = discord.ui.TextInput(label="Note", style=discord.TextStyle.paragraph,
                                   max_length=1800, required=True)

    def __init__(self, cog: "Tickets", ticket_id: int) -> None:
        super().__init__()
        self.cog = cog
        self.ticket_id = ticket_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.save_note(interaction, self.ticket_id, str(self.content.value))


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._done_locks: dict[int, asyncio.Lock] = {}
        self._cleanup_task: asyncio.Task | None = None

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self.cleanup_loop())

    async def cog_unload(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()

    async def thread_exists(self, guild: discord.Guild, thread_id: str) -> bool:
        if guild.get_thread(int(thread_id)) is not None:
            return True
        try:
            return await guild.fetch_channel(int(thread_id)) is not None
        except discord.NotFound:
            return False
        except discord.HTTPException:
            log.exception("Could not check ticket thread %s", thread_id)
            return True

    async def clean_stale_rows(self, guild: discord.Guild, rows: list[dict]) -> list[dict]:
        active = []
        for row in rows:
            if await self.thread_exists(guild, row["thread_id"]):
                active.append(row)
                continue
            with connect() as db:
                db.execute("UPDATE tickets SET status = 'closed', closed_at = ? "
                           "WHERE id = ? AND status = 'open'",
                           (datetime.now(timezone.utc).isoformat(), row["id"]))
            log.info("Closed stale ticket %s because thread %s is gone", row["id"], row["thread_id"])
        return active

    async def cleanup_loop(self) -> None:
        while not self.bot.is_closed():
            try:
                guild = self.bot.get_guild(GUILD_ID)
                if guild is not None:
                    rows = all_rows("SELECT id, thread_id FROM tickets WHERE guild_id = ? AND status = 'open'",
                                    (str(GUILD_ID),))
                    await self.clean_stale_rows(guild, rows)
                    await self.sweep_inactive(guild)
            except Exception:
                log.exception("Stale ticket cleanup failed")
            await asyncio.sleep(3600)

    async def sweep_inactive(self, guild: discord.Guild) -> None:
        now = datetime.now(timezone.utc)
        for ticket in all_rows("SELECT * FROM tickets WHERE guild_id = ? AND status = 'open'",
                               (str(GUILD_ID),)):
            panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
            config = decoded(panel["extra_config_json"], {}) if panel else {}
            inactivity_hours = int(config.get("inactivity_hours", 72))
            warning_hours = int(config.get("inactivity_warning_hours", 24))
            if inactivity_hours <= 0:
                continue
            try:
                thread = guild.get_thread(int(ticket["thread_id"]))
                if thread is None:
                    thread = await guild.fetch_channel(int(ticket["thread_id"]))
                if not isinstance(thread, discord.Thread):
                    continue
                last = datetime.fromisoformat(ticket["created_at"])
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                async for message in thread.history(limit=100):
                    if not message.author.bot:
                        last = message.created_at
                        break
                idle_hours = (now - last).total_seconds() / 3600
                if idle_hours >= inactivity_hours:
                    await self.close_ticket(thread, ticket, "Inactivity timer")
                elif warning_hours > 0 and idle_hours >= warning_hours and not ticket["last_warned_at"]:
                    warning = await safe_send(
                        thread,
                        content=f"<@{ticket['user_id']}> This ticket will close in about "
                                f"{max(1, round(inactivity_hours - idle_hours))} hours if there is no reply.",
                        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                    )
                    if warning is not None:
                        with connect() as db:
                            db.execute("UPDATE tickets SET last_warned_at = ? WHERE id = ?",
                                       (now.isoformat(), ticket["id"]))
            except discord.NotFound:
                await self.clean_stale_rows(guild, [ticket])
            except Exception:
                log.exception("Inactivity check failed for ticket %s", ticket["id"])

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id != GUILD_ID or not interaction.data:
            return
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("ticket:open:"):
            await self.open_picker(interaction, custom_id)
        elif custom_id.startswith("ticket:reason:"):
            await self.create_ticket(interaction, custom_id)
        elif custom_id.startswith("ticket:priority-create:"):
            await self.create_ticket(interaction, custom_id)
        elif custom_id == "ticket:priority-open":
            await self.priority_picker(interaction)
        elif custom_id.startswith("ticket:priority-change:"):
            await self.change_priority(interaction, custom_id)
        elif custom_id == "ticket:quick-open":
            await self.quick_picker(interaction)
        elif custom_id.startswith("ticket:quick-send:"):
            await self.quick_send(interaction, custom_id)
        elif custom_id == "ticket:claim":
            await self.claim(interaction)
        elif custom_id == "ticket:claim:claimed":
            await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)
        elif custom_id == "ticket:done":
            await self.done(interaction)
        elif custom_id == "ticket:close":
            await self.close(interaction)
        elif custom_id == "ticket:assign":
            await self.assign(interaction)
        elif custom_id == "ticket:unassign":
            await self.unassign(interaction)
        elif custom_id == "ticket:note-add":
            await self.add_note(interaction)
        elif custom_id == "ticket:notes-view":
            await self.view_notes(interaction)

    async def open_picker(self, interaction: discord.Interaction, custom_id: str) -> None:
        panel_id = int(custom_id.rsplit(":", 1)[1])
        panel = one("SELECT id FROM panels WHERE id = ? AND guild_id = ? AND type = 'tickets' AND active = 1",
                    (panel_id, str(GUILD_ID)))
        if panel is None:
            await interaction.response.send_message("This ticket panel is no longer available.", ephemeral=True)
            return
        rows = all_rows("SELECT * FROM ticket_reasons WHERE panel_id = ? AND active = 1 ORDER BY position LIMIT 25", (panel_id,))
        if not rows:
            await interaction.response.send_message("No ticket reasons are configured.", ephemeral=True)
            return
        options = [discord.SelectOption(label=r["label"], value=str(r["id"]),
                                        description=r["description"][:100] or None,
                                        emoji=r["emoji"] or None) for r in rows]
        view = discord.ui.View(timeout=120)
        view.add_item(discord.ui.Select(placeholder="Choose a reason", options=options,
                                        custom_id=f"ticket:reason:{panel_id}"))
        await interaction.response.send_message("Choose a ticket reason:", view=view, ephemeral=True)

    async def create_ticket(self, interaction: discord.Interaction, custom_id: str) -> None:
        values = interaction.data.get("values", [])
        if not values:
            await interaction.response.send_message("Choose an option.", ephemeral=True)
            return
        priority_id: int | None = None
        if custom_id.startswith("ticket:priority-create:"):
            _, _, panel_text, reason_text = custom_id.split(":")
            panel_id, reason_id, priority_id = int(panel_text), int(reason_text), int(values[0])
            priority = one("SELECT id FROM ticket_priorities WHERE id = ? AND guild_id = ? "
                           "AND panel_id = ? AND active = 1", (priority_id, str(GUILD_ID), panel_id))
            if priority is None:
                await interaction.response.send_message("That priority is no longer available.", ephemeral=True)
                return
        else:
            panel_id, reason_id = int(custom_id.rsplit(":", 1)[1]), int(values[0])
        reason = one("SELECT * FROM ticket_reasons WHERE id = ? AND panel_id = ? AND active = 1",
                     (reason_id, panel_id))
        selected_panel = one("SELECT * FROM panels WHERE id = ? AND guild_id = ? "
                             "AND type = 'tickets' AND active = 1", (panel_id, str(GUILD_ID)))
        if reason is None or selected_panel is None or not interaction.guild:
            await interaction.response.send_message("This ticket option is no longer available.", ephemeral=True)
            return
        if priority_id is None:
            priorities = all_rows("SELECT * FROM ticket_priorities WHERE guild_id = ? AND panel_id = ? "
                                  "AND active = 1 ORDER BY position LIMIT 25", (str(GUILD_ID), panel_id))
            if priorities:
                options = [discord.SelectOption(label=p["label"], value=str(p["id"]),
                                                emoji=p["emoji"] or None) for p in priorities]
                view = discord.ui.View(timeout=120)
                view.add_item(discord.ui.Select(placeholder="Choose a priority", options=options,
                         custom_id=f"ticket:priority-create:{panel_id}:{reason_id}"))
                await interaction.response.send_message("Choose a ticket priority:", view=view, ephemeral=True)
                return
        channel = interaction.guild.get_channel(int(selected_panel["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("The ticket channel is unavailable.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        open_rows = all_rows("SELECT id, thread_id, reason_id FROM tickets WHERE guild_id = ? "
                             "AND user_id = ? AND status = 'open'",
                             (str(GUILD_ID), str(interaction.user.id)))
        active_rows = await self.clean_stale_rows(interaction.guild, open_rows)
        existing = next((row for row in active_rows if row["reason_id"] == reason["id"]), None)
        if existing:
            await interaction.followup.send(f"You already have an open ticket: <#{existing['thread_id']}>", ephemeral=True)
            return
        role_ids = dict.fromkeys(decoded(reason["support_role_ids_json"], []))
        roles = [role for role_id in role_ids if (role := interaction.guild.get_role(int(role_id))) is not None]
        if not roles:
            await interaction.followup.send("No support roles are available for this reason. Please contact an admin.", ephemeral=True)
            return
        try:
            await interaction.guild.chunk(cache=True)
        except discord.HTTPException:
            log.exception("Could not load support role members for ticket reason %s", reason["id"])
            await interaction.followup.send("Support members could not be loaded. Please try again.", ephemeral=True)
            return
        support_members = {member.id: member for role in roles for member in role.members if not member.bot}
        support_members.pop(interaction.user.id, None)
        if len(support_members) >= 999:
            await interaction.followup.send("This reason has too many support members for a private thread.", ephemeral=True)
            return
        pattern = decoded(selected_panel["extra_config_json"], {}).get("thread_name_pattern", "ticket-{username}")
        name = pattern.replace("{username}", interaction.user.name).replace("{user}", interaction.user.name)
        if reason["emoji"]:
            name = f"{reason['emoji']} {name}"
        name = name[:100]
        thread: discord.Thread | None = None
        try:
            thread = await channel.create_thread(name=name, type=discord.ChannelType.private_thread,
                                                 auto_archive_duration=1440)
            await thread.add_user(interaction.user)
            for member in support_members.values():
                await thread.add_user(member)
            embed = discord.Embed(title="Ticket", description=f"Opened by {interaction.user.mention}\nReason: {reason['label']}",
                                  timestamp=datetime.now(timezone.utc), color=0x5865F2)
            if priority_id is not None:
                selected_priority = one("SELECT label, color FROM ticket_priorities WHERE id = ?", (priority_id,))
                if selected_priority:
                    embed.add_field(name="Priority", value=selected_priority["label"])
                    try:
                        embed.color = discord.Color(int(selected_priority["color"].lstrip("#"), 16))
                    except ValueError:
                        pass
            if await safe_send(thread, embed=embed, view=ticket_view(decoded(selected_panel["extra_config_json"], {}))) is None:
                raise RuntimeError("Could not post ticket info")
            for question in decoded(reason["questions_json"], []):
                if await safe_send(thread, content=str(question)) is None:
                    raise RuntimeError("Could not post ticket question")
            if await safe_send(thread, content="When you have answered the questions, click Done to notify support.", view=done_view()) is None:
                raise RuntimeError("Could not post Done button")
        except (discord.HTTPException, RuntimeError):
            log.exception("Could not create private ticket for user %s", interaction.user.id)
            if thread is not None:
                try:
                    await thread.delete(reason="Incomplete ticket setup")
                except discord.HTTPException:
                    log.exception("Could not remove incomplete ticket thread %s", thread.id)
            await interaction.followup.send("The private ticket could not be created. Please try again.", ephemeral=True)
            return
        with connect() as db:
            db.execute("INSERT INTO tickets (guild_id, thread_id, panel_id, user_id, reason_id, priority_id, status, created_at) "
                       "VALUES (?, ?, ?, ?, ?, ?, 'open', ?)",
                       (str(GUILD_ID), str(thread.id), panel_id, str(interaction.user.id), reason["id"], priority_id,
                        datetime.now(timezone.utc).isoformat()))
        await interaction.followup.send(f"Your ticket is ready: {thread.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID or message.author.bot or not message.content:
            return
        ticket = one("SELECT id, panel_id, user_id FROM tickets WHERE guild_id = ? AND thread_id = ? AND status = 'open'",
                     (str(GUILD_ID), str(message.channel.id)))
        if ticket is None:
            return
        with connect() as db:
            db.execute("UPDATE tickets SET last_warned_at = NULL WHERE id = ?", (ticket["id"],))
        if ticket["user_id"] != str(message.author.id):
            return
        with connect() as db:
            first = db.execute("INSERT OR IGNORE INTO ticket_first_replies (ticket_id, guild_id, message_id) VALUES (?, ?, ?)",
                               (ticket["id"], str(GUILD_ID), str(message.id))).rowcount
        if not first:
            return
        replies = all_rows("SELECT * FROM ticket_autoresponses WHERE guild_id = ? AND enabled = 1 "
                           "AND (panel_id = ? OR panel_id IS NULL) ORDER BY position",
                           (str(GUILD_ID), ticket["panel_id"]))
        for reply in replies:
            if reply["trigger_keyword"].casefold() in message.content.casefold():
                try:
                    await safe_send(message.channel, content=reply["response_text"], allowed_mentions=discord.AllowedMentions.none())
                except discord.HTTPException:
                    log.exception("Could not send auto response in ticket %s", ticket["id"])

    async def priority_picker(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE guild_id = ? AND thread_id = ? AND status = 'open'",
                     (str(GUILD_ID), str(interaction.channel_id)))
        if ticket is None or not self.allowed(interaction, ticket):
            await interaction.response.send_message("Only support staff can change priority.", ephemeral=True)
            return
        priorities = all_rows("SELECT * FROM ticket_priorities WHERE guild_id = ? AND panel_id = ? "
                              "AND active = 1 ORDER BY position LIMIT 25", (str(GUILD_ID), ticket["panel_id"]))
        if not priorities:
            await interaction.response.send_message("No priorities are configured.", ephemeral=True)
            return
        view = discord.ui.View(timeout=120)
        view.add_item(discord.ui.Select(placeholder="Choose a priority",
                    options=[discord.SelectOption(label=p["label"], value=str(p["id"]),
                                                  emoji=p["emoji"] or None) for p in priorities],
                    custom_id=f"ticket:priority-change:{ticket['id']}:{interaction.message.id}"))
        await interaction.response.send_message("Choose a new priority:", view=view, ephemeral=True)

    async def change_priority(self, interaction: discord.Interaction, custom_id: str) -> None:
        _, _, ticket_text, message_text = custom_id.split(":")
        ticket = one("SELECT * FROM tickets WHERE id = ? AND guild_id = ? AND status = 'open'",
                     (int(ticket_text), str(GUILD_ID)))
        if ticket is None or ticket["thread_id"] != str(interaction.channel_id) or not self.allowed(interaction, ticket) or not interaction.data.get("values"):
            await interaction.response.send_message("This priority change is unavailable.", ephemeral=True)
            return
        priority = one("SELECT * FROM ticket_priorities WHERE id = ? AND guild_id = ? "
                       "AND panel_id = ? AND active = 1",
                       (int(interaction.data["values"][0]), str(GUILD_ID), ticket["panel_id"]))
        if priority is None or not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("Priority unavailable.", ephemeral=True)
            return
        try:
            message = await interaction.channel.fetch_message(int(message_text))
            embed = message.embeds[0]
            for index, field in enumerate(embed.fields):
                if field.name == "Priority":
                    embed.set_field_at(index, name="Priority", value=priority["label"])
                    break
            else:
                embed.add_field(name="Priority", value=priority["label"])
            embed.color = discord.Color(int(priority["color"].lstrip("#"), 16))
            if not await safe_edit(message, embed=embed):
                raise RuntimeError("Could not edit ticket priority")
        except (discord.HTTPException, RuntimeError, ValueError, IndexError):
            log.exception("Could not change priority for ticket %s", ticket["id"])
            await interaction.response.send_message("Could not update the ticket embed.", ephemeral=True)
            return
        with connect() as db:
            db.execute("UPDATE tickets SET priority_id = ? WHERE id = ?", (priority["id"], ticket["id"]))
        await interaction.response.send_message("Priority updated.", ephemeral=True)

    async def quick_picker(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE guild_id = ? AND thread_id = ? AND status = 'open'",
                     (str(GUILD_ID), str(interaction.channel_id)))
        if ticket is None or not self.allowed(interaction, ticket):
            await interaction.response.send_message("Only support staff can use quick replies.", ephemeral=True)
            return
        replies = all_rows("SELECT * FROM ticket_quickreplies WHERE guild_id = ? AND panel_id = ? "
                           "ORDER BY position LIMIT 25", (str(GUILD_ID), ticket["panel_id"]))
        if not replies:
            await interaction.response.send_message("No quick replies are configured.", ephemeral=True)
            return
        view = discord.ui.View(timeout=120)
        view.add_item(discord.ui.Select(placeholder="Choose a quick reply",
                    options=[discord.SelectOption(label=r["label"], value=str(r["id"])) for r in replies],
                    custom_id=f"ticket:quick-send:{ticket['id']}"))
        await interaction.response.send_message("Choose a reply:", view=view, ephemeral=True)

    async def quick_send(self, interaction: discord.Interaction, custom_id: str) -> None:
        ticket = one("SELECT * FROM tickets WHERE id = ? AND guild_id = ? AND status = 'open'",
                     (int(custom_id.rsplit(":", 1)[1]), str(GUILD_ID)))
        if ticket is None or ticket["thread_id"] != str(interaction.channel_id) or not self.allowed(interaction, ticket) or not interaction.data.get("values"):
            await interaction.response.send_message("Quick reply unavailable.", ephemeral=True)
            return
        reply = one("SELECT response_text FROM ticket_quickreplies WHERE id = ? AND guild_id = ? "
                    "AND panel_id = ?", (int(interaction.data["values"][0]), str(GUILD_ID), ticket["panel_id"]))
        if reply is None or not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("Quick reply unavailable.", ephemeral=True)
            return
        if await safe_send(interaction.channel, content=reply["response_text"], allowed_mentions=discord.AllowedMentions.none()) is None:
            await interaction.response.send_message("Could not send the reply.", ephemeral=True)
            return
        await interaction.response.send_message("Reply sent.", ephemeral=True)

    async def done(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND guild_id = ? AND status = 'open'",
                     (str(interaction.channel_id), str(GUILD_ID)))
        if ticket is None or not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("This ticket is no longer open.", ephemeral=True)
            return
        if str(interaction.user.id) != ticket["user_id"]:
            await interaction.response.send_message("Only the ticket opener can mark the answers as done.", ephemeral=True)
            return
        reason = one("SELECT support_role_ids_json FROM ticket_reasons WHERE id = ?", (ticket["reason_id"],))
        role_ids = decoded(reason["support_role_ids_json"], []) if reason else []
        roles = [role for role_id in role_ids if interaction.guild and
                 (role := interaction.guild.get_role(int(role_id))) is not None]
        if not roles:
            await interaction.response.send_message("No support roles are available. Please contact an admin.", ephemeral=True)
            return
        lock = self._done_locks.setdefault(ticket["id"], asyncio.Lock())
        async with lock:
            current = one("SELECT status, pinged_at FROM tickets WHERE id = ?", (ticket["id"],))
            if current is None or current["status"] != "open":
                await interaction.response.send_message("This ticket is no longer open.", ephemeral=True)
                return
            if current["pinged_at"] is not None:
                await interaction.response.send_message("Support has already been notified.", ephemeral=True)
                return
            answered_at = datetime.now(timezone.utc).isoformat()
            with connect() as db:
                db.execute("UPDATE tickets SET answered_at = COALESCE(answered_at, ?) "
                           "WHERE id = ? AND status = 'open' AND pinged_at IS NULL",
                           (answered_at, ticket["id"]))
            try:
                await interaction.response.edit_message(view=done_view(disabled=True))
                mentions = " ".join(role.mention for role in roles)
                if await safe_send(interaction.channel,
                    content=f"{mentions} Ticket answers are ready for review.",
                    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=roles),
                ) is None:
                    raise RuntimeError("Could not notify support")
            except (discord.HTTPException, RuntimeError):
                if interaction.message:
                    try:
                        await safe_edit(interaction.message, view=done_view())
                    except discord.HTTPException:
                        log.exception("Could not re-enable Done for ticket %s", ticket["id"])
                if interaction.response.is_done():
                    await interaction.followup.send("Support could not be notified. Please try Done again.", ephemeral=True)
                else:
                    await interaction.response.send_message("Support could not be notified. Please try again.", ephemeral=True)
                log.exception("Could not notify support for ticket %s", ticket["id"])
                return
            with connect() as db:
                db.execute("UPDATE tickets SET pinged_at = ? WHERE id = ? AND pinged_at IS NULL",
                           (datetime.now(timezone.utc).isoformat(), ticket["id"]))

    def allowed(self, interaction: discord.Interaction, ticket: dict) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if interaction.user.guild_permissions.manage_threads:
            return True
        reason = one("SELECT support_role_ids_json FROM ticket_reasons WHERE id = ?", (ticket["reason_id"],))
        allowed_ids = set(decoded(reason["support_role_ids_json"], [])) if reason else set()
        return any(str(role.id) in allowed_ids for role in interaction.user.roles)

    def support_allowed(self, interaction: discord.Interaction, ticket: dict) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        reason = one("SELECT support_role_ids_json FROM ticket_reasons WHERE id = ?",
                     (ticket["reason_id"],))
        ids = set(decoded(reason["support_role_ids_json"], [])) if reason else set()
        return any(str(role.id) in ids for role in interaction.user.roles)

    async def assign(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND guild_id = ? AND status = 'open'",
                     (str(interaction.channel_id), str(GUILD_ID)))
        if ticket is None or not self.support_allowed(interaction, ticket):
            await interaction.response.send_message("Only ticket support staff can assign tickets.",
                                                    ephemeral=True)
            return
        with connect() as db:
            db.execute("UPDATE tickets SET assigned_to = ? WHERE id = ?",
                       (str(interaction.user.id), ticket["id"]))
        embed = interaction.message.embeds[0]
        assignment_field(embed, str(interaction.user.id), ticket["claimed_by"])
        panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        await interaction.response.edit_message(
            embed=embed, view=ticket_view(decoded(panel["extra_config_json"], {}) if panel else {},
                                          claimed=bool(ticket["claimed_by"]), assigned=True))

    async def unassign(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND guild_id = ? AND status = 'open'",
                     (str(interaction.channel_id), str(GUILD_ID)))
        if ticket is None or not self.support_allowed(interaction, ticket):
            await interaction.response.send_message("Only ticket support staff can unassign tickets.",
                                                    ephemeral=True)
            return
        if not ticket["assigned_to"]:
            await interaction.response.send_message("This ticket is not assigned.", ephemeral=True)
            return
        with connect() as db:
            db.execute("UPDATE tickets SET assigned_to = NULL WHERE id = ?", (ticket["id"],))
        embed = interaction.message.embeds[0]
        assignment_field(embed, None, ticket["claimed_by"])
        panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        await interaction.response.edit_message(
            embed=embed, view=ticket_view(decoded(panel["extra_config_json"], {}) if panel else {},
                                          claimed=bool(ticket["claimed_by"]), assigned=False))

    async def add_note(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND guild_id = ? AND status = 'open'",
                     (str(interaction.channel_id), str(GUILD_ID)))
        if ticket is None or not self.support_allowed(interaction, ticket):
            await interaction.response.send_message("Only ticket support staff can add notes.",
                                                    ephemeral=True)
            return
        await interaction.response.send_modal(TicketNoteModal(self, ticket["id"]))

    async def save_note(self, interaction: discord.Interaction, ticket_id: int, content: str) -> None:
        ticket = one("SELECT * FROM tickets WHERE id = ? AND thread_id = ? AND status = 'open'",
                     (ticket_id, str(interaction.channel_id)))
        if ticket is None or not self.support_allowed(interaction, ticket):
            await interaction.response.send_message("This ticket note is unavailable.", ephemeral=True)
            return
        with connect() as db:
            db.execute("INSERT INTO ticket_notes (ticket_id, author_id, content, created_at) "
                       "VALUES (?, ?, ?, ?)",
                       (ticket_id, str(interaction.user.id), content,
                        datetime.now(timezone.utc).isoformat()))
        await safe_send(interaction.channel, content=f"[NOTE] {interaction.user.mention}: {content}",
                        allowed_mentions=discord.AllowedMentions.none())
        await interaction.response.send_message("Note saved.", ephemeral=True)

    async def view_notes(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND guild_id = ?",
                     (str(interaction.channel_id), str(GUILD_ID)))
        if ticket is None or not self.support_allowed(interaction, ticket):
            await interaction.response.send_message("Only ticket support staff can view notes.",
                                                    ephemeral=True)
            return
        notes = all_rows("SELECT * FROM ticket_notes WHERE ticket_id = ? ORDER BY id DESC LIMIT 20",
                         (ticket["id"],))
        content = "\n".join(f"<@{note['author_id']}>: {note['content'][:150]}"
                            for note in notes) or "No notes yet."
        await interaction.response.send_message(content[:1900], ephemeral=True,
                                                allowed_mentions=discord.AllowedMentions.none())

    async def claim(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND status = 'open'", (str(interaction.channel_id),))
        if ticket is None or not self.allowed(interaction, ticket):
            await interaction.response.send_message("Only support staff can claim this ticket.", ephemeral=True)
            return
        if ticket["claimed_by"]:
            await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)
            return
        with connect() as db:
            db.execute("UPDATE tickets SET claimed_by = ? WHERE id = ? AND claimed_by IS NULL",
                       (str(interaction.user.id), ticket["id"]))
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else discord.Embed(title="Ticket")
        assignment_field(embed, ticket.get("assigned_to"), str(interaction.user.id))
        selected_panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        config = decoded(selected_panel["extra_config_json"], {}) if selected_panel else {}
        await interaction.response.edit_message(
            embed=embed, view=ticket_view(config, claimed=True,
                                          assigned=bool(ticket.get("assigned_to"))))

    async def close_ticket(self, thread: discord.Thread, ticket: dict,
                           closed_by: str) -> None:
        closed_at = datetime.now(timezone.utc)
        lines = []
        try:
            async for message in thread.history(limit=1000, oldest_first=True):
                text = message.content or "[embed or attachment]"
                lines.append(f"{message.created_at.isoformat()} {message.author} ({message.author.id}): {text}")
        except discord.HTTPException:
            log.warning("Could not read full transcript for ticket %s", ticket["id"])
        notes = all_rows("SELECT * FROM ticket_notes WHERE ticket_id = ? ORDER BY id",
                         (ticket["id"],))
        if notes:
            lines.append("\nInternal notes:")
            lines.extend(f"{note['created_at']} {note['author_id']}: {note['content']}" for note in notes)
        transcript = "\n".join(lines)
        transcript_dir = Path(DB_PATH).parent / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        path = transcript_dir / f"ticket-{ticket['id']}.txt"
        path.write_text(transcript, encoding="utf-8")
        selected_panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        reason = one("SELECT label FROM ticket_reasons WHERE id = ?", (ticket["reason_id"],))
        log_id = decoded(selected_panel["extra_config_json"], {}).get("transcript_channel_id") if selected_panel else None
        log_channel = thread.guild.get_channel(int(log_id)) if log_id else None
        if isinstance(log_channel, discord.TextChannel):
            opened_at = datetime.fromisoformat(ticket["created_at"])
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)
            priority = (one("SELECT label FROM ticket_priorities WHERE id = ?",
                            (ticket["priority_id"],)) if ticket.get("priority_id") else None)
            embed = discord.Embed(
                title=f"Ticket #{ticket['id']} closed",
                color=0x57F287,
                timestamp=closed_at,
            )
            embed.add_field(name="Opened by", value=f"<@{ticket['user_id']}>", inline=True)
            if ticket.get("assigned_to"):
                embed.add_field(name="Assignee", value=f"<@{ticket['assigned_to']}>", inline=True)
            elif ticket["claimed_by"]:
                embed.add_field(name="Claimed by", value=f"<@{ticket['claimed_by']}>", inline=True)
            embed.add_field(name="Closed by", value=closed_by, inline=True)
            embed.add_field(name="Reason", value=reason["label"] if reason else "Unknown", inline=False)
            embed.add_field(name="Opened at", value=f"<t:{int(opened_at.timestamp())}:R>")
            embed.add_field(name="Closed at", value=f"<t:{int(closed_at.timestamp())}:R>")
            embed.add_field(name="Duration", value=str(closed_at - opened_at).split(".")[0])
            if priority:
                embed.add_field(name="Priority", value=priority["label"])
            embed.set_footer(text="Transcript attached below")
            await safe_send(log_channel,
                embed=embed,
                file=discord.File(io.BytesIO(transcript.encode()), filename=path.name),
            )
        with connect() as db:
            db.execute("UPDATE tickets SET status = 'closed', closed_at = ?, transcript_path = ? WHERE id = ?",
                       (closed_at.isoformat(), str(path), ticket["id"]))
        try:
            await thread.edit(archived=True, locked=True)
        except discord.HTTPException:
            log.warning("Could not archive ticket thread %s", thread.id)

    async def close(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND status = 'open'", (str(interaction.channel_id),))
        if ticket is None or (str(interaction.user.id) != ticket["user_id"] and not self.allowed(interaction, ticket)):
            await interaction.response.send_message("You cannot close this ticket.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("Ticket thread unavailable.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.close_ticket(interaction.channel, ticket, interaction.user.mention)
        await interaction.followup.send("Ticket closed.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.add_view(ticket_view())
    bot.add_view(ticket_view(claimed=True))
    bot.add_view(ticket_view(assigned=True))
    bot.add_view(ticket_view(claimed=True, assigned=True))
    bot.add_view(done_view())
    await bot.add_cog(Tickets(bot))
