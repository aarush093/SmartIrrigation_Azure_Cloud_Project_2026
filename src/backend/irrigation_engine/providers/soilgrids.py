"""ISRIC SoilGrids soil provider (dataset D4).

Extracts sand, silt, clay, organic carbon and bulk density at the field centroid
and depth-weights them across the 0-5, 5-15 and 15-30 cm intervals to give a
single root-zone profile.

Two operational constraints, both from ``dataset/README.md``:

1. The REST API has been reported as temporarily paused, so the adapter must
   tolerate failure and the design keeps a bulk raster or WCS fallback open.
2. Soil properties are static, so one successful retrieval per field is enough
   for the life of the project and the result is cached permanently.

SoilGrids returns values in conventional integer units that must be rescaled:
texture fractions in g/kg, organic carbon in dg/kg, bulk density in cg/cm3.
Getting this wrong silently produces a plausible but wrong available water, so
the conversion factors are named constants and unit-tested.

Endpoint: https://rest.isric.org/soilgrids/v2.0/properties/query
"""

from __future__ import annotations

from typing import Any

import httpx

from irrigation_engine.models import SoilProfile

__all__ = ["SoilGridsProvider", "fetch_soil"]

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

PROPERTIES = ("sand", "silt", "clay", "soc", "bdod")
DEPTH_INTERVALS = ("0-5cm", "5-15cm", "15-30cm")

# Thickness of each interval, used as the depth weighting. Sums to the 30 cm
# root zone the engine models.
DEPTH_WEIGHTS_CM: dict[str, float] = {"0-5cm": 5.0, "5-15cm": 10.0, "15-30cm": 15.0}

# SoilGrids conventional units to engine units.
#   sand, silt, clay  g/kg    -> mass fraction 0 to 1
#   soc               dg/kg   -> mass fraction 0 to 1
#   bdod              cg/cm3  -> g/cm3
UNIT_DIVISORS: dict[str, float] = {
    "sand": 1000.0,
    "silt": 1000.0,
    "clay": 1000.0,
    "soc": 10000.0,
    "bdod": 100.0,
}


class SoilGridsProvider:
    """Soil provider backed by the ISRIC SoilGrids REST API.

    Satisfies :class:`~irrigation_engine.providers.base.SoilProvider`.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        """Configure the provider.

        Args:
            client: An httpx client to reuse. One is created if not supplied.
            timeout_s: Per-request timeout, seconds. Higher than the weather
                provider's because SoilGrids point queries are slower.
        """
        self._client = client
        self.timeout_s = timeout_s

    def fetch_soil(self, lat: float, lon: float) -> SoilProfile:
        """Fetch and depth-weight the 0 to 30 cm soil profile for a point.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.

        Returns:
            The depth-weighted root-zone profile in engine units: mass fractions
            0 to 1 for texture and organic carbon, g/cm3 for bulk density.

        Raises:
            httpx.HTTPError: On transport failure or a non-success status.
            ValueError: If the response omits a requested property or depth.
        """
        # Repeated keys, so a list of pairs rather than a mapping: SoilGrids
        # expects one property= and one depth= per requested layer.
        params: list[tuple[str, str | int | float | bool | None]] = [
            ("lat", lat),
            ("lon", lon),
            ("value", "mean"),
        ]
        params += [("property", p) for p in PROPERTIES]
        params += [("depth", d) for d in DEPTH_INTERVALS]

        if self._client is not None:
            response = self._client.get(SOILGRIDS_URL, params=params, timeout=self.timeout_s)
        else:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.get(SOILGRIDS_URL, params=params)
        response.raise_for_status()

        values = _depth_weighted_means(response.json())
        return SoilProfile(
            sand=values["sand"],
            silt=values["silt"],
            clay=values["clay"],
            organic_carbon=values["soc"],
            bulk_density=values["bdod"],
            latitude=lat,
            longitude=lon,
        )


def _depth_weighted_means(body: dict[str, Any]) -> dict[str, float]:
    """Reduce the SoilGrids layer response to one depth-weighted value per property.

    Weights are the thickness of each depth interval, so the 15-30 cm layer
    counts three times as much as the 0-5 cm layer. Depths that came back empty
    are skipped and the weights renormalised over what did arrive, rather than
    being treated as zero.
    """
    layers = body.get("properties", {}).get("layers")
    if not layers:
        msg = "SoilGrids response contains no layers"
        raise ValueError(msg)

    results: dict[str, float] = {}
    empty: list[str] = []
    for layer in layers:
        name = layer.get("name")
        if name not in PROPERTIES:
            continue

        weighted_sum = 0.0
        total_weight = 0.0
        for depth in layer.get("depths", []):
            label = depth.get("label")
            mean = depth.get("values", {}).get("mean")
            if label not in DEPTH_WEIGHTS_CM or mean is None:
                continue
            weight = DEPTH_WEIGHTS_CM[label]
            weighted_sum += float(mean) * weight
            total_weight += weight

        if total_weight == 0.0:
            empty.append(str(name))
            continue
        results[name] = (weighted_sum / total_weight) / UNIT_DIVISORS[name]

    # SoilGrids answers 200 with every value null for a point it has no data
    # for, which is a different failure from a partial response and deserves a
    # different message: the caller should fall back to a declared soil type
    # rather than retry.
    if len(empty) == len(PROPERTIES):
        msg = (
            "SoilGrids has no data at this point: every property returned null. "
            "Use a declared soil texture instead of retrying."
        )
        raise ValueError(msg)
    if empty:
        msg = f"SoilGrids returned no usable depth for: {', '.join(sorted(empty))}"
        raise ValueError(msg)

    missing = [p for p in PROPERTIES if p not in results]
    if missing:
        msg = f"SoilGrids response is missing properties: {', '.join(missing)}"
        raise ValueError(msg)
    return results


def fetch_soil(lat: float, lon: float) -> SoilProfile:
    """Fetch the soil profile using a default provider instance.

    Args:
        lat: Latitude, decimal degrees.
        lon: Longitude, decimal degrees.

    Returns:
        The depth-weighted 0 to 30 cm profile.
    """
    return SoilGridsProvider().fetch_soil(lat, lon)
