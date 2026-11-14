"""Scan the base resume PDFs and build the skills knowledge base (JSON).

Every folder in resume/ is one base resume CATEGORY that the user named
(resume/<FOLDER>/<file>.pdf + meta.json {label, uploaded_at}). For each PDF the
skills section is located (pdfedit.detect) and its layout is stored, so the
editor knows exactly which lines to rewrite and how much room each has.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfedit
from pdfedit import split_items  # noqa: F401  (re-exported for old callers)

ROOT = Path(__file__).parent
RESUME_DIR = ROOT / "resume"
KB_PATH = ROOT / "knowledge_base.json"

# The three original folders keep their old route keys and labels, and are the
# owner's own resumes (the personal tiers in skills_db apply to them only).
LEGACY_KEYS = {"AI_ML": "ai", "SDE": "sde", "FULL_STACK": "fullstack"}
LEGACY_LABELS = {"AI_ML": "AI / ML", "SDE": "SDE", "FULL_STACK": "Full Stack"}
META = "meta.json"

# "Tech: React, Node.js" / "Tools used: Jira, Postman" lines outside the skills section
_LIST_LINE = re.compile(r"^([A-Za-z][A-Za-z &/+.-]{1,30}):\s*(.+)$")


def folder_key(folder: Path) -> str:
    return LEGACY_KEYS.get(folder.name, folder.name.lower())


def read_meta(folder: Path) -> dict:
    f = folder / META
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resume_folders() -> list[Path]:
    if not RESUME_DIR.exists():
        return []
    return sorted(p for p in RESUME_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))


def parse_pdf(pdf: Path) -> dict:
    section = pdfedit.detect(pdf)
    body = pdfedit.body_text(pdf, section)
    skills = {e["key"]: e["items"] for e in section["entries"]}

    # skills named outside the skills section on "Label: a, b, c" lines
    extra: dict[str, list[str]] = {}
    for line in body.splitlines():
        m = _LIST_LINE.match(line.strip())
        if m:
            items = split_items(m.group(2))
            if len(items) >= 2 and all(len(i.split()) <= 4 for i in items):
                extra.setdefault(m.group(1).strip(), []).extend(items)

    listed = {s.lower() for v in skills.values() for s in v}
    flat = sorted({s for v in (*skills.values(), *extra.values()) for s in v}, key=str.lower)
    try:
        source = str(pdf.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        source = str(pdf)
    return {
        "source_file": source,
        "category_order": list(skills),
        "skills": skills,
        # where the skills section is and how each line is drawn (for editing)
        "skills_section": section,
        "extra_keywords": {k: [s for s in dict.fromkeys(v) if s.lower() not in listed]
                           for k, v in extra.items()},
        "all_skills": flat,
        "total_skills": len(flat),
        # experience / projects / education text: proves skills outside the list
        "body_text": body,
        # name + contact line from the header (cover letters)
        "header": pdfedit.header_info(pdf),
    }


def build() -> dict:
    kb = {"generated_at": datetime.now(timezone.utc).isoformat(), "variants": {}, "errors": {}}
    for folder in resume_folders():
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            continue
        key, meta = folder_key(folder), read_meta(folder)
        try:
            v = parse_pdf(pdfs[0])
        except pdfedit.SectionNotFound as e:
            kb["errors"][key] = str(e)
            continue
        uploaded = meta.get("uploaded_at") or datetime.fromtimestamp(
            pdfs[0].stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
        v.update({"tag": key, "folder": folder.name,
                  "label": meta.get("label") or LEGACY_LABELS.get(folder.name) or key,
                  "personal": folder.name in LEGACY_KEYS, "uploaded_at": uploaded})
        kb["variants"][key] = v
    KB_PATH.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
    return kb


if __name__ == "__main__":
    kb = build()
    for k, v in kb["variants"].items():
        print(f"{k}: {v['total_skills']} skills in {len(v['skills'])} lines")
    for k, e in kb["errors"].items():
        print(f"{k}: SKIPPED - {e}")
    print(f"Saved -> {KB_PATH}")
