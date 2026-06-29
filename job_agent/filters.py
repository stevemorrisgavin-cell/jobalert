from __future__ import annotations

import re
from dataclasses import dataclass


MIN_MONTHLY_STIPEND_INR = 100_000

WOMEN_PATTERNS = [
    r"\bwomen\b",
    r"\bwoman\b",
    r"\bfemale\b",
    r"\bgirls?\b",
    r"\bdiversity\b",
    r"\bwomen[- ]only\b",
    r"\bfemale candidates?\b",
    r"\bwomen candidates?\b",
    r"\bshecodes\b",
    r"\bherkey\b",
    r"\bwomen in tech\b",
]

GRAD_2028_PATTERNS = [
    r"\b2028\b",
    r"\bbatch of 2028\b",
    r"\b2028 batch\b",
    r"\bclass of 2028\b",
    r"\bgraduat(?:e|ing|es) in 2028\b",
    r"\bpass(?:ing)? out in 2028\b",
    r"\b2028 passouts?\b",
]

INTERNSHIP_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\binternship-cum-placement\b",
    r"\binternship cum placement\b",
]

OFF_CAMPUS_PATTERNS = [
    r"\boff[- ]campus\b",
    r"\bcampus hiring\b",
    r"\bgraduate hiring\b",
    r"\bearly careers?\b",
    r"\buniversity hiring\b",
]

PPO_PATTERNS = [
    r"\bppo\b",
    r"\bpre[- ]placement offer\b",
    r"\bplacement\b",
    r"\bfull[- ]time offer\b",
    r"\bconvert(?:ible|sion)?\b",
    r"\binternship-cum-placement\b",
    r"\binternship cum placement\b",
]

EIGHTH_SEM_PATTERNS = [
    r"\b8th sem(?:ester)?\b",
    r"\beighth sem(?:ester)?\b",
    r"\bfinal sem(?:ester)?\b",
]


@dataclass(frozen=True)
class FilterResult:
    matched: bool
    stipend_text: str
    stipend_monthly_inr: int
    women_only_match: bool
    grad_2028_match: bool
    internship_match: bool
    off_campus_match: bool
    ppo_or_placement_match: bool
    eighth_semester_match: bool
    score: int
    reasons: list[str]


def _has_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _word_number_to_float(value: str) -> float | None:
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }
    cleaned = value.lower().strip()
    if cleaned in words:
        return float(words[cleaned])
    try:
        return float(cleaned.replace(",", ""))
    except ValueError:
        return None


def _context_monthly_multiplier(context: str) -> float:
    context = context.lower()
    if re.search(r"\b(lpa|lakhs?\s*(?:per\s*)?(?:annum|year|yr)|ctc|annual|yearly|per\s+year|/year|/yr)\b", context):
        return 1 / 12
    return 1


def extract_best_monthly_stipend(text: str) -> tuple[int, str]:
    candidates: list[tuple[int, str]] = []
    normalized = text.replace("₹", " ₹ ")

    patterns = [
        r"(?P<raw>(?P<num>\d+(?:\.\d+)?)\s*(?:lpa|LPA))",
        r"(?P<raw>(?P<num>\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|L)\s*(?:/|per)?\s*(?P<period>month|monthly|pm|p\.m\.|year|yr|annum|pa|p\.a\.)?)",
        r"(?P<raw>(?P<num>one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+(?:lakh|lakhs|lac|lacs)\s*(?:/|per)?\s*(?P<period>month|monthly|pm|p\.m\.|year|yr|annum|pa|p\.a\.)?)",
        r"(?P<raw>(?:₹|rs\.?|inr)\s*(?P<num>\d{5,8}(?:,\d{2,3})*)\s*(?:/|per)?\s*(?P<period>month|monthly|pm|p\.m\.|year|yr|annum|pa|p\.a\.)?)",
        r"(?P<raw>(?P<num>\d{5,8}(?:,\d{2,3})*)\s*(?:/|per)\s*(?P<period>month|monthly|pm|p\.m\.|year|yr|annum|pa|p\.a\.))",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, normalized, re.I):
            number = _word_number_to_float(match.group("num"))
            if number is None:
                continue
            raw = " ".join(match.group("raw").split())
            period = (match.groupdict().get("period") or "").lower()
            context = normalized[max(0, match.start() - 40) : match.end() + 40]

            if re.search(r"\blpa\b", raw, re.I):
                monthly = int(number * 100_000 / 12)
            elif re.search(r"lakh|lakhs|lac|lacs|\bL\b", raw, re.I):
                monthly = int(number * 100_000)
                if period in {"year", "yr", "annum", "pa", "p.a."}:
                    monthly = int(monthly / 12)
                elif not period:
                    monthly = int(monthly * _context_monthly_multiplier(context))
            else:
                monthly = int(str(number).replace(",", "") if isinstance(number, str) else number)
                if period in {"year", "yr", "annum", "pa", "p.a."}:
                    monthly = int(monthly / 12)
                elif not period:
                    monthly = int(monthly * _context_monthly_multiplier(context))

            candidates.append((monthly, raw))

    if not candidates:
        return 0, ""
    return max(candidates, key=lambda item: item[0])


def evaluate_opportunity(text: str) -> FilterResult:
    women = _has_any(WOMEN_PATTERNS, text)
    grad_2028 = _has_any(GRAD_2028_PATTERNS, text)
    internship = _has_any(INTERNSHIP_PATTERNS, text)
    off_campus = _has_any(OFF_CAMPUS_PATTERNS, text)
    ppo = _has_any(PPO_PATTERNS, text)
    eighth_sem = _has_any(EIGHTH_SEM_PATTERNS, text)
    stipend_monthly, stipend_text = extract_best_monthly_stipend(text)
    stipend_ok = stipend_monthly >= MIN_MONTHLY_STIPEND_INR

    reasons: list[str] = []
    score = 0
    for label, matched, points in [
        ("women-only/diversity signal", women, 30),
        ("2028 graduate signal", grad_2028, 25),
        ("internship signal", internship, 15),
        ("off-campus/early-career signal", off_campus, 10),
        ("PPO/placement signal", ppo, 10),
        ("8th semester preference", eighth_sem, 5),
        ("stipend >= INR 1,00,000/month", stipend_ok, 30),
    ]:
        if matched:
            reasons.append(label)
            score += points

    matched = women and grad_2028 and internship and stipend_ok
    return FilterResult(
        matched=matched,
        stipend_text=stipend_text,
        stipend_monthly_inr=stipend_monthly,
        women_only_match=women,
        grad_2028_match=grad_2028,
        internship_match=internship,
        off_campus_match=off_campus,
        ppo_or_placement_match=ppo,
        eighth_semester_match=eighth_sem,
        score=score,
        reasons=reasons,
    )
