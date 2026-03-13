import os
import cv2
import base64
import json
import urllib.request
import urllib.error


class GrokVisionAnalyzer:
    """
    Uses xAI's Grok vision API to analyze sampled video frames
    and identify exciting Arc Raiders gameplay moments.
    """

    API_URL = "https://api.x.ai/v1/chat/completions"

    SYSTEM_PROMPT = """You are an expert Arc Raiders gameplay analyst. You analyze screenshots from Arc Raiders streams to identify exciting moments worth clipping.

Look for these types of highlights:
- **Kills**: Player eliminating Arc enemies (robots), leapers, or other threats
- **Combat**: Active gunfights, shooting at enemies, taking fire
- **Arc Encounters**: Large Arc enemy appearances, boss-like encounters
- **Explosions**: Big explosions, grenades, environmental destruction
- **Close Calls**: Player at low health, narrow escapes
- **Loot/Rewards**: Finding rare loot, extraction moments
- **Deaths**: Player dying (also exciting/funny content)

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.0 = nothing happening, 0.3 = minor action, 0.6 = good combat, 0.8 = kill/major moment, 1.0 = insane play"""

    def __init__(self, api_key):
        self.api_key = api_key

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
            except Exception as e:
                # If API call fails, skip this frame
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
        payload = {
            "model": "grok-2-vision-latest",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
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
                            "text": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
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

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result["choices"][0]["message"]["content"].strip()

        # Parse JSON from response (handle markdown code blocks)
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        return json.loads(content)

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

        for result in exciting:
            if current is None:
                current = {
                    "timestamp": result["timestamp"],
                    "end_time": result["timestamp"] + sample_interval,
                    "label": result.get("label", "Highlight"),
                    "confidence": result.get("score", 0.5),
                    "peak_score": result.get("score", 0.5),
                }
            elif result["timestamp"] <= current["end_time"] + 15:
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
        duration = max(20, min(60, duration + 10))

        return {
            "timestamp": highlight["timestamp"],
            "duration": duration,
            "pre_pad": 8,
            "label": highlight["label"],
            "confidence": round(min(highlight["confidence"], 1.0), 2),
        }
