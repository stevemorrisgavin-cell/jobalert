from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone

from .config import load_config
from .filters import evaluate_opportunity
from .gmail_reader import read_linkedin_alerts
from .logging_setup import setup_logging
from .models import Opportunity
from .parser import alert_search_text, compact_text, extract_links, guess_title
from .reporter import send_daily_report
from .storage import load_opportunities, merge_opportunities, save_candidate_files, save_csv, save_json

LOGGER = logging.getLogger(__name__)


def fetch() -> int:
    config = load_config()
    setup_logging(config)

    alerts = read_linkedin_alerts(config)
    existing = load_opportunities(config.results_json)
    matches: list[Opportunity] = []
    candidates: list[dict] = []
    diagnostics = {
        "run_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "lookback_days": config.lookback_days,
        "linkedin_alert_emails_read": len(alerts),
        "linkedin_job_links_found": 0,
        "opportunities_checked": 0,
        "matched_this_run": 0,
        "added_this_run": 0,
        "total_saved_matches": 0,
        "rejection_counts": {
            "missing_link": 0,
            "missing_women_or_diversity_signal": 0,
            "missing_2028_signal": 0,
            "missing_internship_signal": 0,
            "missing_minimum_stipend": 0,
        },
    }

    for alert in alerts:
        search_text = alert_search_text(alert)
        links = extract_links(alert)
        diagnostics["linkedin_job_links_found"] += len(links)
        if not links:
            links = [("", "")]

        for link, label in links:
            result = evaluate_opportunity(" ".join([label, search_text]))
            diagnostics["opportunities_checked"] += 1
            missing_reasons = []
            if not link:
                missing_reasons.append("missing LinkedIn job link")
            if not result.women_only_match:
                missing_reasons.append("missing women/diversity signal")
            if not result.grad_2028_match:
                missing_reasons.append("missing 2028 signal")
            if not result.internship_match:
                missing_reasons.append("missing internship signal")
            if result.stipend_monthly_inr < 100_000:
                missing_reasons.append("missing stipend >= INR 1,00,000/month")

            if link:
                candidates.append(
                    {
                        "link": link,
                        "title": guess_title(label, search_text),
                        "score": result.score,
                        "strict_match": result.matched,
                        "stipend_text": result.stipend_text,
                        "stipend_monthly_inr": result.stipend_monthly_inr,
                        "missing_reasons": missing_reasons,
                        "matched_reasons": result.reasons,
                        "email_subject": alert.subject,
                        "email_date": alert.date,
                        "snippet": compact_text(search_text, 500),
                    }
                )
            if not result.matched or not link:
                if not link:
                    diagnostics["rejection_counts"]["missing_link"] += 1
                if not result.women_only_match:
                    diagnostics["rejection_counts"]["missing_women_or_diversity_signal"] += 1
                if not result.grad_2028_match:
                    diagnostics["rejection_counts"]["missing_2028_signal"] += 1
                if not result.internship_match:
                    diagnostics["rejection_counts"]["missing_internship_signal"] += 1
                if result.stipend_monthly_inr < 100_000:
                    diagnostics["rejection_counts"]["missing_minimum_stipend"] += 1
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
    save_candidate_files(config.candidates_json, config.candidates_csv, candidates)
    diagnostics["matched_this_run"] = len(matches)
    diagnostics["added_this_run"] = added
    diagnostics["total_saved_matches"] = len(existing)
    diagnostics["active_candidates_saved"] = len(candidates)
    config.fetch_diagnostics_json.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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
