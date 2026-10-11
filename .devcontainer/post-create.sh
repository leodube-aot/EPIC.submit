#!/usr/bin/env bash
# .devcontainer/post-create.sh
#
# Runs once when the dev container is created. System-level packages (GDAL,
# build tools, etc.) belong in the Dockerfile so they're cached in the image
# layer -- this script is for bootstrapping the workspace itself against the
# mounted source (installing deps from requirements.txt / package.json).
set -euo pipefail

WORKSPACE_DIR="$(pwd)"

# echo "==> Installing global TypeScript (devcontainer default)..."
# npm install -g typescript@5.4.5

# echo "==> Setting up submit-api (Python)..."
# cd "$WORKSPACE_DIR/submit-api"
# make setup

# echo "==> Setting up submit-web (Node)..."
# cd "$WORKSPACE_DIR/submit-web"
# npm install
# Run command:
# npm run dev -- --host

cd "$WORKSPACE_DIR"
echo "==> Container ready! Run 'make run' in submit-api and 'npm run dev -- --host' in submit-web."
