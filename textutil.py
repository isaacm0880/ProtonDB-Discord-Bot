"""Text cleaning helpers (no Discord dependency, so they are easy to test).

Steam returns HTML (store fields), BBCode (news, reviews) and occasionally raw
placeholders. None of it should reach Discord untouched.
"""
from __future__ import annotations

import html
import re

ZWSP = "\u200b"

_BR = re.compile(r"<\s*br\s*/?\s*>", re.I)
_LI_OPEN = re.compile(r"<\s*li\b[^>]*>", re.I)
_BLOCK_CLOSE = re.compile(r"<\s*/\s*(?:p|div|li|ul|ol|h[1-6]|tr|table)\s*>", re.I)
# Only things that look like real tags (so "a < b" survives).
_ANY_TAG = re.compile(r"</?[A-Za-z][^>]*>")

_BB_MEDIA = re.compile(
    r"\[(?P<t>img|video|previewyoutube|youtube|gif)\b[^\]]*\].*?\[/(?P=t)\]",
    re.I | re.S,
)
_BB_LIST_ITEM = re.compile(r"\[\*\]")
_BB_TAGS = (
    "b|i|u|s|strike|h1|h2|h3|h4|h5|h6|p|url|list|olist|quote|code|spoiler|"
    "noparse|hr|table|tr|td|th|center|left|right|img|video|previewyoutube|"
    "youtube|gif|dynamiclink|steamid|code"
)
_BB_ANY = re.compile(rf"\[/?(?:{_BB_TAGS})(?:[= ][^\]]*)?\]", re.I)
_BB_TRAILING_FRAGMENT = re.compile(r"\[[^\]\n]{0,200}$")
_STEAM_PLACEHOLDER = re.compile(r"\{STEAM_CLAN_(?:LOC_)?IMAGE\}\S*", re.I)
_URL = re.compile(r"https?://\S+", re.I)
_HSPACE = re.compile(r"[ \t\r\f\v\u00a0]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def normalise_whitespace(text: str, keep_lines: bool = True) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_HSPACE.sub(" ", line).strip() for line in text.split("\n")]
    if keep_lines:
        return _MANY_NEWLINES.sub("\n\n", "\n".join(lines)).strip()
    return " ".join(part for part in lines if part).strip()


def html_to_text(value: object, keep_lines: bool = True) -> str:
    """Convert Steam's HTML snippets to plain text, keeping simple line breaks."""
    if value is None:
        return ""
    text = str(value)
    text = _BR.sub("\n", text)
    text = _LI_OPEN.sub("\n• ", text)
    text = _BLOCK_CLOSE.sub("\n", text)
    text = _ANY_TAG.sub("", text)
    text = html.unescape(text)
    return normalise_whitespace(text, keep_lines)


def compact_lines(text: str) -> str:
    """Drop blank lines (used for requirement lists)."""
    return "\n".join(line for line in text.split("\n") if line.strip())


def bbcode_to_text(value: object, keep_lines: bool = True, drop_urls: bool = False) -> str:
    """Strip Steam BBCode / placeholders (reviews and news)."""
    if value is None:
        return ""
    text = str(value)
    text = _BB_MEDIA.sub("", text)
    text = _STEAM_PLACEHOLDER.sub("", text)
    text = _BB_LIST_ITEM.sub("\n• ", text)
    text = _BB_ANY.sub("", text)
    text = _BB_TRAILING_FRAGMENT.sub("", text)  # tag cut in half by API truncation
    if drop_urls:
        text = _URL.sub("", text)
    return normalise_whitespace(text, keep_lines)


def news_preview(contents: object, limit: int = 260) -> str:
    """Concise plain-text preview of a Steam news item (HTML and/or BBCode)."""
    text = html_to_text(bbcode_to_text(contents, keep_lines=True, drop_urls=True), keep_lines=False)
    return truncate(text, limit)


def neutralise(text: str) -> str:
    """Stop user-generated text from pinging anyone or forming masked links."""
    return text.replace("@", "@" + ZWSP).replace("](", "]" + ZWSP + "(")


def truncate(text: str, limit: int, suffix: str = "…") -> str:
    """Shorten to at most ``limit`` characters, preferring a word boundary."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return text[:limit]
    cut = text[: limit - len(suffix)].rstrip()
    space = cut.rfind(" ")
    if space >= int(len(cut) * 0.7):
        cut = cut[:space].rstrip()
    return cut + suffix


def safe_http_url(url: object, max_length: int = 1500) -> str | None:
    """Return ``url`` only if it is a plain http(s) URL that is safe in a markdown link."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url or len(url) > max_length:
        return None
    if not re.match(r"^https?://[^\s<>]+$", url, re.I):
        return None
    return url.replace("(", "%28").replace(")", "%29")


def choice_label(name: str, appid: int, limit: int = 100) -> str:
    """Autocomplete label that always keeps the App ID visible within Discord's limit."""
    suffix = f" (App {appid})"
    return truncate(name, limit - len(suffix)) + suffix
