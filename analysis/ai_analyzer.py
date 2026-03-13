import os
import cv2
import base64
import json
import urllib.request
import urllib.error

from analysis.game_profiles import get_profile


class GrokVisionAnalyzer:
    """
    Uses xAI's Grok vision API to analyze sampled video frames
    and identify exciting gameplay moments using game-specific prompts.
    """

    API_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, api_key, game_id="arc_raiders"):
        self.api_key = api_key
        self.profile = get_profile(game_id)

    def analyze_frames(self, video_path, sample_interval_sec=10, progress_callback=None):
        """
        Sample frames from the video and send them to Grok for analysis.

        Args:
            video_path: Path to the video file
            sample_interval_sec: Seconds between sampled frames
            progress_callback: Callback with (0-1) progress

        Returns:
            List of highlight dicts with timestamps
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        frame_interval = int(fps * sample_interval_sec)
        total_samples = total_frames // frame_interval if frame_interval > 0 else 0

        # Collect sampled frames
        frames_data = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / fps
                # Encode frame as JPEG base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                b64 = base64.b64encode(buffer).decode('utf-8')
                frames_data.append({
                    "timestamp": timestamp,
                    "b64": b64,
                })

            frame_idx += 1

        cap.release()

        if not frames_data:
            return []

        # Analyze frames in batches (send 4 at a time to reduce API calls)
        batch_size = 4
        all_results = []
        total_batches = (len(frames_data) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(frames_data), batch_size):
            batch = frames_data[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size

            results = self._analyze_batch(batch)
            all_results.extend(results)

            if progress_callback:
                progress_callback((batch_num + 1) / total_batches)

        # Filter to exciting moments and build highlights
        highlights = self._build_highlights(all_results, sample_interval_sec)
        return highlights

    def _analyze_batch(self, frames_batch):
        """Send a batch of frames to Grok for analysis."""
        results = []

        for frame_data in frames_batch:
            try:
                result = self._call_grok(frame_data["b64"])
                result["timestamp"] = frame_data["timestamp"]
                results.append(result)
                ts = frame_data["timestamp"]
                print(f"  [AI] {ts:.0f}s - score:{result.get('score',0)} exciting:{result.get('exciting')} - {result.get('label','')}")
            except Exception as e:
                print(f"  [AI] {frame_data['timestamp']:.0f}s - ERROR: {e}")
                results.append({
                    "timestamp": frame_data["timestamp"],
                    "exciting": False,
                    "score": 0,
                    "label": "Analysis failed",
                    "reason": str(e),
                })

        return results

    def _call_grok(self, image_b64):
        """Call xAI Grok vision API with a single frame."""
        system_prompt = self.profile.get("ai_system_prompt", "Analyze this gameplay frame.")
        user_prompt = self.profile.get("ai_user_prompt", "Is this an exciting moment?")

        payload = {
            "model": "grok-2-vision-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                },
            ],
            "max_tokens": 150,
            "temperature": 0.3,
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise Exception(f"Grok API {e.code}: {body[:200]}")

        content = result["choices"][0]["message"]["content"].strip()

        # Parse JSON from response (handle markdown code blocks)
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        # Normalize types
        parsed["exciting"] = bool(parsed.get("exciting", False))
        parsed["score"] = float(parsed.get("score", 0))
        return parsed

    def _build_highlights(self, results, sample_interval):
        """Convert analysis results into highlight timestamps."""
        exciting = [r for r in results if r.get("exciting") and r.get("score", 0) >= 0.4]

        if not exciting:
            # Fall back to top scored frames
            sorted_results = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
            exciting = [r for r in sorted_results[:5] if r.get("score", 0) >= 0.2]

        if not exciting:
            return []

        # Merge nearby highlights
        exciting.sort(key=lambda r: r["timestamp"])
        merged = []
        current = None

        merge_gap = self.profile.get("merge_gap", 15)

        for result in exciting:
            if current is None:
                current = {
                    "timestamp": result["timestamp"],
                    "end_time": result["timestamp"] + sample_interval,
                    "label": result.get("label", "Highlight"),
                    "confidence": result.get("score", 0.5),
                    "peak_score": result.get("score", 0.5),
                }
            elif result["timestamp"] <= current["end_time"] + merge_gap:
                current["end_time"] = result["timestamp"] + sample_interval
                if result.get("score", 0) > current["peak_score"]:
                    current["peak_score"] = result["score"]
                    current["label"] = result.get("label", current["label"])
                current["confidence"] = max(current["confidence"], result.get("score", 0.5))
            else:
                merged.append(self._finalize(current))
                current = {
                    "timestamp": result["timestamp"],
                    "end_time": result["timestamp"] + sample_interval,
                    "label": result.get("label", "Highlight"),
                    "confidence": result.get("score", 0.5),
                    "peak_score": result.get("score", 0.5),
                }

        if current:
            merged.append(self._finalize(current))

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
