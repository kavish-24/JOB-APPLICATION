"""JD vs resume gap analysis, tuned for literal-keyword ATS matching.

Pipeline
  1. Scan the JD for known skill spellings (literal, word-boundary) and tag each as
     Required / Preferred, flagging experience-gated lines ("3+ years of X").
  2. Build the *implied* keywords an ATS for this role would also search: the role
     graph from the plan (always) + an LLM expansion from title + JD skills (best
     effort; the pipeline still works if the endpoint is down or rambles).
  3. Check every wanted skill against the resume's skills text, literally.
  4. Classify misses (A3 free / Tier B learnable / Tier C never) and score mismatch.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

import skills_db as db

ROOT = Path(__file__).parent
WEIGHTS = {"required": 3, "preferred": 2, "implied": 1}
MAX_TIER_B = 4
MAX_IMPLIED = 14


# ---------------------------------------------------------------- env / helpers
def load_env() -> None:
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _regex(spelling: str) -> re.Pattern:
    flags = 0 if spelling in db.CASE_SENSITIVE else re.I
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(spelling) + r"(?![A-Za-z0-9+#])", flags)


# (canonical, spelling, compiled regex), longest spelling first
_SPELLINGS = sorted(
    ((c, s, _regex(s)) for c, alts in db.SKILLS.items() for s in [c, *alts]),
    key=lambda t: -len(t[1]),
)
_LOOKUP = {s.lower(): c for c, s, _ in _SPELLINGS}  # exact alias -> canonical

VARIANT_KEYS = {"ai": "ai", "aiml": "ai", "ai_ml": "ai", "ml": "ai", "sde": "sde",
                "fullstack": "fullstack", "full_stack": "fullstack"}


def resolve_variant(name: str) -> str | None:
    return VARIANT_KEYS.get(re.sub(r"[\s\-]+", "_", name.strip().lower()))


def role_family(title: str, default: str) -> str:
    t = title.lower()
    if re.search(r"full[\s-]?stack|front[\s-]?end|\breact|\bmern\b|mobile|web develop", t):
        return "fullstack"
    if re.search(r"\bai\b|\bml\b|machine learning|\bllm|genai|generative|data scien|\bnlp\b|speech", t):
        return "ai"
    if re.search(r"software|\bsde\b|backend|back[\s-]?end|java|python|engineer|developer|trainee", t):
        return "sde"
    return default


# ------------------------------------------------------------------ JD scanning
_PREF = re.compile(r"\b(preferred|nice[\s-]to[\s-]have|good[\s-]to[\s-]have|bonus|"
                   r"a plus|is a plus|desirable|added advantage|optional|plus points?)\b", re.I)
_YEARS = re.compile(r"(\d+)\s*\+?\s*(?:-|to)?\s*\d*\s*\+?\s*(?:years?|yrs?)\b", re.I)


def _find_skills(segment: str) -> list[tuple[str, str]]:
    """Literal matches in a text segment; drops spans inside a longer match
    of another skill (e.g. 'React' inside 'React Native')."""
    hits = []
    for canon, spelling, rx in _SPELLINGS:
        for m in rx.finditer(segment):
            hits.append((m.start(), m.end(), canon, m.group(0)))
    keep = []
    for a in hits:
        inside = any(b is not a and b[2] != a[2] and b[0] <= a[0] and a[1] <= b[1]
                     and (b[1] - b[0]) > (a[1] - a[0]) for b in hits)
        if not inside:
            keep.append(a)
    return [(c, t) for _, _, c, t in sorted(keep)]


def scan_jd(jd: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    mode = "required"
    for raw in jd.splitlines():
        raw = raw.strip()
        is_bullet = raw.startswith(("-", "•", "*", "·", "▪", "●"))
        for seg in re.split(r"(?<=[.;!?])\s+", raw):
            seg = seg.strip(" \t-•*·▪●")
            if not seg:
                continue
            heading = (not is_bullet and len(seg) <= 60 and len(seg.split()) <= 7
                       and not seg.endswith((".", ";", ",")))
            has_pref = bool(_PREF.search(seg))
            if heading:
                mode = "preferred" if has_pref else "required"
            bucket = "preferred" if (has_pref or mode == "preferred") else "required"
            years = [int(y) for y in _YEARS.findall(seg)]
            gated = bool(years) and max(years) >= 2
            for canon, text in _find_skills(seg):
                cur = found.get(canon)
                if cur is None:
                    found[canon] = {"jd_spelling": text, "bucket": bucket, "gated": gated}
                else:  # required beats preferred; any gated mention flags it
                    if bucket == "required":
                        cur["bucket"] = "required"
                    cur["gated"] = cur["gated"] or gated
    return found


# --------------------------------------------------------------------- LLM part
_FEWSHOT = """List the skills and keywords a recruiter's ATS would search for this job. Tool and technology names only, comma separated.

Job title: AI Engineer
JD skills: Python
ATS keywords: Python, LangChain, LangGraph, RAG, Vector Databases, FAISS, OpenAI API, Docker, Hugging Face, Embeddings, Prompt Engineering

Job title: Full Stack Developer
JD skills: JavaScript, React
ATS keywords: JavaScript, React, Node.js, TypeScript, Tailwind CSS, REST APIs, MongoDB, PostgreSQL, Git, Docker

Job title: Backend Engineer
JD skills: Java
ATS keywords: Java, Spring Boot, REST APIs, SQL, PostgreSQL, Docker, Redis, Git, JUnit, Microservices

Job title: {title}
JD skills: {skills}
ATS keywords:"""


def llm_keywords(title: str, jd_skills: list[str]) -> tuple[list[str], str | None]:
    """Ask the LLM what an ATS for this role would also search. Returns
    (keywords, error). Never raises; garbage in the answer is filtered out."""
    endpoint = os.getenv("LLM_ENDPOINT")
    if not endpoint:
        return [], "LLM_ENDPOINT not set in .env"
    prompt = _FEWSHOT.format(title=title.strip(), skills=", ".join(jd_skills) or title.strip())
    req = urllib.request.Request(
        endpoint, data=json.dumps({"question": prompt}).encode(),
        headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.getenv("LLM_TIMEOUT", "120"))) as r:
            answer = json.load(r).get("answer", "")
    except Exception as e:  # network, timeout, bad JSON ...
        return [], f"{type(e).__name__}: {e}"
    line = answer.strip().split("\n")[0].split("Job title")[0]
    out, seen = [], set()
    for item in re.split(r"[,;]", line):
        item = item.strip(" \t\"'`-•*.")
        if 2 <= len(item) <= 40 and len(item.split()) <= 4 and re.search(r"[A-Za-z]", item):
            if item.lower() not in seen:
                seen.add(item.lower())
                out.append(item)
    return out[:30], None


# --------------------------------------------------------------- classification
def tier_of(skill: str, family: str) -> dict:
    if skill in db.TIER_C:
        return {"tier": "C"}
    if skill in db.TIER_A3:
        return {"tier": "A3"}
    for name, freq, hours in db.TIER_B[family]:
        if name == skill:
            return {"tier": "B", "freq": freq, "hours": hours}
    others = [(f, h) for fam, rows in db.TIER_B.items() for n, f, h in rows if n == skill]
    if others:
        return {"tier": "B", "freq": max(others, key=lambda t: db.FREQ_SCORE[t[0]])[0],
                "hours": min(h for _, h in others)}
    if skill in db.EXTRA_B:
        f, h = db.EXTRA_B[skill]
        return {"tier": "B", "freq": f, "hours": h}
    return {"tier": "unclassified"}


def _pct(missing: float, total: float) -> float | None:
    return round(100 * missing / total, 1) if total else None


def _relevant(skill: str, family: str, owned) -> bool:
    """Guard against a weak LLM: skip skills that belong only to another role
    family's Tier-B list (e.g. JUnit for an AI role)."""
    if skill in db.TIER_A3 or owned(skill):
        return True
    in_family = any(n == skill for n, _, _ in db.TIER_B[family])
    elsewhere = any(n == skill for fam, rows in db.TIER_B.items() if fam != family
                    for n, _, _ in rows)
    return in_family or not elsewhere


# ------------------------------------------------------------------------ main
def analyze(kb: dict, variant: str, title: str, jd: str) -> dict:
    load_env()
    resume_text = ", ".join(kb["variants"][variant]["all_skills"])
    family = role_family(title, variant)

    def in_resume(skill: str) -> bool:
        return any(rx.search(resume_text) for c, _, rx in _SPELLINGS if c == skill)

    # 1. skills literally in the JD
    jd_found = scan_jd(jd)
    wanted: list[dict] = []
    for skill, info in jd_found.items():
        wanted.append({"skill": skill, "jd_spelling": info["jd_spelling"],
                       "bucket": info["bucket"], "experience_gated": info["gated"]})

    # 2. implied keywords: role graph + LLM
    llm_raw, llm_err = llm_keywords(title, list(jd_found))
    implied: dict[str, str] = {}
    for name, freq, _ in db.TIER_B[family]:
        if freq in db.IMPLIED_FREQ and name not in jd_found:
            implied[name] = "role_graph"
    unverified = []
    for kw in llm_raw:
        canon = _LOOKUP.get(kw.lower())
        if canon is None:
            unverified.append(kw)
        elif canon not in jd_found and canon not in db.TIER_C and _relevant(canon, family, in_resume):
            implied[canon] = "both" if canon in implied else "llm"
    for skill, src in list(implied.items())[:MAX_IMPLIED]:
        wanted.append({"skill": skill, "bucket": "implied", "source": src,
                       "experience_gated": False})

    # 3. literal match + classification
    for w in wanted:
        w["in_resume"] = in_resume(w["skill"])
        w.update(tier_of(w["skill"], family))

    missing = [w for w in wanted if not w["in_resume"]]
    rank = {"required": 0, "preferred": 1, "implied": 2}
    missing.sort(key=lambda w: (rank[w["bucket"]], -db.FREQ_SCORE.get(w.get("freq", ""), 0),
                                w.get("hours", 0)))

    # 4. suggestions
    free = [w["skill"] for w in missing if w["tier"] == "A3"]
    gated = [w["skill"] for w in missing if w["experience_gated"] and w["tier"] != "C"]
    b_all = [w for w in missing if w["tier"] == "B" and not w["experience_gated"]]
    tier_b = [{"skill": w["skill"], "hours": w["hours"], "bucket": w["bucket"]}
              for w in b_all[:MAX_TIER_B]]
    overflow = [w["skill"] for w in b_all[MAX_TIER_B:]]
    skip_c = [w["skill"] for w in missing if w["tier"] == "C"]
    review = [w["skill"] for w in missing
              if w["tier"] == "unclassified" and not w["experience_gated"]]

    # 5. scoring
    def score(present_extra: set[str]) -> dict:
        out, tot_m, tot_w = {}, 0.0, 0.0
        for b, wt in WEIGHTS.items():
            items = [w for w in wanted if w["bucket"] == b]
            miss = [w for w in items if not (w["in_resume"] or w["skill"] in present_extra)]
            out[f"{b}_mismatch_pct"] = _pct(len(miss), len(items))
            out[f"{b}_missing"] = f"{len(miss)}/{len(items)}"
            tot_m += wt * len(miss)
            tot_w += wt * len(items)
        out["overall_mismatch_pct"] = _pct(tot_m, tot_w)
        return out

    after = {s for s in free} | {t["skill"] for t in tier_b}
    mismatch = score(set())
    return {
        "resume": variant,
        "title": title,
        "role_family": family,
        "mismatch": mismatch,
        "mismatch_after_suggested_additions_pct": score(after)["overall_mismatch_pct"],
        "skills": {
            "matched": [w["skill"] for w in wanted if w["in_resume"]],
            "missing": [{k: w[k] for k in ("skill", "bucket", "tier", "freq", "hours",
                                           "jd_spelling", "source", "experience_gated")
                         if k in w} for w in missing],
        },
        "suggested_additions": {
            "free_a3": free,
            "tier_b": tier_b,
            "tier_b_overflow": overflow,
            "skip_tier_c": skip_c,
            "experience_gated_skip": gated,
            "review_manually": review,
        },
        "llm": {"used": llm_err is None, "error": llm_err,
                "keywords": llm_raw, "unverified_not_scored": unverified},
    }
