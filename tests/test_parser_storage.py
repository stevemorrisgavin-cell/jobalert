from pathlib import Path

from job_agent.gmail_reader import EmailAlert
from job_agent.models import Opportunity
from job_agent.parser import extract_links, normalize_link
from job_agent.storage import load_opportunities, merge_opportunities, save_json


def test_normalize_link_removes_tracking():
    link = "https://www.linkedin.com/jobs/view/123/?utm_source=email&currentJobId=123&trk=abc#frag"
    assert normalize_link(link) == "https://www.linkedin.com/jobs/view/123?currentJobId=123"


def test_extract_links_from_html_alert():
    alert = EmailAlert(
        message_id="1",
        subject="LinkedIn job alert",
        sender="jobs-listings@linkedin.com",
        date="2026-06-29T00:00:00+00:00",
        body_text="",
        body_html='<a href="https://www.linkedin.com/jobs/view/123/?utm_source=email">Women internship</a>',
    )
    links = extract_links(alert)
    assert links == [("https://www.linkedin.com/jobs/view/123", "Women internship")]


def test_merge_deduplicates_links(tmp_path: Path):
    path = tmp_path / "opportunities.json"
    existing = {}
    first = Opportunity(link="https://www.linkedin.com/jobs/view/123?utm_source=email", title="First", score=50)
    second = Opportunity(link="https://www.linkedin.com/jobs/view/123", title="Second", score=80)

    assert merge_opportunities(existing, [first]) == 1
    assert merge_opportunities(existing, [second]) == 0
    save_json(path, existing)

    loaded = load_opportunities(path)
    assert len(loaded) == 1
    item = next(iter(loaded.values()))
    assert item.score == 80

