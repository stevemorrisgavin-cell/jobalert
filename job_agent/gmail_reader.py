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


def read_linkedin_alerts(config: Config) -> list[EmailAlert]:
    since = (datetime.now(timezone.utc) - timedelta(days=config.lookback_days)).strftime("%d-%b-%Y")
    query = f'(SINCE "{since}" FROM "linkedin")'
    alerts: list[EmailAlert] = []

    LOGGER.info("Connecting to Gmail IMAP mailbox=%s lookback_days=%s", config.mailbox, config.lookback_days)
    with imaplib.IMAP4_SSL(config.imap_host) as client:
        client.login(config.gmail_user, config.gmail_app_password)
        client.select(config.mailbox)
        status, data = client.search(None, query)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        message_ids = data[0].split()
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
            if "linkedin" not in sender.lower() and "linkedin" not in subject.lower():
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

