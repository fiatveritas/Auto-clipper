import cv2
import numpy as np
import subprocess
import json

from analysis.game_profiles import get_profile


class GameDetector:
    """
    Detects exciting moments in gameplay by analyzing video frames
    using a game-specific detection profile, with optional audio analysis.

    The detector samples frames at a configurable rate, scores each frame
    window for "action intensity", and returns timestamps above a threshold.
    Audio spikes (gunshots, explosions) boost scores at matching timestamps.
    """

    def __init__(self, game_id="arc_raiders", sample_fps=2, window_seconds=3):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.window_seconds = window_seconds
        self.intensity_threshold = self.profile["intensity_threshold"]

    def _extract_audio_levels(self, video_path, segment_duration=1.0):
        """
        Extract per-second audio loudness levels using ffmpeg.
        Returns dict mapping second -> peak_db value.
        Much more reliable than color detection for combat (gunshots are LOUD).
        """
        audio_weight = self.profile.get("audio_weight", 0)
        if audio_weight <= 0:
            return {}

        print("  [Audio] Extracting audio levels...")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-af", f"astats=metadata=1:reset={int(48000 * segment_duration)},"
                   "ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-",
            "-f", "null", "-",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  [Audio] ffmpeg failed: {e}")
            return {}

        if result.returncode != 0:
            print(f"  [Audio] ffmpeg error (rc={result.returncode})")
            return {}

        # Parse output: lines like "pts_time:123.456" and "lavfi.astats.Overall.Peak_level=-5.2"
        levels = {}
        current_time = 0.0

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("pts_time:"):
                try:
                    current_time = float(line.split(":", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("lavfi.astats.Overall.Peak_level="):
                try:
                    level = float(line.split("=", 1)[1])
                    sec = int(current_time)
                    # Keep the loudest reading per second
                    if sec not in levels or level > levels[sec]:
                        levels[sec] = level
                except (ValueError, IndexError):
                    pass

        if levels:
            loud_count = sum(1 for v in levels.values() if v >= self.profile.get("audio_threshold_db", -8))
            print(f"  [Audio] Got {len(levels)} seconds of audio, {loud_count} loud moments")
        else:
            print("  [Audio] No audio data extracted")

        return levels

    def _get_audio_score(self, timestamp, audio_levels):
        """
        Get an audio-based excitement score for a given timestamp.
        Gunshots/explosions produce sharp spikes well above ambient levels.
        """
        if not audio_levels:
            return 0.0

        sec = int(timestamp)
        level = audio_levels.get(sec)
        if level is None:
            return 0.0

        threshold_db = self.profile.get("audio_threshold_db", -8)
        ceiling_db = self.profile.get("audio_ceiling_db", -1)

        if level < threshold_db:
            return 0.0

        # Scale linearly from threshold to ceiling
        raw = (level - threshold_db) / max(ceiling_db - threshold_db, 1)
        return min(max(raw, 0.0), 1.0)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze a video file and return a list of highlight timestamps.
        Uses both visual detection and audio spike detection.

        Returns:
            List of dicts: [{"timestamp": float, "duration": float,
                             "label": str, "confidence": float}, ...]
        """
        # Extract audio levels first (fast, runs before frame analysis)
        audio_levels = self._extract_audio_levels(video_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        frame_interval = max(1, int(fps / self.sample_fps))
        frames_to_analyze = total_frames // frame_interval

        audio_weight = self.profile.get("audio_weight", 0)

        scores = []
        prev_frame_gray = None
        prev_bar_fill = None

        frame_idx = 0
        analyzed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                cv_score, label, prev_bar_fill = self._score_frame(
                    frame, prev_frame_gray, prev_bar_fill
                )

                # Audio boost: blend audio score with CV score
                # BUT: if the frame is a menu/inventory, do NOT let audio save it
                audio_score = self._get_audio_score(timestamp, audio_levels)
                if label == "Menu/Lobby":
                    # Menu frame — suppress completely regardless of audio
                    # Game sounds during menu navigation are NOT exciting
                    score = 0.0
                elif audio_weight > 0 and audio_score > 0:
                    # Weighted blend: audio can carry the score even if CV is weak
                    score = cv_score * (1.0 - audio_weight) + audio_score * audio_weight
                    if audio_score > 0.5 and label == "Highlight":
                        label = "Loud Combat"
                else:
                    score = cv_score

                scores.append({"score": score, "label": label, "timestamp": timestamp})

                if score >= self.intensity_threshold * 0.5:
                    mins = int(timestamp) // 60
                    secs = int(timestamp) % 60
                    audio_str = f" audio:{audio_score:.2f}" if audio_score > 0 else ""
                    print(f"  [CV] {mins}:{secs:02d} - score:{score:.3f} (cv:{cv_score:.3f}{audio_str}) - {label}")

                prev_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                analyzed += 1

                if progress_callback and analyzed % 20 == 0:
                    progress_callback(analyzed / max(frames_to_analyze, 1))

            frame_idx += 1

        cap.release()

        if progress_callback:
            progress_callback(1.0)

        top_scores = sorted(scores, key=lambda s: s["score"], reverse=True)[:10]
        menu_count = sum(1 for s in scores if s["label"] == "Menu/Lobby")
        zero_count = sum(1 for s in scores if s["score"] == 0.0)
        above_thresh = sum(1 for s in scores if s["score"] >= self.intensity_threshold)
        print(f"  [CV] Game: {self.profile['name']}")
        print(f"  [CV] Analyzed {analyzed} frames over {duration:.0f}s")
        print(f"  [CV] Menu-suppressed: {menu_count}/{analyzed} frames ({100*menu_count/max(analyzed,1):.1f}%)")
        print(f"  [CV] Zero-score: {zero_count}/{analyzed} | Above threshold: {above_thresh}/{analyzed}")
        if audio_levels:
            print(f"  [CV] Audio analysis: enabled (weight={audio_weight})")
        score_strs = [f'{s["score"]:.3f}@{int(s["timestamp"])}s' for s in top_scores]
        print(f"  [CV] Top scores: {score_strs}")
        print(f"  [CV] Threshold: {self.intensity_threshold}")

        highlights = self._find_highlights(scores, duration)
        print(f"  [CV] Found {len(highlights)} highlights")
        for h in highlights:
            print(f"  [CV]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s, conf:{h['confidence']})")
        return highlights

    def _is_menu_frame(self, frame, hsv, gray):
        """
        Detect if the current frame is a menu/lobby/loading screen.
        Only catch the most obvious cases to avoid suppressing real gameplay.
        Thresholds are intentionally strict — it's better to score a menu frame
        than to suppress real gameplay.
        """
        h, w = frame.shape[:2]

        # Almost completely black frame = loading screen
        mean_brightness = np.mean(gray) / 255.0
        if mean_brightness < 0.04:
            return True

        # Very uniform center with low brightness = solid menu background
        # Require BOTH low variance AND low brightness to avoid catching
        # outdoor/sky scenes which can have uniform areas but higher brightness
        center = gray[int(h * 0.2):int(h * 0.8), int(w * 0.2):int(w * 0.8)]
        std_dev = np.std(center)
        if std_dev < 10 and mean_brightness < 0.25:
            return True

        return False

    def _score_frame(self, frame, prev_gray, prev_bar_fill=None):
        """
        Score a single frame for action intensity using the game profile.
        Returns (score: float 0-1, label: str, bar_fill: float or None).
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Menu suppression: if this looks like a menu/lobby, return 0
        if self.profile.get("menu_suppress", "on") != "off" and self._is_menu_frame(frame, hsv, gray):
            return 0.0, "Menu/Lobby", prev_bar_fill

        component_scores = {}
        label_map = {}
        weights = {}
        bar_fill = prev_bar_fill

        # Process each detector from the profile
        for det_id, det in self.profile["detectors"].items():
            label_map[det_id] = det["label"]
            weights[det_id] = det["weight"]

            if det["region"] == "health_bar":
                # Health/shield bar depletion detection
                y1, y2, x1, x2 = det["bar_region"]
                bar_region = hsv[int(h * y1):int(h * y2), int(w * x1):int(w * x2)]
                bar_size = max(bar_region.shape[0] * bar_region.shape[1], 1)

                total_bar_pixels = 0
                for color in det["bar_colors"]:
                    mask = cv2.inRange(bar_region, color["lower"], color["upper"])
                    total_bar_pixels += np.count_nonzero(mask)

                current_fill = total_bar_pixels / bar_size
                bar_fill = current_fill

                if prev_bar_fill is not None:
                    drop = prev_bar_fill - current_fill
                    threshold = det.get("depletion_threshold", 0.3)
                    if drop >= threshold:
                        raw = min(drop / threshold, 1.0)
                        component_scores[det_id] = min(raw * det["multiplier"], 1.0)
                    else:
                        component_scores[det_id] = 0
                else:
                    component_scores[det_id] = 0

            elif det["region"] == "edges":
                # Edge detection (damage vignettes) — check all 4 edges
                edge_size = det.get("edge_size", 0.10)
                edges_list = [
                    hsv[0:int(h * edge_size), :],              # top
                    hsv[int(h * (1 - edge_size)):, :],         # bottom
                    hsv[:, 0:int(w * edge_size)],              # left
                    hsv[:, int(w * (1 - edge_size)):],         # right
                ]
                best = 0
                for edge in edges_list:
                    edge_pixels = max(edge.shape[0] * edge.shape[1], 1)
                    mask1 = cv2.inRange(edge, det["lower"], det["upper"])
                    density = np.count_nonzero(mask1) / edge_pixels
                    if "lower2" in det:
                        mask2 = cv2.inRange(edge, det["lower2"], det["upper2"])
                        density += np.count_nonzero(mask2) / edge_pixels
                    best = max(best, density)
                component_scores[det_id] = min(best * det["multiplier"], 1.0)

            elif det["region"] == "full":
                # Full-frame detection
                mask = cv2.inRange(hsv, det["lower"], det["upper"])
                density = np.count_nonzero(mask) / max(mask.size, 1)
                component_scores[det_id] = min(density * det["multiplier"], 1.0)

            elif isinstance(det["region"], list):
                # Region-based detection [y1, y2, x1, x2]
                y1, y2, x1, x2 = det["region"]
                region = hsv[int(h * y1):int(h * y2), int(w * x1):int(w * x2)]
                mask = cv2.inRange(region, det["lower"], det["upper"])
                density = np.count_nonzero(mask) / max(mask.size, 1)
                if "lower2" in det:
                    mask2 = cv2.inRange(region, det["lower2"], det["upper2"])
                    density += np.count_nonzero(mask2) / max(mask2.size, 1)
                component_scores[det_id] = min(density * det["multiplier"], 1.0)

        # Motion detection (scene changes = action)
        motion_weight = self.profile.get("motion_weight", 0.10)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion = np.mean(diff) / 255.0
            component_scores["motion"] = min(motion * self.profile.get("motion_multiplier", 4), 1.0)
        else:
            component_scores["motion"] = 0
        weights["motion"] = motion_weight
        label_map["motion"] = "Intense Action"

        # Brightness spike (flash from kills, explosions)
        brightness_weight = self.profile.get("brightness_weight", 0.05)
        brightness = np.mean(gray) / 255.0
        threshold = self.profile.get("brightness_threshold", 0.6)
        mult = self.profile.get("brightness_multiplier", 3)
        brightness_spike = max(0, brightness - threshold) * mult
        component_scores["brightness"] = min(brightness_spike, 1.0)
        weights["brightness"] = brightness_weight
        label_map["brightness"] = "Flash Event"

        # Weighted combination — no penalties, just straight weighted sum
        total_score = sum(component_scores.get(k, 0) * weights.get(k, 0) for k in weights)

        # Determine the dominant label
        best_component = max(component_scores, key=component_scores.get)
        label = label_map.get(best_component, "Highlight")

        return total_score, label, bar_fill

    def _find_highlights(self, scores, total_duration):
        """
        Group high-scoring frames into highlight windows using a sliding
        window approach, then merge overlapping windows.
        """
        if not scores:
            return []

        ws = self.profile.get("window_seconds", self.window_seconds)
        window_frames = int(ws * self.sample_fps)
        window_scores = []

        for i in range(len(scores)):
            window_end = min(i + window_frames, len(scores))
            window_slice = scores[i:window_end]
            avg_score = sum(s["score"] for s in window_slice) / len(window_slice)
            peak_score = max(s["score"] for s in window_slice)
            # Blend peak and average so a single strong spike isn't diluted away
            pw = self.profile.get("peak_weight", 0.6)
            blended_score = peak_score * pw + avg_score * (1.0 - pw)

            label_counts = {}
            for s in window_slice:
                label_counts[s["label"]] = label_counts.get(s["label"], 0) + s["score"]
            # Exclude Menu/Lobby from labels
            label_counts.pop("Menu/Lobby", None)
            dominant_label = max(label_counts, key=label_counts.get) if label_counts else "Highlight"

            window_scores.append({
                "start_idx": i,
                "timestamp": scores[i]["timestamp"],
                "avg_score": blended_score,
                "label": dominant_label,
            })

        peaks = [w for w in window_scores if w["avg_score"] >= self.intensity_threshold]

        # Fallback: if we found very few clips (not just zero), try to find more
        min_expected = max(1, int(total_duration / 600))  # expect ~1 clip per 10 min
        if len(peaks) < min_expected:
            sorted_windows = sorted(window_scores, key=lambda w: w["avg_score"], reverse=True)
            fallback_ratio = self.profile.get("fallback_threshold_ratio", 0.3)
            fallback_threshold = self.intensity_threshold * fallback_ratio
            max_fallback = max(5, min_expected * 2)
            fallback_peaks = [w for w in sorted_windows[:max_fallback] if w["avg_score"] >= fallback_threshold]
            # Merge original peaks with fallback (deduplicate by timestamp proximity)
            existing_times = {p["timestamp"] for p in peaks}
            for fp in fallback_peaks:
                if not any(abs(fp["timestamp"] - t) < self.profile.get("merge_gap", 8) for t in existing_times):
                    peaks.append(fp)
                    existing_times.add(fp["timestamp"])

        if not peaks:
            return []

        merged = self._merge_highlights(peaks)
        merged.sort(key=lambda h: h["timestamp"])
        return merged

    def _merge_highlights(self, peaks, merge_gap=None):
        """Merge highlights that are within merge_gap seconds of each other."""
        if not peaks:
            return []

        if merge_gap is None:
            merge_gap = self.profile.get("merge_gap", 8)
        ws = self.profile.get("window_seconds", self.window_seconds)

        peaks.sort(key=lambda p: p["timestamp"])

        merged = []
        current = {
            "timestamp": peaks[0]["timestamp"],
            "end_time": peaks[0]["timestamp"] + ws,
            "label": peaks[0]["label"],
            "confidence": peaks[0]["avg_score"],
            "peak_score": peaks[0]["avg_score"],
        }

        for peak in peaks[1:]:
            if peak["timestamp"] <= current["end_time"] + merge_gap:
                current["end_time"] = peak["timestamp"] + ws
                current["peak_score"] = max(current["peak_score"], peak["avg_score"])
                current["confidence"] = (current["confidence"] + peak["avg_score"]) / 2
                if peak["avg_score"] > current["peak_score"] * 0.9:
                    current["label"] = peak["label"]
            else:
                merged.append(self._finalize_highlight(current))
                current = {
                    "timestamp": peak["timestamp"],
                    "end_time": peak["timestamp"] + ws,
                    "label": peak["label"],
                    "confidence": peak["avg_score"],
                    "peak_score": peak["avg_score"],
                }

        merged.append(self._finalize_highlight(current))
        return merged

    def _finalize_highlight(self, highlight):
        """Convert a merged highlight window into the output format."""
        duration = highlight["end_time"] - highlight["timestamp"]
        min_dur = self.profile.get("min_clip_duration", 20)
        max_dur = self.profile.get("max_clip_duration", 60)
        extension = self.profile.get("clip_extension", 10)
        duration = max(min_dur, min(max_dur, duration + extension))

        return {
            "timestamp": highlight["timestamp"],
            "duration": duration,
            "pre_pad": self.profile.get("pre_pad", 8),
            "label": highlight["label"],
            "confidence": round(min(highlight["confidence"], 1.0), 2),
        }


# Backwards compatibility alias
ArcRaidersDetector = GameDetector
