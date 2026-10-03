#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Bootstrap from the same pinned base; no host Python or native scientific stack is required.
base_image=$(awk '$1 == "FROM" { print $2; exit }' Dockerfile)
docker run --rm --mount "type=bind,source=$PWD,target=/workspace" -w /workspace "$base_image" python scripts/init_env.py
docker compose config --quiet
docker compose build analytics
docker compose up -d --wait postgres
