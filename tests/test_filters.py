from job_agent.filters import evaluate_opportunity, extract_best_monthly_stipend


def test_extracts_one_lakh_monthly_words():
    amount, raw = extract_best_monthly_stipend("Stipend: one lakh per month for women interns")
    assert amount == 100_000
    assert "one lakh" in raw.lower()


def test_extracts_12_lpa_as_one_lakh_monthly():
    amount, raw = extract_best_monthly_stipend("Internship stipend / CTC is 12 LPA")
    assert amount == 100_000
    assert raw.lower() == "12 lpa"


def test_extracts_higher_lpa():
    amount, _ = extract_best_monthly_stipend("Paid internship with 18 LPA conversion")
    assert amount == 150_000


def test_extracts_numeric_monthly():
    amount, _ = extract_best_monthly_stipend("Stipend INR 100000 per month")
    assert amount == 100_000


def test_ignores_tracking_ids_as_stipend():
    amount, raw = extract_best_monthly_stipend("midSig=12345678 otpToken=96430703 tracking id only")
    assert amount == 0
    assert raw == ""


def test_opportunity_match_requires_only_2028_signal():
    text = """
    LinkedIn Jobs: software engineer role for B.Tech 2028 batch.
    """
    result = evaluate_opportunity(text)
    assert result.matched is True
    assert result.grad_2028_match is True


def test_opportunity_accepts_2028_without_stipend_or_women_signal():
    text = "Off-campus role for 2028 passouts. No stipend mentioned."
    result = evaluate_opportunity(text)
    assert result.matched is True
    assert result.stipend_monthly_inr == 0
    assert result.women_only_match is False


def test_opportunity_rejects_without_2028_signal():
    text = "Women diversity internship with INR 100000 per month stipend."
    result = evaluate_opportunity(text)
    assert result.matched is False
