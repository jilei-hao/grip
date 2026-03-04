#!/usr/bin/env bash
# Run the GRIP daily digest and append stdout+stderr to a dated log file.
# Intended to be invoked by cron — see setup_cron.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/grip_$(date +%Y%m%d).log"

# Activate the conda environment; adjust CONDA_BASE if your miniconda/anaconda
# lives somewhere other than ~/tk/miniconda3.
CONDA_BASE="${CONDA_BASE:-$HOME/tk/miniconda3}"
# shellcheck source=/dev/null
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate grip-stg

cd "$REPO_ROOT"

{
  echo "==== grip started at $(date) ===="
  grip
  echo "==== grip finished at $(date) ===="
} >> "$LOG_FILE" 2>&1
