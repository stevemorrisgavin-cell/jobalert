from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
LOGS_DIR = ROOT_DIR / "logs"


@dataclass(frozen=True)
class Config:
    gmail_user: str
    gmail_app_password: str
    report_to: str
    imap_host: str = "imap.gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    mailbox: str = "INBOX"
    lookback_days: int = 21
    results_json: Path = RESULTS_DIR / "opportunities.json"
    results_csv: Path = RESULTS_DIR / "opportunities.csv"
    candidates_json: Path = RESULTS_DIR / "active_candidates.json"
    candidates_csv: Path = RESULTS_DIR / "active_candidates.csv"
    fetch_diagnostics_json: Path = RESULTS_DIR / "fetch_diagnostics.json"
    report_json: Path = RESULTS_DIR / "daily_report.json"
    log_file: Path = LOGS_DIR / "agent.log"


def load_config() -> Config:
    load_dotenv(ROOT_DIR / ".env")

    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    report_to = os.getenv("REPORT_TO", "").strip()

    missing = [
        name
        for name, value in {
            "GMAIL_USER": gmail_user,
            "GMAIL_APP_PASSWORD": gmail_app_password,
            "REPORT_TO": report_to,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        gmail_user=gmail_user,
        gmail_app_password=gmail_app_password,
        report_to=report_to,
        imap_host=os.getenv("IMAP_HOST", "imap.gmail.com").strip(),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        mailbox=os.getenv("GMAIL_MAILBOX", "INBOX").strip(),
        lookback_days=int(os.getenv("LOOKBACK_DAYS", "21")),
    )


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
