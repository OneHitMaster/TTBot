"""TikTok Content Posting API: Upload von Videos."""
import os
import time
from pathlib import Path
from typing import Optional, Tuple

import requests

# TikTok API Endpoints
BASE_URL = "https://open.tiktokapis.com"
INIT_UPLOAD_URL = f"{BASE_URL}/v2/post/publish/inbox/video/init/"
TOKEN_URL = f"{BASE_URL}/v2/oauth/token/"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB pro Chunk


class TikTokUploader:
    """Videos per TikTok Content Posting API hochladen."""

    def __init__(
        self,
        client_key: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_key = client_key
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_auth_url(self, state: str = "state") -> str:
        """URL für OAuth-Login (im Browser öffnen)."""
        scopes = "user.info.basic,video.upload,video.publish"
        return (
            "https://www.tiktok.com/auth/authorize/"
            f"?client_key={self.client_key}"
            f"&scope={scopes}"
            f"&response_type=code"
            f"&redirect_uri={requests.utils.quote(self.redirect_uri)}"
            f"&state={state}"
        )

    def exchange_code_for_tokens(self, code: str) -> Tuple[str, str, int]:
        """
        Tauscht Authorization Code gegen Access und Refresh Token.
        Returns: (access_token, refresh_token, expires_in)
        """
        r = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise RuntimeError(f"TikTok API: {data.get('error', '')} - {data.get('description', '')}")
        return (
            data["access_token"],
            data["refresh_token"],
            int(data.get("expires_in", 86400)),
        )

    def refresh_access_token(self) -> str:
        """Erneuert den Access Token mit dem Refresh Token."""
        if not self.refresh_token:
            raise ValueError("Refresh Token fehlt.")
        r = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise RuntimeError(f"TikTok API: {data.get('error', '')} - {data.get('description', '')}")
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        return self.access_token

    def _init_upload(self, video_size: int) -> Tuple[str, str]:
        """Initialisiert den Upload, gibt (publish_id, upload_url) zurück."""
        if not self.access_token:
            raise ValueError("Access Token fehlt. OAuth durchführen oder TIKTOK_ACCESS_TOKEN setzen.")
        total_chunks = (video_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        payload = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": CHUNK_SIZE,
                "total_chunk_count": total_chunks,
            }
        }
        r = requests.post(
            INIT_UPLOAD_URL,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json=payload,
        )
        data = r.json()
        if r.status_code == 401 and data.get("error", {}).get("code") == "access_token_invalid":
            if self.refresh_token:
                self.refresh_access_token()
                return self._init_upload(video_size)
            raise RuntimeError("Access Token abgelaufen. Bitte erneut per OAuth anmelden.")
        r.raise_for_status()
        err = data.get("error", {})
        if err.get("code") != "ok":
            raise RuntimeError(f"TikTok Init: {err.get('code', '')} - {err.get('message', '')}")
        return data["data"]["publish_id"], data["data"]["upload_url"]

    def _upload_chunks(self, upload_url: str, video_path: str, video_size: int) -> None:
        """Lädt die Video-Chunks an upload_url hoch."""
        with open(video_path, "rb") as f:
            chunk_index = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                start = chunk_index * CHUNK_SIZE
                end = start + len(chunk) - 1
                headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                }
                r = requests.put(upload_url, headers=headers, data=chunk)
                r.raise_for_status()
                chunk_index += 1
                time.sleep(0.2)  # Rate limit schonen

    def upload_video(
        self,
        video_path: str,
        caption: Optional[str] = None,
        post_after_upload: bool = False,
    ) -> str:
        """
        Lädt ein Video hoch.
        - video_path: Pfad zur MP4-Datei
        - caption: Beschreibung/Caption (optional)
        - post_after_upload: TikTok erlaubt „Inbox“ – Nutzer bestätigt im App den Post.
        Returns: publish_id zum Status-Check.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(video_path)
        video_size = path.stat().st_size

        publish_id, upload_url = self._init_upload(video_size)
        self._upload_chunks(upload_url, str(path), video_size)

        # Optional: Publish-Request (je nach API-Version); oft geht das nur über Inbox.
        # Der Nutzer erhält eine Benachrichtigung und kann in der App posten/bearbeiten.
        return publish_id
