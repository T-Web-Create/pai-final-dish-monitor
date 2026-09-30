#!/usr/bin/env bash
# 2つ目以降のターミナルから同じコンテナに入る
set -euo pipefail
cd "$(dirname "$0")/../docker"
exec docker compose exec sim bash
