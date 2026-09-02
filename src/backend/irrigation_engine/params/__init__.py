"""Agronomic parameters, loaded from YAML.

Every agronomic constant in this project — Kc, p, Zr, Ky, application efficiency,
pedotransfer coefficients — lives in a YAML file in this package and never inline
in code. Each value carries a comment naming its source, for example
``FAO-56 Table 12``, ``FAO-56 Table 22`` or ``Saxton and Rawls 2006``.

Anything not confirmed against its source carries ``TODO [VERIFY]`` and a
conservative default. A wrong constant that looks authoritative is worse than an
admitted gap: it survives review and fails in the field.

Files, seeded in M1:
    ``crops.yaml``       Kc, stage lengths, Zr, p and Ky per crop
    ``soil.yaml``        Saxton and Rawls (2006) regression coefficients
    ``irrigation.yaml``  application efficiency per method, engine defaults
"""

from irrigation_engine.params.loader import clear_cache, load_params

__all__ = ["clear_cache", "load_params"]
