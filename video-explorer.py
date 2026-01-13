import os
import subprocess
import sys
from flask import Flask, render_template_string, send_from_directory, abort, Response

# --- Aut-install imageio-ffmpeg ---
try:
    import imageio_ffmpeg as iio_ffmpeg
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"])
    import imageio_ffmpeg as iio_ffmpeg

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ogv"}
BROWSER_SUPPORTED = {".mp4", ".webm", ".ogv"}
PORT = 777
BASE_DIR = os.getcwd()

app = Flask(__name__)

def find_videos(base_dir):
    videos = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                full_path = os.path.join(root, f)
                videos.append(os.path.relpath(full_path, base_dir).replace("\\","/"))
    return sorted(videos, key=lambda p: p.lower())

VIDEOS = find_videos(BASE_DIR)

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
.badge-ext { background:#212529; }
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
<video id="player_{{ loop.index }}" class="video-js vjs-big-play-centered" controls muted preload="none" data-setup='{}'>
<source src="{{ url_for('serve_video', filename=v) }}" type="{{ 'video/mp4' if v.split('.')[-1].lower() not in ['webm','ogv'] else 'video/'+v.split('.')[-1].lower() }}">
Ваш браузер не підтримує відео.
</video>
</div>
<div class="card-body">
<div class="d-flex align-items-start justify-content-between">
<div class="video-title me-2">{{ v }}</div>
<span class="badge badge-ext">{{ v.split('.')[-1].upper() }}</span>
</div>
</div>
</div>
</div>
{% endfor %}
</div>
{% else %}
<div class="alert alert-warning">Відеофайлів не знайдено у "{{ base_dir }}".</div>
{% endif %}
</main>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        videos=VIDEOS,
        base_dir=BASE_DIR
    )

@app.route("/video/<path:filename>")
def serve_video(filename):
    safe_path = os.path.normpath(os.path.join(BASE_DIR, filename))
    if not safe_path.startswith(os.path.abspath(BASE_DIR)) or not os.path.exists(safe_path):
        abort(404)

    ext = os.path.splitext(filename)[1].lower()

    if ext in BROWSER_SUPPORTED:
        return send_from_directory(BASE_DIR, filename, as_attachment=False)
    else:
        # Stream ffmpeg
        ffmpeg_bin = iio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_bin,
            "-i", safe_path,
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+faststart",
            "-vcodec", "libx264",
            "-preset", "fast",
            "-acodec", "aac",
            "-threads", "0",
            "pipe:1"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return Response(proc.stdout, mimetype="video/mp4")

if __name__ == "__main__":
    print(f"Server started: http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
