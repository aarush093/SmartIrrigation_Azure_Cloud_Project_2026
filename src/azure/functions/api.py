"""FastAPI application, mounted into the Functions host by AsgiFunctionApp.

Phase-I declared "FastAPI, Azure Functions Python worker" as the backend stack.
Mounting the ASGI app rather than writing bare HTTP triggers is what makes that
declaration literally true rather than approximately true. Plan Section 17.4.

Three routes, all operator-facing or PWA-facing. The farmer-facing channel is
voice and missed calls; he never touches an HTTP endpoint.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from irrigation_engine.scheduler.models import IST

app = FastAPI(
    title="Smart Irrigation advisory",
    description=(
        "Power-window-aware irrigation scheduling. The farmer-facing channel is "
        "voice and missed calls; this API serves the operator screen and the PWA."
    ),
    version="0.1.0",
)


class OnboardRequest(BaseModel):
    """The facts collected at onboarding, per plan Section 5.1.

    Deliberately small. Every field here is something an extension worker can
    establish in five minutes standing in the field, with no instrument beyond a
    bucket and a watch.
    """

    phone: str = Field(description="E.164. This is the identity; there is no login.")
    language: str = Field(default="hi", description="Script master: hi, en or ta.")
    name: str | None = None
    village: str | None = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    crop: str
    sowing_date: dt.date
    area_value: float = Field(gt=0.0, description="Area in the unit the farmer uses.")
    area_unit: str = Field(default="acre", description="acre, hectare, bigha, guntha or cent.")
    irrigation_method: str = Field(default="furrow")
    pump_hp: float | None = Field(default=None, gt=0.0)
    pump_head_m: float | None = Field(default=None, gt=0.0)
    bucket_litres: float | None = Field(
        default=None, gt=0.0, description="Bucket test volume. Preferred over the nameplate."
    )
    bucket_seconds: float | None = Field(default=None, gt=0.0)
    consent_given: bool = Field(default=False, description="Spoken consent for the daily call.")


class OnboardResponse(BaseModel):
    """What onboarding returns."""

    farmer_id: str
    field_id: str
    accepted: bool
    warnings: list[str] = Field(default_factory=list)


class TodayResponse(BaseModel):
    """The day's decision, shaped for the icon-only PWA.

    The PWA renders three tiles from this: pump minutes with a start time, the
    power window on a 24-hour ring, and rain probability as a filling drop. It
    never computes anything.
    """

    field_id: str
    date: dt.date
    decision: str
    reason_code: str
    minutes: float
    start_time: dt.datetime | None
    stop_time: dt.datetime | None
    window_start: dt.datetime | None
    window_end: dt.datetime | None
    script_text: str | None = None
    audio_url: str | None = Field(
        default=None, description="Cached speech, so a tile can speak when tapped."
    )


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness check.

    Returns:
        Status and the current IST time, so a monitor can spot clock drift.
    """
    return {"status": "ok", "now_ist": dt.datetime.now(tz=IST).isoformat()}


@app.post("/onboard", response_model=OnboardResponse)
def onboard(request: OnboardRequest) -> OnboardResponse:
    """Register a farmer and one field.

    Warnings rather than errors where a value is merely suboptimal. An
    onboarding that failed because no bucket test was done would send the
    extension worker away with nothing, which is worse for the farmer than a
    less accurate discharge estimate.

    Args:
        request: The onboarding form.

    Returns:
        The assigned identifiers and any warnings for the operator to act on.
    """
    warnings: list[str] = []
    if request.bucket_litres is None or request.bucket_seconds is None:
        warnings.append(
            "No bucket test recorded. Pump discharge will be estimated from the "
            "nameplate rating, which is the largest single source of error in "
            "the running time this farmer is told."
        )
    if not request.consent_given:
        warnings.append("Spoken consent for the daily call was not recorded.")

    # Persistence lands with the Cosmos bindings in M5.
    farmer_id = f"farmer-{abs(hash(request.phone)) % 10**6:06d}"
    return OnboardResponse(
        farmer_id=farmer_id,
        field_id=f"{farmer_id}-f1",
        accepted=True,
        warnings=warnings,
    )


@app.get("/today")
def today(field_id: str) -> TodayResponse | None:
    """Return today's decision for one field.

    Args:
        field_id: The field to fetch.

    Returns:
        The day's schedule, or None where none has been computed yet.
    """
    del field_id
    # Cosmos read lands in M5.
    return None
