# dcbot-suite

A private Discord bot suite for one server, managed through a web dashboard. Features include tickets, honeypot moderation, reaction roles, levels, welcome/goodbye messages, sticky messages, temporary voice channels, sticky roles, and recurring date announcements.

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
7. Enable the **Server Members** and **Message Content** intents in the Discord developer portal.
8. Grant the bot permissions to manage roles, threads, messages, reactions, members, and moderation actions, including **Create Private Threads** and **Manage Channels** for Temp Voice. It also needs **Move Members** to move users from the hub. Place its role above roles it must assign. Support and sticky ping roles must be mentionable, or the bot needs permission to mention them.
9. Make `data/` writable by UID 10001 (`chown -R 10001:10001 data` on the host).
10. Run `docker compose -f docker-compose.prod.yml up -d --build`.
11. Open the web dashboard at the configured web host port and log in.

For detailed setup and LXC notes, see [docs/SETUP.md](docs/SETUP.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Temp Voice commands

Run these in the temporary voice channel while connected to it. `/tempvoice name <name>` renames it (up to 100 characters), `/tempvoice limit <limit>` sets its user limit (0–99; 0 is unlimited), `/tempvoice lock` prevents everyone from connecting, `/tempvoice unlock` lets everyone see and connect to it, and `/tempvoice delete` removes it immediately. These commands require channel ownership. `/tempvoice claim` transfers ownership to a connected member when the current owner is no longer in the channel. Confirmations and errors are private to the command user.

Other member commands are `/rank [user]` (defaults to yourself), `/leaderboard` (top 10 by XP), `/birthday set <day> <month> [label] [year]`, `/birthday remove [label]`, and `/birthday list`. Birthday months appear as English choices; day accepts 1–31 and year accepts 1900–2100, with invalid calendar dates and future years rejected. These replies are private to the command user.

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

## Local development

The fastest local workflow is `docker compose up --build`. For direct development, export the `.env` variables into each process, create a Python 3.12 virtual environment, install `api/requirements.txt` and `bot/requirements.txt`, and run `uvicorn main:app --reload` from `api/`, `python main.py` from `bot/`, and `pnpm install && pnpm dev` from `web/`. Use an absolute local SQLite URL for both Python processes so they resolve the same file.

## Manual deployment

On the LXC host, run `git pull`, `docker compose -f docker-compose.prod.yml build --no-cache`, and `docker compose -f docker-compose.prod.yml up -d`. There are no automatic updates. Back up `data/dcbot.db` with SQLite's backup command, or stop the services before copying the database and its WAL files. API startup adds `tickets.priority_id` to existing databases; new feature tables are created automatically. Back up the database before upgrading.

## First run checklist

- [ ] The API health endpoint responds at `/health`.
- [ ] The dashboard login succeeds.
- [ ] Channels, roles, and emojis appear in the dashboard after bot startup.
- [ ] Configure a panel and select **Post / Update Panel**.
- [ ] Confirm the panel task completes in `GET /api/tasks` and the message appears in Discord.
- [ ] Test each moderation action with a separate non-admin account before relying on it.
