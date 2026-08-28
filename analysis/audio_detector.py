import subprocess


class AudioDetector:
    """
    Detects exciting moments using ONLY audio analysis.
    No video frame scanning — fastest detection method.

    Gunshots, explosions, and combat sounds produce sharp volume spikes
    well above ambient game audio. This detector finds those spikes
    and groups them into highlight clips.
    """

    def __init__(self, game_id="league_of_legends", profile=None):
        if profile is None:
            from analysis.game_profiles import get_profile
            profile = self.profile = get_profile(game_id)
        else:
            self.profile = profile

        self.threshold_db = self.profile.get("audio_threshold_db", -8)
        self.ceiling_db = self.profile.get("audio_ceiling_db", -1)
        self.min_spike_gap = 1.0  # seconds between distinct spikes

    def analyze_video(self, video_path, progress_callback=None):
        """
        Analyze a video file using only audio and return highlight timestamps.

        Returns:
            List of dicts: [{"timestamp": float, "duration": float,
                             "label": str, "confidence": float}, ...]
        """
        if progress_callback:
            progress_callback(0.05)

        print("  [Audio] Extracting audio levels from video...")
        levels = self._extract_audio_levels(video_path)

        if not levels:
            print("  [Audio] No audio data found")
            if progress_callback:
                progress_callback(1.0)
            return []

        if progress_callback:
            progress_callback(0.6)

        # Score each second
        scores = []
        for sec in sorted(levels.keys()):
            level = levels[sec]
            score = self._db_to_score(level)
            label = self._classify_level(level)
            scores.append({"score": score, "label": label, "timestamp": float(sec)})

        # Find the max timestamp for duration
        duration = max(levels.keys()) + 1 if levels else 0

        # Log top scores
        top = sorted(scores, key=lambda s: s["score"], reverse=True)[:10]
        print(f"  [Audio] Analyzed {len(levels)} seconds of audio")
        print(f"  [Audio] Threshold: {self.threshold_db} dB, ceiling: {self.ceiling_db} dB")
        loud_count = sum(1 for s in scores if s["score"] > 0)
        print(f"  [Audio] Found {loud_count} loud seconds")
        score_strs = [f'{s["score"]:.2f}@{int(s["timestamp"])}s({s["label"]})' for s in top[:5]]
        print(f"  [Audio] Top: {score_strs}")

        if progress_callback:
            progress_callback(0.8)

        highlights = self._find_highlights(scores, duration)

        if progress_callback:
            progress_callback(1.0)

        print(f"  [Audio] Found {len(highlights)} highlights")
        for h in highlights:
            print(f"  [Audio]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s, conf:{h['confidence']})")

        return highlights

    def _extract_audio_levels(self, video_path):
        """Extract per-second peak audio levels using ffmpeg astats."""
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
            print(f"  [Audio] ffmpeg failed: {e}")
            return {}

        if result.returncode != 0:
            print(
                f"  [Audio] ffmpeg error: "
                f"{result.stderr[:200]}"
            )
            return {}

        levels = {}
        current_time = 0.0

        for line in result.stdout.splitlines():
            line = line.strip()

            # FFmpeg outputs timestamp headers like:
            # frame:123 pts:125952 pts_time:2.856054
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

                    # FFmpeg reports complete silence as -inf.
                    if value.lower() == "-inf":
                        continue

                    level = float(value)
                    sec = int(current_time)

                    # Multiple audio frames can occur within one second.
                    # Keep the loudest measurement for that second.
                    if (
                        sec not in levels
                        or level > levels[sec]
                    ):
                        levels[sec] = level

                except (ValueError, IndexError):
                    pass

        return levels

    def _db_to_score(self, level_db):
        """Convert a dB level to a 0-1 score."""
        if level_db < self.threshold_db:
            return 0.0
        raw = (level_db - self.threshold_db) / max(self.ceiling_db - self.threshold_db, 1)
        return min(max(raw, 0.0), 1.0)

    def _classify_level(self, level_db):
        """Classify a dB level into a human-readable label."""
        if level_db >= -3:
            return "Loud Combat"
        elif level_db >= -6:
            return "Gunfire/Explosion"
        elif level_db >= -10:
            return "Combat Audio"
        elif level_db >= self.threshold_db:
            return "Ambient Activity"
        else:
            return "Ambient"

    def _find_highlights(self, scores, duration):
        """Group loud seconds into highlight windows."""
        if not scores:
            return []

        intensity_threshold = self.profile.get("intensity_threshold", 0.35)

        # Find seconds above threshold
        loud_seconds = [s for s in scores if s["score"] >= intensity_threshold]

        if not loud_seconds:
            # Fallback: take the loudest moments, but be selective
            # Only fall back if the top moments are genuinely above-average loud
            sorted_scores = sorted(scores, key=lambda s: s["score"], reverse=True)
            fallback_ratio = self.profile.get("fallback_threshold_ratio", 0.50)
            fallback_threshold = intensity_threshold * fallback_ratio
            # Only take top 3 and require genuine audio activity above the fallback
            loud_seconds = [s for s in sorted_scores[:3] if s["score"] >= fallback_threshold
                           and s["label"] not in ("Ambient", "Ambient Activity")]

        if not loud_seconds:
            return []

        # Group nearby loud seconds into clusters
        loud_seconds.sort(key=lambda s: s["timestamp"])
        merge_gap = self.profile.get("merge_gap", 8)

        clusters = []
        current = {
            "start": loud_seconds[0]["timestamp"],
            "end": loud_seconds[0]["timestamp"],
            "peak_score": loud_seconds[0]["score"],
            "label": loud_seconds[0]["label"],
            "scores": [loud_seconds[0]["score"]],
        }

        for s in loud_seconds[1:]:
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

        # Convert clusters to highlight format
        highlights = []
        for cluster in clusters:
            raw_duration = cluster["end"] - cluster["start"]
            min_dur = self.profile.get("min_clip_duration", 20)
            max_dur = self.profile.get("max_clip_duration", 60)
            extension = self.profile.get("clip_extension", 10)
            clip_duration = max(min_dur, min(max_dur, raw_duration + extension))

            avg_score = sum(cluster["scores"]) / len(cluster["scores"])
            confidence = min(avg_score * 1.5, 1.0)

            highlights.append({
                "timestamp": cluster["start"],
                "duration": clip_duration,
                "pre_pad": self.profile.get("pre_pad", 8),
                "label": cluster["label"],
                "confidence": round(confidence, 2),
            })

        highlights.sort(key=lambda h: h["timestamp"])
        return highlights
