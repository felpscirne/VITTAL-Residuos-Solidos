import pandas as pd

from app.models import Event

APP_TIMEZONE = "America/Sao_Paulo"
GENERAL_SECTOR_LABELS = {
    "geral",
    "geral (todos)",
    "todos",
    "todos os setores",
    "todos os setores afetados",
}


def _normalize_sector_values(affected_sectors):
    if not affected_sectors:
        return []
    return [sector.strip() for sector in affected_sectors.split(",") if sector.strip()]


def _to_local_naive_timestamp(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(APP_TIMEZONE).tz_localize(None)
    return ts


def _normalize_sector_token(value):
    return str(value).strip().lower()


def get_events_for_period(start_date=None, end_date=None, setor=None):
    events = Event.query.order_by(Event.start_date.asc()).all()
    normalized_start = _to_local_naive_timestamp(start_date) if start_date is not None else None
    normalized_end = _to_local_naive_timestamp(end_date) if end_date is not None else None
    normalized_setor = _normalize_sector_token(setor) if setor else None

    filtered_events = []
    for event in events:
        event_start = _to_local_naive_timestamp(event.start_date)
        event_end = _to_local_naive_timestamp(event.end_date)

        if normalized_start is not None and event_end < normalized_start:
            continue
        if normalized_end is not None and event_start > normalized_end:
            continue

        if normalized_setor:
            affected_values = {_normalize_sector_token(value) for value in _normalize_sector_values(event.affected_sectors)}
            if affected_values and normalized_setor not in affected_values and not (affected_values & GENERAL_SECTOR_LABELS):
                continue

        filtered_events.append(event)

    if not setor:
        return filtered_events

    return filtered_events


def apply_event_markers(fig, events):
    if not events:
        return fig

    for event in events:
        start = _to_local_naive_timestamp(event.start_date).normalize()
        end = _to_local_naive_timestamp(event.end_date).normalize() + pd.Timedelta(days=1)
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(255, 193, 7, 0.24)",
            line_color="rgba(255, 140, 0, 0.45)",
            line_width=1,
            layer="below",
            annotation_text=event.title,
            annotation_position="top left",
        )

    return fig
