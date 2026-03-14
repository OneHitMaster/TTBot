#!/usr/bin/env python3
"""
Kleiner Webserver für den output/ Ordner.
Unter http://localhost:8080/ erscheint eine Übersicht mit erkennbaren Videonamen,
Beschreibung und Hashtags zum Kopieren für TikTok.
"""
import json
from pathlib import Path

# Projektroot
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
PORT = 8080


def get_videos_with_meta():
    """Sammelt alle .mp4 im output/ und lädt passende .json Metadaten."""
    if not OUTPUT_DIR.is_dir():
        return []
    out = []
    for mp4 in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        meta = {"file": mp4.name, "title": mp4.stem, "text": "", "hashtags": [], "caption": ""}
        json_path = mp4.with_suffix(".json")
        if json_path.exists():
            try:
                with open(json_path, encoding="utf-8") as f:
                    meta.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        out.append(meta)
    return out


def _html_esc(s: str) -> str:
    """Escape für HTML-Inhalt."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_index():
    """Generiert die Übersichtsseite mit Beschreibung und Hashtags."""
    videos = get_videos_with_meta()
    rows = []
    for v in videos:
        title = v.get("title", v["file"])
        text = (v.get("text") or "")[:200] + ("…" if len((v.get("text") or "")) > 200 else "")
        hashtags = v.get("hashtags") or []
        hashtag_str = " ".join(hashtags)
        caption = v.get("caption") or ""
        caption_esc = _html_esc(caption)
        hashtags_esc = _html_esc(hashtag_str)
        rows.append(f"""
        <div class="card">
          <div class="card-title">{_html_esc(str(title))}</div>
          <a href="/{v["file"]}" class="video-link">▶ {v["file"]}</a>
          <p class="text">{_html_esc(text)}</p>
          <p class="hashtags">{hashtags_esc}</p>
          <div class="caption-data" style="display:none">{caption_esc}</div>
          <div class="hashtags-data" style="display:none">{hashtags_esc}</div>
          <div class="actions">
            <button type="button" onclick="copyCaption(this)">Caption kopieren</button>
            <button type="button" onclick="copyHashtags(this)">Hashtags kopieren</button>
          </div>
        </div>""")
    videos_html = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TTBot Videos</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #1a1a2e; color: #eee; }}
    h1 {{ margin-top: 0; }}
    .card {{ background: #16213e; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; max-width: 480px; }}
    .card-title {{ font-weight: bold; font-size: 1.1rem; margin-bottom: 0.5rem; }}
    .video-link {{ color: #4fc3f7; text-decoration: none; display: inline-block; margin-bottom: 0.5rem; }}
    .video-link:hover {{ text-decoration: underline; }}
    .text {{ color: #b0b0b0; font-size: 0.9rem; margin: 0.5rem 0; line-height: 1.4; }}
    .hashtags {{ color: #81c784; font-size: 0.9rem; margin: 0.5rem 0; word-break: break-word; }}
    .actions {{ margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    button {{ background: #0f3460; color: #eee; border: none; padding: 0.5rem 0.75rem; border-radius: 8px; cursor: pointer; font-size: 0.9rem; }}
    button:hover {{ background: #1a4a7a; }}
    .toast {{ position: fixed; bottom: 1rem; right: 1rem; background: #2e7d32; color: #fff; padding: 0.5rem 1rem; border-radius: 8px; display: none; }}
    .toast-error {{ background: #c62828; }}
  </style>
</head>
<body>
  <h1>TTBot Videos</h1>
  <p>Neueste zuerst. Caption/Hashtags kopieren und in der TikTok-App einfügen.</p>
  <div id="list">{videos_html}</div>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
  <script>
    function copyToClipboard(text) {{
      if (!text) return Promise.resolve(false);
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        return navigator.clipboard.writeText(text).then(function() {{ return true; }}).catch(function() {{ return fallbackCopy(text); }});
      }}
      return Promise.resolve(fallbackCopy(text));
    }}
    function fallbackCopy(text) {{
      try {{
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        ta.setSelectionRange(0, text.length);
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        return ok;
      }} catch (e) {{ return false; }}
    }}
    function copyCaption(btn) {{
      var card = btn.closest(".card");
      var el = card ? card.querySelector(".caption-data") : null;
      var caption = el ? el.textContent : "";
      copyToClipboard(caption).then(function(ok) {{ showToast(ok ? "Caption kopiert" : "Kopieren fehlgeschlagen"); }});
    }}
    function copyHashtags(btn) {{
      var card = btn.closest(".card");
      var el = card ? card.querySelector(".hashtags-data") : null;
      var hashtags = el ? el.textContent : "";
      copyToClipboard(hashtags.trim()).then(function(ok) {{ showToast(ok ? "Hashtags kopiert" : "Kopieren fehlgeschlagen"); }});
    }}
    function showToast(msg) {{
      var t = document.getElementById("toast");
      t.textContent = msg || "In Zwischenablage kopiert";
      t.style.display = "block";
      t.className = "toast " + (msg.indexOf("fehlgeschlagen") !== -1 ? "toast-error" : "");
      setTimeout(function() {{ t.style.display = "none"; t.className = "toast"; }}, 2500);
    }}
  </script>
</body>
</html>"""


def main():
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, request, client_address, server):
            super().__init__(request, client_address, server, directory=str(OUTPUT_DIR))
        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_index().encode("utf-8"))
            else:
                super().do_GET()
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("", PORT), CustomHandler)
    print(f"TTBot Videos: http://localhost:{PORT}/")
    print("Übersicht mit Beschreibung und Hashtags. Strg+C zum Beenden.")
    server.serve_forever()


if __name__ == "__main__":
    main()
