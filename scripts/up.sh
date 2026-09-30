#!/usr/bin/env bash
# コンテナを起動して中に入る。SSD 未マウントなら何もせず止まる。
set -euo pipefail
SSD=/mnt/llm-storage
if ! mountpoint -q "$SSD"; then
  echo "[停止] $SSD がマウントされていません。先に: sudo mount $SSD" >&2
  exit 1
fi
cd "$(dirname "$0")/../docker"
export HOST_USER="$(id -un)" HOST_UID="$(id -u)" HOST_GID="$(id -g)"
# 自分のユーザーだけに X 画面の利用を許可（全開放の xhost + は使わない）
xhost +SI:localuser:"$HOST_USER" >/dev/null
docker compose up -d --build
exec docker compose exec sim bash
