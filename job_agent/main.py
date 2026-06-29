from __future__ import annotations

import argparse
import logging

from .config import load_config
from .filters import evaluate_opportunity
from .gmail_reader import read_linkedin_alerts
from .logging_setup import setup_logging
from .models import Opportunity
from .parser import alert_search_text, compact_text, extract_links, guess_title
from .reporter import send_daily_report
from .storage import load_opportunities, merge_opportunities, save_csv, save_json

LOGGER = logging.getLogger(__name__)


def fetch() -> int:
    config = load_config()
    setup_logging(config)

    alerts = read_linkedin_alerts(config)
    existing = load_opportunities(config.results_json)
    matches: list[Opportunity] = []

    for alert in alerts:
        search_text = alert_search_text(alert)
        links = extract_links(alert)
        if not links:
            links = [("", "")]

        for link, label in links:
            result = evaluate_opportunity(" ".join([label, search_text]))
            if not result.matched or not link:
                continue

            matches.append(
                Opportunity(
                    link=link,
                    title=guess_title(label, search_text),
                    email_subject=alert.subject,
                    email_from=alert.sender,
                    email_date=alert.date,
                    snippet=compact_text(search_text, 600),
                    stipend_text=result.stipend_text,
                    stipend_monthly_inr=result.stipend_monthly_inr,
                    women_only_match=result.women_only_match,
                    grad_2028_match=result.grad_2028_match,
                    internship_match=result.internship_match,
                    off_campus_match=result.off_campus_match,
                    ppo_or_placement_match=result.ppo_or_placement_match,
                    eighth_semester_match=result.eighth_semester_match,
                    score=result.score,
                    matched_reasons=result.reasons,
                )
            )

    added = merge_opportunities(existing, matches)
    save_json(config.results_json, existing)
    save_csv(config.results_csv, existing)
    LOGGER.info("Fetch complete alerts=%s matches=%s added=%s total=%s", len(alerts), len(matches), added, len(existing))
    print(f"Fetch complete: alerts={len(alerts)} matches={len(matches)} added={added} total={len(existing)}")
    return 0


def report() -> int:
    config = load_config()
    setup_logging(config)
    count = send_daily_report(config)
    LOGGER.info("Daily report sent to %s with %s matches", config.report_to, count)
    print(f"Daily report sent to {config.report_to} with {count} matches")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LinkedIn Gmail job alert agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fetch", help="Read LinkedIn Gmail alerts and update results")
    subparsers.add_parser("report", help="Send the daily report email")
    args = parser.parse_args()

    if args.command == "fetch":
        return fetch()
    if args.command == "report":
        return report()
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

