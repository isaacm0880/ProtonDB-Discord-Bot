"""Plain data containers and exception types shared across modules."""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------
class UpstreamError(Exception):
    """A remote service (Steam / ProtonDB) could not give a usable answer."""

    def __init__(self, service: str, detail: str = ""):
        super().__init__(f"{service}: {detail}" if detail else service)
        self.service = service
        self.detail = detail


class UpstreamUnavailable(UpstreamError):
    """Timeout, network failure or HTTP 5xx/4xx."""


class RateLimited(UpstreamError):
    def __init__(self, service: str, retry_after: float = 30.0):
        super().__init__(service, f"rate limited, retry in {retry_after:.0f}s")
        self.retry_after = retry_after


class BadResponse(UpstreamError):
    """Response arrived but was not the JSON structure we expect."""


# --------------------------------------------------------------------------
# Steam
# --------------------------------------------------------------------------
@dataclass
class SearchResult:
    appid: int
    name: str


@dataclass
class ResolvedGame:
    appid: int
    name: str | None = None


@dataclass
class Price:
    currency: str | None = None
    initial: int | None = None
    final: int | None = None
    discount_percent: int = 0
    initial_formatted: str | None = None
    final_formatted: str | None = None


@dataclass
class SteamApp:
    appid: int
    name: str | None = None
    app_type: str | None = None
    is_free: bool = False
    short_description: str | None = None
    header_image: str | None = None
    developers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    release_date: str | None = None
    coming_soon: bool = False
    price: Price | None = None
    requirements_min: str | None = None   # raw HTML from Steam
    requirements_rec: str | None = None   # raw HTML from Steam

    @property
    def store_url(self) -> str:
        return f"https://store.steampowered.com/app/{self.appid}/"


@dataclass
class ReviewSummary:
    review_score_desc: str | None = None
    total_positive: int = 0
    total_negative: int = 0
    total_reviews: int = 0

    @property
    def percent_positive(self) -> int | None:
        rated = self.total_positive + self.total_negative
        if rated <= 0:
            return None
        return round(100 * self.total_positive / rated)


@dataclass
class Review:
    voted_up: bool | None
    text: str
    timestamp: int | None = None
    playtime_minutes: int | None = None
    votes_up: int | None = None


@dataclass
class NewsItem:
    gid: str | None
    title: str
    url: str | None
    contents: str
    date: int | None
    feedlabel: str | None = None
    feedname: str | None = None


# --------------------------------------------------------------------------
# ProtonDB
# --------------------------------------------------------------------------
@dataclass
class ProtonSummary:
    tier: str | None = None
    trending_tier: str | None = None
    best_reported_tier: str | None = None
    confidence: str | None = None
    score: float | None = None
    total: int | None = None


@dataclass
class ProtonCounts:
    reports: int
    timestamp: int


@dataclass
class ProtonReport:
    timestamp: int | None = None
    verdict: str | None = None       # "yes" / "no" as published by ProtonDB
    rating: str | None = None        # tier-like rating, when present
    proton_version: str | None = None
    hardware: str | None = None
    notes: str | None = None


@dataclass
class ReportsResult:
    reports: list[ProtonReport] = field(default_factory=list)
    ok: bool = False
    reason: str | None = None        # short, user-safe explanation when ok is False
