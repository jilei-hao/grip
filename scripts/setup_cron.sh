#!/usr/bin/env bash
# Install (or update) the 8 AM cron job for the GRIP daily digest.
# Run once: bash scripts/setup_cron.sh
# To remove: bash scripts/remove_cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$SCRIPT_DIR/run_grip.sh"
CRON_MARKER="# grip-daily-digest"
CRON_LINE="0 8 * * * $RUN_SCRIPT $CRON_MARKER"

chmod +x "$RUN_SCRIPT"

# Add only if not already present
if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
  echo "GRIP cron job already installed:"
  crontab -l | grep "$CRON_MARKER"
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  echo "Installed cron job:"
  echo "  $CRON_LINE"
fi
