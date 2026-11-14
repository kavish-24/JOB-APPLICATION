"""MCP server (stdio) that edits the TECHNICAL SKILLS section of a resume copy.

Tools
  read_skills_section(pdf_path)           current lines + width limit
  add_skills_to_resume(pdf_path, ...)     put skills into the finite space using
                                          the priority logic in compose.py:
                                          add if there is room, else drop the
                                          least valuable skill, then add.
Only files inside ./output may be edited, so the original resumes are safe.
Nothing may be printed to stdout here (it is the MCP transport).
"""
from pathlib import Path

from mcp.server.mcpserver import MCPServer

import compose
import pdfedit

OUTPUT_DIR = (Path(__file__).parent / "output").resolve()
mcp = MCPServer("resume-editor")


def _safe(pdf_path: str) -> Path:
    p = Path(pdf_path).resolve()
    if OUTPUT_DIR not in p.parents or p.suffix.lower() != ".pdf" or not p.exists():
        raise ValueError(f"Only existing PDFs inside {OUTPUT_DIR} can be edited")
    return p


@mcp.tool()
def read_skills_section(pdf_path: str) -> dict:
    """Return the skills lines of a resume copy and the max width (pt) of a line."""
    cur = pdfedit.read_skills(_safe(pdf_path))
    return {"order": cur["order"], "lines": cur["lines"], "labels": cur["labels"],
            "avail_pt": round(cur["avail"], 1), "font_size": cur["size"],
            "page": cur["section"]["page"], "heading": cur["section"]["heading"]}


@mcp.tool()
def add_skills_to_resume(pdf_path: str, additions: list[dict], wanted: dict,
                         role_family: str, personal: bool = False) -> dict:
    """Add skills to a resume copy, keeping every skills line on one printed line.

    additions:   [{"skill": canonical name, "text": spelling to print,
                   "bucket": "required"|"preferred"|"implied"}] in priority order
    wanted:      {skill: bucket} for every skill the JD wants (never removed)
    role_family: internal skill profile ("ai" | "sde" | "fullstack" | "general")
    personal:    True only for the owner's own resumes (curated tiers apply)
    Edits the file in place and returns the changelog, skills left without a
    slot, and the final line widths."""
    result = compose.apply_to_pdf(_safe(pdf_path), additions, wanted, role_family, personal)
    result.pop("lines", None)
    return result


if __name__ == "__main__":
    mcp.run()
