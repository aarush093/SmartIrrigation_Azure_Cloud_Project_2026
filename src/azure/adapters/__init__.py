"""Azure implementations of the engine's adapter interfaces.

Every module here may import the Azure SDK; nothing in
``src/backend/irrigation_engine`` may, and CI enforces that. Each is behind a
feature flag so that ``make demo`` runs end to end with no Azure resource.
"""
