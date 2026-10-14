# dcbot-suite

A private Discord bot suite for one server, managed through a web dashboard. Features include tickets, moderation, rules verification, reaction roles, message and voice XP, welcome/goodbye messages, sticky messages, temporary voice channels, sticky roles, recurring date announcements, polls, community events, and live server stats.

## Requirements

- A Discord application and bot token
- Docker Engine and Docker Compose on a Proxmox LXC host
- A writable `data/` directory for UID 10001

## Setup

1. Copy `.env.example` to `.env`.
2. Set `DISCORD_TOKEN` and `DISCORD_GUILD_ID`.
3. Generate a bcrypt password hash, for example with `python -c "import bcrypt; print(bcrypt.hashpw(input('Password: ').encode(), bcrypt.gensalt()).decode())"` in an environment with `bcrypt` installed. Put the result in `DASHBOARD_PASSWORD_HASH`.
   Wrap the hash in single quotes in `.env` so Compose preserves its `$` characters.
4. Generate `SESSION_SECRET` with at least 32 random characters, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
5. Set `NEXT_PUBLIC_API_BASE_URL` to the API address reachable by your browser. Set `API_HOST_PORT` and `WEB_HOST_PORT` to free host ports.
6. Set `WEB_ORIGIN` to the exact URL the browser uses to reach the dashboard (LXC IP + `WEB_HOST_PORT`). Rebuild the web container after changing `WEB_ORIGIN` or `NEXT_PUBLIC_API_BASE_URL`.
7. Enable the **Server Members**, **Message Content**, and **Presence** intents in the Discord developer portal. Presence is required for the stats `{online}` count.
8. Grant the bot **View Channels**, **Send Messages**, **Embed Links**, **Read Message History**, **Create Private Threads**, **Send Messages in Threads**, **Manage Threads**, **Manage Roles**, **Manage Messages**, **Manage Channels**, **Move Members**, **Moderate Members**, **Kick Members**, **Ban Members**, **Add Reactions**, and **Create Polls** as needed. It also needs **Create Events** and **Manage Events** for scheduled events. Place its role above roles it must assign, including the verified role. Support and sticky ping roles must be mentionable, or the bot needs permission to mention them.
9. Make `data/` writable by UID 10001 (`chown -R 10001:10001 data` on the host).
10. Run `docker compose -f docker-compose.prod.yml up -d --build`.
11. Open the web dashboard at the configured web host port and log in.

For detailed setup and LXC notes, see [docs/SETUP.md](docs/SETUP.md), [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), and the [feature guide](docs/FEATURES.md).

## Temp Voice commands

Run these in the configured Temp Voice control text channel while connected to a temporary voice channel. `/tempvoice name <name>` renames it (up to 100 characters and preserves its leading emoji), `/tempvoice limit <limit>` sets its user limit (0–99; 0 is unlimited), `/tempvoice lock` prevents everyone from connecting, `/tempvoice unlock` allows everyone to connect, and `/tempvoice delete` removes it immediately. These commands require channel ownership. `/tempvoice claim` transfers ownership to a connected member when the current owner is no longer in the channel. Confirmations and errors are private to the command user.

Other member commands are `/rank [user]` (defaults to yourself), `/stats [user]`, `/leaderboard xp`, `/leaderboard messages`, `/birthday set <day> <month> [label] [year]`, `/birthday remove [label]`, and `/birthday list`. Birthday months appear as English choices; day accepts 1–31 and year accepts 1900–2100, with invalid calendar dates and future years rejected. These replies are private to the command user.

Moderators can use `/warn`, `/warns`, `/clearwarns`, `/mute`, `/unmute`, `/ban`, `/kick`, `/slowmode`, `/lock`, and `/unlock`. Configure warning thresholds and logs on `/dashboard/moderation`. An administrator can use `/post-rules` in the configured rules channel; the dashboard can also post or resend the persistent verification message. All moderation and verification confirmations are private.

Use `/help` for the full command list. `/userinfo [user]` and `/serverinfo` show public information embeds. `/poll <question> <option1> <option2> [option3…option10] [duration] [multi]` posts a native poll publicly in the current channel. Available durations start at one hour.

`/event create <title> <date> <time> [description] [type] [channel] [duration_minutes]` schedules an announcement, a Discord event, or both. Enter the date as `YYYY-MM-DD` or `DD.MM.YYYY` and the time as `HH:MM` or `H:MM` in Europe/Berlin time. Choose **Message only**, **Discord event only**, or **Both**. Select a channel for **Message only** or **Both**; those types post there publicly. `/event list` shows upcoming events and their IDs, and `/event cancel <id>` lets the creator or an admin cancel one. Command confirmations and errors are private.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Discord bot token |
| `DISCORD_GUILD_ID` | Server ID for the current dashboard |
| `DASHBOARD_USER` | Single admin username |
| `DASHBOARD_PASSWORD_HASH` | bcrypt password hash |
| `SESSION_SECRET` | Signed session secret and internal sync credential |
| `DATABASE_URL` | Shared SQLite database URL for API and bot |
| `API_HOST_PORT` | Published API host port |
| `WEB_HOST_PORT` | Published web host port |
| `API_BASE_URL` | Internal bot-to-API URL; keep `http://api:8000` |
| `WEB_ORIGIN` | Exact browser URL for the dashboard; used for API CORS and cookies |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-reachable API URL; set before building web |
| `COOKIE_SECURE` | Optional: `true` when served over HTTPS |
| `DASHBOARD_DISCORD_USER_ID` | Optional: Discord ID to attribute dashboard audit entries |

## Local development

The fastest local workflow is `docker compose up --build`. For direct development, export the `.env` variables into each process, create a Python 3.12 virtual environment, install `api/requirements.txt` and `bot/requirements.txt`, and run `uvicorn main:app --reload` from `api/`, `python main.py` from `bot/`, and `pnpm install && pnpm dev` from `web/`. Use an absolute local SQLite URL for both Python processes so they resolve the same file.

## Manual deployment

On the LXC host, run `git pull`, `docker compose -f docker-compose.prod.yml build --no-cache api bot web`, and `docker compose -f docker-compose.prod.yml up -d`. Always use `--no-cache` for changed services. There are no automatic updates. Back up `data/dcbot.db` with `scripts/backup-db.sh` before upgrading; see [deployment instructions](docs/DEPLOYMENT.md) for a cron example. API startup migrates existing ticket, level, panel, welcome, remembering, and Temp Voice settings. The bot requeues interrupted tasks, reports a heartbeat, and runs database maintenance about once a day.

## First run checklist

- [ ] The API health endpoint responds at `/health`.
- [ ] The dashboard login succeeds.
- [ ] Channels, roles, and emojis appear in the dashboard after bot startup.
- [ ] Configure a panel and select **Post / Update Panel**.
- [ ] Confirm the panel task completes in `GET /api/tasks` and the message appears in Discord.
- [ ] Test each moderation action with a separate non-admin account before relying on it.

