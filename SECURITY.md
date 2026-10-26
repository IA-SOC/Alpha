# Security policy

This is a university prototype of an AI assistant for SOC analysts. It isn't deployed anywhere and it only works with synthetic data.

## Reporting a vulnerability

Please don't open a public issue. Use **Report a vulnerability** under the Security tab of this repo, which opens a private advisory that only the maintainers can see.

Tell us what you found, how to reproduce it and what an attacker could do with it. We'll answer within a week.

## What's in scope

- The intake API and the investigation agent in `soc-ai-analyst-sprint2/`
- The web frontend, once it lands
- The CI workflows in `.github/`

## Data

Every case, alert and indicator in this repo is synthetic. If you ever spot real customer data, a real credential or a real internal hostname, report it the same way so we can remove it and rewrite history if needed.
