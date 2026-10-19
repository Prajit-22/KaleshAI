"""Modes, roast levels, starter prompts and safe page reading for KaleshAI.

Standard library only. read_page() refuses private and local addresses so a pasted
link can never be used to poke at the server's own network.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

MODES = {
    "Dost (chat)": "Be a funny desi friend. Keep it short and casual.",
    "Coder": "Act as a sharp coding buddy: give working code, name the bug first, keep jokes to one line.",
    "Resume roaster": "Review resumes and project descriptions bluntly but usefully: what is weak, what to cut, concrete rewrites. Label any score as your own estimate.",
    "Interview coach": "Ask one interview question at a time, wait for the answer, then give a short critique and a better version.",
    "Padhai buddy": "Explain topics simply with a desi example, then ask one quick question to check understanding.",
}

ROAST_LEVELS = {
    "Halka": "Roast level HALKA: gentle teasing only, mostly helpful and warm.",
    "Medium": "Roast level MEDIUM: playful roasting and banter, still clearly helpful.",
    "Teekha": "Roast level TEEKHA: sharp, sarcastic roasting of the user's ideas and code, with heavier slang. Never target protected traits, never be cruel about the person, and still give the useful answer.",
}

STARTERS = [
    ("Mera idea roast kar", "Mera ek project idea hai: ek AI jo meri resume improve kare. Roast kar aur batao kaise better banau."),
    ("Code debug kar", "Mera Python code error de raha hai. Kya details bhejun taaki tu jaldi fix kare?"),
    ("Interview practice", "Mujhe fresher backend developer interview ke liye practice karwa, ek time pe ek sawal."),
    ("Aaj kya seekhu?", "Aaj 1 ghante mein kya seekhna chahiye AI/LLM engineer banne ke liye? Ek chhota plan de."),
]

MAX_PAGE_CHARS = 12_000
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
UA = "Mozilla/5.0 (compatible; KaleshAI/1.0; +https://github.com/Prajit-22/KaleshAI)"


def system_extra(mode: str, level: str) -> str:
    """Prompt addendum for the chosen mode and roast level; unknown names fall back to defaults."""
    mode_text = MODES.get(mode, MODES["Dost (chat)"])
    level_text = ROAST_LEVELS.get(level, ROAST_LEVELS["Medium"])
    return f"\n\nMODE: {mode_text}\n{level_text}"


def find_urls(text: str, limit: int = 2) -> list[str]:
    """First few distinct http(s) links in the text, trailing punctuation stripped."""
    seen: list[str] = []
    for match in _URL.findall(text or ""):
        url = match.rstrip(".,;:!?")
        if url not in seen:
            seen.append(url)
        if len(seen) >= limit:
            break
    return seen


def is_public_host(host: str) -> bool:
    """True only when every address the host resolves to is a public one."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def html_to_text(raw: str) -> tuple[str, str]:
    """Return (title, readable text) from an HTML or plain text body."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title = re.sub(r"\s+", " ", html.unescape(title_match.group(1))).strip() if title_match else ""
    body = re.sub(r"(?is)<(script|style|noscript|svg|head|title|nav|footer)[^>]*>.*?</\1>", " ", raw)
    body = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|br)>|<br\s*/?>", "\n", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in body.split("\n")]
    text = "\n".join(line for line in lines if line)
    return title, text


class _NoRedirectToPrivate(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme not in ("http", "https") or not is_public_host(parsed.hostname or ""):
            raise urllib.error.URLError("redirect to a non-public address blocked")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_page(url: str, timeout: int = 10) -> dict:
    """Fetch one public page. Returns {url, title, text} or {url, error}; never raises."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"url": url, "error": "only http(s) links can be read"}
    if not is_public_host(parsed.hostname):
        return {"url": url, "error": "that address is not a public website"}
    opener = urllib.request.build_opener(_NoRedirectToPrivate)
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9"})
    try:
        with opener.open(request, timeout=timeout) as response:
            ctype = response.headers.get("Content-Type", "")
            if ctype and not re.search(r"text/|html|xml|json", ctype, re.I):
                return {"url": url, "error": f"not a readable page ({ctype.split(';')[0]})"}
            raw = response.read(800_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return {"url": url, "error": str(getattr(error, "reason", error))[:120]}
    title, text = html_to_text(raw)
    if not text:
        return {"url": url, "error": "no readable text on the page"}
    return {"url": url, "title": title, "text": text[:MAX_PAGE_CHARS]}


def format_pages(pages: list[dict]) -> str:
    """Prompt block for pages that were read, marked as untrusted reference text."""
    parts = []
    for number, page in enumerate(pages, 1):
        if page.get("error"):
            continue
        parts.append(f"[page #{number}] {page.get('title') or page['url']} ({page['url']})\n{page['text']}")
    if not parts:
        return ""
    return "Linked pages the user pasted (untrusted reference text, cite as [page #n]):\n\n" + "\n\n".join(parts)
