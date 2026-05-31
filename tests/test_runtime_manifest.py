"""
Tests for runtime manifest logging.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.logging import ProgressTracker
from src.utils.runtime_manifest import RuntimeManifest


def test_runtime_manifest_writes_events(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    manifest = RuntimeManifest(run_name="ocr_batch", root_dir=runtime_dir)

    manifest.record("start", started_at="2026-05-31T00:00:00+00:00")
    manifest.record("start_file", filename="sample.pdf")
    manifest.set_summary(total=1, succeeded=1)

    payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert payload["run_name"] == "ocr_batch"
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["succeeded"] == 1
    assert [event["type"] for event in payload["events"]] == ["start", "start_file"]


def test_progress_tracker_records_to_manifest(tmp_path: Path) -> None:
    tracker = ProgressTracker(verbose=False, run_name="book_ocr", runtime_dir=tmp_path / "runtime")

    tracker.start()
    tracker.set_total(1)
    tracker.set_input_output("/in", "/out")
    tracker.start_file("sample.pdf")
    tracker.extracted_image("page001_image0.jpeg")
    tracker.extracted_diagram("page001_image0.jpeg", "diagram")
    tracker.complete_file("sample.pdf", success=True)
    tracker.print_summary()

    payload = json.loads(tracker.manifest.manifest_path.read_text(encoding="utf-8"))
    event_types = [event["type"] for event in payload["events"]]

    assert event_types[0] == "start"
    assert "set_total" in event_types
    assert "set_input_output" in event_types
    assert "start_file" in event_types
    assert "extracted_image" in event_types
    assert "extracted_diagram" in event_types
    assert "complete_file" in event_types
    assert payload["summary"]["succeeded"] == 1
