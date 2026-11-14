"""Base resume store: upload / replace / rename / delete the PDFs in resume/.

A base resume lives under a CATEGORY the user names ("SDE", "Test Engineer",
anything). One folder per category: resume/<FOLDER>/<file>.pdf + meta.json
{label, uploaded_at}. On upload the skills section is located and its layout
is stored in the knowledge base, so later edits know which lines to rewrite.

Nothing is ever erased: a replaced PDF moves to resume/<FOLDER>/_previous/, a
deleted category moves to resume/_deleted/.
"""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pdfedit
import scan

RESUME_DIR = scan.RESUME_DIR
MAX_BYTES = 10 * 1024 * 1024


class ResumeError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def category_key(category: str) -> str:
    """'Test Engineer' -> 'test_engineer' (used in URLs and folder names)."""
    name = (category or "").strip()
    if not name or len(name) > 60:
        raise ResumeError("Give the category a name (up to 60 characters)")
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]
    if not key:
        raise ResumeError("The category name needs at least one letter or digit")
    return key


def find_folder(key: str) -> Path | None:
    return next((f for f in scan.resume_folders() if scan.folder_key(f) == key), None)


def _safe_name(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename or "resume").stem).strip("._") or "resume"
    return stem[:60] + ".pdf"


def inspect(pdf: Path) -> dict:
    """Find the skills section; raise ResumeError with a readable reason."""
    try:
        sec = pdfedit.detect(pdf)
    except pdfedit.SectionNotFound as e:
        raise ResumeError(str(e))
    except Exception as e:
        raise ResumeError(f"Could not read the PDF: {type(e).__name__}: {e}")
    if not any(e["items"] for e in sec["entries"]):
        raise ResumeError("Found a skills heading but no skills under it")
    return sec


def _write_meta(folder: Path, meta: dict) -> None:
    (folder / scan.META).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def save(category: str, filename: str, data: bytes) -> dict:
    """Add a base resume under a category, or replace the PDF of an existing
    category (the old PDF is archived)."""
    key = category_key(category)
    if not data.startswith(b"%PDF"):
        raise ResumeError("That file is not a PDF")
    if len(data) > MAX_BYTES:
        raise ResumeError("PDF is larger than 10 MB")

    RESUME_DIR.mkdir(exist_ok=True)
    tmp = RESUME_DIR / f"_upload_{_stamp()}.pdf"
    tmp.write_bytes(data)
    try:
        inspect(tmp)
        folder = find_folder(key) or RESUME_DIR / key.upper()
        folder.mkdir(exist_ok=True)
        old = sorted(folder.glob("*.pdf"))
        if old:
            archive = folder / "_previous"
            archive.mkdir(exist_ok=True)
            for p in old:
                shutil.move(str(p), archive / f"{_stamp()}_{p.name}")
        shutil.move(str(tmp), folder / _safe_name(filename))
    finally:
        tmp.unlink(missing_ok=True)
    meta = scan.read_meta(folder)
    _write_meta(folder, {"label": meta.get("label") or category.strip(), "uploaded_at": _now()})
    scan.build()
    return listing()[key]


def rename(key: str, label: str) -> dict:
    """Change the category's display name (its key/URL stays the same)."""
    folder = find_folder(key)
    if folder is None:
        raise KeyError(key)
    label = (label or "").strip()
    if not label or len(label) > 60:
        raise ResumeError("Give the category a name (up to 60 characters)")
    meta = scan.read_meta(folder)
    kb_v = json.loads(scan.KB_PATH.read_text(encoding="utf-8"))["variants"].get(key, {})
    meta.setdefault("uploaded_at", kb_v.get("uploaded_at", _now()))
    meta["label"] = label
    _write_meta(folder, meta)
    scan.build()
    return listing()[key]


def delete(key: str) -> None:
    """Move the category's folder to resume/_deleted/ (recoverable)."""
    folder = find_folder(key)
    if folder is None:
        raise KeyError(key)
    trash = RESUME_DIR / "_deleted"
    trash.mkdir(exist_ok=True)
    shutil.move(str(folder), trash / f"{folder.name}_{_stamp()}")
    scan.build()


def previous_versions(folder: Path) -> list[str]:
    archive = folder / "_previous"
    return sorted((p.name for p in archive.glob("*.pdf")), reverse=True) if archive.exists() else []


def _section_summary(sec: dict) -> dict:
    return {"page": sec["page"] + 1, "heading": sec["heading"], "found_by": sec["found_by"],
            "lines": sum(len(e["slots"]) for e in sec["entries"]),
            "entries": [{"key": e["key"], "label": e["label"], "lines": len(e["slots"]),
                         "items": len(e["items"])} for e in sec["entries"]],
            "font": f"{sec['entries'][0]['fam']} {sec['entries'][0]['size']}pt"}


def listing() -> dict:
    kb = json.loads(scan.KB_PATH.read_text(encoding="utf-8")) if scan.KB_PATH.exists() else scan.build()
    out = {}
    for key, v in kb["variants"].items():
        folder = find_folder(key)
        out[key] = {
            "key": key, "label": v.get("label", key),
            "file": Path(v["source_file"]).name, "uploaded_at": v.get("uploaded_at"),
            "url": f"/resume/{key}", "total_skills": v["total_skills"],
            "skills": v["skills"], "category_order": v["category_order"],
            "skills_section": _section_summary(v["skills_section"]),
            "previous_versions": previous_versions(folder) if folder else [],
        }
    return out


def version_path(key: str, name: str) -> Path | None:
    folder = find_folder(key)
    if folder is None or "/" in name or "\\" in name:
        return None
    p = folder / "_previous" / name
    return p if p.is_file() and p.suffix.lower() == ".pdf" else None
