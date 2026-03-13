import os
import uuid
import json
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

from analysis.detector import ArcRaidersDetector
from clip_manager import ClipManager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(BASE_DIR, "static", "clips")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "static", "thumbnails")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Track active jobs: job_id -> {status, progress, clips, error}
jobs = {}

clip_manager = ClipManager(CLIPS_DIR, THUMBNAILS_DIR, DOWNLOADS_DIR)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def start_analysis():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if not _is_valid_twitch_url(url):
        return jsonify({"error": "Please provide a valid Twitch VOD URL (e.g. twitch.tv/videos/...)"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "clips": [],
        "error": None,
        "url": url,
    }

    thread = threading.Thread(target=_run_analysis, args=(job_id, url), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/clips/<job_id>")
def get_clips(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"clips": job["clips"]})


@app.route("/api/clips/<job_id>/<clip_id>/download")
def download_clip(job_id, clip_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            return send_from_directory(
                CLIPS_DIR, clip["filename"],
                as_attachment=True,
                download_name=clip["filename"]
            )

    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/clips/<job_id>/<clip_id>/delete", methods=["POST"])
def delete_clip(job_id, clip_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    for i, clip in enumerate(job["clips"]):
        if clip["id"] == clip_id:
            clip_manager.delete_clip(clip)
            job["clips"].pop(i)
            return jsonify({"success": True})

    return jsonify({"error": "Clip not found"}), 404


def _is_valid_twitch_url(url):
    """Check if URL is a valid Twitch VOD or clip URL."""
    valid_patterns = [
        "twitch.tv/videos/",
        "twitch.tv/",
    ]
    return any(pattern in url.lower() for pattern in valid_patterns)


def _run_analysis(job_id, url):
    """Background worker that downloads, analyzes, and clips the VOD."""
    job = jobs[job_id]

    def update_progress(status, progress, message=""):
        job["status"] = status
        job["progress"] = progress
        socketio.emit("job_update", {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "message": message,
        })

    try:
        # Step 1: Download VOD
        update_progress("downloading", 5, "Downloading Twitch VOD...")
        video_path = clip_manager.download_vod(url, job_id, progress_callback=lambda p: update_progress("downloading", 5 + int(p * 35), f"Downloading... {int(p * 100)}%"))

        if not video_path:
            raise Exception("Failed to download VOD. Check the URL and try again.")

        # Step 2: Analyze video for highlights
        update_progress("analyzing", 40, "Analyzing video for Arc Raiders highlights...")
        detector = ArcRaidersDetector()
        highlights = detector.analyze_video(
            video_path,
            progress_callback=lambda p: update_progress("analyzing", 40 + int(p * 40), f"Analyzing frames... {int(p * 100)}%")
        )

        if not highlights:
            update_progress("complete", 100, "Analysis complete - no highlights found")
            job["clips"] = []
            return

        # Step 3: Extract clips
        update_progress("clipping", 80, f"Extracting {len(highlights)} clips...")
        clips = clip_manager.extract_clips(
            video_path, highlights, job_id,
            progress_callback=lambda p: update_progress("clipping", 80 + int(p * 18), f"Clipping... {int(p * 100)}%")
        )

        job["clips"] = clips
        update_progress("complete", 100, f"Done! Found {len(clips)} highlight clips")

        # Clean up downloaded VOD to save space
        clip_manager.cleanup_download(video_path)

    except Exception as e:
        job["error"] = str(e)
        update_progress("error", 0, str(e))


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
