---
name: setup
description: "One-time setup for swisslifeops. Writes a local config (your email, document paths, preferences) to ~/.config/swisslifeops/config.yaml, checks for the Playwright MCP and a Gmail MCP, and confirms the swisslifeops CLI is installed. No personal data leaves your machine."
---

# /swisslifeops:setup — first-time configuration

Run once. Sets up swisslifeops for your situation. Nothing personal is uploaded anywhere; it all
lives in a local, git-ignored config.

## Step 1 — check the CLI
Run `swisslifeops --version`. If missing:
`pipx install "git+https://github.com/nattimmis/swisslifeops"` (add the `browser` extra and
`playwright install chromium` for the IncaMail opener).

## Step 2 — collect preferences (ask ONE at a time)
1. Email address (your IncaMail recipient address)
2. Full name (for fit sheets / cover notes)
3. Postcode + city
4. Folder holding your documents (CV, references)
5. Default dossier filenames to attach (e.g. `cv.pdf`, `reference_letters.pdf`)

## Step 3 — write config
Create `~/.config/swisslifeops/config.yaml` from `config.example.yaml`, filling in the answers.
Remind the user it is git-ignored and local-only.

## Step 4 — check MCPs
- Playwright MCP present? (needed for IncaMail + any browser automation)
- A Gmail/mail MCP present? (needed so `/swisslifeops:incamail` can read notifications + verification
  links). If either is missing, give the user the one-line install and continue.

## Step 5 — summary
List what is ready and what still needs the user (e.g. "install Playwright MCP", "fill document
paths"). End with the available commands: `/swisslifeops:incamail`, `/swisslifeops:rav-log`,
`/swisslifeops:digest`.
