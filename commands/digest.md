---
name: digest
description: "Assemble one daily life-admin digest: new secured mail to open, job replies and applications to send, RAV deadlines, and a short NEEDS-YOU list of the few decisions only you can make. Reads your inbox read-only and prepares drafts; sends nothing on its own."
---

# /swisslifeops:digest — one daily digest, one NEEDS-YOU list

Pull the day's Swiss life-admin into a single summary so nothing slips.

## Gather (read-only)
- **Secured mail:** search Gmail for `from:im.post.ch newer_than:2d`; list any IncaMail notifications
  not yet opened. Offer to open them with `/swisslifeops:incamail`.
- **Jobs:** recruiter replies awaiting an answer; applications queued to send; interviews to confirm.
- **RAV:** how many work efforts are logged this month vs. the target; the next deadline.
- **Admin/flat/other:** anything time-sensitive the user tracks.

## Prepare, don't commit
Draft replies and applications (attach the real document files, verify them), but leave them as
drafts. Then print a short **NEEDS YOU** list: only the items that genuinely need a human decision
(accepting an offer, signing, paying, submitting something official). Everything on that list is a
hard stop — swisslifeops never does those for the user.

## Output
A compact digest with sections (Secured mail / Jobs / RAV / Admin) and the NEEDS-YOU list at the top.
