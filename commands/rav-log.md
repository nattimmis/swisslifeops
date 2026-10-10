---
name: rav-log
description: "Log a job application to your monthly RAV Arbeitsbemühungen (work-effort) proof, and export the month's list when you need to submit it. Keeps a local JSONL record; never submits to the authorities for you."
---

# /swisslifeops:rav-log — track your monthly work-effort proof

Swiss unemployment requires a monthly proof of job applications (Arbeitsbemühungen / work efforts).
This command keeps that list locally and exports it when you need it. It does **not** submit anything
official — that stays with you.

## Log an application
Ask for (or infer from context): date, company, role, and channel (email / job-room / portal /
recruiter). Then run:

```bash
swisslifeops rav log --date <YYYY-MM-DD> --company "<name>" --role "<title>" --channel "<how>"
```

If the user just applied via another swisslifeops action, offer to log it automatically.

## Export a month
```bash
swisslifeops rav export --month <YYYY-MM>
```
Show the list. Offer to format it as the proof the user's ALK/RAV expects, but let the user do the
actual submission (or hand off to a dedicated RAV browser command). This pairs well with the separate
`swiss-rav` plugin by **msolanas** if the user wants job-room.ch form automation.
