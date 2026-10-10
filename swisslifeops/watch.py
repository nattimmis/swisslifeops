"""
IncaMail / RAV Gmail watcher (cheap, local-model, draft-only).

One pass (schedule it with cron / a systemd timer):
  1. Look in your mailbox over IMAP for NEW Swiss Post IncaMail notifications
     (from swisspost@im.post.ch) you have not handled yet.
  2. Open each one with the standalone IncaMail opener (it fetches its own verification link over
     IMAP), downloading the decrypted message + attachments locally.
  3. Classify it with a LOCAL model (Ollama) - type, deadline, whether it needs a signature or reply,
     and which of your configured documents would be the correct attachment(s).
  4. Write an "action card" + a NEEDS-YOU line and (optionally) a draft reply.

It never sends, signs, or submits anything. Replying to an authority is the one irreversible step and
it is always left for you to approve. The expensive LLM work runs on your own box, so this costs ~no
API tokens to run continuously.
"""
from __future__ import annotations
import os, re, json, time, imaplib, email, pathlib, datetime, urllib.request
from . import incamail

STATE = incamail.STATE.parent
QUEUE = STATE / "queue"
SEEN_FILE = STATE / "watch_seen.json"
NEEDS_YOU = STATE / "NEEDS-YOU.md"
READ_URL_RE = re.compile(r"https://app\.incamail\.com/Login\?sec=[^\s\"'<>]+#token=[^\s\"'<>]+")

CLASSIFY_PROMPT = """You are triaging a secured letter from a Swiss authority. Return STRICT JSON only.
Fields:
  type: one of ["info","needs_signature","needs_reply","deadline","payment","other"]
  sender: short string
  subject: short string
  deadline: ISO date or "" if none
  needs_signature: true/false
  needs_reply: true/false
  summary: one sentence, plain English
  suggested_docs: array of document KEYS (from this allowed list, may be empty): {doc_keys}
Message:
---
{body}
---
JSON:"""


def _load_seen() -> set:
    try:
        return set(json.loads(SEEN_FILE.read_text()))
    except Exception:
        return set()


def _save_seen(seen: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def _imap_notifications(imap_cfg: dict):
    host = imap_cfg["host"]; user = imap_cfg["user"]
    pw = os.environ.get(imap_cfg.get("password_env", "SWISSLIFEOPS_IMAP_PASSWORD"), "")
    if not pw:
        raise RuntimeError("IMAP password env var empty")
    M = imaplib.IMAP4_SSL(host); M.login(user, pw); M.select(imap_cfg.get("mailbox", "INBOX"))
    typ, data = M.search(None, '(FROM "swisspost@im.post.ch")')
    ids = data[0].split() if data and data[0] else []
    out = []
    for mid in reversed(ids[-40:]):
        typ, md = M.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(md[0][1])
        key = msg.get("Message-ID") or mid.decode()
        body = incamail._email_text(msg)
        m = READ_URL_RE.search(body)
        out.append({"key": key, "subject": msg.get("Subject", ""), "read_url": m.group(0) if m else None})
    M.logout()
    return out


def classify(body: str, doc_keys: list[str], ollama: dict) -> dict:
    base = ollama.get("base_url", "http://localhost:11434")
    model = ollama.get("model", "qwen2.5:7b")
    prompt = CLASSIFY_PROMPT.format(doc_keys=json.dumps(doc_keys), body=body[:4000])
    req = urllib.request.Request(
        f"{base}/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False,
                         "format": "json", "options": {"temperature": 0}}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())["response"]
        card = json.loads(resp)
    except Exception as e:
        card = {"type": "other", "summary": f"(local classification failed: {e}) - review manually",
                "needs_signature": False, "needs_reply": True, "deadline": "", "suggested_docs": []}
    return card


def run_once(cfg: dict) -> list[dict]:
    ic = cfg.get("incamail", {})
    wc = cfg.get("watch", {})
    email_addr = ic.get("email") or os.environ.get("SWISSLIFEOPS_EMAIL", "")
    imap_cfg = ic.get("imap")
    if not (email_addr and imap_cfg):
        raise RuntimeError("watch needs incamail.email and incamail.imap in config")
    dossier = wc.get("dossier", {})           # {doc_key: path}
    ollama = wc.get("ollama", {})
    QUEUE.mkdir(parents=True, exist_ok=True)
    seen = _load_seen()
    cards = []
    for note in _imap_notifications(imap_cfg):
        if note["key"] in seen:
            continue
        print(f"[watch] new secured mail: {note['subject']!r}")
        if not note["read_url"]:
            seen.add(note["key"]); continue
        res = incamail.open_link(note["read_url"], email_addr, strategy="imap",
                                 imap_cfg=imap_cfg, verify_wait=wc.get("verify_wait", 300))
        body = ""
        try:
            body = (pathlib.Path(res["dir"]) / "body.txt").read_text()
        except Exception:
            pass
        card = classify(body, list(dossier.keys()), ollama)
        card.update({"key": note["key"], "dir": res.get("dir"),
                     "downloaded": res.get("attachments", []),
                     "suggested_attachment_paths": [dossier[k] for k in card.get("suggested_docs", []) if k in dossier],
                     "opened_at": datetime.datetime.now().isoformat(timespec="seconds")})
        (QUEUE / f"{abs(hash(note['key']))}.json").write_text(json.dumps(card, indent=2))
        _append_needs_you(card)
        cards.append(card)
        seen.add(note["key"])
    _save_seen(seen)
    print(f"[watch] processed {len(cards)} new message(s)")
    return cards


def _append_needs_you(card: dict):
    NEEDS_YOU.parent.mkdir(parents=True, exist_ok=True)
    line = (f"- [{'ACTION' if card.get('needs_reply') or card.get('needs_signature') else 'info'}] "
            f"{card.get('subject','?')} — {card.get('summary','')}"
            f"{' (deadline ' + card['deadline'] + ')' if card.get('deadline') else ''}"
            f"{' — attach: ' + ', '.join(card['suggested_attachment_paths']) if card.get('suggested_attachment_paths') else ''}\n")
    with open(NEEDS_YOU, "a") as f:
        f.write(line)
