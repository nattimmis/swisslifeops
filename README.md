# swisslifeops

A small, honest toolkit for running the admin side of a life in Switzerland:
job search, RAV reporting, applications, email triage, tax-prep organisation,
and a single daily digest.

It is **human-in-the-loop by design**. swisslifeops will happily *draft, prepare
and organise* on its own, but it will **never** do any of the following without
your explicit confirmation:

- send money or place a paid order,
- sign or commit to a lease or contract,
- accept a job offer,
- file or submit anything official (RAV, tax authority, insurer).

An assistant that silently mis-files an RAV form or a tax return can cost you
real money or benefits. So those actions always stop and ask.

## Install

```bash
pipx install git+https://github.com/nattimmis/swisslifeops
swisslifeops --help
```

## Configure

```bash
cp config.example.yaml ~/.config/swisslifeops/config.yaml
# edit it: your own paths, addresses and preferences
```

Nothing personal is stored in this repository. Your config, documents and any
credentials live on your machine and are git-ignored.

## Commands

| Command | What it does |
|---------|--------------|
| `swisslifeops triage` | Summarise an inbox export into action / draft / ignore buckets. |
| `swisslifeops fitsheet <company>` | Render a one-page "why I fit" sheet (HTML/PDF) from your config. |
| `swisslifeops apply <company>` | Prepare a tailored application (cover note + dossier) as a **draft**. |
| `swisslifeops rav log` / `rav export <month>` | Track and export the monthly Arbeitsbemühungen proof. |
| `swisslifeops tax prep` | Gather and organise tax documents into a reviewable folder (no filing). |
| `swisslifeops digest` | Assemble one daily digest of jobs, flat, admin and a NEEDS-YOU list. |

Add `--send` to actually send a prepared draft; consequential actions will still
prompt for confirmation.

## Design notes

- **Attachments** are read from local paths and verified after sending (the
  common failure mode is a broken CV *link*; always attach the real file).
- **Guardrails** live in `swisslifeops/guardrails.py` and gate every consequential
  action behind an explicit confirmation.
- **Private model (optional, roadmap):** you can fine-tune a local model on your
  own hardware to power drafting offline and for free. Any model trained on your
  personal data stays private and is never shipped in this package.

## Status

v0.1 - working scaffolding of the pieces above. MIT licensed. Contributions welcome.
