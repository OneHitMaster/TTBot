# TikTok Bot

Ein Bot, der **Ideen sammelt**, daraus **Videos erstellt** und sie automatisch bei **TikTok hochlädt**.

## Ablauf

1. **Ideen** kommen automatisch aus **Google Trends** (was gerade in deinem Land trendet) – du musst nichts in `ideas.json` eintragen. Optional kannst du weiterhin eigene Ideen in `ideas.json` pflegen (werden genutzt, wenn keine Trends da sind).
2. **Video-Erstellung**: **Edge TTS**, **synchroner Lauftext**, **Hintergrund**: optional **Stock-Videos** (z. B. Natur, Meer, Wald) von Pexels oder aus einem eigenen Ordner – darüber ein dunkler Overlay und die **Text-Karte**. Ohne Pexels/Ordner: schöner **Gradient-Hintergrund**. Vertikal 1080×1920 (TikTok).
3. **Upload** (optional) über die TikTok Content Posting API oder manuell in der App.

**Trend-Modus:** Standardmäßig nutzt der Bot `IDEA_SOURCE=trends_then_file`: Zuerst werden aktuelle Suchtrends (Google Trends) geholt und daraus Video-Ideen erzeugt; nur wenn keine Trends verfügbar sind, wird `ideas.json` genutzt. In der `.env` kannst du auf `IDEA_SOURCE=file` stellen, wenn du nur eigene Ideen nutzen willst.

## Voraussetzungen

- **Python 3.9+**
- **FFmpeg** im PATH (wird von moviepy für Video-Export genutzt)
- **TikTok Developer App** mit Content Posting API ([developers.tiktok.com](https://developers.tiktok.com/))

## Auf dem Raspberry Pi

Der Bot läuft auch auf einem **Raspberry Pi** (Raspberry Pi OS / Debian).

**→ Ausführliche Schritt-für-Schritt-Anleitung:** [ANLEITUNG_RASPBERRY_PI.md](ANLEITUNG_RASPBERRY_PI.md)

**Einfacher Weg (empfohlen):** Pi vorbereiten → Setup-Skript ausführen → `python main.py --only-video` → Videos liegen in `output/`, du lädst sie in der TikTok-App hoch. Kein TikTok-Developer-Account nötig.

**Vollautomatisch (optional):** Mit TikTok-API direkt hochladen – dafür einmal OAuth und Redirect-URI einrichten (siehe Anleitung).

Kurz-Setup (einfacher Weg):

```bash
cd TTBot
chmod +x setup_raspberry.sh
./setup_raspberry.sh
```

Das Skript installiert FFmpeg, Python-Umgebung und Schriftarten. Anschließend:

```bash
source venv/bin/activate
cp .env.example .env
# .env bearbeiten: TikTok-Keys eintragen
python main.py --auth   # OAuth, dann Token in .env
python main.py          # Bot starten
```

**Hinweis:** Video-Encodes auf dem Pi dauern länger. In der `.env` kannst du für schnellere Encodes eine kleinere Auflösung setzen:

```env
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
```

**Automatischer Lauf (z. B. täglich):** In Crontab eintragen (`crontab -e`), z. B. täglich um 10:00 Uhr (Pfad anpassen):

```cron
0 10 * * * cd /home/pi/TTBot && /home/pi/TTBot/venv/bin/python main.py
```

## Installation (Windows / Linux Desktop)

```bash
cd TTBot
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

`.env` anlegen (siehe `.env.example`):

```env
TIKTOK_CLIENT_KEY=deine_client_key
TIKTOK_CLIENT_SECRET=dein_client_secret
TIKTOK_REDIRECT_URI=https://deine-domain.com/callback
```

Redirect-URI muss in der TikTok Developer Console exakt eingetragen sein (HTTPS, statisch).

## Erster Login (OAuth)

1. **OAuth-URL anzeigen**
   ```bash
   python main.py --auth
   ```
2. URL im Browser öffnen und die App autorisieren.
3. Nach dem Redirect die URL aufrufen – dort steht `code=...` in der Adresszeile.
4. **Token eintauschen**
   ```bash
   python main.py --auth --code DEIN_CODE
   ```
5. Die ausgegebenen `TIKTOK_ACCESS_TOKEN` und `TIKTOK_REFRESH_TOKEN` in die `.env` eintragen.

## Nutzung

- **Ein Video aus der nächsten Idee erstellen und hochladen**
  ```bash
  python main.py
  ```

- **Nur Video erstellen (ohne Upload)**
  ```bash
  python main.py --only-video
  ```

Erstellte Videos liegen im Ordner `output/`.

## Ideen: Trends oder eigene Liste

- **Automatisch (Standard):** Der Bot holt sich Ideen aus **Google Trends** (z. B. Deutschland). Nichts eintragen nötig. In `.env`: `IDEA_SOURCE=trends_then_file` oder `IDEA_SOURCE=trends`. Trends werden bis zu 12 Stunden gecacht (`TRENDS_CACHE_HOURS`, `TRENDS_COUNTRY=germany`).
- **Nur eigene Ideen:** `IDEA_SOURCE=file` setzen und `ideas.json` befüllen.

**ideas.json** (optional bzw. Fallback): Jede Idee hat:

- `id`: Eindeutige ID
- `title`: Titel (wird im Video angezeigt)
- `text`: Gesprochener Text (gTTS)
- `hashtags`: Liste von Hashtags für die Caption

Beispiel:

```json
{
  "id": "4",
  "title": "Mein neues Thema",
  "text": "Der gesprochene Text für das Video.",
  "hashtags": ["#thema", "#tipps"]
}
```

## Hinweise

- **TikTok API**: Pro Access Token gelten Limits (z. B. 6 Upload-Requests pro Minute). Der Bot nutzt die Inbox-Variante; du bestätigst den Post in der TikTok-App.
- **FFmpeg**: Unter Windows FFmpeg installieren und ins PATH legen ([ffmpeg.org](https://ffmpeg.org/)).
- **Stimme**: In der `.env` kannst du `TTS_VOICE` setzen, z. B. `de-DE-KatjaNeural` (weiblich), `de-DE-ConradNeural` (männlich). Liste mit `edge-tts --list-voices`.
- **Hintergrund-Videos**: Mit **PEXELS_API_KEY** (kostenlos auf pexels.com/api) sucht der Bot passende Clips (z. B. `VIDEO_BACKGROUND_QUERY=nature`). Alternativ: Ordner mit eigenen MP4-Dateien unter `BACKGROUND_VIDEOS_DIR` (z. B. `output/backgrounds`). Ohne Key/Ordner wird ein Gradient genutzt.

## Projektstruktur

```
TTBot/
├── main.py              # Einstieg: Idee → Video → Upload
├── config.py            # Konfiguration aus .env
├── ideas.json           # Deine Video-Ideen
├── requirements.txt
├── .env.example
├── output/              # Erstellte Videos
└── src/
    ├── ideas/           # Ideensammlung (ideas.json)
    ├── video_creator/   # TTS + Video (moviepy, gTTS, PIL)
    └── upload/          # TikTok Content Posting API
```

Viel Erfolg mit deinem TikTok-Bot.
