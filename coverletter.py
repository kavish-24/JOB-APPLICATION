"""Brief cover letters: the LOCAL model (LLM_ENDPOINT) writes the body, the rest
(greeting, sign-off, name, contact line) is filled in here, then it is rendered
to a one-page PDF.

The model only sees the resume's own text, the JD, title and company, and is
told to use only facts from the resume.
"""
import json
import os
import re
import urllib.request
from datetime import date
from pathlib import Path

import pymupdf

from analyze import load_env

MAX_WORDS = 230
MIN_WORDS = 40

PROMPT = """You are writing the body of a brief cover letter for an entry-level job application.

Rules:
- 3 short paragraphs, 150-220 words in total, plain text, no bullet points.
- Paragraph 1: the role and company, and one line on why this candidate fits.
- Paragraph 2: two or three concrete things from the RESUME that match the JOB (projects, internships, skills). Use ONLY facts written in the resume. Never invent employers, numbers, degrees or skills.
- Paragraph 3: a short, confident close asking for an interview.
- Do NOT write a greeting ("Dear ...") or a sign-off ("Sincerely ..."), and no placeholders like [Company].
- Sound like a real fresher: simple, specific, no clichés like "I am writing to express my interest".

JOB TITLE: {title}
COMPANY: {company}
KEY SKILLS FOR THIS JOB: {skills}

JOB DESCRIPTION:
{jd}

RESUME:
{resume}

Cover letter body:
"""


class LetterError(RuntimeError):
    pass


def _ask_local(prompt: str) -> str:
    load_env()
    endpoint = os.getenv("LLM_ENDPOINT")
    if not endpoint:
        raise LetterError("LLM_ENDPOINT is not set in .env (the local model writes cover letters)")
    req = urllib.request.Request(
        endpoint, data=json.dumps({"question": prompt}).encode(),
        headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.getenv("LLM_TIMEOUT", "120"))) as r:
            return str(json.load(r).get("answer", ""))
    except Exception as e:
        raise LetterError(f"Local model is not reachable ({type(e).__name__}: {e}). "
                          "Is the LLM_ENDPOINT tunnel running?")


_GREETING = re.compile(r"^\s*(dear|hello|hi|to whom)\b[^\n]*\n+", re.I)
_SIGNOFF = re.compile(r"\n\s*(sincerely|best regards|regards|kind regards|thank you,|yours)\b.*$",
                      re.I | re.S)
_PREAMBLE = re.compile(r"^\s*(here is|here's|sure|certainly)[^\n]*\n+", re.I)


def _fill(m: re.Match, values: dict) -> str:
    key = re.sub(r"[^a-z]", "", m.group(1).lower())
    for words, val in values.items():
        if val and any(w in key for w in words):
            return val
    return ""


def clean_body(answer: str, company: str = "", title: str = "", name: str = "") -> str:
    """Strip greeting / sign-off / chatter a small model may add, fill known
    [placeholders], cap length."""
    t = answer.replace("\r", "").strip()
    t = t.split("Cover letter body:")[-1]
    t = _PREAMBLE.sub("", t)
    t = _GREETING.sub("", t)
    t = _SIGNOFF.sub("", t)
    values = {("company", "organisation", "organization", "employer"): company.strip(),
              ("title", "position", "role", "job"): title.strip(),
              ("yourname", "name", "candidate"): name.strip()}
    t = re.sub(r"\[([^\]]{1,40})\]", lambda m: _fill(m, values), t)
    t = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", t))   # tidy what was removed
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    if len(paras) == 1:                             # one blob: split into ~3 paragraphs
        sents = re.split(r"(?<=[.!?])\s+", paras[0])
        n = max(1, round(len(sents) / 3))
        paras = [" ".join(sents[i:i + n]) for i in range(0, len(sents), n)]
    out, words = [], 0
    for p in paras:
        w = len(p.split())
        if words + w > MAX_WORDS:                   # cut at a sentence boundary
            keep = []
            for s in re.split(r"(?<=[.!?])\s+", p):
                if words + len(s.split()) > MAX_WORDS:
                    break
                keep.append(s)
                words += len(s.split())
            if keep:
                out.append(" ".join(keep))
            break
        out.append(p)
        words += w
    return "\n\n".join(out)


def compose_text(body: str, name: str, company: str) -> str:
    greet = f"Dear Hiring Team at {company.strip()}," if company.strip() else "Dear Hiring Manager,"
    sign = f"Sincerely,\n{name}" if name else "Sincerely,"
    return f"{greet}\n\n{body}\n\n{sign}"


def write(resume_text: str, header: dict, title: str, company: str, jd: str,
          skills: list[str]) -> dict:
    prompt = PROMPT.format(title=title.strip(), company=company.strip() or "the company",
                           skills=", ".join(skills[:15]) or "see job description",
                           jd=jd.strip()[:2500], resume=resume_text.strip()[:3500])
    body = clean_body(_ask_local(prompt), company, title, header.get("name", ""))
    if len(body.split()) < MIN_WORDS:
        raise LetterError("The local model returned too little text for a cover letter; try again")
    return {"text": compose_text(body, header.get("name", ""), company),
            "name": header.get("name", ""), "contact": header.get("contact", "")}


def render_pdf(path: Path, text: str, name: str = "", contact: str = "",
               title: str = "", company: str = "") -> None:
    """One-page letter: name + contact header, date, recipient, the text."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    m = 64
    y = m
    if name:
        page.insert_text((m, y + 14), name, fontname="hebo", fontsize=18)
        y += 26
    if contact:
        page.insert_text((m, y + 9), contact, fontname="helv", fontsize=9, color=(0.35, 0.35, 0.35))
        y += 16
    page.draw_line((m, y + 4), (612 - m, y + 4), color=(0.8, 0.8, 0.8), width=0.6)
    y += 24
    meta = [date.today().strftime("%d %B %Y")]
    if company:
        meta += ["", f"Hiring Team, {company}"]
    if title:
        meta += [f"Re: {title}"]
    for line in meta:
        if line:
            page.insert_text((m, y + 10), line, fontname="helv", fontsize=10.5)
        y += 15
    y += 10
    rect = pymupdf.Rect(m, y, 612 - m, 792 - m)
    for size in (11, 10.5, 10, 9.5, 9):           # shrink until it fits one page
        shape = page.new_shape()
        if shape.insert_textbox(rect, text, fontname="helv", fontsize=size, lineheight=1.45) >= 0:
            shape.commit()
            break
    else:
        raise LetterError("Cover letter is too long for one page; shorten it")
    tmp = f"{path}.tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, path)
