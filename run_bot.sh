#!/bin/bash
# TTBot: Video erstellen (ohne TikTok-API).
# Für Cron oder manuell. Logs landen in cron.log.
# Neuestes Video steht in output/ – z.B. per Webserver (Schritt 5) aufs Handy holen und in der App hochladen.

set -e
cd "$(dirname "$0")"
LOG="${LOG:-./cron.log}"

# Mit venv, falls vorhanden
if [ -d "venv" ]; then
  PYTHON="./venv/bin/python"
else
  PYTHON="python3"
fi

echo "=== $(date -Iseconds) ===" >> "$LOG"
$PYTHON main.py --only-video >> "$LOG" 2>&1

# Pfad zum zuletzt erstellten Video ausgeben (neueste .mp4 in output/)
if [ -d "output" ]; then
  latest=$(ls -t output/*.mp4 2>/dev/null | head -1)
  if [ -n "$latest" ]; then
    echo "Neuestes Video: $latest" >> "$LOG"
    echo "Neuestes Video: $latest"
  fi
fi
