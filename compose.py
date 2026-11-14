"""Plan the new TECHNICAL SKILLS section: add skills into the finite space.

Rules (resume_skills_crafter.md, steps 3-5):
  * Space is fixed: every line must still fit on ONE printed line. Widths are
    measured in points against the real PDF (pdfedit).
  * A suggested skill goes on its own category line if there is room.
  * No room -> drop the least valuable skill on that line until it fits, but an
    addition may only displace something worth LESS than itself:
        value of an addition : required 10, preferred 4.5, implied 4.2,
                               plus up to +2 for JD emphasis (in title, repeated,
                               mandatory heading, ATS hint); +0.6 if already
                               proven in a bullet (Tier A3)
        value of a resume item (owner's resumes): Vue.js 0 | off-role A2 1 |
                                off-role A1 2 | on-role A2 4 | on-role A1 5 |
                                CS fundamentals 4
        (anyone else's resume): proven in experience/projects 5, else 3
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
ADD_VALUE = {"required": 10, "preferred": 4.5, "implied": 4.2}
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
    meta = {m["skill"]: m for m in analysis["skills"]["missing"]}
    sug = analysis["suggested_additions"]
    names = list(sug["free_a3"]) + [t["skill"] for t in sug["tier_b"]]
    def spelled(s: str) -> str:
        """JD's own wording, but proper casing when it only differs in case."""
        jd = meta.get(s, {}).get("jd_spelling") or s
        return s if jd.lower() == s.lower() else jd

    adds = [{"skill": s, "text": spelled(s),
             "bucket": buckets.get(s, "implied"),
             # JD emphasis (title, repetition, mandatory, ATS hint) raises its worth
             "bonus": min(2.0, meta.get(s, {}).get("emphasis", 0.0))
                      + (0.6 if meta.get(s, {}).get("tier") == "A3" else 0.0),  # proven = no risk
             "tier": meta.get(s, {}).get("tier", "")}
            for s in names]
    adds.sort(key=lambda a: -(ADD_VALUE.get(a["bucket"], 3) + a["bonus"]))
    return adds


def additions_for(analysis: dict, selected: list[str]) -> list[dict]:
    """Only the skills the user ticked in the picker, best first. A user pick
    gets +1 worth so it can displace a slightly more valuable resume item."""
    cats = analysis["categories"]
    pool = {i["skill"]: i for i in cats["must_add"] + cats["might_add"]}
    adds = []
    for s in dict.fromkeys(selected):
        i = pool.get(s)
        if i is None:
            continue
        adds.append({"skill": s, "text": i["text"], "bucket": i["bucket"], "tier": i["tier"],
                     "bonus": min(2.0, i.get("emphasis") or 0.0)
                              + (0.6 if i["tier"] == "A3" else 0.0) + 1.0})
    adds.sort(key=lambda a: -(ADD_VALUE.get(a["bucket"], 3) + a["bonus"]))
    return adds


_TOKEN_ALIASES = {"ml": "ai", "devops": "tools", "tool": "tools", "fundamental": "fundamentals",
                  "database": "databases", "db": "databases", "language": "languages",
                  "programming": "languages", "front": "frontend", "back": "backend",
                  "mobile": "frontend", "web": "frontend", "cloud": "tools",
                  "framework": "frameworks"}


def _tokens(name: str) -> set[str]:
    return {_TOKEN_ALIASES.get(t, t) for t in re.findall(r"[a-z]+", (name or "").lower())}


def choose_line(skill: str, lines: dict, labels: dict) -> str:
    """Resume line a new skill goes on, for ANY resume's own line names:
    1. a line whose name matches the skill's group (Databases, Tools, ...),
    2. the line already holding most skills of that group,
    3. a catch-all line (Tools / Other / Technologies),
    4. the last line."""
    group = db.CATEGORY_OF.get(skill, db.DEFAULT_CATEGORY)
    if group in lines:
        return group
    gt = _tokens(group)
    for key in lines:
        if gt & _tokens(labels.get(key) or ""):
            return key
    counts = {k: sum(db.CATEGORY_OF.get(canon(i) or i) == group for i in items)
              for k, items in lines.items()}
    best = max(counts, key=counts.get) if counts else None
    if best and counts[best] > 0:
        return best
    for key in lines:
        if _tokens(labels.get(key) or "") & {"tools", "other", "technologies", "misc", "additional"}:
            return key
    return list(lines)[-1]


def plan(current: dict, additions: list[dict], wanted: dict, role_family: str,
         personal: bool = True, body: str = "") -> dict:
    """current = pdfedit.read_skills(); wanted = {skill: bucket} for the JD.
    personal = the owner's curated resume tiers apply; otherwise an item is
    worth more when the resume's own experience/project text proves it."""
    sec = current["section"]
    lines = {cat: list(items) for cat, items in current["lines"].items()}
    labels = current["labels"]
    wanted_set = set(wanted)
    core = CORE_LINES.get(role_family, set())

    def fits(cat: str, items: list[str]) -> bool:
        return pdfedit.fits(sec, cat, items)

    before = {c: pdfedit.usage(sec, c, i) for c, i in lines.items()}

    def in_body(item: str) -> bool:
        c = canon(item)
        rxs = [rx for cc, _, rx in analyze._SPELLINGS if cc == c] if c else [analyze._regex(item)]
        return any(rx.search(body) for rx in rxs)

    def item_value(cat: str, item: str) -> float:
        c = canon(item) or item
        if not personal:
            return 5 if in_body(item) else 3      # proven elsewhere on the resume > listed only
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
        on_resume = [i for v in lines.values() for i in v]
        if (canon(text) and any(canon(i) == canon(text) for i in on_resume)) or \
                text.lower() in {i.lower() for i in on_resume}:
            continue  # already on the resume
        cat = choose_line(skill, lines, labels)
        worth = ADD_VALUE.get(add["bucket"], 3) + add.get("bonus", 0)
        trial, dropped = list(lines[cat]), []
        while not fits(cat, trial + [text]):
            cands = [i for i in trial if removable(i) and item_value(cat, i) < worth]
            if not cands:
                break
            worst = min(cands, key=lambda i: (item_value(cat, i), -len(i)))
            trial.remove(worst)
            dropped.append(worst)
        if not fits(cat, trial + [text]):
            no_slot.append({"skill": skill, "category": cat,
                            "reason": "line full and nothing less valuable to drop"})
            continue
        lines[cat] = trial + [text]
        for d in dropped:
            c = canon(d) or d
            if not personal:
                why = "not proven elsewhere on the resume, not in JD"
            else:
                why = ("Vue.js: first to go" if c == "Vue.js" else
                       "A2 (no bullet proves it), not in JD" if c in db.TIER_A2
                       else "not in JD, space needed")
            changelog.append({"action": "removed", "skill": d, "category": cat, "reason": why})
        changelog.append({"action": "added", "skill": text, "category": cat,
                          "reason": f"{add['bucket']} JD keyword" + (
                              " (unverified: check you can speak to it)"
                              if add.get("tier") == "unverified" else "")})

    # order inside each line: required -> preferred -> implied -> rest (stable)
    def rank(item: str) -> int:
        return BUCKET_RANK.get(wanted.get(canon(item) or item), 3)
    for cat in lines:
        lines[cat].sort(key=rank)

    # the line with the most Required JD skills goes first, when the layout
    # allows moving lines (all single-line, one column)
    def n_required(cat: str) -> int:
        return sum(wanted.get(canon(i) or i) == "required" for i in lines[cat])
    order = sorted(lines, key=lambda c: -n_required(c)) if current["reorderable"] else list(lines)
    seps = {e["key"]: e["sep"] for e in sec["entries"]}

    def space(c: str) -> dict:
        used, budget = pdfedit.usage(sec, c, lines[c])
        return {"before": round(before[c][0], 1), "after": round(used, 1), "budget": round(budget, 1)}

    return {
        "lines": lines,
        "labels": labels,
        "order": order,
        "skills_section": "\n".join(pdfedit.line_text(labels[c], lines[c], seps[c]) for c in order),
        "changelog": changelog,
        "no_slot": no_slot,
        "space": {c: space(c) for c in order},
    }


def compose(kb: dict, variant: str, analysis: dict) -> dict:
    """Preview: plan against the original PDF without writing anything."""
    v = kb["variants"][variant]
    pdf = ROOT / v["source_file"]
    result = plan(pdfedit.read_skills(pdf), additions_from(analysis),
                  analysis["skills"]["wanted_buckets"], analysis["role_family"],
                  v.get("personal", False), v.get("body_text", ""))
    result["resume"] = variant
    return result


def apply_to_pdf(pdf_path, additions: list[dict], wanted: dict, role_family: str,
                 personal: bool = True) -> dict:
    """Plan against `pdf_path` and rewrite its skills lines (edits the file)."""
    current = pdfedit.read_skills(pdf_path)
    body = pdfedit.body_text(pdf_path, current["section"])
    result = plan(current, additions, wanted, role_family, personal, body)
    result["widths"] = pdfedit.write_skills(
        pdf_path, pdf_path, [(c, result["lines"][c]) for c in result["order"]])
    return result
