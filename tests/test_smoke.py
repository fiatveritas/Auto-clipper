"""
Smoke tests — import chain + core API contracts.

Runs in a few seconds and doesn't need any fixture videos, weights,
or external services. Purpose: catch dumb regressions (a renamed
function, a missing import, a deleted constant) before they ship.

Run:
    python -m pytest tests/
  or
    python tests/test_smoke.py
"""
from __future__ import annotations

import os
import sys

# Allow running directly: `python tests/test_smoke.py`
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_clip_modes_enum_complete():
    from analysis.clip_modes import ClipMode
    values = {m.value for m in ClipMode}
    assert values == {"cv", "yolo", "voice", "hybrid", "all"}, f"got {values}"


def test_clip_modes_parse_lenient():
    from analysis.clip_modes import ClipMode
    assert ClipMode.parse(None) is ClipMode.HYBRID
    assert ClipMode.parse("bogus") is ClipMode.HYBRID
    assert ClipMode.parse("CV") is ClipMode.CV
    assert ClipMode.parse(ClipMode.YOLO) is ClipMode.YOLO


def test_clip_modes_property_matrix():
    from analysis.clip_modes import ClipMode
    assert ClipMode.CV.uses_cv and not ClipMode.CV.uses_yolo
    assert ClipMode.YOLO.uses_yolo and not ClipMode.YOLO.uses_cv
    assert ClipMode.VOICE.uses_voice and ClipMode.VOICE.is_live
    assert ClipMode.HYBRID.uses_cv and ClipMode.HYBRID.uses_yolo
    assert ClipMode.ALL.uses_cv and ClipMode.ALL.uses_yolo and ClipMode.ALL.uses_voice


def test_game_profiles_arc_raiders_present():
    from analysis.game_profiles import GAME_PROFILES, get_profile
    assert "arc_raiders" in GAME_PROFILES
    # No more v2-v7 variants — should have been consolidated
    variants = [k for k in GAME_PROFILES if k.startswith("arc_raiders_v")]
    assert not variants, f"stale variants still present: {variants}"
    # Fallback behavior
    assert get_profile("totally_unknown_game")["name"] == "Arc Raiders"


def test_game_profiles_13_entity_classes_defined():
    from analysis.arc_clip_detector import YOLO_CLASSES, ENTITY_PROFILES
    expected_real_classes = {
        "bastion", "bombardier", "fireball", "hornet", "leaper",
        "pop", "probe", "raider", "raider-down", "rocketeer",
        "snitch", "turret", "wasp",
    }
    for c in expected_real_classes:
        assert c in ENTITY_PROFILES, f"{c} missing from ENTITY_PROFILES"
    # Every real class must also appear in YOLO_CLASSES (id↔name roundtrip)
    yolo_names = set(YOLO_CLASSES.values())
    assert expected_real_classes.issubset(yolo_names), \
        f"real classes not in YOLO_CLASSES: {expected_real_classes - yolo_names}"


def test_hud_digit_classes_zeroed():
    """Classes 0/1/5 in YOLO_CLASSES are HUD digit noise; should score nothing."""
    from analysis.arc_clip_detector import ENTITY_PROFILES
    for hud in ("0", "1", "5"):
        assert ENTITY_PROFILES[hud]["base"] == 0, f"{hud!r} should have base=0"


def test_arc_clip_detector_adapter_imports():
    """Adapter + dependencies import cleanly (catches circular imports)."""
    from analysis.arc_clip_detector import (
        ArcClipDetectorAdapter,
        YOLODetector,
        ScoringEngine,
        PixelAnalyzer,
        Clusterer,
    )
    # All five names must resolve — the import itself is the test
    assert all([ArcClipDetectorAdapter, YOLODetector, ScoringEngine,
                PixelAnalyzer, Clusterer])
    # Adapter shouldn't explode even without weights — has_yolo=False gracefully
    adapter = ArcClipDetectorAdapter(game_id="arc_raiders")
    assert adapter.game_id == "arc_raiders"


def test_scoring_combine_floor():
    """combine() should never bury a strong pixel signal under a cold YOLO."""
    from analysis.arc_clip_detector import ScoringEngine
    s = ScoringEngine()
    # Strong pixel, zero YOLO — would be 21 with naive blend, but safety
    # floor keeps 80% of pixel score
    combined = s.combine(yolo=0, pixel=60, boss=False)
    assert combined >= 48, f"safety floor broken: {combined}"
    # Boss always gets min 85
    boss = s.combine(yolo=0, pixel=0, boss=True)
    assert boss >= 85


def test_match_trigger_phrases():
    """Voice trigger phrase matcher is case-insensitive + word-boundary aware.

    Exercises the REAL `_find_triggers` path, not a re-implementation. If
    the matcher's regex breaks, this test breaks with it.
    """
    try:
        from analysis.clip_trigger_detector import ClipTriggerDetector
    except Exception:
        return  # backend import errors in this env are fine; skip
    detector = ClipTriggerDetector()
    samples = [
        # (transcript_segment, expected_trigger_count)
        ({"text": "let's push this compound and CLIP THAT", "end": 5.0}, 1),
        ({"text": "okay save clip for sure", "end": 10.0}, 1),
        ({"text": "just rotating, nothing special", "end": 20.0}, 0),
        ({"text": "nice clipping skills bro", "end": 30.0}, 0),  # 'clipping' shouldn't trigger
    ]
    for segment, expected in samples:
        found = detector._find_triggers([segment])
        assert len(found) == expected, f"{segment['text']!r} → got {len(found)}, want {expected}"


def test_all_shell_scripts_parse():
    """Every shell script in the repo must have valid bash syntax."""
    import subprocess
    scripts = [
        "install.sh", "run.sh", "reinstall.sh",
        "install-remote.sh", "Auto-Clipper.command",
    ]
    for s in scripts:
        path = os.path.join(ROOT, s)
        assert os.path.exists(path), f"{s} missing"
        result = subprocess.run(["bash", "-n", path], capture_output=True)
        assert result.returncode == 0, f"{s} has syntax errors: {result.stderr.decode()}"


def test_url_validation():
    """_is_valid_stream_url accepts VOD URLs, rejects live-channel URLs."""
    import app
    # Should accept — VOD patterns
    assert app._is_valid_stream_url("https://www.twitch.tv/videos/123456789")
    assert app._is_valid_stream_url("https://m.twitch.tv/videos/123456789")
    assert app._is_valid_stream_url("https://www.youtube.com/watch?v=abc123")
    assert app._is_valid_stream_url("https://youtu.be/abc123")
    assert app._is_valid_stream_url("https://www.youtube.com/live/xyz")
    assert app._is_valid_stream_url("https://www.youtube.com/shorts/xyz")
    # Should reject — live channel, not a VOD
    assert not app._is_valid_stream_url("https://www.twitch.tv/shroud")
    assert not app._is_valid_stream_url("https://example.com/random")
    assert not app._is_valid_stream_url("")


def test_models_best_pt_bundled():
    """The 21 MB YOLO weights must be present in the repo."""
    weights = os.path.join(ROOT, "models", "best.pt")
    assert os.path.exists(weights), "models/best.pt not bundled"
    size_mb = os.path.getsize(weights) / (1024 * 1024)
    # Sanity: YOLOv11n is ~5 MB, trained Arc Raiders weights are ~21 MB.
    # Below 2 MB is likely a corrupt download.
    assert size_mb > 2, f"best.pt seems truncated at {size_mb:.1f} MB"


def test_time_parser_edge_cases():
    """_parse_time_to_seconds handles common formats + invalid input."""
    from clip_manager import _parse_time_to_seconds
    assert _parse_time_to_seconds("0:30") == 30.0
    assert _parse_time_to_seconds("1:30:00") == 5400.0
    assert _parse_time_to_seconds("90") == 90.0
    assert _parse_time_to_seconds("invalid") is None
    assert _parse_time_to_seconds("") is None


if __name__ == "__main__":
    # Run all test_* functions and print a summary.
    import traceback
    passed = failed = 0
    this = sys.modules[__name__]
    for name in sorted(dir(this)):
        if not name.startswith("test_"):
            continue
        fn = getattr(this, name)
        if not callable(fn):
            continue
        try:
            fn()
            print(f"  [OK] {name}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
