"""Job hunt tracker: applications stored in data/job_hunt.json."""
import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "job_hunt.json"
OUTPUT_DIR = ROOT / "output"
STAGES = ["applied", "interviewing", "cleared", "rejected"]
Stage = Literal["applied", "interviewing", "cleared", "rejected"]


def _clean_skills(v: list[str]) -> list[str]:
    seen, out = set(), []
    for s in v or []:
        s = str(s).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _check_resume(v: str | None) -> str | None:
    """Must be a PDF the MCP tool created in output/ (or empty)."""
    if not v:
        return None
    if "/" in v or "\\" in v or not (OUTPUT_DIR / v).is_file():
        raise ValueError(f"resume_used '{v}' is not a file in output/")
    return v


class JobIn(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    link: str | None = Field(default=None, max_length=500)
    resume_used: str | None = None
    skills_lacking: list[str] = []
    skills_added: list[str] = []
    skills_matched: list[str] = []
    jd: str | None = Field(default=None, max_length=30000)
    cover_letter: str | None = Field(default=None, max_length=8000)
    cover_letter_file: str | None = None
    applied_date: date = Field(default_factory=date.today)
    stage: Stage = "applied"
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("skills_lacking", "skills_added", "skills_matched")
    @classmethod
    def clean_skills(cls, v):
        return _clean_skills(v)

    @field_validator("resume_used", "cover_letter_file")
    @classmethod
    def check_resume(cls, v):
        return _check_resume(v)


class JobPatch(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=160)
    link: str | None = None
    resume_used: str | None = None
    skills_lacking: list[str] | None = None
    skills_added: list[str] | None = None
    skills_matched: list[str] | None = None
    jd: str | None = Field(default=None, max_length=30000)
    cover_letter: str | None = Field(default=None, max_length=8000)
    cover_letter_file: str | None = None
    applied_date: date | None = None
    stage: Stage | None = None
    notes: str | None = None

    @field_validator("skills_lacking", "skills_added", "skills_matched")
    @classmethod
    def clean_skills(cls, v):
        return None if v is None else _clean_skills(v)

    @field_validator("resume_used", "cover_letter_file")
    @classmethod
    def check_resume(cls, v):
        return _check_resume(v)


def load() -> list[dict]:
    if not DATA.exists():
        return []
    return json.loads(DATA.read_text(encoding="utf-8"))


def save(jobs: list[dict]) -> None:
    DATA.parent.mkdir(exist_ok=True)
    tmp = DATA.with_suffix(".tmp")
    tmp.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, DATA)  # atomic: a crash never leaves half a file


def create(job: JobIn) -> dict:
    jobs = load()
    now = datetime.now().isoformat(timespec="seconds")
    item = {"id": uuid.uuid4().hex[:10], **job.model_dump(mode="json"),
            "created_at": now, "updated_at": now,
            "stage_history": [{"stage": job.stage, "at": now}]}
    jobs.insert(0, item)
    save(jobs)
    return item


def update(job_id: str, patch: JobPatch) -> dict | None:
    jobs = load()
    for item in jobs:
        if item["id"] == job_id:
            changes = patch.model_dump(mode="json", exclude_unset=True)
            now = datetime.now().isoformat(timespec="seconds")
            if "stage" in changes and changes["stage"] != item["stage"]:
                item.setdefault("stage_history", []).append({"stage": changes["stage"], "at": now})
            item.update(changes)
            item["updated_at"] = now
            save(jobs)
            return item
    return None


def delete(job_id: str) -> bool:
    """Delete the application AND the crafted resume copy it used (unless
    another application still points at the same copy)."""
    jobs = load()
    gone = next((j for j in jobs if j["id"] == job_id), None)
    if gone is None:
        return False
    kept = [j for j in jobs if j["id"] != job_id]
    save(kept)
    for field in ("resume_used", "cover_letter_file"):
        name = gone.get(field)
        if name and not any(j.get(field) == name for j in kept):
            path = (OUTPUT_DIR / name).resolve()
            if path.parent == OUTPUT_DIR.resolve() and path.suffix.lower() == ".pdf":
                path.unlink(missing_ok=True)
    return True


def counts() -> dict:
    jobs = load()
    out = {"total": len(jobs), **{s: 0 for s in STAGES}}
    for j in jobs:
        out[j.get("stage", "applied")] = out.get(j.get("stage", "applied"), 0) + 1
    return out


def lacking_from(analysis: dict, edit: dict) -> list[str]:
    """Skills to study if shortlisted: unproven skills the tool PUT on the resume
    (an interviewer will ask) + required/preferred JD skills that did not fit."""
    added = {c["skill"].lower() for c in edit.get("changelog", []) if c["action"] == "added"}
    out = []
    for m in analysis["skills"]["missing"]:
        names = {m["skill"].lower(), (m.get("jd_spelling") or "").lower()}
        on_resume = bool(names & added)
        if on_resume and m.get("tier") in ("B", "unverified"):
            out.append(m["skill"])
        elif not on_resume and m["bucket"] in ("required", "preferred"):
            out.append(m["skill"])
    return _clean_skills(out)


def added_from(edit: dict) -> list[str]:
    return _clean_skills([c["skill"] for c in edit.get("changelog", []) if c["action"] == "added"])


def lacking_from_selection(analysis: dict, edit: dict) -> list[str]:
    """Picker flow: skills to study if shortlisted = unproven skills put on the
    resume (an interviewer will ask) + must-add skills that were not added."""
    added = {s.lower() for s in added_from(edit)}
    out = []
    for i in analysis["categories"]["must_add"] + analysis["categories"]["might_add"]:
        on_resume = bool({i["skill"].lower(), i["text"].lower()} & added)
        if on_resume and i["tier"] != "A3":
            out.append(i["text"])
        elif not on_resume and i in analysis["categories"]["must_add"]:
            out.append(i["text"])
    return _clean_skills(out)
