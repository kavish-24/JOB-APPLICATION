"""API to view the resume skills knowledge base.

Run:  python -m uvicorn app:app --reload --port 8000
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import analyze
import coverletter
import ats_keywords as ats_kw
import compose
import jobs
import resumes
import settings
import scan

app = FastAPI(title="Resume Skills Knowledge Base")
ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_kb() -> dict:
    if not scan.KB_PATH.exists():
        return scan.build()
    return json.loads(scan.KB_PATH.read_text(encoding="utf-8"))


def variant(key: str) -> dict:
    v = load_kb()["variants"].get(key)
    if v is None:
        raise HTTPException(404, f"No resume found for '{key}'")
    return v


@app.get("/")
def index():
    return {"routes": [*load_kb()["variants"], "/rescan", "/keywords", "/api/resumes",
                       "/api/profile"],
            "generated_at": load_kb()["generated_at"]}


def parse_body(raw: str) -> dict:
    """Accept strict JSON, or JSON where the JD is pasted as a Python-style
    triple-quoted multi-line string (\"\"\"...\"\"\")."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = re.sub(r'"""(.*?)"""', lambda m: json.dumps(m.group(1).strip()),
                       raw, flags=re.S)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise HTTPException(400, f"Body is not valid JSON: {e}")


async def read_request(request: Request) -> tuple[dict, str, dict]:
    body = parse_body((await request.body()).decode("utf-8-sig"))
    missing = [k for k in ("resume", "title", "jd") if not str(body.get(k, "")).strip()]
    if missing:
        raise HTTPException(422, f"Missing field(s): {', '.join(missing)}")
    kb = load_kb()
    raw = str(body["resume"]).strip().lower()
    key = raw if raw in kb["variants"] else analyze.resolve_variant(raw)
    if key is None or key not in kb["variants"]:
        raise HTTPException(404, f"Unknown resume '{body['resume']}' "
                                 f"(have: {', '.join(kb['variants']) or 'none, upload one'})")
    return kb, key, body


@app.post("/analyze")
async def analyze_jd(request: Request):
    """JSON body with resume (ai|sde|fullstack), title, jd (multi-line allowed) and
    optional company. Groq finds the ATS keywords for title + company + JD; they
    are checked against the resume and split into categories.have / must_add /
    might_add. Nothing is edited here."""
    kb, key, body = await read_request(request)
    title, jd, company = body["title"], body["jd"], str(body.get("company", ""))
    keywords = await run_in_threadpool(keywords_or_error, title, jd, company)
    analysis = await run_in_threadpool(analyze.analyze, kb, key, title, jd, max_new(body), keywords)
    return {**analysis, "company": company, "ats_keywords": keywords}


def keywords_or_error(title: str, jd: str, company: str) -> dict:
    """Groq keywords for /analyze; a Groq failure must not fail the analysis."""
    try:
        return ats_kw.extract_keywords(title, jd, company)
    except ats_kw.KeywordError as e:
        return {"error": str(e)}


@app.post("/keywords")
async def ats_keywords(request: Request):
    """JSON body with title, jd (and optional company) -> ATS keyword JSON from
    Groq. Keyword output only: does not analyse or edit any resume."""
    body = parse_body((await request.body()).decode("utf-8-sig"))
    missing = [k for k in ("title", "jd") if not str(body.get(k, "")).strip()]
    if missing:
        raise HTTPException(422, f"Missing field(s): {', '.join(missing)}")
    try:
        return await run_in_threadpool(ats_kw.extract_keywords, str(body["title"]),
                                       str(body["jd"]), str(body.get("company", "")))
    except ats_kw.KeywordError as e:
        raise HTTPException(502, str(e))


def max_new(body: dict) -> int:
    """Optional body field: how many unproven skills (Tier B / unverified) to add."""
    try:
        return max(0, min(12, int(body.get("max_new", analyze.MAX_NEW))))
    except (TypeError, ValueError):
        return analyze.MAX_NEW


def analyze_and_compose(kb: dict, key: str, title: str, jd: str, limit: int) -> dict:
    analysis = analyze.analyze(kb, key, title, jd, limit)
    return {"analysis": analysis, "compose": compose.compose(kb, key, analysis)}


@app.post("/compose")
async def compose_skills(request: Request):
    """Same body as /analyze -> analysis + the rewritten TECHNICAL SKILLS section
    (same space: adds if there is room, otherwise drops the least useful skill)."""
    kb, key, body = await read_request(request)
    return await run_in_threadpool(analyze_and_compose, kb, key, body["title"], body["jd"], max_new(body))


async def call_mcp(tool: str, arguments: dict) -> dict:
    """Call a tool on the resume-editor MCP server (stdio, one process per call)."""
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")],
                                   cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    text = result.content[0].text if result.content else ""
    if result.is_error:
        raise HTTPException(500, f"MCP tool {tool} failed: {text}")
    return json.loads(text)


@app.post("/apply")
async def apply_to_resume(request: Request):
    """Analyse the JD, copy the chosen resume, and have the MCP tool put the skills
    into the copy (add if there is room, otherwise drop the least valuable skill)."""
    kb, key, body = await read_request(request)
    analysis = await run_in_threadpool(analyze.analyze, kb, key, body["title"], body["jd"], max_new(body))
    slug = re.sub(r"[^a-z0-9]+", "-", body["title"].lower()).strip("-")[:40] or "role"
    name = f"{key}_{slug}_{time.strftime('%Y%m%d-%H%M%S')}.pdf"
    copy = OUTPUT_DIR / name
    shutil.copy2(ROOT / kb["variants"][key]["source_file"], copy)
    edit = await call_mcp("add_skills_to_resume", {
        "pdf_path": str(copy),
        "additions": compose.additions_from(analysis),
        "wanted": analysis["skills"]["wanted_buckets"],
        "role_family": analysis["role_family"],
        "personal": bool(analysis.get("personal", False)),
    })
    return {"file": name, "url": f"/files/{name}", "original_url": f"/resume/{key}",
            "analysis": analysis, "edit": edit,
            "skills_lacking": jobs.lacking_from(analysis, edit)}


@app.post("/apply_selected")
async def apply_selected(request: Request):
    """Body: {"analysis": <the /analyze response>, "selected": [skill, ...]}.
    Copies the analysed resume and has the MCP tool add ONLY the selected skills
    (add if there is room, otherwise drop a less valuable skill)."""
    body = parse_body((await request.body()).decode("utf-8-sig"))
    analysis, selected = body.get("analysis"), body.get("selected")
    if not isinstance(analysis, dict) or "categories" not in analysis:
        raise HTTPException(422, "Run /analyze first and send its result as 'analysis'")
    if not isinstance(selected, list):
        raise HTTPException(422, "'selected' must be a list of skills (may be empty)")
    kb = load_kb()
    key = analysis.get("resume")
    if key not in kb["variants"]:
        raise HTTPException(404, f"Unknown resume '{key}'")
    additions = compose.additions_for(analysis, [str(s) for s in selected])
    if selected and not additions:
        raise HTTPException(422, "None of the selected skills are in the analysis")
    slug = re.sub(r"[^a-z0-9]+", "-", str(analysis.get("title", "")).lower()).strip("-")[:40] or "role"
    name = f"{key}_{slug}_{time.strftime('%Y%m%d-%H%M%S')}.pdf"
    copy = OUTPUT_DIR / name
    # always a fresh copy per application, even with nothing to add, so the
    # base resume is never the file an application points at
    shutil.copy2(ROOT / kb["variants"][key]["source_file"], copy)
    if not additions:
        edit = {"changelog": [], "no_slot": [], "unchanged": True}
        return {"file": name, "url": f"/files/{name}", "original_url": f"/resume/{key}",
                "edit": edit, "skills_added": [],
                "skills_lacking": jobs.lacking_from_selection(analysis, edit)}
    edit = await call_mcp("add_skills_to_resume", {
        "pdf_path": str(copy),
        "additions": additions,
        "wanted": analysis["skills"]["wanted_buckets"],
        "role_family": analysis["role_family"],
        "personal": bool(analysis.get("personal", False)),
    })
    return {"file": name, "url": f"/files/{name}", "original_url": f"/resume/{key}",
            "edit": edit, "skills_added": jobs.added_from(edit),
            "skills_lacking": jobs.lacking_from_selection(analysis, edit)}


# ------------------------------------------------------------- cover letters
def _letter_slug(title: str, company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{company} {title}".lower()).strip("-")[:50] or "letter"


@app.post("/cover_letter")
async def cover_letter(request: Request):
    """Body: resume (category key), title, company, jd, optional skills [..].
    The LOCAL model writes a brief letter from the resume's own text; returns
    the text (editable) plus the name/contact used for the PDF header."""
    body = parse_body((await request.body()).decode("utf-8-sig"))
    missing = [k for k in ("resume", "title", "jd") if not str(body.get(k, "")).strip()]
    if missing:
        raise HTTPException(422, f"Missing field(s): {', '.join(missing)}")
    kb = load_kb()
    v = kb["variants"].get(str(body["resume"]))
    if v is None:
        raise HTTPException(404, f"Unknown resume '{body['resume']}'")
    resume_text = "SKILLS: " + ", ".join(v["all_skills"]) + "\n" + v.get("body_text", "")
    header = v.get("header") or {}
    skills = [str(s) for s in body.get("skills") or []]
    try:
        return await run_in_threadpool(coverletter.write, resume_text, header, str(body["title"]),
                                       str(body.get("company", "")), str(body["jd"]), skills)
    except coverletter.LetterError as e:
        raise HTTPException(502, str(e))


@app.post("/cover_letter/pdf")
async def cover_letter_pdf(request: Request):
    """Body: text (the possibly edited letter), name, contact, title, company,
    resume. Renders a one-page PDF into output/ and returns its URL."""
    body = parse_body((await request.body()).decode("utf-8-sig"))
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(422, "The cover letter is empty")
    if len(text) > 8000:
        raise HTTPException(422, "The cover letter is too long")
    title, company = str(body.get("title", "")), str(body.get("company", ""))
    key = re.sub(r"[^a-z0-9_]+", "", str(body.get("resume", "")).lower())[:30] or "cv"
    name = f"cover_{key}_{_letter_slug(title, company)}_{time.strftime('%Y%m%d-%H%M%S')}.pdf"
    try:
        await run_in_threadpool(coverletter.render_pdf, OUTPUT_DIR / name, text,
                                str(body.get("name", "")), str(body.get("contact", "")), title, company)
    except coverletter.LetterError as e:
        raise HTTPException(422, str(e))
    return {"file": name, "url": f"/files/{name}"}


# ------------------------------------------------------------- base resumes
@app.get("/api/resumes")
def list_resumes():
    return list(resumes.listing().values())


@app.post("/api/resumes", status_code=201)
async def upload_resume(file: UploadFile = File(...), category: str = Form(...)):
    """Upload a base resume under a category the user names. The skills section
    is located and its layout stored; an existing category is replaced (the old
    PDF is archived, never erased)."""
    data = await file.read()
    try:
        return await run_in_threadpool(resumes.save, category, file.filename or "", data)
    except resumes.ResumeError as e:
        raise HTTPException(422, str(e))


@app.patch("/api/resumes/{tag}")
def edit_resume(tag: str, body: dict):
    try:
        return resumes.rename(tag, str(body.get("label", "")))
    except KeyError:
        raise HTTPException(404, f"No resume category '{tag}'")
    except resumes.ResumeError as e:
        raise HTTPException(422, str(e))


@app.delete("/api/resumes/{tag}", status_code=204)
def delete_resume(tag: str):
    try:
        resumes.delete(tag)
    except KeyError:
        raise HTTPException(404, f"No resume category '{tag}'")


@app.get("/api/resumes/{tag}/versions/{name}")
def get_resume_version(tag: str, name: str):
    path = resumes.version_path(tag, name)
    if path is None:
        raise HTTPException(404, "No such version")
    return FileResponse(path, media_type="application/pdf")


def _header(kb: dict) -> dict:
    return next((v.get("header") for v in kb["variants"].values() if v.get("header")), {}) or {}


def display_name(kb: dict) -> str:
    """The name set in the account panel, else the one on the resumes."""
    return settings.load().get("display_name") or _header(kb).get("name", "")


def resume_email(kb: dict) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", _header(kb).get("contact", ""))
    return m.group(0) if m else ""


@app.get("/api/settings")
async def get_settings():
    kb = load_kb()
    s = settings.load()
    return {"display_name": display_name(kb), "resume_name": _header(kb).get("name", ""),
            "email": resume_email(kb),
            "llm_endpoint": s.get("llm_endpoint", ""),
            "llm_endpoint_effective": settings.llm_endpoint(),
            "llm_endpoint_source": "app" if s.get("llm_endpoint") else (
                ".env" if settings.llm_endpoint() else "none"),
            "local_model": await run_in_threadpool(settings.probe)}


@app.patch("/api/settings")
async def save_settings(request: Request):
    """Body: {display_name?, llm_endpoint?}. An empty llm_endpoint falls back to .env."""
    body = parse_body((await request.body()).decode("utf-8-sig"))
    try:
        settings.update(body.get("display_name"), body.get("llm_endpoint"))
    except settings.SettingsError as e:
        raise HTTPException(422, str(e))
    return await get_settings()


@app.post("/api/settings/test")
async def test_llm(request: Request):
    """Body: {llm_endpoint?}: check a URL (or the saved one) without saving it."""
    body = parse_body((await request.body()).decode("utf-8-sig") or "{}")
    url = str(body.get("llm_endpoint") or "").strip() or None
    return await run_in_threadpool(settings.probe, url, True)


@app.get("/api/status")
async def status():
    """Real status for the app header/footer: providers, owner name, counts."""
    analyze.load_env()
    kb = load_kb()
    name = display_name(kb)
    return {
        "groq": "ready" if os.getenv("GROQ_API_KEY") else "missing",
        "local_model": (await run_in_threadpool(settings.probe))["state"],
        "user": {"name": name,
                 "initials": "".join(w[0] for w in name.split()[:2]).upper() if name else ""},
        "resumes": len(kb["variants"]),
        "jobs": jobs.counts()["total"],
    }


@app.get("/api/profile")
def profile():
    """Base resumes, every skill across them (with the tags that list it), and
    application counts."""
    items = list(resumes.listing().values())
    kb = load_kb()
    skills: dict[str, dict] = {}
    for key, v in kb["variants"].items():
        for s in v["all_skills"]:
            e = skills.setdefault(s.lower(), {"skill": s, "tags": []})
            e["tags"].append(key)
    return {"user": {"name": display_name(kb), "email": resume_email(kb)},
            "resumes": items,
            "skills": sorted(skills.values(), key=lambda e: (-len(e["tags"]), e["skill"].lower())),
            "jobs": jobs.counts()}


# ------------------------------------------------------------- job hunt tracker
@app.get("/api/job_hunt")
def list_jobs():
    return {"jobs": jobs.load(), "stages": jobs.STAGES}


@app.post("/api/job_hunt", status_code=201)
def add_job(job: jobs.JobIn):
    return jobs.create(job)


@app.get("/api/job_hunt/{job_id}")
def get_job(job_id: str):
    item = next((j for j in jobs.load() if j["id"] == job_id), None)
    if item is None:
        raise HTTPException(404, "No such application")
    return item


@app.patch("/api/job_hunt/{job_id}")
def edit_job(job_id: str, patch: jobs.JobPatch):
    item = jobs.update(job_id, patch)
    if item is None:
        raise HTTPException(404, "No such application")
    return item


@app.delete("/api/job_hunt/{job_id}", status_code=204)
def remove_job(job_id: str):
    if not jobs.delete(job_id):
        raise HTTPException(404, "No such application")


@app.get("/files/{name}")
def get_output(name: str):
    path = (OUTPUT_DIR / name).resolve()
    if path.parent != OUTPUT_DIR.resolve() or not path.is_file():
        raise HTTPException(404, "No such file")
    return FileResponse(path, media_type="application/pdf")


@app.get("/resume/{key}")
def get_original(key: str):
    """The untouched source resume PDF, for the viewer's before/after toggle."""
    return FileResponse(ROOT / variant(key)["source_file"], media_type="application/pdf")


@app.get("/outputs")
def list_outputs():
    files = sorted((p for p in OUTPUT_DIR.glob("*.pdf") if not p.name.startswith("cover_")),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"file": p.name, "url": f"/files/{p.name}"} for p in files]


@app.get("/{key}")
def get_variant(key: str):
    return variant(key)


@app.post("/rescan")  # POST, so it doesn't clash with GET /{key}
def rescan():
    """Re-read the PDFs and rebuild knowledge_base.json."""
    kb = scan.build()
    return {k: v["total_skills"] for k, v in kb["variants"].items()}
