# Deployment on Proxmox LXC

Install Docker Engine and the Compose plugin inside the LXC, and configure the container so Docker can run. Clone the repository into a persistent directory. Create `.env` from `.env.example`. Choose free host ports using `API_HOST_PORT` and `WEB_HOST_PORT`, then set `NEXT_PUBLIC_API_BASE_URL` to the LXC IP and chosen API port. Set `WEB_ORIGIN` to the exact URL the browser uses to reach the dashboard, including its protocol and web port. Rebuild the web image after changing either URL.

Create `data/` and grant UID 10001 write access. Start the stack with `docker compose -f docker-compose.prod.yml up -d --build`. The API becomes healthy before the bot and web start. Inspect logs with `docker compose -f docker-compose.prod.yml logs -f api bot web`.

For updates, run `git pull`, `docker compose -f docker-compose.prod.yml build --no-cache api bot web`, and `docker compose -f docker-compose.prod.yml up -d`. Back up the database before applying this feature update; API startup migrates existing ticket and panel settings and creates the stats table. Rebuild every changed service with `--no-cache`. For backup, use `sqlite3 data/dcbot.db '.backup backup.db'` while services run, or stop services and copy the database together with any WAL and SHM files. Keep `.env` and backups outside version control.

For remote access, terminate HTTPS with a reverse proxy and limit dashboard access. Set `COOKIE_SECURE=true`. Allow the browser to reach both the web port and API URL. The API CORS origin is configured through the `WEB_ORIGIN` environment variable, which must be the exact URL the browser uses to reach the dashboard.

