import cv2
import os

from analysis.game_profiles import get_profile

from analysis.video_reader import VideoReader


class YoloLocalAnalyzer:
    """
    Runs a local YOLOv11 .pt model on video frames using ultralytics.
    No API key needed — works fully offline.
    """

    SAMPLE_INTERVAL = 1.0  # seconds between sampled frames

    def __init__(self, game_id="league_of_legends", model_path=None):
        self.profile = get_profile(game_id)
        # Default: look for best.pt in the models/ folder
        if model_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base, "models", "best.pt")
        self.model_path = model_path

    def analyze_video(self, video_path, progress_callback=None):
        """
        Run local YOLO inference on sampled video frames and build highlights.

        Uses VideoReader.iter_sampled() so skipped source frames are advanced
        with grab() rather than fully decoded.

        Args:
            video_path: Path to the video file
            progress_callback: Callback with (0-1) progress

        Returns:
            List of highlight dicts with timestamps, ready for clip extraction
        """
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            )

        if not os.path.exists(self.model_path):
            raise RuntimeError(
                f"YOLO model not found at {self.model_path}. "
                f"Place your best.pt file in the models/ folder."
            )

        # DirectML setup for AMD GPU.
        try:
            import onnxruntime as ort

            _orig_session = ort.InferenceSession

            def _dml_session(path_or_bytes, *args, **kwargs):
                kwargs["providers"] = [
                    "DmlExecutionProvider",
                    "CPUExecutionProvider"
                ]
                kwargs["provider_options"] = [
                    {"device_id": 0},
                    {}
                ]

                return _orig_session(
                    path_or_bytes,
                    *args,
                    **kwargs
                )

            ort.InferenceSession = _dml_session

        except Exception:
            pass

        model = YOLO(
            self.model_path
            if self.model_path.endswith(".onnx")
            else "models/best.onnx"
        )

        reader = VideoReader(video_path)

        fps = reader.fps
        total_frames = reader.frame_count
        duration = reader.duration

        from analysis.video_utils import frame_interval_for

        frame_skip = frame_interval_for(
            fps,
            sample_interval_sec=self.SAMPLE_INTERVAL
        )

        frames_to_analyze = max(
            1,
            total_frames // frame_skip
        )

        print(
            f"  [YoloLocal] Analyzing {video_path} "
            f"({duration:.0f}s, sampling every "
            f"{self.SAMPLE_INTERVAL}s)"
        )

        print(
            f"  [YoloLocal] Using model: "
            f"{self.model_path}"
        )

        frame_results = []
        analyzed = 0

        with reader:

            # Skip unused source frames with grab() and decode only
            # the frames that will actually be sent to YOLO.
            for video_frame in reader.iter_sampled(frame_skip):

                frame = video_frame.image
                frame_idx = video_frame.index
                timestamp = frame_idx / fps

                try:
                    results = model(
                        frame,
                        verbose=False
                    )

                    score = self._score_result(
                        results
                    )

                    label = self._label_result(
                        results
                    )

                except Exception as e:
                    print(
                        f"  [YoloLocal] Inference error "
                        f"at {timestamp:.1f}s: {e}"
                    )

                    score = 0.0
                    label = "error"

                frame_results.append({
                    "timestamp": timestamp,
                    "score": score,
                    "label": label,
                })

                analyzed += 1

                # Keep approximately the same 10-second diagnostic
                # reporting cadence as the original implementation.
                if analyzed % 10 == 0:
                    print(
                        f"  [YoloLocal] {timestamp:.1f}s - "
                        f"score:{score:.2f} label:{label}"
                    )

                if progress_callback:
                    progress_callback(
                        min(
                            analyzed / frames_to_analyze,
                            1.0
                        )
                    )

        if progress_callback:
            progress_callback(1.0)

        print(
            f"  [YoloLocal] Done: "
            f"{len(frame_results)} frames analyzed"
        )

        if not frame_results:
            return []

        return self._build_highlights(
            frame_results
        )

    def _score_result(self, results):
        """Score a frame based on YOLO detection results."""
        if not results or len(results) == 0:
            return 0.0

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return 0.0

        confidences = boxes.conf.cpu().numpy().tolist()
        if not confidences:
            return 0.0

        avg_conf = sum(confidences) / len(confidences)
        count_bonus = min(len(confidences) / 5.0, 1.0)
        score = avg_conf * 0.6 + count_bonus * 0.4

        return round(min(score, 1.0), 3)

    def _label_result(self, results):
        """Generate a human-readable label from YOLO detections."""
        if not results or len(results) == 0:
            return "Detection"

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return "Detection"

        labels = []
        names = result.names  # class index -> name mapping
        for cls_id in boxes.cls.cpu().numpy().tolist()[:3]:
            cls_name = names.get(int(cls_id), "")
            if cls_name and cls_name not in labels:
                labels.append(cls_name)

        return " / ".join(labels) if labels else "Detection"

    def _build_highlights(self, frame_results):
        """Convert scored frames into highlight clips."""
        intensity_threshold = self.profile.get("intensity_threshold", 0.35)

        frame_results.sort(key=lambda r: r["timestamp"])

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

        print(f"  [YoloLocal] Found {len(merged)} highlight(s)")
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
