#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y software-properties-common ffmpeg git curl build-essential

CONDA_ENV_NAME="${CONDA_ENV_NAME:-env311}"
if ! command -v conda >/dev/null 2>&1; then
  echo "Conda is not on PATH. Please install Miniconda/Anaconda first."
  exit 1
fi

. "${HOME}/anaconda3/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV_NAME}" || conda create -n "${CONDA_ENV_NAME}" python=3.11 -y
conda activate "${CONDA_ENV_NAME}"

python -m pip install -U pip wheel setuptools
pip install -r backend/requirements.txt
cp -n .env.example .env || true

echo
 echo "Installed. Run: conda activate ${CONDA_ENV_NAME} && ./run.sh"
