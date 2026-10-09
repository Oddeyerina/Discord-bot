import asyncio
import io
import logging
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from config import GUILD_ID
from db import DB_PATH, all_rows, connect, decoded, one

log = logging.getLogger(__name__)


def ticket_view(config: dict | None = None, claimed: bool = False) -> discord.ui.View:
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
    return view


def done_view(disabled: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Done", style=discord.ButtonStyle.success,
                                    custom_id="ticket:done", disabled=disabled))
    return view


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._done_locks: dict[int, asyncio.Lock] = {}

        @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id != GUILD_ID or not interaction.data:
            return
        custom_id = interaction.data.get("custom_id", "") if hasattr(interaction.data, "get") else getattr(interaction.data, "custom_id", "")
        if custom_id.startswith("ticket:open:"):
            await self.open_picker(interaction, custom_id)
        elif custom_id.startswith("ticket:reason:"):
            await self.create_ticket(interaction, custom_id)
        elif custom_id == "ticket:claim":
            await self.claim(interaction)
        elif custom_id == "ticket:claim:claimed":
            await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)
        elif custom_id == "ticket:done":
            await self.done(interaction)
        elif custom_id == "ticket:close":
            await self.close(interaction)

    async def open_picker(self, interaction: discord.Interaction, custom_id: str) -> None:
        panel_id = int(custom_id.rsplit(":", 1)[1])
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
        panel_id = int(custom_id.rsplit(":", 1)[1])
        values = interaction.data.get("values", [])
        reason = one("SELECT * FROM ticket_reasons WHERE id = ? AND panel_id = ? AND active = 1",
                     (int(values[0]), panel_id)) if values else None
        selected_panel = one("SELECT * FROM panels WHERE id = ? AND guild_id = ?", (panel_id, str(GUILD_ID)))
        if reason is None or selected_panel is None or not interaction.guild:
            await interaction.response.send_message("This ticket option is no longer available.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(selected_panel["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("The ticket channel is unavailable.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        existing = one("SELECT thread_id FROM tickets WHERE guild_id = ? AND user_id = ? "
                       "AND reason_id = ? AND status = 'open' LIMIT 1",
                       (str(GUILD_ID), str(interaction.user.id), reason["id"]))
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
        name = pattern.replace("{username}", interaction.user.name).replace("{user}", interaction.user.name)[:100]
        thread: discord.Thread | None = None
        try:
            thread = await channel.create_thread(name=name, type=discord.ChannelType.private_thread,
                                                 auto_archive_duration=1440)
            await thread.add_user(interaction.user)
            for member in support_members.values():
                await thread.add_user(member)
            embed = discord.Embed(title="Ticket", description=f"Opened by {interaction.user.mention}\nReason: {reason['label']}",
                                  timestamp=datetime.now(timezone.utc), color=0x5865F2)
            await thread.send(embed=embed, view=ticket_view(decoded(selected_panel["extra_config_json"], {})))
            for question in decoded(reason["questions_json"], []):
                await thread.send(str(question))
            await thread.send("When you have answered the questions, click Done to notify support.", view=done_view())
        except discord.HTTPException:
            log.exception("Could not create private ticket for user %s", interaction.user.id)
            if thread is not None:
                try:
                    await thread.delete(reason="Incomplete ticket setup")
                except discord.HTTPException:
                    log.exception("Could not remove incomplete ticket thread %s", thread.id)
            await interaction.followup.send("The private ticket could not be created. Please try again.", ephemeral=True)
            return
        with connect() as db:
            db.execute("INSERT INTO tickets (guild_id, thread_id, panel_id, user_id, reason_id, status, created_at) "
                       "VALUES (?, ?, ?, ?, ?, 'open', ?)",
                       (str(GUILD_ID), str(thread.id), panel_id, str(interaction.user.id), reason["id"],
                        datetime.now(timezone.utc).isoformat()))
        await interaction.followup.send(f"Your ticket is ready: {thread.mention}", ephemeral=True)

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
                await interaction.channel.send(
                    f"{mentions} Ticket answers are ready for review.",
                    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=roles),
                )
            except discord.HTTPException:
                if interaction.message:
                    try:
                        await interaction.message.edit(view=done_view())
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
        embed.add_field(name="Claimed by", value=interaction.user.mention)
        selected_panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        config = decoded(selected_panel["extra_config_json"], {}) if selected_panel else {}
        await interaction.response.edit_message(embed=embed, view=ticket_view(config, claimed=True))

    async def close(self, interaction: discord.Interaction) -> None:
        ticket = one("SELECT * FROM tickets WHERE thread_id = ? AND status = 'open'", (str(interaction.channel_id),))
        if ticket is None or (str(interaction.user.id) != ticket["user_id"] and not self.allowed(interaction, ticket)):
            await interaction.response.send_message("You cannot close this ticket.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("Ticket thread unavailable.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        lines = []
        async for message in interaction.channel.history(limit=1000, oldest_first=True):
            text = message.content or "[embed or attachment]"
            lines.append(f"{message.created_at.isoformat()} {message.author} ({message.author.id}): {text}")
        transcript = "\n".join(lines)
        transcript_dir = Path(DB_PATH).parent / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        path = transcript_dir / f"ticket-{ticket['id']}.txt"
        path.write_text(transcript, encoding="utf-8")
        selected_panel = one("SELECT extra_config_json FROM panels WHERE id = ?", (ticket["panel_id"],))
        log_id = decoded(selected_panel["extra_config_json"], {}).get("transcript_channel_id") if selected_panel else None
        log_channel = interaction.guild.get_channel(int(log_id)) if log_id and interaction.guild else None
        if isinstance(log_channel, discord.TextChannel):
            await log_channel.send(f"Transcript for ticket #{ticket['id']}",
                                   file=discord.File(io.BytesIO(transcript.encode()), filename=path.name))
        with connect() as db:
            db.execute("UPDATE tickets SET status = 'closed', closed_at = ?, transcript_path = ? WHERE id = ?",
                       (datetime.now(timezone.utc).isoformat(), str(path), ticket["id"]))
        await interaction.channel.edit(archived=True, locked=True)
        await interaction.followup.send("Ticket closed.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.add_view(ticket_view())
    bot.add_view(ticket_view(claimed=True))
    bot.add_view(done_view())
    await bot.add_cog(Tickets(bot))
