# Architecture

The dashboard calls FastAPI with JSON and a signed HTTP-only session cookie. FastAPI owns configuration writes. The bot reads configuration from the shared SQLite database in WAL mode and writes only runtime records such as ticket state, XP, panel message IDs, and task results. The bot sends guild channel, role, and emoji snapshots to the API's internal sync endpoint using `SESSION_SECRET`. This endpoint is outside `/api` and requires the internal header.

Each panel feature stores its embed and target channel in `panels`. Publishing queues `post_panel` or `update_panel` in `bot_tasks`. The bot claims pending tasks about every two seconds and records `done` or `failed`. A saved `message_id` makes later publishes edit the existing panel message. Guild data sync runs at startup and every five minutes.

## Ticket flow

The ticket panel's Open Ticket button sends an ephemeral reason picker. If priorities are configured, the user then chooses one in a second ephemeral picker. The bot creates a private thread in the panel's channel and adds the opener and members holding the reason's support roles. It posts the info embed with persistent Claim, Close, Change priority, and Quick Reply buttons, then the follow-up questions, then a persistent Done button. The info embed shows the selected priority. Only the opener can click Done. The bot disables it and pings the configured support roles once; `answered_at` and `pinged_at` record this step. A support member can claim the ticket, change its priority through an ephemeral picker, or send a configured quick reply. The first nonempty message by the opener is checked against configured auto-response keywords; the bot sends matching responses only for that first message. Closing archives and locks the thread, saves a plaintext transcript, posts it to the configured transcript channel, and marks the ticket closed.
Claimed tickets use a distinct `ticket:claim:claimed` custom ID for their disabled Claim button. Both claimed and unclaimed views are registered at bot startup, so the disabled state remains correct after restarts.

Discord adds users, rather than roles, as private-thread members. The bot expands the configured support roles to their members when opening the ticket. The same role IDs are used for the notification after Done. Existing SQLite databases receive the `answered_at`, `pinged_at`, and `priority_id` columns during API startup. Priorities remain as inactive rows when removed from configuration so existing tickets retain their references. `ticket_first_replies` records which opener message triggered auto-response matching.
If support roles change while tickets are open, the API keeps the original reason row for those tickets and creates a new row for future tickets, so the Done ping reaches the members added when each ticket opened.

## Added features

- Sticky Messages store channel, optional mention role, embed, and cooldown in `sticky_channels`. The bot refreshes a sticky after new human messages; **Sticky now** queues a `post_sticky` task. The current message ID and last post time are runtime fields.
- Temp Voice stores hub settings in `tempvoice_config` and created channels in `tempvoice_active`. Joining the hub creates a private voice channel and moves the member; an empty temporary channel is removed.
- Sticky Roles records a departing member's assignable roles in `sticky_roles_saved` and restores valid roles on rejoin, excluding configured roles. The saved row remains for future joins.
- Remembering Dates are entered by members with `/birthday set`, `/birthday remove`, and `/birthday list`. A daily 08:00 UTC check uses the configured IANA timezone and `remembered_announcements` to avoid duplicate posts for the same local day. Announcement embeds support `{user}`, `{label}`, and `{age}` when a year is stored. February 29 is announced only in leap years.

The API owns feature configuration through authenticated routes. The bot writes runtime rows and timestamps through the shared SQLite file. Voice channels and categories are included in guild data sync for dashboard dropdowns.

Tables include `guild_id` so the schema can support more than one server later. The current API and UI use the configured `DISCORD_GUILD_ID` only. Credentials are a single environment-configured admin account; multi-user auth is outside Phase 1.

## Adding a feature

1. Add configuration and runtime tables in `api/models.py`, plus Pydantic input schemas in `api/schemas.py`.
2. Add a focused router in `api/routers/` and register it in `api/main.py`. Apply session authentication through the common router registration.
3. Add a cog in `bot/cogs/` and load it from `bot/main.py`. Read settings from SQLite. Use `bot_tasks` when a dashboard action must be executed in Discord.
4. Add a dashboard page under `web/app/dashboard/` and a navigation entry in `web/lib/navigation.ts`. Reuse `useConfig`, dropdowns, and `EmbedEditor`.
5. Document permissions, settings, and behavior. Introduce migrations before changing tables in an existing deployment; SQLAlchemy's initial schema creation does not alter existing tables.
