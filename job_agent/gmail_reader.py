from __future__ import annotations

import email
import imaplib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Iterable

from .config import Config

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailAlert:
    message_id: str
    subject: str
    sender: str
    date: str
    body_text: str
    body_html: str


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    decoded_parts = email.header.decode_header(value)
    result: list[str] = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result).strip()


def _message_date(raw: Message) -> str:
    try:
        parsed = parsedate_to_datetime(raw.get("Date", ""))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _extract_bodies(raw: Message) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []

    if raw.is_multipart():
        parts: Iterable[Message] = raw.walk()
    else:
        parts = [raw]

    for part in parts:
        content_type = part.get_content_type()
        disposition = (part.get("Content-Disposition") or "").lower()
        if "attachment" in disposition:
            continue
        if content_type not in {"text/plain", "text/html"}:
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")
        if content_type == "text/plain":
            text_parts.append(decoded)
        else:
            html_parts.append(decoded)

    return "\n".join(text_parts), "\n".join(html_parts)


def _select_mailbox(client: imaplib.IMAP4_SSL, preferred_mailbox: str) -> str:
    candidates = [
        preferred_mailbox,
        '"[Gmail]/All Mail"',
        "[Gmail]/All Mail",
        '"[Google Mail]/All Mail"',
        "[Google Mail]/All Mail",
        "INBOX",
    ]
    seen: set[str] = set()
    for mailbox in candidates:
        if not mailbox or mailbox in seen:
            continue
        seen.add(mailbox)
        status, _ = client.select(mailbox, readonly=True)
        if status == "OK":
            return mailbox
    raise RuntimeError("Could not select Gmail mailbox. Tried All Mail and INBOX.")


def _search_linkedin_message_ids(client: imaplib.IMAP4_SSL, lookback_days: int) -> list[bytes]:
    raw_queries = [
        f'newer_than:{lookback_days}d from:(linkedin.com)',
        f'newer_than:{lookback_days}d (from:linkedin OR from:linkedin.com)',
        f'newer_than:{lookback_days}d linkedin',
    ]
    for raw_query in raw_queries:
        try:
            status, data = client.search(None, "X-GM-RAW", raw_query)
            if status == "OK":
                ids = data[0].split()
                LOGGER.info("Gmail raw search matched %s emails with query=%s", len(ids), raw_query)
                if ids:
                    return ids
        except imaplib.IMAP4.error as exc:
            LOGGER.warning("Gmail raw search failed for query=%s error=%s", raw_query, exc)

    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%d-%b-%Y")
    queries = [
        f'(SINCE "{since}" FROM "linkedin")',
        f'(SINCE "{since}" FROM "linkedin.com")',
        f'(SINCE "{since}" TEXT "LinkedIn")',
    ]
    message_ids: set[bytes] = set()
    for query in queries:
        status, data = client.search(None, query)
        if status != "OK":
            LOGGER.warning("IMAP search failed query=%s status=%s", query, status)
            continue
        message_ids.update(data[0].split())
    LOGGER.info("Fallback IMAP search matched %s unique LinkedIn emails", len(message_ids))
    return sorted(message_ids, key=lambda value: int(value) if value.isdigit() else 0)


def read_linkedin_alerts(config: Config) -> list[EmailAlert]:
    alerts: list[EmailAlert] = []

    LOGGER.info("Connecting to Gmail IMAP mailbox=%s lookback_days=%s", config.mailbox, config.lookback_days)
    with imaplib.IMAP4_SSL(config.imap_host) as client:
        client.login(config.gmail_user, config.gmail_app_password)
        selected_mailbox = _select_mailbox(client, config.mailbox)
        LOGGER.info("Selected Gmail mailbox=%s", selected_mailbox)

        message_ids = _search_linkedin_message_ids(client, config.lookback_days)
        LOGGER.info("Found %s candidate LinkedIn emails", len(message_ids))
        for message_id in message_ids:
            status, msg_data = client.fetch(message_id, "(RFC822)")
            if status != "OK":
                LOGGER.warning("Skipping message %s because fetch failed: %s", message_id, status)
                continue
            raw_bytes = msg_data[0][1]
            raw = email.message_from_bytes(raw_bytes)
            body_text, body_html = _extract_bodies(raw)
            sender = _decode_header_value(raw.get("From"))
            subject = _decode_header_value(raw.get("Subject"))
            sender_subject = f"{sender} {subject}".lower()
            is_job_alert = (
                "jobs-listings@linkedin.com" in sender_subject
                or "job alert" in sender_subject
                or "is hiring" in sender_subject
                or "jobs for you" in sender_subject
                or "top job" in sender_subject
            )
            if "linkedin" not in sender_subject or not is_job_alert:
                continue
            alerts.append(
                EmailAlert(
                    message_id=raw.get("Message-ID", message_id.decode("ascii", errors="replace")),
                    subject=subject,
                    sender=sender,
                    date=_message_date(raw),
                    body_text=body_text,
                    body_html=body_html,
                )
            )
    return alerts
