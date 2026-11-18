# Deployment Guide

Patterns for deploying to and operating a general Linux server over SSH.

## Running these scripts on a remote host
The scripts are plain bash and are meant to run **on the Linux server**. From a
local machine (including Windows), pipe them over SSH:
```bash
# read-only health snapshot
ssh user@host 'bash -s' < scripts/preflight_check.sh

# service control
ssh user@host 'bash -s' -- status nginx < scripts/service_ctl.sh

# deploy from a git repo on the server
ssh user@host 'bash -s' -- \
  --root /var/www/app --service myapp.service \
  --source git --repo https://github.com/org/app.git --branch main \
  --health http://127.0.0.1:8080/healthz \
  < scripts/deploy.sh
```
Prereqs on the server: `bash`, `git` (for git source), `curl` (for health
checks), `systemctl`. Passwordless SSH keys are strongly recommended.

## Release layout (what deploy.sh creates)
```
/var/www/app/
├── releases/
│   ├── 20261002071500/   # each deploy = timestamped immutable release
│   └── 20261002073000/
└── current -> releases/20261002073000   # atomic symlink; services point here
```
Point the systemd unit's `WorkingDirectory` / app root at `.../current`. Swap is
atomic, so rollback is just re-pointing the symlink — no re-copy, no rebuild.

## systemd unit template
`/etc/systemd/system/myapp.service`:
```ini
[Unit]
Description=My App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/app/current
ExecStart=/var/www/app/current/bin/start
Restart=on-failure
RestartSec=3
EnvironmentFile=-/var/www/app/.env
# hardening (optional)
NoNewPrivileges=true
PrivateTmp=true
MemoryMax=1G

[Install]
WantedBy=multi-user.target
```
After editing: `systemctl daemon-reload && systemctl restart myapp.service`.

## Zero-downtime notes
- A symlink swap + `systemctl restart` gives a *fast* cutover but a brief blip
  for a single-process service. For true zero-downtime use one of:
  - `systemctl reload` when the app supports graceful reload (e.g. nginx, php-fpm).
  - Socket activation or a process manager (pm2, gunicorn `--reload`, systemd
    `Type=notify` with graceful drain).
  - Multiple instances behind a load balancer; drain one node, deploy, re-add.
- Always pass `--health` so a bad release auto-rolls-back.

## Nginx reverse proxy (fronting the app)
`/etc/nginx/sites-available/myapp.conf`:
```nginx
server {
    listen 80;
    server_name app.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```
Enable + apply:
```bash
ln -s /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## TLS with certbot
```bash
certbot --nginx -d app.example.com --redirect --agree-tos -m you@example.com
certbot renew --dry-run          # verify auto-renew works
```

## Deploy checklist (run before/after each deploy)
1. `preflight_check.sh` — disk/memory/load healthy, no failed units.
2. Commit/config backed up; DB migrations reversible.
3. `deploy.sh --dry-run` — confirm the release stages and builds cleanly.
4. Real deploy with `--health`.
5. `service_ctl.sh health <unit>` — active + scan recent error logs.
6. Smoke-test the public endpoint (`curl -I https://app.example.com`).

## Rollback manually (if ever needed outside deploy.sh)
```bash
cd /var/www/app
ls -1dt releases/*/                 # list, newest first
ln -sfn /var/www/app/releases/<good_ts> current.tmp.$$ \
  && mv -Tf current.tmp.$$ current  # atomic re-point
systemctl restart myapp.service
```
