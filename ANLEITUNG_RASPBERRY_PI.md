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
5. Videos in der TikTok-App hochladen (von Hand)
6. Optional: Bot per Cron täglich laufen lassen

**Du brauchst dafür:** keinen TikTok-Developer-Account, keine .env mit Keys, keine Redirect-URI.

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

1. Liest die nächste Idee aus `ideas.json`
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

## Schritt 5: Videos in der TikTok-App hochladen

1. Die fertigen Videos liegen in **`~/TTBot/output/`** (z.B. `video_1.mp4`, `video_2.mp4`).
2. Diese Dateien auf dein Handy bringen (z.B. per Cloud, USB, oder Ordner `output` per SMB im Netzwerk freigeben).
3. In der **TikTok-App** auf „+” tippen → Video hochladen → Datei auswählen.
4. Caption und Hashtags eintragen (die Ideen aus `ideas.json` enthalten Vorschläge; sie stehen auch in der Ausgabe des Bots).

Damit erstellst du die Videos automatisch auf dem Pi und lädst sie nur noch in der App hoch – ohne TikTok-API und OAuth.

---

## Schritt 6: Bot automatisch laufen lassen (Cron, optional)

Damit der Bot z.B. **täglich um 10:00 Uhr** ein neues Video erstellt:

```bash
crontab -e
```

Falls gefragt, einen Editor wählen (z.B. nano). Am Ende der Datei eintragen (Pfad anpassen, wenn dein Benutzer nicht `pi` ist oder TTBot woanders liegt):

```cron
0 10 * * * cd /home/pi/TTBot && /home/pi/TTBot/venv/bin/python main.py --only-video >> /home/pi/TTBot/cron.log 2>&1
```

Speichern und beenden. Ab dann erstellt der Bot jeden Tag um 10:00 Uhr ein Video in `~/TTBot/output/`. Logs: `~/TTBot/cron.log`.

**Cron-Zeiten anpassen:**

- Täglich 10:00: `0 10 * * *`
- Alle 12 Stunden: `0 8,20 * * *`
- Nur Mo–Fr 9:00: `0 9 * * 1-5`

---

## Kurz-Checkliste (einfacher Weg)

- [ ] Raspberry Pi mit Raspberry Pi OS eingerichtet und aktualisiert
- [ ] TTBot-Projekt auf dem Pi (git clone oder kopiert)
- [ ] `./setup_raspberry.sh` erfolgreich ausgeführt
- [ ] `python main.py --only-video` läuft, Videos erscheinen in `output/`
- [ ] Videos in der TikTok-App hochgeladen
- [ ] Optional: Cron für tägliche Video-Erstellung eingerichtet

---

## Vollautomatisch: Upload per TikTok-API (optional)

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
- **FFmpeg nicht gefunden:** Nach dem Setup `which ffmpeg` prüfen. Sonst: `sudo apt-get install ffmpeg`.
- **„Access Token invalid“** (nur bei API-Upload): Token erneuern – OAuth erneut durchführen und neue Tokens in `.env` eintragen.
- **„Redirect URI mismatch“** (nur bei API-Upload): Die in TikTok eingetragene URL muss exakt der Aufruf-URL entsprechen.

Viel Erfolg mit deinem TikTok-Bot auf dem Raspberry Pi.
