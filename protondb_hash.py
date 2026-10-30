"""Hash used by ProtonDB's static report files.

ProtonDB publishes individual reports as static JSON at::

    https://www.protondb.com/data/reports/all-devices/app/<hash>.json

where ``<hash>`` is derived from ``https://www.protondb.com/data/counts.json``
(``reports`` and ``timestamp``) and the Steam App ID. This was the part of the
old bot that broke: the files simply 404 when the hash is wrong.

What is verified and what is not
--------------------------------
Verified (see tests/test_protondb_hash.py, which compares against real
JavaScript executed by Node):
  * ``js_hash`` is a faithful port of the classic JS string hash
    ``h = (h << 5) - h + charCode; h &= h`` followed by ``Math.abs``.
  * ``_mix`` matches the template-literal helper ``${t}p${e * (t % n)}``.

Partially verified from a public implementation reference: the hash appends `m`.
NOT live-verified: the exact way ProtonDB's current front-end combines those pieces
(literal prefix/suffix, which page value is used for the "all" bucket). No
public, current source for that could be reached when this was written, so the
combination below is the one used by the previous version of this bot plus a few
close variants. ``services.protondb_reports`` tries the variants in order,
accepts a result only if the server answers with a real JSON report page, and
remembers which variant worked (and logs it). If none works, the bot says so
and falls back to the ProtonDB summary + direct link instead of inventing data.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

_INT32_MOD = 1 << 32
_INT32_MAX = (1 << 31) - 1


def _to_int32(value: int) -> int:
    value &= _INT32_MOD - 1
    return value - _INT32_MOD if value > _INT32_MAX else value


def js_hash(text: str) -> int:
    """Port of ProtonDB hashing: append `m`, then JS 32-bit string hash and abs.

    JavaScript iterates UTF-16 code units, so we do too.
    """
    raw = (text + "m").encode("utf-16-le", "surrogatepass")
    units = struct.unpack(f"<{len(raw) // 2}H", raw)
    h = 0
    for unit in units:
        h = _to_int32(_to_int32(h << 5) - h + unit)
    return abs(h)


def _mix(e: int, t: str, n: int) -> str:
    """``${t}p${e * (t % n)}`` where ``t`` is a numeric string."""
    if n <= 0:
        raise ValueError("timestamp must be positive")
    return f"{t}p{e * (int(t) % n)}"


@dataclass(frozen=True)
class HashVariant:
    name: str
    page: int
    tail: str


# Order matters: the first entry is what the previous bot version used.
VARIANTS: tuple[HashVariant, ...] = (
    HashVariant("page1+all-devices", 1, "all-devices"),
    HashVariant("page0+all-devices", 0, "all-devices"),
    HashVariant("page1+all", 1, "all"),
    HashVariant("page0+all", 0, "all"),
)


def report_hash(appid: int, reports: int, timestamp: int, variant: HashVariant) -> str:
    text = (
        "p"
        + _mix(appid, str(reports), timestamp)
        + "*vRT"
        + _mix(variant.page, str(appid), timestamp)
        + variant.tail
    )
    return str(js_hash(text))


def ordered_variants(preferred: str | None) -> list[HashVariant]:
    """Put the variant that worked last time first."""
    if not preferred:
        return list(VARIANTS)
    first = [v for v in VARIANTS if v.name == preferred]
    return first + [v for v in VARIANTS if v.name != preferred]
