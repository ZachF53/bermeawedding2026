# Brian & Aisha — Wedding Website

A Django-powered wedding website for **Brian & Aisha**, getting married
**September 5, 2026** at **The Skyline, 707 Dawson St, San Antonio TX 78202**.

## Stack

- Django 5.x
- SQLite (development) — easy to swap to Postgres for production
- Pillow for image handling
- WhiteNoise for static files
- python-dotenv for environment configuration
- Gunicorn for production WSGI
- django-crispy-forms for nicer forms

## Project layout

```
BermaWedding/
├── manage.py
├── requirements.txt
├── .env.example
├── bermeawedding/          # Django project (settings, urls, wsgi, asgi)
├── wedding/                # Main app — models, views, templates, admin
├── media/
│   ├── couple/             # Photos of Brian & Aisha
│   ├── events/             # Event images
│   └── story/              # Timeline / "Our Story" images
├── static/                 # Project-level static assets
└── templates/              # Project-level template overrides (optional)
```

## Local setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url> bermeawedding
cd bermeawedding

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env from the template
cp .env.example .env        # macOS / Linux
copy .env.example .env      # Windows
# then open .env and fill in real values

# 5. Apply migrations and create an admin user
python manage.py migrate
python manage.py createsuperuser

# 6. Run the dev server
python manage.py runserver
```

Visit:
- Site: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

Use the admin to add story moments, events, couple photos, and to moderate
guestbook entries and view RSVPs.

## Environment variables

See `.env.example`. At minimum, set:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key (generate a long random string in prod) |
| `DEBUG` | `True` in dev, `False` in prod |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | SMTP settings for RSVP notifications |
| `NOTIFICATION_EMAIL` | Address that receives RSVP submission emails |

## DigitalOcean deployment

These steps assume the site is currently hosted at SiteGround and the domain's
DNS is managed there. We'll deploy to a DigitalOcean Droplet and then move DNS.

### 1. Create the Droplet

1. Sign in to DigitalOcean and create a Droplet:
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic / Regular / 1 GB RAM / 1 vCPU is enough to start
   - **Region:** Closest to your guests (e.g., NYC3, SFO3, or a Texas-region option)
   - **Authentication:** SSH key (preferred) or password
   - **Hostname:** `brianandaisha` or similar
2. Once provisioned, note the Droplet's public IPv4 address.

### 2. Initial server setup

SSH in as root and create a deploy user:

```bash
ssh root@<droplet-ip>
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

Reconnect as `deploy`:

```bash
ssh deploy@<droplet-ip>
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx git certbot python3-certbot-nginx
```

### 3. Pull the project and install

```bash
cd /home/deploy
git clone <your-repo-url> bermeawedding
cd bermeawedding
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DEBUG=False, real SECRET_KEY, ALLOWED_HOSTS=brianandaisha.com,www.brianandaisha.com,
# and SMTP credentials.
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
deactivate
```

### 4. Gunicorn systemd service

Create `/etc/systemd/system/bermeawedding.service`:

```ini
[Unit]
Description=Gunicorn for Brian & Aisha Wedding
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/bermeawedding
EnvironmentFile=/home/deploy/bermeawedding/.env
ExecStart=/home/deploy/bermeawedding/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/deploy/bermeawedding/bermeawedding.sock \
    bermeawedding.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bermeawedding
sudo systemctl status bermeawedding
```

### 5. Nginx config

Create `/etc/nginx/sites-available/bermeawedding`:

```nginx
server {
    listen 80;
    server_name brianandaisha.com www.brianandaisha.com;

    client_max_body_size 25M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/deploy/bermeawedding/staticfiles/;
    }

    location /media/ {
        alias /home/deploy/bermeawedding/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/deploy/bermeawedding/bermeawedding.sock;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/bermeawedding /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. TLS with Let's Encrypt

> Run this **after** DNS is pointed at the Droplet (next section), or
> Certbot's HTTP-01 challenge will fail.

```bash
sudo certbot --nginx -d brianandaisha.com -d www.brianandaisha.com
```

Certbot will edit the Nginx config to add SSL and set up auto-renewal.

### 7. DNS cutover from SiteGround

Plan ahead — DNS changes can take up to 48 hours to fully propagate, though
most resolvers update within an hour.

**Step A — Lower TTL at SiteGround (do this 24–48 hours before cutover).**

1. Log in to SiteGround → Site Tools → Domain → DNS Zone Editor.
2. Edit the `A` record for `@` (root) and the `A` (or `CNAME`) for `www`.
3. Set TTL to **300 seconds (5 minutes)** if it's higher today (often 3600+).
4. Save. This makes the actual cutover propagate quickly.

**Step B — Decide where DNS will be hosted going forward.**

You have two options:

- **Option 1 — Keep DNS at SiteGround.** Just change the A records.
- **Option 2 — Move DNS to DigitalOcean.** Cleaner long-term if SiteGround is going away.

**Option 1: Keep DNS at SiteGround (simpler)**

In SiteGround DNS Zone Editor:

| Type | Host | Points to | TTL |
|---|---|---|---|
| A | @ | `<droplet-ip>` | 300 |
| A | www | `<droplet-ip>` | 300 |

Save. Wait for propagation (check with `dig brianandaisha.com +short` or
[dnschecker.org](https://dnschecker.org)). Once it resolves to the Droplet IP
worldwide, run the Certbot step above.

**Option 2: Move DNS to DigitalOcean**

1. In DigitalOcean: **Networking → Domains → Add Domain** → enter
   `brianandaisha.com` and assign it to your Droplet. This auto-creates an
   `A` record for `@` pointing at the Droplet.
2. Add a `CNAME` for `www` → `brianandaisha.com.`, or a second `A` for `www`
   pointing at the Droplet IP.
3. Add any MX, TXT, or other records you currently use at SiteGround
   (especially MX records for email — copy them exactly, or email will break
   the moment you switch nameservers).
4. At your **domain registrar** (where you actually own the domain — could be
   SiteGround, GoDaddy, Namecheap, etc.), update the **nameservers** to:
   - `ns1.digitalocean.com`
   - `ns2.digitalocean.com`
   - `ns3.digitalocean.com`
5. Wait for nameserver propagation (can take a few hours up to 48 hours).
6. Confirm with `dig NS brianandaisha.com` — once you see the DigitalOcean
   nameservers returned, DNS is live on DO.
7. Run the Certbot step to issue TLS certs.

**Step C — Verify.**

```bash
dig brianandaisha.com +short        # should return your Droplet IP
dig www.brianandaisha.com +short    # same
curl -I https://brianandaisha.com   # should return 200 with valid TLS
```

**Step D — Decommission SiteGround.**

Only after the new site has been serving cleanly for several days:

1. Confirm RSVPs and email notifications are flowing.
2. Make a final backup of any data still on SiteGround.
3. Cancel the SiteGround hosting plan (keep the domain registration if it
   lives there, unless you've also moved that).

### 8. Updating the site

```bash
ssh deploy@<droplet-ip>
cd /home/deploy/bermeawedding
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
deactivate
sudo systemctl restart bermeawedding
```

### 9. Backups

- Run `python manage.py dumpdata > backup.json` before risky migrations.
- Snapshot the Droplet from the DigitalOcean dashboard before the cutover and
  before any major upgrade.
- Back up `/home/deploy/bermeawedding/media/` regularly — that's where guest
  photos and event images live.

## Useful management commands

```bash
python manage.py runserver           # dev server
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py test                # run the test suite
```

## Customizing the site

Most copy lives in templates under `wedding/templates/wedding/`.
Couple/event/story content is managed entirely through the Django admin.
Styles are in `wedding/static/wedding/css/styles.css`.
