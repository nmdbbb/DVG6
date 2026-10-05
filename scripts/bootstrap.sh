#!/usr/bin/env sh
# Dựng toàn bộ hệ thống từ máy trống bằng một lệnh: ./scripts/bootstrap.sh
set -eu
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env
make all
make dashboard
