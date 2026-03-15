"""
TikTok Bot: Ideen sammeln → Video erstellen → Hochladen.

Verwendung:
  python main.py                    # Nächste Idee verarbeiten und hochladen
  python main.py --only-video       # Nur Video erstellen (kein Upload)
  python main.py --auth             # OAuth-URL anzeigen (für ersten Login)
"""
import argparse
import sys
from pathlib import Path

# Projektroot für Imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.ideas import IdeaCollector
from src.video_creator import VideoCreator
from src.upload import TikTokUploader


def run_auth():
    """Zeigt die OAuth-URL und optional Token-Tausch mit Code."""
    if not config.TIKTOK_CLIENT_KEY or not config.TIKTOK_CLIENT_SECRET:
        print("Bitte TIKTOK_CLIENT_KEY und TIKTOK_CLIENT_SECRET in .env setzen.")
        return
    uploader = TikTokUploader(
        client_key=config.TIKTOK_CLIENT_KEY,
        client_secret=config.TIKTOK_CLIENT_SECRET,
        redirect_uri=config.TIKTOK_REDIRECT_URI,
    )
    print("Öffne diese URL im Browser und autorisiere die App:")
    print(uploader.get_auth_url())
    print("\nNach dem Login wirst du zu deiner Redirect-URI weitergeleitet.")
    print("Dort findest du in der URL den Parameter 'code=...'.")
    print("Dann ausführen: python main.py --auth --code DEIN_CODE")
    print("Die erhaltenen Tokens in .env eintragen (TIKTOK_ACCESS_TOKEN, TIKTOK_REFRESH_TOKEN).")


def run_auth_with_code(code: str):
    """Tauscht den Authorization Code gegen Tokens und gibt sie aus."""
    uploader = TikTokUploader(
        client_key=config.TIKTOK_CLIENT_KEY,
        client_secret=config.TIKTOK_CLIENT_SECRET,
        redirect_uri=config.TIKTOK_REDIRECT_URI,
    )
    access, refresh, expires = uploader.exchange_code_for_tokens(code)
    print("Tokens erhalten. Trage diese in deine .env ein:")
    print(f"TIKTOK_ACCESS_TOKEN={access}")
    print(f"TIKTOK_REFRESH_TOKEN={refresh}")
    print(f"Access Token gültig für {expires} Sekunden (~24h). Nutze Refresh Token zum Erneuern.")


def main():
    parser = argparse.ArgumentParser(description="TikTok Bot: Ideen → Video → Upload")
    parser.add_argument("--only-video", action="store_true", help="Nur Video erstellen, nicht hochladen")
    parser.add_argument("--auth", action="store_true", help="OAuth-URL anzeigen")
    parser.add_argument("--code", type=str, help="Authorization Code (nach --auth im Browser erhalten)")
    args = parser.parse_args()

    if args.auth:
        if args.code:
            run_auth_with_code(args.code)
        else:
            run_auth()
        return

    # Idee holen (aus Trends und/oder ideas.json, siehe IDEA_SOURCE in .env)
    collector = IdeaCollector(
        ideas_path=config.IDEAS_FILE,
        source=config.IDEA_SOURCE,
        base_dir=config.BASE_DIR,
        trends_country=config.TRENDS_COUNTRY,
        trends_cache_hours=config.TRENDS_CACHE_HOURS,
    )
    idea = collector.get_next_idea()
    if not idea:
        print("Keine Ideen mehr (Trends leer oder abgelaufen, ideas.json leer?). Bitte IDEA_SOURCE prüfen oder ideas.json befüllen.")
        return

    print(f"Idee: {idea.title}")
    print("Video wird erstellt (TTS + Hintergrund + Text) – bitte warten …")

    # Video erstellen (nur mit Hintergrund-Video; sonst Abbruch)
    creator = VideoCreator(
        config.OUTPUT_DIR,
        width=config.VIDEO_WIDTH,
        height=config.VIDEO_HEIGHT,
        voice=getattr(config, "TTS_VOICE", "de-DE-KatjaNeural"),
        pexels_api_key=getattr(config, "PEXELS_API_KEY", ""),
        background_query=getattr(config, "VIDEO_BACKGROUND_QUERY", "nature landscape"),
        background_videos_dir=config.BACKGROUND_VIDEOS_DIR,
    )
    try:
        video_path = creator.create(idea)
    except RuntimeError as e:
        print(str(e))
        return
    print(f"Video erstellt: {video_path}")

    if args.only_video:
        return

    # Upload (nur wenn Tokens konfiguriert)
    if not config.TIKTOK_ACCESS_TOKEN or not config.TIKTOK_CLIENT_KEY:
        print("Upload übersprungen: TIKTOK_ACCESS_TOKEN und TikTok-App in .env konfigurieren.")
        print("Zum Einrichten: python main.py --auth")
        return

    uploader = TikTokUploader(
        client_key=config.TIKTOK_CLIENT_KEY,
        client_secret=config.TIKTOK_CLIENT_SECRET,
        redirect_uri=config.TIKTOK_REDIRECT_URI,
        access_token=config.TIKTOK_ACCESS_TOKEN,
        refresh_token=config.TIKTOK_REFRESH_TOKEN or None,
    )
    try:
        publish_id = uploader.upload_video(video_path, caption=idea.caption())
        print(f"Upload gestartet. publish_id: {publish_id}")
        print("Prüfe deine TikTok-App (Inbox): Du erhältst eine Benachrichtigung und kannst den Post fertigstellen.")
    except Exception as e:
        print(f"Upload fehlgeschlagen: {e}")
        raise

    collector.mark_used(idea)


if __name__ == "__main__":
    main()
