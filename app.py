"""API to view the resume skills knowledge base.

Run:  python -m uvicorn app:app --reload --port 8000
"""
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import analyze
import scan

app = FastAPI(title="Resume Skills Knowledge Base")


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
    return {"routes": ["/ai", "/sde", "/fullstack", "/rescan"],
            "generated_at": load_kb()["generated_at"]}


class AnalyzeRequest(BaseModel):
    resume: str  # ai | sde | fullstack
    title: str
    jd: str


@app.post("/analyze")
def analyze_jd(req: AnalyzeRequest):
    """JD + resume variant + title -> missing skills and mismatch percentage."""
    key = analyze.resolve_variant(req.resume)
    if key is None or key not in load_kb()["variants"]:
        raise HTTPException(404, f"Unknown resume '{req.resume}' (use ai, sde or fullstack)")
    return analyze.analyze(load_kb(), key, req.title, req.jd)


@app.get("/{key}")
def get_variant(key: str):
    return variant(key)


@app.post("/rescan")  # POST, so it doesn't clash with GET /{key}
def rescan():
    """Re-read the PDFs and rebuild knowledge_base.json."""
    kb = scan.build()
    return {k: v["total_skills"] for k, v in kb["variants"].items()}
