#!/usr/bin/env bash
# 停止。--purge を付けると課題用のイメージ・コンテナ・ボリュームを完全に削除
# （SSD 上のコード・データ・録画は消えない）
set -euo pipefail
cd "$(dirname "$0")/../docker"
export HOST_USER="$(id -un)" HOST_UID="$(id -u)" HOST_GID="$(id -g)"
if [[ "${1:-}" == "--purge" ]]; then
  docker compose down --rmi all -v
else
  docker compose down
fi
xhost -SI:localuser:"$HOST_USER" >/dev/null || true
