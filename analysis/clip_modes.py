"""
Clip Modes — orchestration enum for Auto-Clipper detection strategies.

Each mode picks which signal(s) drive highlight detection:
  CV     : pixel analysis only (muzzle flash, damage vignette, audio peaks)
  YOLO   : neural object detection only (raiders, bosses, turrets)
  VOICE  : "clip it" / "clip that" speech triggers — scans the VOD's audio
           track via `analysis.clip_trigger_detector.ClipTriggerDetector` and
           extracts the N seconds preceding each trigger.
  HYBRID : CV + YOLO running in parallel, union-scored (best for VODs)
  ALL    : every signal on — CV + YOLO + voice triggers

Mode selection is surfaced in the web UI under the "Pick your clipping mode"
card. The analyzer reads `self.clip_mode` and gates detectors accordingly.
"""

from enum import Enum


class ClipMode(str, Enum):
    CV = "cv"
    YOLO = "yolo"
    VOICE = "voice"
    HYBRID = "hybrid"
    ALL = "all"

    @classmethod
    def parse(cls, value):
        """Lenient parse — accepts strings, enum instances, or None (→ HYBRID)."""
        if value is None:
            return cls.HYBRID
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            return cls.HYBRID

    @property
    def uses_cv(self) -> bool:
        return self in (ClipMode.CV, ClipMode.HYBRID, ClipMode.ALL)

    @property
    def uses_yolo(self) -> bool:
        return self in (ClipMode.YOLO, ClipMode.HYBRID, ClipMode.ALL)

    @property
    def uses_voice(self) -> bool:
        return self in (ClipMode.VOICE, ClipMode.ALL)

    @property
    def is_live(self) -> bool:
        """VOICE + ALL require a live audio/video source and rolling buffer."""
        return self in (ClipMode.VOICE, ClipMode.ALL)
