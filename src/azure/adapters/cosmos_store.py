"""Cosmos DB repository for the five containers.

Managed identity throughout. The Bicep sets ``disableLocalAuth`` on the account,
so there is no key to leak and no connection string in configuration: the
Functions app's system-assigned identity holds the data-plane role.

**The events container is where idempotency is actually enforced.** The
deduplication key is the document id, so a replayed event fails on the
uniqueness constraint in the database rather than on a set held in application
memory that dies with the process. `MissedCallRouter` still checks first,
because a cheap in-process check avoids a round trip, but the database is what
makes the guarantee hold across restarts and across concurrent instances.

Behind a feature flag like every other Azure integration: with no endpoint
configured this returns empty results and accepts writes silently, so the
Functions host starts and every route answers with no Cosmos account.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

__all__ = ["CosmosStore", "InMemoryStore", "Store"]

logger = logging.getLogger(__name__)

FARMERS = "farmers"
FIELDS = "fields"
FEEDER_WINDOWS = "feeder_windows"
SCHEDULES = "schedules"
EVENTS = "events"


class Store:
    """The repository interface the Functions app depends on.

    Defined as a plain class rather than a Protocol because both
    implementations live here and there is nothing to structurally match.
    """

    def farmers_due(self, now: dt.datetime) -> list[dict[str, Any]]:
        """Farmers whose daily call falls in the current hour."""
        raise NotImplementedError

    def fields_for(self, farmer_id: str) -> list[dict[str, Any]]:
        """Every field belonging to one farmer."""
        raise NotImplementedError

    def phone_to_farmer(self) -> dict[str, str]:
        """Phone number to farmer id, for the missed-call webhook."""
        raise NotImplementedError

    def schedule_for(self, field_id: str, day: dt.date) -> dict[str, Any] | None:
        """The stored schedule for one field on one day."""
        raise NotImplementedError

    def save_schedule(self, schedule: dict[str, Any]) -> None:
        """Persist a schedule. Idempotent on (field_id, date)."""
        raise NotImplementedError

    def save_event(self, event: dict[str, Any], deduplication_key: str) -> bool:
        """Persist an event.

        Returns:
            True if it was written, False if the key already existed, which
            means this is a replay and the caller must do nothing.
        """
        raise NotImplementedError


class InMemoryStore(Store):
    """Everything in a dict, for tests and for a host with no Cosmos account.

    Returning a working stand-in rather than raising is what lets the Functions
    app start and every route answer with no Azure subscription at all.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.farmers: list[dict[str, Any]] = []
        self.fields: list[dict[str, Any]] = []
        self.schedules: dict[tuple[str, str], dict[str, Any]] = {}
        self.events: dict[str, dict[str, Any]] = {}

    def farmers_due(self, now: dt.datetime) -> list[dict[str, Any]]:
        """Every farmer, since there is no call-hour index in memory."""
        del now
        return list(self.farmers)

    def fields_for(self, farmer_id: str) -> list[dict[str, Any]]:
        """Fields belonging to one farmer."""
        return [f for f in self.fields if f.get("farmer_id") == farmer_id]

    def phone_to_farmer(self) -> dict[str, str]:
        """Phone number to farmer id."""
        return {f["phone"]: f["farmer_id"] for f in self.farmers if "phone" in f}

    def schedule_for(self, field_id: str, day: dt.date) -> dict[str, Any] | None:
        """The stored schedule, or None."""
        return self.schedules.get((field_id, day.isoformat()))

    def save_schedule(self, schedule: dict[str, Any]) -> None:
        """Store a schedule, overwriting any for the same field and day."""
        self.schedules[(schedule["field_id"], schedule["date"])] = schedule

    def save_event(self, event: dict[str, Any], deduplication_key: str) -> bool:
        """Store an event unless its key is already present."""
        if deduplication_key in self.events:
            return False
        self.events[deduplication_key] = event
        return True


class CosmosStore(Store):
    """Cosmos DB backed, authenticated by managed identity.

    The SDK is imported lazily so this module imports and type-checks without
    ``azure-cosmos`` installed, exactly as the other Azure adapters do.
    """

    def __init__(self, *, endpoint: str, database: str = "irrigation") -> None:
        """Configure the store.

        Args:
            endpoint: Cosmos account endpoint. Empty disables the store.
            database: Database name.
        """
        self.endpoint = endpoint
        self.database = database
        self.enabled = bool(endpoint)
        self._client: Any = None

    def _container(self, name: str) -> Any:
        """Get a container proxy, creating the client on first use."""
        if self._client is None:
            from azure.cosmos import CosmosClient
            from azure.identity import DefaultAzureCredential

            self._client = CosmosClient(self.endpoint, credential=DefaultAzureCredential())
        return self._client.get_database_client(self.database).get_container_client(name)

    def farmers_due(self, now: dt.datetime) -> list[dict[str, Any]]:
        """Farmers whose call hour matches the current hour.

        Filtering in the query rather than in Python: at pilot scale it makes no
        difference, but reading every farmer every hour is the shape of query
        that stops working first as a system grows.
        """
        if not self.enabled:
            return []
        query = "SELECT * FROM c WHERE c.call_hour = @hour"
        return list(
            self._container(FARMERS).query_items(
                query=query,
                parameters=[{"name": "@hour", "value": now.hour}],
                enable_cross_partition_query=True,
            )
        )

    def fields_for(self, farmer_id: str) -> list[dict[str, Any]]:
        """Fields belonging to one farmer, read from its own partition."""
        if not self.enabled:
            return []
        return list(
            self._container(FIELDS).query_items(
                query="SELECT * FROM c WHERE c.farmer_id = @id",
                parameters=[{"name": "@id", "value": farmer_id}],
                partition_key=farmer_id,
            )
        )

    def phone_to_farmer(self) -> dict[str, str]:
        """Phone number to farmer id, for the missed-call webhook."""
        if not self.enabled:
            return {}
        rows = self._container(FARMERS).query_items(
            query="SELECT c.phone, c.farmer_id FROM c", enable_cross_partition_query=True
        )
        return {r["phone"]: r["farmer_id"] for r in rows if r.get("phone")}

    def schedule_for(self, field_id: str, day: dt.date) -> dict[str, Any] | None:
        """The stored schedule for one field on one day, or None."""
        if not self.enabled:
            return None
        try:
            return dict(
                self._container(SCHEDULES).read_item(
                    item=f"{field_id}|{day.isoformat()}", partition_key=field_id
                )
            )
        except Exception:  # absent is a normal state, not an error
            return None

    def save_schedule(self, schedule: dict[str, Any]) -> None:
        """Upsert, so re-planning the same day overwrites rather than duplicates."""
        if not self.enabled:
            return
        document = dict(schedule)
        document["id"] = f"{schedule['field_id']}|{schedule['date']}"
        self._container(SCHEDULES).upsert_item(document)

    def save_event(self, event: dict[str, Any], deduplication_key: str) -> bool:
        """Create, never upsert.

        The deduplication key is the document id, so a replay raises on the
        uniqueness constraint and this returns False. That is the guarantee that
        survives a restart, which an in-memory set does not.
        """
        if not self.enabled:
            return True
        document = dict(event)
        document["id"] = deduplication_key
        try:
            self._container(EVENTS).create_item(document)
        except Exception:  # a conflict means a replay, which is expected
            logger.info("duplicate event %s ignored", deduplication_key)
            return False
        return True
