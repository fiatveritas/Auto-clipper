import cv2

from analysis.game_profiles import get_profile



class RoboflowWorkflowAnalyzer:
    """
    Uses Roboflow's inference SDK WebRTC streaming to run a hosted workflow
    (detect-and-classify) on video frames and identify gameplay highlights.
    """

    def __init__(self, api_key, game_id="league_of_legends",
                 workspace="beanies-workspace",
                 workflow="detect-and-classify-3"):
        self.api_key = api_key
        self.profile = get_profile(game_id)
        self.workspace = workspace
        self.workflow = workflow

    def analyze_video(self, video_path, progress_callback=None):
        """
        Stream video through a Roboflow workflow and build highlights
        from detection/classification predictions.

        Args:
            video_path: Path to the video file
            progress_callback: Callback with (0-1) progress

        Returns:
            List of highlight dicts with timestamps, ready for clip extraction
        """
        from inference_sdk import InferenceHTTPClient
        from inference_sdk.webrtc import VideoFileSource, StreamConfig, VideoMetadata

        client = InferenceHTTPClient.init(
            api_url="https://serverless.roboflow.com",
            api_key=self.api_key,
        )

        source = VideoFileSource(video_path, realtime_processing=False)

        config = StreamConfig(
            stream_output=[],
            data_output=[
                "output_image",
                "predictions",
                "detection_predictions",
                "classification_predictions",
            ],
            requested_plan="webrtc-gpu-medium",
            requested_region="us",
        )

        session = client.webrtc.stream(
            source=source,
            workflow=self.workflow,
            workspace=self.workspace,
            image_input="image",
            config=config,
        )

        # Collect per-frame results
        frame_results = []
        total_frames_est = self._estimate_frames(video_path)

        @session.on_data()
        def on_data(data: dict, metadata: VideoMetadata):
            timestamp_ms = metadata.pts * metadata.time_base * 1000
            timestamp_sec = timestamp_ms / 1000.0

            score = self._score_frame(data)
            label = self._label_frame(data)

            frame_results.append({
                "timestamp": timestamp_sec,
                "frame_id": metadata.frame_id,
                "score": score,
                "label": label,
            })

            if progress_callback and total_frames_est > 0:
                progress_callback(min(metadata.frame_id / total_frames_est, 1.0))

            if metadata.frame_id % 50 == 0:
                print(f"  [Roboflow] Frame {metadata.frame_id} @ {timestamp_sec:.1f}s - score:{score:.2f} label:{label}")

        print(f"  [Roboflow] Starting workflow '{self.workflow}' on {video_path}")
        session.run()
        print(f"  [Roboflow] Processing complete: {len(frame_results)} frames analyzed")

        if progress_callback:
            progress_callback(1.0)

        if not frame_results:
            return []

        highlights = self._build_highlights(frame_results)
        return highlights

    def _estimate_frames(self, video_path):
        """Get total frame count for progress estimation."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return total

    def _score_frame(self, data):
        """
        Score a frame based on Roboflow workflow outputs.
        Higher score = more likely an exciting moment.
        """
        score = 0.0

        # Detection predictions — count and confidence of detected objects
        det_preds = data.get("detection_predictions", {})
        if isinstance(det_preds, dict):
            predictions = det_preds.get("predictions", [])
        elif isinstance(det_preds, list):
            predictions = det_preds
        else:
            predictions = []

        if predictions:
            # More detections and higher confidence = higher score
            confidences = [p.get("confidence", 0) for p in predictions if isinstance(p, dict)]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                count_bonus = min(len(confidences) / 5.0, 1.0)  # Cap at 5 detections
                score = max(score, avg_conf * 0.6 + count_bonus * 0.4)

        # Classification predictions — look for action-related classes
        cls_preds = data.get("classification_predictions", {})
        if isinstance(cls_preds, dict):
            top_conf = cls_preds.get("confidence", 0)
            if isinstance(top_conf, (int, float)) and top_conf > 0:
                score = max(score, float(top_conf))

        # Generic predictions key
        preds = data.get("predictions", {})
        if isinstance(preds, dict):
            pred_list = preds.get("predictions", [])
        elif isinstance(preds, list):
            pred_list = preds
        else:
            pred_list = []

        if pred_list:
            confidences = [p.get("confidence", 0) for p in pred_list if isinstance(p, dict)]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                score = max(score, avg_conf)

        return round(min(score, 1.0), 3)

    def _label_frame(self, data):
        """Generate a human-readable label from Roboflow predictions."""
        labels = []

        # From detection predictions
        det_preds = data.get("detection_predictions", {})
        if isinstance(det_preds, dict):
            predictions = det_preds.get("predictions", [])
        elif isinstance(det_preds, list):
            predictions = det_preds
        else:
            predictions = []

        for p in predictions[:3]:  # Top 3
            if isinstance(p, dict):
                cls_name = p.get("class", p.get("label", ""))
                if cls_name:
                    labels.append(cls_name)

        # From classification predictions
        cls_preds = data.get("classification_predictions", {})
        if isinstance(cls_preds, dict):
            top_class = cls_preds.get("top", cls_preds.get("class", ""))
            if top_class:
                labels.append(top_class)

        if labels:
            return " / ".join(dict.fromkeys(labels))  # Deduplicate preserving order
        return "Detection"

    def _build_highlights(self, frame_results):
        """Convert scored frame results into highlight clips."""
        intensity_threshold = self.profile.get("intensity_threshold", 0.35)

        # Sort by timestamp
        frame_results.sort(key=lambda r: r["timestamp"])

        if not frame_results:
            return []

        # Use a sliding window to smooth scores (3-second windows at ~30fps)
        # Group frames into 3-second buckets
        bucket_size = 3.0  # seconds
        buckets = {}
        for r in frame_results:
            bucket_key = int(r["timestamp"] / bucket_size)
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append(r)

        # Average score per bucket
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

        # Find windows above threshold
        exciting = [w for w in scored_windows if w["score"] >= intensity_threshold]

        if not exciting:
            # Fallback: top 5 windows
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

        print(f"  [Roboflow] Found {len(merged)} highlight(s)")
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
