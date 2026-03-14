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

        print(f"  [AI] Sampling {total_samples} frames from {duration:.0f}s video (every {sample_interval_sec}s)")

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

        # Analyze frames individually (batching causes issues with API)
        all_results = []
        error_count = 0
        last_error = ""

        for i, frame_data in enumerate(frames_data):
            result = self._analyze_single(frame_data)
            all_results.append(result)

            if result.get("_error"):
                error_count += 1
                last_error = result.get("reason", "Unknown error")

            if progress_callback:
                progress_callback((i + 1) / len(frames_data))

        # Report error stats
        success_count = len(all_results) - error_count
        print(f"  [AI] Results: {success_count}/{len(all_results)} frames analyzed successfully")
        if error_count > 0:
            print(f"  [AI] WARNING: {error_count} frames failed - last error: {last_error}")

        # If ALL frames failed, raise so the user sees the actual error
        if error_count == len(all_results) and last_error:
            raise Exception(f"AI analysis failed for all frames: {last_error}")

        # Filter to exciting moments and build highlights
        highlights = self._build_highlights(all_results, sample_interval_sec)
        return highlights

    def _analyze_single(self, frame_data):
        """Analyze a single frame with Grok, with retry on transient errors."""
        ts = frame_data["timestamp"]
        retries = 2

        for attempt in range(retries + 1):
            try:
                result = self._call_grok(frame_data["b64"])
                result["timestamp"] = ts
                print(f"  [AI] {ts:.0f}s - score:{result.get('score',0)} exciting:{result.get('exciting')} - {result.get('label','')}")
                return result
            except Exception as e:
                error_str = str(e)
                if attempt < retries and ("429" in error_str or "500" in error_str or "503" in error_str or "timeout" in error_str.lower()):
                    import time
                    wait = 2 ** (attempt + 1)
                    print(f"  [AI] {ts:.0f}s - retrying in {wait}s ({error_str[:80]})")
                    time.sleep(wait)
                    continue
                print(f"  [AI] {ts:.0f}s - ERROR: {e}")
                return {
                    "timestamp": ts,
                    "exciting": False,
                    "score": 0,
                    "label": "Analysis failed",
                    "reason": error_str,
                    "_error": True,
                }

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
            # Strip ```json or ``` wrapper
            lines = content.split("\n")
            # Remove first and last ``` lines
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            content = "\n".join(json_lines).strip()

        # Try to extract JSON object if mixed with text
        if not content.startswith("{"):
            # Look for JSON object in the response
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end + 1]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Grok returned non-JSON — try to interpret as text
            print(f"  [AI] Non-JSON response: {content[:100]}")
            # Heuristic: if it mentions combat/fighting/shooting, consider it exciting
            lower = content.lower()
            has_action = any(w in lower for w in ["combat", "fight", "shoot", "explos", "kill", "attack", "gunfire", "battle"])
            return {
                "exciting": has_action,
                "score": 0.5 if has_action else 0.0,
                "label": content[:50] if has_action else "Non-combat",
                "reason": "Parsed from text response",
            }

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
