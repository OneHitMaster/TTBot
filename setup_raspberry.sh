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
echo "Setup abgeschlossen. Nächste Schritte (einfacher Weg):"
echo "  1. source venv/bin/activate"
echo "  2. python main.py --only-video    # Erstellt Video in output/"
echo "  3. Auf dem Handy: Browser → http://ttbot-pi.local:8080 (vorher: cd output && python3 -m http.server 8080)"
echo "  4. Video in TikTok-App hochladen"
echo ""
echo "Hinweis: Video-Encodes auf dem Pi können einige Minuten dauern."
echo "Optional .env mit VIDEO_WIDTH=720 VIDEO_HEIGHT=1280 für schnellere Encodes."
echo "Vollautomatischer Upload (TikTok-API) siehe ANLEITUNG_RASPBERRY_PI.md."
