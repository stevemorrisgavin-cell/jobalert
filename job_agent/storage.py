from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Opportunity
from .parser import normalize_link


CSV_FIELDS = [
    "link",
    "title",
    "company",
    "location",
    "source",
    "email_subject",
    "email_from",
    "email_date",
    "stipend_text",
    "stipend_monthly_inr",
    "women_only_match",
    "grad_2028_match",
    "internship_match",
    "off_campus_match",
    "ppo_or_placement_match",
    "eighth_semester_match",
    "score",
    "matched_reasons",
    "first_seen_utc",
    "last_seen_utc",
    "snippet",
]


def load_opportunities(path: Path) -> dict[str, Opportunity]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    opportunities: dict[str, Opportunity] = {}
    for item in data:
        item["link"] = normalize_link(item["link"])
        opportunities[item["link"]] = Opportunity(**item)
    return opportunities


def merge_opportunities(existing: dict[str, Opportunity], new_items: list[Opportunity]) -> int:
    added = 0
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for item in new_items:
        item.link = normalize_link(item.link)
        if item.link in existing:
            old = existing[item.link]
            old.last_seen_utc = now
            old.score = max(old.score, item.score)
            old.matched_reasons = sorted(set(old.matched_reasons) | set(item.matched_reasons))
            if item.snippet and len(item.snippet) > len(old.snippet):
                old.snippet = item.snippet
            continue
        existing[item.link] = item
        added += 1
    return added


def save_json(path: Path, opportunities: dict[str, Opportunity]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(opportunities.values(), key=lambda item: (item.score, item.first_seen_utc), reverse=True)
    path.write_text(
        json.dumps([item.to_dict() for item in ordered], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def save_csv(path: Path, opportunities: dict[str, Opportunity]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(opportunities.values(), key=lambda item: (item.score, item.first_seen_utc), reverse=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in ordered:
            row = item.to_dict()
            row["matched_reasons"] = "; ".join(item.matched_reasons)
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def save_candidate_files(json_path: Path, csv_path: Path, candidates: list[dict]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(candidates, key=lambda item: item.get("score", 0), reverse=True)
    json_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = [
        "link",
        "title",
        "score",
        "strict_match",
        "stipend_text",
        "stipend_monthly_inr",
        "missing_reasons",
        "matched_reasons",
        "email_subject",
        "email_date",
        "snippet",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for candidate in ordered:
            row = dict(candidate)
            row["missing_reasons"] = "; ".join(row.get("missing_reasons", []))
            row["matched_reasons"] = "; ".join(row.get("matched_reasons", []))
            writer.writerow({field: row.get(field, "") for field in fields})
