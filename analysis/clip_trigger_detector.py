import subprocess
import json
import os
import tempfile
import re


class ClipTriggerDetector:
    """
    Detects moments where someone says 'clip that', 'clip this', 'clip it',
    or just 'clip' in a video's audio track using OpenAI Whisper.

    For each detected trigger phrase, it creates a highlight covering the
    preceding N seconds (default 30) so the exciting moment is captured.
    """

    def __init__(self, clip_duration=30, pre_pad=5):
        self.clip_duration = clip_duration
        self.pre_pad = pre_pad  # extra seconds before the trigger phrase
        self._whisper_available = None

    def is_available(self):
        """Check if whisper is installed and usable."""
        if self._whisper_available is not None:
            return self._whisper_available
        try:
            result = subprocess.run(
                ["whisper", "--help"],
                capture_output=True, timeout=10,
            )
            self._whisper_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Try the Python module form
            try:
                result = subprocess.run(
                    ["python3", "-m", "whisper", "--help"],
                    capture_output=True, timeout=10,
                )
                self._whisper_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._whisper_available = False
        return self._whisper_available

    def analyze_video(self, video_path, progress_callback=None):
        """
        Transcribe the video audio with Whisper and find clip trigger phrases.

        Returns list of highlights where someone said 'clip that/this/clip'.
        Each highlight covers the clip_duration seconds BEFORE the trigger.
        """
        if progress_callback:
            progress_callback(0.05)

        print("  [ClipTrigger] Extracting audio for speech detection...")

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.wav")

            # Extract audio as 16kHz mono WAV (what Whisper expects)
            extract_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                audio_path,
            ]
            result = subprocess.run(extract_cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                print(f"  [ClipTrigger] Audio extraction failed")
                if progress_callback:
                    progress_callback(1.0)
                return []

            if progress_callback:
                progress_callback(0.15)

            print("  [ClipTrigger] Running Whisper transcription (this may take a while)...")

            # Run Whisper and get word-level timestamps
            segments = self._run_whisper(audio_path, tmpdir, progress_callback)

            if progress_callback:
                progress_callback(0.9)

            # Find trigger phrases
            triggers = self._find_triggers(segments)
            print(f"  [ClipTrigger] Found {len(triggers)} clip trigger(s)")

            # Convert triggers to highlight format
            highlights = self._triggers_to_highlights(triggers, video_path)

            if progress_callback:
                progress_callback(1.0)

            return highlights

    def _run_whisper(self, audio_path, output_dir, progress_callback=None):
        """Run Whisper transcription and return segments with timestamps."""
        # Try whisper CLI first, fall back to python module
        for cmd_prefix in [["whisper"], ["python3", "-m", "whisper"]]:
            try:
                cmd = cmd_prefix + [
                    audio_path,
                    "--model", "base",
                    "--language", "en",
                    "--output_format", "json",
                    "--output_dir", output_dir,
                    "--word_timestamps", "True",
                ]
                result = subprocess.run(
                    cmd, capture_output=True, timeout=1800,  # 30 min max
                )
                if result.returncode == 0:
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        else:
            print("  [ClipTrigger] Whisper not available, falling back to ffmpeg subtitle detection")
            return self._fallback_keyword_scan(audio_path)

        if progress_callback:
            progress_callback(0.8)

        # Parse the JSON output
        json_path = os.path.join(output_dir, "audio.json")
        if not os.path.exists(json_path):
            print("  [ClipTrigger] No Whisper output found")
            return []

        try:
            with open(json_path) as f:
                data = json.load(f)
            return data.get("segments", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def _fallback_keyword_scan(self, audio_path):
        """
        Fallback when Whisper is not installed: use ffmpeg speech activity
        detection to find loud speech moments that could be 'clip' callouts.
        Returns empty list - this is a graceful degradation.
        """
        print("  [ClipTrigger] No speech-to-text available. Install openai-whisper: pip install openai-whisper")
        return []

    def _find_triggers(self, segments):
        """
        Search transcription segments for clip trigger phrases.
        Returns list of {'timestamp': float, 'text': str} for each trigger.
        """
        triggers = []
        # Pattern matches: "clip that", "clip this", "clip it", "clip me",
        # or standalone "clip" at word boundaries (not "clipping", "eclipse", etc.)
        pattern = re.compile(
            r'\bclip\s+(?:that|this|it|me)\b|\bclip\b(?!\s*(?:ping|ped|per|board|s\b))',
            re.IGNORECASE,
        )

        for seg in segments:
            text = seg.get("text", "")
            start = seg.get("start", 0)
            end = seg.get("end", 0)

            # Check if segment contains a trigger phrase
            match = pattern.search(text)
            if not match:
                continue

            # Try to get word-level timestamp for more accuracy
            trigger_time = end  # Default: end of segment
            words = seg.get("words", [])
            for word_info in words:
                word_text = word_info.get("word", "").strip().lower()
                if word_text in ("clip", "clip!",):
                    trigger_time = word_info.get("end", word_info.get("start", end))
                    break

            triggers.append({
                "timestamp": trigger_time,
                "text": text.strip(),
            })

        return triggers

    def _triggers_to_highlights(self, triggers, video_path):
        """Convert trigger timestamps to highlight dicts covering preceding seconds."""
        # Get video duration for bounds checking
        duration = self._get_duration(video_path)

        highlights = []
        min_gap = 10  # Minimum gap between triggers to avoid overlapping clips
        last_trigger_time = -999

        for trigger in triggers:
            t = trigger["timestamp"]

            # Skip if too close to a previous trigger
            if t - last_trigger_time < min_gap:
                continue

            # The highlight covers clip_duration seconds BEFORE the trigger
            clip_start = max(0, t - self.clip_duration)
            clip_end = min(t + self.pre_pad, duration) if duration else t + self.pre_pad

            highlights.append({
                "timestamp": clip_start + (clip_end - clip_start) / 2,
                "duration": clip_end - clip_start,
                "pre_pad": 0,  # Already computed the right window
                "label": f"Clip Trigger: \"{trigger['text'][:50]}\"",
                "confidence": 0.95,
                "trigger_time": round(t, 1),
            })
            last_trigger_time = t

        return highlights

    def _get_duration(self, video_path):
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 0
