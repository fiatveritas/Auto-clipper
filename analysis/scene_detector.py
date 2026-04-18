import cv2
import numpy as np

from analysis.game_profiles import get_profile


class SceneChangeDetector:
    """
    Detects exciting moments by measuring visual "tempo" — how rapidly
    the scene is changing. Uses histogram comparison between frames.

    Action sequences produce rapid visual changes: explosions flash bright,
    camera shakes shift colors, HUD elements appear/disappear, damage
    effects overlay the screen. Idle gameplay has very stable histograms.

    This is fundamentally different from motion detection:
    - Motion measures pixel displacement (things moving)
    - Scene change measures color distribution shifts (visual "look" changing)
    An explosion might not move many pixels but massively shifts the histogram.
    """

    def __init__(self, game_id="arc_raiders", sample_fps=4):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.intensity_threshold = self.profile.get("intensity_threshold", 0.35)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze video using histogram-based scene change detection.

        Returns:
            List of highlight dicts with timestamp, duration, label, confidence.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        # NaN-safe: OpenCV returns NaN on some codecs; NaN != NaN is the idiom.
        if not fps or fps != fps or fps <= 0:
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if total_frames > 0 else 0

        frame_interval = max(1, int(fps / self.sample_fps))
        frames_to_analyze = total_frames // frame_interval

        prev_hists = None
        prev_brightness = None
        scores = []
        frame_idx = 0
        analyzed = 0

        print(f"  [Scene] Analyzing {duration:.0f}s video for scene changes...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps

                # Compute color histograms for each channel
                hists = []
                for ch in range(3):
                    hist = cv2.calcHist([frame], [ch], None, [64], [0, 256])
                    cv2.normalize(hist, hist)
                    hists.append(hist)

                # Compute overall brightness
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray) / 255.0

                scene_score = 0.0
                label = "Stable"

                if prev_hists is not None:
                    # Compare histograms using correlation
                    # correlation = 1.0 means identical, 0.0 means completely different
                    diffs = []
                    for i in range(3):
                        corr = cv2.compareHist(prev_hists[i], hists[i], cv2.HISTCMP_CORREL)
                        # Convert: 1.0 (same) -> 0.0, 0.0 (different) -> 1.0
                        diffs.append(1.0 - max(corr, 0.0))

                    # Average color shift across channels
                    color_shift = sum(diffs) / len(diffs)

                    # Brightness flash detection
                    flash_score = 0.0
                    if prev_brightness is not None:
                        brightness_delta = abs(brightness - prev_brightness)
                        # Explosions/muzzle flash cause sudden brightness spikes
                        if brightness_delta > 0.08:
                            flash_score = min(brightness_delta * 5.0, 0.5)

                    # Chi-square distance (more sensitive to distribution changes)
                    chi_scores = []
                    for i in range(3):
                        chi = cv2.compareHist(prev_hists[i], hists[i], cv2.HISTCMP_CHISQR)
                        chi_scores.append(min(chi / 10.0, 1.0))  # Normalize
                    chi_shift = sum(chi_scores) / len(chi_scores)

                    # Combine signals
                    raw_score = (color_shift * 3.0) + (chi_shift * 2.0) + flash_score
                    scene_score = min(raw_score, 1.0)

                    if scene_score >= 0.7:
                        label = "Major Scene Change"
                    elif scene_score >= 0.45:
                        label = "Visual Disruption"
                    elif scene_score >= 0.25:
                        label = "Scene Shift"
                    else:
                        label = "Stable"

                scores.append({
                    "score": scene_score,
                    "label": label,
                    "timestamp": timestamp,
                })

                if scene_score >= self.intensity_threshold * 0.5:
                    mins = int(timestamp) // 60
                    secs = int(timestamp) % 60
                    print(f"  [Scene] {mins}:{secs:02d} - score:{scene_score:.3f} - {label}")

                prev_hists = hists
                prev_brightness = brightness
                analyzed += 1

                if progress_callback and analyzed % 20 == 0:
                    progress_callback(analyzed / max(frames_to_analyze, 1))

            frame_idx += 1

        cap.release()

        if progress_callback:
            progress_callback(1.0)

        top = sorted(scores, key=lambda s: s["score"], reverse=True)[:5]
        print(f"  [Scene] Analyzed {analyzed} frames over {duration:.0f}s")
        score_strs = [f'{s["score"]:.3f}@{int(s["timestamp"])}s' for s in top]
        print(f"  [Scene] Top: {score_strs}")

        highlights = self._find_highlights(scores, duration)
        print(f"  [Scene] Found {len(highlights)} highlights")
        for h in highlights:
            print(f"  [Scene]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s)")

        return highlights

    def _find_highlights(self, scores, duration):
        """Group high scene-change periods into highlight clips."""
        if not scores:
            return []

        # Use a sliding window to smooth out individual spikes
        window_frames = max(1, int(3 * self.sample_fps))  # 3-second window
        window_scores = []

        for i in range(len(scores)):
            window = scores[max(0, i - window_frames):i + 1]
            # Use a mix of average and peak — scene changes are spiky
            avg = sum(s["score"] for s in window) / len(window)
            peak = max(s["score"] for s in window)
            blended = avg * 0.6 + peak * 0.4  # Favor peaks slightly
            peak_label = max(window, key=lambda s: s["score"])["label"]
            window_scores.append({
                "score": blended,
                "label": peak_label,
                "timestamp": scores[i]["timestamp"],
            })

        above = [s for s in window_scores if s["score"] >= self.intensity_threshold]

        if not above:
            sorted_scores = sorted(window_scores, key=lambda s: s["score"], reverse=True)
            fallback = self.intensity_threshold * 0.4
            above = [s for s in sorted_scores[:10] if s["score"] >= fallback]

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
            confidence = min(avg * 1.6, 1.0)

            highlights.append({
                "timestamp": c["start"],
                "duration": clip_dur,
                "pre_pad": self.profile.get("pre_pad", 8),
                "label": c["label"],
                "confidence": round(confidence, 2),
            })

        return highlights
