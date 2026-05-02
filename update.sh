#!/usr/bin/env bash
# =====================================================================
# Brian & Aisha Wedding — redeploy after a git push.
#
# Run as the `wedding` user (or with sudo, since systemctl restart
# bermeawedding requires sudo for the wedding user). Safe to re-run.
#
#   ssh wedding@24.144.99.254
#   bash /home/wedding/bermeawedding2026/update.sh
# =====================================================================

set -euo pipefail

cd /home/wedding/bermeawedding2026
source venv/bin/activate

git pull origin main
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# MUST restart even for pure static-asset changes: settings.py uses
# whitenoise.storage.CompressedManifestStaticFilesStorage in production,
# which loads the staticfiles manifest into the gunicorn process at
# startup. Without a restart, {% static %} keeps emitting the OLD hashed
# URLs from memory and browsers never see the new collectstatic output.
sudo systemctl restart bermeawedding

echo "[OK] Deployment updated successfully"
