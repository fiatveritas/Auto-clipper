from pathlib import Path
import json

from .schema import (
    PRIMARY_EVENTS,
    TAGS,
    TAG_GROUPS,
)

class DatasetManager:
    """Manages dataset labels for supervised learning."""

    def __init__(self, dataset_dir):
        self.dataset_dir = Path(dataset_dir)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

        self.labels_file = self.dataset_dir / "labels.json"

        self.data = {
            "version": 1,
            "labels": {}
        }

        self.labels = self.data["labels"]

        self.load()

    def load(self):
        """Load labels from disk. Creates an empty dataset if none exists."""

        if not self.labels_file.exists():
            self.save()
            return

        with open(self.labels_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.labels = self.data.setdefault("labels", {})

    def save(self):
        """Write dataset to disk."""

        with open(self.labels_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def get_label(self, clip_id):
        """Return the label for a clip or None."""

        return self.labels.get(clip_id)

    def has_label(self, clip_id):
        """Return True if the clip has already been labeled."""

        return clip_id in self.labels

    def save_label(
        self,
        clip_id,
        is_highlight,
        primary_event,
        tags=None,
        notes=""
    ):
        """Create or update a label."""

        if primary_event not in PRIMARY_EVENTS:
            raise ValueError(f"Invalid primary event: {primary_event}")

        tags = tags or []

        invalid = [t for t in tags if t not in TAGS]
        if invalid:
            raise ValueError(f"Invalid tags: {invalid}")

        self.labels[clip_id] = {
            "is_highlight": bool(is_highlight),
            "primary_event": primary_event,
            "tags": tags,
            "notes": notes,
        }

        self.save()

    def delete_label(self, clip_id):
        """Delete a label if it exists."""

        if clip_id in self.labels:
            del self.labels[clip_id]
            self.save()

    def unlabeled(self, clip_ids):
        """Return clip ids that have not been labeled."""

        return [cid for cid in clip_ids if cid not in self.labels]

    def statistics(self):
        """Generate basic dataset statistics."""

        stats = {
            "total": len(self.labels),
            "highlights": 0,
            "non_highlights": 0,
            "primary_events": {},
            "tags": {},
        }

        for label in self.labels.values():

            if label["is_highlight"]:
                stats["highlights"] += 1
            else:
                stats["non_highlights"] += 1

            pe = label["primary_event"]
            stats["primary_events"][pe] = (
                stats["primary_events"].get(pe, 0) + 1
            )

            for tag in label["tags"]:
                stats["tags"][tag] = (
                    stats["tags"].get(tag, 0) + 1
                )

        return stats