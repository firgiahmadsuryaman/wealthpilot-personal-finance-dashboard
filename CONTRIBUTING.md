# Contributing

WealthPilot is currently a personal portfolio project. Bug reports and improvements are welcome, especially around accounting correctness, test coverage, accessibility, and data-source transparency.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Guidelines

- Include a regression test for accounting, API validation, or goal-management changes.
- Do not add made-up market prices or seed sample holdings into the default database.
- Keep API keys, `.env`, databases, logs, and personal screenshots out of commits.
- Preserve the distinction between external cash flows and internal asset trades.
- Document data-source freshness, limitations, and licensing when adding a provider.
- Avoid integrations that require users to share broker passwords, PINs, OTPs, or session tokens.
