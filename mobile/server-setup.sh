#!/bin/bash
# Six-String Bootcamp server setup — run as root on fresh Ubuntu 24.04.
# Usage: bash server-setup.sh yourdomain.com
set -e
DOMAIN="${1:?Usage: bash server-setup.sh yourdomain.com}"
APP_DIR="$HOME/Six-String-Bootcamp"

apt update && apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cat > /etc/systemd/system/sixstring.service <<UNIT
[Unit]
Description=Six-String Bootcamp (Streamlit)
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m streamlit run app.py --server.port 8501 --server.headless true --server.enableCORS false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now sixstring

cat > /etc/nginx/sites-available/sixstring <<NGINX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/sixstring /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 'Nginx Full' >/dev/null 2>&1 || true
echo "y" | ufw enable >/dev/null 2>&1 || true

certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" --redirect || \
  echo "NOTE: certbot failed (DNS may not have propagated yet). Re-run: certbot --nginx -d $DOMAIN -d www.$DOMAIN"

echo "Done. App: https://$DOMAIN"
