"""Read and rewrite the TECHNICAL SKILLS lines of a resume PDF in place.

The resume font is Liberation Serif 9pt, which is metric-compatible with the
built-in Times-Roman, so text widths measured here match the real PDF.
"""
import os

import pymupdf

import scan

_FONT = pymupdf.Font("tiro")  # Times-Roman metrics == Liberation Serif


def text_width(text: str, size: float = 9.0) -> float:
    return _FONT.text_length(text, fontsize=size)


def _color(c: int) -> tuple[float, float, float]:
    return ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)


def read_skills(pdf_path) -> dict:
    """Current skills lines + where they sit on the page.

    Returns {order, lines{cat: [items]}, slots[{rect, x0, y}], size, color,
             avail}; avail = widest a line may be (pt) before it leaves the
    right text edge of the page."""
    page = pymupdf.open(pdf_path)[0]
    all_lines, inside, slots, cats = [], False, [], {}
    for block in page.get_text("dict", sort=True)["blocks"]:
        for ln in block.get("lines", []):
            spans = ln["spans"]
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            all_lines.append((text, ln["bbox"][2]))
            if text.startswith("TECHNICAL SKILLS"):
                inside = True
                continue
            if inside and text.isupper() and ":" not in text:  # next heading
                inside = False
            if inside and ":" in text:
                cat, rest = text.split(":", 1)
                cats[cat.strip()] = scan.split_items(rest)
                slots.append({"rect": list(ln["bbox"]), "x0": spans[0]["origin"][0],
                              "y": spans[0]["origin"][1], "size": spans[0]["size"],
                              "color": spans[0]["color"]})
    if not slots:
        raise ValueError("No TECHNICAL SKILLS section found in " + str(pdf_path))
    right = max(x1 for t, x1 in all_lines if len(t) > 100)
    size = slots[0]["size"]
    # the widest existing line is known to fit, so the limit is never below it
    widest = max(text_width(line_text(c, i), size) for c, i in cats.items())
    return {"order": list(cats), "lines": cats, "slots": slots, "size": size,
            "color": slots[0]["color"],
            "avail": max(right - slots[0]["x0"], widest)}


def line_text(cat: str, items: list[str]) -> str:
    return f"{cat}: " + ", ".join(items)


def write_skills(src, dst, ordered: list[tuple[str, list[str]]]) -> list[dict]:
    """Replace the skills lines of `src` with `ordered` [(category, items)] and
    save to `dst`. Each line goes into the next original slot, same font/size/
    colour, and must fit on one line. Returns per-line widths."""
    cur = read_skills(src)
    if len(ordered) != len(cur["slots"]):
        raise ValueError(f"expected {len(cur['slots'])} lines, got {len(ordered)}")
    doc = pymupdf.open(src)
    page = doc[0]
    report = []
    for slot, (cat, items) in zip(cur["slots"], ordered):
        w = text_width(line_text(cat, items), slot["size"])
        if w > cur["avail"] + 0.3:
            raise ValueError(f"'{cat}' line is {w:.1f}pt, limit {cur['avail']:.1f}pt")
        report.append({"category": cat, "width": round(w, 1), "limit": round(cur["avail"], 1)})
    for slot in cur["slots"]:
        x0, y0, x1, y1 = slot["rect"]
        page.add_redact_annot(pymupdf.Rect(x0 - 1, y0 + 1.5, page.rect.width - 10, y1 - 1.5),
                              fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    for slot, (cat, items) in zip(cur["slots"], ordered):
        page.insert_text((slot["x0"], slot["y"]), line_text(cat, items), fontname="tiro",
                         fontsize=slot["size"], color=_color(slot["color"]))
    tmp = f"{dst}.tmp"  # PyMuPDF can't overwrite the file it has open
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, dst)
    return report
