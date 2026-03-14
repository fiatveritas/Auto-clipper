import re
import json
import urllib.request
import urllib.error

from analysis.game_profiles import get_profile


class ChatSpikeDetector:
    """
    Detects exciting moments using Twitch chat activity spikes.

    When something exciting happens on stream, chat goes crazy — messages
    per second spike dramatically. This detector downloads the chat log
    for a Twitch VOD and finds those spikes.

    Works only with Twitch VOD URLs.
    """

    def __init__(self, game_id="arc_raiders"):
        self.profile = get_profile(game_id)
        self.intensity_threshold = self.profile.get("intensity_threshold", 0.35)

    def analyze_chat(self, vod_url, video_path, progress_callback=None):
        """
        Download chat data for a Twitch VOD and find activity spikes.

        Args:
            vod_url: The original Twitch VOD URL
            video_path: Path to the downloaded video (for duration)
            progress_callback: Progress callback (0-1)

        Returns:
            List of highlight dicts
        """
        if progress_callback:
            progress_callback(0.05)

        # Extract VOD ID from URL
        vod_id = self._extract_vod_id(vod_url)
        if not vod_id:
            print("  [Chat] Could not extract VOD ID from URL, falling back to empty results")
            if progress_callback:
                progress_callback(1.0)
            return []

        print(f"  [Chat] Fetching chat data for VOD {vod_id}...")

        # Download chat messages
        messages = self._fetch_chat(vod_id, progress_callback)

        if not messages:
            print("  [Chat] No chat messages found")
            if progress_callback:
                progress_callback(1.0)
            return []

        print(f"  [Chat] Got {len(messages)} chat messages")

        if progress_callback:
            progress_callback(0.7)

        # Build messages-per-second histogram
        histogram = self._build_histogram(messages)

        if progress_callback:
            progress_callback(0.85)

        # Find spikes
        highlights = self._find_spikes(histogram)

        if progress_callback:
            progress_callback(1.0)

        print(f"  [Chat] Found {len(highlights)} chat spike highlights")
        for h in highlights:
            print(f"  [Chat]   -> {h['label']} at {int(h['timestamp'])}s ({h['duration']}s, conf:{h['confidence']})")

        return highlights

    def _extract_vod_id(self, url):
        """Extract VOD ID from Twitch URL."""
        if not url:
            return None
        # Match patterns like twitch.tv/videos/123456789
        match = re.search(r'twitch\.tv/videos/(\d+)', url)
        if match:
            return match.group(1)
        # Match /v/123456789
        match = re.search(r'/v/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def _fetch_chat(self, vod_id, progress_callback=None):
        """
        Fetch chat messages for a Twitch VOD using the public GQL API.
        Returns list of {"offset_seconds": int, "message": str}.
        """
        messages = []
        cursor = None
        page = 0
        max_pages = 200  # Safety limit

        while page < max_pages:
            try:
                body = [{
                    "operationName": "VideoCommentsByOffsetOrCursor",
                    "variables": {
                        "videoID": vod_id,
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044571e9e5a4"
                        }
                    }
                }]

                if cursor:
                    body[0]["variables"]["cursor"] = cursor
                else:
                    body[0]["variables"]["contentOffsetSeconds"] = 0

                data = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    "https://gql.twitch.tv/gql",
                    data=data,
                    headers={
                        "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=15) as resp:
                    result = json.loads(resp.read().decode("utf-8"))

                comments = result[0].get("data", {}).get("video", {}).get("comments", {})
                edges = comments.get("edges", [])

                if not edges:
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    offset = node.get("contentOffsetSeconds", 0)
                    msg_body = node.get("message", {})
                    fragments = msg_body.get("fragments", [])
                    text = " ".join(f.get("text", "") for f in fragments)
                    messages.append({
                        "offset_seconds": offset,
                        "message": text,
                    })

                # Check for next page
                if comments.get("pageInfo", {}).get("hasNextPage"):
                    cursor = edges[-1].get("cursor")
                else:
                    break

                page += 1

                if progress_callback and page % 10 == 0:
                    progress_callback(0.05 + min(page / max_pages, 0.6))

            except Exception as e:
                print(f"  [Chat] Error fetching page {page}: {e}")
                break

        return messages

    def _build_histogram(self, messages, bucket_size=5):
        """
        Build a messages-per-bucket histogram.
        bucket_size is in seconds.
        """
        if not messages:
            return {}

        histogram = {}
        for msg in messages:
            bucket = (msg["offset_seconds"] // bucket_size) * bucket_size
            histogram[bucket] = histogram.get(bucket, 0) + 1

        return histogram

    def _find_spikes(self, histogram, bucket_size=5):
        """Find periods where chat activity spikes above average."""
        if not histogram:
            return []

        values = list(histogram.values())
        avg = sum(values) / len(values) if values else 0
        std_dev = (sum((v - avg) ** 2 for v in values) / max(len(values), 1)) ** 0.5

        # Threshold: mean + 1.5 standard deviations (adjusted by intensity_threshold)
        spike_threshold = avg + std_dev * (2.0 - self.intensity_threshold * 2)
        spike_threshold = max(spike_threshold, avg * 1.5)  # At least 1.5x average

        print(f"  [Chat] Avg: {avg:.1f} msgs/{bucket_size}s, std: {std_dev:.1f}, threshold: {spike_threshold:.1f}")

        # Find buckets above threshold
        spikes = []
        max_msgs = max(values) if values else 1
        for timestamp, count in sorted(histogram.items()):
            if count >= spike_threshold:
                score = min(count / max_msgs, 1.0)
                label = "Chat Explosion" if count >= avg * 4 else "Chat Spike" if count >= avg * 2.5 else "Chat Active"
                spikes.append({
                    "timestamp": float(timestamp),
                    "score": score,
                    "label": label,
                    "count": count,
                })

        if not spikes:
            return []

        # Merge nearby spikes
        merge_gap = self.profile.get("merge_gap", 8)
        clusters = []
        current = {
            "start": spikes[0]["timestamp"],
            "end": spikes[0]["timestamp"] + bucket_size,
            "peak_score": spikes[0]["score"],
            "label": spikes[0]["label"],
            "scores": [spikes[0]["score"]],
        }

        for s in spikes[1:]:
            if s["timestamp"] <= current["end"] + merge_gap:
                current["end"] = s["timestamp"] + bucket_size
                current["scores"].append(s["score"])
                if s["score"] > current["peak_score"]:
                    current["peak_score"] = s["score"]
                    current["label"] = s["label"]
            else:
                clusters.append(current)
                current = {
                    "start": s["timestamp"],
                    "end": s["timestamp"] + bucket_size,
                    "peak_score": s["score"],
                    "label": s["label"],
                    "scores": [s["score"]],
                }
        clusters.append(current)

        # Convert to highlights
        highlights = []
        for c in clusters:
            raw_dur = c["end"] - c["start"]
            min_dur = self.profile.get("min_clip_duration", 20)
            max_dur = self.profile.get("max_clip_duration", 60)
            extension = self.profile.get("clip_extension", 10)
            clip_dur = max(min_dur, min(max_dur, raw_dur + extension))

            avg_score = sum(c["scores"]) / len(c["scores"])
            confidence = min(avg_score * 1.5, 1.0)

            highlights.append({
                "timestamp": c["start"],
                "duration": clip_dur,
                "pre_pad": self.profile.get("pre_pad", 8),
                "label": c["label"],
                "confidence": round(confidence, 2),
            })

        return highlights
