"""JD vs resume gap analysis, tuned for literal-keyword ATS matching.

Discovery is dynamic, not a lookup in a fixed table:
  1. Terms come from the JD itself: known skills (vocabulary) AND anything that
     looks like a technology (shape heuristics + comma-separated skill lists),
     plus skills named in the job title.
  2. Each term is weighted by the JD's own signals: in the title, how often it is
     mentioned, under a mandatory heading, or in a sentence about ATS/keywords.
  3. The LLM is asked what an ATS for THIS title + JD focus would also search
     (title "AI Engineer" + JD "Python" -> LangChain, LangGraph, ...). Its terms
     are accepted even if my vocabulary has never heard of them. The static role
     table is only a fallback when the LLM is down or useless.
  4. Every term is checked literally against the resume text; misses are
     classified (A3 free / Tier B learnable / Tier C never / unverified) and the
     mismatch is scored with the signal weights.
"""
import json
import math
import os
import re
import urllib.request
from pathlib import Path

import skills_db as db

ROOT = Path(__file__).parent
WEIGHTS = {"required": 3, "preferred": 2, "implied": 1}
MAX_NEW = 4          # unproven additions (Tier B / unverified) per resume
MAX_IMPLIED = 16
MIN_LLM_USABLE = 4   # fewer usable LLM terms than this -> add role-table fallback


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
_TIER_C_LOWER = {c.lower() for c in db.TIER_C}

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


# ------------------------------------------------------- dynamic term detection
_PREF = re.compile(r"\b(preferred|nice[\s-]to[\s-]have|good[\s-]to[\s-]have|bonus|"
                   r"a plus|is a plus|desirable|added advantage|optional|plus points?)\b", re.I)
_MAND = re.compile(r"\b(mandatory|must[\s-]have|required|requirements?|key skills|"
                   r"primary skills|essential|minimum qualifications?)\b", re.I)
_HINT = re.compile(r"\b(ats|applicant tracking|keywords?|must (?:include|mention|list)|"
                   r"should (?:include|mention|list)|resume (?:should|must))\b", re.I)
_YEARS = re.compile(r"(\d+)\s*\+?\s*(?:-|to)?\s*\d*\s*\+?\s*(?:years?|yrs?)\b", re.I)
_LEAD = re.compile(r"^(?:(?:proficien\w*|experience|knowledge|understanding|familiarity|"
                   r"good|strong|solid|hands[\s-]on|working|expertise|exposure|skilled)"
                   r"(?:\s+(?:with|in|of|on))?\s+)+", re.I)
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[.+#][A-Za-z0-9]+)*[+#]*")

# words / acronyms / soft skills that look like terms but are not skills
_STOP = {w.lower() for w in """
And The For With Team Teams Skills Skill Education Experience Experiences Freshers Fresher
Students Candidates Candidate Developer Developers Engineer Engineers Software Technology
Technologies Knowledge Understanding Communication Teamwork Leadership Analytical Problem
Solving Problem-solving Responsibilities Requirements Qualifications Mandatory Preferred
Plus Etc Basic Good Strong Excellent Ability Work Working Company Product Products Client
Clients Customers Business Industry Years Year Months Full Time Part Role Position Location
Salary Benefits Perks About Our Your You We They Their This That These Those Must Should
UG PG BE ME IT CS BTECH MTECH BSC MSC MCA BCA CTC LPA USA UK EU HR HRM ASAP FAQ KPI ROI OK NA
CEO CTO COO MBA PHD VP DEV OPS QA UAT PM TL EMEA APAC ID ATS AI API APIS
""".split()}


# degrees and qualifications ("B.Tech", "MTech in IT") are not skills
_EDU = re.compile(r"\b(?:[BM]\.?\s?(?:tech|e|sc|ca|ba|com)|ph\.?d|degree|diploma|graduate)\b", re.I)


def _tech_like(tok: str) -> bool:
    """A token that looks like a technology name by its shape alone."""
    tok = tok.rstrip(".")
    if not (2 <= len(tok) <= 25) or tok.lower() in _STOP:
        return False
    if len(tok) == 2 and not re.search(r"[+#\d]", tok):
        return False
    if re.search(r"[.+#]", tok) and re.search(r"[A-Za-z]{2}|^C[+#]", tok):   # Node.js, C#, ASP.NET
        return True
    if tok.isupper() and 2 <= len(tok) <= 6 and tok.isalpha():               # AWS, GCP, NLP
        return True
    if re.search(r"[a-z][A-Z]|[A-Z]{2,}[a-z]", tok) and tok[0].isalpha():   # PostgreSQL, ReactJs
        return True
    return bool(re.search(r"\d", tok) and re.search(r"[A-Za-z]{2}", tok))    # S3, Web3, Python3


def _list_items(seg: str) -> list[str]:
    """Items of a comma/slash separated skill list (every item must be short)."""
    body = seg.split(":", 1)[1] if ":" in seg[:45] else seg
    raw = re.split(r"\s*(?:,|;|/|\||\band\b|\bor\b)\s*", body)
    items = [_LEAD.sub("", i.strip(" .()–-")).strip(" .()") for i in raw]
    items = [i for i in items if i]
    if len(items) < 3 or any(len(i.split()) > 3 or len(i) > 28 for i in items):
        return []
    return [i for i in items if re.search(r"[A-Za-z]", i) and i.lower() not in _STOP
            and (i[0].isupper() or _tech_like(i))]


# "experience with Airflow", "knowledge of Kafka Streams": a capitalised name after a cue
_CUE = re.compile(r"\b(?i:experience|knowledge|familiarity|proficiency|expertise|exposure|"
                  r"skilled|understanding)\s+(?i:with|in|of|on|to)\s+"
                  r"([A-Z][\w.+#-]*(?:\s+[A-Z][\w.+#-]*){0,2})")


def _after_cue(seg: str) -> list[str]:
    out = []
    for m in _CUE.finditer(seg):
        phrase = m.group(1)
        # the cue is case-insensitive, the skill name must still start capitalised
        if phrase[0].isupper():
            out.append(phrase.rstrip(".,"))
    return out


def _unknown_terms(seg: str, known_texts: set[str]) -> list[str]:
    """Terms in a segment that the vocabulary does not know."""
    cand = [m.group(0).rstrip(".") for m in _TOKEN.finditer(seg) if _tech_like(m.group(0))]
    cand += _list_items(seg) + _after_cue(seg)
    out, seen = [], set()
    for t in cand:
        low = t.lower()
        words = set(re.findall(r"[a-z0-9.+#]+", low))
        if (low in seen or low in _LOOKUP or low in _STOP or low in known_texts
                or any(w in known_texts for w in words) or _EDU.search(t)
                # a fragment of a skill the vocabulary already matched: "MVC" in
                # "ASP.NET MVC"
                or any(low in kt.split() for kt in known_texts)):
            continue
        seen.add(low)
        out.append(t)
    # drop a term that is just a word of a longer unknown term: "API" in "Web API"
    return [t for t in out
            if not any(u is not t and t.lower() in u.lower().split() for u in out)]


def _find_skills(segment: str) -> list[tuple[str, str]]:
    """Literal vocabulary matches; drops spans inside a longer match
    (e.g. 'React' inside 'React Native', 'OpenAI' inside 'OpenAI API')."""
    hits = []
    for canon, spelling, rx in _SPELLINGS:
        for m in rx.finditer(segment):
            hits.append((m.start(), m.end(), canon, m.group(0)))
    keep = [a for a in hits
            if not any(b is not a and b[0] <= a[0] and a[1] <= b[1]
                       and (b[1] - b[0]) > (a[1] - a[0]) for b in hits)]
    return [(c, t) for _, _, c, t in sorted(keep)]


def scan_jd(jd: str, title: str = "") -> dict[str, dict]:
    """term -> {jd_spelling, bucket, gated, count, mandatory, hint, in_title, known}.
    `term` is the canonical name for vocabulary skills, the JD's own spelling
    for everything else."""
    found: dict[str, dict] = {}

    def add(term: str, text: str, known: bool, bucket: str, gated: bool,
            mandatory: bool, hint: bool) -> None:
        cur = found.get(term)
        if cur is None:
            found[term] = {"jd_spelling": text, "bucket": bucket, "gated": gated,
                           "count": 1, "mandatory": mandatory, "hint": hint,
                           "in_title": False, "known": known}
            return
        cur["count"] += 1
        if bucket == "required":
            cur["bucket"] = "required"
        cur["gated"] = cur["gated"] or gated
        cur["mandatory"] = cur["mandatory"] or mandatory
        cur["hint"] = cur["hint"] or hint

    mode, mandatory_mode = "required", False
    for raw in jd.splitlines():
        raw = raw.strip()
        is_bullet = raw.startswith(("-", "•", "*", "·", "▪", "●"))
        for seg in re.split(r"(?<=[.;!?])\s+", raw):
            seg = seg.strip(" \t-•*·▪●")
            if not seg:
                continue
            known = _find_skills(seg)
            # a short line is a heading, unless it is just a skill name (no bullet,
            # no trailing colon) like the bare "AWS" under "Nice to have:"
            heading = (not is_bullet and len(seg) <= 60 and len(seg.split()) <= 7
                       and not seg.endswith((".", ";", ","))
                       and (seg.endswith(":") or not known))
            has_pref = bool(_PREF.search(seg))
            if heading:
                mode = "preferred" if has_pref else "required"
                mandatory_mode = bool(_MAND.search(seg)) and not has_pref
            bucket = "preferred" if (has_pref or mode == "preferred") else "required"
            years = [int(y) for y in _YEARS.findall(seg)]
            gated = bool(years) and max(years) >= 2
            hint = bool(_HINT.search(seg))
            mand = mandatory_mode and not has_pref
            known_texts = {t.lower() for _, t in known}
            for canon, text in known:
                add(canon, text, True, bucket, gated, mand, hint)
            for term in _unknown_terms(seg, known_texts):
                add(term, term, False, bucket, gated, mand, hint)

    # the job title is the strongest signal: skills named there count as required
    for canon, text in _find_skills(title):
        if canon not in found:
            add(canon, text, True, "required", False, True, False)
        found[canon]["in_title"] = True
    for term, info in found.items():
        if not info["in_title"] and title and _regex(info["jd_spelling"]).search(title):
            info["in_title"] = True
    return found


def emphasis(info: dict) -> float:
    """How loudly the JD asks for a term (title, repetition, mandatory, ATS hint)."""
    return (2.0 * info["in_title"] + 0.5 * min(info["count"] - 1, 3)
            + 1.0 * info["mandatory"] + 1.5 * info["hint"])


# --------------------------------------------------------------------- LLM part
_FEWSHOT = """List the skills and keywords a recruiter's ATS would search for this job. Tool and technology names only, comma separated.

Job title: AI Engineer
JD focus: Python
ATS keywords: Python, LangChain, LangGraph, RAG, Vector Databases, FAISS, OpenAI API, Docker, Hugging Face, Embeddings, Prompt Engineering

Job title: Full Stack Developer
JD focus: JavaScript, React
ATS keywords: JavaScript, React, Node.js, TypeScript, Tailwind CSS, REST APIs, MongoDB, PostgreSQL, Git, Docker

Job title: Backend Engineer
JD focus: Java
ATS keywords: Java, Spring Boot, REST APIs, SQL, PostgreSQL, Docker, Redis, Git, JUnit, Microservices

Job title: Data Analyst
JD focus: SQL, Excel
ATS keywords: SQL, Excel, Python, Pandas, Power BI, Tableau, Data Visualization, Statistics, ETL

Job title: {title}
JD focus: {skills}
ATS keywords:"""


def llm_keywords(title: str, focus: list[str]) -> tuple[list[str], str | None]:
    """What would an ATS for this title + JD focus also search? Returns
    (keywords, error). Never raises; junk in the answer is filtered out."""
    endpoint = os.getenv("LLM_ENDPOINT")
    if not endpoint:
        return [], "LLM_ENDPOINT not set in .env"
    prompt = _FEWSHOT.format(title=title.strip(), skills=", ".join(focus) or title.strip())
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
        item = item.strip(" \t\"'`-•*").rstrip(".")   # keep a leading dot: ".NET Core"
        if (2 <= len(item) <= 30 and len(item.split()) <= 3 and re.search(r"[A-Za-z]", item)
                and item.lower() not in _STOP and item.lower() not in seen):
            seen.add(item.lower())
            out.append(item)
    return out[:30], None


# --------------------------------------------------------------- classification
def tier_of(skill: str, family: str, known: bool = True) -> dict:
    if skill.lower() in _TIER_C_LOWER or skill in db.TIER_C:
        return {"tier": "C"}
    if skill in db.TIER_A3:
        return {"tier": "A3"}
    for name, freq, hours in db.TIER_B[family]:
        if name == skill:
            return {"tier": "B", "freq": freq, "hours": hours}
    others = [(f, h) for rows in db.TIER_B.values() for n, f, h in rows if n == skill]
    if others:
        return {"tier": "B", "freq": max(others, key=lambda t: db.FREQ_SCORE[t[0]])[0],
                "hours": min(h for _, h in others)}
    if skill in db.EXTRA_B:
        f, h = db.EXTRA_B[skill]
        return {"tier": "B", "freq": f, "hours": h}
    # not in the knowledge base: could be anything -> the user must verify it
    return {"tier": "unverified" if not known or skill not in db.SKILLS else "unclassified"}


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
def analyze(kb: dict, variant: str, title: str, jd: str, max_new: int = MAX_NEW) -> dict:
    load_env()
    resume_text = ", ".join(kb["variants"][variant]["all_skills"])
    family = role_family(title, variant)

    def in_resume(term: str) -> bool:
        if term in db.SKILLS:
            return any(rx.search(resume_text) for c, _, rx in _SPELLINGS if c == term)
        return bool(_regex(term).search(resume_text))

    # 1+2. what the JD (and its title) asks for, and how loudly
    jd_found = scan_jd(jd, title)
    wanted: list[dict] = []
    for term, info in jd_found.items():
        wanted.append({"skill": term, "jd_spelling": info["jd_spelling"],
                       "bucket": info["bucket"], "experience_gated": info["gated"],
                       "emphasis": round(emphasis(info), 1), "known": info["known"],
                       "in_title": info["in_title"], "ats_hint": info["hint"],
                       "mentions": info["count"], "source": "jd"})

    # 3. implied keywords: ask the LLM about THIS title + the JD's strongest terms
    focus = [w["skill"] for w in sorted(wanted, key=lambda w: -w["emphasis"])][:12]
    llm_raw, llm_err = llm_keywords(title, focus)
    implied: dict[str, tuple[str, bool]] = {}   # term -> (source, known)
    for kw in llm_raw:
        canon = _LOOKUP.get(kw.lower())
        if canon is None:
            if kw not in jd_found and kw.lower() not in {t.lower() for t in jd_found}:
                implied.setdefault(kw, ("llm", False))
        elif (canon not in jd_found and canon not in db.TIER_C
              and _relevant(canon, family, lambda s: in_resume(s))):
            implied.setdefault(canon, ("llm", True))
    if len(implied) < MIN_LLM_USABLE:        # LLM down or useless -> static fallback
        for name, freq, _ in db.TIER_B[family]:
            if freq in db.IMPLIED_FREQ and name not in jd_found:
                implied.setdefault(name, ("role_table_fallback", True))
    for term, (src, known) in list(implied.items())[:MAX_IMPLIED]:
        wanted.append({"skill": term, "jd_spelling": term, "bucket": "implied",
                       "experience_gated": False, "emphasis": 0.0, "known": known,
                       "in_title": False, "ats_hint": False, "mentions": 0, "source": src})

    # 4. literal match + classification
    for w in wanted:
        w["in_resume"] = in_resume(w["skill"])
        w.update(tier_of(w["skill"], family, w["known"]))

    def value(w: dict) -> float:     # how much it is worth adding
        return WEIGHTS[w["bucket"]] * 3 + w["emphasis"]

    missing = [w for w in wanted if not w["in_resume"]]
    # known, learnable skills outrank unverified ones of the same weight
    missing.sort(key=lambda w: (-value(w) + (3 if w["tier"] == "unverified" else 0),
                                -db.FREQ_SCORE.get(w.get("freq", ""), 0),
                                w.get("hours") or 0))

    # 5. suggestions
    free = [w["skill"] for w in missing if w["tier"] == "A3"]
    gated = [w["skill"] for w in missing if w["experience_gated"] and w["tier"] != "C"]
    learn_all = [w for w in missing if w["tier"] in ("B", "unverified")
                 and not w["experience_gated"]]
    learn = [{"skill": w["skill"], "hours": w.get("hours"), "bucket": w["bucket"],
              "tier": w["tier"], "emphasis": w["emphasis"]} for w in learn_all[:max_new]]
    overflow = [w["skill"] for w in learn_all[max_new:]]
    skip_c = [w["skill"] for w in missing if w["tier"] == "C"]
    review = [w["skill"] for w in missing
              if w["tier"] == "unclassified" and not w["experience_gated"]]

    # 6. scoring: bucket weight + a quarter point per point of JD emphasis
    def score(present_extra: set[str]) -> dict:
        out, tot_m, tot_w = {}, 0.0, 0.0
        for b, wt in WEIGHTS.items():
            items = [w for w in wanted if w["bucket"] == b]
            miss = [w for w in items if not (w["in_resume"] or w["skill"] in present_extra)]
            out[f"{b}_mismatch_pct"] = _pct(len(miss), len(items))
            out[f"{b}_missing"] = f"{len(miss)}/{len(items)}"
            tot_m += sum(wt + 0.25 * w["emphasis"] for w in miss)
            tot_w += sum(wt + 0.25 * w["emphasis"] for w in items)
        out["overall_mismatch_pct"] = _pct(tot_m, tot_w)
        return out

    after = set(free) | {t["skill"] for t in learn}
    keys = ("skill", "bucket", "tier", "freq", "hours", "jd_spelling", "source",
            "emphasis", "experience_gated")
    return {
        "resume": variant,
        "title": title,
        "role_family": family,
        "mismatch": score(set()),
        "mismatch_after_suggested_additions_pct": score(after)["overall_mismatch_pct"],
        "signals": {
            "in_title": [w["skill"] for w in wanted if w["in_title"]],
            "ats_hints": [w["skill"] for w in wanted if w["ats_hint"]],
            "most_emphasised": [w["skill"] for w in
                                sorted(wanted, key=lambda w: -w["emphasis"])
                                if w["emphasis"] >= 1.5][:8],
        },
        "skills": {
            "matched": [w["skill"] for w in wanted if w["in_resume"]],
            "wanted_buckets": {w["skill"]: w["bucket"] for w in wanted},
            "missing": [{k: w[k] for k in keys if k in w} for w in missing],
        },
        "suggested_additions": {
            "free_a3": free,
            "tier_b": learn,          # Tier B (learnable) + unverified, best first
            "tier_b_overflow": overflow,
            "skip_tier_c": skip_c,
            "experience_gated_skip": gated,
            "review_manually": review,
        },
        "llm": {"used": llm_err is None, "error": llm_err, "keywords": llm_raw,
                "fallback_used": any(s == "role_table_fallback" for s, _ in implied.values())},
    }
