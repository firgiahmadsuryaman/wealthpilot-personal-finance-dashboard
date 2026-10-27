# Security Policy

WealthPilot is a local-first portfolio project, not a hardened multi-user financial service.

## Safe use

- Keep the app bound to `127.0.0.1` unless authentication, authorization, HTTPS, rate limiting, and deployment hardening have been added and reviewed.
- Keep provider keys in `.env`; never commit `.env`, API keys, access tokens, cookies, PINs, or OTPs.
- Do not enter Pegadaian or Pluang account credentials into this application. The current version does not log in to either service.
- Back up the SQLite database before changing or upgrading the application.
- Review the data provider's market-data license before redisplaying quotes to other people or publishing market data.

## Reporting a vulnerability

For this personal portfolio project, please do not publish secrets or private financial records in an issue. Share a minimal reproducible report with the repository owner through a private channel before disclosing a suspected security issue publicly.
