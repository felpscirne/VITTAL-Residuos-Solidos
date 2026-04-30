from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from app.services.event_markers import (
    _normalize_sector_values,
    _to_local_naive_timestamp,
    apply_event_markers,
)


@dataclass
class DummyEvent:
    title: str
    start_date: object
    end_date: object


def test_normalize_sector_values_ignores_empty_tokens():
    assert _normalize_sector_values(" A, ,B ,, C ") == ["A", "B", "C"]
    assert _normalize_sector_values(None) == []


def test_to_local_naive_timestamp_converts_timezone_aware_values():
    ts = _to_local_naive_timestamp("2025-01-01T12:00:00+00:00")

    assert ts == pd.Timestamp("2025-01-01 09:00:00")
    assert ts.tzinfo is None


def test_apply_event_markers_adds_one_vrect_per_event():
    fig = go.Figure()
    event = DummyEvent(
        title="Parada",
        start_date="2025-01-10 15:00:00",
        end_date="2025-01-11 10:00:00",
    )

    updated = apply_event_markers(fig, [event])

    assert len(updated.layout.shapes) == 1
    assert updated.layout.shapes[0].x0 == pd.Timestamp("2025-01-10")
    assert updated.layout.shapes[0].x1 == pd.Timestamp("2025-01-12")
    assert updated.layout.annotations[0].text == "Parada"
