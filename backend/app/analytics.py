from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any


HALF_HOUR = timedelta(minutes=30)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_analysis(
    actual_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    cutoff: datetime,
    delivery_start: datetime,
    delivery_end: datetime,
) -> dict[str, Any]:
    actuals = {
        parse_timestamp(row["startTime"]): float(row["generation"])
        for row in actual_rows
        if row.get("generation") is not None
    }

    latest_forecasts: dict[datetime, dict[str, Any]] = {}
    for row in forecast_rows:
        if row.get("generation") is None:
            continue
        start = parse_timestamp(row["startTime"])
        published = parse_timestamp(row["publishTime"])
        if published > cutoff or not delivery_start <= start < delivery_end:
            continue
        existing = latest_forecasts.get(start)
        if existing is None or published > parse_timestamp(existing["publishTime"]):
            latest_forecasts[start] = row

    forecast_times = sorted(latest_forecasts)
    if len(forecast_times) > 1:
        deltas = [
            int((right - left).total_seconds() / 60)
            for left, right in zip(forecast_times, forecast_times[1:])
            if right > left
        ]
        resolution_minutes = min(deltas) if deltas else 60
    else:
        resolution_minutes = 60

    interval = timedelta(minutes=resolution_minutes)
    points: list[dict[str, Any]] = []
    for start in forecast_times:
        forecast = latest_forecasts[start]
        actual_samples = [
            actuals[stamp]
            for stamp in sorted(actuals)
            if start <= stamp < start + interval
        ]
        expected_actual_samples = max(1, int(interval / HALF_HOUR))
        if len(actual_samples) != expected_actual_samples:
            actual = None
        else:
            actual = mean(actual_samples)
        predicted = float(forecast["generation"])
        error = predicted - actual if actual is not None else None
        points.append(
            {
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "publishTime": parse_timestamp(forecast["publishTime"])
                .isoformat()
                .replace("+00:00", "Z"),
                "forecastMw": predicted,
                "actualMw": actual,
                "errorMw": error,
            }
        )

    paired = [point for point in points if point["actualMw"] is not None]
    errors = [point["errorMw"] for point in paired]
    absolute_errors = [abs(error) for error in errors]
    actual_total = sum(point["actualMw"] for point in paired)
    expected_intervals = max(1, int(24 * 60 / resolution_minutes))
    metrics = {
        "maeMw": mean(absolute_errors) if paired else None,
        "rmseMw": (
            (mean(error**2 for error in errors)) ** 0.5 if paired else None
        ),
        "biasMw": mean(errors) if paired else None,
        "wapePercent": (
            sum(absolute_errors) / actual_total * 100
            if actual_total
            else None
        ),
        "pairedIntervals": len(paired),
        "forecastIntervals": len(points),
        "expectedIntervals": expected_intervals,
        "actualHalfHours": len(actuals),
        "coveragePercent": min(len(paired) / expected_intervals * 100, 100),
    }
    return {
        "points": points,
        "metrics": metrics,
        "resolutionMinutes": resolution_minutes,
        "latestPublishTime": max(
            (point["publishTime"] for point in points), default=None
        ),
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
    }


def forecast_window(cutoff: datetime, days: int = 3) -> tuple[str, str]:
    start = (cutoff - timedelta(days=days)).astimezone(timezone.utc)
    end = cutoff.astimezone(timezone.utc)
    return (
        start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        end.isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
