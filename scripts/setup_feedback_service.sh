#!/usr/bin/env bash
# Install the GRIP feedback server as a systemd service (Linux only).
# Runs as the current user, restarts automatically on failure.
#
# Prerequisites:
#   - systemd must be available  (Linux servers, WSL2 with systemd enabled)
#   - grip[feedback-server] installed in the conda environment
#   - .env file present in REPO_ROOT with GRIP_SLACK_SIGNING_SECRET set
#
# Usage:
#   bash scripts/setup_feedback_service.sh        # install and start
#   bash scripts/setup_feedback_service.sh --remove  # uninstall
#
# After setup, manage the service with:
#   systemctl --user status  grip-feedback
#   systemctl --user restart grip-feedback
#   journalctl --user -u grip-feedback -f

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
RUN_SCRIPT="$SCRIPT_DIR/run_feedback_server.sh"
SERVICE_NAME="grip-feedback"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

# ── Check platform ────────────────────────────────────────────────────────────
if ! command -v systemctl &>/dev/null; then
  echo "Error: systemctl not found. This script requires systemd (Linux)."
  echo "For macOS, see docs/feedback-server-setup.md for alternatives."
  exit 1
fi

# ── Remove mode ───────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--remove" ]]; then
  systemctl --user stop  "$SERVICE_NAME" 2>/dev/null || true
  systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$SERVICE_FILE"
  systemctl --user daemon-reload
  echo "Removed systemd service: $SERVICE_NAME"
  exit 0
fi

# ── Locate conda environment ──────────────────────────────────────────────────
CONDA_BASE="${CONDA_BASE:-$HOME/tk/miniconda3}"
CONDA_ENV_BIN="$CONDA_BASE/envs/grip-stg/bin"

if [[ ! -f "$CONDA_ENV_BIN/grip-feedback-server" ]]; then
  echo "Error: grip-feedback-server not found in $CONDA_ENV_BIN"
  echo "Make sure the grip[feedback-server] package is installed:"
  echo "  conda activate grip-stg && pip install -e '.[feedback-server]'"
  exit 1
fi

# ── Write systemd unit ────────────────────────────────────────────────────────
mkdir -p "$(dirname "$SERVICE_FILE")"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=GRIP Feedback Server (Slack Events API)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=${REPO_ROOT}/.env
ExecStart=${CONDA_ENV_BIN}/grip-feedback-server
Restart=on-failure
RestartSec=10
StandardOutput=append:${REPO_ROOT}/logs/feedback_server.log
StandardError=append:${REPO_ROOT}/logs/feedback_server.log

[Install]
WantedBy=default.target
EOF

# ── Enable and start ──────────────────────────────────────────────────────────
mkdir -p "$REPO_ROOT/logs"
chmod +x "$RUN_SCRIPT"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

echo ""
echo "Installed and started systemd service: $SERVICE_NAME"
echo ""
echo "Check status:  systemctl --user status $SERVICE_NAME"
echo "Follow logs:   journalctl --user -u $SERVICE_NAME -f"
echo "Stop:          systemctl --user stop $SERVICE_NAME"
echo ""
echo "IMPORTANT: Enable systemd linger so the service survives logout:"
echo "  loginctl enable-linger $(whoami)"
