from __future__ import annotations

import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from .config import Config
from .models import Opportunity
from .storage import load_opportunities


IST = ZoneInfo("Asia/Kolkata")


def build_report(opportunities: list[Opportunity]) -> tuple[str, str]:
    today = datetime.now(IST).strftime("%d %b %Y")
    subject = f"Daily LinkedIn internship matches - {today} ({len(opportunities)})"

    if not opportunities:
        return subject, f"No matching LinkedIn opportunities found for {today}.\n"

    lines = [
        f"Daily LinkedIn internship matches - {today}",
        "",
        f"Total matches: {len(opportunities)}",
        "",
    ]
    for index, item in enumerate(opportunities[:30], start=1):
        lines.extend(
            [
                f"{index}. {item.title}",
                f"   Link: {item.link}",
                f"   Stipend: {item.stipend_text or 'matched'} (~INR {item.stipend_monthly_inr:,}/month)",
                f"   Score: {item.score}",
                f"   Reasons: {', '.join(item.matched_reasons)}",
                f"   Email: {item.email_subject}",
                "",
            ]
        )
    if len(opportunities) > 30:
        lines.append(f"...and {len(opportunities) - 30} more in results/opportunities.csv")
    return subject, "\n".join(lines)


def send_daily_report(config: Config) -> int:
    opportunities = list(load_opportunities(config.results_json).values())
    opportunities.sort(key=lambda item: (item.score, item.first_seen_utc), reverse=True)
    subject, body = build_report(opportunities)

    message = EmailMessage()
    message["From"] = config.gmail_user
    message["To"] = config.report_to
    message["Subject"] = subject
    message.set_content(body)

    if config.results_csv.exists():
        message.add_attachment(
            config.results_csv.read_bytes(),
            maintype="text",
            subtype="csv",
            filename="opportunities.csv",
        )

    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
        smtp.login(config.gmail_user, config.gmail_app_password)
        smtp.send_message(message)

    config.report_json.write_text(
        json.dumps(
            {
                "sent_at_ist": datetime.now(IST).replace(microsecond=0).isoformat(),
                "to": config.report_to,
                "count": len(opportunities),
                "subject": subject,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(opportunities)

