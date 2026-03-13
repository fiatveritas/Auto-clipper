import json
import os
import re
import tempfile
import uuid
import subprocess
import time
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
        download_start_time = [None]
        # Estimate expected duration in seconds for time-based progress
        expected_duration = [None]
        if time_start or time_end:
            start_sec = _parse_time_to_seconds(time_start or "0") or 0
            end_sec = _parse_time_to_seconds(time_end) if time_end else None
            if end_sec is not None:
                expected_duration[0] = end_sec - start_sec

        def progress_hook(d):
            if progress_callback and d["status"] == "downloading":
                if download_start_time[0] is None:
                    download_start_time[0] = time.time()

                pct = None

                # Method 1: total bytes known
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total

                # Method 2: fragment-based (used with download_ranges)
                if pct is None:
                    frag_idx = d.get("fragment_index")
                    frag_count = d.get("fragment_count")
                    if frag_idx is not None and frag_count and frag_count > 0:
                        pct = frag_idx / frag_count

                # Method 3: parse _percent_str from yt-dlp
                if pct is None:
                    pct_str = d.get("_percent_str", "").strip().rstrip("%")
                    try:
                        pct = float(pct_str) / 100
                    except (ValueError, TypeError):
                        pass

                # Method 4: estimate from elapsed time vs expected video duration
                # Twitch downloads are roughly real-time to 3x speed
                if pct is None and expected_duration[0] and download_start_time[0]:
                    elapsed = time.time() - download_start_time[0]
                    # Assume download speed is ~2x real-time on average
                    estimated_total_time = expected_duration[0] / 2.0
                    if estimated_total_time > 0:
                        pct = min(elapsed / estimated_total_time, 0.95)

                # Method 5: check downloaded file size growth
                if pct is None and os.path.exists(output_path):
                    try:
                        file_size = os.path.getsize(output_path)
                        # Rough estimate: 720p Twitch is ~2-4 MB/s, use 3 MB/s
                        if expected_duration[0]:
                            est_total = expected_duration[0] * 3 * 1024 * 1024
                            pct = min(file_size / est_total, 0.95)
                    except OSError:
                        pass

                if pct is not None and pct - last_progress[0] >= 0.01:
                    last_progress[0] = pct
                    progress_callback(min(pct, 0.99))

            elif progress_callback and d["status"] == "finished":
                progress_callback(1.0)

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
                None, [(start_sec, end_sec)]
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

    def edit_clip(self, clip_path, job_id, clip_id, crop=None, speed=1.0,
                  brightness=0.0, contrast=1.0, volume=1.0):
        """
        Export a clip with crop, speed, and filter adjustments.

        Args:
            clip_path: Path to the source clip file
            job_id: Job identifier
            clip_id: Clip identifier
            crop: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios, or None
            speed: Playback speed multiplier (0.25-4.0)
            brightness: -1.0 to 1.0
            contrast: 0.5 to 2.0
            volume: 0.0 to 3.0

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        filename = f"{job_id}_{clip_id}_edit.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Get source dimensions for crop
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            clip_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if probe.returncode != 0:
            return None
        src_w, src_h = [int(x) for x in probe.stdout.strip().split(",")]

        # Build video filter chain
        vfilters = []

        # Crop
        if crop:
            cx = int(crop["x"] * src_w)
            cy = int(crop["y"] * src_h)
            cw = int(crop["w"] * src_w)
            ch = int(crop["h"] * src_h)
            # Ensure even dimensions for h264
            cw = cw - (cw % 2)
            ch = ch - (ch % 2)
            if cw > 0 and ch > 0:
                vfilters.append(f"crop={cw}:{ch}:{cx}:{cy}")

        # Speed
        speed = max(0.25, min(4.0, speed))
        if speed != 1.0:
            vfilters.append(f"setpts={1.0/speed}*PTS")

        # Brightness and contrast (eq filter)
        brightness = max(-1.0, min(1.0, brightness))
        contrast = max(0.5, min(2.0, contrast))
        if brightness != 0.0 or contrast != 1.0:
            vfilters.append(f"eq=brightness={brightness}:contrast={contrast}")

        # Ensure even output dimensions
        vfilters.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")

        # Build audio filter chain
        afilters = []
        volume = max(0.0, min(3.0, volume))
        if volume != 1.0:
            afilters.append(f"volume={volume}")
        if speed != 1.0:
            afilters.append(f"atempo={speed}")

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
        ]

        vf_str = ",".join(vfilters) if vfilters else None
        af_str = ",".join(afilters) if afilters else None

        if vf_str:
            cmd += ["-vf", vf_str]
        if af_str:
            cmd += ["-af", af_str]

        cmd += [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [Edit] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def delete_clip(self, clip):
        """Delete a clip and its thumbnail."""
        clip_path = os.path.join(self.clips_dir, clip["filename"])
        if os.path.exists(clip_path):
            os.remove(clip_path)

        if clip.get("thumbnail"):
            thumb_path = os.path.join(self.thumbnails_dir, clip["thumbnail"])
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

    def make_tiktok(self, clip_path, job_id, clip_id, gameplay_region, webcam_region, layout="stacked"):
        """
        Convert a clip to TikTok vertical format (1080x1920) by cropping
        gameplay and webcam regions and compositing them.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            gameplay_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios
            webcam_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios, or None
            layout: "stacked" (gameplay top, webcam bottom) or "gameplay_only"

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        # Get source video dimensions
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            clip_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if probe.returncode != 0:
            return None
        src_w, src_h = [int(x) for x in probe.stdout.strip().split(",")]

        out_w, out_h = 1080, 1920
        filename = f"{job_id}_{clip_id}_tiktok.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Convert ratio-based regions to pixel coordinates
        gx = int(gameplay_region["x"] * src_w)
        gy = int(gameplay_region["y"] * src_h)
        gw = int(gameplay_region["w"] * src_w)
        gh = int(gameplay_region["h"] * src_h)

        if webcam_region and layout == "stacked":
            wx = int(webcam_region["x"] * src_w)
            wy = int(webcam_region["y"] * src_h)
            ww = int(webcam_region["w"] * src_w)
            wh = int(webcam_region["h"] * src_h)

            # Gameplay takes top 70%, webcam takes bottom 30%
            gameplay_h = int(out_h * 0.70)
            webcam_h = out_h - gameplay_h

            filter_complex = (
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={out_w}:{gameplay_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{gameplay_h}:(ow-iw)/2:(oh-ih)/2:color=black[top];"
                f"[0:v]crop={ww}:{wh}:{wx}:{wy},scale={out_w}:{webcam_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{webcam_h}:(ow-iw)/2:(oh-ih)/2:color=black[bot];"
                f"[top][bot]vstack=inputs=2[out]"
            )
        else:
            # Gameplay only - fill the whole vertical frame
            filter_complex = (
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=black[out]"
            )

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [TikTok] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def make_youtube_short(self, clip_path, job_id, clip_id, gameplay_region, webcam_region, layout="stacked"):
        """
        Convert a clip to YouTube Shorts vertical format (1080x1920) with an 80px
        black safe zone at the top for the YT UI overlay.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            gameplay_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios
            webcam_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios, or None
            layout: "stacked" (gameplay top, webcam bottom) or "gameplay_only"

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        # Get source video dimensions
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            clip_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if probe.returncode != 0:
            return None
        src_w, src_h = [int(x) for x in probe.stdout.strip().split(",")]

        out_w, out_h = 1080, 1920
        safe_zone = 80  # pixels reserved at top for YT UI
        content_h = out_h - safe_zone
        filename = f"{job_id}_{clip_id}_ytshort.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Convert ratio-based regions to pixel coordinates
        gx = int(gameplay_region["x"] * src_w)
        gy = int(gameplay_region["y"] * src_h)
        gw = int(gameplay_region["w"] * src_w)
        gh = int(gameplay_region["h"] * src_h)

        if webcam_region and layout == "stacked":
            wx = int(webcam_region["x"] * src_w)
            wy = int(webcam_region["y"] * src_h)
            ww = int(webcam_region["w"] * src_w)
            wh = int(webcam_region["h"] * src_h)

            # Gameplay takes top 70% of content area, webcam takes bottom 30%
            gameplay_h = int(content_h * 0.70)
            webcam_h = content_h - gameplay_h

            filter_complex = (
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={out_w}:{gameplay_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{gameplay_h}:(ow-iw)/2:(oh-ih)/2:color=black[top];"
                f"[0:v]crop={ww}:{wh}:{wx}:{wy},scale={out_w}:{webcam_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{webcam_h}:(ow-iw)/2:(oh-ih)/2:color=black[bot];"
                f"[top][bot]vstack=inputs=2[content];"
                f"color=black:{out_w}:{safe_zone}:d=1[safezone];"
                f"[safezone][content]vstack=inputs=2,"
                f"pad=ceil(iw/2)*2:ceil(ih/2)*2[out]"
            )
        else:
            # Gameplay only - fill the content area below the safe zone
            filter_complex = (
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={out_w}:{content_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{content_h}:(ow-iw)/2:(oh-ih)/2:color=black[content];"
                f"color=black:{out_w}:{safe_zone}:d=1[safezone];"
                f"[safezone][content]vstack=inputs=2,"
                f"pad=ceil(iw/2)*2:ceil(ih/2)*2[out]"
            )

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [YTShort] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def make_gif(self, clip_path, job_id, clip_id, start_offset=0, duration=10, fps=15, width=480):
        """
        Convert a clip (or portion of it) to a high-quality GIF using
        ffmpeg palettegen/paletteuse two-pass approach.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            start_offset: Start offset in seconds within the clip
            duration: Duration in seconds for the GIF
            fps: Frames per second for the GIF
            width: Output width in pixels (height auto-scaled)

        Returns:
            {"filename": str, "size": int} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        filename = f"{job_id}_{clip_id}.gif"
        out_path = os.path.join(self.clips_dir, filename)

        palette_path = os.path.join(self.clips_dir, f"{job_id}_{clip_id}_palette.png")

        filters = f"fps={fps},scale={width}:-1:flags=lanczos"

        # Pass 1: generate palette
        palette_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_offset),
            "-t", str(duration),
            "-i", clip_path,
            "-vf", f"{filters},palettegen=stats_mode=diff",
            palette_path,
        ]
        result = subprocess.run(palette_cmd, capture_output=True, timeout=120)
        if result.returncode != 0 or not os.path.exists(palette_path):
            print(f"  [GIF] palette generation error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        # Pass 2: generate GIF using palette
        gif_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_offset),
            "-t", str(duration),
            "-i", clip_path,
            "-i", palette_path,
            "-filter_complex", f"[0:v]{filters}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
            out_path,
        ]
        result = subprocess.run(gif_cmd, capture_output=True, timeout=120)

        # Clean up palette file
        if os.path.exists(palette_path):
            os.remove(palette_path)

        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [GIF] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        file_size = os.path.getsize(out_path)
        return {"filename": filename, "size": file_size}

    def add_watermark(self, clip_path, job_id, clip_id, watermark_path, position="bottom-right", opacity=0.7, scale=0.15):
        """
        Overlay a PNG watermark image on a clip.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            watermark_path: Path to the PNG watermark image
            position: One of "top-left", "top-right", "bottom-left", "bottom-right", "center"
            opacity: Watermark opacity (0.0 to 1.0)
            scale: Watermark size as a fraction of the video width

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path) or not os.path.exists(watermark_path):
            return None

        filename = f"{job_id}_{clip_id}_wm.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Position mapping: 10px margin from edges
        margin = 10
        position_map = {
            "top-left": f"x={margin}:y={margin}",
            "top-right": f"x=main_w-overlay_w-{margin}:y={margin}",
            "bottom-left": f"x={margin}:y=main_h-overlay_h-{margin}",
            "bottom-right": f"x=main_w-overlay_w-{margin}:y=main_h-overlay_h-{margin}",
            "center": "x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2",
        }
        pos_str = position_map.get(position, position_map["bottom-right"])

        filter_complex = (
            f"[1:v]scale=iw*{scale}/1:ih*{scale}/1,"
            f"format=rgba,colorchannelmixer=aa={opacity}[wm];"
            f"[0:v][wm]overlay={pos_str},"
            f"pad=ceil(iw/2)*2:ceil(ih/2)*2[out]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-i", watermark_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [Watermark] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def split_clip(self, clip_path, job_id, clip_id, split_time):
        """
        Split a clip into two parts at the given timestamp.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            split_time: Time in seconds at which to split the clip

        Returns:
            {"part1": {"filename": str, "duration": float},
             "part2": {"filename": str, "duration": float}} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        filename1 = f"{job_id}_{clip_id}_part1.mp4"
        filename2 = f"{job_id}_{clip_id}_part2.mp4"
        out_path1 = os.path.join(self.clips_dir, filename1)
        out_path2 = os.path.join(self.clips_dir, filename2)

        # Part 1: from start to split_time
        cmd1 = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-t", str(split_time),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags", "+faststart",
            out_path1,
        ]
        result1 = subprocess.run(cmd1, capture_output=True, timeout=180)
        if result1.returncode != 0 or not os.path.exists(out_path1):
            print(f"  [Split] ffmpeg error (part1): {result1.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        # Part 2: from split_time to end
        cmd2 = [
            "ffmpeg", "-y",
            "-ss", str(split_time),
            "-i", clip_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags", "+faststart",
            out_path2,
        ]
        result2 = subprocess.run(cmd2, capture_output=True, timeout=180)
        if result2.returncode != 0 or not os.path.exists(out_path2):
            print(f"  [Split] ffmpeg error (part2): {result2.stderr.decode('utf-8', errors='replace')[-300:]}")
            # Clean up part1 if part2 failed
            if os.path.exists(out_path1):
                os.remove(out_path1)
            return None

        dur1 = self.get_vod_duration(out_path1)
        dur2 = self.get_vod_duration(out_path2)

        return {
            "part1": {"filename": filename1, "duration": round(dur1, 1)},
            "part2": {"filename": filename2, "duration": round(dur2, 1)},
        }

    def extend_clip(self, vod_path, job_id, clip_id, new_start, new_end):
        """
        Re-extract a clip from the VOD with extended boundaries.

        Args:
            vod_path: Path to the downloaded VOD
            job_id: Job identifier
            clip_id: Clip identifier
            new_start: New start time in seconds
            new_end: New end time in seconds

        Returns:
            {"filename": str, "thumbnail": str or None, "start_time": float,
             "end_time": float, "duration": float, "timestamp_display": str} or None on failure
        """
        duration = new_end - new_start
        if duration <= 0 or duration > 300:
            return None

        filename = f"{job_id}_{clip_id}_ext.mp4"
        clip_path = os.path.join(self.clips_dir, filename)
        thumb_filename = f"{job_id}_{clip_id}_ext.jpg"
        thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(new_start),
            "-i", vod_path,
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
            print(f"  [Extend] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        # Thumbnail
        thumb_cmd = [
            "ffmpeg", "-y",
            "-ss", str(new_start + duration / 2),
            "-i", vod_path,
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

    def merge_clips(self, clip_paths, job_id, transition="none", transition_duration=0.5):
        """
        Merge multiple clips into a single highlight reel.

        Args:
            clip_paths: List of paths to clip files
            job_id: Job identifier
            transition: "none", "fade", or "wipe"
            transition_duration: Duration of transitions in seconds

        Returns:
            {"filename": str, "duration": float} or None on failure
        """
        if not clip_paths or len(clip_paths) < 2:
            return None

        for p in clip_paths:
            if not os.path.exists(p):
                return None

        filename = f"{job_id}_merged.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        if transition == "none":
            # Use concat demuxer for lossless-ish concatenation
            concat_file = os.path.join(self.clips_dir, f"{job_id}_concat.txt")
            try:
                with open(concat_file, "w") as f:
                    for p in clip_paths:
                        f.write(f"file '{p}'\n")

                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_file,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-movflags", "+faststart",
                    out_path,
                ]

                result = subprocess.run(cmd, capture_output=True, timeout=600)
                if result.returncode != 0 or not os.path.exists(out_path):
                    print(f"  [Merge] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
                    return None
            finally:
                if os.path.exists(concat_file):
                    os.remove(concat_file)
        else:
            # Use xfade for fade/wipe transitions
            # Get durations of each clip for calculating xfade offsets
            durations = []
            for p in clip_paths:
                dur = self.get_vod_duration(p)
                if dur <= 0:
                    return None
                durations.append(dur)

            # Build the xfade filter chain
            xfade_type = "fade" if transition == "fade" else "wipeleft"
            td = float(transition_duration)

            # Start by building inputs
            inputs = []
            for p in clip_paths:
                inputs += ["-i", p]

            # Build the filter graph chaining xfade filters
            filter_parts = []
            # First pair
            offset = durations[0] - td
            filter_parts.append(
                f"[0:v][1:v]xfade=transition={xfade_type}:duration={td}:offset={offset}[v01]"
            )
            # Audio crossfade for first pair
            filter_parts.append(
                f"[0:a][1:a]acrossfade=d={td}[a01]"
            )

            prev_v = "v01"
            prev_a = "a01"
            cumulative_offset = offset + durations[1] - td

            for i in range(2, len(clip_paths)):
                cur_v = f"v{i:02d}"
                cur_a = f"a{i:02d}"
                filter_parts.append(
                    f"[{prev_v}][{i}:v]xfade=transition={xfade_type}:duration={td}:offset={cumulative_offset}[{cur_v}]"
                )
                filter_parts.append(
                    f"[{prev_a}][{i}:a]acrossfade=d={td}[{cur_a}]"
                )
                prev_v = cur_v
                prev_a = cur_a
                cumulative_offset += durations[i] - td

            # Ensure even dimensions
            filter_parts.append(
                f"[{prev_v}]pad=ceil(iw/2)*2:ceil(ih/2)*2[outv]"
            )

            filter_complex = ";".join(filter_parts)

            cmd = inputs[:]
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", f"[{prev_a}]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                out_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)
            if result.returncode != 0 or not os.path.exists(out_path):
                print(f"  [Merge] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
                return None

        merged_duration = self.get_vod_duration(out_path)
        return {"filename": filename, "duration": round(merged_duration, 1)}

    def add_captions(self, clip_path, job_id, clip_id, text, position="bottom", font_size=48, color="white", bg_opacity=0.5):
        """
        Burn text captions into a video using the ffmpeg drawtext filter.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            text: Caption text to burn in
            position: "top", "center", or "bottom"
            font_size: Font size in pixels
            color: Font color name (e.g. "white", "yellow")
            bg_opacity: Background box opacity (0.0 to 1.0)

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        filename = f"{job_id}_{clip_id}_captioned.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Escape special characters for drawtext
        escaped_text = text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "%%")

        # Position mapping
        if position == "top":
            y_expr = "th*0.05"
        elif position == "center":
            y_expr = "(h-text_h)/2"
        else:  # bottom
            y_expr = "h-text_h-th*0.05"

        bg_color = f"black@{bg_opacity}"

        drawtext_filter = (
            f"drawtext=text='{escaped_text}':fontsize={font_size}:fontcolor={color}"
            f":x=(w-text_w)/2:y={y_expr}"
            f":box=1:boxcolor={bg_color}:boxborderw=10"
        )

        vf = f"{drawtext_filter},pad=ceil(iw/2)*2:ceil(ih/2)*2"

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [Captions] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def add_zoom_pan(self, clip_path, job_id, clip_id, zoom_start=1.0, zoom_end=1.3, pan_x=0, pan_y=0):
        """
        Apply a Ken Burns style zoom/pan effect to a clip.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            zoom_start: Starting zoom level (1.0 = no zoom)
            zoom_end: Ending zoom level
            pan_x: Horizontal pan offset in pixels (positive = right)
            pan_y: Vertical pan offset in pixels (positive = down)

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        filename = f"{job_id}_{clip_id}_zoompan.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Get source dimensions and fps
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            clip_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        if probe.returncode != 0:
            return None

        probe_data = json.loads(probe.stdout)
        stream = probe_data["streams"][0]
        src_w = int(stream["width"])
        src_h = int(stream["height"])
        # Parse frame rate (e.g. "30/1" or "30000/1001")
        fps_parts = stream["r_frame_rate"].split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])

        # Get total duration to calculate zoom increment per frame
        total_duration = self.get_vod_duration(clip_path)
        if total_duration <= 0:
            return None

        total_frames = int(total_duration * fps)
        if total_frames <= 0:
            total_frames = 1

        # zoompan filter: zoom interpolates from zoom_start to zoom_end,
        # pan_x/pan_y shift over time
        # 'on' = output number of frames per input frame, set to 1 for passthrough rate
        # 'z' = zoom expression, 'd' = duration (total frames), 'n' = current frame index
        zoom_expr = f"if(eq(on,0),{zoom_start},{zoom_start}+(in_1)*({zoom_end}-{zoom_start})/{total_frames})"
        # Simplified: use linear interpolation
        zoom_expr = f"{zoom_start}+on*{(zoom_end - zoom_start)}/{total_frames}"
        pan_x_expr = f"iw/2-(iw/zoom/2)+on*{pan_x}/{total_frames}"
        pan_y_expr = f"ih/2-(ih/zoom/2)+on*{pan_y}/{total_frames}"

        zoompan_filter = (
            f"zoompan=z='{zoom_expr}':x='{pan_x_expr}':y='{pan_y_expr}'"
            f":d=1:s={src_w}x{src_h}:fps={fps}"
        )

        vf = f"{zoompan_filter},pad=ceil(iw/2)*2:ceil(ih/2)*2"

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [ZoomPan] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def add_sound_effect(self, clip_path, job_id, clip_id, sfx_path, timestamp=0, volume=0.8):
        """
        Overlay a sound effect on the clip at a specific timestamp.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            sfx_path: Path to the sound effect audio file
            timestamp: Time in seconds at which to start the sound effect
            volume: Volume of the sound effect (0.0 to 1.0)

        Returns:
            {"filename": str} or None on failure
        """
        if not os.path.exists(clip_path) or not os.path.exists(sfx_path):
            return None

        filename = f"{job_id}_{clip_id}_sfx.mp4"
        out_path = os.path.join(self.clips_dir, filename)

        # Delay the sound effect to the desired timestamp and adjust volume,
        # then mix with the original audio
        filter_complex = (
            f"[1:a]volume={volume},adelay={int(timestamp * 1000)}|{int(timestamp * 1000)}[sfx];"
            f"[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-i", sfx_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(out_path):
            print(f"  [SFX] ffmpeg error: {result.stderr.decode('utf-8', errors='replace')[-300:]}")
            return None

        return {"filename": filename}

    def detect_volume_spikes(self, video_path, threshold_db=-10, min_gap=3):
        """
        Analyze audio for volume spikes (loud moments) using ffmpeg astats.

        Args:
            video_path: Path to the video file to analyze
            threshold_db: Volume threshold in dB; peaks above this are reported
            min_gap: Minimum gap in seconds between reported spikes

        Returns:
            List of {"timestamp": float, "volume_db": float} or None on failure
        """
        if not os.path.exists(video_path):
            return None

        # Use astats with per-frame metadata to detect volume levels
        cmd = [
            "ffprobe", "-v", "error",
            "-f", "lavfi",
            "-i", f"amovie={video_path},astats=metadata=1:reset=1",
            "-show_entries", "frame_tags=lavfi.astats.Overall.Peak_level",
            "-show_entries", "frame=pts_time",
            "-of", "json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            # Fallback: use volumedetect for overall stats and ebur128 for per-segment analysis
            # Try a simpler approach: extract audio levels at regular intervals
            cmd_fallback = [
                "ffmpeg", "-i", video_path,
                "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-",
                "-f", "null", "-",
            ]
            result_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=300)
            if result_fb.returncode != 0:
                print(f"  [VolumeSpikes] ffmpeg error: {result_fb.stderr[:300]}")
                return None

            # Parse the ametadata output
            spikes = []
            last_spike_time = -min_gap
            current_time = 0.0

            for line in result_fb.stdout.splitlines():
                line = line.strip()
                if line.startswith("frame:"):
                    # Extract pts_time if available
                    pass
                elif line.startswith("lavfi.astats.Overall.Peak_level="):
                    try:
                        level = float(line.split("=", 1)[1])
                        if level >= threshold_db and (current_time - last_spike_time) >= min_gap:
                            spikes.append({"timestamp": round(current_time, 2), "volume_db": round(level, 1)})
                            last_spike_time = current_time
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("pts_time:"):
                    try:
                        current_time = float(line.split(":", 1)[1])
                    except (ValueError, IndexError):
                        pass

            return spikes

        # Parse JSON output from ffprobe
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        spikes = []
        last_spike_time = -min_gap

        for frame in data.get("frames", []):
            pts_time = float(frame.get("pts_time", 0))
            tags = frame.get("tags", {})
            peak_str = tags.get("lavfi.astats.Overall.Peak_level", "-inf")
            try:
                peak_db = float(peak_str)
            except ValueError:
                continue

            if peak_db >= threshold_db and (pts_time - last_spike_time) >= min_gap:
                spikes.append({"timestamp": round(pts_time, 2), "volume_db": round(peak_db, 1)})
                last_spike_time = pts_time

        return spikes

    def get_smart_thumbnail(self, clip_path, job_id, clip_id, num_candidates=10):
        """
        Pick the most visually interesting frame from a clip based on contrast.

        Extracts N evenly-spaced frames, evaluates each for contrast/brightness
        using ffprobe, and picks the frame with the highest contrast.

        Args:
            clip_path: Path to the source clip
            job_id: Job identifier
            clip_id: Clip identifier
            num_candidates: Number of candidate frames to evaluate

        Returns:
            {"filename": str, "timestamp": float} or None on failure
        """
        if not os.path.exists(clip_path):
            return None

        duration = self.get_vod_duration(clip_path)
        if duration <= 0:
            return None

        # Generate candidate timestamps evenly spaced across the clip
        interval = duration / (num_candidates + 1)
        candidates = [interval * (i + 1) for i in range(num_candidates)]

        best_score = -1
        best_timestamp = candidates[0]
        best_frame_path = None

        tmp_dir = tempfile.mkdtemp(prefix="smartthumb_")

        try:
            for idx, ts in enumerate(candidates):
                frame_path = os.path.join(tmp_dir, f"frame_{idx}.jpg")

                # Extract single frame
                extract_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(ts),
                    "-i", clip_path,
                    "-frames:v", "1",
                    "-q:v", "2",
                    frame_path,
                ]
                result = subprocess.run(extract_cmd, capture_output=True, timeout=30)
                if result.returncode != 0 or not os.path.exists(frame_path):
                    continue

                # Analyze frame for contrast using ffprobe signalstats
                analyze_cmd = [
                    "ffprobe", "-v", "error",
                    "-f", "lavfi",
                    "-i", f"movie={frame_path},signalstats",
                    "-show_entries", "frame_tags=lavfi.signalstats.YMIN,lavfi.signalstats.YMAX,lavfi.signalstats.YAVG",
                    "-of", "json",
                ]
                analyze = subprocess.run(analyze_cmd, capture_output=True, text=True, timeout=30)

                if analyze.returncode != 0:
                    # Fallback: use file size as a rough proxy for visual complexity
                    score = os.path.getsize(frame_path)
                else:
                    try:
                        adata = json.loads(analyze.stdout)
                        frames = adata.get("frames", [])
                        if frames:
                            tags = frames[0].get("tags", {})
                            y_min = float(tags.get("lavfi.signalstats.YMIN", 16))
                            y_max = float(tags.get("lavfi.signalstats.YMAX", 235))
                            y_avg = float(tags.get("lavfi.signalstats.YAVG", 128))
                            # Contrast = range of luminance; prefer high contrast
                            # Also slightly prefer mid-range brightness
                            contrast = y_max - y_min
                            brightness_penalty = abs(y_avg - 128) * 0.5
                            score = contrast - brightness_penalty
                        else:
                            score = os.path.getsize(frame_path)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        score = os.path.getsize(frame_path)

                if score > best_score:
                    best_score = score
                    best_timestamp = ts
                    best_frame_path = frame_path

            if best_frame_path is None:
                return None

            # Copy best frame to thumbnails directory
            thumb_filename = f"{job_id}_{clip_id}_smart.jpg"
            thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)

            import shutil
            shutil.copy2(best_frame_path, thumb_path)

        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if not os.path.exists(thumb_path):
            return None

        return {"filename": thumb_filename, "timestamp": round(best_timestamp, 2)}

    def batch_tiktok(self, clip_paths_and_ids, job_id, gameplay_region, webcam_region, layout="stacked"):
        """
        Apply the same TikTok formatting to multiple clips.

        Args:
            clip_paths_and_ids: List of (clip_path, clip_id) tuples
            job_id: Job identifier
            gameplay_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios
            webcam_region: {"x": float, "y": float, "w": float, "h": float} as 0-1 ratios, or None
            layout: "stacked" or "gameplay_only"

        Returns:
            List of {"clip_id": str, "result": dict or None} for each input clip
        """
        results = []
        for clip_path, clip_id in clip_paths_and_ids:
            result = self.make_tiktok(clip_path, job_id, clip_id, gameplay_region, webcam_region, layout)
            results.append({"clip_id": clip_id, "result": result})
        return results

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
