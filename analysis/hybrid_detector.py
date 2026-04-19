import cv2
import numpy as np
import subprocess

from analysis.game_profiles import get_profile


class HybridDetector:
    """
    Combines three independent signals — audio loudness, motion energy,
    and scene change — into a single fused score per timestamp.

    Each signal catches different kinds of action:
      - Audio:  gunshots, explosions, ability sounds
      - Motion: camera shakes, fast movement, dodging
      - Scene:  flashes, damage overlays, color shifts

    A moment only needs ONE strong signal to qualify, so this catches
    things that any single detector would miss on its own.
    """

    def __init__(self, game_id="arc_raiders", sample_fps=4):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.intensity_threshold = self.profile.get("intensity_threshold", 0.35)
        self.audio_threshold_db = self.profile.get("audio_threshold_db", -8)
        self.audio_ceiling_db = self.profile.get("audio_ceiling_db", -1)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Run all three analyses and fuse the results.

        Returns:
            List of highlight dicts with timestamp, duration, label, confidence.
        """
        if progress_callback:
            progress_callback(0.02)

        # Phase 1: Audio (fast, no video decoding)
        print("  [Hybrid] Phase 1/3: Audio analysis...")
        audio_levels = self._extract_audio_levels(video_path)
        if progress_callback:
            progress_callback(0.20)

        # Phase 2+3: Motion + Scene change in a single video pass
        print("  [Hybrid] Phase 2/3: Motion + Scene change (single pass)...")
        scores = self._analyze_video_pass(video_path, audio_levels, progress_callback)

        if progress_callback:
            progress_callback(0.95)

        duration = scores[-1]["timestamp"] + 1 if scores else 0
        highlights = self._find_highlights(scores, duration)

        if progress_callback:
            progress_callback(1.0)

        print(f"  [Hybrid] Found {len(highlights)} highlights")
        for h in highlights:
            print(f"  [Hybrid]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s, conf:{h['confidence']})")

        return highlights

    def _extract_audio_levels(self, video_path):
        """Extract per-second peak audio levels using ffmpeg."""
        cmd = [
            "ffmpeg", "-i", video_path,
            "-af", "astats=metadata=1:reset=48000,"
                   "ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-",
            "-f", "null", "-",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  [Hybrid] ffmpeg failed: {e}")
            return {}

        if result.returncode != 0:
            return {}

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
                    if sec not in levels or level > levels[sec]:
                        levels[sec] = level
                except (ValueError, IndexError):
                    pass

        loud = sum(1 for v in levels.values() if v >= self.audio_threshold_db)
        print(f"  [Hybrid] Audio: {len(levels)}s analyzed, {loud} loud seconds")
        return levels

    def _db_to_score(self, level_db):
        """Convert a dB level to a 0-1 score."""
        if level_db < self.audio_threshold_db:
            return 0.0
        raw = (level_db - self.audio_threshold_db) / max(self.audio_ceiling_db - self.audio_threshold_db, 1)
        return min(max(raw, 0.0), 1.0)

    def _is_menu_frame(self, frame, gray):
        """Detect menu/inventory/UI overlay frames that should not be clipped.

        Intentionally strict — false negatives (scoring a menu frame) are
        much less harmful than false positives (suppressing real gameplay).
        """
        h, w = frame.shape[:2]
        brightness = np.mean(gray) / 255.0

        # Completely black frame = loading screen
        if brightness < 0.04:
            return True

        # Very uniform AND dim center = solid menu background
        center = gray[int(h * 0.2):int(h * 0.8), int(w * 0.2):int(w * 0.8)]
        std_dev = np.std(center)
        if std_dev < 10 and brightness < 0.25:
            return True

        # Low saturation + very low variance = greyed-out menu overlay
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mean_sat = np.mean(hsv[:, :, 1])
        if mean_sat < 15 and std_dev < 20:
            return True

        # Game-specific menu colors (keep — these are intentionally targeted)
        menu_colors = self.profile.get("menu_suppress_colors")
        if menu_colors:
            for mc in menu_colors:
                mask = cv2.inRange(hsv, mc["lower"], mc["upper"])
                coverage = np.count_nonzero(mask) / max(mask.size, 1)
                if coverage >= mc.get("min_coverage", 0.4):
                    return True

        return False

    def _analyze_video_pass(self, video_path, audio_levels, progress_callback):
        """Single pass through video computing motion + scene change + audio fusion."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        from analysis.video_utils import probe_video, frame_interval_for
        fps, total_frames, _duration = probe_video(cap)
        frame_interval = frame_interval_for(fps, sample_fps=self.sample_fps)
        frames_to_analyze = total_frames // frame_interval

        prev_gray = None
        prev_hists = None
        prev_brightness = None
        prev_motion_energy = 0.0
        scores = []
        frame_idx = 0
        analyzed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
                brightness = np.mean(gray) / 255.0

                # Menu/inventory suppression — skip UI frames entirely
                if self.profile.get("menu_suppress", "on") != "off" and self._is_menu_frame(frame, gray):
                    scores.append({
                        "score": 0.0,
                        "label": "Menu/UI",
                        "timestamp": timestamp,
                    })
                    prev_gray = gray_blur
                    prev_brightness = brightness
                    analyzed += 1
                    if progress_callback and analyzed % 20 == 0:
                        progress_callback(0.20 + (analyzed / max(frames_to_analyze, 1)) * 0.70)
                    frame_idx += 1
                    continue

                # Color histograms for scene change
                hists = []
                for ch in range(3):
                    hist = cv2.calcHist([frame], [ch], None, [64], [0, 256])
                    cv2.normalize(hist, hist)
                    hists.append(hist)

                # --- Signal 1: Audio ---
                audio_score = self._db_to_score(audio_levels.get(int(timestamp), -100))

                # --- Signal 2: Motion ---
                motion_score = 0.0
                if prev_gray is not None:
                    diff = cv2.absdiff(gray_blur, prev_gray)
                    motion_energy = np.mean(diff) / 255.0
                    diff_std = np.std(diff) / 255.0

                    # Acceleration bonus
                    accel = 0.0
                    if motion_energy > prev_motion_energy * 1.5 and motion_energy > 0.02:
                        accel = min((motion_energy - prev_motion_energy) * 5.0, 0.3)

                    motion_score = min((motion_energy * 8.0) + (diff_std * 4.0) + accel, 1.0)
                    prev_motion_energy = motion_energy

                # --- Signal 3: Scene change ---
                scene_score = 0.0
                if prev_hists is not None:
                    diffs = []
                    chi_scores = []
                    for i in range(3):
                        corr = cv2.compareHist(prev_hists[i], hists[i], cv2.HISTCMP_CORREL)
                        diffs.append(1.0 - max(corr, 0.0))
                        chi = cv2.compareHist(prev_hists[i], hists[i], cv2.HISTCMP_CHISQR)
                        chi_scores.append(min(chi / 10.0, 1.0))

                    color_shift = sum(diffs) / len(diffs)
                    chi_shift = sum(chi_scores) / len(chi_scores)

                    flash = 0.0
                    if prev_brightness is not None:
                        bd = abs(brightness - prev_brightness)
                        if bd > 0.08:
                            flash = min(bd * 5.0, 0.5)

                    scene_score = min((color_shift * 3.0) + (chi_shift * 2.0) + flash, 1.0)

                # --- Fusion ---
                # Take the max of any signal, then boost if multiple agree
                max_score = max(audio_score, motion_score, scene_score)
                signals_active = sum(1 for s in [audio_score, motion_score, scene_score] if s >= 0.2)

                # Multi-signal agreement bonus: if 2+ signals fire, boost confidence
                if signals_active >= 3:
                    fused = min(max_score * 1.3, 1.0)
                elif signals_active >= 2:
                    fused = min(max_score * 1.15, 1.0)
                else:
                    fused = max_score

                # Classify based on which signal dominated
                if fused < 0.2:
                    label = "Idle"
                elif audio_score >= motion_score and audio_score >= scene_score:
                    label = "Loud Combat" if audio_score >= 0.6 else "Combat Audio"
                elif motion_score >= scene_score:
                    label = "Intense Action" if motion_score >= 0.6 else "Active Movement"
                else:
                    label = "Visual Disruption" if scene_score >= 0.6 else "Scene Shift"

                scores.append({
                    "score": fused,
                    "label": label,
                    "timestamp": timestamp,
                })

                if fused >= self.intensity_threshold * 0.5:
                    mins = int(timestamp) // 60
                    secs = int(timestamp) % 60
                    parts = f"a:{audio_score:.2f} m:{motion_score:.2f} s:{scene_score:.2f}"
                    print(f"  [Hybrid] {mins}:{secs:02d} - fused:{fused:.3f} ({parts}) - {label}")

                prev_gray = gray_blur
                prev_hists = hists
                prev_brightness = brightness
                analyzed += 1

                if progress_callback and analyzed % 20 == 0:
                    progress_callback(0.20 + (analyzed / max(frames_to_analyze, 1)) * 0.70)

            frame_idx += 1

        cap.release()

        top = sorted(scores, key=lambda s: s["score"], reverse=True)[:5]
        print(f"  [Hybrid] Analyzed {analyzed} frames")
        score_strs = [f'{s["score"]:.3f}@{int(s["timestamp"])}s' for s in top]
        print(f"  [Hybrid] Top: {score_strs}")

        return scores

    def _find_highlights(self, scores, duration):
        """Group high-scoring periods into highlights."""
        if not scores:
            return []

        # Sliding window smoothing
        window_frames = max(1, int(3 * self.sample_fps))
        window_scores = []

        for i in range(len(scores)):
            window = scores[max(0, i - window_frames):i + 1]
            avg = sum(s["score"] for s in window) / len(window)
            peak = max(s["score"] for s in window)
            blended = avg * 0.5 + peak * 0.5
            peak_label = max(window, key=lambda s: s["score"])["label"]
            window_scores.append({
                "score": blended,
                "label": peak_label,
                "timestamp": scores[i]["timestamp"],
            })

        above = [s for s in window_scores if s["score"] >= self.intensity_threshold]

        # Fallback: if we found very few clips, try to find more
        min_expected = max(1, int(duration / 600))  # ~1 clip per 10 min
        if len(above) < min_expected:
            sorted_scores = sorted(window_scores, key=lambda s: s["score"], reverse=True)
            fallback = self.intensity_threshold * self.profile.get("fallback_threshold_ratio", 0.15)
            max_fallback = max(5, min_expected * 2)
            fallback_candidates = [s for s in sorted_scores[:max_fallback]
                                   if s["score"] >= fallback and s["label"] not in ("Idle", "Menu/UI")]
            existing_times = {s["timestamp"] for s in above}
            merge_gap_val = self.profile.get("merge_gap", 8)
            for fc in fallback_candidates:
                if not any(abs(fc["timestamp"] - t) < merge_gap_val for t in existing_times):
                    above.append(fc)
                    existing_times.add(fc["timestamp"])

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
