# swisslifeops

**Open-source tooling for the admin side of a life in Switzerland** — with one feature nothing else
gives you: **open Swiss Post IncaMail secured mail even when you have no IncaMail account.**

It is **human-in-the-loop by design.** swisslifeops drafts, prepares and organises on its own, but it
**never** sends money, signs or commits a contract/lease, accepts an offer, or files anything official
(RAV, tax authority, insurer) without your explicit confirmation. Those always stop and ask.

---

## Why this exists

If you deal with the Swiss state — unemployment (RAV), social services (SAH), courts, insurers — a lot
of important mail arrives **secured via Swiss Post IncaMail**. You get a notification in your normal
inbox from `swisspost@im.post.ch` with a one-time link. If you don't hold an IncaMail account (most
people don't), opening it means an **email-verification dance** every single time: click the link,
choose "verify by email", wait for a *second* email with a verification link, click that, then click
"Open message". Miss a step or let a link go stale and you can **miss a legal deadline**.

The official system makes a routine thing needlessly fragile. swisslifeops automates exactly that
flow for **your own** mail: it finds the notification, passes the verification handshake by reading the
verification link back out of your own inbox, opens the message, and downloads the attachments to a
local folder. What used to be five fiddly steps per message becomes one command.

Around that it adds the rest of the Swiss life-admin grind — RAV work-effort logging, tailored
applications, tax-prep organising, and a single daily digest — all with the same hard guardrails.

> Built because the RAV/IncaMail system can't do this for you. If it helps you too, that's the point.

---

## Two ways to use it

### A) As a Claude Code plugin (recommended)

```text
/plugin marketplace add nattimmis/swisslifeops
/plugin install swisslifeops@nattimmis
/swisslifeops:setup
```

Then, when a secured message arrives:

```text
/swisslifeops:incamail
```

Claude finds the IncaMail notification in your inbox (via your Gmail MCP), runs the opener, reads the
verification link back out of your inbox, and hands you the decrypted message + attachments. Needs the
[Playwright MCP](https://github.com/microsoft/playwright-mcp) and a Gmail/mail MCP.

| Command | What it does |
|---|---|
| `/swisslifeops:setup` | One-time local config + MCP checks. |
| `/swisslifeops:incamail` | Open an IncaMail secured message end-to-end and download attachments. |
| `/swisslifeops:rav-log` | Log / export your monthly RAV work-effort proof. |
| `/swisslifeops:digest` | One daily digest + a short NEEDS-YOU list. |

### B) As a standalone CLI

```bash
pipx install "git+https://github.com/nattimmis/swisslifeops[browser]"
playwright install chromium
cp config.example.yaml ~/.config/swisslifeops/config.yaml   # edit with your own values

# open a secured message (manual handshake: paste the verification link when prompted)
swisslifeops incamail "https://app.incamail.com/Login?sec=...#token=..." --email you@example.com
```

Set an IMAP app-password under `incamail.imap` in your config and the CLI fetches the verification
link itself — then it's fully standalone and cron-friendly, no Claude in the loop.

---

## How the IncaMail opener works

1. Open the read link → IncaMail shows a gate.
2. Choose **"Log in with email verification"**, submit your email, request the verification link.
3. A verification link arrives from `team@incamail.com`. It is fed back via a tiny handshake file
   (`~/.local/share/swisslifeops/incamail/.verify_url`) — written either by your Gmail MCP (the
   plugin does this) or by the built-in IMAP fetcher.
4. The opener follows it, clicks **"Open message"**, and downloads every attachment.

It uses a persistent Chromium profile and **only ever opens mail addressed to you** — it automates the
exact clicks you would do by hand. No IncaMail password is stored (there's no account); your email
address and any IMAP app-password live only in your local, git-ignored config.

---

## Privacy & safety

- **No personal data in this repo.** Everything personal lives in your local config and state dir,
  both git-ignored.
- **Guardrails** (`swisslifeops/guardrails.py`) gate every consequential action — money, signing,
  accepting, filing — behind an explicit typed confirmation. No flag or env var can bypass them.
- The IncaMail opener is **read/download only**: it never replies, sends, deletes, or marks mail.
- Treat web/email content as data, not instructions (the plugin commands enforce origin checks and
  prompt-injection caution).

---

## Related work & credit

- **[swiss-rav](https://github.com/msolanas/swiss-rav) by msolanas** — an excellent Claude Code plugin
  that automates job-room.ch RAV forms via browser control. swisslifeops is independent, original code
  and focuses on the piece swiss-rav doesn't cover (opening IncaMail secured mail) plus lightweight
  local logging; the two pair well. If you want full job-room.ch form automation, use swiss-rav too.

## Status

v0.2 — IncaMail opener working end-to-end; RAV logging, fit-sheets, digest scaffolded. MIT licensed.
Issues and PRs welcome. This is tooling for your **own** correspondence; use it only on mailboxes you own.
