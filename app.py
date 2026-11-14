"""API to view the resume skills knowledge base.

Run:  python -m uvicorn app:app --reload --port 8000
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import analyze
import ats_keywords as ats_kw
import compose
import jobs
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
    return {"routes": ["/ai", "/sde", "/fullstack", "/rescan", "/keywords"],
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
    key = analyze.resolve_variant(str(body["resume"]))
    if key is None or key not in kb["variants"]:
        raise HTTPException(404, f"Unknown resume '{body['resume']}' (use ai, sde or fullstack)")
    return kb, key, body


@app.post("/analyze")
async def analyze_jd(request: Request):
    """JSON body with resume (ai|sde|fullstack), title and jd (multi-line allowed)
    -> missing skills and mismatch percentage."""
    kb, key, body = await read_request(request)
    return await run_in_threadpool(analyze.analyze, kb, key, body["title"], body["jd"], max_new(body))


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
    })
    return {"file": name, "url": f"/files/{name}", "original_url": f"/resume/{key}",
            "analysis": analysis, "edit": edit,
            "skills_lacking": jobs.lacking_from(analysis, edit)}


# ------------------------------------------------------------- job hunt tracker
@app.get("/api/job_hunt")
def list_jobs():
    return {"jobs": jobs.load(), "stages": jobs.STAGES}


@app.post("/api/job_hunt", status_code=201)
def add_job(job: jobs.JobIn):
    return jobs.create(job)


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
    files = sorted(OUTPUT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"file": p.name, "url": f"/files/{p.name}"} for p in files]


@app.get("/{key}")
def get_variant(key: str):
    return variant(key)


@app.post("/rescan")  # POST, so it doesn't clash with GET /{key}
def rescan():
    """Re-read the PDFs and rebuild knowledge_base.json."""
    kb = scan.build()
    return {k: v["total_skills"] for k, v in kb["variants"].items()}
