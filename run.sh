#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

CONDA_ENV_NAME="${CONDA_ENV_NAME:-env311}"
PORT="${PORT:-8765}"
HOST="${HOST:-127.0.0.1}"
CONDA_SH="${HOME}/anaconda3/etc/profile.d/conda.sh"

if [ -f "${CONDA_SH}" ]; then
  . "${CONDA_SH}"
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "conda command not found. Please run: source ~/anaconda3/etc/profile.d/conda.sh"
  exit 1
fi

conda activate "${CONDA_ENV_NAME}" || {
  echo "Environment '${CONDA_ENV_NAME}' not found. Create it with: conda create -n ${CONDA_ENV_NAME} python=3.11 -y"
  exit 1
}

detect_port_pids() {
  local port="$1"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  fi

  if [ -z "${pids}" ] && command -v ss >/dev/null 2>&1; then
    pids="$(ss -ltnp "sport = :${port}" 2>/dev/null | awk 'NR > 1 { if (match($NF, /pid=([0-9]+)/, m)) print m[1] }' | sort -u)"
  fi

  if [ -z "${pids}" ] && command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "${port}" 2>/dev/null || true)"
  fi

  printf '%s\n' "${pids}" | awk 'NF' | sort -u
}

stop_existing_server() {
  local port="$1"
  local pids
  pids="$(detect_port_pids "${port}")"

  if [ -z "${pids}" ]; then
    return 0
  fi

  echo "Port ${port} on ${HOST} is already in use."
  echo "Stopping the existing Podcast Studio process(es) before startup..."
  echo "PIDs: ${pids}"

  for pid in ${pids}; do
    kill "${pid}" 2>/dev/null || true
  done

  sleep 1

  for pid in ${pids}; do
    if kill -0 "${pid}" 2>/dev/null; then
      echo "Force stopping PID ${pid}..."
      kill -9 "${pid}" 2>/dev/null || true
    fi
  done

  echo "Existing server stopped. Starting a fresh instance..."
}

# Stop any existing uvicorn instance already bound to the target port.
stop_existing_server "${PORT}"

set -a
[ -f .env ] && source .env
set +a
exec uvicorn backend.app.main:app --host "${HOST}" --port "${PORT}"
