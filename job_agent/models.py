from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Opportunity:
    link: str
    title: str = ""
    company: str = ""
    location: str = ""
    source: str = "LinkedIn Gmail alert"
    email_subject: str = ""
    email_from: str = ""
    email_date: str = ""
    snippet: str = ""
    stipend_text: str = ""
    stipend_monthly_inr: int = 0
    women_only_match: bool = False
    grad_2028_match: bool = False
    internship_match: bool = False
    off_campus_match: bool = False
    ppo_or_placement_match: bool = False
    eighth_semester_match: bool = False
    score: int = 0
    matched_reasons: list[str] = field(default_factory=list)
    first_seen_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    last_seen_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

