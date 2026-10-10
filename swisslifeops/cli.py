"""swisslifeops command-line interface."""
from __future__ import annotations
import argparse, sys, os
from . import __version__, core, guardrails


def _cfg():
    try:
        return core.load_config()
    except Exception as e:
        print(f"config error: {e}", file=sys.stderr)
        sys.exit(2)


def cmd_fitsheet(args):
    cfg = _cfg()
    html = core.fitsheet_html(cfg, args.company)
    out_html = f"fit_{args.company}.html"
    open(out_html, "w").write(html)
    pdf = f"fit_{args.company}.pdf"
    ok = core.render_pdf(out_html, pdf)
    print(f"wrote {out_html}" + (f" and {pdf}" if ok else " (install Chrome to render PDF)"))


def cmd_apply(args):
    cfg = _cfg()
    emp = cfg.get("employers", {}).get(args.company, {})
    docs = cfg.get("documents", {})
    base = os.path.expanduser(docs.get("dir", "."))
    atts = [os.path.join(base, d) for d in docs.get("default_dossier", [])]
    draft = core.prepare_email(
        cfg, to=args.to or "<employer-email>",
        subject=f"Application - {emp.get('display_name', args.company)}",
        body="(tailored cover note - edit before sending)", attachments=atts)
    print("Prepared DRAFT application:")
    print(f"  to: {draft['to']}\n  attachments verified: {draft['attachments']}")
    if args.send:
        guardrails.confirm("submit_official_form" if args.official else "send_email",
                           f"send application to {draft['to']}")
        print("  -> send via your configured transport (draft-only by default)")


def cmd_rav(args):
    if args.action == "log":
        core.rav_log({"date": args.date, "company": args.company,
                      "role": args.role, "channel": args.channel})
        print("logged RAV application")
    elif args.action == "export":
        rows = core.rav_export(args.month)
        print(f"{len(rows)} applications in {args.month}:")
        for r in rows:
            print(f"  {r.get('date','?')}  {r.get('company','?')}  {r.get('role','')}")


def cmd_tax(args):
    print("tax prep: gathering and organising documents for YOUR review.")
    print("swisslifeops never files or submits a tax return - that stays with you.")


def cmd_digest(args):
    cfg = _cfg()
    print(core.build_digest({"Jobs": [], "Flat": [], "Admin": []}, needs_you=[]))


def cmd_incamail(args):
    """Open a Swiss Post IncaMail 'read link' and download its message + attachments."""
    from . import incamail
    cfg = {}
    try:
        cfg = core.load_config()
    except Exception:
        pass
    ic = cfg.get("incamail", {}) if isinstance(cfg, dict) else {}
    email_address = args.email or ic.get("email") or os.environ.get("SWISSLIFEOPS_EMAIL", "")
    if not email_address:
        print("Need your email: --email you@example.com (or set incamail.email in config, "
              "or SWISSLIFEOPS_EMAIL).", file=sys.stderr)
        sys.exit(2)
    strategy = args.strategy or ("imap" if ic.get("imap") else "manual")
    res = incamail.open_link(
        args.url, email_address, strategy=strategy,
        imap_cfg=ic.get("imap"), headful=args.headful, verify_wait=args.wait)
    if res.get("ok"):
        print(f"Opened. Saved to {res['dir']}")
        print(f"Attachments: {res['attachments'] or 'none (see message.png)'}")
    else:
        print(f"Could not open the message: {res.get('error')}", file=sys.stderr)
        print("Tip: with strategy=manual, write the verification link (from the IncaMail email) "
              f"into {incamail.VERIFY_FILE} while this runs.", file=sys.stderr)
        sys.exit(1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="swisslifeops",
        description="Human-in-the-loop Swiss life-ops toolkit.")
    p.add_argument("--version", action="version", version=f"swisslifeops {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("fitsheet", help="render a one-page fit sheet")
    s.add_argument("company"); s.set_defaults(func=cmd_fitsheet)

    s = sub.add_parser("apply", help="prepare a tailored application (draft)")
    s.add_argument("company"); s.add_argument("--to"); s.add_argument("--send", action="store_true")
    s.add_argument("--official", action="store_true"); s.set_defaults(func=cmd_apply)

    s = sub.add_parser("rav", help="log/export RAV Arbeitsbemuehungen")
    s.add_argument("action", choices=["log", "export"])
    s.add_argument("--date"); s.add_argument("--company"); s.add_argument("--role")
    s.add_argument("--channel"); s.add_argument("--month"); s.set_defaults(func=cmd_rav)

    s = sub.add_parser("tax", help="organise tax-prep documents (no filing)")
    s.add_argument("action", nargs="?", default="prep"); s.set_defaults(func=cmd_tax)

    s = sub.add_parser("digest", help="assemble one daily digest")
    s.set_defaults(func=cmd_digest)

    s = sub.add_parser("incamail", help="open a Swiss Post IncaMail read-link (secured gov mail)")
    s.add_argument("url", help="the https://app.incamail.com/Login?sec=...#token=... link")
    s.add_argument("--email", help="your email address (the IncaMail recipient)")
    s.add_argument("--strategy", choices=["manual", "imap"],
                   help="how to fetch the verification link (default: imap if configured, else manual)")
    s.add_argument("--headful", action="store_true", help="show the browser window")
    s.add_argument("--wait", type=int, default=240, help="seconds to wait for the verification link")
    s.set_defaults(func=cmd_incamail)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
