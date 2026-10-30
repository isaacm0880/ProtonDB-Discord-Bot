"""Pure functions that turn upstream JSON into model objects.

Everything here is defensive: Steam and ProtonDB are unofficial/undocumented in
places, so missing keys or wrong types must never raise anything except
``BadResponse`` (and only when the overall structure is unusable).
"""
from __future__ import annotations

from typing import Any

from textutil import bbcode_to_text
from models import (
    BadResponse,
    NewsItem,
    Price,
    ProtonCounts,
    ProtonReport,
    ProtonSummary,
    Review,
    ReviewSummary,
    SearchResult,
    SteamApp,
)


# --------------------------------------------------------------------------
# tiny coercion helpers
# --------------------------------------------------------------------------
def as_str(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == value:  # not NaN
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value == value:
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [s for s in (as_str(v) for v in value) if s]


def as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------
# Steam
# --------------------------------------------------------------------------
def parse_search(payload: Any, limit: int = 25) -> list[SearchResult]:
    items = as_dict(payload).get("items")
    if not isinstance(items, list):
        return []
    results: list[SearchResult] = []
    seen: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = as_str(item.get("type"))
        if kind is not None and kind.lower() != "app":
            continue
        appid = as_int(item.get("id"))
        name = as_str(item.get("name"))
        if appid is None or appid <= 0 or not name or appid in seen:
            continue
        seen.add(appid)
        results.append(SearchResult(appid=appid, name=name))
        if len(results) >= limit:
            break
    return results


def parse_steam_app(appid: int, payload: Any) -> SteamApp | None:
    """Parse the ``appdetails`` response. Returns None when Steam has no data."""
    if not isinstance(payload, dict):
        raise BadResponse("Steam", "appdetails returned an unexpected structure")
    entry = payload.get(str(appid))
    if not isinstance(entry, dict):
        return None
    if not entry.get("success"):
        return None
    data = as_dict(entry.get("data"))
    if not data:
        return None

    price = None
    po = data.get("price_overview")
    if isinstance(po, dict):
        price = Price(
            currency=as_str(po.get("currency")),
            initial=as_int(po.get("initial")),
            final=as_int(po.get("final")),
            discount_percent=as_int(po.get("discount_percent")) or 0,
            initial_formatted=as_str(po.get("initial_formatted")),
            final_formatted=as_str(po.get("final_formatted")),
        )

    reqs = data.get("pc_requirements")  # Steam sends [] when there are none
    req_min = req_rec = None
    if isinstance(reqs, dict):
        req_min = as_str(reqs.get("minimum"))
        req_rec = as_str(reqs.get("recommended"))

    genres = []
    for g in data.get("genres") or []:
        desc = as_str(g.get("description")) if isinstance(g, dict) else None
        if desc:
            genres.append(desc)

    release = as_dict(data.get("release_date"))
    return SteamApp(
        appid=appid,
        name=as_str(data.get("name")),
        app_type=as_str(data.get("type")),
        is_free=bool(data.get("is_free")),
        short_description=as_str(data.get("short_description")),
        header_image=as_str(data.get("header_image")),
        developers=str_list(data.get("developers")),
        publishers=str_list(data.get("publishers")),
        genres=genres,
        release_date=as_str(release.get("date")),
        coming_soon=bool(release.get("coming_soon")),
        price=price,
        requirements_min=req_min,
        requirements_rec=req_rec,
    )


def parse_review_summary(payload: Any) -> ReviewSummary:
    if not isinstance(payload, dict):
        raise BadResponse("Steam", "appreviews returned an unexpected structure")
    if "success" in payload and payload["success"] not in (1, True):
        raise BadResponse("Steam", "review API reported failure")
    qs = as_dict(payload.get("query_summary"))
    if not qs:
        raise BadResponse("Steam", "appreviews had no query_summary")
    pos = as_int(qs.get("total_positive")) or 0
    neg = as_int(qs.get("total_negative")) or 0
    total = as_int(qs.get("total_reviews"))
    return ReviewSummary(
        review_score_desc=as_str(qs.get("review_score_desc")),
        total_positive=pos,
        total_negative=neg,
        total_reviews=total if total is not None else pos + neg,
    )


def parse_reviews(payload: Any, limit: int = 5) -> list[Review]:
    if not isinstance(payload, dict):
        raise BadResponse("Steam", "appreviews returned an unexpected structure")
    if "success" in payload and payload["success"] not in (1, True):
        raise BadResponse("Steam", "review API reported failure")
    rows = payload.get("reviews")
    if not isinstance(rows, list):
        return []
    reviews: list[Review] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = bbcode_to_text(row.get("review"), keep_lines=False)
        if not text:
            continue
        author = as_dict(row.get("author"))
        voted = row.get("voted_up")
        reviews.append(
            Review(
                voted_up=voted if isinstance(voted, bool) else None,
                text=text,
                timestamp=as_int(row.get("timestamp_created")),
                playtime_minutes=as_int(author.get("playtime_forever")),
                votes_up=as_int(row.get("votes_up")),
            )
        )
        if len(reviews) >= limit:
            break
    return reviews


def parse_news(payload: Any, limit: int = 5) -> list[NewsItem]:
    if not isinstance(payload, dict):
        raise BadResponse("Steam", "news returned an unexpected structure")
    appnews = payload.get("appnews")
    if not isinstance(appnews, dict):
        raise BadResponse("Steam", "news response had no appnews")
    rows = appnews.get("newsitems")
    if not isinstance(rows, list):
        return []
    items: list[NewsItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = as_str(row.get("title"))
        if not title:
            continue
        gid = row.get("gid")
        items.append(
            NewsItem(
                gid=str(gid) if gid not in (None, "") else None,
                title=title,
                url=as_str(row.get("url")),
                contents=str(row.get("contents") or ""),
                date=as_int(row.get("date")),
                feedlabel=as_str(row.get("feedlabel")),
                feedname=as_str(row.get("feedname")),
            )
        )
    items.sort(key=lambda i: i.date or 0, reverse=True)
    return items[:limit]


# --------------------------------------------------------------------------
# ProtonDB
# --------------------------------------------------------------------------
def parse_protondb_summary(payload: Any) -> ProtonSummary:
    if not isinstance(payload, dict):
        raise BadResponse("ProtonDB", "summary returned an unexpected structure")

    def tier(key: str) -> str | None:
        value = as_str(payload.get(key))
        return value.lower() if value else None

    total = as_int(payload.get("total"))
    if total is None:
        total = as_int(payload.get("reports"))
    return ProtonSummary(
        tier=tier("tier"),
        trending_tier=tier("trendingTier"),
        best_reported_tier=tier("bestReportedTier"),
        confidence=as_str(payload.get("confidence")),
        score=as_float(payload.get("score")),
        total=total,
    )


def parse_counts(payload: Any) -> ProtonCounts:
    if not isinstance(payload, dict):
        raise BadResponse("ProtonDB", "counts.json returned an unexpected structure")
    reports = as_int(payload.get("reports"))
    stamp = as_int(payload.get("timestamp"))
    if reports is None or stamp is None or stamp <= 0 or reports < 0:
        raise BadResponse(
            "ProtonDB",
            f"counts.json missing usable reports/timestamp (keys: {sorted(payload)[:10]})",
        )
    return ProtonCounts(reports=reports, timestamp=stamp)


_NOTE_KEY_ORDER = ("verdict", "extra", "other", "concerns")
_HARDWARE_KEYS = ("gpu", "cpu", "os", "kernel", "gpuDriver", "ram")


def _first_str(dicts: list[dict], key: str) -> str | None:
    for d in dicts:
        value = as_str(d.get(key))
        if value:
            return value
    return None


def _extract_notes(*sources: Any) -> str | None:
    parts: list[str] = []
    for src in sources:
        if isinstance(src, str):
            text = as_str(src)
            if text:
                parts.append(text)
        elif isinstance(src, dict):
            used = set()
            for key in _NOTE_KEY_ORDER:
                text = as_str(src.get(key))
                if text:
                    parts.append(text)
                used.add(key)
            for key, value in src.items():
                if key in used:
                    continue
                text = as_str(value)
                if text and len(text) > 15:  # skip short enum-like answers
                    parts.append(text)
        if parts:
            break
    if not parts:
        return None
    return "\n".join(dict.fromkeys(parts))  # de-duplicate, keep order


def _timestamp(value: Any) -> int | None:
    ts = as_int(value)
    if ts is None or ts <= 0:
        return None
    if ts > 10**11:  # milliseconds
        ts //= 1000
    return ts


def parse_protondb_reports(payload: Any) -> list[ProtonReport]:
    """Parse a ProtonDB report-page JSON document.

    Accepts ``{"reports": [...]}`` (or ``data``/``items``) or a bare list.
    """
    rows: Any
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("reports", "data", "items"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        if rows is None:
            raise BadResponse(
                "ProtonDB", f"report page had no report list (keys: {sorted(payload)[:10]})"
            )
    else:
        raise BadResponse("ProtonDB", "report page was not a JSON object or list")

    reports: list[ProtonReport] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        responses = as_dict(row.get("responses"))
        device = as_dict(row.get("device"))
        inferred = as_dict(device.get("inferred"))
        sources = [
            as_dict(inferred.get("steam")),
            inferred,
            device,
            responses,
            row,
        ]
        hw_parts = []
        gpu = _first_str(sources, "gpu")
        cpu = _first_str(sources, "cpu")
        if gpu:
            hw_parts.append(gpu)
        if cpu:
            hw_parts.append(cpu)
        osname = _first_str(sources, "os")
        kernel = _first_str(sources, "kernel")
        driver = _first_str(sources, "gpuDriver")
        if osname:
            hw_parts.append(osname)
        if kernel:
            hw_parts.append(f"kernel {kernel}")
        if driver:
            hw_parts.append(f"driver {driver}")

        verdict = as_str(responses.get("verdict")) or as_str(row.get("verdict"))
        reports.append(
            ProtonReport(
                timestamp=_timestamp(row.get("timestamp")),
                verdict=verdict.lower() if verdict else None,
                rating=as_str(responses.get("rating")) or as_str(row.get("rating")),
                proton_version=as_str(responses.get("protonVersion"))
                or as_str(row.get("protonVersion")),
                hardware=" · ".join(hw_parts) or None,
                notes=_extract_notes(responses.get("notes"), row.get("notes")),
            )
        )
    return reports
