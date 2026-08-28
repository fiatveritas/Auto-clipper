import cv2

from analysis.game_profiles import get_profile
from analysis.video_reader import VideoReader


class RoboflowModelAnalyzer:
    """
    Uses Roboflow's inference SDK direct model inference (CLIENT.infer())
    to detect objects in video frames and identify gameplay highlights.

    Simpler than the WebRTC workflow approach — just sends frames to a
    trained model and gets back detection predictions.
    """

    DEFAULT_MODEL_ID = "arc-raiders-05arl-bgcvo/1"
    SAMPLE_INTERVAL = 1.0  # seconds between sampled frames

    def __init__(self, api_key, game_id="league_of_legends", model_id=None):
        self.api_key = api_key
        self.profile = get_profile(game_id)
        self.model_id = model_id or self.DEFAULT_MODEL_ID

    def analyze_video(self, video_path, progress_callback=None):
        """
        Extract sampled frames from video, run them through the Roboflow
        model in bounded batches, and build highlights from detection
        results.

        Uses:
            - VideoReader.iter_sampled() to avoid decoding unused frames
            - batched Roboflow inference
            - bounded concurrent HTTP requests

        Returns:
            List of highlight dicts with timestamps, ready for clip extraction
        """
        from inference_sdk import (
            InferenceHTTPClient,
            InferenceConfiguration,
        )

        from analysis.video_utils import frame_interval_for

        # --------------------------------------------------------------
        # Roboflow client
        #
        # Hosted inference benefits from multiple concurrent requests.
        # Keep this conservative so we do not create an excessive number
        # of simultaneous HTTP requests.
        # --------------------------------------------------------------
        client = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=self.api_key,
        )

        configuration = InferenceConfiguration(
            max_concurrent_requests=4,
            max_batch_size=4,
        )

        client.configure(configuration)

        # --------------------------------------------------------------
        # Video setup
        # --------------------------------------------------------------
        reader = VideoReader(video_path)

        fps = reader.fps
        total_frames = reader.frame_count
        duration = reader.duration

        frame_skip = frame_interval_for(
            fps,
            sample_interval_sec=self.SAMPLE_INTERVAL
        )

        frames_to_analyze = max(
            1,
            total_frames // frame_skip
        )

        print(
            f"  [RoboflowModel] Analyzing {video_path} "
            f"({duration:.0f}s, sampling every "
            f"{self.SAMPLE_INTERVAL}s)"
        )

        print(
            "  [RoboflowModel] "
            "Batched inference enabled "
            "(batch=4, concurrent=4)"
        )

        frame_results = []
        analyzed = 0

        # --------------------------------------------------------------
        # Batch settings
        #
        # We intentionally keep only a small number of frames in memory.
        # --------------------------------------------------------------
        batch_size = 4

        batch_frames = []
        batch_timestamps = []

        # --------------------------------------------------------------
        # Helper used whenever a batch is ready.
        # --------------------------------------------------------------
        def process_batch():

            nonlocal analyzed

            if not batch_frames:
                return

            try:

                results = client.infer(
                    batch_frames,
                    model_id=self.model_id
                )

                # A single-image response may be returned as a dict.
                # Normalize everything to a list.
                if isinstance(results, dict):
                    results = [results]

                if not isinstance(results, list):
                    results = [results]

                # ------------------------------------------------------
                # Protect against an unexpected response count.
                # ------------------------------------------------------
                if len(results) != len(batch_frames):

                    print(
                        "  [RoboflowModel] Warning: "
                        f"sent {len(batch_frames)} frames but "
                        f"received {len(results)} result(s)"
                    )

                # ------------------------------------------------------
                # Process every frame in this batch.
                # ------------------------------------------------------
                for i, timestamp in enumerate(
                    batch_timestamps
                ):

                    if i < len(results):

                        result = results[i]

                        score = self._score_result(
                            result
                        )

                        label = self._label_result(
                            result
                        )

                    else:

                        score = 0.0
                        label = "error"

                    frame_results.append({
                        "timestamp": timestamp,
                        "score": score,
                        "label": label,
                    })

                    analyzed += 1

                    # ----------------------------------------------
                    # Diagnostic cadence
                    # ----------------------------------------------
                    if analyzed % 10 == 0:

                        print(
                            f"  [RoboflowModel] "
                            f"{timestamp:.1f}s - "
                            f"score:{score:.2f} "
                            f"label:{label}"
                        )

                    # ----------------------------------------------
                    # Progress
                    # ----------------------------------------------
                    if progress_callback:

                        progress_callback(
                            min(
                                analyzed
                                / frames_to_analyze,
                                1.0
                            )
                        )

            except Exception as e:

                # ------------------------------------------------------
                # If an entire batch fails, preserve timestamps and
                # record errors rather than aborting the video.
                # ------------------------------------------------------
                print(
                    "  [RoboflowModel] "
                    f"Batch inference error: {e}"
                )

                for timestamp in batch_timestamps:

                    frame_results.append({
                        "timestamp": timestamp,
                        "score": 0.0,
                        "label": "error",
                    })

                    analyzed += 1

                    if progress_callback:

                        progress_callback(
                            min(
                                analyzed
                                / frames_to_analyze,
                                1.0
                            )
                        )

            finally:

                batch_frames.clear()
                batch_timestamps.clear()

        # --------------------------------------------------------------
        # Sample video and submit batches.
        # --------------------------------------------------------------
        with reader:

            for video_frame in reader.iter_sampled(
                frame_skip
            ):

                frame = video_frame.image
                frame_idx = video_frame.index

                timestamp = (
                    frame_idx / fps
                )

                batch_frames.append(frame)
                batch_timestamps.append(timestamp)

                # ------------------------------------------------------
                # Send a batch as soon as it reaches the configured size.
                # ------------------------------------------------------
                if len(batch_frames) >= batch_size:
                    process_batch()

            # ----------------------------------------------------------
            # Flush the final partial batch.
            # ----------------------------------------------------------
            process_batch()

        # --------------------------------------------------------------
        # Completion
        # --------------------------------------------------------------
        if progress_callback:
            progress_callback(1.0)

        print(
            f"  [RoboflowModel] Done: "
            f"{len(frame_results)} frames analyzed"
        )

        if not frame_results:
            return []

        return self._build_highlights(
            frame_results
        )

    def _score_result(self, result):
        """Score a frame based on inference result. Higher = more exciting."""
        predictions = []

        if isinstance(result, dict):
            predictions = result.get("predictions", [])
        elif isinstance(result, list):
            predictions = result

        if not predictions:
            return 0.0

        confidences = []
        for p in predictions:
            if isinstance(p, dict):
                conf = p.get("confidence", 0)
                if isinstance(conf, (int, float)):
                    confidences.append(float(conf))

        if not confidences:
            return 0.0

        avg_conf = sum(confidences) / len(confidences)
        count_bonus = min(len(confidences) / 5.0, 1.0)
        score = avg_conf * 0.6 + count_bonus * 0.4

        return round(min(score, 1.0), 3)

    def _label_result(self, result):
        """Generate a human-readable label from detections."""
        predictions = []

        if isinstance(result, dict):
            predictions = result.get("predictions", [])
        elif isinstance(result, list):
            predictions = result

        labels = []
        for p in predictions[:3]:
            if isinstance(p, dict):
                cls_name = p.get("class", p.get("label", ""))
                if cls_name:
                    labels.append(cls_name)

        if labels:
            return " / ".join(dict.fromkeys(labels))
        return "Detection"

    def _build_highlights(self, frame_results):
        """Convert scored frames into highlight clips."""
        intensity_threshold = self.profile.get("intensity_threshold", 0.35)

        frame_results.sort(key=lambda r: r["timestamp"])

        # Group into 3-second buckets
        bucket_size = 3.0
        buckets = {}
        for r in frame_results:
            bucket_key = int(r["timestamp"] / bucket_size)
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append(r)

        scored_windows = []
        for key in sorted(buckets.keys()):
            frames = buckets[key]
            avg_score = sum(f["score"] for f in frames) / len(frames)
            best = max(frames, key=lambda f: f["score"])
            scored_windows.append({
                "timestamp": key * bucket_size,
                "score": avg_score,
                "peak_score": best["score"],
                "label": best["label"],
            })

        exciting = [w for w in scored_windows if w["score"] >= intensity_threshold]

        if not exciting:
            fallback_ratio = self.profile.get("fallback_threshold_ratio", 0.3)
            min_score = intensity_threshold * fallback_ratio
            sorted_windows = sorted(scored_windows, key=lambda w: w["score"], reverse=True)
            exciting = [w for w in sorted_windows[:5] if w["score"] >= min_score]

        if not exciting:
            return []

        # Merge nearby highlights
        exciting.sort(key=lambda w: w["timestamp"])
        merge_gap = self.profile.get("merge_gap", 8)
        merged = []
        current = None

        for window in exciting:
            if current is None:
                current = {
                    "timestamp": window["timestamp"],
                    "end_time": window["timestamp"] + bucket_size,
                    "label": window["label"],
                    "confidence": window["score"],
                    "peak_score": window["peak_score"],
                }
            elif window["timestamp"] <= current["end_time"] + merge_gap:
                current["end_time"] = window["timestamp"] + bucket_size
                if window["peak_score"] > current["peak_score"]:
                    current["peak_score"] = window["peak_score"]
                    current["label"] = window["label"]
                current["confidence"] = max(current["confidence"], window["score"])
            else:
                merged.append(self._finalize(current))
                current = {
                    "timestamp": window["timestamp"],
                    "end_time": window["timestamp"] + bucket_size,
                    "label": window["label"],
                    "confidence": window["score"],
                    "peak_score": window["peak_score"],
                }

        if current:
            merged.append(self._finalize(current))

        print(f"  [RoboflowModel] Found {len(merged)} highlight(s)")
        return merged

    def _finalize(self, highlight):
        """Format a merged highlight for clip extraction."""
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
