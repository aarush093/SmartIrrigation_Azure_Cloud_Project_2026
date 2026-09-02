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
texture fractions arrive in g/kg, organic carbon in dg/kg and bulk density in
cg/cm3. Getting this wrong silently produces a plausible but wrong available
water, so the conversion factors are named constants and unit-tested.

Endpoint: https://rest.isric.org/soilgrids/v2.0/properties/query

Implemented in M1.
"""

from __future__ import annotations

import httpx

from irrigation_engine.models import SoilProfile

__all__ = ["SoilGridsProvider", "fetch_soil"]

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

PROPERTIES = ("sand", "silt", "clay", "soc", "bdod")
DEPTH_INTERVALS = ("0-5cm", "5-15cm", "15-30cm")

# Thickness of each interval, used as the depth weighting. Sums to the 30 cm
# root zone the engine models.
DEPTH_WEIGHTS_CM = (5.0, 10.0, 15.0)


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
        raise NotImplementedError("M1")

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
        raise NotImplementedError("M1")


def fetch_soil(lat: float, lon: float) -> SoilProfile:
    """Fetch the soil profile using a default provider instance.

    Args:
        lat: Latitude, decimal degrees.
        lon: Longitude, decimal degrees.

    Returns:
        The depth-weighted 0 to 30 cm profile.
    """
    raise NotImplementedError("M1")
