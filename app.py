import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

from analysis.detector import ArcRaidersDetector
from analysis.ai_analyzer import GrokVisionAnalyzer
from clip_manager import ClipManager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(BASE_DIR, "static", "clips")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "static", "thumbnails")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

jobs = {}
clip_manager = ClipManager(CLIPS_DIR, THUMBNAILS_DIR, DOWNLOADS_DIR)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def start_analysis():
    data = request.get_json()
    url = data.get("url", "").strip()
    api_key = data.get("api_key", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if not _is_valid_twitch_url(url):
        return jsonify({"error": "Please provide a valid Twitch VOD URL (e.g. twitch.tv/videos/...)"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "downloading",
        "progress": 5,
        "message": "Starting download...",
        "clips": [],
        "error": None,
        "url": url,
        "vod_path": None,
        "vod_duration": 0,
    }

    thread = threading.Thread(
        target=_run_analysis, args=(job_id, url, api_key), daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    # Don't expose vod_path to frontend
    safe = {k: v for k, v in job.items() if k != "vod_path"}
    return jsonify(safe)


@app.route("/api/clips/<job_id>")
def get_clips(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"clips": job["clips"], "vod_duration": job.get("vod_duration", 0)})


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


@app.route("/api/clips/<job_id>/<clip_id>/trim", methods=["POST"])
def trim_clip(job_id, clip_id):
    """Re-extract a clip with new start/end times."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    vod_path = job.get("vod_path")
    if not vod_path or not os.path.exists(vod_path):
        return jsonify({"error": "VOD no longer available. Re-analyze to trim clips."}), 400

    data = request.get_json()
    new_start = data.get("start")
    new_end = data.get("end")

    if new_start is None or new_end is None:
        return jsonify({"error": "start and end required"}), 400

    new_start = max(0, float(new_start))
    new_end = float(new_end)

    if new_end <= new_start:
        return jsonify({"error": "End must be after start"}), 400

    # Find the clip to update
    for i, clip in enumerate(job["clips"]):
        if clip["id"] == clip_id:
            # Delete old clip file
            clip_manager.delete_clip(clip)

            # Re-extract with new times
            result = clip_manager.reclip(vod_path, job_id, clip_id, new_start, new_end)
            if not result:
                return jsonify({"error": "Failed to re-extract clip"}), 500

            # Update clip info
            clip["filename"] = result["filename"]
            clip["thumbnail"] = result["thumbnail"]
            clip["start_time"] = result["start_time"]
            clip["end_time"] = result["end_time"]
            clip["duration"] = result["duration"]
            clip["timestamp_display"] = result["timestamp_display"]

            return jsonify({"success": True, "clip": clip})

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
    valid_patterns = ["twitch.tv/videos/", "twitch.tv/"]
    return any(pattern in url.lower() for pattern in valid_patterns)


def _run_analysis(job_id, url, api_key=""):
    job = jobs[job_id]

    def update(status, progress, message=""):
        job["status"] = status
        job["progress"] = progress
        job["message"] = message

    try:
        update("downloading", 5, "Downloading Twitch VOD...")
        video_path = clip_manager.download_vod(
            url, job_id,
            progress_callback=lambda p: update(
                "downloading", 5 + int(p * 35),
                f"Downloading... {int(p * 100)}%"
            )
        )

        if not video_path:
            raise Exception("Failed to download VOD. Check the URL and try again.")

        # Keep VOD for trimming later
        job["vod_path"] = video_path
        job["vod_duration"] = clip_manager.get_vod_duration(video_path)

        use_ai = bool(api_key)

        if use_ai:
            update("analyzing", 42, "AI is watching your gameplay...")
            analyzer = GrokVisionAnalyzer(api_key)
            highlights = analyzer.analyze_frames(
                video_path,
                sample_interval_sec=8,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"AI analyzing frames... {int(p * 100)}%"
                )
            )
        else:
            update("analyzing", 42, "Analyzing video for highlights...")
            detector = ArcRaidersDetector()
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Scanning frames... {int(p * 100)}%"
                )
            )

        if not highlights:
            update("complete", 100, "Analysis complete - no highlights found")
            job["clips"] = []
            return

        update("clipping", 82, f"Extracting {len(highlights)} clips...")
        clips = clip_manager.extract_clips(
            video_path, highlights, job_id,
            progress_callback=lambda p: update(
                "clipping", 82 + int(p * 16),
                f"Cutting clip {int(p * len(highlights)) + 1} of {len(highlights)}..."
            )
        )

        job["clips"] = clips
        update("complete", 100, f"Done! Found {len(clips)} highlight clips")

        # NOTE: We keep the VOD so users can trim clips

    except Exception as e:
        job["error"] = str(e)
        update("error", 0, str(e))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
