import pandas as pd
from sqlalchemy import and_

from app.models import Event


def _normalize_sector_values(affected_sectors):
    if not affected_sectors:
        return []
    return [sector.strip() for sector in affected_sectors.split(",") if sector.strip()]


def get_events_for_period(start_date=None, end_date=None, setor=None):
    query = Event.query

    if start_date is not None:
        query = query.filter(Event.end_date >= start_date)
    if end_date is not None:
        query = query.filter(Event.start_date <= end_date)

    events = query.order_by(Event.start_date.asc()).all()
    if not setor:
        return events

    filtered_events = []
    for event in events:
        affected_values = _normalize_sector_values(event.affected_sectors)
        if not affected_values:
            continue
        if "Geral" in affected_values or "Geral (Todos)" in affected_values or setor in affected_values:
            filtered_events.append(event)
    return filtered_events


def apply_event_markers(fig, events):
    if not events:
        return fig

    for event in events:
        start = pd.Timestamp(event.start_date).normalize()
        end = pd.Timestamp(event.end_date).normalize() + pd.Timedelta(days=1)
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(255, 193, 7, 0.16)",
            line_width=0,
            layer="below",
            annotation_text=event.title,
            annotation_position="top left",
        )

    return fig
