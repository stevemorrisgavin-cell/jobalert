# LinkedIn Gmail Job Alert Agent

Simple Python agent that reads LinkedIn job alert emails from Gmail, filters women-only off-campus internship or internship-cum-placement opportunities for 2028 graduates, keeps matches with stipend equivalent to at least INR 1,00,000 per month, and sends one daily report email at 9 PM IST.

The agent does not scrape LinkedIn. It only reads Gmail alert email content.

## Features

- Reads LinkedIn job alert emails using Gmail IMAP.
- Filters for women/diversity hiring, 2028 batch, internship, and stipend >= INR 1,00,000/month.
- Understands stipend forms like `1 lakh/month`, `one lakh per month`, `100000/month`, `12 LPA`, and higher values.
- Deduplicates normalized LinkedIn job links.
- Persists results to `results/opportunities.json` and `results/opportunities.csv`.
- Sends a daily email report using Gmail SMTP.
- Runs on GitHub Actions every 3 hours plus a daily 9 PM IST report.

## GitHub Setup

1. Create a new GitHub repository.
2. Upload/push this folder to the repository.
3. Go to `Settings -> Secrets and variables -> Actions -> New repository secret`.
4. Add these secrets:

```text
GMAIL_USER=your-alert-gmail@gmail.com
GMAIL_APP_PASSWORD=your Gmail App Password
REPORT_TO=receiver@example.com
```

5. Go to `Settings -> Actions -> General -> Workflow permissions`.
6. Select `Read and write permissions`.
7. Save.
8. Open the `Actions` tab and manually run `Search LinkedIn Gmail Alerts` once.

## Gmail App Password

Use a Gmail App Password, not your normal Gmail password.

Recommended Gmail setup:

- Create a separate Gmail account only for job alerts.
- Enable 2-Step Verification.
- Create an App Password.
- Subscribe that Gmail to LinkedIn job alerts.
- Put the App Password into GitHub Secrets as `GMAIL_APP_PASSWORD`.

## Workflows

Search job:

```yaml
cron: "0 */3 * * *"
```

Daily report:

```yaml
cron: "30 15 * * *"
```

GitHub cron uses UTC. `15:30 UTC` is `21:00 IST`.

## Local Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
pytest -q
```

## Local Run

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Run:

```bash
python -m job_agent.main fetch
python -m job_agent.main report
```

## Important Limitation

LinkedIn alert emails often do not include stipend details. Because this project does not scrape LinkedIn directly, it can only match stipend when the stipend appears in the email subject/body/link text.
