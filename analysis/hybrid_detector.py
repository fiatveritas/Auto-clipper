import cv2
import numpy as np
import subprocess
import concurrent.futures

from analysis.game_profiles import get_profile
from analysis.video_reader import VideoReader


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

    def __init__(self, game_id="league_of_legends", sample_fps=4):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.intensity_threshold = self.profile.get("intensity_threshold", 0.35)
        self.audio_threshold_db = self.profile.get("audio_threshold_db", -8)
        self.audio_ceiling_db = self.profile.get("audio_ceiling_db", -1)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Run audio analysis and visual analysis concurrently, then fuse
        audio + motion + scene scores after both processing paths complete.

        Returns:
            List of highlight dicts with timestamp, duration, label,
            confidence.
        """
        if progress_callback:
            progress_callback(0.02)

        print(
            "  [Hybrid] Starting concurrent audio + visual analysis..."
        )

        # --------------------------------------------------------------
        # Start FFmpeg audio extraction in a background thread.
        # --------------------------------------------------------------
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1
        )

        audio_future = executor.submit(
            self._extract_audio_levels,
            video_path
        )

        try:
            # ----------------------------------------------------------
            # Run Motion + Scene analysis immediately on the main thread.
            #
            # This pass intentionally does NOT need audio_levels.
            # ----------------------------------------------------------
            print(
                "  [Hybrid] Motion + Scene analysis..."
            )

            scores = self._analyze_video_pass(
                video_path,
                progress_callback
            )

            # ----------------------------------------------------------
            # Wait only for whatever portion of audio extraction remains.
            # ----------------------------------------------------------
            audio_levels = audio_future.result()

            # ----------------------------------------------------------
            # Fuse audio into the completed visual scores.
            # ----------------------------------------------------------
            for item in scores:

                timestamp = item["timestamp"]

                motion_score = item.get(
                    "motion_score",
                    0.0
                )

                scene_score = item.get(
                    "scene_score",
                    0.0
                )

                # Preserve menu suppression.
                if item.get("is_menu", False):
                    item["audio_score"] = 0.0
                    item["score"] = 0.0
                    item["label"] = "Menu/UI"
                    continue

                audio_score = self._db_to_score(
                    audio_levels.get(
                        int(timestamp),
                        -100
                    )
                )

                # ------------------------------------------------------
                # Original Hybrid fusion behavior.
                # ------------------------------------------------------
                max_score = max(
                    audio_score,
                    motion_score,
                    scene_score
                )

                signals_active = sum(
                    1
                    for s in [
                        audio_score,
                        motion_score,
                        scene_score
                    ]
                    if s >= 0.2
                )

                if signals_active >= 3:
                    fused = min(
                        max_score * 1.3,
                        1.0
                    )

                elif signals_active >= 2:
                    fused = min(
                        max_score * 1.15,
                        1.0
                    )

                else:
                    fused = max_score

                # ------------------------------------------------------
                # Original Hybrid classification behavior.
                # ------------------------------------------------------
                if fused < 0.2:
                    label = "Idle"

                elif (
                    audio_score >= motion_score
                    and audio_score >= scene_score
                ):
                    label = (
                        "Loud Combat"
                        if audio_score >= 0.6
                        else "Combat Audio"
                    )

                elif motion_score >= scene_score:
                    label = (
                        "Intense Action"
                        if motion_score >= 0.6
                        else "Active Movement"
                    )

                else:
                    label = (
                        "Visual Disruption"
                        if scene_score >= 0.6
                        else "Scene Shift"
                    )

                item["audio_score"] = audio_score
                item["score"] = fused
                item["label"] = label

            if progress_callback:
                progress_callback(0.95)

            duration = (
                scores[-1]["timestamp"] + 1
                if scores
                else 0
            )

            highlights = self._find_highlights(
                scores,
                duration
            )

            if progress_callback:
                progress_callback(1.0)

            print(
                f"  [Hybrid] Found "
                f"{len(highlights)} highlights"
            )

            for h in highlights:
                print(
                    f"  [Hybrid]   -> "
                    f"{h['label']} at "
                    f"{int(h['timestamp'])}s "
                    f"({h['duration']}s, "
                    f"conf:{h['confidence']})"
                )

            return highlights

        finally:
            executor.shutdown(wait=True)

    def _extract_audio_levels(self, video_path):
        """Extract per-second peak audio levels using ffmpeg."""
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-i", video_path,
            "-vn",
            "-af",
            "astats=metadata=1:reset=48000,"
            "ametadata=print:file=-",
            "-f", "null",
            "-",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  [Hybrid] ffmpeg failed: {e}")
            return {}

        if result.returncode != 0:
            print(
                f"  [Hybrid] ffmpeg error: "
                f"{result.stderr[:200]}"
            )
            return {}

        levels = {}
        current_time = 0.0

        for line in result.stdout.splitlines():
            line = line.strip()

            if "pts_time:" in line:
                try:
                    time_part = (
                        line
                        .split("pts_time:", 1)[1]
                        .split()[0]
                    )
                    current_time = float(time_part)

                except (ValueError, IndexError):
                    pass

            elif line.startswith(
                "lavfi.astats.Overall.Peak_level="
            ):
                try:
                    value = line.split("=", 1)[1]

                    if value.lower() == "-inf":
                        continue

                    level = float(value)
                    sec = int(current_time)

                    if (
                        sec not in levels
                        or level > levels[sec]
                    ):
                        levels[sec] = level

                except (ValueError, IndexError):
                    pass

        loud = sum(
            1
            for v in levels.values()
            if v >= self.audio_threshold_db
        )

        print(
            f"  [Hybrid] Audio: "
            f"{len(levels)}s analyzed, "
            f"{loud} loud seconds"
        )

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

    def _analyze_video_pass(
        self,
        video_path,
        progress_callback
    ):
        """
        Single visual pass computing Motion + Scene signals.

        Audio extraction runs independently in a background thread and is
        fused after this pass completes.

        Uses efficient sampled decoding and half-resolution working
        buffers for Motion + Scene processing.
        """
        reader = VideoReader(video_path)

        from analysis.video_utils import frame_interval_for

        fps = reader.fps
        total_frames = reader.frame_count

        frame_interval = frame_interval_for(
            fps,
            sample_fps=self.sample_fps
        )

        frames_to_analyze = (
            total_frames // frame_interval
        )

        prev_gray = None
        prev_hists = None
        prev_brightness = None
        prev_motion_energy = 0.0

        scores = []
        analyzed = 0

        with reader:

            for video_frame in reader.iter_sampled(
                frame_interval
            ):

                frame = video_frame.image
                frame_idx = video_frame.index
                timestamp = frame_idx / fps

                # ------------------------------------------------------
                # Preserve full-resolution menu behavior.
                # ------------------------------------------------------
                menu_gray = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2GRAY
                )

                if (
                    self.profile.get(
                        "menu_suppress",
                        "on"
                    ) != "off"
                    and self._is_menu_frame(
                        frame,
                        menu_gray
                    )
                ):
                    scores.append({
                        "score": 0.0,
                        "label": "Menu/UI",
                        "timestamp": timestamp,
                        "motion_score": 0.0,
                        "scene_score": 0.0,
                        "is_menu": True,
                    })

                    analyzed += 1

                    if (
                        progress_callback
                        and analyzed % 20 == 0
                    ):
                        progress_callback(
                            0.05
                            + (
                                analyzed
                                / max(
                                    frames_to_analyze,
                                    1
                                )
                            )
                            * 0.85
                        )

                    continue

                # ------------------------------------------------------
                # Shared half-resolution working frame.
                # ------------------------------------------------------
                h, w = frame.shape[:2]

                small_frame = cv2.resize(
                    frame,
                    (w // 2, h // 2),
                    interpolation=cv2.INTER_AREA
                )

                # ------------------------------------------------------
                # Motion buffer.
                # ------------------------------------------------------
                gray = cv2.cvtColor(
                    small_frame,
                    cv2.COLOR_BGR2GRAY
                )

                gray_blur = cv2.GaussianBlur(
                    gray,
                    (5, 5),
                    0
                )

                brightness = (
                    float(np.mean(gray)) / 255.0
                )

                # ------------------------------------------------------
                # Scene histograms.
                # ------------------------------------------------------
                hists = []

                for ch in range(3):

                    hist = cv2.calcHist(
                        [small_frame],
                        [ch],
                        None,
                        [64],
                        [0, 256]
                    )

                    cv2.normalize(
                        hist,
                        hist
                    )

                    hists.append(hist)

                # ------------------------------------------------------
                # Motion signal.
                # ------------------------------------------------------
                motion_score = 0.0

                if prev_gray is not None:

                    diff = cv2.absdiff(
                        gray_blur,
                        prev_gray
                    )

                    motion_energy = (
                        float(np.mean(diff))
                        / 255.0
                    )

                    diff_std = (
                        float(np.std(diff))
                        / 255.0
                    )

                    accel = 0.0

                    if (
                        motion_energy
                        > prev_motion_energy * 1.5
                        and motion_energy > 0.02
                    ):
                        accel = min(
                            (
                                motion_energy
                                - prev_motion_energy
                            )
                            * 5.0,
                            0.3
                        )

                    motion_score = min(
                        (motion_energy * 8.0)
                        + (diff_std * 4.0)
                        + accel,
                        1.0
                    )

                    prev_motion_energy = (
                        motion_energy
                    )

                # ------------------------------------------------------
                # Scene signal.
                # ------------------------------------------------------
                scene_score = 0.0

                if prev_hists is not None:

                    diffs = []
                    chi_scores = []

                    for i in range(3):

                        corr = cv2.compareHist(
                            prev_hists[i],
                            hists[i],
                            cv2.HISTCMP_CORREL
                        )

                        diffs.append(
                            1.0 - max(
                                corr,
                                0.0
                            )
                        )

                        chi = cv2.compareHist(
                            prev_hists[i],
                            hists[i],
                            cv2.HISTCMP_CHISQR
                        )

                        chi_scores.append(
                            min(
                                chi / 10.0,
                                1.0
                            )
                        )

                    color_shift = (
                        sum(diffs)
                        / len(diffs)
                    )

                    chi_shift = (
                        sum(chi_scores)
                        / len(chi_scores)
                    )

                    flash = 0.0

                    if prev_brightness is not None:

                        bd = abs(
                            brightness
                            - prev_brightness
                        )

                        if bd > 0.08:
                            flash = min(
                                bd * 5.0,
                                0.5
                            )

                    scene_score = min(
                        (color_shift * 3.0)
                        + (chi_shift * 2.0)
                        + flash,
                        1.0
                    )

                # ------------------------------------------------------
                # Store raw visual signals.
                #
                # Temporary visual-only score/label make diagnostics
                # possible before final audio fusion.
                # ------------------------------------------------------
                visual_score = max(
                    motion_score,
                    scene_score
                )

                if visual_score < 0.2:
                    visual_label = "Idle"

                elif motion_score >= scene_score:
                    visual_label = (
                        "Intense Action"
                        if motion_score >= 0.6
                        else "Active Movement"
                    )

                else:
                    visual_label = (
                        "Visual Disruption"
                        if scene_score >= 0.6
                        else "Scene Shift"
                    )

                scores.append({
                    "score": visual_score,
                    "label": visual_label,
                    "timestamp": timestamp,
                    "motion_score": motion_score,
                    "scene_score": scene_score,
                    "is_menu": False,
                })

                if (
                    visual_score
                    >= self.intensity_threshold * 0.5
                ):
                    mins = int(timestamp) // 60
                    secs = int(timestamp) % 60

                    print(
                        f"  [Hybrid] "
                        f"{mins}:{secs:02d} - "
                        f"visual:{visual_score:.3f} "
                        f"(m:{motion_score:.2f} "
                        f"s:{scene_score:.2f}) - "
                        f"{visual_label}"
                    )

                prev_gray = gray_blur
                prev_hists = hists
                prev_brightness = brightness

                analyzed += 1

                if (
                    progress_callback
                    and analyzed % 20 == 0
                ):
                    progress_callback(
                        0.05
                        + (
                            analyzed
                            / max(
                                frames_to_analyze,
                                1
                            )
                        )
                        * 0.85
                    )

        top = sorted(
            scores,
            key=lambda s: s["score"],
            reverse=True
        )[:5]

        print(
            f"  [Hybrid] Visual pass analyzed "
            f"{analyzed} frames"
        )

        score_strs = [
            f'{s["score"]:.3f}@'
            f'{int(s["timestamp"])}s'
            for s in top
        ]

        print(
            f"  [Hybrid] Visual Top: "
            f"{score_strs}"
        )

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
