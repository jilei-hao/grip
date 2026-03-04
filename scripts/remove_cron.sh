#!/usr/bin/env bash
# Remove the GRIP daily digest cron job installed by setup_cron.sh.

CRON_MARKER="# grip-daily-digest"

if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
  crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab -
  echo "Removed GRIP cron job."
else
  echo "No GRIP cron job found."
fi
