import cv2
import math
import numpy as np

from analysis.game_profiles import get_profile


class MotionDetector:
    """
    Detects exciting moments using pure motion energy analysis.
    No color detection, no audio — only measures how much the screen
    is changing between frames.

    Combat, explosions, fast camera movement, and player action all
    produce high frame-to-frame differences. Menus and idle gameplay
    produce very little motion.
    """

    def __init__(self, game_id="arc_raiders", sample_fps=4):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.intensity_threshold = self.profile.get("intensity_threshold", 0.35)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze video using frame-to-frame motion energy.

        Returns:
            List of highlight dicts with timestamp, duration, label, confidence.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        # NaN-safe fps fallback — default OpenCV returns NaN on some codecs,
        # which is truthy and slips past `if fps > 0`.
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or math.isnan(fps) or fps <= 0:
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if total_frames > 0 else 0

        frame_interval = max(1, int(fps / max(1, self.sample_fps)))
        frames_to_analyze = total_frames // frame_interval if frame_interval > 0 else 0

        scores = []
        prev_gray = None
        prev_prev_gray = None
        frame_idx = 0
        analyzed = 0

        print(f"  [Motion] Analyzing {duration:.0f}s video at {self.sample_fps} fps sample rate...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Slight blur to reduce noise
                gray = cv2.GaussianBlur(gray, (5, 5), 0)

                motion_score = 0.0
                label = "Idle"

                if prev_gray is not None:
                    # Basic frame difference
                    diff = cv2.absdiff(gray, prev_gray)
                    motion_energy = np.mean(diff) / 255.0

                    # Detect "shake" — high variance in the diff means
                    # the whole frame is shifting (camera shake, explosions)
                    diff_std = np.std(diff) / 255.0

                    # Acceleration: compare current motion to previous motion
                    accel_bonus = 0.0
                    if prev_prev_gray is not None:
                        prev_diff = cv2.absdiff(prev_gray, prev_prev_gray)
                        prev_energy = np.mean(prev_diff) / 255.0
                        # Sudden increase in motion = action start
                        if motion_energy > prev_energy * 1.5 and motion_energy > 0.02:
                            accel_bonus = min((motion_energy - prev_energy) * 5.0, 0.3)

                    # Combine signals
                    # motion_energy: raw pixel change (0-1 range but usually 0-0.15)
                    # diff_std: shake/explosion indicator
                    # accel_bonus: sudden motion increase
                    raw_score = (motion_energy * 8.0) + (diff_std * 4.0) + accel_bonus
                    motion_score = min(raw_score, 1.0)

                    # Classify
                    if motion_score >= 0.7:
                        label = "Intense Action"
                    elif motion_score >= 0.45:
                        label = "Combat Movement"
                    elif motion_score >= 0.25:
                        label = "Active Movement"
                    else:
                        label = "Idle"

                scores.append({
                    "score": motion_score,
                    "label": label,
                    "timestamp": timestamp,
                })

                if motion_score >= self.intensity_threshold * 0.5:
                    mins = int(timestamp) // 60
                    secs = int(timestamp) % 60
                    print(f"  [Motion] {mins}:{secs:02d} - score:{motion_score:.3f} - {label}")

                prev_prev_gray = prev_gray
                prev_gray = gray
                analyzed += 1

                if progress_callback and analyzed % 20 == 0:
                    progress_callback(analyzed / max(frames_to_analyze, 1))

            frame_idx += 1

        cap.release()

        if progress_callback:
            progress_callback(1.0)

        top = sorted(scores, key=lambda s: s["score"], reverse=True)[:5]
        print(f"  [Motion] Analyzed {analyzed} frames over {duration:.0f}s")
        score_strs = [f'{s["score"]:.3f}@{int(s["timestamp"])}s' for s in top]
        print(f"  [Motion] Top: {score_strs}")

        highlights = self._find_highlights(scores, duration)
        print(f"  [Motion] Found {len(highlights)} highlights")
        for h in highlights:
            print(f"  [Motion]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s)")

        return highlights

    def _find_highlights(self, scores, duration):
        """Group high-motion periods into highlights using sliding window."""
        if not scores:
            return []

        window_size = 3  # seconds

        # Sliding window average
        window_scores = []
        window_frames = max(1, int(window_size * self.sample_fps))

        for i in range(len(scores)):
            window = scores[max(0, i - window_frames):i + 1]
            avg_score = sum(s["score"] for s in window) / len(window)
            peak_label = max(window, key=lambda s: s["score"])["label"]
            window_scores.append({
                "score": avg_score,
                "label": peak_label,
                "timestamp": scores[i]["timestamp"],
            })

        # Find segments above threshold
        above = [s for s in window_scores if s["score"] >= self.intensity_threshold]

        if not above:
            # Fallback to top moments
            sorted_scores = sorted(window_scores, key=lambda s: s["score"], reverse=True)
            fallback_threshold = self.intensity_threshold * 0.5
            above = [s for s in sorted_scores[:10] if s["score"] >= fallback_threshold]

        if not above:
            return []

        above.sort(key=lambda s: s["timestamp"])
        merge_gap = self.profile.get("merge_gap", 8)

        clusters = []
        current = {
            "start": above[0]["timestamp"],
            "end": above[0]["timestamp"],
            "peak_score": above[0]["score"],
            "label": above[0]["label"],
            "scores": [above[0]["score"]],
        }

        for s in above[1:]:
            if s["timestamp"] <= current["end"] + merge_gap:
                current["end"] = s["timestamp"]
                current["scores"].append(s["score"])
                if s["score"] > current["peak_score"]:
                    current["peak_score"] = s["score"]
                    current["label"] = s["label"]
            else:
                clusters.append(current)
                current = {
                    "start": s["timestamp"],
                    "end": s["timestamp"],
                    "peak_score": s["score"],
                    "label": s["label"],
                    "scores": [s["score"]],
                }
        clusters.append(current)

        highlights = []
        for c in clusters:
            raw_dur = c["end"] - c["start"]
            min_dur = self.profile.get("min_clip_duration", 20)
            max_dur = self.profile.get("max_clip_duration", 60)
            extension = self.profile.get("clip_extension", 10)
            clip_dur = max(min_dur, min(max_dur, raw_dur + extension))

            avg = sum(c["scores"]) / len(c["scores"])
            confidence = min(avg * 1.8, 1.0)

            highlights.append({
                "timestamp": c["start"],
                "duration": clip_dur,
                "pre_pad": self.profile.get("pre_pad", 8),
                "label": c["label"],
                "confidence": round(confidence, 2),
            })

        return highlights
