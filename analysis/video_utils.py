"""
Shared helpers for video I/O used by every analyzer.

Extracted after the review caught 7+ copies of the NaN-safe fps guard
drifting apart (two files used `math.isnan`, five used `fps != fps`,
one used `or 30.0` which misses NaN entirely).
"""

from __future__ import annotations

from typing import Tuple

import cv2


def safe_fps(cap, default: float = 30.0) -> float:
    """Return a sanitized fps value from an opened cv2.VideoCapture.

    OpenCV returns NaN on some codec/container combinations; `NaN != NaN`
    is the identity check (cheaper than importing math.isnan). We also
    reject 0 and negatives which some MKV/WebM files produce.
    """
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps != fps or fps <= 0:
        return default
    return fps


def probe_video(cap, default_fps: float = 30.0) -> Tuple[float, int, float]:
    """One-shot video probe: (fps, total_frames, duration_seconds).

    Safe against NaN fps and None/0 frame counts. Duration is 0.0 when
    the frame count is unknown; callers should not divide by it.
    """
    fps = safe_fps(cap, default=default_fps)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if total_frames > 0 else 0.0
    return fps, total_frames, duration


def frame_interval_for(fps: float, *, sample_fps: float | None = None,
                       sample_interval_sec: float | None = None) -> int:
    """Compute how many frames to skip between samples.

    Pass exactly one of `sample_fps` (e.g. 2 = sample 2 frames/sec) or
    `sample_interval_sec` (e.g. 1.0 = sample every 1 second). Always
    returns at least 1 — you never want to divide by zero downstream.
    """
    if sample_fps is not None:
        return max(1, int(fps / max(1, sample_fps)))
    if sample_interval_sec is not None:
        return max(1, int(fps * sample_interval_sec))
    raise ValueError("provide sample_fps or sample_interval_sec")
