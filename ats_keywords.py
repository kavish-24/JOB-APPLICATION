"""ATS keyword extraction via Groq (title + JD -> keyword JSON).

Standalone on purpose: only the /keywords API uses this. It is NOT part of
/analyze, /compose or /apply and never edits a resume.
"""
import json
import os
import urllib.error
import urllib.request

from analyze import load_env

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) optimization assistant and technical recruiter who specializes in ENTRY-LEVEL and JUNIOR roles (0–2 years of experience, freshers, interns, new graduates).

Your job: read a job posting and extract the keywords a candidate should include in their resume so it passes ATS keyword filters and is shortlisted.

## How to analyze
1. Read the JOB TITLE, COMPANY, and JOB DESCRIPTION carefully.
2. Pull keywords that appear EXPLICITLY in the job description first. ATS systems match exact phrases, so keep the exact wording used in the JD (e.g., if the JD says "RESTful APIs", do not change it to "REST").
3. Then add a SMALL number of closely related keywords that are standard for this role and level, and are very likely searched by recruiters even if not written in the JD.
4. Use the company name and its industry/domain only to infer relevant domain terms (e.g., fintech → "payments", e-commerce → "inventory"). Do not invent facts about the company.
5. Include common synonyms/abbreviations where ATS might search either form (e.g., "JavaScript (JS)", "Continuous Integration/Continuous Deployment (CI/CD)").

## BEGINNER-LEVEL RULES (very important)
This is a beginner / entry-level position. Be mindful of the candidate's level:
- DO NOT suggest senior-only skills or phrases such as: "system architecture ownership", "led a team of engineers", "mentoring juniors", "designing distributed systems at scale", "technical roadmap", "stakeholder management at director level", "5+ years of experience", "principal/staff-level", "hiring and managing", "P&L ownership".
- DO NOT suggest advanced specialist tools unless the JD explicitly asks for them.
- PREFER skills a fresher could realistically have learned through college, courses, internships, personal projects, hackathons, or open source.
- If the JD itself lists a senior-sounding requirement, still include the keyword but mark it as "stretch" and suggest a beginner-appropriate way to show it (e.g., "used Docker in a personal project" instead of "managed container infrastructure").
- Favor learning-oriented and collaborative soft skills (e.g., "team collaboration", "problem-solving", "willingness to learn", "Agile/Scrum exposure") over leadership/strategy skills.

## Honesty rule
Only suggest keywords; never encourage the candidate to claim skills they do not have. Add a short note reminding them to include only keywords they can genuinely back up in an interview.

## Output format
Return ONLY valid JSON, no extra text, in exactly this structure:

{
  "role_summary": "1–2 sentence summary of what this entry-level role actually needs",
  "must_have_keywords": [
    {"keyword": "", "source": "JD" | "inferred", "where_to_use": "Skills | Projects | Experience | Summary"}
  ],
  "good_to_have_keywords": [
    {"keyword": "", "source": "JD" | "inferred", "where_to_use": ""}
  ],
  "technical_skills": [],
  "tools_and_platforms": [],
  "soft_skills": [],
  "domain_keywords": [],
  "action_verbs": [],
  "stretch_keywords": [
    {"keyword": "", "beginner_friendly_phrasing": ""}
  ],
  "job_title_variations": [],
  "sample_resume_bullets": [
    "3–5 example project/experience bullets for a beginner that naturally include the top keywords"
  ],
  "keywords_to_avoid": ["senior-level terms that would look unrealistic for this candidate"],
  "honesty_note": ""
}

Limits: must_have_keywords 10–15 items, good_to_have_keywords 5–10, action_verbs 8–12. Rank must_have_keywords from most to least important."""


class KeywordError(RuntimeError):
    pass


def _parse_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def extract_keywords(title: str, jd: str, company: str = "") -> dict:
    """Ask Groq for ATS keywords for this title + JD. Raises KeywordError."""
    load_env()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise KeywordError("GROQ_API_KEY not set in .env")
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    user = (f"JOB TITLE: {title.strip()}\n"
            f"COMPANY: {company.strip() or 'Not specified'}\n\n"
            f"JOB DESCRIPTION:\n{jd.strip()}")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        GROQ_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "ats-keywords/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.getenv("GROQ_TIMEOUT", "90"))) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise KeywordError(f"Groq HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    except Exception as e:
        raise KeywordError(f"Groq request failed: {type(e).__name__}: {e}")
    content = data["choices"][0]["message"].get("content") or ""
    try:
        result = _parse_json(content)
    except json.JSONDecodeError:
        raise KeywordError(f"Model did not return valid JSON: {content[:300]}")
    return {"model": model, "title": title, "company": company, "keywords": result}
