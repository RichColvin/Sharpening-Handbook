"""The tool groups on the web site's home page (index.html), read as the
book's chapters.

Each group (Beekeeping Tools, Bench Tools, ...) becomes one chapter, in
the home page's order, and its list becomes that chapter's contents:

  - "page":    a tool page, e.g. "Hoes, garden & other" -> GT-Hoe.html
  - "see":     a pointer to another page, e.g. "Loppers - see guidance
               for Secateurs" (kept as HTML, links and all)
  - "label":   a line with no page of its own, e.g. "Single Point
               Cutting Tools" over the lines below it
  - "heading": a sub-group, e.g. "Japanese Gardening Tools"

"See also" lines under an entry are left out; they point to pages the
contents lists anyway.

Created 01 November 2026.
"""

import re
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

SITE_DIR = Path(__file__).resolve().parent.parent


def _own_parts(li):
    """The li's own content - not the lists nested inside it (the home
    page leaves some <li>s unclosed, so later entries can end up inside
    earlier ones)."""
    parts = []
    for child in li.children:
        if getattr(child, "name", None) in ("li", "ul", "ol"):
            break
        if getattr(child, "name", None) == "div":       # the (i) circles
            continue
        parts.append(child)
    return parts


def _entry(li):
    parts = _own_parts(li)
    holder = BeautifulSoup("<span></span>", "html.parser").span
    for part in parts:
        holder.append(BeautifulSoup(str(part), "html.parser"))
    text = " ".join(holder.get_text(" ").split())
    text = re.sub(r"\s+([,)])", r"\1", text).replace("( ", "(")
    links = [a for a in holder.find_all("a", href=True)
             if not a["href"].startswith("Info-")]
    for a in links:
        a["href"] = a["href"].strip().replace("%20", " ")
    if not text or text.lower().startswith("see also"):
        return None
    # "Termite End Grain Tools - see also, Ring Tools": its own page,
    # with a pointer the contents doesn't need.
    see_also = re.search(r"\s*-\s*see also\b", text, re.I)
    if see_also and links and holder.get_text().find(
            links[0].get_text()) < holder.get_text().lower().find("see"):
        return {"kind": "page", "file": links[0]["href"],
                "text": text[:see_also.start()]}
    if re.search(r"\bsee\b", text, re.I):
        return {"kind": "see", "html": _clean_see_html(holder),
                "text": text}
    if not links:
        return {"kind": "label", "text": text}
    return {"kind": "page", "file": links[0]["href"], "text": text}


def _clean_see_html(holder):
    """The "see" line as simple HTML: link targets kept (build_book.py
    turns them into page numbers), the site's styling dropped."""
    for tag in holder.find_all(True):
        if tag.name == "a":
            tag.attrs = {"href": tag["href"]}
        elif tag.name in ("i", "b", "span"):
            tag.unwrap()
    return " ".join(str(holder.decode_contents()).split())


@lru_cache(maxsize=None)
def site_groups():
    """[{"title": ..., "entries": [...]}, ...] in the home page's order."""
    soup = BeautifulSoup((SITE_DIR / "index.html").read_text(
        encoding="utf-8", errors="replace"), "html.parser")
    groups = []
    for element in soup.find_all(True):
        classes = element.get("class") or []
        if element.name == "table" and "catbox" in classes:
            heading = element.find("p", class_="catbox") or element
            title = " ".join(heading.get_text(" ").split())
            title = title.replace("ⓘ", "").strip()     # the (i)
            title = re.sub(r"\s*\(General\)", "", title)
            if groups and title.startswith(groups[-1]["title"]) \
                    and "continued" in title.lower():
                continue                    # same group, next column
            groups.append({"title": title, "entries": []})
        elif not groups:
            continue
        elif element.name == "p" and "TextTableHdrNorm" in classes:
            groups[-1]["entries"].append(
                {"kind": "heading", "text": element.get_text(strip=True)})
        elif element.name == "li":
            entry = _entry(element)
            if entry:
                groups[-1]["entries"].append(entry)
    return groups
