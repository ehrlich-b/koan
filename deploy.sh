#!/bin/bash
set -e

SERVER="root@104.131.94.68"
REMOTE_DIR="/var/www/koan"
SSH_OPTS="-o StrictHostKeyChecking=no"

# Build a fresh copy of the site.
python3 build.py

# Sync the built site (delete removes files that no longer exist locally).
ssh $SSH_OPTS "$SERVER" "mkdir -p $REMOTE_DIR"
rsync -avz --delete -e "ssh $SSH_OPTS" dist/ "$SERVER:$REMOTE_DIR/"

# Plumbing (nginx vhost) is owned by ~/repos/infra — this script only ships content.
echo
echo "Deployed to koan.ehrlich.dev"
