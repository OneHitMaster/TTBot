#!/bin/bash
# TTBot – Setup auf dem Raspberry Pi (Raspberry Pi OS / Debian)
# Ausführen: chmod +x setup_raspberry.sh && ./setup_raspberry.sh

set -e
echo "=== TTBot Setup für Raspberry Pi ==="

# System-Pakete
echo "Installiere System-Pakete (FFmpeg, Python, Schriftarten)..."
sudo apt-get update
sudo apt-get install -y \
  ffmpeg \
  python3 \
  python3-venv \
  python3-pip \
  fonts-dejavu-core

# Optional: kleinere Auflösung für schnellere Encodes auf dem Pi (in .env setzen)
# VIDEO_WIDTH=720 VIDEO_HEIGHT=1280

cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
  echo "Erstelle Python-Umgebung..."
  python3 -m venv venv
fi
echo "Aktiviere venv und installiere Python-Pakete..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup abgeschlossen. Nächste Schritte:"
echo "  1. .env anlegen (siehe .env.example)"
echo "  2. source venv/bin/activate"
echo "  3. python main.py --auth   # OAuth, dann Token in .env"
echo "  4. python main.py          # Bot starten"
echo ""
echo "Hinweis: Video-Encodes auf dem Pi können einige Minuten dauern."
echo "Optional in .env setzen: VIDEO_WIDTH=720 VIDEO_HEIGHT=1280 für schnellere Encodes."
