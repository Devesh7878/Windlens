from __future__ import annotations

import os
import threading
import time
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .analytics import build_analysis, forecast_window


API_BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
LONDON = ZoneInfo("Europe/London")
DECISION_CUTOFF = datetime_time.fromisoformat(
    os.getenv("DECISION_CUTOFF_LOCAL", "10:00")
)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()

app = FastAPI(
    title="WindLens",
    description="UK wind forecast snapshots and realized forecast accuracy.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def cached(key: str, loader: Any) -> Any:
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > now:
            return entry[1]

    value = loader()
    with _cache_lock:
        _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, value)
    return value


def fetch_elexon(dataset: str, params: dict[str, str]) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            f"{API_BASE}/{dataset}",
            params=params,
            timeout=(5, 30),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Elexon {dataset} request failed: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Elexon {dataset} returned invalid JSON.",
        ) from exc

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise HTTPException(
            status_code=502,
            detail=f"Elexon {dataset} response did not contain a data list.",
        )
    return rows


def fetch_actuals(delivery_day: date) -> list[dict[str, Any]]:
    key = f"actuals:{delivery_day.isoformat()}"
    return cached(
        key,
        lambda: fetch_elexon(
            "FUELHH",
            {
                "settlementDateFrom": delivery_day.isoformat(),
                "settlementDateTo": delivery_day.isoformat(),
                "fuelType": "WIND",
            },
        ),
    )


def fetch_forecasts(delivery_day: date, cutoff: datetime) -> list[dict[str, Any]]:
    start, end = forecast_window(cutoff)
    key = f"forecasts:{delivery_day.isoformat()}:{start}:{end}"
    return cached(
        key,
        lambda: fetch_elexon(
            "WINDFOR",
            {
                "publishDateTimeFrom": start,
                "publishDateTimeTo": end,
            },
        ),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analysis")
def analysis(
    delivery_date: date = Query(alias="date"),
) -> dict[str, Any]:
    if delivery_date.year != 2026 or delivery_date.month != 1:
        raise HTTPException(
            status_code=400,
            detail="This pilot is scoped to delivery dates in January 2026.",
        )

    local_cutoff = datetime.combine(
        delivery_date - timedelta(days=1), DECISION_CUTOFF, tzinfo=LONDON
    )
    cutoff = local_cutoff.astimezone(timezone.utc)
    delivery_start = datetime.combine(delivery_date, datetime_time.min, tzinfo=LONDON)
    delivery_end = datetime.combine(
        delivery_date + timedelta(days=1), datetime_time.min, tzinfo=LONDON
    )
    actual_rows = fetch_actuals(delivery_date)
    forecast_rows = fetch_forecasts(delivery_date, cutoff)

    try:
        result = build_analysis(
            actual_rows,
            forecast_rows,
            cutoff,
            delivery_start.astimezone(timezone.utc),
            delivery_end.astimezone(timezone.utc),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not interpret the Elexon dataset response: {exc}",
        ) from exc

    return {
        "deliveryDate": delivery_date.isoformat(),
        "timezone": "Europe/London",
        "decisionCutoffLocal": local_cutoff.isoformat(),
        "actualDataset": "FUELHH",
        "forecastDataset": "WINDFOR",
        **result,
    }


STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend_root() -> FileResponse:
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        requested = os.path.abspath(os.path.join(STATIC_DIR, path))
        if not requested.startswith(STATIC_DIR + os.sep):
            raise HTTPException(status_code=404, detail="Not found")
        if os.path.isfile(requested):
            return FileResponse(requested)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
