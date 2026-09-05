"""DISCOM feeder schedule extraction via Azure AI Document Intelligence.

``src/azure`` is on the import path rather than being a package itself, so this
imports as ``document_intelligence``. Everything here may import the Azure SDK;
nothing in ``src/backend/irrigation_engine`` may, and CI enforces that.
"""
