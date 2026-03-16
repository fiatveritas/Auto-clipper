import subprocess
import json
import os
import tempfile
import re


# Default trigger patterns - users can customize these
DEFAULT_TRIGGER_PHRASES = [
    "clip that",
    "clip this",
    "clip it",
    "clip me",
    "clip",
]

# Words that follow "clip" and indicate it's NOT a trigger
CLIP_FALSE_POSITIVES = {"ping", "ped", "per", "board", "s", "ping", "art"}


class ClipTriggerDetector:
    """
    Detects moments where someone says 'clip that', 'clip this', 'clip it',
    or just 'clip' in a video's audio track.

    Supports multiple backends:
    1. faster-whisper (fastest, recommended) - pip install faster-whisper
    2. openai-whisper (original) - pip install openai-whisper
    3. Graceful fallback with clear install instructions

    For each detected trigger phrase, it creates a highlight covering the
    preceding N seconds (default 30) so the exciting moment is captured.
    """

    def __init__(self, clip_duration=30, pre_pad=5, model_size="base",
                 custom_triggers=None, language="en"):
        self.clip_duration = clip_duration
        self.pre_pad = pre_pad
        self.model_size = model_size
        self.language = language
        self._backend = None  # "faster-whisper", "openai-whisper", or None

        # Build trigger patterns from defaults or custom list
        triggers = custom_triggers if custom_triggers else DEFAULT_TRIGGER_PHRASES
        self._build_trigger_pattern(triggers)

    def _build_trigger_pattern(self, triggers):
        """Build regex pattern from trigger phrase list."""
        # Separate multi-word phrases from single words
        multi_word = []
        single_words = []
        for t in triggers:
            t = t.strip().lower()
            if not t:
                continue
            if " " in t:
                multi_word.append(re.escape(t))
            else:
                single_words.append(re.escape(t))

        parts = []
        # Multi-word phrases first (more specific)
        for phrase in multi_word:
            # Allow flexible whitespace between words
            parts.append(r'\b' + phrase.replace(r'\ ', r'\s+') + r'\b')

        # Single words with false-positive exclusion
        for word in single_words:
            parts.append(
                r'\b' + word + r'\b(?!\s*(?:' +
                '|'.join(re.escape(fp) for fp in CLIP_FALSE_POSITIVES) +
                r'))'
            )

        self._trigger_pattern = re.compile('|'.join(parts), re.IGNORECASE) if parts else None
        self._trigger_words = set(w.strip().lower().split()[0] for w in triggers if w.strip())

    def get_backend(self):
        """Detect which speech-to-text backend is available."""
        if self._backend is not None:
            return self._backend

        # Try faster-whisper first (4x faster, less memory)
        try:
            import faster_whisper
            self._backend = "faster-whisper"
            print("  [ClipTrigger] Using faster-whisper backend (recommended)")
            return self._backend
        except ImportError:
            pass

        # Try openai-whisper
        try:
            import whisper
            self._backend = "openai-whisper"
            print("  [ClipTrigger] Using openai-whisper backend")
            return self._backend
        except ImportError:
            pass

        self._backend = ""
        return self._backend

    def is_available(self):
        """Check if any whisper backend is installed."""
        return bool(self.get_backend())

    def get_install_instructions(self):
        """Return install instructions for the best backend."""
        return (
            "No speech-to-text backend found. Install one:\n"
            "  pip install faster-whisper   (recommended, 4x faster)\n"
            "  pip install openai-whisper   (original, more compatible)"
        )

    def analyze_video(self, video_path, progress_callback=None):
        """
        Transcribe the video audio and find clip trigger phrases.

        Returns list of highlights where someone said a trigger phrase.
        Each highlight covers the clip_duration seconds BEFORE the trigger.
        """
        if progress_callback:
            progress_callback(0.05)

        backend = self.get_backend()
        if not backend:
            print(f"  [ClipTrigger] {self.get_install_instructions()}")
            if progress_callback:
                progress_callback(1.0)
            return []

        print("  [ClipTrigger] Extracting audio for speech detection...")

        # Extract audio as 16kHz mono WAV
        audio_path = self._extract_audio(video_path)
        if not audio_path:
            if progress_callback:
                progress_callback(1.0)
            return []

        if progress_callback:
            progress_callback(0.15)

        try:
            print(f"  [ClipTrigger] Transcribing with {backend} (model: {self.model_size})...")

            if backend == "faster-whisper":
                segments = self._run_faster_whisper(audio_path, progress_callback)
            else:
                segments = self._run_openai_whisper(audio_path, progress_callback)

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
        finally:
            # Clean up temp audio file
            try:
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
            except OSError:
                pass

    def _extract_audio(self, video_path):
        """Extract audio as 16kHz mono WAV for Whisper."""
        audio_path = video_path + ".whisper_temp.wav"
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            print("  [ClipTrigger] Audio extraction failed")
            return None
        return audio_path

    def _run_faster_whisper(self, audio_path, progress_callback=None):
        """Run faster-whisper Python API (4x faster than openai-whisper)."""
        from faster_whisper import WhisperModel

        # Use int8 quantization on CPU for speed, float16 on GPU
        model = WhisperModel(
            self.model_size,
            device="auto",
            compute_type="auto",
        )

        segments_iter, info = model.transcribe(
            audio_path,
            language=self.language,
            word_timestamps=True,
            vad_filter=True,         # Skip silent sections (huge speedup)
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        if progress_callback:
            progress_callback(0.3)

        # Convert to standard segment format
        segments = []
        total_duration = info.duration or 1
        for seg in segments_iter:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                    })

            segments.append({
                "text": seg.text,
                "start": seg.start,
                "end": seg.end,
                "words": words,
            })

            # Update progress based on how far through the audio we are
            if progress_callback and total_duration > 0:
                pct = min(0.85, 0.3 + (seg.end / total_duration) * 0.55)
                progress_callback(pct)

        return segments

    def _run_openai_whisper(self, audio_path, progress_callback=None):
        """Run openai-whisper Python API with word timestamps."""
        import whisper

        model = whisper.load_model(self.model_size)

        if progress_callback:
            progress_callback(0.25)

        result = model.transcribe(
            audio_path,
            language=self.language,
            word_timestamps=True,
        )

        if progress_callback:
            progress_callback(0.8)

        # Convert to standard format
        segments = []
        for seg in result.get("segments", []):
            words = []
            for w in seg.get("words", []):
                words.append({
                    "word": w.get("word", ""),
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                })
            segments.append({
                "text": seg.get("text", ""),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "words": words,
            })

        return segments

    def _find_triggers(self, segments):
        """
        Search transcription segments for clip trigger phrases.
        Returns list of {'timestamp': float, 'text': str} for each trigger.
        """
        if not self._trigger_pattern:
            return []

        triggers = []

        for seg in segments:
            text = seg.get("text", "")
            end = seg.get("end", 0)

            # Check if segment contains a trigger phrase
            match = self._trigger_pattern.search(text)
            if not match:
                continue

            # Try to get word-level timestamp for more accuracy
            trigger_time = end  # Default: end of segment
            words = seg.get("words", [])
            for word_info in words:
                word_text = word_info.get("word", "").strip().lower().rstrip("!?.,")
                if word_text in self._trigger_words:
                    trigger_time = word_info.get("end", word_info.get("start", end))
                    break

            triggers.append({
                "timestamp": trigger_time,
                "text": text.strip(),
            })

        return triggers

    def _triggers_to_highlights(self, triggers, video_path):
        """Convert trigger timestamps to highlight dicts covering preceding seconds."""
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
