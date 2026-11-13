"""Plan the new TECHNICAL SKILLS section: add skills into the finite space.

Rules (resume_skills_crafter.md, steps 3-5):
  * Space is fixed: every line must still fit on ONE printed line. Widths are
    measured in points against the real PDF (pdfedit).
  * A suggested skill goes on its own category line if there is room.
  * No room -> drop the least valuable skill on that line until it fits, but an
    addition may only displace something worth LESS than itself:
        value of an addition : required 10, preferred 4.5, implied 3
        value of a resume item: Vue.js 0 | off-role A2 1 | off-role A1 2 |
                                on-role A2 4 | on-role A1 5 | CS fundamentals 4
  * Never drop Python / Java / JavaScript / SQL, or anything the JD wants.
  * Order: category with most Required JD skills first; within a line,
    Required -> Preferred -> Implied -> the rest.
"""
import re
from pathlib import Path

import analyze
import pdfedit
import skills_db as db

ROOT = Path(__file__).parent
BUCKET_RANK = {"required": 0, "preferred": 1, "implied": 2}
ADD_VALUE = {"required": 10, "preferred": 4.5, "implied": 3}
# resume lines that matter for each role family (items there are "on-role")
CORE_LINES = {
    "ai": {"AI/ML"},
    "sde": {"Languages", "Backend", "Databases", "Tools & DevOps", "CS Fundamentals"},
    "fullstack": {"Languages", "Frontend & Mobile", "Backend", "Databases"},
}


def canon(item: str) -> str | None:
    """Resume item -> canonical skill name ('LLMs (Google Gemini)' -> 'LLMs')."""
    for form in (item, re.sub(r"\s*\(.*?\)", "", item).strip()):
        c = analyze._LOOKUP.get(form.lower())
        if c:
            return c
    return None


def additions_from(analysis: dict) -> list[dict]:
    """Analysis -> skills to try adding, with the JD's own spelling."""
    buckets = analysis["skills"]["wanted_buckets"]
    spelling = {m["skill"]: m.get("jd_spelling") or m["skill"]
                for m in analysis["skills"]["missing"]}
    sug = analysis["suggested_additions"]
    names = list(sug["free_a3"]) + [t["skill"] for t in sug["tier_b"]]
    adds = [{"skill": s, "text": spelling.get(s, s), "bucket": buckets.get(s, "implied")}
            for s in names]
    adds.sort(key=lambda a: BUCKET_RANK.get(a["bucket"], 2))  # stable
    return adds


def plan(current: dict, additions: list[dict], wanted: dict, role_family: str) -> dict:
    """current = pdfedit.read_skills(); wanted = {skill: bucket} for the JD."""
    lines = {cat: list(items) for cat, items in current["lines"].items()}
    avail, size = current["avail"], current["size"]
    wanted_set = set(wanted)
    core = CORE_LINES.get(role_family, set())

    def width(cat: str, items: list[str]) -> float:
        return pdfedit.text_width(pdfedit.line_text(cat, items), size)

    before = {c: width(c, i) for c, i in lines.items()}

    def item_value(cat: str, item: str) -> float:
        c = canon(item) or item
        if c == "Vue.js":
            return 0       # md: drop first when space is tight
        if cat == "CS Fundamentals":
            return 4       # fresher screens search these
        a2 = c in db.TIER_A2
        if cat in core:
            return 4 if a2 else 5
        return 1 if a2 else 2

    def removable(item: str) -> bool:
        c = canon(item) or item
        return c not in db.PROTECTED and c not in wanted_set

    changelog, no_slot = [], []
    for add in additions:
        skill, text = add["skill"], add["text"]
        if canon(text) and any(canon(i) == canon(text) for v in lines.values() for i in v):
            continue  # already on the resume
        cat = db.CATEGORY_OF.get(skill, db.DEFAULT_CATEGORY)
        if cat not in lines:
            cat = db.DEFAULT_CATEGORY if db.DEFAULT_CATEGORY in lines else next(iter(lines))
        worth = ADD_VALUE.get(add["bucket"], 3)
        trial, dropped = list(lines[cat]), []
        while width(cat, trial + [text]) > avail:
            cands = [i for i in trial if removable(i) and item_value(cat, i) < worth]
            if not cands:
                break
            worst = min(cands, key=lambda i: (item_value(cat, i), -len(i)))
            trial.remove(worst)
            dropped.append(worst)
        if width(cat, trial + [text]) > avail:
            no_slot.append({"skill": skill, "category": cat,
                            "reason": "line full and nothing less valuable to drop"})
            continue
        lines[cat] = trial + [text]
        for d in dropped:
            c = canon(d) or d
            why = ("Vue.js: first to go" if c == "Vue.js" else
                   "A2 (no bullet proves it), not in JD" if c in db.TIER_A2
                   else "not in JD, space needed")
            changelog.append({"action": "removed", "skill": d, "category": cat, "reason": why})
        changelog.append({"action": "added", "skill": text, "category": cat,
                          "reason": f"{add['bucket']} JD keyword"})

    # order inside each line: required -> preferred -> implied -> rest (stable)
    def rank(item: str) -> int:
        return BUCKET_RANK.get(wanted.get(canon(item) or item), 3)
    for cat in lines:
        lines[cat].sort(key=rank)

    # the category with the most Required JD skills goes first (stable otherwise)
    def n_required(cat: str) -> int:
        return sum(wanted.get(canon(i) or i) == "required" for i in lines[cat])
    order = sorted(lines, key=lambda c: -n_required(c))

    return {
        "lines": lines,
        "order": order,
        "skills_section": "\n".join(pdfedit.line_text(c, lines[c]) for c in order),
        "changelog": changelog,
        "no_slot": no_slot,
        "space": {c: {"before": round(before[c], 1), "after": round(width(c, lines[c]), 1),
                      "budget": round(avail, 1)} for c in order},
    }


def compose(kb: dict, variant: str, analysis: dict) -> dict:
    """Preview: plan against the original PDF without writing anything."""
    pdf = ROOT / kb["variants"][variant]["source_file"]
    result = plan(pdfedit.read_skills(pdf), additions_from(analysis),
                  analysis["skills"]["wanted_buckets"], analysis["role_family"])
    result["resume"] = variant
    return result


def apply_to_pdf(pdf_path, additions: list[dict], wanted: dict, role_family: str) -> dict:
    """Plan against `pdf_path` and rewrite its skills lines (edits the file)."""
    current = pdfedit.read_skills(pdf_path)
    result = plan(current, additions, wanted, role_family)
    result["widths"] = pdfedit.write_skills(
        pdf_path, pdf_path, [(c, result["lines"][c]) for c in result["order"]])
    return result
