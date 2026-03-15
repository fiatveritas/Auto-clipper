import os
import re
import json
import shutil
import uuid
import threading
from datetime import datetime
import glob as glob_mod
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file

from analysis.detector import GameDetector
from analysis.ai_analyzer import GrokVisionAnalyzer
from analysis.audio_detector import AudioDetector
from analysis.motion_detector import MotionDetector
from analysis.scene_detector import SceneChangeDetector
from analysis.hybrid_detector import HybridDetector
from analysis.roboflow_analyzer import RoboflowWorkflowAnalyzer
from analysis.roboflow_model_analyzer import RoboflowModelAnalyzer
from analysis.yolo_local_analyzer import YoloLocalAnalyzer
from analysis.arc_clip_detector import ArcClipDetectorAdapter
from analysis.game_profiles import get_all_games
from clip_manager import ClipManager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10 GB for VOD uploads

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(BASE_DIR, "static", "clips")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "static", "thumbnails")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
LIBRARY_DIR = os.path.join(BASE_DIR, "library")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(LIBRARY_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

WATERMARKS_DIR = os.path.join(BASE_DIR, "static", "watermarks")
SFX_DIR = os.path.join(BASE_DIR, "static", "sfx")
PRESETS_FILE = os.path.join(BASE_DIR, "export_presets.json")
ANALYTICS_FILE = os.path.join(BASE_DIR, "analytics.json")
HIGHLIGHT_RULES_FILE = os.path.join(BASE_DIR, "highlight_rules.json")
os.makedirs(WATERMARKS_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)

jobs = {}
watch_folder_thread = None
watch_folder_running = False
clip_manager = ClipManager(CLIPS_DIR, THUMBNAILS_DIR, DOWNLOADS_DIR)


def _save_session(job_id):
    """Persist a completed job's state to disk."""
    job = jobs.get(job_id)
    if not job or job.get("status") != "complete":
        return
    session_data = {
        "job_id": job_id,
        "status": "complete",
        "clips": job["clips"],
        "vod_duration": job.get("vod_duration", 0),
        "vod_path": job.get("vod_path"),
        "url": job.get("url", ""),
        "message": job.get("message", ""),
        "created_at": job.get("created_at", datetime.now().isoformat()),
    }
    path = os.path.join(SESSIONS_DIR, f"{job_id}.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(session_data, f, indent=2)
    os.replace(tmp_path, path)


def _load_sessions():
    """Load all saved session files into the jobs dict on startup."""
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSIONS_DIR, fname)) as f:
                data = json.load(f)
            job_id = data["job_id"]
            # Filter out clips whose files no longer exist
            data["clips"] = [
                c for c in data.get("clips", [])
                if os.path.exists(os.path.join(CLIPS_DIR, c.get("filename", "")))
            ]
            jobs[job_id] = {
                "status": data["status"],
                "progress": 100,
                "message": data.get("message", "Restored session"),
                "clips": data["clips"],
                "error": None,
                "vod_path": data.get("vod_path"),
                "vod_duration": data.get("vod_duration", 0),
                "url": data.get("url", ""),
                "created_at": data.get("created_at", ""),
            }
        except (json.JSONDecodeError, KeyError, OSError):
            continue


_load_sessions()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/games")
def list_games():
    """Return list of supported games for the UI, including custom profiles."""
    games = get_all_games()
    # Add custom profiles
    cp_file = os.path.join(BASE_DIR, "custom_profiles.json")
    if os.path.exists(cp_file):
        try:
            with open(cp_file) as f:
                custom = json.load(f)
            for pid, profile in custom.items():
                games.append({
                    "id": pid,
                    "name": profile.get("name", pid),
                    "description": "Custom profile",
                })
        except (json.JSONDecodeError, KeyError):
            pass
    return jsonify({"games": games})


@app.route("/api/analyze", methods=["POST"])
def start_analysis():
    data = request.get_json()
    url = data.get("url", "").strip()
    library_file = data.get("library_file", "").strip()
    api_key = data.get("api_key", "").strip()
    time_start = data.get("time_start", "").strip()
    time_end = data.get("time_end", "").strip()
    game_id = data.get("game", "arc_raiders").strip()
    detection_method = data.get("detection_method", "audio_cv").strip()
    sensitivity = int(data.get("sensitivity", 50))
    detection_overrides = data.get("detection_overrides", {})

    # Option 1: Re-analyze a saved VOD from the library
    if library_file:
        safe_name = os.path.basename(library_file)
        lib_path = os.path.join(LIBRARY_DIR, safe_name)
        if not os.path.exists(lib_path):
            return jsonify({"error": "Saved VOD not found"}), 404

        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "status": "analyzing",
            "progress": 42,
            "message": "Loading saved VOD...",
            "clips": [],
            "error": None,
            "url": f"library:{safe_name}",
            "vod_path": lib_path,
            "vod_duration": 0,
        }

        thread = threading.Thread(
            target=_run_analysis_on_file, args=(job_id, lib_path, api_key, time_start, time_end, game_id, detection_method, sensitivity, detection_overrides), daemon=True
        )
        thread.start()
        return jsonify({"job_id": job_id})

    # Option 2: Download from URL
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if not _is_valid_stream_url(url):
        return jsonify({"error": "Please provide a valid Twitch or YouTube VOD URL"}), 400

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
        target=_run_analysis, args=(job_id, url, api_key, time_start, time_end, game_id, detection_method, sensitivity, detection_overrides), daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/library")
def list_library():
    """List all saved VODs in the library."""
    vods = []
    for f in sorted(os.listdir(LIBRARY_DIR)):
        fpath = os.path.join(LIBRARY_DIR, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            duration = clip_manager.get_vod_duration(fpath)
            vods.append({
                "filename": f,
                "size": size,
                "duration": duration,
            })
    return jsonify({"vods": vods})


@app.route("/api/library/<filename>/delete", methods=["POST"])
def delete_library_vod(filename):
    """Delete a saved VOD from the library."""
    safe_name = os.path.basename(filename)
    fpath = os.path.join(LIBRARY_DIR, safe_name)
    if os.path.exists(fpath):
        os.remove(fpath)
        return jsonify({"success": True})
    return jsonify({"error": "File not found"}), 404


@app.route("/api/sessions")
def list_sessions():
    """List all saved sessions for the Recent Sessions UI."""
    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSIONS_DIR, fname)) as f:
                data = json.load(f)
            vod_available = bool(data.get("vod_path") and os.path.exists(data["vod_path"]))
            sessions.append({
                "job_id": data["job_id"],
                "clip_count": len(data.get("clips", [])),
                "url": data.get("url", ""),
                "created_at": data.get("created_at", ""),
                "vod_available": vod_available,
            })
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return jsonify({"sessions": sessions})


@app.route("/api/sessions/<job_id>/delete", methods=["POST"])
def delete_session(job_id):
    """Delete a saved session."""
    safe_id = os.path.basename(job_id)
    path = os.path.join(SESSIONS_DIR, f"{safe_id}.json")
    if os.path.exists(path):
        os.remove(path)
        jobs.pop(job_id, None)
        return jsonify({"success": True})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/upload", methods=["POST"])
def upload_vod():
    """Accept a VOD file upload and start analysis.

    Uses streaming write to handle large files (1GB+) without loading
    the entire file into memory.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    allowed_ext = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".ts", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"error": f"Unsupported file type. Use: {', '.join(allowed_ext)}"}), 400

    api_key = request.form.get("api_key", "").strip()
    time_start = request.form.get("time_start", "").strip()
    time_end = request.form.get("time_end", "").strip()
    game_id = request.form.get("game", "arc_raiders").strip()
    detection_method = request.form.get("detection_method", "audio_cv").strip()
    sensitivity = int(request.form.get("sensitivity", 50))
    try:
        detection_overrides = json.loads(request.form.get("detection_overrides", "{}"))
    except (json.JSONDecodeError, TypeError):
        detection_overrides = {}

    job_id = str(uuid.uuid4())[:8]

    # Save to library using streaming chunks to avoid loading entire file into RAM
    safe_name = re.sub(r'[^\w\-. ]', '_', file.filename)
    lib_path = os.path.join(LIBRARY_DIR, safe_name)
    try:
        with open(lib_path, "wb") as out:
            chunk_size = 16 * 1024 * 1024  # 16 MB chunks
            while True:
                chunk = file.stream.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as e:
        # Clean up partial file
        if os.path.exists(lib_path):
            os.remove(lib_path)
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

    file_size_mb = os.path.getsize(lib_path) / (1024 * 1024)
    print(f"  [Upload] Saved {safe_name} ({file_size_mb:.1f} MB)")

    jobs[job_id] = {
        "status": "analyzing",
        "progress": 42,
        "message": "File saved! Analyzing...",
        "clips": [],
        "error": None,
        "url": f"upload:{safe_name}",
        "vod_path": lib_path,
        "vod_duration": 0,
    }

    thread = threading.Thread(
        target=_run_analysis_on_file,
        args=(job_id, lib_path, api_key, time_start, time_end, game_id, detection_method, sensitivity, detection_overrides),
        daemon=True,
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

            _save_session(job_id)
            return jsonify({"success": True, "clip": clip})

    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/clips/<job_id>/<clip_id>/tiktok", methods=["POST"])
def make_tiktok(job_id, clip_id):
    """Convert a clip to TikTok vertical format."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    gameplay_region = data.get("gameplay")
    webcam_region = data.get("webcam")
    layout = data.get("layout", "stacked")

    if not gameplay_region:
        return jsonify({"error": "Gameplay region is required"}), 400

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.make_tiktok(
                clip_path, job_id, clip_id, gameplay_region, webcam_region, layout
            )
            if not result:
                return jsonify({"error": "Failed to create TikTok version"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


@app.route("/api/clips/<job_id>/<clip_id>/edit", methods=["POST"])
def edit_clip_route(job_id, clip_id):
    """Export a clip with crop, speed, and filter adjustments."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    crop = data.get("crop")  # {x, y, w, h} as 0-1 ratios
    speed = float(data.get("speed", 1.0))
    brightness = float(data.get("brightness", 0.0))
    contrast = float(data.get("contrast", 1.0))
    volume = float(data.get("volume", 1.0))

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.edit_clip(
                clip_path, job_id, clip_id,
                crop=crop, speed=speed,
                brightness=brightness, contrast=contrast, volume=volume
            )
            if not result:
                return jsonify({"error": "Failed to export edited clip"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

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
            _save_session(job_id)
            return jsonify({"success": True})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 1: YouTube Shorts export
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/youtube-short", methods=["POST"])
def make_youtube_short(job_id, clip_id):
    """Convert a clip to YouTube Shorts vertical format."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    gameplay_region = data.get("gameplay")
    webcam_region = data.get("webcam")
    layout = data.get("layout", "stacked")

    if not gameplay_region:
        return jsonify({"error": "Gameplay region is required"}), 400

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.make_youtube_short(
                clip_path, job_id, clip_id, gameplay_region, webcam_region, layout
            )
            if not result:
                return jsonify({"error": "Failed to create YouTube Short version"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 2: GIF export
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/gif", methods=["POST"])
def make_gif(job_id, clip_id):
    """Export a clip (or portion) as an animated GIF."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    start_offset = float(data.get("start_offset", 0))
    duration = float(data.get("duration", 10))
    fps = int(data.get("fps", 15))
    width = int(data.get("width", 480))

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.make_gif(
                clip_path, job_id, clip_id,
                start_offset=start_offset, duration=duration,
                fps=fps, width=width
            )
            if not result:
                return jsonify({"error": "Failed to create GIF"}), 500

            return jsonify({
                "success": True,
                "filename": result["filename"],
                "size": result.get("size", 0),
            })

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 3: Watermark a clip
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/watermark", methods=["POST"])
def add_watermark(job_id, clip_id):
    """Apply a watermark image to a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    watermark_filename = data.get("watermark_filename", "")
    position = data.get("position", "bottom_right")
    opacity = float(data.get("opacity", 0.5))
    scale = float(data.get("scale", 0.15))

    safe_name = os.path.basename(watermark_filename)
    watermark_path = os.path.join(WATERMARKS_DIR, safe_name)
    if not os.path.exists(watermark_path):
        return jsonify({"error": "Watermark file not found"}), 404

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.add_watermark(
                clip_path, job_id, clip_id, watermark_path,
                position=position, opacity=opacity, scale=scale
            )
            if not result:
                return jsonify({"error": "Failed to apply watermark"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 4: Upload watermark
# ---------------------------------------------------------------------------
@app.route("/api/watermarks/upload", methods=["POST"])
def upload_watermark():
    """Upload a watermark image (PNG/JPG)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    allowed_ext = {".png", ".jpg", ".jpeg"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"error": f"Unsupported file type. Use: {', '.join(allowed_ext)}"}), 400

    safe_name = re.sub(r'[^\w\-. ]', '_', file.filename)
    dest = os.path.join(WATERMARKS_DIR, safe_name)
    file.save(dest)

    return jsonify({"success": True, "filename": safe_name})


# ---------------------------------------------------------------------------
# Route 5: List watermarks
# ---------------------------------------------------------------------------
@app.route("/api/watermarks")
def list_watermarks():
    """Return list of available watermark images."""
    files = []
    for f in sorted(os.listdir(WATERMARKS_DIR)):
        if os.path.isfile(os.path.join(WATERMARKS_DIR, f)):
            files.append(f)
    return jsonify({"watermarks": files})


# ---------------------------------------------------------------------------
# Route 6: Split clip
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/split", methods=["POST"])
def split_clip(job_id, clip_id):
    """Split a clip into two parts at a given time."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    split_time = data.get("split_time")
    if split_time is None:
        return jsonify({"error": "split_time is required"}), 400

    split_time = float(split_time)

    for i, clip in enumerate(job["clips"]):
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.split_clip(clip_path, job_id, clip_id, split_time)
            if not result:
                return jsonify({"error": "Failed to split clip"}), 500

            # Remove original clip and insert two new ones
            job["clips"].pop(i)
            job["clips"].insert(i, result["part1"])
            job["clips"].insert(i + 1, result["part2"])
            _save_session(job_id)

            return jsonify({
                "success": True,
                "clips": [result["part1"], result["part2"]],
            })

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 7: Extend clip
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/extend", methods=["POST"])
def extend_clip(job_id, clip_id):
    """Extend a clip's boundaries using the original VOD."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    vod_path = job.get("vod_path")
    if not vod_path or not os.path.exists(vod_path):
        return jsonify({"error": "VOD no longer available. Re-analyze to extend clips."}), 400

    data = request.get_json()
    new_start = data.get("start")
    new_end = data.get("end")

    if new_start is None or new_end is None:
        return jsonify({"error": "start and end required"}), 400

    new_start = max(0, float(new_start))
    new_end = float(new_end)

    if new_end <= new_start:
        return jsonify({"error": "End must be after start"}), 400

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            result = clip_manager.extend_clip(vod_path, job_id, clip_id, new_start, new_end)
            if not result:
                return jsonify({"error": "Failed to extend clip"}), 500

            clip["filename"] = result["filename"]
            clip["thumbnail"] = result.get("thumbnail", clip.get("thumbnail"))
            clip["start_time"] = result["start_time"]
            clip["end_time"] = result["end_time"]
            clip["duration"] = result["duration"]
            clip["timestamp_display"] = result.get("timestamp_display", clip.get("timestamp_display"))

            _save_session(job_id)
            return jsonify({"success": True, "clip": clip})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 8: Merge clips
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/merge", methods=["POST"])
def merge_clips(job_id):
    """Merge multiple clips into one, optionally with transitions."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    clip_ids = data.get("clip_ids", [])
    transition = data.get("transition", "none")
    transition_duration = float(data.get("transition_duration", 0.5))

    if len(clip_ids) < 2:
        return jsonify({"error": "At least 2 clips required for merge"}), 400

    clip_paths = []
    for cid in clip_ids:
        found = False
        for clip in job["clips"]:
            if clip["id"] == cid:
                path = os.path.join(CLIPS_DIR, clip["filename"])
                if not os.path.exists(path):
                    return jsonify({"error": f"Clip file not found: {cid}"}), 404
                clip_paths.append(path)
                found = True
                break
        if not found:
            return jsonify({"error": f"Clip not found: {cid}"}), 404

    result = clip_manager.merge_clips(
        clip_paths, job_id, transition=transition,
        transition_duration=transition_duration
    )
    if not result:
        return jsonify({"error": "Failed to merge clips"}), 500

    return jsonify({"success": True, "filename": result["filename"]})


# ---------------------------------------------------------------------------
# Route 9: Add captions
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/captions", methods=["POST"])
def add_captions(job_id, clip_id):
    """Burn captions/subtitles into a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    text = data.get("text", "")
    position = data.get("position", "bottom")
    font_size = int(data.get("font_size", 24))
    color = data.get("color", "white")
    bg_opacity = float(data.get("bg_opacity", 0.5))

    if not text:
        return jsonify({"error": "Caption text is required"}), 400

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.add_captions(
                clip_path, job_id, clip_id,
                text=text, position=position, font_size=font_size,
                color=color, bg_opacity=bg_opacity
            )
            if not result:
                return jsonify({"error": "Failed to add captions"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 10: Zoom/Pan
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/zoompan", methods=["POST"])
def add_zoom_pan(job_id, clip_id):
    """Apply a zoom/pan effect to a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    zoom_start = float(data.get("zoom_start", 1.0))
    zoom_end = float(data.get("zoom_end", 1.5))
    pan_x = float(data.get("pan_x", 0.5))
    pan_y = float(data.get("pan_y", 0.5))

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.add_zoom_pan(
                clip_path, job_id, clip_id,
                zoom_start=zoom_start, zoom_end=zoom_end,
                pan_x=pan_x, pan_y=pan_y
            )
            if not result:
                return jsonify({"error": "Failed to apply zoom/pan"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 11: Sound effect
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/sfx", methods=["POST"])
def add_sfx(job_id, clip_id):
    """Overlay a sound effect onto a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    sfx_filename = data.get("sfx_filename", "")
    timestamp = float(data.get("timestamp", 0))
    volume = float(data.get("volume", 1.0))

    safe_name = os.path.basename(sfx_filename)
    sfx_path = os.path.join(SFX_DIR, safe_name)
    if not os.path.exists(sfx_path):
        return jsonify({"error": "Sound effect file not found"}), 404

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.add_sfx(
                clip_path, job_id, clip_id, sfx_path,
                timestamp=timestamp, volume=volume
            )
            if not result:
                return jsonify({"error": "Failed to add sound effect"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 12: Upload SFX
# ---------------------------------------------------------------------------
@app.route("/api/sfx/upload", methods=["POST"])
def upload_sfx():
    """Upload a sound effect file (MP3/WAV/OGG)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    allowed_ext = {".mp3", ".wav", ".ogg"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"error": f"Unsupported file type. Use: {', '.join(allowed_ext)}"}), 400

    safe_name = re.sub(r'[^\w\-. ]', '_', file.filename)
    dest = os.path.join(SFX_DIR, safe_name)
    file.save(dest)

    return jsonify({"success": True, "filename": safe_name})


# ---------------------------------------------------------------------------
# Route 13: List SFX
# ---------------------------------------------------------------------------
@app.route("/api/sfx")
def list_sfx():
    """Return list of available sound effects."""
    files = []
    for f in sorted(os.listdir(SFX_DIR)):
        if os.path.isfile(os.path.join(SFX_DIR, f)):
            files.append(f)
    return jsonify({"sfx": files})


# ---------------------------------------------------------------------------
# Route 14: Volume spike detection
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/volume-spikes", methods=["POST"])
def detect_volume_spikes(job_id, clip_id):
    """Detect loud moments / volume spikes in a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            spikes = clip_manager.detect_volume_spikes(clip_path)
            if spikes is None:
                return jsonify({"error": "Failed to detect volume spikes"}), 500

            return jsonify({"success": True, "spikes": spikes})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 15: Smart thumbnail
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/smart-thumbnail", methods=["POST"])
def smart_thumbnail(job_id, clip_id):
    """Generate a smart thumbnail for a clip."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if not os.path.exists(clip_path):
                return jsonify({"error": "Clip file not found"}), 404

            result = clip_manager.get_smart_thumbnail(clip_path, job_id, clip_id)
            if not result:
                return jsonify({"error": "Failed to generate smart thumbnail"}), 500

            return jsonify({"success": True, "filename": result["filename"]})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 16: Batch TikTok
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/batch-tiktok", methods=["POST"])
def batch_tiktok(job_id):
    """Convert multiple clips to TikTok format in batch."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    clip_ids = data.get("clip_ids", [])
    gameplay_region = data.get("gameplay")
    webcam_region = data.get("webcam")
    layout = data.get("layout", "stacked")

    if not clip_ids:
        return jsonify({"error": "No clip IDs provided"}), 400
    if not gameplay_region:
        return jsonify({"error": "Gameplay region is required"}), 400

    results = []
    errors = []

    for cid in clip_ids:
        found = False
        for clip in job["clips"]:
            if clip["id"] == cid:
                found = True
                clip_path = os.path.join(CLIPS_DIR, clip["filename"])
                if not os.path.exists(clip_path):
                    errors.append({"clip_id": cid, "error": "Clip file not found"})
                    break

                result = clip_manager.make_tiktok(
                    clip_path, job_id, cid, gameplay_region, webcam_region, layout
                )
                if result:
                    results.append({"clip_id": cid, "filename": result["filename"]})
                else:
                    errors.append({"clip_id": cid, "error": "Failed to create TikTok version"})
                break
        if not found:
            errors.append({"clip_id": cid, "error": "Clip not found"})

    return jsonify({"success": True, "results": results, "errors": errors})


# ---------------------------------------------------------------------------
# Route 17: Clip metadata (tags, notes, review status)
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/<clip_id>/metadata", methods=["POST"])
def update_clip_metadata(job_id, clip_id):
    """Update metadata on a clip: tags, notes, review status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json()
    tags = data.get("tags")
    notes = data.get("notes")
    review_status = data.get("review_status")

    valid_statuses = {"pending", "approved", "rejected", "maybe"}
    if review_status and review_status not in valid_statuses:
        return jsonify({"error": f"Invalid review_status. Use: {', '.join(valid_statuses)}"}), 400

    for clip in job["clips"]:
        if clip["id"] == clip_id:
            if tags is not None:
                clip["tags"] = tags
            if notes is not None:
                clip["notes"] = notes
            if review_status is not None:
                clip["review_status"] = review_status
            _save_session(job_id)
            return jsonify({"success": True, "clip": clip})

    return jsonify({"error": "Clip not found"}), 404


# ---------------------------------------------------------------------------
# Route 18: Export presets CRUD
# ---------------------------------------------------------------------------
def _load_presets():
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE) as f:
            return json.load(f)
    return []


def _save_presets(presets):
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Return all saved export presets."""
    return jsonify({"presets": _load_presets()})


@app.route("/api/presets", methods=["POST"])
def create_preset():
    """Create a new export preset."""
    data = request.get_json()
    name = data.get("name", "").strip()
    preset_type = data.get("type", "tiktok")
    settings = data.get("settings", {})

    if not name:
        return jsonify({"error": "Preset name is required"}), 400

    presets = _load_presets()
    preset = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "type": preset_type,
        "settings": settings,
    }
    presets.append(preset)
    _save_presets(presets)

    return jsonify({"success": True, "preset": preset})


@app.route("/api/presets/<preset_id>/delete", methods=["POST"])
def delete_preset(preset_id):
    """Delete an export preset."""
    presets = _load_presets()
    new_presets = [p for p in presets if p.get("id") != preset_id]
    if len(new_presets) == len(presets):
        return jsonify({"error": "Preset not found"}), 404
    _save_presets(new_presets)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Route 19: Analytics tracking
# ---------------------------------------------------------------------------
def _load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    return {"events": []}


def _save_analytics(data):
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Return tracked analytics events."""
    return jsonify(_load_analytics())


@app.route("/api/analytics/track", methods=["POST"])
def track_analytics():
    """Track an analytics event (export, download, etc.)."""
    data = request.get_json()
    event_type = data.get("event", "")
    event_data = data.get("data", {})

    if not event_type:
        return jsonify({"error": "Event type is required"}), 400

    analytics = _load_analytics()
    analytics["events"].append({
        "id": str(uuid.uuid4())[:8],
        "event": event_type,
        "data": event_data,
        "timestamp": datetime.now().isoformat(),
    })
    _save_analytics(analytics)

    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Route 20: Duplicate detection
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/duplicates")
def detect_duplicates(job_id):
    """Find clips with >50% overlapping time ranges."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    clips = job.get("clips", [])
    groups = []
    visited = set()

    for i, c1 in enumerate(clips):
        if c1["id"] in visited:
            continue
        s1 = c1.get("start_time", 0)
        e1 = c1.get("end_time", s1 + c1.get("duration", 0))
        group = [c1["id"]]

        for j, c2 in enumerate(clips):
            if j <= i or c2["id"] in visited:
                continue
            s2 = c2.get("start_time", 0)
            e2 = c2.get("end_time", s2 + c2.get("duration", 0))

            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            overlap = max(0, overlap_end - overlap_start)

            dur1 = e1 - s1
            dur2 = e2 - s2
            min_dur = min(dur1, dur2) if min(dur1, dur2) > 0 else 1

            if overlap / min_dur > 0.5:
                group.append(c2["id"])
                visited.add(c2["id"])

        if len(group) > 1:
            visited.add(c1["id"])
            groups.append(group)

    return jsonify({"duplicate_groups": groups})


# ---------------------------------------------------------------------------
# Route 21: Sort / filter clips
# ---------------------------------------------------------------------------
@app.route("/api/clips/<job_id>/sorted")
def sorted_clips(job_id):
    """Return clips sorted and/or filtered by query params."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    sort_by = request.args.get("sort_by", "time")
    order = request.args.get("order", "asc")
    tag_filter = request.args.get("tag")
    status_filter = request.args.get("review_status")

    result = list(job.get("clips", []))

    if tag_filter:
        result = [c for c in result if tag_filter in c.get("tags", [])]
    if status_filter:
        result = [c for c in result if c.get("review_status") == status_filter]

    sort_keys = {
        "confidence": lambda c: c.get("confidence", 0),
        "duration": lambda c: c.get("duration", 0),
        "time": lambda c: c.get("start_time", 0),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["time"])
    result.sort(key=key_fn, reverse=(order == "desc"))

    return jsonify({"clips": result, "total": len(result)})


# ---------------------------------------------------------------------------
# Route 22: Watch folder start / stop / status
# ---------------------------------------------------------------------------
def _watch_folder_loop(api_key, game_id):
    """Background loop that watches LIBRARY_DIR for new files and auto-analyzes."""
    global watch_folder_running
    import time
    seen = set(os.listdir(LIBRARY_DIR))
    while watch_folder_running:
        time.sleep(5)
        try:
            current = set(os.listdir(LIBRARY_DIR))
            new_files = current - seen
            for fname in new_files:
                fpath = os.path.join(LIBRARY_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in {".mp4", ".mkv", ".mov", ".avi", ".flv", ".ts", ".webm"}:
                    continue
                job_id = str(uuid.uuid4())[:8]
                jobs[job_id] = {
                    "status": "analyzing",
                    "progress": 42,
                    "message": f"Auto-analyzing {fname}...",
                    "clips": [],
                    "error": None,
                    "url": f"watch:{fname}",
                    "vod_path": fpath,
                    "vod_duration": 0,
                }
                thread = threading.Thread(
                    target=_run_analysis_on_file,
                    args=(job_id, fpath, api_key, "", "", game_id),
                    daemon=True,
                )
                thread.start()
            seen = current
        except OSError:
            pass


@app.route("/api/watch-folder/start", methods=["POST"])
def watch_folder_start():
    """Start watching the library folder for new files."""
    global watch_folder_thread, watch_folder_running

    if watch_folder_running:
        return jsonify({"success": True, "message": "Already running"})

    data = request.get_json() or {}
    api_key = data.get("api_key", "")
    game_id = data.get("game", "arc_raiders")

    watch_folder_running = True
    watch_folder_thread = threading.Thread(
        target=_watch_folder_loop, args=(api_key, game_id), daemon=True
    )
    watch_folder_thread.start()

    return jsonify({"success": True, "message": "Watch folder started"})


@app.route("/api/watch-folder/stop", methods=["POST"])
def watch_folder_stop():
    """Stop the watch folder background thread."""
    global watch_folder_running
    watch_folder_running = False
    return jsonify({"success": True, "message": "Watch folder stopped"})


@app.route("/api/watch-folder/status")
def watch_folder_status():
    """Return whether the watch folder is currently running."""
    return jsonify({"running": watch_folder_running})


# ---------------------------------------------------------------------------
# Route 23: Custom highlight rules
# ---------------------------------------------------------------------------
def _load_highlight_rules():
    if os.path.exists(HIGHLIGHT_RULES_FILE):
        with open(HIGHLIGHT_RULES_FILE) as f:
            return json.load(f)
    return []


def _save_highlight_rules(rules):
    with open(HIGHLIGHT_RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


@app.route("/api/highlight-rules", methods=["GET", "POST"])
def highlight_rules():
    """List or create custom highlight detection rules."""
    if request.method == "GET":
        return jsonify({"rules": _load_highlight_rules()})

    data = request.get_json()
    name = data.get("name", "").strip()
    rule_type = data.get("type", "volume_spike")
    params = data.get("params", {})

    if not name:
        return jsonify({"error": "Rule name is required"}), 400

    valid_types = {"volume_spike", "color_detect", "motion"}
    if rule_type not in valid_types:
        return jsonify({"error": f"Invalid type. Use: {', '.join(valid_types)}"}), 400

    rules = _load_highlight_rules()
    rule = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "type": rule_type,
        "params": params,
    }
    rules.append(rule)
    _save_highlight_rules(rules)

    return jsonify({"success": True, "rule": rule})


@app.route("/api/highlight-rules/<rule_id>/delete", methods=["POST"])
def delete_highlight_rule(rule_id):
    """Delete a custom highlight rule."""
    rules = _load_highlight_rules()
    new_rules = [r for r in rules if r.get("id") != rule_id]
    if len(new_rules) == len(rules):
        return jsonify({"error": "Rule not found"}), 404
    _save_highlight_rules(new_rules)
    return jsonify({"success": True})


def _is_valid_stream_url(url):
    """Check if the URL is a valid Twitch or YouTube VOD link."""
    url_lower = url.lower()
    patterns = ["twitch.tv/videos/", "twitch.tv/", "youtube.com/watch", "youtu.be/", "youtube.com/live/"]
    return any(p in url_lower for p in patterns)


def _get_platform_name(url):
    """Return 'Twitch' or 'YouTube' based on the URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    return "Twitch"


def _save_to_library(url, video_path):
    """Move a downloaded VOD to the library with a readable name."""
    # Extract VOD ID from URL for the filename
    vod_id = re.search(r'videos/(\d+)', url)
    yt_id = re.search(r'(?:v=|youtu\.be/)([\w-]+)', url)
    if vod_id:
        name = f"twitch_{vod_id.group(1)}.mp4"
    elif yt_id:
        name = f"youtube_{yt_id.group(1)}.mp4"
    else:
        name = f"vod_{os.path.basename(video_path)}"

    lib_path = os.path.join(LIBRARY_DIR, name)

    # Don't overwrite if already saved
    if os.path.exists(lib_path):
        # Already in library, delete the temp download
        if video_path != lib_path:
            os.remove(video_path)
        return lib_path

    shutil.move(video_path, lib_path)
    return lib_path


CUSTOM_PROFILES_FILE = os.path.join(BASE_DIR, "custom_profiles.json")


@app.route("/api/batch-analyze", methods=["POST"])
def batch_analyze():
    """Queue multiple URLs for sequential analysis."""
    data = request.get_json()
    urls = data.get("urls", [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    api_key = data.get("api_key", "").strip()
    game_id = data.get("game", "arc_raiders").strip()
    detection_method = data.get("detection_method", "audio_cv").strip()
    sensitivity = int(data.get("sensitivity", 50))
    detection_overrides = data.get("detection_overrides", {})

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "downloading",
        "progress": 0,
        "message": f"Processing 1 of {len(urls)}...",
        "clips": [],
        "error": None,
        "url": urls[0],
        "vod_path": None,
        "vod_duration": 0,
    }

    def run_batch():
        all_clips = []
        for i, url in enumerate(urls):
            job = jobs[job_id]
            job["message"] = f"Processing {i + 1} of {len(urls)}..."
            job["url"] = url
            try:
                _run_analysis(job_id, url, api_key, "", "", game_id, detection_method, sensitivity, detection_overrides)
                all_clips.extend(job.get("clips", []))
            except Exception as e:
                print(f"  [Batch] Error on URL {i + 1}: {e}")
        job = jobs[job_id]
        job["clips"] = all_clips
        job["status"] = "complete"
        job["progress"] = 100
        job["message"] = f"Batch complete! {len(all_clips)} clips from {len(urls)} VODs."

    thread = threading.Thread(target=run_batch, daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/clips/<job_id>/highlight-reel", methods=["POST"])
def highlight_reel(job_id):
    """Stitch all clips into one highlight reel video."""
    data = request.get_json()
    clip_ids = data.get("clip_ids", [])
    transition = data.get("transition", "none")
    resolution = data.get("resolution", "source")
    quality = data.get("quality", "medium")

    if not clip_ids:
        return jsonify({"error": "No clips selected"}), 400

    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Collect clip files in order
    clip_files = []
    for clip in job.get("clips", []):
        if clip["id"] in clip_ids:
            clip_path = os.path.join(CLIPS_DIR, clip["filename"])
            if os.path.exists(clip_path):
                clip_files.append(clip_path)

    if len(clip_files) < 1:
        return jsonify({"error": "No valid clips found"}), 400

    try:
        # Build ffmpeg concat filter
        reel_name = f"highlight_reel_{job_id}_{uuid.uuid4().hex[:6]}.mp4"
        reel_path = os.path.join(CLIPS_DIR, reel_name)

        # Create concat file
        concat_file = os.path.join(CLIPS_DIR, f"_concat_{job_id}.txt")
        with open(concat_file, "w") as f:
            for cf in clip_files:
                f.write(f"file '{cf}'\n")

        # Quality settings
        crf = {"high": "18", "medium": "23", "low": "28"}.get(quality, "23")

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file]

        # Resolution
        if resolution == "1080p":
            cmd += ["-vf", "scale=-2:1080"]
        elif resolution == "720p":
            cmd += ["-vf", "scale=-2:720"]
        elif resolution == "480p":
            cmd += ["-vf", "scale=-2:480"]

        cmd += ["-c:v", "libx264", "-crf", crf, "-c:a", "aac", "-b:a", "128k", reel_path]

        import subprocess
        result = subprocess.run(cmd, capture_output=True, timeout=600)

        # Cleanup
        if os.path.exists(concat_file):
            os.remove(concat_file)

        if result.returncode != 0:
            return jsonify({"error": "Failed to create highlight reel"}), 500

        return jsonify({"success": True, "filename": reel_name})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/custom-profiles", methods=["POST"])
def save_custom_profile():
    """Save a custom game profile."""
    data = request.get_json()
    profile_id = data.get("id", "").strip()
    name = data.get("name", "").strip()

    if not profile_id or not name:
        return jsonify({"error": "Name and ID are required"}), 400

    # Load existing custom profiles
    custom_profiles = {}
    if os.path.exists(CUSTOM_PROFILES_FILE):
        with open(CUSTOM_PROFILES_FILE) as f:
            custom_profiles = json.load(f)

    # Build the profile
    profile = {
        "name": name,
        "audio_threshold_db": float(data.get("audio_threshold_db", -8)),
        "audio_ceiling_db": float(data.get("audio_ceiling_db", -1)),
        "audio_weight": float(data.get("audio_weight", 0.7)),
        "intensity_threshold": float(data.get("intensity_threshold", 0.35)),
        "min_clip_duration": int(data.get("min_clip_duration", 20)),
        "max_clip_duration": int(data.get("max_clip_duration", 60)),
        "clip_extension": int(data.get("clip_extension", 10)),
        "pre_pad": int(data.get("pre_pad", 8)),
        "merge_gap": int(data.get("merge_gap", 8)),
        "detectors": {},
        "custom": True,
    }

    ai_prompt = data.get("ai_system_prompt", "").strip()
    if ai_prompt:
        profile["ai_system_prompt"] = ai_prompt
        profile["ai_user_prompt"] = f"Analyze this {name} gameplay frame. Is this an exciting moment?"

    custom_profiles[profile_id] = profile

    with open(CUSTOM_PROFILES_FILE, "w") as f:
        json.dump(custom_profiles, f, indent=2)

    return jsonify({"success": True, "id": profile_id})


@app.route("/api/custom-profiles")
def list_custom_profiles():
    """List all custom game profiles."""
    if not os.path.exists(CUSTOM_PROFILES_FILE):
        return jsonify({"profiles": {}})
    with open(CUSTOM_PROFILES_FILE) as f:
        return jsonify({"profiles": json.load(f)})


def _run_analysis(job_id, url, api_key="", time_start="", time_end="", game_id="arc_raiders", detection_method="audio_cv", sensitivity=50, detection_overrides=None):
    job = jobs[job_id]
    platform = _get_platform_name(url)

    def update(status, progress, message=""):
        job["status"] = status
        job["progress"] = progress
        job["message"] = message

    try:
        range_msg = ""
        if time_start or time_end:
            range_msg = f" ({time_start or '0:00'} to {time_end or 'end'})"
        update("downloading", 5, f"Downloading {platform} VOD{range_msg}...")

        video_path = clip_manager.download_vod(
            url, job_id,
            time_start=time_start or None,
            time_end=time_end or None,
            progress_callback=lambda p: update(
                "downloading", 5 + int(p * 35),
                f"Downloading{range_msg}... {int(p * 100)}%"
            )
        )

        if not video_path:
            raise Exception("Failed to download VOD. Check the URL and try again.")

        # Save to library so user doesn't have to re-download
        update("downloading", 40, "Saving to library...")
        video_path = _save_to_library(url, video_path)

        _run_analysis_on_file(job_id, video_path, api_key, time_start, time_end, game_id, detection_method, sensitivity, detection_overrides)

    except Exception as e:
        job["error"] = str(e)
        update("error", 0, str(e))


def _run_analysis_on_file(job_id, video_path, api_key="", time_start="", time_end="", game_id="arc_raiders", detection_method="audio_cv", sensitivity=50, detection_overrides=None):
    """Run analysis on a local video file (from library or download)."""
    job = jobs[job_id]

    def update(status, progress, message=""):
        job["status"] = status
        job["progress"] = progress
        job["message"] = message

    # Sensitivity maps 0-100 to a threshold multiplier:
    # 0=very selective (threshold*1.6), 50=default (threshold*1.0), 100=catch everything (threshold*0.3)
    sensitivity_multiplier = 1.6 - (sensitivity / 100) * 1.3

    try:
        job["vod_path"] = video_path
        job["vod_duration"] = clip_manager.get_vod_duration(video_path)

        def _apply_sensitivity(det):
            """Apply sensitivity multiplier to a detector's thresholds."""
            if hasattr(det, 'profile'):
                det.profile = dict(det.profile)
                original = det.profile.get("intensity_threshold", 0.40)
                det.profile["intensity_threshold"] = max(0.05, original * sensitivity_multiplier)
                # Scale audio threshold with sensitivity too
                # Higher sensitivity = lower audio threshold (catch more sounds)
                audio_thresh = det.profile.get("audio_threshold_db", -15)
                audio_adjust = (sensitivity / 100 - 0.5) * 8
                det.profile["audio_threshold_db"] = audio_thresh - audio_adjust
            if hasattr(det, 'intensity_threshold'):
                det.intensity_threshold = max(0.05, det.intensity_threshold * sensitivity_multiplier)
            if hasattr(det, 'threshold_db') and hasattr(det, 'profile'):
                det.threshold_db = det.profile.get("audio_threshold_db", -15)
            return det

        def _apply_overrides(det):
            """Apply user detection_overrides on top of sensitivity-adjusted values."""
            if not detection_overrides:
                return det
            ov = detection_overrides
            if hasattr(det, 'profile'):
                det.profile = dict(det.profile)
                for key in ("intensity_threshold", "audio_weight", "audio_threshold_db",
                            "merge_gap", "min_clip_duration", "max_clip_duration",
                            "fallback_threshold_ratio", "window_seconds",
                            "brightness_threshold"):
                    if key in ov:
                        det.profile[key] = ov[key]
                        print(f"  [Override] {key} = {ov[key]}")
                # Sync intensity_threshold to the detector attribute
                if "intensity_threshold" in ov and hasattr(det, 'intensity_threshold'):
                    det.intensity_threshold = ov["intensity_threshold"]
            if hasattr(det, 'sample_fps') and "sample_fps" in ov:
                det.sample_fps = ov["sample_fps"]
                print(f"  [Override] sample_fps = {ov['sample_fps']}")
            # peak_weight and menu_suppress are applied in the detector itself
            if hasattr(det, 'profile'):
                if "peak_weight" in ov:
                    det.profile["peak_weight"] = ov["peak_weight"]
                    print(f"  [Override] peak_weight = {ov['peak_weight']}")
                if "menu_suppress" in ov:
                    det.profile["menu_suppress"] = ov["menu_suppress"]
                    print(f"  [Override] menu_suppress = {ov['menu_suppress']}")
            return det

        if detection_method == "ai_vision" and api_key:
            update("analyzing", 42, "AI is watching your gameplay...")
            try:
                analyzer = GrokVisionAnalyzer(api_key, game_id=game_id)
                highlights = analyzer.analyze_frames(
                    video_path,
                    sample_interval_sec=8,
                    progress_callback=lambda p: update(
                        "analyzing", 42 + int(p * 38),
                        f"AI analyzing frames... {int(p * 100)}%"
                    )
                )
            except Exception as ai_err:
                error_msg = str(ai_err)
                print(f"  [AI] Fatal error: {error_msg}")
                job["error"] = f"AI analysis failed: {error_msg}"
                update("error", 0, f"AI error: {error_msg}")
                return
        elif detection_method == "ai_vision" and not api_key:
            job["error"] = "AI Vision requires a Grok API key. Enter your key in the API Key field."
            update("error", 0, "AI Vision requires a Grok API key")
            return
        elif detection_method == "audio_only":
            update("analyzing", 42, "Listening for combat audio...")
            detector = _apply_overrides(_apply_sensitivity(AudioDetector(game_id=game_id)))
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Analyzing audio... {int(p * 100)}%"
                )
            )
        elif detection_method == "cv_only":
            update("analyzing", 42, "Scanning video frames...")
            detector = _apply_overrides(_apply_sensitivity(GameDetector(game_id=game_id)))
            # Override audio_weight to 0 for CV-only mode
            detector.profile = dict(detector.profile)
            detector.profile["audio_weight"] = 0
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Scanning frames... {int(p * 100)}%"
                )
            )
        elif detection_method == "motion":
            update("analyzing", 42, "Detecting motion energy...")
            detector = _apply_overrides(_apply_sensitivity(MotionDetector(game_id=game_id)))
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Analyzing motion... {int(p * 100)}%"
                )
            )
        elif detection_method == "scene_change":
            update("analyzing", 42, "Detecting scene changes...")
            detector = _apply_overrides(_apply_sensitivity(SceneChangeDetector(game_id=game_id)))
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Analyzing scene changes... {int(p * 100)}%"
                )
            )
        elif detection_method == "hybrid":
            update("analyzing", 42, "Running hybrid analysis (audio + motion + scene)...")
            detector = _apply_overrides(_apply_sensitivity(HybridDetector(game_id=game_id)))
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Hybrid scanning... {int(p * 100)}%"
                )
            )
        elif detection_method == "roboflow_workflow":
            if not api_key:
                job["error"] = "Roboflow Workflow requires a Roboflow API key. Enter your key in the API Key field."
                update("error", 0, "Roboflow Workflow requires a Roboflow API key")
                return
            update("analyzing", 42, "Running Roboflow AI workflow...")
            try:
                analyzer = RoboflowWorkflowAnalyzer(
                    api_key=api_key,
                    game_id=game_id,
                    workspace="beanies-workspace",
                    workflow="detect-and-classify-3",
                )
                highlights = analyzer.analyze_video(
                    video_path,
                    progress_callback=lambda p: update(
                        "analyzing", 42 + int(p * 38),
                        f"Roboflow analyzing... {int(p * 100)}%"
                    )
                )
            except Exception as rf_err:
                error_msg = str(rf_err)
                print(f"  [Roboflow] Fatal error: {error_msg}")
                job["error"] = f"Roboflow analysis failed: {error_msg}"
                update("error", 0, f"Roboflow error: {error_msg}")
                return
        elif detection_method == "roboflow_model":
            if not api_key:
                job["error"] = "Roboflow Model requires a Roboflow API key. Enter your key in the API Key field."
                update("error", 0, "Roboflow Model requires a Roboflow API key")
                return
            update("analyzing", 42, "Running Roboflow model inference...")
            try:
                analyzer = RoboflowModelAnalyzer(
                    api_key=api_key,
                    game_id=game_id,
                )
                highlights = analyzer.analyze_video(
                    video_path,
                    progress_callback=lambda p: update(
                        "analyzing", 42 + int(p * 38),
                        f"Roboflow model analyzing... {int(p * 100)}%"
                    )
                )
            except Exception as rf_err:
                error_msg = str(rf_err)
                print(f"  [RoboflowModel] Fatal error: {error_msg}")
                job["error"] = f"Roboflow model analysis failed: {error_msg}"
                update("error", 0, f"Roboflow model error: {error_msg}")
                return
        elif detection_method in ("yolo_local", "arc_cv_pipeline"):
            # Map sensitivity slider to scoring version:
            # 0-19: v1_strict (fewest clips, highest quality)
            # 20-39: v5_combat_only (only confirmed fights)
            # 40-59: v3_temporal (DEFAULT — detects changes between frames)
            # 60-79: v2_balanced (good balance)
            # 80-100: v4_aggressive (most clips, catches everything)
            if sensitivity < 20:
                cv_version = "v1_strict"
            elif sensitivity < 40:
                cv_version = "v5_combat_only"
            elif sensitivity < 60:
                cv_version = "v3_temporal"
            elif sensitivity < 80:
                cv_version = "v2_balanced"
            else:
                cv_version = "v4_aggressive"

            update("analyzing", 42, f"Running CV pipeline ({cv_version})...")
            try:
                analyzer = ArcClipDetectorAdapter(
                    game_id=game_id,
                    scoring_version=cv_version,
                    detection_overrides=detection_overrides,
                )
                highlights = analyzer.analyze_video(
                    video_path,
                    progress_callback=lambda p: update(
                        "analyzing", 42 + int(p * 38),
                        f"CV analyzing ({cv_version})... {int(p * 100)}%"
                    )
                )
            except Exception as cv_err:
                error_msg = str(cv_err)
                print(f"  [CVPipeline] Fatal error: {error_msg}")
                job["error"] = f"CV pipeline failed: {error_msg}"
                update("error", 0, f"CV error: {error_msg}")
                return
        elif detection_method == "chat_spikes":
            update("analyzing", 42, "Downloading Twitch chat data...")
            from analysis.chat_detector import ChatSpikeDetector
            detector = _apply_overrides(_apply_sensitivity(ChatSpikeDetector(game_id=game_id)))
            # Get the URL for chat data
            vod_url = job.get("url", "")
            highlights = detector.analyze_chat(
                vod_url, video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Analyzing chat activity... {int(p * 100)}%"
                )
            )
        else:
            # Default: audio_cv (combined)
            update("analyzing", 42, "Analyzing audio + video...")
            detector = _apply_overrides(_apply_sensitivity(GameDetector(game_id=game_id)))
            highlights = detector.analyze_video(
                video_path,
                progress_callback=lambda p: update(
                    "analyzing", 42 + int(p * 38),
                    f"Scanning audio + video... {int(p * 100)}%"
                )
            )

        if not highlights:
            update("complete", 100, "Analysis complete - no highlights found")
            job["clips"] = []
            job["created_at"] = datetime.now().isoformat()
            _save_session(job_id)
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
        job["created_at"] = datetime.now().isoformat()
        update("complete", 100, f"Done! Found {len(clips)} highlight clips")
        _save_session(job_id)

    except Exception as e:
        job["error"] = str(e)
        update("error", 0, str(e))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
