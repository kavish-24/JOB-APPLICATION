"""Find, read and rewrite the skills section of ANY resume PDF.

detect() locates the skills section by its heading ("Skills", "Technical
Skills", "Core Competencies", "Tech Stack", ... or an inline "Skills: a, b"),
then records every line of it: page, baseline, where the text starts (after
any bullet), font style (serif / sans / mono, bold "Category:" prefix), size,
colour, and how wide each line may grow before it leaves its text column.
Lines with or without "Category:" labels and wrapped (multi-line) entries are
supported.

write_skills() redraws ONLY those lines, in place, with the metric-matched
base-14 font of the same style, so the rest of the resume is untouched.
"""
import os
import re
from collections import Counter

import pymupdf


class SectionNotFound(ValueError):
    pass


_SKILL_HEAD = re.compile(
    r"^(?:(?:technical|core|key|relevant|professional|it|software|computer|primary|"
    r"other|additional|my)\s+)*"
    r"(?:skills?|skill\s*sets?|competenc(?:y|ies)|proficienc(?:y|ies)|areas?\s+of\s+expertise|"
    r"expertise|technolog(?:y|ies)|tech(?:nical)?\s+stack|toolkit|tools)"
    r"(?:\s*(?:&|and|/|,)\s*(?:tools|technologies|competencies|expertise|interests|abilities|"
    r"skills|certifications|languages))?"
    r"(?:\s+(?:summary|overview))?$", re.I)
_OTHER_HEAD = re.compile(
    r"^(?:(?:professional|work|relevant|academic|personal|key|career|selected)\s+)*"
    r"(?:summary|profile|objective|about(?:\s+me)?|experience|employment(?:\s+history)?|"
    r"internships?|projects?|education|certifications?|certificates?|achievements?|"
    r"accomplishments|awards?|honou?rs|publications?|interests|hobbies|activities|"
    r"volunteer(?:ing)?|references|courses?|coursework|training|leadership|"
    r"extra[\s-]?curricular(?:\s+activities)?|declaration|contact|details|information|"
    r"positions?\s+of\s+responsibility)"
    r"(?:\s*(?:&|and)\s*\w+(?:\s+\w+)?)?$", re.I)
_BULLET = re.compile(r"^[\s•·▪●◦○■□➢►▸‣⁃✓✔\-–—*]+")
_LABEL = re.compile(r"^([^:]{1,45}):\s*(.*)$")

# base-14 font for (style, bold)
_BASE14 = {("serif", False): "tiro", ("serif", True): "tibo",
           ("sans", False): "helv", ("sans", True): "hebo",
           ("mono", False): "cour", ("mono", True): "cobo"}
_FONTS: dict[str, pymupdf.Font] = {}
_SANS_NAMES = ("sans", "arial", "helvetica", "calibri", "carlito", "verdana", "segoe", "roboto",
               "open", "lato", "inter", "montserrat", "poppins", "nunito", "tahoma", "trebuchet",
               "aptos", "source", "noto", "ubuntu", "raleway", "gill", "futura", "avenir")
_SERIF_NAMES = ("times", "serif", "georgia", "garamond", "cambria", "roman", "book", "minion",
                "palatino", "baskerville", "charter", "caslon", "tiro")


def _font(code: str) -> pymupdf.Font:
    if code not in _FONTS:
        _FONTS[code] = pymupdf.Font(code)
    return _FONTS[code]


def _code(fam: str, bold: bool) -> str:
    return _BASE14[(fam, bool(bold))]


def width(text: str, fam: str = "serif", bold: bool = False, size: float = 9.0) -> float:
    return _font(_code(fam, bold)).text_length(text, fontsize=size)


def text_width(text: str, size: float = 9.0) -> float:   # kept for old callers
    return width(text, "serif", False, size)


def _style(span: dict) -> str:
    n = span["font"].lower()
    if "mono" in n or "courier" in n or "consol" in n or span["flags"] & 8:
        return "mono"
    if any(k in n for k in _SANS_NAMES):
        return "sans"
    if any(k in n for k in _SERIF_NAMES) or span["flags"] & 4:
        return "serif"
    return "sans"


def _bold(span: dict) -> bool:
    n = span["font"].lower()
    return bool(span["flags"] & 16) or any(k in n for k in ("bold", "black", "heavy", "semibold"))


def _color(c: int) -> tuple[float, float, float]:
    return ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)


def split_items(text: str, sep: str = ",") -> list[str]:
    """Split on the separator when not inside parentheses."""
    items, depth, cur = [], 0, ""
    seps = {",", ";", "|", "•", "·"} if sep == "," else {sep.strip()}
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch in seps and depth == 0:
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    items.append(cur.strip())
    return [i.rstrip(".").strip() for i in items if i.strip(" .")]


# ------------------------------------------------------------------ reading
def _lines(page) -> list[dict]:
    """Visual lines of a page (fragments on the same baseline merged)."""
    raw = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        for ln in block.get("lines", []):
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if spans:
                raw.append({"spans": spans, "bbox": list(ln["bbox"]),
                            "y": spans[0]["origin"][1]})
    raw.sort(key=lambda l: (round(l["y"]), l["bbox"][0]))
    merged: list[dict] = []
    for l in raw:
        m = merged[-1] if merged else None
        size = max(s["size"] for s in l["spans"])
        if (m and abs(m["y"] - l["y"]) < 1.5
                and 0 <= l["bbox"][0] - m["bbox"][2] < 2 * size):
            m["spans"] += l["spans"]
            m["bbox"] = [min(m["bbox"][0], l["bbox"][0]), min(m["bbox"][1], l["bbox"][1]),
                         max(m["bbox"][2], l["bbox"][2]), max(m["bbox"][3], l["bbox"][3])]
        else:
            merged.append(l)
    for l in merged:
        l["text"] = "".join(s["text"] for s in l["spans"]).strip()
        l["size"] = max(s["size"] for s in l["spans"])
    return merged


def _body_size(lines: list[dict]) -> float:
    c = Counter()
    for l in lines:
        for s in l["spans"]:
            c[round(s["size"], 1)] += len(s["text"])
    return c.most_common(1)[0][0] if c else 10.0


def _heading_like(l: dict, body: float) -> bool:
    t = l["text"]
    if len(t.split()) > 6 or "," in t or t.endswith("."):
        return False
    letters = sum(ch.isalpha() for ch in t)
    return (all(_bold(s) for s in l["spans"]) or l["size"] >= body + 0.8
            or (t.isupper() and letters >= 3))


def _right_edge(lines: list[dict], x_lo: float, x_hi: float, page_w: float) -> float:
    """Right edge of the text column the skills section sits in."""
    col = [l for l in lines if x_lo <= l["bbox"][0] <= x_hi]
    longs = [l["bbox"][2] for l in col if len(l["text"]) > 60]
    if longs:
        return max(longs)
    left = min((l["bbox"][0] for l in lines), default=36)
    return page_w - left


def _first_text(spans: list[dict], fam_bold) -> tuple[int, float, str]:
    """(index of first text span, x where text starts, bullet text)."""
    s0 = spans[0]
    t0 = s0["text"]
    m = _BULLET.match(t0)
    if m and not t0[m.end():].strip() and len(spans) > 1:     # bullet is its own span
        return 1, spans[1]["origin"][0], t0.strip()
    if m and m.group(0).strip():                               # bullet inside the span
        fam, bold = fam_bold(s0)
        return 0, s0["origin"][0] + width(m.group(0), fam, bold, s0["size"]), m.group(0).strip()
    lead = len(t0) - len(t0.lstrip())
    fam, bold = fam_bold(s0)
    return 0, s0["origin"][0] + width(t0[:lead], fam, bold, s0["size"]), ""


def _sep_of(text: str) -> str:
    for sep in (" | ", " • ", " · ", "; "):
        if sep in text:
            return sep
    return ", "


def _parse(lines, start, heading, body, page) -> tuple[list[dict], list[int]]:
    ref_x = heading["bbox"][0] if heading else lines[start]["bbox"][0]
    x_lo, x_hi = ref_x - 20, ref_x + 150
    right = _right_edge(lines, x_lo, x_hi, page.rect.width)
    head_size = heading["size"] if heading else body + 1
    line_h = body * 1.3
    prev_bottom = heading["bbox"][3] if heading else None
    entries: list[dict] = []
    used: list[int] = []
    fam_bold = lambda s: (_style(s), _bold(s))

    for idx in range(start, len(lines)):
        l = lines[idx]
        x0, y0, x1, y1 = l["bbox"]
        if not (x_lo <= x0 <= x_hi):
            continue                      # another column
        if prev_bottom is not None and y0 - prev_bottom > 2.6 * line_h:
            break                         # big vertical gap: section over
        clean = _BULLET.sub("", l["text"]).strip()
        if not clean:
            continue                      # a bullet drawn as its own text ("●")
        head = clean.rstrip(":").strip()
        is_head = ":" not in head and "," not in head and len(head.split()) <= 6
        if is_head and (_OTHER_HEAD.match(head) or (_SKILL_HEAD.match(head) and idx != start)
                        or (_heading_like(l, body) and l["size"] >= head_size - 0.3)):
            break                         # next section heading
        prev_bottom = y1
        if is_head and _heading_like(l, body):
            continue                      # a sub-label line ("Programming"): leave it alone

        spans = l["spans"]
        k, text_x, bullet = _first_text(spans, fam_bold)
        tspans = spans[k:]
        item_span = tspans[-1]
        fam = _style(item_span)
        m = _LABEL.match(clean)
        label = m.group(1).strip() if m and len(m.group(1).split()) <= 5 else None
        slot = {"x": round(text_x, 2), "y": round(l["y"], 2), "x1": round(x1, 2),
                "rect": [round(v, 2) for v in l["bbox"]], "size": round(item_span["size"], 2),
                "color": item_span["color"], "text": l["text"]}

        prev = entries[-1] if entries else None
        wrapped = (prev is not None and label is None and not bullet
                   and (text_x > prev["slots"][0]["x"] + 2
                        or prev["slots"][-1]["x1"] > right - 0.2 * (right - ref_x)))
        if wrapped:
            prev["slots"].append(slot)
            prev["raw"] += " " + clean
        else:
            bold_prefix = False
            if label:
                acc, label_spans = "", []
                for s in tspans:
                    label_spans.append(s)
                    acc += s["text"]
                    if ":" in acc:
                        break
                rest = tspans[len(label_spans):]
                bold_prefix = all(_bold(s) for s in label_spans) and (
                    not rest or not all(_bold(s) for s in rest))
            entries.append({"label": label, "raw": m.group(2) if label else clean,
                            "slots": [slot], "fam": fam, "bold_prefix": bold_prefix,
                            "bold_items": _bold(item_span) and not bold_prefix,
                            "size": slot["size"], "color": slot["color"],
                            "bullet": bullet})
        used.append(idx)

    # another column beside the section (two-column resumes) caps the width
    if entries:
        top = min(s["rect"][1] for e in entries for s in e["slots"])
        bottom = max(s["rect"][3] for e in entries for s in e["slots"])
        beside = [l["bbox"][0] for l in lines
                  if l["bbox"][0] > x_hi and l["bbox"][1] < bottom and l["bbox"][3] > top]
        if beside:
            right = min(right, min(beside) - 10)

    # finish entries: items, separator, keys, per-slot width limits
    seen: set[str] = set()
    for n, e in enumerate(entries, 1):
        e["sep"] = _sep_of(e["raw"])
        e["items"] = split_items(e["raw"], e["sep"].strip() if e["sep"] != ", " else ",")
        key = e["label"] or ("Skills" if len(entries) == 1 else f"Line {n}")
        while key in seen:
            key += " (2)"
        seen.add(key)
        e["key"] = key
        for i, s in enumerate(e["slots"]):
            # never below what the line already uses (measured with our font)
            needed = _measure_slot(e, i, s["text"])
            s["avail"] = round(max(right - s["x"], needed), 2)
        del e["raw"]
    return [e for e in entries if e["items"] or e["label"]], used


def _measure_slot(e: dict, i: int, line_text_: str) -> float:
    t = _BULLET.sub("", line_text_).strip()
    if i == 0 and e["label"]:
        m = _LABEL.match(t)
        body = m.group(2) if m else t
        return (width(e["label"] + ": ", e["fam"], e["bold_prefix"], e["size"])
                + width(body, e["fam"], e["bold_items"], e["size"]))
    return width(t, e["fam"], e["bold_items"], e["size"])


def detect(pdf_path) -> dict:
    """Locate the skills section. Raises SectionNotFound."""
    doc = pymupdf.open(pdf_path)
    try:
        for pno, page in enumerate(doc):
            lines = _lines(page)
            body = _body_size(lines)
            for i, l in enumerate(lines):
                clean = _BULLET.sub("", l["text"]).strip()
                head = clean.rstrip(":").strip()
                if ":" not in head and len(head.split()) <= 6 and _SKILL_HEAD.match(head):
                    start, heading, how = i + 1, l, "heading"
                else:
                    m = _LABEL.match(clean)
                    if not (m and m.group(2).strip() and _SKILL_HEAD.match(m.group(1).strip())):
                        continue
                    start, heading, how = i, None, "inline"
                entries, used = _parse(lines, start, heading, body, page)
                if any(e["items"] for e in entries):
                    reorderable = (all(len(e["slots"]) == 1 for e in entries)
                                   and len({round(e["slots"][0]["x"]) for e in entries}) == 1)
                    if reorderable:   # lines can swap slots: give them one shared limit
                        shared = max(e["slots"][0]["avail"] for e in entries)
                        for e in entries:
                            e["slots"][0]["avail"] = shared
                    bottom = max(s["rect"][3] for e in entries for s in e["slots"])
                    top = heading["bbox"][1] if heading else entries[0]["slots"][0]["rect"][1]
                    return {"page": pno, "found_by": how,
                            "heading": heading["text"] if heading else None,
                            "region": [round(lines[i]["bbox"][0], 2), round(top, 2),
                                       round(page.rect.width, 2), round(bottom, 2)],
                            "right": round(max(s["x"] + s["avail"] for e in entries
                                               for s in e["slots"]), 2),
                            "reorderable": reorderable, "entries": entries}
        raise SectionNotFound(
            "No skills section found. The resume needs a heading such as 'Skills', "
            "'Technical Skills' or 'Core Competencies' followed by the skills as text "
            "(e.g. 'Languages: Python, Java' or 'Python, Java, SQL').")
    finally:
        doc.close()


def body_text(pdf_path, section: dict | None = None) -> str:
    """All resume text EXCEPT the skills section (experience, projects, ...)."""
    section = section or detect(pdf_path)
    x0, top, x1, bottom = section["region"]
    doc = pymupdf.open(pdf_path)
    try:
        out = []
        for pno, page in enumerate(doc):
            for l in _lines(page):
                bx0, by0, _, by1 = l["bbox"]
                inside = (pno == section["page"] and by0 >= top - 1 and by1 <= bottom + 1
                          and x0 - 20 <= bx0 <= x1)
                if not inside:
                    out.append(l["text"])
        return "\n".join(out)
    finally:
        doc.close()


def header_info(pdf_path) -> dict:
    """Candidate name (largest text near the top of page 1) and contact line
    (first line up top with an email, phone or link)."""
    doc = pymupdf.open(pdf_path)
    try:
        lines = [l for l in _lines(doc[0]) if l["bbox"][1] < 160]
    finally:
        doc.close()
    if not lines:
        return {"name": "", "contact": ""}
    name_line = max(lines[:6], key=lambda l: l["size"])
    contact = next((l["text"] for l in lines if l is not name_line and re.search(
        r"@|\+?\d[\d\s-]{7,}|linkedin|github|\.com", l["text"], re.I)), "")
    return {"name": name_line["text"].strip(), "contact": contact.strip()}


def read_skills(pdf_path) -> dict:
    """Current skills lines + layout, keyed by entry key (label or 'Line n')."""
    sec = detect(pdf_path)
    es = sec["entries"]
    return {"section": sec, "order": [e["key"] for e in es],
            "lines": {e["key"]: list(e["items"]) for e in es},
            "labels": {e["key"]: e["label"] for e in es},
            "size": es[0]["size"], "color": es[0]["color"],
            "avail": max(s["avail"] for e in es for s in e["slots"]),
            "reorderable": sec["reorderable"]}


# ------------------------------------------------------------------ layout
def _entry(section: dict, key: str) -> dict:
    return next(e for e in section["entries"] if e["key"] == key)


def wrap(e: dict, items: list[str], label: str | None = "__same__") -> list[str] | None:
    """Lay items out over the entry's slots; None if they do not fit."""
    label = e["label"] if label == "__same__" else label
    words = e["sep"].join(items).split(" ") if items else []
    out, i = [], 0
    for k, slot in enumerate(e["slots"]):
        avail = slot["avail"]
        if k == 0 and label:
            avail -= width(label + ": ", e["fam"], e["bold_prefix"], e["size"])
        line = ""
        while i < len(words):
            cand = f"{line} {words[i]}" if line else words[i]
            if width(cand, e["fam"], e["bold_items"], e["size"]) <= avail + 0.3:
                line, i = cand, i + 1
            else:
                break
        out.append(line)
        if i == len(words):
            break
    return out if i == len(words) else None


def fits(section: dict, key: str, items: list[str]) -> bool:
    return wrap(_entry(section, key), items) is not None


def usage(section: dict, key: str, items: list[str]) -> tuple[float, float]:
    """(points of text, points available) for an entry."""
    e = _entry(section, key)
    used = width(line_text(e["label"], items, e["sep"]), e["fam"], e["bold_items"], e["size"])
    return used, sum(s["avail"] for s in e["slots"])


def line_text(label: str | None, items: list[str], sep: str = ", ") -> str:
    body = sep.join(items)
    return f"{label}: {body}" if label else body


# ------------------------------------------------------------------ writing
def write_skills(src, dst, ordered: list[tuple[str, list[str]]]) -> list[dict]:
    """Rewrite the skills section of `src` with `ordered` [(key, items)] and save
    to `dst`. Entries keep their own slots, except when every entry is a single
    line in one column: then the order of `ordered` is applied."""
    sec = detect(src)
    entries = sec["entries"]
    by_key = {e["key"]: e for e in entries}
    keys = [k for k, _ in ordered]
    if sorted(keys) != sorted(by_key):
        raise ValueError(f"expected entries {sorted(by_key)}, got {sorted(keys)}")
    content = dict(ordered)
    placement = list(zip(entries, keys)) if sec["reorderable"] else [(e, e["key"]) for e in entries]

    plans, report = [], []
    for host, key in placement:
        label = by_key[key]["label"]
        lines = wrap(host, content[key], label)
        if lines is None:
            raise ValueError(f"'{key}' does not fit in its {len(host['slots'])} line(s)")
        plans.append((host, label, lines))
        report.append({"category": key, "lines_used": len(lines), "lines": len(host["slots"])})

    doc = pymupdf.open(src)
    page = doc[sec["page"]]
    for host, _, _ in plans:
        for s in host["slots"]:
            x0, y0, x1, y1 = s["rect"]
            page.add_redact_annot(pymupdf.Rect(s["x"] - 0.5, y0 + 1.5,
                                               max(x1, s["x"] + s["avail"]) + 1, y1 - 1.5),
                                  fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                          graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    for host, label, lines in plans:
        color = _color(host["color"])
        for k, (s, text) in enumerate(zip(host["slots"], lines)):
            x = s["x"]
            if k == 0 and label:
                pre = label + ": "
                page.insert_text((x, s["y"]), pre, fontname=_code(host["fam"], host["bold_prefix"]),
                                 fontsize=host["size"], color=color)
                x += width(pre, host["fam"], host["bold_prefix"], host["size"])
            if text:
                page.insert_text((x, s["y"]), text, fontname=_code(host["fam"], host["bold_items"]),
                                 fontsize=host["size"], color=color)
    tmp = f"{dst}.tmp"  # PyMuPDF can't overwrite the file it has open
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, dst)
    return report
