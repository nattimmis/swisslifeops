"""
IncaMail read-link opener (PII-free).

Swiss authorities (RAV, SAH, courts, insurers) routinely send secured mail via Swiss Post
**IncaMail**. Recipients who do NOT have an IncaMail account get a notification in their normal
inbox from ``swisspost@im.post.ch`` with a one-time link:

    https://app.incamail.com/Login?sec=<SERVER_SECRET>&language=en#token=<DECRYPTION_KEY>

Opening it shows a gate. The no-account path is "Log in with email verification": you enter your
address, IncaMail emails a verification **link** (from ``team@incamail.com``), and opening that link
authorises the browser so the message decrypts and its attachments become downloadable.

This module drives that flow with Playwright. It stores **no** personal data: your email address
comes from config/env/CLI, and the verification link is supplied by one of two strategies:

* ``manual``  - the opener requests verification, then waits for the link to appear in a small
  handshake file (``~/.local/share/swisslifeops/incamail/.verify_url``). Whatever has access to your
  mailbox (your Gmail MCP in Claude Code, or you pasting it) writes the link there. See the
  ``/incamail`` plugin command for the Claude-driven version.
* ``imap``    - fully standalone: give an IMAP host + an app password and the opener fetches the
  newest ``team@incamail.com`` verification mail itself and extracts the link.

A persistent Chromium profile is reused so the browser keeps your cookies between runs. This tool
only ever opens mail addressed to *you*; it automates the same clicks you would do by hand.
"""
from __future__ import annotations
import os, re, time, html, imaplib, email, pathlib, datetime, hashlib

STATE = pathlib.Path(os.environ.get(
    "SWISSLIFEOPS_STATE",
    os.path.expanduser("~/.local/share/swisslifeops"))) / "incamail"
VERIFY_FILE = STATE / ".verify_url"
VERIFY_RE = re.compile(r"https://app\.incamail\.com/verification#[A-Za-z0-9+/=_-]+")


def _slug(url: str) -> str:
    m = re.search(r"sec=([A-Za-z0-9]+)", url)
    return m.group(1)[:10] if m else hashlib.sha1(url.encode()).hexdigest()[:10]


# ---- verification-link strategies -----------------------------------------
def link_from_file(timeout: int = 240) -> str | None:
    """Wait for an external helper to drop the verification link into VERIFY_FILE."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if VERIFY_FILE.exists():
            t = VERIFY_FILE.read_text().strip()
            if t.startswith("http"):
                return t
        time.sleep(2)
    return None


def link_from_imap(cfg: dict, since_ts: float, timeout: int = 240) -> str | None:
    """Poll an IMAP mailbox for the newest team@incamail.com verification link."""
    host = cfg["host"]
    user = cfg["user"]
    pw = os.environ.get(cfg.get("password_env", "SWISSLIFEOPS_IMAP_PASSWORD"), "")
    mailbox = cfg.get("mailbox", "INBOX")
    if not pw:
        raise RuntimeError("IMAP password env var is empty")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            M = imaplib.IMAP4_SSL(host)
            M.login(user, pw)
            M.select(mailbox)
            typ, data = M.search(None, '(FROM "team@incamail.com" SUBJECT "IncaMail")')
            ids = (data[0].split() if data and data[0] else [])
            for mid in reversed(ids[-8:]):
                typ, msg_data = M.fetch(mid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                body = _email_text(msg)
                m = VERIFY_RE.search(body)
                if m:
                    M.logout()
                    return m.group(0)
            M.logout()
        except Exception as e:
            print(f"  [imap] {e}")
        time.sleep(5)
    return None


def _email_text(msg) -> str:
    out = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/html", "text/plain"):
                try:
                    out.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace"))
                except Exception:
                    pass
    else:
        try:
            out.append(msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace"))
        except Exception:
            pass
    return html.unescape("\n".join(out))


# ---- the browser flow ------------------------------------------------------
def _click_text(page, texts, timeout=4000):
    for t in texts:
        for sel in (f"button:has-text('{t}')", f"a:has-text('{t}')", f"text={t}"):
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click(timeout=timeout)
                    return True
            except Exception:
                pass
    return False


def _dismiss_cookies(page):
    for t in ("Accept all", "Alle akzeptieren", "Accept", "Akzeptieren", "I agree", "OK"):
        if _click_text(page, [t], timeout=3000):
            page.wait_for_timeout(500)
            return


def open_link(url: str, email_address: str, *, strategy: str = "manual",
              imap_cfg: dict | None = None, headful: bool = False,
              verify_wait: int = 240) -> dict:
    """Open one IncaMail read link and download its message + attachments.

    Returns a dict: {dir, attachments:[...], ok:bool}.
    """
    from playwright.sync_api import sync_playwright
    out_dir = STATE / _slug(url)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = str(STATE / "profile")
    if VERIFY_FILE.exists():
        VERIFY_FILE.unlink()
    downloaded: list[str] = []
    started = time.time()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=not headful, accept_downloads=True,
            viewport={"width": 1280, "height": 1000},
            args=["--disable-blink-features=AutomationControlled"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def _save(dl):
            try:
                dest = out_dir / dl.suggested_filename
                if dest.exists():   # dedupe repeat clicks
                    return
                dl.save_as(dest)
                downloaded.append(dl.suggested_filename)
                print(f"  downloaded {dl.suggested_filename}")
            except Exception as e:
                print(f"  download err: {e}")
        ctx.on("download", _save)

        page.set_default_timeout(6000)
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        _dismiss_cookies(page)

        body = _body(page)
        if "verification" in body.lower() and "get verification link" not in body.lower() \
                and "verified successfully" not in body.lower():
            pass  # already a message view (trusted browser)
        else:
            _click_text(page, ["Log in with email verification", "email verification"])
            page.wait_for_timeout(1500)
            for sel in ("input[type=email]:visible", "input[name=email]:visible", "input[type=email]"):
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(email_address)
                        break
                except Exception:
                    pass
            _click_text(page, ["Get verification link", "Continue", "Weiter", "Send"])
            page.wait_for_timeout(2500)
            print(f"  verification link requested for {email_address}")

            if strategy == "imap":
                vurl = link_from_imap(imap_cfg or {}, started, verify_wait)
            else:
                print(f"  waiting for verification link in {VERIFY_FILE} (up to {verify_wait}s)")
                vurl = link_from_file(verify_wait)
            if not vurl:
                ctx.close()
                return {"dir": str(out_dir), "attachments": [], "ok": False, "error": "no verification link"}
            page.goto(vurl, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

        # final "Open message" step(s)
        for _ in range(4):
            b = _body(page).lower()
            if "open message" in b or "verified successfully" in b:
                if not _click_text(page, ["Open message", "Nachricht öffnen", "Öffnen"]):
                    break
                page.wait_for_timeout(2500)
                _dismiss_cookies(page)
            else:
                break

        # trigger attachment downloads
        for _ in range(3):
            page.wait_for_timeout(1000)
            for sel in ("button:has-text('Download all')", "a[href*='attachment']", "a[download]",
                        "button:has-text('Download')", "button:has-text('Herunterladen')"):
                try:
                    for el in page.query_selector_all(sel):
                        if el.is_visible():
                            el.click()
                            page.wait_for_timeout(1200)
                except Exception:
                    pass
        try:
            page.screenshot(path=str(out_dir / "message.png"), full_page=True)
            (out_dir / "body.txt").write_text(_body(page)[:9000])
            (out_dir / "url.txt").write_text(url + "\n")
        except Exception:
            pass
        if VERIFY_FILE.exists():
            VERIFY_FILE.unlink()
        ctx.close()
    return {"dir": str(out_dir), "attachments": downloaded, "ok": True}


def _body(page) -> str:
    try:
        return page.inner_text("body")
    except Exception:
        return ""
