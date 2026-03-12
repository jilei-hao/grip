#!/usr/bin/env bash
# Run the GRIP feedback server (Slack Events API endpoint) and append
# stdout+stderr to a dated log file.
#
# Usage:
#   bash scripts/run_feedback_server.sh            # foreground (Ctrl-C to stop)
#
# In production, manage this process via systemd — see setup_feedback_service.sh.
# For local dev with ngrok, run this in one terminal and ngrok in another.
#
# Environment overrides (all optional):
#   GRIP_SERVER_HOST  — bind address (default: 0.0.0.0)
#   GRIP_SERVER_PORT  — port         (default: 5000)
#   CONDA_BASE        — path to conda installation (default: ~/tk/miniconda3)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/feedback_server_$(date +%Y%m%d).log"

# Activate the conda environment; adjust CONDA_BASE if your miniconda/anaconda
# lives somewhere other than ~/tk/miniconda3.
CONDA_BASE="${CONDA_BASE:-$HOME/tk/miniconda3}"
# shellcheck source=/dev/null
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate grip-stg

cd "$REPO_ROOT"

{
  echo "==== grip-feedback-server started at $(date) ===="
  grip-feedback-server
  echo "==== grip-feedback-server stopped at $(date) ===="
} >> "$LOG_FILE" 2>&1
