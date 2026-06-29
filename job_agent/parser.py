from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

from .gmail_reader import EmailAlert


class LinkAndTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.text_parts: list[str] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href")
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            label = " ".join(" ".join(self._current_text).split())
            self.links.append((self._current_href, label))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data)
            if self._current_href:
                self._current_text.append(data)


def html_to_links_and_text(body_html: str) -> tuple[list[tuple[str, str]], str]:
    parser = LinkAndTextParser()
    parser.feed(body_html or "")
    return parser.links, html.unescape(" ".join(parser.text_parts))


def normalize_link(raw_url: str) -> str:
    raw_url = (
        raw_url.strip()
        .replace("&amp;", "&")
        .replace("&#38;", "&")
        .replace("&quot;", '"')
    )
    parsed = urlparse(raw_url)
    query = parse_qs(parsed.query)

    for key in ("url", "u", "redirectUrl"):
        if key in query and query[key]:
            decoded = unquote(query[key][0])
            if "linkedin.com" in decoded:
                raw_url = decoded
                parsed = urlparse(raw_url)
                query = parse_qs(parsed.query)
                break

    clean_query = []
    for key, values in query.items():
        if key.lower().startswith("utm_") or key.lower() in {"trk", "lipi", "midtoken", "midtok"}:
            continue
        for value in values:
            clean_query.append(f"{key}={value}")

    path = parsed.path.rstrip("/") or parsed.path
    return parsed._replace(path=path, query="&".join(clean_query), fragment="").geturl()


def extract_links(alert: EmailAlert) -> list[tuple[str, str]]:
    html_links, _ = html_to_links_and_text(alert.body_html)
    text_links = [(match.group(0), "") for match in re.finditer(r"https?://[^\s<>\"]+", alert.body_text)]
    seen: set[str] = set()
    links: list[tuple[str, str]] = []
    for raw_url, label in html_links + text_links:
        if "linkedin.com" not in raw_url.lower():
            continue
        if not any(token in raw_url.lower() for token in ("/jobs/", "currentJobId", "job")):
            continue
        normalized = normalize_link(raw_url)
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append((normalized, label))
    return links


def compact_text(text: str, max_length: int = 1200) -> str:
    text = re.sub(r"\s+", " ", html.unescape(text or "")).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def alert_search_text(alert: EmailAlert) -> str:
    _, html_text = html_to_links_and_text(alert.body_html)
    return compact_text(" ".join([alert.subject, alert.sender, alert.body_text, html_text]), max_length=8000)


def guess_title(label: str, search_text: str) -> str:
    label = compact_text(label, 120)
    if label and not re.search(r"view|apply|see job|jobs?|linkedin", label, re.I):
        return label
    patterns = [
        r"(?P<title>[\w .,+/&()-]{8,90}intern[\w .,+/&()-]{0,60})",
        r"(?P<title>[\w .,+/&()-]{8,90}placement[\w .,+/&()-]{0,60})",
    ]
    for pattern in patterns:
        match = re.search(pattern, search_text, re.I)
        if match:
            return compact_text(match.group("title"), 120)
    return "LinkedIn opportunity"
