"""Scan resume PDFs and build a categorised skills knowledge base (JSON)."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

ROOT = Path(__file__).parent
RESUME_DIR = ROOT / "resume"
KB_PATH = ROOT / "knowledge_base.json"

# folder name -> API route key
VARIANTS = {"AI_ML": "ai", "SDE": "sde", "FULL_STACK": "fullstack"}

SECTION_HEADS = ["SUMMARY", "TECHNICAL SKILLS", "EXPERIENCE", "PROJECTS",
                 "EDUCATION", "ACHIEVEMENTS & CERTIFICATIONS"]


def split_items(text: str) -> list[str]:
    """Split on commas that are not inside parentheses."""
    items, depth, cur = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    items.append(cur.strip())
    return [i for i in items if i]


def sections(text: str) -> dict[str, str]:
    """Cut the resume text into its headed sections."""
    pat = r"^(%s)\s*$" % "|".join(re.escape(h) for h in SECTION_HEADS)
    parts = re.split(pat, text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def line_layout(doc, categories: list[str]) -> dict:
    """Measure each skills line in the PDF and how many more characters would
    still fit on one printed line (right edge = widest body line)."""
    lines = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for ln in block.get("lines", []):
                t = "".join(s["text"] for s in ln["spans"]).strip()
                if t:
                    lines.append((t, ln["bbox"][0], ln["bbox"][2]))
    right = max((x1 for t, _, x1 in lines if len(t) > 100), default=0)
    out = {}
    for t, x0, x1 in lines:
        for cat in categories:
            if t.startswith(cat + ":") and cat not in out:
                per_char = (x1 - x0) / len(t)
                spare = int((right - x1) / per_char) - 2  # 2-char safety margin
                out[cat] = {"chars": len(t), "max_chars": len(t) + max(spare, 0)}
    return out


def parse_pdf(pdf: Path) -> dict:
    doc = pymupdf.open(pdf)
    text = "".join(p.get_text() for p in doc)
    secs = sections(text)

    categories: dict[str, list[str]] = {}
    for line in secs.get("TECHNICAL SKILLS", "").splitlines():
        if ":" in line:
            cat, rest = line.split(":", 1)
            categories[cat.strip()] = split_items(rest)

    # Skills mentioned outside the skills section (project "Tech:" lines,
    # "AI & Generative AI: ..." line under certifications).
    extra: dict[str, list[str]] = {}
    for m in re.finditer(r"^Tech:\s*(.+)$", secs.get("PROJECTS", ""), flags=re.M):
        extra.setdefault("Project Tech Stack", []).extend(split_items(m.group(1)))
    for line in secs.get("ACHIEVEMENTS & CERTIFICATIONS", "").splitlines():
        m = re.match(r"^(AI & Generative AI|[A-Za-z &/]+):\s*(.+)$", line)
        if m:
            extra.setdefault(m.group(1), []).extend(split_items(m.group(2)))

    listed = {s.lower() for v in categories.values() for s in v}
    flat = sorted({s for v in (*categories.values(), *extra.values()) for s in v},
                  key=str.lower)
    return {
        "source_file": str(pdf.relative_to(ROOT)).replace("\\", "/"),
        "category_order": list(categories),
        "skills": categories,
        "layout": line_layout(doc, list(categories)),
        "extra_keywords": {k: [s for s in dict.fromkeys(v) if s.lower() not in listed or k == "Project Tech Stack"]
                           for k, v in extra.items()},
        "all_skills": flat,
        "total_skills": len(flat),
    }


def build() -> dict:
    kb = {"generated_at": datetime.now(timezone.utc).isoformat(), "variants": {}}
    for folder, key in VARIANTS.items():
        pdfs = sorted((RESUME_DIR / folder).glob("*.pdf"))
        if pdfs:
            kb["variants"][key] = parse_pdf(pdfs[0])
    KB_PATH.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
    return kb


if __name__ == "__main__":
    kb = build()
    for k, v in kb["variants"].items():
        print(f"{k}: {v['total_skills']} skills in {len(v['skills'])} categories")
    print(f"Saved -> {KB_PATH}")
