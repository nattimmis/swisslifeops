"""Hard guardrails: consequential actions always require explicit confirmation.

The whole point of swisslifeops is that it can draft and prepare autonomously,
but it must never move money, sign, accept, or file anything official on its own.
"""
from __future__ import annotations
import os

# Actions that MUST NOT happen without an explicit human yes.
CONSEQUENTIAL = {
    "send_money",
    "place_paid_order",
    "sign_contract",
    "sign_lease",
    "accept_job_offer",
    "file_tax_submission",
    "submit_official_form",   # RAV, authorities, insurer
}


class BlockedAction(RuntimeError):
    pass


def confirm(action: str, detail: str, *, assume_yes: bool | None = None) -> bool:
    """Return True only if a human explicitly approves a consequential action.

    `assume_yes` is intentionally ignored for CONSEQUENTIAL actions: no flag or
    env var can auto-approve moving money, signing, accepting or filing.
    """
    consequential = action in CONSEQUENTIAL
    if not consequential:
        if assume_yes is None:
            assume_yes = os.environ.get("SWISSLIFEOPS_ASSUME_YES") == "1"
        return bool(assume_yes)

    # Consequential: force an interactive, typed confirmation every time.
    print(f"\n[CONFIRM REQUIRED] {action}: {detail}")
    print("This moves money, signs, accepts, or files something official.")
    try:
        answer = input("Type the action name to approve, anything else to abort: ").strip()
    except EOFError:
        raise BlockedAction(f"{action} aborted (no interactive confirmation available)")
    if answer != action:
        raise BlockedAction(f"{action} not confirmed - aborted")
    return True
