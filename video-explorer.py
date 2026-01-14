import os
import subprocess
import sys
import hashlib
from flask import Flask, render_template_string, send_file, abort, Response, redirect

# --- Auto-install imageio-ffmpeg ---
try:
    import imageio_ffmpeg as iio_ffmpeg
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"])
    import imageio_ffmpeg as iio_ffmpeg

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ogv"}
BROWSER_SUPPORTED = {".mp4", ".webm", ".ogv"}
PORT = 777
BASE_DIR = os.getcwd()

SVG_FAVICON = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="4" y="10" width="56" height="44" rx="6" fill="#212529"/>
  <polygon points="28,22 28,42 46,32" fill="#ff6a00"/>
</svg>
"""

app = Flask(__name__)

# --- helpers ---
def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024

def make_id(path: str) -> str:
    return hashlib.md5(path.encode("utf-8")).hexdigest()

# --- scan videos ---
def find_videos(base_dir):
    videos = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")

                videos.append({
                    "id": make_id(rel_path),
                    "path": rel_path,
                    "size": format_size(os.path.getsize(full_path)),
                    "ext": ext[1:]
                })
    return sorted(videos, key=lambda x: x["path"].lower())

VIDEOS = find_videos(BASE_DIR)

# --- id → path map ---
VIDEO_MAP = {v["id"]: v for v in VIDEOS}

HTML_TEMPLATE = """
<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Відеотека</title>

<link href="https://vjs.zencdn.net/8.26.0/video-js.css" rel="stylesheet" />
<script src="https://vjs.zencdn.net/8.26.0/video.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body { background-color:#f1f3f5; }
.video-card { border:0; box-shadow:0 6px 18px rgba(0,0,0,.06); }
.video-title { font-size:.95rem; word-break:break-word; }
.ratio video { width:100%; height:100%; }
.badge-ext {
    background:#212529;
    font-size: .65rem;
    padding: .35em .55em;
    align-self: flex-start;
}
.pagination .page-link { border:none; background:#ff6a00; color:#fff; }
.pagination .page-item.active .page-link { background:#ff3d00; }
</style>
</head>

<body>
<main class="container my-4">

{% if videos %}
<div class="row g-4 row-cols-1 row-cols-sm-2 row-cols-lg-3">
{% for v in videos %}
<div class="col">
<div class="card video-card h-100">

<div class="ratio ratio-16x9">
<video
  class="video-js vjs-big-play-centered"
  controls
  muted
  preload="metadata"
  data-setup='{}'>
  <source src="{{ url_for('serve_video', video_id=v.id) }}" type="video/mp4">
</video>
</div>

<div class="card-body">
<div class="d-flex justify-content-between">
<div class="video-title">
  {{ v.path }}<br>
  <small class="text-muted">{{ v.size }}</small>
</div>
<span class="badge badge-ext">{{ v.ext.upper() }}</span>
</div>
</div>

</div>
</div>
{% endfor %}
</div>
{% else %}
<div class="alert alert-warning">Відео не знайдено</div>
{% endif %}

</main>

<script>
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('video').forEach(video => {
    video.addEventListener('play', () => {
      if (video.muted) video.muted = false;
    }, { once: true });
  });
});
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, videos=VIDEOS)

@app.route("/favicon.svg")
def favicon_svg():
    return Response(SVG_FAVICON, mimetype="image/svg+xml")

@app.route("/favicon.ico")
def favicon_ico():
    return redirect("/favicon.svg", code=302)

@app.route("/video/<video_id>")
def serve_video(video_id):
    video = VIDEO_MAP.get(video_id)
    if not video:
        abort(404)

    full_path = os.path.join(BASE_DIR, video["path"])
    ext = os.path.splitext(full_path)[1].lower()

    if ext in BROWSER_SUPPORTED:
        return send_file(full_path)
    else:
        ffmpeg_bin = iio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_bin,
            "-i", full_path,
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+faststart",
            "-vcodec", "libx264",
            "-preset", "fast",
            "-acodec", "aac",
            "pipe:1"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return Response(proc.stdout, mimetype="video/mp4")

if __name__ == "__main__":
    print(f"Server started: http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
