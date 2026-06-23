#!/bin/bash
set -e

SERVER="root@104.131.94.68"
REMOTE_DIR="/var/www/koan"
NGINX_CONF="/etc/nginx/sites-enabled/koan.ehrlich.dev.conf"
SSH_OPTS="-o StrictHostKeyChecking=no"

# Build a fresh copy of the site.
python3 build.py

# Sync the built site (delete removes files that no longer exist locally).
ssh $SSH_OPTS "$SERVER" "mkdir -p $REMOTE_DIR"
rsync -avz --delete -e "ssh $SSH_OPTS" dist/ "$SERVER:$REMOTE_DIR/"

# Create the nginx site config on first deploy if it isn't there yet.
ssh $SSH_OPTS "$SERVER" "test -f $NGINX_CONF || cat > $NGINX_CONF << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name koan.ehrlich.dev;
    root /var/www/koan;
    index index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF"

ssh $SSH_OPTS "$SERVER" "nginx -t && nginx -s reload"

echo
echo "Deployed to koan.ehrlich.dev"
echo "First-time setup (run once after DNS points koan.ehrlich.dev -> 104.131.94.68):"
echo "  ssh $SERVER 'certbot --nginx -d koan.ehrlich.dev'   # enable HTTPS"
