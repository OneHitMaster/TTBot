# TikTok-Bot auf dem Raspberry Pi – Schritt-für-Schritt-Anleitung

Zwei Wege:

- **Einfacher Weg (empfohlen):** Der Bot **erstellt automatisch Videos** aus deinen Ideen. Du lädst sie **selbst in der TikTok-App** hoch – kein TikTok-Developer-Account, kein OAuth, keine Redirect-URL.
- **Vollautomatisch:** Bot erstellt Videos **und** lädt sie per TikTok-API hoch. Dafür brauchst du eine TikTok-Developer-App und einmal OAuth (aufwendiger).

---

## Übersicht – Einfacher Weg (nur Videos erstellen)

1. Raspberry Pi vorbereiten
2. Projekt auf den Pi kopieren
3. Abhängigkeiten installieren (Setup-Skript)
4. Bot starten → Videos landen in `output/`
5. Videos vom Pi aufs Handy holen (Webserver, Samba oder Cloud)
6. In der TikTok-App hochladen
7. Optional: Bot per Cron täglich laufen lassen

**Du brauchst dafür:** keinen TikTok-Developer-Account, keine .env mit Keys, keine Redirect-URI. Themen kommen automatisch aus **Google Trends** – **keine ideas.json nötig**, der Bot sucht sich aktuelle Suchtrends und macht daraus Videos.

---

## Schritt 1: Raspberry Pi vorbereiten

### 1.1 Raspberry Pi OS installieren

- Lade **Raspberry Pi Imager** von [raspberrypi.com/software](https://www.raspberrypi.com/software/) herunter und installiere es.
- Starte den Imager und wähle:
  - **Betriebssystem:** *Raspberry Pi OS (64-bit)* (empfohlen für Pi 4/Pi 5 – nutzt mehr RAM, Encodes laufen oft besser). Für Pi 3 oder älter: *Raspberry Pi OS (32-bit)*.
  - **Speicherkarte:** deine SD-Karte.
- Klicke auf das Zahnrad (Einstellungen) und setze:
  - Benutzername und Passwort
  - WLAN (SSID + Passwort), wenn du per WLAN verbindest
  - **Hostname** z.B. `ttbot-pi`
  - **SSH aktivieren:** „Enable“ und „Use password authentication“ (oder SSH-Key, wenn du einen nutzt)
- „Speichern“ und dann „Schreiben“ – warte, bis das Schreiben fertig ist.

### 1.2 Pi starten und einloggen

- SD-Karte in den Pi stecken, Strom und Netzwerk (LAN oder WLAN) verbinden, Pi einschalten.
- **Am Bildschirm:** Einloggen mit deinem Benutzer und Passwort.
- **Per SSH (von deinem PC):**
  ```bash
  ssh pi@ttbot-pi.local
  ```
  (Ersetze `pi` durch deinen Benutzernamen und `ttbot-pi` durch den gesetzten Hostname, falls anders.)

### 1.3 System aktualisieren

Im Terminal auf dem Pi (oder per SSH):

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

Optional: Neustart danach: `sudo reboot`

---

## Schritt 2: Projekt auf den Raspberry Pi bringen

Du brauchst den TTBot-Ordner auf dem Pi. Zwei Wege:

### Variante A: Mit Git (wenn das Projekt in einem Git-Repo liegt)

```bash
cd ~
git clone https://github.com/DEIN_USER/TTBot.git
cd TTBot
```

(URL durch deine echte Repository-URL ersetzen.)

### Variante B: Projekt per USB/Netzwerk kopieren

- Auf deinem **Windows-PC:** TTBot-Ordner z.B. als ZIP packen.
- Auf den Pi kopieren:
  - per **SMB/Netzwerk:** z.B. `\\ttbot-pi\home\pi\` und dort entpacken, oder
  - per **SCP** von deinem PC:
    ```bash
    scp -r C:\Users\handy\AndroidStudioProjects\TTBot pi@ttbot-pi.local:~/
    ```
- Auf dem Pi ins Projektverzeichnis wechseln:
  ```bash
  cd ~/TTBot
  ```

---

## Schritt 3: Abhängigkeiten installieren (Setup-Skript)

Im Projektordner auf dem Pi:

```bash
cd ~/TTBot
chmod +x setup_raspberry.sh
./setup_raspberry.sh
```

Das Skript installiert u.a.:

- FFmpeg
- Python 3, venv, pip
- Schriftarten (DejaVu)
- Python-Pakete aus `requirements.txt` in eine virtuelle Umgebung

Bei Fehlermeldungen: Prüfen, ob Internetverbindung besteht und ob du mit `sudo` Rechte hast.

---

## Schritt 4: Bot starten (Videos erstellen)

Einmal pro Lauf die virtuelle Umgebung aktivieren und den Bot so starten, dass er **nur Videos erstellt** (kein Upload):

```bash
cd ~/TTBot
source venv/bin/activate
python main.py --only-video
```

Der Bot:

1. Holt ein aktuelles Trend-Thema (Google Trends, keine ideas.json nötig)
2. Erstellt daraus ein Video (Sprache + Titelbild) und speichert es in **`~/TTBot/output/`**

Du siehst z.B.: „Idee: …“, „Video erstellt: …/output/video_1.mp4“.

**Optional – schnellere Encodes auf dem Pi:** Lege eine Datei `.env` an und füge hinzu:

```bash
nano .env
```

Inhalt (optional):

```env
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
```

Speichern: `Strg+O`, Enter, `Strg+X`.

---

## Schritt 5: Videos vom Pi aufs Handy holen

Die Videos liegen auf dem Pi in **`~/TTBot/output/`**. So kommst du mit dem Handy dran (Handy und Pi im **gleichen WLAN**):

### Option A: Übersichtsseite mit Beschreibung und Hashtags (empfohlen)

**Auf dem Pi** (einmal starten, solange du Videos laden willst):

```bash
cd ~/TTBot
python3 serve.py
```

(Alternativ mit venv: `./venv/bin/python serve.py`)

**Auf dem Handy:** Browser öffnen und eingeben:

```
http://ttbot-pi.local:8080
```

(Ersetze `ttbot-pi` durch den Hostnamen deines Pi, falls anders.)

Es erscheint eine **Übersicht** mit erkennbaren Videonamen (vom Titel der Idee), Beschreibungstext und Hashtags. Pro Video: „Caption kopieren“ bzw. „Hashtags kopieren“ – dann in der TikTok-App beim Hochladen einfügen. Auf den Video-Link tippen → Datei laden → in der App hochladen.

Zum Beenden: `Strg+C`.

**Hinweis:** Die Videodateien heißen jetzt z. B. `Was_dir_niemand_ueber_Gewohnheiten_erzaehlt_20260314_171416.mp4` (erkennbar am Titel). Zu jedem Video liegt eine `.json` mit Titel, Text und Hashtags – die Übersichtsseite zeigt sie dir zum Kopieren. Damit die Seite **dauerhaft** erreichbar ist, siehe Schritt 7a.

### Option A2: Nur Dateiliste (ohne Übersichtsseite)

Falls du nur die Roh-Liste der Dateien brauchst:

```bash
cd ~/TTBot/output
python3 -m http.server 8080
```

Dann erscheint die klassische Dateiliste; die Übersicht mit Caption/Hashtags gibt es hier nicht.

### Option B: Ordner per Samba freigeben

**Auf dem Pi:** Samba installieren und einen freigegebenen Ordner einrichten:

```bash
sudo apt-get install -y samba
sudo nano /etc/samba/smb.conf
```

Am **Ende** der Datei einfügen (Benutzername anpassen):

```ini
[TTBot-Videos]
path = /home/pi/TTBot/output
read only = yes
guest ok = yes
```

Speichern (`Strg+O`, Enter, `Strg+X`). Samba neu starten:

```bash
sudo systemctl restart smb
```

**Auf dem Handy (Android):** Dateien-App öffnen → Menü → „Netzwerkspeicher“ / „Server“ / „SMB“ → Server: `ttbot-pi.local` (oder die IP des Pi), Gast-Zugang, keine Anmeldung. Ordner **TTBot-Videos** öffnen und die MP4-Dateien wählen (öffnen/speichern, dann in TikTok hochladen).

**Auf dem iPhone:** Dateien-App → „…“ → „Mit Server verbinden“ → `smb://ttbot-pi.local` → Gast → Ordner **TTBot-Videos** auswählen.

### Option C: Cloud (z.B. Google Drive)

Videos vom Pi in einen Cloud-Ordner kopieren (z.B. per [rclone](https://rclone.org) mit Google Drive), dann auf dem Handy die Cloud-App öffnen und die Datei herunterladen. Etwas mehr Einrichtung, dafür von überall nutzbar.

---

## Schritt 6: In der TikTok-App hochladen

1. Video vom Pi aufs Handy geholt (Option A, B oder C).
2. **TikTok-App** öffnen → „+” → „Hochladen“ → die heruntergeladene/geöffnete Video-Datei auswählen.
3. Caption und Hashtags eintragen (Vorschläge stehen auf der Übersichtsseite :8080 bzw. in der Bot-Ausgabe).

Damit erstellst du die Videos automatisch auf dem Pi und lädst sie nur noch in der App hoch – ohne TikTok-API und OAuth.

---

## Schritt 7: Alles automatisch im Hintergrund

**Ohne TikTok-API:** Der Bot erstellt nur die Videos. Du holst sie dir per Übersichtsseite (Schritt 5) aufs Handy und lädst sie in der TikTok-App hoch – keine Developer-App, keine Redirect-URI, kein OAuth.

### 7a) Webseite dauerhaft online

Damit die Übersicht mit Beschreibung und Hashtags **immer** erreichbar ist (ohne manuelles Starten von `serve.py`):

```bash
sudo cp /home/pi/TTBot/ttbot-serve.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ttbot-serve
```

Status prüfen: `sudo systemctl status ttbot-serve`. Unter `http://ttbot-pi.local:8080/` (oder IP des Pi) ist die Seite dann dauerhaft erreichbar.

### 7b) Bot: z.B. 5 Videos pro Tag (Cron)

Damit der Bot **mehrmals täglich** ein Video erstellt (z.B. 5× am Tag), Cron einrichten:

```bash
chmod +x /home/pi/TTBot/run_bot.sh
crontab -e
```

Im Editor (z.B. nano) am Ende eintragen (Pfad anpassen, wenn Benutzer nicht `pi` oder TTBot woanders liegt):

**5 Videos pro Tag** (z.B. 8:00, 11:00, 14:00, 17:00, 20:00):

```cron
0 8 * * * /home/pi/TTBot/run_bot.sh
0 11 * * * /home/pi/TTBot/run_bot.sh
0 14 * * * /home/pi/TTBot/run_bot.sh
0 17 * * * /home/pi/TTBot/run_bot.sh
0 20 * * * /home/pi/TTBot/run_bot.sh
```

Speichern und beenden. Der Bot läuft dann automatisch zu diesen Zeiten, erstellt je ein Video in `~/TTBot/output/` und schreibt Logs nach `~/TTBot/cron.log`. Die Übersichtsseite unter :8080 zeigt alle Videos mit Caption und Hashtags zum Kopieren.

**Andere Verteilung:**

- 3× am Tag (8:00, 14:00, 20:00): drei Zeilen mit `0 8`, `0 14`, `0 20`
- 1× am Tag (10:00): nur `0 10 * * * /home/pi/TTBot/run_bot.sh`
- Nur Mo–Fr: z.B. `0 9 * * 1-5 /home/pi/TTBot/run_bot.sh`

---

## Kurz-Checkliste (einfacher Weg)

- [ ] Raspberry Pi mit Raspberry Pi OS eingerichtet und aktualisiert
- [ ] TTBot-Projekt auf dem Pi (git clone oder kopiert)
- [ ] `./setup_raspberry.sh` erfolgreich ausgeführt
- [ ] `python main.py --only-video` läuft, Videos erscheinen in `output/`
- [ ] Optional: Webserver dauerhaft (Schritt 7a: systemd) + Cron für z.B. 5 Videos/Tag (Schritt 7b)
- [ ] Videos in der TikTok-App hochgeladen (Übersicht unter :8080)

---

## Vollautomatisch: Upload per TikTok-API (optional)

**Nur nötig, wenn** die Videos wirklich ohne Handy in die TikTok-Inbox sollen. Ansonsten reicht der einfache Weg: Cron + Script (Schritt 7) + Videos per Webserver/Samba holen und in der App hochladen – ohne Developer-App und ohne Redirect-URI.

Wenn der Bot die Videos **direkt bei TikTok hochladen** soll (ohne manuellen Upload in der App), brauchst du eine TikTok-Developer-App und einmal OAuth. Das ist aufwendiger (Redirect-URI, ggf. ngrok).

1. **TikTok Developer App:** [developers.tiktok.com](https://developers.tiktok.com/) → App erstellen → Content Posting API aktivieren. Client Key und Client Secret notieren.
2. **Redirect-URI:** In der App eine HTTPS-URL eintragen, unter der TikTok nach dem Login zurückleitet. Ohne eigene Domain z.B. **ngrok** oder **localhost.run** nutzen (temporäre HTTPS-URL auf deinen Rechner).
3. **.env auf dem Pi:** `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI` eintragen.
4. **OAuth einmal durchführen:** `python main.py --auth` → URL im Browser öffnen → bei TikTok einloggen und erlauben → in der Redirect-URL den `code=...` kopieren → `python main.py --auth --code DEIN_CODE` → ausgegebene Tokens in `.env` eintragen (`TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`).
5. **Bot mit Upload starten:** `python main.py` (ohne `--only-video`). Die Videos landen in deiner TikTok-Inbox; in der App kannst du sie freigeben.

TikTok schreibt diesen Ablauf für API-Uploads vor; einfacher (ohne OAuth/Redirect) geht es leider nicht.

---

## Häufige Probleme

- **Video-Erstellung dauert lange:** Auf dem Pi normal. Optional in `.env`: `VIDEO_WIDTH=720`, `VIDEO_HEIGHT=1280`.
- **„Kein Hintergrund-Video verfügbar“:** Pexels-Key in `.env` prüfen (`PEXELS_API_KEY`) oder Ordner mit MP4-Dateien unter `BACKGROUND_VIDEOS_DIR` anlegen. Ohne gültiges Video bricht der Bot ab.
- **FFmpeg nicht gefunden:** Nach dem Setup `which ffmpeg` prüfen. Sonst: `sudo apt-get install ffmpeg`.
- **„Access Token invalid“** (nur bei API-Upload): Token erneuern – OAuth erneut durchführen und neue Tokens in `.env` eintragen.
- **„Redirect URI mismatch“** (nur bei API-Upload): Die in TikTok eingetragene URL muss exakt der Aufruf-URL entsprechen.

Viel Erfolg mit deinem TikTok-Bot auf dem Raspberry Pi.
