#!/usr/bin/env bash
# =====================================================================
# Brian & Aisha Wedding — Ubuntu 24.04 droplet bootstrap script.
#
# Target droplet: 24.144.99.254
# Domain:        bermeawedding2026.com / www.bermeawedding2026.com
# App user:      wedding
# App dir:       /home/wedding/bermeawedding2026
#
# HOW TO USE
#   1. scp this file to the droplet:  scp deploy.sh root@24.144.99.254:/root/
#   2. ssh to the droplet as root and run it: bash /root/deploy.sh
#   3. After it finishes, edit /home/wedding/bermeawedding2026/.env and
#      replace REPLACE_WITH_SECRET_KEY and REPLACE_WITH_SENDGRID_KEY with
#      real values, then `systemctl restart bermeawedding`.
#   4. Once DNS for bermeawedding2026.com points to this droplet, run:
#        sudo certbot --nginx -d bermeawedding2026.com -d www.bermeawedding2026.com
#   5. Log in to /dashboard/ and CHANGE THE DEFAULT PASSWORD immediately.
#
# DESIGN NOTES
#   - Script is idempotent: re-running it is safe. Existing user, repo,
#     venv, systemd unit, and nginx config are detected and reused.
#   - Runs entirely as root. Steps that must execute as the `wedding`
#     user are wrapped in `sudo -u wedding -H bash -c '...'` rather than
#     `su - wedding`, because `su -` opens an interactive subshell and
#     would not return control to the rest of this script.
#   - apt upgrade is run with DEBIAN_FRONTEND=noninteractive so config
#     file prompts (kernel, sshd) don't hang the script.
#   - collectstatic relies on STATIC_ROOT = BASE_DIR / 'staticfiles',
#     which is already set in bermeawedding/settings.py.
# =====================================================================

set -euo pipefail

# ---------- Config ---------------------------------------------------
APP_USER="wedding"
APP_PASSWORD="WeddingAdmin2026!"
APP_HOME="/home/${APP_USER}"
APP_DIR="${APP_HOME}/bermeawedding2026"
REPO_URL="https://github.com/ZachF53/bermeawedding2026.git"
DROPLET_IP="24.144.99.254"
DOMAIN="bermeawedding2026.com"
SUPERUSER_NAME="brianandaisha"
SUPERUSER_EMAIL="bermeawedding@outlook.com"
SUPERUSER_PASSWORD="WeddingAdmin2026!"
RSVP_SECRET="4uSTHu0SsCu5olLeBEPI19n0W7TQhWtj"

# ---------- Sanity ---------------------------------------------------
if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: must be run as root (got EUID=${EUID})." >&2
    exit 1
fi

echo
echo "############################################################"
echo "# PART 1: ROOT — system packages, user, firewall"
echo "############################################################"

# 1. System update — non-interactive so unattended config-file prompts
#    don't hang the script on a fresh droplet.
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get -o Dpkg::Options::='--force-confdef' \
        -o Dpkg::Options::='--force-confold' \
        upgrade -y

# 2. Required packages.
apt-get install -y \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    git curl ufw

# 3. Create the wedding user (idempotent).
if id -u "${APP_USER}" >/dev/null 2>&1; then
    echo "User ${APP_USER} already exists — skipping creation."
else
    adduser "${APP_USER}" --gecos "" --disabled-password
    echo "${APP_USER}:${APP_PASSWORD}" | chpasswd
fi

# 4. Sudo group.
usermod -aG sudo "${APP_USER}"

# 5. Mirror root's authorized_keys so you can ssh in as wedding.
mkdir -p "${APP_HOME}/.ssh"
if [[ -f /root/.ssh/authorized_keys ]]; then
    cp /root/.ssh/authorized_keys "${APP_HOME}/.ssh/authorized_keys"
fi
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}/.ssh"
chmod 700 "${APP_HOME}/.ssh"
[[ -f "${APP_HOME}/.ssh/authorized_keys" ]] && chmod 600 "${APP_HOME}/.ssh/authorized_keys"

# 6. UFW firewall (idempotent — `ufw allow` is a no-op if rule exists).
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable


echo
echo "############################################################"
echo "# PART 2: AS ${APP_USER} — clone, venv, dependencies, migrate"
echo "############################################################"

# 7. Clone the repo (idempotent).
if [[ ! -d "${APP_DIR}/.git" ]]; then
    sudo -u "${APP_USER}" -H git clone "${REPO_URL}" "${APP_DIR}"
else
    echo "Repo already cloned — pulling latest main."
    sudo -u "${APP_USER}" -H bash -c "cd '${APP_DIR}' && git pull origin main"
fi

# 8. Virtualenv + Python deps. `-H` ensures pip's cache lands under
#    /home/wedding, not /root.
sudo -u "${APP_USER}" -H bash -c "
    set -euo pipefail
    cd '${APP_DIR}'
    [[ -d venv ]] || python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
"

# 9. .env file. Written as root (avoids quoting hell of nesting a
#    heredoc inside `sudo -u ... bash -c '...'`), then chowned. Only
#    overwritten if the file does not already exist, so re-running the
#    script will NOT clobber real keys you have already pasted in.
if [[ ! -f "${APP_DIR}/.env" ]]; then
    cat > "${APP_DIR}/.env" << ENVFILE
# IMPORTANT: replace the two REPLACE_WITH_* values below before the site
# is publicly used. After editing, run: sudo systemctl restart bermeawedding
SECRET_KEY=REPLACE_WITH_SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},${DROPLET_IP}
SENDGRID_API_KEY=REPLACE_WITH_SENDGRID_KEY
DEFAULT_FROM_EMAIL=zacherylong@aspiredwebsites.com
NOTIFICATION_EMAIL=${SUPERUSER_EMAIL}
RSVP_SECRET=${RSVP_SECRET}
# NOTE: settings.py uses sqlite hardcoded at BASE_DIR/db.sqlite3 — there
# is no DATABASE_URL parser wired up. Leaving this var here as a
# reminder if you migrate to Postgres later.
# DATABASE_URL=sqlite:///db.sqlite3
ENVFILE
    chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
else
    echo ".env already exists — leaving in place."
fi

# 10. migrate + collectstatic.
sudo -u "${APP_USER}" -H bash -c "
    set -euo pipefail
    cd '${APP_DIR}'
    source venv/bin/activate
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
"

# 11. Superuser. Idempotent: skipped if already present.
sudo -u "${APP_USER}" -H bash -c "
    cd '${APP_DIR}'
    source venv/bin/activate
    python manage.py shell -c \"
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${SUPERUSER_NAME}').exists():
    User.objects.create_superuser('${SUPERUSER_NAME}', '${SUPERUSER_EMAIL}', '${SUPERUSER_PASSWORD}')
    print('Superuser created')
else:
    print('Superuser already exists')
\"
"


echo
echo "############################################################"
echo "# PART 3: ROOT — gunicorn unit, nginx, services"
echo "############################################################"

# 12. Gunicorn systemd unit.
cat > /etc/systemd/system/bermeawedding.service << SERVICE
[Unit]
Description=Brian & Aisha Wedding Django App
After=network.target

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --access-logfile - \\
    --workers 3 \\
    --bind unix:${APP_DIR}/bermeawedding.sock \\
    bermeawedding.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

# 13. Reload, start, enable. Use restart (not start) so a re-run of the
#     script picks up any unit-file changes.
systemctl daemon-reload
systemctl enable bermeawedding
systemctl restart bermeawedding

# 14. Nginx vhost.
cat > /etc/nginx/sites-available/bermeawedding << NGINX
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} ${DROPLET_IP};

    client_max_body_size 20M;

    location = /favicon.ico {
        access_log off;
        log_not_found off;
    }

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:${APP_DIR}/bermeawedding.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

# 15. Enable vhost, drop default, validate, reload.
ln -sf /etc/nginx/sites-available/bermeawedding /etc/nginx/sites-enabled/bermeawedding
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx


echo
echo "############################################################"
echo "# PART 4: VERIFY"
echo "############################################################"
echo "=== DEPLOYMENT STATUS ==="
systemctl is-active --quiet bermeawedding && echo "[OK] Gunicorn: running" || echo "[FAIL] Gunicorn: not running"
systemctl is-active --quiet nginx          && echo "[OK] Nginx:    running" || echo "[FAIL] Nginx:    not running"
ufw status | grep -q "Status: active"      && echo "[OK] Firewall: active"  || echo "[FAIL] Firewall: inactive"
echo
echo "=== SITE INFO ==="
echo "IP:               ${DROPLET_IP}"
echo "Domain:           ${DOMAIN} (once DNS propagates)"
echo "Dashboard login:  http://${DROPLET_IP}/dashboard/login/"
echo "Username:         ${SUPERUSER_NAME}"
echo "Password:         ${SUPERUSER_PASSWORD}   <-- CHANGE THIS AFTER FIRST LOGIN"
echo
echo "=== NEXT STEPS ==="
echo "1. Edit ${APP_DIR}/.env and replace:"
echo "     REPLACE_WITH_SECRET_KEY    (run: python3 ${APP_DIR}/generate_secret.py)"
echo "     REPLACE_WITH_SENDGRID_KEY  (paste your SendGrid API key)"
echo "   then: sudo systemctl restart bermeawedding"
echo "2. Point DNS for ${DOMAIN} at ${DROPLET_IP} (DigitalOcean nameservers:"
echo "   ns1.digitalocean.com, ns2.digitalocean.com, ns3.digitalocean.com)."
echo "3. Once DNS resolves, get a TLS cert:"
echo "     sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo
echo "=== SSH ACCESS ==="
echo "ssh ${APP_USER}@${DROPLET_IP}"
echo "password: ${APP_PASSWORD}   (or your SSH key, mirrored from root)"
echo
echo "Done."
