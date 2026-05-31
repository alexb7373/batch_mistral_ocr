"""
Runtime manifest utilities for OCR runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ManifestEvent:
    """Single manifest event."""

    type: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)


class RuntimeManifest:
    """Persistent run manifest written under `runtime/`."""

    def __init__(self, run_name: str, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path("runtime")
        self.run_name = run_name
        self.run_dir = self.root_dir / f"{run_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.manifest_path = self.run_dir / "manifest.json"
        self.events: List[ManifestEvent] = []
        self.summary: Dict[str, Any] = {}
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._write()

    def record(self, event_type: str, **data: Any) -> None:
        self.events.append(ManifestEvent(type=event_type, timestamp=_utc_now(), data=data))
        self._write()

    def set_summary(self, **summary: Any) -> None:
        self.summary.update(summary)
        self._write()

    def _write(self) -> None:
        payload = {
            "run_name": self.run_name,
            "run_dir": str(self.run_dir),
            "created_at": self.events[0].timestamp if self.events else _utc_now(),
            "updated_at": _utc_now(),
            "summary": self.summary,
            "events": [
                {"type": event.type, "timestamp": event.timestamp, "data": event.data}
                for event in self.events
            ],
        }
        self.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
