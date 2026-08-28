import cv2
import numpy as np
import subprocess

from analysis.game_profiles import get_profile

from analysis.video_reader import VideoReader

import concurrent.futures


class GameDetector:
    """
    Detects exciting moments in gameplay by analyzing video frames
    using a game-specific detection profile, with optional audio analysis.

    The detector samples frames at a configurable rate, scores each frame
    window for "action intensity", and returns timestamps above a threshold.
    Audio spikes (gunshots, explosions) boost scores at matching timestamps.
    """

    def __init__(
        self,
        game_id="league_of_legends",
        sample_fps=2,
        window_seconds=3
    ):
        self.profile = get_profile(game_id)
        self.sample_fps = sample_fps
        self.window_seconds = window_seconds
        self.intensity_threshold = self.profile["intensity_threshold"]


    def _extract_audio_levels(self, video_path, segment_duration=1.0):
        """
        Extract per-second audio loudness levels using ffmpeg.
        Returns dict mapping second -> peak_db value.
        """
        audio_weight = self.profile.get("audio_weight", 0)

        if audio_weight <= 0:
            return {}

        print("  [Audio] Extracting audio levels...")

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-i", video_path,
            "-vn",
            "-af",
            f"astats=metadata=1:reset={int(48000 * segment_duration)},"
            "ametadata=print:file=-",
            "-f", "null",
            "-",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  [Audio] ffmpeg failed: {e}")
            return {}

        if result.returncode != 0:
            print(
                f"  [Audio] ffmpeg error "
                f"(rc={result.returncode})"
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

        if levels:
            threshold = self.profile.get(
                "audio_threshold_db",
                -8
            )

            loud_count = sum(
                1
                for v in levels.values()
                if v >= threshold
            )

            print(
                f"  [Audio] Got {len(levels)} seconds "
                f"of audio, {loud_count} loud moments"
            )

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

        Audio extraction runs concurrently with visual frame analysis.
        Audio/CV fusion occurs after both processing paths complete.

        Returns:
            List of dicts:
            [
                {
                    "timestamp": float,
                    "duration": float,
                    "label": str,
                    "confidence": float
                },
                ...
            ]
        """

        # --------------------------------------------------------------
        # Start audio extraction in the background.
        # --------------------------------------------------------------
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        audio_future = executor.submit(
            self._extract_audio_levels,
            video_path
        )

        try:
            # ----------------------------------------------------------
            # Prepare video analysis while FFmpeg audio analysis runs.
            # ----------------------------------------------------------
            reader = VideoReader(video_path)

            fps = reader.fps
            total_frames = reader.frame_count
            duration = reader.duration

            frame_interval = max(
                1,
                int(fps / self.sample_fps)
            )

            frames_to_analyze = (
                total_frames // frame_interval
            )

            audio_weight = self.profile.get(
                "audio_weight",
                0
            )

            # Store the raw CV results first.
            # Audio will be fused afterward.
            scores = []

            prev_frame_gray = None
            prev_bar_fill = None

            analyzed = 0

            # ----------------------------------------------------------
            # Visual analysis
            # ----------------------------------------------------------
            with reader:

                for video_frame in reader.iter_sampled(
                    frame_interval
                ):

                    frame = video_frame.image
                    frame_idx = video_frame.index
                    timestamp = frame_idx / fps

                    (
                        cv_score,
                        label,
                        prev_bar_fill,
                        prev_frame_gray,
                        early
                    ) = self._score_frame(
                        frame,
                        prev_frame_gray,
                        prev_bar_fill
                    )


                    # ----------------------------------------------
                    # Store CV result only.
                    #
                    # Audio extraction is still running in parallel.
                    # Fusion happens after the frame pass.
                    # ----------------------------------------------
                    scores.append({
                        "cv_score": cv_score,
                        "score": cv_score,
                        "label": label,
                        "timestamp": timestamp,
                    })

                    analyzed += 1


                    if (
                        progress_callback
                        and analyzed % 20 == 0
                    ):
                        progress_callback(
                            analyzed
                            / max(frames_to_analyze, 1)
                        )

            # ----------------------------------------------------------
            # Visual processing is complete.
            #
            # If FFmpeg is still running, this waits only for whatever
            # audio time remains.
            # ----------------------------------------------------------
            audio_levels = audio_future.result()

            # ----------------------------------------------------------
            # Fuse audio into the stored CV results.
            # ----------------------------------------------------------
            for item in scores:

                timestamp = item["timestamp"]
                cv_score = item["cv_score"]
                label = item["label"]

                audio_score = self._get_audio_score(
                    timestamp,
                    audio_levels
                )

                # Menu frames remain fully suppressed.
                if label == "Menu/Lobby":
                    score = 0.0

                # Preserve the existing audio gate:
                # audio can boost a visual event but cannot create
                # a highlight from an otherwise inactive CV frame.
                elif (
                    audio_weight > 0
                    and audio_score > 0
                    and cv_score > 0.02
                ):
                    score = (
                        cv_score * (1.0 - audio_weight)
                        + audio_score * audio_weight
                    )

                    if (
                        audio_score > 0.5
                        and label == "Highlight"
                    ):
                        label = "Loud Combat"

                else:
                    score = cv_score

                item["score"] = score
                item["label"] = label
                item["audio_score"] = audio_score

            if progress_callback:
                progress_callback(1.0)

            # ----------------------------------------------------------
            # Diagnostics
            # ----------------------------------------------------------
            top_scores = sorted(
                scores,
                key=lambda s: s["score"],
                reverse=True
            )[:10]

            menu_count = sum(
                1
                for s in scores
                if s["label"] == "Menu/Lobby"
            )

            zero_count = sum(
                1
                for s in scores
                if s["score"] == 0.0
            )

            above_thresh = sum(
                1
                for s in scores
                if s["score"] >= self.intensity_threshold
            )

            print(
                f"  [CV] Game: "
                f"{self.profile['name']}"
            )

            print(
                f"  [CV] Analyzed {analyzed} frames "
                f"over {duration:.0f}s"
            )

            print(
                f"  [CV] Menu-suppressed: "
                f"{menu_count}/{analyzed} frames "
                f"("
                f"{100 * menu_count / max(analyzed, 1):.1f}"
                f"%)"
            )

            print(
                f"  [CV] Zero-score: "
                f"{zero_count}/{analyzed} | "
                f"Above threshold: "
                f"{above_thresh}/{analyzed}"
            )

            if audio_levels:
                print(
                    f"  [CV] Audio analysis: enabled "
                    f"(weight={audio_weight})"
                )

            score_strs = [
                f'{s["score"]:.3f}@'
                f'{int(s["timestamp"])}s'
                for s in top_scores
            ]

            print(
                f"  [CV] Top scores: {score_strs}"
            )

            print(
                f"  [CV] Threshold: "
                f"{self.intensity_threshold}"
            )

            # ----------------------------------------------------------
            # Highlight generation
            # ----------------------------------------------------------
            highlights = self._find_highlights(
                scores,
                duration
            )

            print(
                f"  [CV] Found "
                f"{len(highlights)} highlights"
            )

            for h in highlights:
                print(
                    f"  [CV]   -> {h['label']} at "
                    f"{int(h['timestamp'])}s "
                    f"({h['duration']}s, "
                    f"conf:{h['confidence']})"
                )


            return highlights

        finally:
            executor.shutdown(wait=True)

    def _is_menu_frame(
        self,
        frame,
        hsv,
        gray,
        mean_brightness=None
    ):
        """
        Detect if the current frame is a menu/lobby/loading screen.

        mean_brightness may be supplied by _score_frame so the grayscale
        mean does not need to be calculated twice.

        For darker frames that require the center-uniformity test, use a
        2x2 strided sample of the center region. This preserves the same
        screen area while reducing the number of pixels processed by
        np.std() by approximately 75%.

        Thresholds remain intentionally strict to avoid suppressing
        real gameplay.
        """
        h, w = gray.shape[:2]

        # --------------------------------------------------------------
        # Reuse brightness calculated by _score_frame when available.
        # --------------------------------------------------------------
        if mean_brightness is None:
            mean_brightness = (
                float(np.mean(gray)) / 255.0
            )

        # Almost completely black frame = loading screen.
        if mean_brightness < 0.04:
            return True

        # Bright frames cannot satisfy the dark/uniform menu test.
        if mean_brightness >= 0.25:
            return False

        # --------------------------------------------------------------
        # Darker frames require center-uniformity analysis.
        # --------------------------------------------------------------
        center = gray[
            int(h * 0.2):int(h * 0.8),
            int(w * 0.2):int(w * 0.8)
        ]

        # --------------------------------------------------------------
        # MENU STD OPTIMIZATION
        #
        # NumPy slicing produces a strided view rather than performing
        # another cv2.resize().
        #
        # Process approximately 25% of the center pixels.
        # --------------------------------------------------------------
        center_sample = center[::2, ::2]

        std_dev = float(
            np.std(center_sample)
        )

        if std_dev < 10:
            return True

        return False

    def _score_frame(self, frame, prev_gray, prev_bar_fill=None):
        """
        Score a single frame for action intensity using the game profile.

        Returns:
            (
                score,
                label,
                bar_fill,
                small_gray,
                early_exit_candidate
            )
        """
        h, w = frame.shape[:2]

        # --------------------------------------------------------------
        # Prepare grayscale working buffer.
        # --------------------------------------------------------------
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        small_gray = cv2.resize(
            gray,
            (w // 2, h // 2),
            interpolation=cv2.INTER_AREA
        )

        # --------------------------------------------------------------
        # Calculate mean brightness ONCE.
        #
        # This value is shared by:
        #   - menu suppression
        #   - brightness/flash detector
        #
        # Previously np.mean(small_gray) was calculated twice.
        # --------------------------------------------------------------
        mean_brightness = (
            float(np.mean(small_gray))
            / 255.0
        )

        # --------------------------------------------------------------
        # Menu suppression
        # --------------------------------------------------------------
        if (
            self.profile.get("menu_suppress", "on") != "off"
            and self._is_menu_frame(
                frame,
                None,
                small_gray,
                mean_brightness
            )
        ):
            return (
                0.0,
                "Menu/Lobby",
                prev_bar_fill,
                small_gray,
                False
            )

        component_scores = {}
        label_map = {}
        weights = {}

        bar_fill = prev_bar_fill

        # --------------------------------------------------------------
        # Health-bar detector
        # --------------------------------------------------------------
        health_det_id = None
        health_det = None

        for det_id, det in self.profile["detectors"].items():

            if det.get("region") == "health_bar":
                health_det_id = det_id
                health_det = det
                break

        if health_det is not None:

            label_map[health_det_id] = health_det["label"]
            weights[health_det_id] = health_det["weight"]

            y1, y2, x1, x2 = health_det["bar_region"]

            bar_bgr = frame[
                int(h * y1):int(h * y2),
                int(w * x1):int(w * x2)
            ]

            bar_region = cv2.cvtColor(
                bar_bgr,
                cv2.COLOR_BGR2HSV
            )

            bar_size = max(
                bar_region.shape[0]
                * bar_region.shape[1],
                1
            )

            total_bar_pixels = 0

            for color in health_det["bar_colors"]:


                mask = cv2.inRange(
                    bar_region,
                    color["lower"],
                    color["upper"]
                )

                total_bar_pixels += (
                    cv2.countNonZero(mask)
                )

            current_fill = (
                total_bar_pixels / bar_size
            )

            bar_fill = current_fill

            if prev_bar_fill is not None:

                drop = (
                    prev_bar_fill
                    - current_fill
                )

                depletion_threshold = health_det.get(
                    "depletion_threshold",
                    0.3
                )

                if drop >= depletion_threshold:

                    raw = min(
                        drop / depletion_threshold,
                        1.0
                    )

                    component_scores[
                        health_det_id
                    ] = min(
                        raw
                        * health_det["multiplier"],
                        1.0
                    )

                else:
                    component_scores[
                        health_det_id
                    ] = 0.0

            else:
                component_scores[
                    health_det_id
                ] = 0.0

        # --------------------------------------------------------------
        # Motion detection
        # --------------------------------------------------------------
        motion_weight = self.profile.get(
            "motion_weight",
            0.10
        )

        if prev_gray is not None:

            diff = cv2.absdiff(
                small_gray,
                prev_gray
            )

            motion = (
                float(np.mean(diff))
                / 255.0
            )

            component_scores["motion"] = min(
                motion
                * self.profile.get(
                    "motion_multiplier",
                    4
                ),
                1.0
            )

        else:
            component_scores["motion"] = 0.0

        weights["motion"] = motion_weight
        label_map["motion"] = "Intense Action"

        # --------------------------------------------------------------
        # Brightness detection
        #
        # Reuse mean_brightness calculated above.
        # --------------------------------------------------------------
        brightness_weight = self.profile.get(
            "brightness_weight",
            0.05
        )

        brightness_trigger = self.profile.get(
            "brightness_threshold",
            0.6
        )

        brightness_multiplier = self.profile.get(
            "brightness_multiplier",
            3
        )

        brightness_spike = max(
            0.0,
            mean_brightness - brightness_trigger
        ) * brightness_multiplier

        component_scores["brightness"] = min(
            brightness_spike,
            1.0
        )

        weights["brightness"] = brightness_weight
        label_map["brightness"] = "Flash Event"

        # --------------------------------------------------------------
        # Early gate
        # --------------------------------------------------------------
        motion_threshold = 0.02
        brightness_threshold = 0.05

        health_score = 0.0

        if health_det_id is not None:
            health_score = component_scores.get(
                health_det_id,
                0.0
            )

        early_exit_candidate = (
            prev_gray is not None
            and component_scores["motion"] < motion_threshold
            and component_scores["brightness"] < brightness_threshold
            and health_score <= 0.0
        )

        # --------------------------------------------------------------
        # REAL EARLY EXIT
        # --------------------------------------------------------------
        if early_exit_candidate:

            total_score = sum(
                component_scores.get(k, 0.0)
                * weights.get(k, 0.0)
                for k in weights
            )

            best_component = max(
                component_scores,
                key=component_scores.get
            )

            label = label_map.get(
                best_component,
                "Highlight"
            )

            return (
                total_score,
                label,
                bar_fill,
                small_gray,
                True
            )

        # --------------------------------------------------------------
        # Full-resolution HSV.
        # --------------------------------------------------------------
        hsv = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2HSV
        )

        # --------------------------------------------------------------
        # Shared half-resolution HSV.
        #
        # Used by:
        #   - full-frame color-density detectors
        #   - sufficiently large bounded regions
        # --------------------------------------------------------------
        small_hsv = cv2.resize(
            hsv,
            (
                max(w // 2, 1),
                max(h // 2, 1)
            ),
            interpolation=cv2.INTER_AREA
        )

        small_h, small_w = small_hsv.shape[:2]

        region_cache = {}

        # --------------------------------------------------------------
        # Remaining profile detectors
        # --------------------------------------------------------------
        for det_id, det in self.profile["detectors"].items():

            if det.get("region") == "health_bar":
                continue

            label_map[det_id] = det["label"]
            weights[det_id] = det["weight"]

            # ----------------------------------------------------------
            # Edge detector
            # ----------------------------------------------------------
            if det["region"] == "edges":

                edge_size = det.get(
                    "edge_size",
                    0.10
                )

                edges_list = [
                    hsv[
                        0:int(h * edge_size),
                        :
                    ],
                    hsv[
                        int(h * (1 - edge_size)):,
                        :
                    ],
                    hsv[
                        :,
                        0:int(w * edge_size)
                    ],
                    hsv[
                        :,
                        int(w * (1 - edge_size)):
                    ],
                ]

                best = 0.0

                for edge in edges_list:

                    edge_pixels = max(
                        edge.shape[0]
                        * edge.shape[1],
                        1
                    )


                    mask1 = cv2.inRange(
                        edge,
                        det["lower"],
                        det["upper"]
                    )

                    density = (
                        cv2.countNonZero(mask1)
                        / edge_pixels
                    )

                    if "lower2" in det:



                        mask2 = cv2.inRange(
                            edge,
                            det["lower2"],
                            det["upper2"]
                        )

                        density += (
                            cv2.countNonZero(mask2)
                            / edge_pixels
                        )

                    best = max(
                        best,
                        density
                    )

                component_scores[det_id] = min(
                    best * det["multiplier"],
                    1.0
                )

            # ----------------------------------------------------------
            # Full-frame detector
            #
            # Keep successful half-resolution optimization.
            # ----------------------------------------------------------
            elif det["region"] == "full":



                mask = cv2.inRange(
                    small_hsv,
                    det["lower"],
                    det["upper"]
                )

                density = (
                    cv2.countNonZero(mask)
                    / max(mask.size, 1)
                )

                component_scores[det_id] = min(
                    density
                    * det["multiplier"],
                    1.0
                )

            # ----------------------------------------------------------
            # Region detector
            # ----------------------------------------------------------
            elif isinstance(
                det["region"],
                list
            ):

                y1, y2, x1, x2 = det["region"]

                region_fraction = (
                    (y2 - y1)
                    * (x2 - x1)
                )

                # ------------------------------------------------------
                # Large regions reuse small_hsv.
                #
                # Small HUD regions remain full resolution.
                # ------------------------------------------------------
                use_small_region = (
                    region_fraction >= 0.25
                )

                if use_small_region:

                    key = (
                        "small_region",
                        y1,
                        y2,
                        x1,
                        x2
                    )

                    if key not in region_cache:

                        region_cache[key] = small_hsv[
                            int(small_h * y1):
                            int(small_h * y2),

                            int(small_w * x1):
                            int(small_w * x2)
                        ]

                else:

                    key = (
                        "region",
                        y1,
                        y2,
                        x1,
                        x2
                    )

                    if key not in region_cache:

                        region_cache[key] = hsv[
                            int(h * y1):
                            int(h * y2),

                            int(w * x1):
                            int(w * x2)
                        ]

                region = region_cache[key]


                mask = cv2.inRange(
                    region,
                    det["lower"],
                    det["upper"]
                )

                density = (
                    cv2.countNonZero(mask)
                    / max(mask.size, 1)
                )

                if "lower2" in det:


                    mask2 = cv2.inRange(
                        region,
                        det["lower2"],
                        det["upper2"]
                    )

                    density += (
                        cv2.countNonZero(mask2)
                        / max(mask2.size, 1)
                    )

                component_scores[det_id] = min(
                    density
                    * det["multiplier"],
                    1.0
                )

        # --------------------------------------------------------------
        # Weighted combination
        # --------------------------------------------------------------
        total_score = sum(
            component_scores.get(k, 0.0)
            * weights.get(k, 0.0)
            for k in weights
        )

        # --------------------------------------------------------------
        # Dominant label
        # --------------------------------------------------------------
        best_component = max(
            component_scores,
            key=component_scores.get
        )

        label = label_map.get(
            best_component,
            "Highlight"
        )

        return (
            total_score,
            label,
            bar_fill,
            small_gray,
            False
        )
        
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
