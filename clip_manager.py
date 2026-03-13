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

    def download_vod(self, url, job_id, progress_callback=None):
        """Download a Twitch VOD using yt-dlp."""
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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(output_path):
            return output_path

        return None

    def extract_clips(self, video_path, highlights, job_id, progress_callback=None):
        """Extract clip segments from the downloaded video using ffmpeg."""
        clips = []

        for i, highlight in enumerate(highlights):
            clip_id = str(uuid.uuid4())[:8]
            filename = f"{job_id}_{clip_id}.mp4"
            clip_path = os.path.join(self.clips_dir, filename)
            thumb_filename = f"{job_id}_{clip_id}.jpg"
            thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)

            start_time = max(0, highlight["timestamp"] - highlight.get("pre_pad", 3))
            duration = highlight.get("duration", 15)

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

            result = subprocess.run(cmd, capture_output=True, timeout=120)

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
                "start_time": start_time,
                "duration": duration,
                "label": highlight.get("label", "Highlight"),
                "confidence": highlight.get("confidence", 0.5),
                "timestamp_display": _format_time(start_time),
            }
            clips.append(clip_info)

            if progress_callback:
                progress_callback((i + 1) / len(highlights))

        return clips

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
