"""Core, PII-free building blocks. Everything reads from your local config;
nothing personal is hard-coded here."""
from __future__ import annotations
import os, html, json, datetime
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

CONFIG_PATHS = [
    Path(os.environ.get("SWISSLIFEOPS_CONFIG", "")),
    Path.home() / ".config" / "swisslifeops" / "config.yaml",
    Path("config.yaml"),
]


def load_config() -> dict:
    for p in CONFIG_PATHS:
        if p and p.is_file():
            if not yaml:
                raise RuntimeError("PyYAML not installed")
            return yaml.safe_load(p.read_text()) or {}
    raise FileNotFoundError(
        "No config found. Copy config.example.yaml to "
        "~/.config/swisslifeops/config.yaml and edit it."
    )


# ---- fit sheet -------------------------------------------------------------
_CSS = ("*{box-sizing:border-box}@page{size:A4;margin:10mm}"
        "body{font-family:Arial,sans-serif;font-size:10.3px;line-height:1.34}"
        ".h{border-bottom:3px solid #0b5;padding-bottom:6px;margin-bottom:8px}"
        "h1{font-size:16px;margin:0}table{width:100%;border-collapse:collapse}"
        "th{background:#0b5;color:#fff;text-align:left;padding:3px 6px}"
        "td{border-bottom:1px solid #e3e3e3;padding:3px 6px;vertical-align:top}"
        "td.n{width:38%;font-weight:bold;color:#0a4}")


def fitsheet_html(cfg: dict, company_key: str) -> str:
    """Render a one-page 'why I fit <company>' sheet from config data only."""
    prof = cfg.get("profile", {})
    emp = cfg.get("employers", {}).get(company_key)
    if not emp:
        raise KeyError(f"employer '{company_key}' not in config.employers")
    rows = "".join(
        f'<tr><td class="n">{html.escape(str(n))}</td><td>{html.escape(str(e))}</td></tr>'
        for n, e in emp.get("needs", [])
    )
    roles = " / ".join(emp.get("roles", []))
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"
            f"<div class='h'><h1>Why I fit {html.escape(emp.get('display_name', company_key))}</h1>"
            f"<div>{html.escape(roles)}</div>"
            f"<div>{html.escape(prof.get('full_name',''))} &middot; {html.escape(prof.get('location',''))} "
            f"&middot; {html.escape(prof.get('cv_url',''))}</div></div>"
            f"<table><tr><th>What you need</th><th>What I bring</th></tr>{rows}</table></body></html>")


def render_pdf(html_path: str, pdf_path: str) -> bool:
    """Render HTML->PDF with headless Chrome if available; else leave the HTML."""
    import shutil, subprocess
    chrome = next((shutil.which(c) for c in
                   ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
                   if shutil.which(c)), None)
    if not chrome:
        return False
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    f"file://{os.path.abspath(html_path)}"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(pdf_path)


# ---- RAV Arbeitsbemuehungen ------------------------------------------------
def _rav_store() -> Path:
    d = Path.home() / ".local" / "share" / "swisslifeops"
    d.mkdir(parents=True, exist_ok=True)
    return d / "rav_log.jsonl"


def rav_log(entry: dict) -> None:
    entry.setdefault("logged_at", datetime.date.today().isoformat())
    with _rav_store().open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rav_export(month: str) -> list[dict]:
    """Return all logged applications for YYYY-MM (for the monthly proof)."""
    p = _rav_store()
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if str(e.get("date", e.get("logged_at", ""))).startswith(month):
            out.append(e)
    return out


# ---- email (draft-only by default) ----------------------------------------
def prepare_email(cfg: dict, to: str, subject: str, body: str, attachments: list[str]):
    """Prepare an email payload and verify attachment files exist on disk.

    Returns a dict describing the draft. Actually sending is the caller's job
    via the user's configured transport; swisslifeops never ships credentials.
    """
    missing = [a for a in attachments if not os.path.isfile(os.path.expanduser(a))]
    if missing:
        raise FileNotFoundError(f"attachments not found: {missing}")
    return {"from": cfg.get("email", {}).get("from"), "to": to, "subject": subject,
            "body": body, "attachments": [os.path.expanduser(a) for a in attachments],
            "transport": cfg.get("email", {}).get("transport", "draft-only")}


# ---- digest ----------------------------------------------------------------
def build_digest(sections: dict[str, list[str]], needs_you: list[str]) -> str:
    today = datetime.date.today().isoformat()
    lines = [f"Life digest {today}", ""]
    for name, items in sections.items():
        lines.append(f"## {name}")
        lines += [f"- {i}" for i in items] or ["- (nothing new)"]
        lines.append("")
    lines.append("## NEEDS YOU")
    lines += [f"- {n}" for n in needs_you] or ["- nothing pending"]
    return "\n".join(lines)
