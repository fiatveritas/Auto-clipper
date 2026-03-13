import os
import uuid
import subprocess
import yt_dlp


class ClipManager:
    """Handles downloading VODs, extracting clips, and managing clip files."""

    def __init__(self, clips_dir, thumbnails_dir, downloads_dir):
        self.clips_dir = clips_dir
        self.thumbnails_dir = thumbnails_dir
        self.downloads_dir = downloads_dir

    def download_vod(self, url, job_id, time_start=None, time_end=None, progress_callback=None):
        """Download a Twitch VOD using yt-dlp, optionally a time range."""
        output_path = os.path.join(self.downloads_dir, f"{job_id}.mp4")

        last_progress = [0]

        def progress_hook(d):
            if d["status"] == "downloading" and progress_callback:
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total
                    if pct - last_progress[0] >= 0.02:
                        last_progress[0] = pct
                        progress_callback(pct)

        ydl_opts = {
            "format": "best[height<=720]/best",
            "outtmpl": output_path,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }

        # Time range for partial downloads
        if time_start or time_end:
            start_sec = _parse_time_to_seconds(time_start or "0") or 0
            end_sec = _parse_time_to_seconds(time_end) if time_end else float("inf")
            if end_sec is None:
                end_sec = float("inf")
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
                None, [{"start_time": start_sec, "end_time": end_sec}]
            )
            ydl_opts["force_keyframes_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(output_path):
            return output_path

        return None

    def get_vod_path(self, job_id):
        """Get the path to a downloaded VOD if it still exists."""
        path = os.path.join(self.downloads_dir, f"{job_id}.mp4")
        return path if os.path.exists(path) else None

    def get_vod_duration(self, video_path):
        """Get the duration of a video file in seconds."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return 0

    def extract_clips(self, video_path, highlights, job_id, progress_callback=None):
        """Extract clip segments from the downloaded video using ffmpeg."""
        clips = []

        for i, highlight in enumerate(highlights):
            clip_id = str(uuid.uuid4())[:8]
            filename = f"{job_id}_{clip_id}.mp4"
            clip_path = os.path.join(self.clips_dir, filename)
            thumb_filename = f"{job_id}_{clip_id}.jpg"
            thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)

            start_time = max(0, highlight["timestamp"] - highlight.get("pre_pad", 8))
            duration = highlight.get("duration", 25)

            # Extract clip with ffmpeg
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                clip_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=180)

            if result.returncode != 0 or not os.path.exists(clip_path):
                continue

            # Generate thumbnail at the midpoint of the clip
            thumb_time = start_time + duration / 2
            thumb_cmd = [
                "ffmpeg", "-y",
                "-ss", str(thumb_time),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "5",
                thumb_path,
            ]
            subprocess.run(thumb_cmd, capture_output=True, timeout=30)

            clip_info = {
                "id": clip_id,
                "filename": filename,
                "thumbnail": thumb_filename if os.path.exists(thumb_path) else None,
                "start_time": round(start_time, 1),
                "end_time": round(start_time + duration, 1),
                "duration": round(duration, 1),
                "label": highlight.get("label", "Highlight"),
                "confidence": highlight.get("confidence", 0.5),
                "timestamp_display": _format_time(start_time),
            }
            clips.append(clip_info)

            if progress_callback:
                progress_callback((i + 1) / len(highlights))

        return clips

    def reclip(self, video_path, job_id, clip_id, new_start, new_end):
        """Re-extract a clip with new start/end times from the VOD."""
        duration = new_end - new_start
        if duration <= 0 or duration > 300:
            return None

        filename = f"{job_id}_{clip_id}_trim.mp4"
        clip_path = os.path.join(self.clips_dir, filename)
        thumb_filename = f"{job_id}_{clip_id}_trim.jpg"
        thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(new_start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            clip_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=180)
        if result.returncode != 0 or not os.path.exists(clip_path):
            return None

        # Thumbnail
        thumb_cmd = [
            "ffmpeg", "-y",
            "-ss", str(new_start + duration / 2),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "5",
            thumb_path,
        ]
        subprocess.run(thumb_cmd, capture_output=True, timeout=30)

        return {
            "filename": filename,
            "thumbnail": thumb_filename if os.path.exists(thumb_path) else None,
            "start_time": round(new_start, 1),
            "end_time": round(new_end, 1),
            "duration": round(duration, 1),
            "timestamp_display": _format_time(new_start),
        }

    def delete_clip(self, clip):
        """Delete a clip and its thumbnail."""
        clip_path = os.path.join(self.clips_dir, clip["filename"])
        if os.path.exists(clip_path):
            os.remove(clip_path)

        if clip.get("thumbnail"):
            thumb_path = os.path.join(self.thumbnails_dir, clip["thumbnail"])
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

    def cleanup_download(self, video_path):
        """Remove the downloaded VOD file."""
        if video_path and os.path.exists(video_path):
            os.remove(video_path)


def _format_time(seconds):
    """Format seconds into HH:MM:SS display string."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _parse_time_to_seconds(time_str):
    """Parse a time string like '1:30:00' or '45:00' or '90' into seconds."""
    time_str = time_str.strip()
    if not time_str or time_str == "inf":
        return None

    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])
    except (ValueError, IndexError):
        return None


def _make_download_sections(start_str, end_str):
    """Create a yt-dlp download_sections string for partial downloads."""
    start_sec = _parse_time_to_seconds(start_str)
    end_sec = _parse_time_to_seconds(end_str)

    if start_sec is not None and end_sec is not None:
        return f"*{start_sec}-{end_sec}"
    elif start_sec is not None:
        return f"*{start_sec}-inf"
    elif end_sec is not None:
        return f"*0-{end_sec}"

    return None
