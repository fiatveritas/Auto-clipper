import cv2
import numpy as np


class ArcRaidersDetector:
    """
    Detects exciting moments in Arc Raiders gameplay by analyzing video frames.

    Detection methods:
    1. Kill feed / elimination text detection (bright UI text flashes)
    2. Rapid scene changes (explosions, combat chaos)
    3. Health bar / damage indicators (red screen flashes)
    4. Crosshair / hit marker detection (bright center-screen flashes)
    5. Audio spike analysis (loud combat sounds) via frame brightness proxy
    6. HUD kill/score popup detection

    The detector samples frames at a configurable rate, scores each frame
    window for "action intensity", and returns timestamps above a threshold.
    """

    # Arc Raiders UI color ranges (HSV) for detecting game-specific elements
    # Kill feed text is typically white/bright yellow
    KILL_TEXT_LOWER = np.array([0, 0, 200])
    KILL_TEXT_UPPER = np.array([180, 50, 255])

    # Damage indicator red flash
    DAMAGE_RED_LOWER = np.array([0, 120, 100])
    DAMAGE_RED_UPPER = np.array([10, 255, 255])
    DAMAGE_RED_LOWER2 = np.array([170, 120, 100])
    DAMAGE_RED_UPPER2 = np.array([180, 255, 255])

    # Hit marker / crosshair flash (bright white center)
    HIT_MARKER_LOWER = np.array([0, 0, 230])
    HIT_MARKER_UPPER = np.array([180, 30, 255])

    # Muzzle flash / explosion orange-yellow
    EXPLOSION_LOWER = np.array([10, 100, 150])
    EXPLOSION_UPPER = np.array([35, 255, 255])

    # Arc (enemy) blue glow
    ARC_BLUE_LOWER = np.array([90, 80, 100])
    ARC_BLUE_UPPER = np.array([130, 255, 255])

    def __init__(self, sample_fps=2, window_seconds=3, intensity_threshold=0.35):
        """
        Args:
            sample_fps: Frames to analyze per second (lower = faster, less precise)
            window_seconds: Sliding window size for grouping action
            intensity_threshold: 0-1 threshold for what counts as a "highlight"
        """
        self.sample_fps = sample_fps
        self.window_seconds = window_seconds
        self.intensity_threshold = intensity_threshold

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze a video file and return a list of highlight timestamps.

        Returns:
            List of dicts: [{"timestamp": float, "duration": float,
                             "label": str, "confidence": float}, ...]
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        # Calculate frame sampling interval
        frame_interval = max(1, int(fps / self.sample_fps))
        frames_to_analyze = total_frames // frame_interval

        scores = []
        frame_timestamps = []
        prev_frame_gray = None

        frame_idx = 0
        analyzed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                score, label = self._score_frame(frame, prev_frame_gray)

                scores.append({"score": score, "label": label, "timestamp": timestamp})
                frame_timestamps.append(timestamp)

                prev_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                analyzed += 1

                if progress_callback and analyzed % 20 == 0:
                    progress_callback(analyzed / max(frames_to_analyze, 1))

            frame_idx += 1

        cap.release()

        if progress_callback:
            progress_callback(1.0)

        # Find highlight windows
        highlights = self._find_highlights(scores, duration)
        return highlights

    def _score_frame(self, frame, prev_gray):
        """
        Score a single frame for action intensity.
        Returns (score: float 0-1, label: str).
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        component_scores = {}

        # 1. Kill feed region (top-right area of screen where kill notifications appear)
        kill_region = hsv[int(h * 0.05):int(h * 0.25), int(w * 0.55):int(w * 0.95)]
        kill_mask = cv2.inRange(kill_region, self.KILL_TEXT_LOWER, self.KILL_TEXT_UPPER)
        kill_density = np.count_nonzero(kill_mask) / max(kill_mask.size, 1)
        component_scores["kill_feed"] = min(kill_density * 8, 1.0)

        # 2. Damage indicator (red vignette around screen edges)
        edges_top = hsv[0:int(h * 0.1), :]
        edges_bottom = hsv[int(h * 0.9):, :]
        edges_left = hsv[:, 0:int(w * 0.1)]
        edges_right = hsv[:, int(w * 0.9):]

        red_score = 0
        for edge in [edges_top, edges_bottom, edges_left, edges_right]:
            mask1 = cv2.inRange(edge, self.DAMAGE_RED_LOWER, self.DAMAGE_RED_UPPER)
            mask2 = cv2.inRange(edge, self.DAMAGE_RED_LOWER2, self.DAMAGE_RED_UPPER2)
            red_density = (np.count_nonzero(mask1) + np.count_nonzero(mask2)) / max(edge.shape[0] * edge.shape[1], 1)
            red_score = max(red_score, red_density)
        component_scores["damage"] = min(red_score * 5, 1.0)

        # 3. Hit marker detection (bright flash in center crosshair area)
        center_region = hsv[int(h * 0.4):int(h * 0.6), int(w * 0.4):int(w * 0.6)]
        hit_mask = cv2.inRange(center_region, self.HIT_MARKER_LOWER, self.HIT_MARKER_UPPER)
        hit_density = np.count_nonzero(hit_mask) / max(hit_mask.size, 1)
        component_scores["hit_marker"] = min(hit_density * 6, 1.0)

        # 4. Explosion / muzzle flash (orange-yellow bursts)
        explosion_mask = cv2.inRange(hsv, self.EXPLOSION_LOWER, self.EXPLOSION_UPPER)
        explosion_density = np.count_nonzero(explosion_mask) / max(explosion_mask.size, 1)
        component_scores["explosion"] = min(explosion_density * 4, 1.0)

        # 5. Arc enemy blue glow detection
        arc_mask = cv2.inRange(hsv, self.ARC_BLUE_LOWER, self.ARC_BLUE_UPPER)
        arc_density = np.count_nonzero(arc_mask) / max(arc_mask.size, 1)
        component_scores["arc_enemy"] = min(arc_density * 5, 1.0)

        # 6. Scene change detection (motion / chaos)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion = np.mean(diff) / 255.0
            component_scores["motion"] = min(motion * 4, 1.0)
        else:
            component_scores["motion"] = 0

        # 7. Overall brightness spike (flash from kills, explosions)
        brightness = np.mean(gray) / 255.0
        brightness_spike = max(0, brightness - 0.6) * 3
        component_scores["brightness"] = min(brightness_spike, 1.0)

        # Weighted combination
        weights = {
            "kill_feed": 0.25,
            "damage": 0.20,
            "hit_marker": 0.15,
            "explosion": 0.15,
            "arc_enemy": 0.10,
            "motion": 0.10,
            "brightness": 0.05,
        }

        total_score = sum(component_scores[k] * weights[k] for k in weights)

        # Determine the dominant label
        best_component = max(component_scores, key=component_scores.get)
        label_map = {
            "kill_feed": "Kill / Elimination",
            "damage": "Taking Damage",
            "hit_marker": "Landing Hits",
            "explosion": "Explosion / Combat",
            "arc_enemy": "Arc Enemy Encounter",
            "motion": "Intense Action",
            "brightness": "Flash Event",
        }
        label = label_map.get(best_component, "Highlight")

        return total_score, label

    def _find_highlights(self, scores, total_duration):
        """
        Group high-scoring frames into highlight windows using a sliding
        window approach, then merge overlapping windows.
        """
        if not scores:
            return []

        # Sliding window: compute average score for each window
        window_frames = int(self.window_seconds * self.sample_fps)
        window_scores = []

        for i in range(len(scores)):
            window_end = min(i + window_frames, len(scores))
            window_slice = scores[i:window_end]
            avg_score = sum(s["score"] for s in window_slice) / len(window_slice)

            # Find the dominant label in this window
            label_counts = {}
            for s in window_slice:
                label_counts[s["label"]] = label_counts.get(s["label"], 0) + s["score"]
            dominant_label = max(label_counts, key=label_counts.get) if label_counts else "Highlight"

            window_scores.append({
                "start_idx": i,
                "timestamp": scores[i]["timestamp"],
                "avg_score": avg_score,
                "label": dominant_label,
            })

        # Find peaks above threshold
        peaks = [w for w in window_scores if w["avg_score"] >= self.intensity_threshold]

        if not peaks:
            # Lower threshold if nothing found and return top moments
            sorted_windows = sorted(window_scores, key=lambda w: w["avg_score"], reverse=True)
            # Take top 5 moments if their score is at least half the threshold
            fallback_threshold = self.intensity_threshold * 0.5
            peaks = [w for w in sorted_windows[:10] if w["avg_score"] >= fallback_threshold]

        if not peaks:
            return []

        # Merge overlapping/nearby highlights
        merged = self._merge_highlights(peaks)

        # Sort by timestamp
        merged.sort(key=lambda h: h["timestamp"])

        return merged

    def _merge_highlights(self, peaks, merge_gap=8):
        """Merge highlights that are within merge_gap seconds of each other."""
        if not peaks:
            return []

        # Sort by timestamp
        peaks.sort(key=lambda p: p["timestamp"])

        merged = []
        current = {
            "timestamp": peaks[0]["timestamp"],
            "end_time": peaks[0]["timestamp"] + self.window_seconds,
            "label": peaks[0]["label"],
            "confidence": peaks[0]["avg_score"],
            "peak_score": peaks[0]["avg_score"],
        }

        for peak in peaks[1:]:
            if peak["timestamp"] <= current["end_time"] + merge_gap:
                # Extend current highlight
                current["end_time"] = peak["timestamp"] + self.window_seconds
                current["peak_score"] = max(current["peak_score"], peak["avg_score"])
                current["confidence"] = (current["confidence"] + peak["avg_score"]) / 2
                # Use label from higher-scoring peak
                if peak["avg_score"] > current["peak_score"] * 0.9:
                    current["label"] = peak["label"]
            else:
                # Finalize current and start new
                merged.append(self._finalize_highlight(current))
                current = {
                    "timestamp": peak["timestamp"],
                    "end_time": peak["timestamp"] + self.window_seconds,
                    "label": peak["label"],
                    "confidence": peak["avg_score"],
                    "peak_score": peak["avg_score"],
                }

        merged.append(self._finalize_highlight(current))
        return merged

    def _finalize_highlight(self, highlight):
        """Convert a merged highlight window into the output format."""
        duration = highlight["end_time"] - highlight["timestamp"]
        # Clip duration between 20 and 60 seconds (default longer)
        duration = max(20, min(60, duration + 10))

        return {
            "timestamp": highlight["timestamp"],
            "duration": duration,
            "pre_pad": 8,
            "label": highlight["label"],
            "confidence": round(min(highlight["confidence"] * 1.5, 1.0), 2),
        }
