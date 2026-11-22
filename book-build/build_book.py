"""Build the printed (PDF) Sharpening Handbook from the web pages.

The web pages stay the only copy that's edited.  This reads them, makes
the changes a printed page needs, and prints each chapter to PDF with
Google Chrome:

  - the site header, footer and standard includes are dropped;
  - a shared section (e.g. include-GT-OngoingMaintenance.html) is
    replaced by a note pointing to its chapter;
  - links to other handbook pages become "(see Chapter N)";
  - links to other web sites keep their wording but lose the link (in a
    list, such as further reading, the site's address is printed after
    it); links to videos are marked for rewording - see edits.py.

Everything changed is listed in out/Review-ChNN.md for checking.

Usage (from the repository's top folder):
    book-build/.venv/bin/python book-build/build_book.py              # BUILD_BY_DEFAULT
    book-build/.venv/bin/python book-build/build_book.py 5 9          # Chapters 5 and 9
    book-build/.venv/bin/python book-build/build_book.py --final      # no highlights
    book-build/.venv/bin/python book-build/build_book.py --single-sided

Output: book-build/out/Letter/*.pdf and book-build/out/A4/*.pdf.  To
publish them, copy them to the web site's Book/Letter and Book/A4 folders
(the download page, indexPrintableBook.html, links there).

Created 01 November 2026.
"""

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment
from pypdf import PdfReader

BOOK_DIR = Path(__file__).resolve().parent
SITE_DIR = BOOK_DIR.parent
OUT_DIR = BOOK_DIR / "out"
sys.path.insert(0, str(BOOK_DIR))

from chapters import (BUILD_BY_DEFAULT, CHAPTERS, DEFAULT_REVISED,  # noqa: E402
                      EXCLUDED_PAGES, KEEP_TABLE_NOTES, BREAKABLE_TABLES, WRAP_MOVED_NOTES,
                      ROW_PICTURES, SHORT_TORMEK_VIDEOS,
                      EDITION, GROUP_FIRST_CHAPTER, PLANNED_CHAPTER)
from site_index import site_groups  # noqa: E402
from edits import EDITS  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAPER = {"Letter": "letter", "A4": "A4"}
PAPER_HEIGHT = {"Letter": 11.0, "A4": 11.69}     # inches

# Must match .sheet's zoom in book.css: the title page's height is given
# in the zoomed (scaled) inches.
SHEET_ZOOM = 0.90

# Hole side (inside) and other margins, in inches.
MARGIN_INSIDE = 1.0
MARGIN_OUTSIDE = 0.6
MARGIN_TOP = 0.6
MARGIN_BOTTOM = 0.75

MATHJAX = ("<script>window.MathJax = {tex: {inlineMath: [['\\\\(', "
           "'\\\\)']]}};</script>\n<script src=\"https://cdn.jsdelivr.net/"
           "npm/mathjax@3.2.2/es5/tex-chtml.js\"></script>")

VIDEO_SITES = ("youtube.com", "youtu.be", "vimeo.com")

# Includes that are part of every page's furniture, not its content.
DROPPED_INCLUDES = {
    "include-SiteStandards.html",
    "include-Header.html",
    "include-Footer.html",
    "include-FooterMin.html",
    "include-Horizontal-Rules.html",
}

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=Cinzel:wght@400;700"
         "&family=Cormorant+Garamond:ital,wght@0,400;0,700;1,400"
         "&family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400"
         "&family=Merienda:wght@400;700"
         "&family=Bona+Nova:ital,wght@0,400;0,700;1,400"
         "&display=swap")


# ---------------------------------------------------------------------
# Where each page and shared section lives in the book
# ---------------------------------------------------------------------
_all_chapters = None


def all_chapters():
    """Every chapter, in order: those set out in chapters.py, then one per
    home-page group (numbered from GROUP_FIRST_CHAPTER), with any
    settings chapters.py gives them.  A page listed in more than one
    group is printed in the first; the others' contents point to it."""
    global _all_chapters
    if _all_chapters is not None:
        return _all_chapters
    settings = {c["number"]: c for c in CHAPTERS}
    chapters = [dict({"revised": DEFAULT_REVISED, "pages": []}, **c)
                for c in CHAPTERS
                if "sections" in c or "pages" in c or "web_only" in c]
    printed = {page for c in chapters
               for page in c["pages"] + c.get("web_only", [])}
    printed |= set(PLANNED_CHAPTER)     # covered by a chapter, not printed
    for i, group in enumerate(site_groups()):
        number = GROUP_FIRST_CHAPTER + i
        contents = []
        for entry in group["entries"]:
            page = entry.get("file")
            if page in EXCLUDED_PAGES:
                continue
            if entry["kind"] == "page" and is_external(page):
                # e.g. Science of Sharp: a web site, not a page
                text = re.sub(r"\s*\(link to that web site\)", "",
                              entry["text"])
                entry = {"kind": "label",
                         "text": f"{text} (web site: {site_name(page)})"}
            contents.append(entry)
        chapter = {"number": number, "title": group["title"],
                   "revised": DEFAULT_REVISED, "contents": contents}
        chapter.update(settings.get(number, {}))
        chapter["pages"] = []
        for entry in contents:
            page = entry.get("file")
            if entry["kind"] == "page" and page not in printed:
                printed.add(page)
                chapter["pages"].append(page)
        chapters.append(chapter)
    _all_chapters = sorted(chapters, key=lambda c: c["number"])
    return _all_chapters


def page_chapter_map():
    where = dict(PLANNED_CHAPTER)
    for chapter in all_chapters():
        for page in chapter.get("pages", []) + chapter.get("web_only", []):
            where[page] = chapter["number"]
    return where


def include_section_map():
    """include file -> (chapter number, section title)."""
    sections = {}
    for chapter in all_chapters():
        for section in chapter.get("sections", []):
            for include in ([section["include"]] if "include" in section
                            else []) + section.get("also", []):
                sections[include] = (chapter["number"], section["title"])
    return sections


def section_by_title(title):
    """(chapter number, section title) for a section named in chapters.py."""
    for chapter in all_chapters():
        for section in chapter.get("sections", []):
            if section["title"] == title:
                return chapter["number"], title
    sys.exit(f"chapters.py names a section \"{title}\" that isn't listed")


def page_extracts(filename):
    """Sections taken from part of this page: (from, to, number, title)."""
    return [(s["from"], s["to"], chapter["number"], s["title"])
            for chapter in all_chapters() for s in chapter.get("sections", [])
            if s.get("page") == filename]


_title_cache = {}


def apply_edits(filename, text, review=None):
    """edits.py's changes for this page; each is (text or regular
    expression, replacement)."""
    for old, new in EDITS.get(filename, []):
        label = old.pattern if hasattr(old, "pattern") else old
        if hasattr(old, "pattern"):
            text, found = old.subn(new, text)
        else:
            found = old in text
            text = text.replace(old, new)
        if review is None:
            continue
        if found:
            review.add(filename, "Reworded (edits.py)",
                       f"{short(label)} -> "
                       f"{'(rearranged)' if callable(new) else short(new) or '(removed)'}")
        else:
            review.add(filename, "PROBLEM - edits.py text not found",
                       short(label))
    return text


def page_title(filename):
    """The title a page shows under the site header."""
    if filename in _title_cache:
        return _title_cache[filename]
    title = Path(filename).stem
    path = SITE_DIR / filename
    if path.exists():
        text = apply_edits(filename, path.read_text(encoding="utf-8",
                                                    errors="replace"))
        soup = BeautifulSoup(text, "html.parser")
        heading = soup.find("p", style=re.compile("Bona Nova"))
        if heading and heading.get_text(strip=True):
            title = " ".join(heading.get_text().split())
    _title_cache[filename] = title
    return title


# ---------------------------------------------------------------------
# Turning one web page into book content
# ---------------------------------------------------------------------
class Review:
    """What the build changed on each page, for out/Review-ChNN.md."""

    def __init__(self):
        self.items = {}

    def add(self, page, kind, text):
        self.items.setdefault(page, []).append((kind, text))


def load_source(source, review, end_notes, cuts=(), common_title=None):
    """The page (or, for a section taken from part of a page, that part)
    as parsed HTML, with edits.py applied.  A part of the page printed
    as a section elsewhere is cut out, and end_notes points to it."""
    filename = source if isinstance(source, str) else source["page"]
    text = (SITE_DIR / filename).read_text(encoding="utf-8",
                                           errors="replace")
    text = apply_edits(filename, text, review)
    if isinstance(source, str) and cuts:
        # Not every page has every part (e.g. Newer Sharpening Tools).
        found = 0
        for cut in cuts:
            text, n = re.subn(cut, "", text, flags=re.S)
            found += n
        if found and common_title:
            end_notes.append(f'<b>{html.escape(common_title)}</b> - at the '
                             f'start of this chapter.')
    # "60°<br>to<br>75°" / "40°<br>-<br>45°" on one line: "60° - 75°".
    text = re.sub(r"(&deg;\s*(?:</b>)?)\s*<br>\s*(?:to|-)\s*<br>\s*",
                  r"\1 - ", text)
    text = close_table_cells(text)
    # "<h4>Purchasing Tools</h3>": a heading closed with the wrong tag
    # swallows everything after it, so each gets its own closing tag.
    text = re.sub(r"<h([1-6])(\b[^>]*)>(.*?)</h[1-6]>",
                  r"<h\1\2>\3</h\1>", text, flags=re.S | re.I)
    if isinstance(source, dict):
        start, end = find_span(text, source["from"], source["to"], filename)
        return BeautifulSoup(text[start:end], "html.parser")
    for start_text, end_text, number, title in page_extracts(filename):
        start, end = find_span(text, start_text, end_text, filename)
        text = text[:start] + text[end:]
        end_notes.append(f'<b>Ongoing maintenance</b> - see Chapter '
                         f'{number}, <i>{html.escape(title)}</i>.')
        review.add(filename, "Section moved to its own chapter",
                   f"its maintenance text -> Chapter {number}, {title}")
    return BeautifulSoup(text, "html.parser")


CELL_TAG = re.compile(r"<(/?)(table|tr|td|th)\b[^>]*>", re.I)


def close_table_cells(text):
    """Close table cells the site leaves open ("<td>...<td>"), as a
    browser does: otherwise the HTML reader nests the next cells inside
    the open one, and a row's cells land in the wrong columns."""
    out, last = [], 0
    open_cell = [None]          # per table level: open cell tag or None
    for match in CELL_TAG.finditer(text):
        closing, tag = match.group(1), match.group(2).lower()
        insert = ""
        if tag == "table" and not closing:
            open_cell.append(None)
        elif tag in ("td", "th") and closing:
            # "<td ...> ... </th>": close what was opened.
            if open_cell[-1] and open_cell[-1] != tag:
                out.append(text[last:match.start()] + f"</{open_cell[-1]}>")
                last = match.end()
                open_cell[-1] = None
                continue
            open_cell[-1] = None
        elif open_cell[-1] and (tag in ("td", "th", "tr")
                                or tag == "table" and closing):
            insert = f"</{open_cell[-1]}>"
            open_cell[-1] = None
        if tag in ("td", "th") and not closing:
            open_cell[-1] = tag
        if tag == "table" and closing and len(open_cell) > 1:
            open_cell.pop()
        out.append(text[last:match.start()] + insert + match.group(0))
        last = match.end()
    out.append(text[last:])
    return "".join(out)


def find_span(text, start_text, end_text, filename):
    start = text.find(start_text)
    end = text.find(end_text, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        sys.exit(f"chapters.py: can't find \"{start_text}\" ... "
                 f"\"{end_text}\" in {filename}")
    return start, end


def short(text, length=110):
    text = " ".join(BeautifulSoup(text, "html.parser").get_text().split())
    return text if len(text) <= length else text[:length - 3] + "..."


def strip_web_furniture(root):
    for comment in root.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in root.find_all(["script", "link", "meta", "title", "head"]):
        tag.decompose()
    for div in root.find_all("div", style=re.compile(r"position:\s*sticky")):
        div.decompose()
    # "Click to read more" under the sharpness-scale picture.
    # "Click to read more", "Click on either image for a bigger sized
    # view." - captions for the web page's links.
    for p in root.find_all("p"):
        words = p.get_text(" ", strip=True).lower()
        if words == "click to read more" or re.match(
                r"\(?(you can )?click on (the|either|any of the) "
                r"(gray|grey|image|picture)", words) and len(words) < 80:
            p.decompose()
    # Quote boxes: no blank line below the author's name.
    for quote in root.find_all("p", style=re.compile("Merienda")):
        author = quote.find("p") or quote.find_next_sibling("p")
        for p in [quote] + ([author] if author else []):
            p["style"] = (p.get("style", "").rstrip("; ") +
                          "; margin-bottom: 0;")
    # Embedded (YouTube) video players print as an empty box.
    for frame in root.find_all("iframe"):
        frame.decompose()
    # "Index" boxes of links to places on the same page - for getting
    # around the web page, not needed on paper.
    for box in root.find_all("div"):
        if box.decomposed:
            continue
        first = box.find(["b", "strong"])
        links = box.find_all("a", href=True)
        if (first and first.get_text(strip=True) == "Index" and links
                and all(a["href"].startswith("#") for a in links)
                and len(box.get_text(strip=True)) < 1500):
            box.decompose()


def replace_includes(root, filename, review, sections, end_notes,
                     maintenance=None):
    """maintenance: the chapter's own maintenance section, (number,
    title), which its pages point to instead of the include they use."""
    for div in root.find_all(attrs={"w3-include-html": True}):
        include = div["w3-include-html"]
        if include in DROPPED_INCLUDES:
            div.decompose()
        elif include in sections:
            number, title = maintenance or sections[include]
            end_notes.append(f'<b>Ongoing maintenance</b> - see Chapter '
                             f'{number}, <i>{html.escape(title)}</i>.')
            div.decompose()
            review.add(filename, "Shared section replaced by a note",
                       f"{include} -> Chapter {number}, {title}")
        else:
            div.decompose()
            review.add(filename, "PROBLEM - include not in the book",
                       f"{include} was left out; add it to chapters.py")


def is_video(url):
    host = urlparse(url).netloc.lower()
    return any(host == site or host.endswith("." + site)
               for site in VIDEO_SITES)


def is_external(href):
    parsed = urlparse(href)
    if parsed.scheme in ("http", "https", "mailto"):
        return True
    # A few links leave out https:// (e.g. "crocus.co.uk").
    return not parsed.scheme and not href.split("?")[0].endswith(".html") \
        and "." in href.split("/")[0] and not href.startswith("#")


def site_name(href):
    host = urlparse(href if "//" in href else "https://" + href).netloc
    return host.lower().removeprefix("www.")


def fix_links(root, filename, chapter_number, review, where, final,
              end_notes):
    referenced = set()

    # Every tool page rates its edges on the sharpness scale, so the box
    # at the end says where it's explained (and the text needn't).
    scale = "SharpnessScale.html"
    if root.find("a", href=re.compile(r"^SharpnessScale\.html")):
        end_notes.insert(0, f'<b>{html.escape(page_title(scale))}</b> - '
                            f'{see_text(scale, chapter_number, where)}.')
        referenced.add(scale)

    # A picture with a caption linking to another page (e.g. the
    # Grindstones sidebar) becomes a line in the box at the page's end.
    for div in root.find_all("div"):
        links = div.find_all("a", href=True)
        targets = {a["href"] for a in links}
        if (len(links) == 2 and len(targets) == 1
                and div.find("img") and not is_external(links[0]["href"])
                and len(div.get_text(strip=True)) < 60):
            target = links[0]["href"]
            end_notes.append(f'<b>{html.escape(page_title(target))}</b>'
                             f' - {see_text(target, chapter_number, where)}.')
            div.decompose()
            referenced.add(target)
            review.add(filename, "Picture link replaced by a note",
                       f"{page_title(target)} sidebar -> "
                       f"{see_text(target, chapter_number, where)}")

    for a in root.find_all("a"):
        href = (a.get("href") or "").strip()
        text = " ".join(a.get_text().split())
        if not href or href.startswith("#"):
            a.unwrap()
            continue
        if is_external(href):
            if is_video(href):
                review.add(filename, "VIDEO - needs rewording in edits.py",
                           f"\"{short(str(a.find_parent(['p', 'li']) or a), 200)}\" ({href})")
                if not final:
                    span = root.new_tag("span", attrs={"class": "needs-review"})
                    a.wrap(span)
            elif a.find_parent("li") and text:
                a.insert_after(BeautifulSoup(
                    f' <span class="web-address">({html.escape(site_name(href))})</span>',
                    "html.parser"))
                review.add(filename, "Web link removed (address printed)",
                           f"{text} - {href}")
            else:
                review.add(filename, "Web link removed",
                           f"{text or '(picture)'} - {href}")
            a.unwrap()
            continue

        target = href.split("?")[0].split("#")[0].replace("%20", " ")
        # Pictures, and the sharpness-rating badges in the guideline
        # tables, just lose the link.
        if (target in ("index.html", "ShowPicture.html") or len(text) < 4
                or a.find(["img", "table"])):
            a.unwrap()
            continue
        if not target.lower().endswith(".html"):
            # A PDF, drawing or 3D-print file kept on the web site.
            a.insert_after(BeautifulSoup(
                ' <span class="see-ref">(on the web site)</span>',
                "html.parser"))
            review.add(filename, "Document link -> \"(on the web site)\"",
                       f"{text} - {target}")
            a.unwrap()
            continue
        if target in EXCLUDED_PAGES or target.startswith("indexCalc"):
            # A calculator, or a page kept on the web site only (unless
            # the sentence already says so).
            after = a.next_sibling
            if not (isinstance(after, str) and "web site" in after[:40]):
                a.insert_after(BeautifulSoup(
                    ' <span class="see-ref">(on the web site)</span>',
                    "html.parser"))
            review.add(filename, "LEFT-OUT PAGE link -> \"(on the web "
                       "site)\" - may need rewording in edits.py",
                       f"\"{short(str(a.find_parent(['p', 'li']) or a), 200)}\"")
            a.unwrap()
            continue
        if target not in where:
            review.add(filename, "PROBLEM - linked page not in the book",
                       f"{text} -> {target}; add it to chapters.py")
            a.unwrap()
            continue
        if target not in referenced:
            referenced.add(target)
            a.insert_after(BeautifulSoup(
                f' <span class="see-ref">({see_text(target, chapter_number, where)})</span>',
                "html.parser"))
            review.add(filename, "Page link -> cross-reference",
                       f"{text} -> {see_text(target, chapter_number, where)}")
        a.unwrap()


WEB_WORDING = re.compile(r"\b(click|clicking|hover|this site|web ?site|"
                         r"scroll|below link|link)\b", re.I)


def flag_web_wording(root, filename, review):
    """Sentences that only make sense on a screen, e.g. "click on ..."."""
    blocks = ["p", "li", "td"]
    for block in root.find_all(blocks):
        # Only the block's own words: the site leaves many <p>s
        # unclosed, so later paragraphs end up nested inside earlier ones.
        own = [s for s in block.find_all(string=True)
               if s.find_parent(blocks) is block]
        text = " ".join(" ".join(own).split())
        if WEB_WORDING.search(text):
            review.add(filename, "WEB WORDING - may need rewording in "
                       "edits.py", f"\"{short(text, 200)}\"")


def see_text(target, chapter_number, where):
    number = where.get(target)
    if number is None:
        return "not yet in the book"
    if number == chapter_number:
        return f"see {html.escape(page_title(target))}, in this chapter"
    return f"see Chapter {number}"


def drop_leading_rules(root):
    """The page heading has its own rule, so a rule the web page (or
    include) starts with would print as a second one under it."""
    for child in list(root.children):
        if isinstance(child, str) and not child.strip():
            continue
        if getattr(child, "name", None) == "hr":
            child.decompose()
            continue
        break


# Standard paragraphs (on about 84 pages) explaining the sharpness scale.
# Chapter 1 covers it, so the book drops them and the box at the end of
# the page points there instead.
STANDARD_PARAGRAPHS = (
    "Sharpness scales (as shown in the grey icon",
    "These are general recommendations; you will need to use your own "
    "judgment",
)
BLOCK_TAGS = {"p", "div", "table", "ul", "ol", "li", "h1", "h2", "h3",
              "h4", "h5", "hr", "blockquote"}


def own_text(block):
    own = [s for s in block.find_all(string=True)
           if s.find_parent(["p", "li", "td"]) is block]
    return " ".join(" ".join(own).split())


def remove_own_words(p):
    """Remove a paragraph.  The site leaves <p>s unclosed, so the
    paragraphs after it may be inside it: only its own words go."""
    for child in list(p.children):
        if getattr(child, "name", None) not in BLOCK_TAGS:
            child.extract()
    p.unwrap()


def drop_coffee(root, filename, review):
    """The book leaves out "Buy me a coffee" (the box and the sentence)."""
    for a in root.find_all("a", href=re.compile("buymeacoffee", re.I)):
        if a.decomposed:
            continue
        box = a.find_parent("div")
        if box and len(box.get_text(strip=True)) < 60:
            box.decompose()
        else:
            a.decompose()
        review.add(filename, "Buy me a coffee removed", "the link/box")
    for p in root.find_all("p"):
        if "coffee" in own_text(p).lower():
            review.add(filename, "Buy me a coffee removed",
                       f"\"{short(own_text(p), 90)}\"")
            remove_own_words(p)


def fix_colon_spacing(root, filename, review):
    """"multi-step :" -> "multi-step:" (a space typed before a colon)."""
    fixed = 0
    for string in root.find_all(string=True):
        if isinstance(string, Comment) or string.parent.name in (
                "style", "script"):
            continue
        new = re.sub(r"(?<=[A-Za-z)\]”\"'’])[ \xa0]+:(?=\s|$)",
                     ":", str(string))
        # " : The goal" just after "<u>remember</u>"
        if (string.previous_sibling is not None
                and re.match(r"[ \xa0]+:(?=\s)", new)):
            new = new.lstrip(" \xa0")
        if new != str(string):
            string.replace_with(new)
            fixed += 1
    if fixed:
        review.add(filename, "Space before a colon removed", f"{fixed} place(s)")


def shorten_tormek_videos(root, filename, review):
    """A Tormek video ("Tormek Live Sharpening Class - Part 9 ...
    (YouTube video).") with no description after it."""
    for li in root.find_all("li"):
        # A Tormek video: "Tormek" in its title, before "(YouTube video)".
        if li.decomposed or "Tormek" not in own_text(li).split(
                "YouTube video)")[0]:
            continue
        mark = next((t for t in li.find_all(string=True)
                     if "YouTube video)" in t and t.find_parent("li") is li),
                    None)
        if mark is None:
            continue
        head, _, tail = str(mark).partition("YouTube video)")
        rest = tail.strip(" .\n\t") or any(
            (sib.strip() if isinstance(sib, str) else sib.name not in ("ul", "ol"))
            for sib in mark.next_siblings)
        if not rest:
            continue
        node = mark
        while node is not None and node.parent is not li:
            node = node.parent
        for sibling in list(node.next_siblings):
            if getattr(sibling, "name", None) in ("ul", "ol"):
                break
            sibling.extract()
        mark.replace_with(head + "YouTube video).")
        review.add(filename, "Tormek video description shortened",
                   short(own_text(li), 80))


def drop_tool_merchants(root, filename, review):
    """The book leaves out Matt Stern / The Tool Merchants: each list
    item naming them or linking to their site (with its sub-list)."""
    for li in root.find_all("li"):
        if li.decomposed:
            continue
        mentions = re.search(r"tool merchants|matt stern", own_text(li), re.I)
        links = [a for a in li.find_all("a", href=True)
                 if "toolmerchants" in a["href"].lower()
                 and a.find_parent("li") is li]
        if mentions or links:
            review.add(filename, "Tool Merchants removed",
                       f"\"{short(li.get_text(' '), 90)}\"")
            li.decompose()
    for p in root.find_all("p"):
        if not p.decomposed and re.search(r"tool merchants|matt stern",
                                          own_text(p), re.I):
            review.add(filename, "PROBLEM - Tool Merchants in a paragraph",
                       f"\"{short(own_text(p), 120)}\" - reword in edits.py")


def drop_proedge(root, filename, review):
    """The book leaves the Sorby ProEdge out of its tables: a row for the
    ProEdge system, and each ProEdge belt listed in a table cell."""
    for row in root.find_all("tr"):
        if row.decomposed:
            continue
        first = row.find(["td", "th"])
        if first and "Sorby ProEdge" in first.get_text():
            row.decompose()
            review.add(filename, "Sorby ProEdge removed", "a table row")
    for block in root.find_all(["li", "p"]):
        if block.decomposed or not block.find_parent("td"):
            continue
        if "ProEdge" in own_text(block):
            review.add(filename, "Sorby ProEdge removed",
                       f"\"{short(own_text(block), 80)}\"")
            if block.name == "li" and not block.find(["p", "ul", "ol",
                                                      "li"]):
                block.decompose()
            else:
                remove_own_words(block)
    # "Thank you to Bobby Smith for the information regarding the Sorby
    # ProEdge grinding media."
    for li in root.find_all("li"):
        if not li.decomposed and "ProEdge" in own_text(li) \
                and own_text(li).startswith("Thank you"):
            li.decompose()


def drop_knife_engineering(root, filename, review):
    """The book leaves out the comments on Dr. Larrin Thomas' book,
    "Knife Engineering": each mention, and the quotation it introduces."""
    for block in root.find_all(["p", "li"]):
        if block.decomposed:
            continue
        text = own_text(block)
        if "Larrin" not in text or "Knife Engineering" not in text:
            continue
        quote = None
        if text.rstrip().endswith(","):         # "... noted in his book, "
            quote = block.find_next("p", style=re.compile(r"margin-left"))
        review.add(filename, "Knife Engineering comment removed",
                   f"\"{short(text, 120)}\"")
        if block.name == "li" and not block.find(["p", "ul", "ol", "li"]):
            block.decompose()
        else:
            remove_own_words(block)
        # The quotation may run to several indented paragraphs.
        while quote is not None and not quote.decomposed:
            following = quote.find_next("p")
            remove_own_words(quote)
            quote = (following if following is not None and re.search(
                r"margin-left:\s*33px", following.get("style", "")) else None)


def drop_standard_paragraphs(root, filename, review):
    for p in root.find_all("p"):
        own = [s for s in p.find_all(string=True)
               if s.find_parent(["p", "li", "td"]) is p]
        text = " ".join(" ".join(own).split())
        if not text.startswith(STANDARD_PARAGRAPHS):
            continue
        remove_own_words(p)
        review.add(filename, "Standard paragraph removed",
                   f"\"{short(text, 70)}\"")
    # The "Example icon" picture that went with them.
    for caption in root.find_all("p"):
        if caption.get_text(strip=True) == "Example icon":
            box = caption.find_parent("div")
            (box or caption).decompose()


def first_content(tag):
    """The first child that isn't blank text (spaces, &nbsp;)."""
    for child in tag.children:
        if isinstance(child, str):
            if child.replace("\xa0", "").strip():
                return None
            continue
        return child
    return None


def nothing_after(tag, root):
    """True when nothing with words or pictures follows tag on the page
    (looking past the unclosed tags the site's heading may sit in)."""
    node = tag
    while node is not None and node is not root:
        for sibling in node.next_siblings:
            if isinstance(sibling, str):
                if sibling.strip().replace("\xa0", ""):
                    return False
            elif sibling.get_text(strip=True) or sibling.find(
                    ["img", "table"]) or sibling.name in ("img", "table"):
                return False
        node = node.parent
    return True


def drop_empty_headings(root, filename, review):
    """A heading left with nothing under it (e.g. "Sharpness Scale" once
    its standard paragraphs are gone), with any blank spacer paragraphs
    after it."""
    for heading in root.find_all(["h2", "h3", "h4"]):
        spacers = []
        following = heading.next_sibling
        while following is not None:
            if isinstance(following, str):
                if following.strip().replace("\xa0", ""):
                    break
            elif following.name == "p" and first_content(following) and \
                    first_content(following).name == "hr":
                # An unclosed <p>&nbsp; holding the rule (and the rest of
                # the page) that follows.
                following = following.find(True, recursive=False)
                break
            elif (following.name in ("p", "div", "ul", "ol", "br")
                  and not following.get_text(strip=True)
                  and not following.find(["img", "table"])):
                # An unclosed <p>&nbsp; can hold the rule that follows.
                if following.find("hr"):
                    following = following.find("hr")
                    break
                spacers.append(following)
            else:
                break
            following = following.next_sibling
        # Empty only if a rule or a heading of the same or a higher level
        # comes next - "More Information" over its "Books & Papers"
        # isn't.  And never a "heading" holding more than a heading's
        # words: an unclosed tag on the site can put the rest of the
        # page inside one.
        # At the very end of the page (e.g. Notes & Comments emptied by
        # the ProEdge rule), the rule above it goes too.
        level = int(heading.name[1])
        at_end = following is None and nothing_after(heading, root)
        ends = at_end or (following is not None and (
            following.name == "hr"
            or (following.name in ("h2", "h3", "h4")
                and int(following.name[1]) <= level)))
        text = heading.get_text(" ", strip=True)
        if ends and len(text) < 100:
            review.add(filename, "Empty heading removed", text)
            for tag in spacers:
                tag.decompose()
            if at_end:
                before = heading.previous_sibling
                while before is not None and (
                        isinstance(before, str) and not before.strip()
                        or getattr(before, "name", None) in ("hr", "br")):
                    previous = before.previous_sibling
                    if not isinstance(before, str):
                        before.decompose()
                    before = previous
            heading.decompose()


def guidelines_tables(root):
    for table in root.find_all("table"):
        heading = table.find(["td", "th"])
        if heading and "General Guidelines" in heading.get_text():
            yield table


HR_WEIGHT = {"style1": 3, "style9": 3, "style2": 1.5, "style8": 1.5,
             "style3": 1, "style0": 1}


def drop_double_rules(root, filename, review):
    """Two horizontal rules with nothing between them: the thinner goes.
    Repeated until none are left - three in a row leave two after one
    pass."""
    changed = True
    while changed:
        changed = _drop_double_rules_once(root, filename, review)


def _drop_double_rules_once(root, filename, review):
    changed = False
    for hr in root.find_all("hr"):
        if hr.decomposed:
            continue
        other = None
        for element in hr.next_elements:
            if isinstance(element, str):
                if element.replace("\xa0", "").strip():
                    break
                continue
            if element.name == "hr":
                other = element
                break
            if element.name in ("img", "table", "iframe"):
                break
        if other is None:
            continue
        weight = [HR_WEIGHT.get((h.get("class") or [""])[0], 2)
                  for h in (hr, other)]
        (other if weight[1] <= weight[0] else hr).decompose()
        review.add(filename, "Doubled rule - thinner one removed", "")
        changed = True
    return changed


def all_bold(cell):
    """True when every word in the cell is in <b>/<strong>."""
    words = [t for t in cell.find_all(string=True) if t.strip()]
    return bool(words) and all(t.find_parent(["b", "strong"]) for t in words)


def flow_list_columns(root, filename, review):
    """A list the web page sets in two columns with a one-row table (e.g.
    Videos & Presentations) becomes one list in two balanced columns, so
    where it runs onto the next page both pages' columns are even."""
    for table in root.find_all("table"):
        if table.decomposed:
            continue
        rows = [r for r in table.find_all("tr") if r.find_parent("table") is table]
        if len(rows) != 1:
            continue
        cells = rows[0].find_all(["td", "th"], recursive=False)
        lists = [c.find(["ul", "ol"], recursive=False) for c in cells]
        if len(cells) != 2 or not all(lists) or any(
                c.get_text(strip=True) != l.get_text(strip=True)
                for c, l in zip(cells, lists)):
            continue
        left, right = lists
        items = right.find_all("li", recursive=False)
        # "Tormek's Videos (continued)" joins the "Tormek's Videos" before it.
        if items:
            first = items[0]
            head = first.find(["b", "strong"])
            last = left.find_all("li", recursive=False)
            if head and last and "(continued)" in first.get_text():
                name = head.get_text(strip=True)
                prev = last[-1].find(["b", "strong"])
                sub_new = first.find(["ul", "ol"])
                sub_old = last[-1].find(["ul", "ol"])
                if prev and prev.get_text(strip=True) == name and sub_new \
                        and sub_old:
                    for li in sub_new.find_all("li", recursive=False):
                        sub_old.append(li.extract())
                    first.decompose()
        for li in right.find_all("li", recursive=False):
            left.append(li.extract())
        holder = root.new_tag("div", attrs={"class": "list-columns"})
        holder.append(left.extract())
        table.replace_with(holder)
        review.add(filename, "Two-column list set as balanced columns", "")


def table_breaks(root, filename, review):
    """Across a page break, a table's header rows repeat (they move into
    a <thead>, which Chrome repeats), and its rows stay whole.  Rows of
    one cell are left free to break: some pages lay out whole sections
    as one-cell rows."""
    for table in root.find_all("table"):
        rows = [row for row in table.find_all("tr")
                if row.find_parent("table") is table]
        # A table that's one row is page layout (e.g. a list set in two
        # columns), free to break; rows of a real table stay whole.
        if len(rows) > 1:
            for row in rows:
                if len(row.find_all(["td", "th"], recursive=False)) > 1:
                    row["class"] = row.get("class", []) + ["keep-row"]
        # Header rows repeated part-way down (on the web, to save
        # scrolling back up) go: the book repeats headers on each page.
        seen = set()
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            if cells and all(c.name == "th" for c in cells):
                words = " ".join(row.get_text(" ").split())
                if words in seen:
                    row.decompose()
                    review.add(filename, "Repeated header row removed",
                               short(words, 60))
                seen.add(words)
        rows = [row for row in rows if not row.decomposed]
        if table.find("thead") or len(rows) < 3:
            continue
        # Leading rows that are all headings, or a title row spanning
        # the table, then at least one of all headings.
        header = []
        for row in rows:
            cells = row.find_all(["td", "th"], recursive=False)
            spanning = len(cells) == 1 and cells[0].get("colspan")
            if cells and (all(c.name == "th" for c in cells) or
                          (spanning and not header)):
                header.append(row)
            else:
                break
        # A first row of plain cells whose words are all bold (Saw
        # Chains' "File Size to Use") is a header row too.
        if not header and len(rows) >= 3:
            cells = rows[0].find_all(["td", "th"], recursive=False)
            if len(cells) > 1 and all(all_bold(c) for c in cells):
                header.append(rows[0])
                for cell in cells:
                    cell.name = "th"
        # A title row alone counts too ("Honing / Stropping the Tool"),
        # if it's short enough to be a title rather than a cell of text.
        has_th = any(all(c.name == "th" for c in
                         row.find_all(["td", "th"], recursive=False))
                     for row in header)
        titled = bool(header) and len(header[0].get_text(strip=True)) < 60
        # Header cells spanning further rows down (Saw Chains: "rowspan
        # 3") take those rows into the header too, or the repeat breaks.
        reach = 0
        for index, row in enumerate(rows):
            if index >= len(header) and index >= reach:
                break
            if index >= len(header):
                header.append(row)
            for cell in row.find_all(["td", "th"], recursive=False):
                down = int(re.sub(r"\D", "", cell.get("rowspan", "1")) or 1)
                reach = max(reach, index + down)
        if not (has_th or titled) or len(header) >= len(rows) - 1:
            continue
        thead = root.new_tag("thead")
        header[0].insert_before(thead)
        for row in header:
            thead.append(row.extract())


STEEL_LABELS = ("High Carbon Steel", "High Speed Steel",
                "Steel with Carbide Insert")


def narrow_steel_column(root):
    """The High Speed Grinders notes (on about a dozen pages) set "High
    Carbon Steel" etc. in a 200px column; a narrower one lets the notes
    beside it run wider and shorter."""
    for cell in root.find_all("td"):
        if " ".join(cell.get_text().split()) in STEEL_LABELS:
            cell["style"] = re.sub(r"width:\s*\d+px", "width: 95px",
                                   cell.get("style", ""))


POINTER = re.compile(r"^(see (notes? (&|and) comments,? )?below\.?|n/?a)?$",
                     re.I)


def table_grid(table):
    """[(row, [(cell, first column, columns spanned), ...]), ...] for
    the table's own rows, allowing for cells spanning rows."""
    grid, carry = [], {}            # carry: column -> rows still covered
    for row in table.find_all("tr"):
        if row.find_parent("table") is not table:
            continue
        placed, column = [], 0
        for cell in row.find_all(["td", "th"], recursive=False):
            while carry.get(column, 0) > 0:
                column += 1
            span = int(re.sub(r"\D", "", cell.get("colspan", "1")) or 1)
            down = int(re.sub(r"\D", "", cell.get("rowspan", "1")) or 1)
            placed.append((cell, column, span))
            for c in range(column, column + span):
                carry[c] = down
            column += span
        carry = {c: n - 1 for c, n in carry.items() if n - 1 > 0}
        grid.append((row, placed))
    return grid


def drop_pointer_column(root, filename, review):
    """With the notes moved to Notes & Comments, a General Guidelines
    table's last column only says "See Notes & Comments, below." on each
    row - so it goes.  A table where that column still holds real text
    keeps it (and is listed in the review file)."""
    if filename in KEEP_TABLE_NOTES:
        return
    for table in list(guidelines_tables(root)):
        grid = table_grid(table)
        last = max((col + span - 1 for _, cells in grid
                    for _, col, span in cells), default=-1)
        if last < 1:
            continue
        in_last = [(cell, col, span) for _, cells in grid
                   for cell, col, span in cells if col + span - 1 == last]
        header, body = [], []
        for item in in_last:
            cell, col, span = item
            if span > 1:
                continue                # a title spanning the table
            (header if cell.name == "th" or cell.find_parent("thead")
             else body).append(item)
        words = [" ".join(c.get_text(" ").split()) for c, _, _ in body]
        if not body or not all(POINTER.match(w) for w in words):
            review.add(filename, "Table kept its last column",
                       "it holds more than pointers: "
                       + short("; ".join(w for w in words
                                         if not POINTER.match(w)), 100))
            continue
        if not all(re.search(r"note|comment", c.get_text(), re.I)
                   or not c.get_text(strip=True) for c, _, _ in header):
            continue
        # The table's right-hand border was on the removed cells: give it
        # to the cells that are now last (e.g. "thick", like the others).
        widths = [re.search(r"border-right-width:\s*([\w.]+)",
                            c.get("style", "")) for c, _, _ in body]
        right = next((w.group(1) for w in widths if w), "thick")
        new_last = [cell for _, cells in grid for cell, col, span in cells
                    if col + span - 1 == last - 1]
        for cell, col, span in in_last:
            if span > 1:
                cell["colspan"] = str(span - 1)
            else:
                cell.decompose()
        for cell in new_last:
            style = re.sub(r"border-right-width:\s*[\w.]+;?", "",
                           cell.get("style", ""))
            cell["style"] = (style.rstrip("; \n\t") + "; "
                             f"border-right-style: solid; "
                             f"border-right-color: black; "
                             f"border-right-width: {right};")
        review.add(filename, "Notes column removed from a table",
                   "it only pointed to Notes & Comments")


def keep_guidelines_together(root, filename):
    """Print each General Guidelines table on one page where it fits."""
    if filename in BREAKABLE_TABLES:
        return
    for table in guidelines_tables(root):
        table["class"] = table.get("class", []) + ["keep-together"]


def row_pictures(root, filename, review):
    """ROW_PICTURES: in a General Guidelines table, each row's first cell
    gets its name top-left and its picture to the right."""
    mode = ROW_PICTURES.get(filename)
    if not mode:
        return
    for table in guidelines_tables(root):
        moved = 0
        for row, cells in table_grid(table):
            cells = [c for c, _, _ in cells]
            if len(cells) < 3 or row.find_parent("thead"):
                continue
            first, last = cells[0], cells[-1]
            photo = first.find("img")
            if photo is None:
                continue
            if mode == "none":          # pictures left on the web site
                (photo.find_parent("a") or photo).decompose()
                for img in first.find_all("img"):
                    img.decompose()
                first["style"] = (first.get("style", "") +
                                  "; vertical-align: middle;")
                continue
            if mode == "to_notes":
                holder = photo.find_parent("a") or photo
                holder.extract()
                photo.attrs = {"src": photo["src"],
                               "style": "float: right; width: 110px; "
                                        "margin: 0 0 6px 10px;"}
                last.insert(0, photo)
                first["style"] = (first.get("style", "") +
                                  "; vertical-align: middle;")
                continue
            if mode == "diagram":
                box = last.find("div")
                diagram = box.find("img") if box else None
                if diagram is None:
                    continue
                holder = photo.find_parent("p")
                (holder or photo).decompose()
                photo = diagram.extract()
                box.decompose()
                photo["style"] = "width: 70px;"
                moved += 1
            else:
                photo.extract()
            photo["style"] = (photo.get("style", "") + "; float: right; "
                              "margin: 0 0 4px 8px;")
            name = first.find(["b", "strong"])
            (name or first).insert_before(photo) if name else \
                first.insert(0, photo)
            first["style"] = (first.get("style", "") + "; text-align: left;"
                              " vertical-align: top;")
        if moved:
            note = BeautifulSoup(
                '<p><i>Photographs of each of these hoes are on the web '
                'site.</i></p>', "html.parser")
            table.insert_before(note)
            review.add(filename, "Table photos replaced by edge diagrams",
                       f"{moved} rows")


def move_table_notes(root, filename, review):
    """Each Notes cell in a General Guidelines table moves to the start
    of the page's Notes & Comments, under the tool's name, and the cell
    points to it - so the tables stay short enough to keep on one page.
    Tables with no Tool column (a single row) move theirs untitled."""
    if filename in KEEP_TABLE_NOTES:
        return
    moved = []
    for table in guidelines_tables(root):
        grid = table_grid(table)
        last = max((col + span - 1 for _, placed in grid
                    for _, col, span in placed), default=-1)
        for row, placed in grid:
            # (A th inside a cell's own small table doesn't make the row a
            # header row - Fly Cutter's U-shaped cutter.)
            if row.find("th", recursive=False):
                continue
            cells = [c for c, _, _ in placed]
            if len(cells) < 3 and not (placed and placed[0][1] > 0):
                continue
            # Only a cell in the table's last (Notes) column: a row that
            # starts under a spanning cell (Carving Chisel's "Double") has
            # its β value last, not a note.
            notes, col, span = placed[-1]
            if col + span - 1 != last:
                continue
            if not notes.get_text(strip=True) and not notes.find("img"):
                continue
            # "e.g., bass or tupelo": examples that help on the web page,
            # left out of the book.
            if re.match(r"\(?e\.\s?g\.", notes.get_text(" ", strip=True),
                        re.I) and len(notes.get_text(strip=True)) < 120:
                notes.clear()
                notes.append(BeautifulSoup(
                    "<i>See Notes &amp; Comments, below.</i>", "html.parser"))
                review.add(filename, "Example note (e.g. ...) left out",
                           " ".join(cells[0].get_text(" ").split())[:60])
                continue
            # A cell may name two tools, each in bold.
            names = [" ".join(b.get_text().split())
                     for b in cells[0].find_all("b")]
            tool = (" & ".join(n for n in names if n) if len(names) > 1
                    else " ".join(cells[0].get_text(" ").split()))
            if not re.search(r"[A-Za-z]", tool):
                # An angle ("40°") in the first column: "40° Grind" in a
                # table of several rows; untitled in a one-row table.
                rows_with_notes = sum(1 for _, p in grid if p and not
                                      _.find("th", recursive=False))
                tool = f"{tool} Grind" if tool and rows_with_notes > 1 \
                    else ""
            moved.append((tool, notes.decode_contents()))
            notes.clear()
            notes.append(BeautifulSoup(
                "<i>See Notes &amp; Comments, below.</i>", "html.parser"))
            review.add(filename, "Table note moved to Notes & Comments",
                       tool or "(the table's only row)")
    if not moved:
        return
    wrap = (' style="clear: none;"' if filename in WRAP_MOVED_NOTES
            else "")
    # Rows with the same name ("40° Grind" twice) share one heading.
    parts, previous = [], None
    for tool, body in moved:
        heading = (f"<h4>{html.escape(tool)}</h4>"
                   if tool and tool != previous else "")
        # A thin rule between one tool's (or grind's) notes and the next.
        if heading and parts:
            heading = '<hr class="note-rule">' + heading
        parts.append(f'<div class="moved-note"{wrap}>{heading}{body}</div>')
        previous = tool
    blocks = "".join(parts)
    heading = root.find(lambda tag: tag.name in ("h2", "h3")
                        and "Notes" in tag.get_text()
                        and "Comments" in tag.get_text())
    if heading:
        heading.insert_after(BeautifulSoup(blocks, "html.parser"))
    else:
        last = list(guidelines_tables(root))[-1]
        last.insert_after(BeautifulSoup(
            f"<h2>Notes &amp; Comments</h2>{blocks}", "html.parser"))


def content_of(soup):
    root = soup.body or soup.html or soup
    return root


def book_page(source, title, chapter_number, review, where, sections,
              final, marker, maintenance=None, common=None):
    """source: a page or include file, or a section dict taken from part
    of a page (see chapters.py)."""
    filename = (source if isinstance(source, str)
                else f"{source['page']} (its {title} part)")
    # Pointers to shared sections and other chapters (maintenance,
    # grindstones) are gathered into one box at the end of the page.
    end_notes = []
    cuts = common["cut"] if common and isinstance(source, str) else ()
    soup = load_source(source, review, end_notes, cuts,
                       common["title"] if common else None)
    root = content_of(soup)
    strip_web_furniture(root)
    drop_coffee(root, filename, review)
    drop_tool_merchants(root, filename, review)
    replace_includes(root, filename, review, sections, end_notes,
                     maintenance)
    fix_links(root, filename, chapter_number, review, where, final,
              end_notes)
    drop_standard_paragraphs(root, filename, review)
    if chapter_number in SHORT_TORMEK_VIDEOS:
        shorten_tormek_videos(root, filename, review)
    drop_knife_engineering(root, filename, review)
    drop_proedge(root, filename, review)
    fix_colon_spacing(root, filename, review)
    flag_web_wording(root, filename, review)
    drop_leading_rules(root)
    row_pictures(root, filename, review)
    move_table_notes(root, filename, review)
    drop_pointer_column(root, filename, review)
    drop_empty_headings(root, filename, review)
    flow_list_columns(root, filename, review)
    table_breaks(root, filename, review)
    drop_double_rules(root, filename, review)
    keep_guidelines_together(root, filename)
    narrow_steel_column(root)
    inner = root.decode_contents() if root is not soup else str(root)
    # Leftover document tags from include files.
    inner = re.sub(r"</?(html|body|!DOCTYPE)[^>]*>", "", inner, flags=re.I)
    if end_notes:
        inner += ('<div class="see-note">'
                  + "".join(f"<p>{note}</p>"
                            for note in dict.fromkeys(end_notes))
                  + "</div>")
    mark = (f'<span style="position:absolute; color:white; font-size:1px;">'
            f'[[BOOKPAGE-{marker}]]</span>' if marker is not None else "")
    return (f'<section class="book-page">'
            f'<h1 class="page-title" style="position: relative;">'
            f'{html.escape(title)}{mark}</h1>\n{inner}</section>\n')


# ---------------------------------------------------------------------
# A chapter, as one HTML file printed to one PDF
# ---------------------------------------------------------------------
def page_css(chapter, paper, single_sided):
    number = chapter["number"]
    footer_title = css_string(f"Chapter {number} · {chapter['title']}")
    footer_edition = css_string(f"Sharpening Handbook · {EDITION}, "
                                f"{chapter['revised']}")
    box = ("font-family: 'Libre Caslon Text', serif; font-size: 9pt; "
           "color: #5D6532;")
    left_page = (f"margin-left: {MARGIN_OUTSIDE}in; "
                 f"margin-right: {MARGIN_INSIDE}in;")
    if single_sided:
        left_page = (f"margin-left: {MARGIN_INSIDE}in; "
                     f"margin-right: {MARGIN_OUTSIDE}in;")
    # A whole page, less a little so it can't spill onto a second one.
    title_height = ((PAPER_HEIGHT[paper] - MARGIN_TOP - MARGIN_BOTTOM)
                    / SHEET_ZOOM - 0.1)
    return f"""
@page {{
    size: {PAPER[paper]};
    margin: {MARGIN_TOP}in {MARGIN_OUTSIDE}in {MARGIN_BOTTOM}in {MARGIN_INSIDE}in;
}}
@page :right {{
    @bottom-left  {{ content: {footer_title}; {box} }}
    @bottom-right {{ content: "{number}-" counter(page); {box} font-size: 11pt; }}
}}
@page :left {{
    {left_page}
    @bottom-left  {{ content: "{number}-" counter(page); {box} font-size: 11pt; }}
    @bottom-right {{ content: {footer_edition}; {box} }}
}}
@page :first {{
    @bottom-left  {{ content: {footer_edition}; {box} }}
    @bottom-right {{ content: none; }}
}}
.chapter-title-page {{
    height: {title_height:.2f}in;
}}
"""


def css_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def site_styles():
    """The site's own styles (include-SiteStandards.html), once."""
    soup = BeautifulSoup((SITE_DIR / "include-SiteStandards.html")
                         .read_text(encoding="utf-8"), "html.parser")
    return "\n".join(style.get_text() for style in soup.find_all("style"))


def chapter_entries(chapter):
    """(source file, title) for each page or section, in order."""
    if "sections" in chapter:
        return [(s.get("include") or s, s["title"])
                for s in chapter["sections"]]
    lead = ([(chapter["common"], chapter["common"]["title"])]
            if chapter.get("common") else [])
    return lead + [(page, page_title(page)) for page in chapter["pages"]]


# Contents longer than this go in two columns.  When the title page's
# rows (contents, plus an intro and a two-line title) pass
# TITLE_PAGE_ROWS, it's set tighter, and the list can run on past it.
CONTENTS_TWO_COLUMNS = 14
TITLE_PAGE_ROWS = 16


def contents_lines(chapter):
    """The chapter's contents: the home-page group's list, or (chapters
    1-4) one line per section."""
    if "contents" in chapter:
        if chapter.get("common"):
            title = chapter["common"]["title"]
            return [{"kind": "page", "file": title, "text": title}] + \
                chapter["contents"]
        return chapter["contents"]
    if "web_only" in chapter:
        return [{"kind": "item", "text": page_title(page)}
                for page in chapter["web_only"]]
    return [{"kind": "page", "file": source if isinstance(source, str)
             else title, "text": title}
            for source, title in chapter_entries(chapter)]


def page_ref(target, number, where, page_numbers):
    """"6-14" for a page in this chapter, "Chapter 9" for one elsewhere."""
    if where.get(target) == number or target in page_numbers:
        found = (page_numbers or {}).get(target, "")
        return f"{number}-{found}" if found else ""
    other = where.get(target)
    return f"Chapter {other}" if other else ""


def contents_html(chapter, where, page_numbers):
    number = chapter["number"]
    lines = []
    for entry in contents_lines(chapter):
        if chapter.get("contents_own_only") and not (
                entry["kind"] == "page"
                and where.get(entry["file"]) == number):
            continue
        kind = entry["kind"]
        text = html.escape(entry["text"])
        if kind == "heading":
            lines.append(f'<div class="toc-heading">{text}</div>')
        elif kind == "label":
            lines.append(f'<div class="toc-line toc-label">{text}</div>')
        elif kind == "item":        # listed, but only on the web site
            lines.append(f'<div class="toc-line">{text}</div>')
        elif kind == "page":
            ref = page_ref(entry["file"], number, where, page_numbers)
            if ref.startswith("Chapter"):
                lines.append(f'<div class="toc-line toc-see">{text} - '
                             f'<i>see {ref}</i></div>')
            else:
                lines.append(f'<div class="toc-line"><span>{text}</span>'
                             f'<span class="page">{ref}</span></div>')
        else:   # "see": its links become page numbers
            see = BeautifulSoup(entry["html"], "html.parser")
            for a in see.find_all("a"):
                ref = page_ref(a["href"], number, where, page_numbers)
                a.replace_with(f'{a.get_text()} ({ref})' if ref
                               else a.get_text())
            lines.append(f'<div class="toc-line toc-see">'
                         f'{html.escape(str(see.get_text()))}</div>')
    count = len(lines)
    two = count > CONTENTS_TWO_COLUMNS
    rows = (count + 1) // 2 if two else count
    rows += 4 if chapter.get("intro") else 0
    rows += 2 if len(chapter["title"]) > 26 else 0
    layout = "two-columns" if two else "one-column"
    return (f'<div class="chapter-contents {layout}">{"".join(lines)}'
            f'</div>'), rows > TITLE_PAGE_ROWS


def chapter_html(chapter, paper, review, final, single_sided,
                 page_numbers=None):
    where = page_chapter_map()
    sections = include_section_map()
    entries = chapter_entries(chapter)
    number = chapter["number"]
    maintenance = (section_by_title(chapter["maintenance"])
                   if chapter.get("maintenance") else None)

    contents, long_contents = contents_html(chapter, where,
                                            page_numbers or {})
    intro = (f'<p class="intro">{html.escape(chapter["intro"])}</p>'
             if chapter.get("intro") else "")
    body = [f"""
<div class="chapter-title-page{' long-contents' if long_contents else ''}">
  <p class="book-name"><span class="cap">S</span>harpening <span class="cap">H</span>andbook</p>
  <p class="tagline">Because <i>sharp enough</i> ... usually is not</p>
  <p class="chapter-number">Chapter {number}</p>
  <h1>{html.escape(chapter["title"])}</h1>
  {intro}
  {contents}
  <div class="web-site">
    <img src="Web%20QR%20Code.png" alt="SharpeningHandbook.info">
    <p>The full handbook, and the latest version of this chapter, are on the web at
    <b>SharpeningHandbook.info</b>.  This chapter: {html.escape(chapter["revised"])}.</p>
  </div>
</div>
"""]
    for i, (source, title) in enumerate(entries):
        body.append(book_page(source, title, number, review, where,
                              sections, final,
                              marker=None if page_numbers else i,
                              maintenance=maintenance,
                              common=chapter.get("common")))
    # Pages with formulas load MathJax on the web; the book loads a
    # current version of it (the site's cdn.mathjax.org has been retired).
    has_math = any(isinstance(source, str) and "mathjax" in
                   (SITE_DIR / source).read_text(errors="replace").lower()
                   for source, _ in entries)
    math = MATHJAX if has_math else ""

    base = SITE_DIR.as_uri() + "/"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<base href="{base}">
<title>Sharpening Handbook - Chapter {number} - {html.escape(chapter["title"])}</title>
<link href="{FONTS}" rel="stylesheet">
{math}
<style>{site_styles()}</style>
<link href="{(BOOK_DIR / 'book.css').as_uri()}" rel="stylesheet">
<style>{page_css(chapter, paper, single_sided)}</style>
</head>
<body><div class="sheet">
{''.join(body)}
</div></body>
</html>
"""


def print_pdf(html_path, pdf_path):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--run-all-compositor-stages-before-draw",
         "--virtual-time-budget=20000",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        capture_output=True, text=True, timeout=180)
    if not pdf_path.exists():
        sys.exit(f"Chrome didn't write {pdf_path}:\n{result.stderr}")


def find_page_numbers(pdf_path, chapter):
    """{page file (or section title): the page it starts on}, from the
    pass-1 markers."""
    pages = [page.extract_text() or "" for page in PdfReader(pdf_path).pages]
    found = {}
    for i, (source, title) in enumerate(chapter_entries(chapter)):
        tag = f"[[BOOKPAGE-{i}]]"
        hit = next((n + 1 for n, text in enumerate(pages)
                    if tag in text.replace(" ", "")), None)
        found[source if isinstance(source, str) else title] = hit or "?"
    return found


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def build_chapter(chapter, final, single_sided):
    name = f"SH-Ch{chapter['number']:02d}-{slug(chapter['title'])}"
    html_dir = OUT_DIR / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    review = Review()
    for paper in PAPER:
        # Pass 1 finds where each page starts; pass 2 prints the
        # chapter's contents with those page numbers.
        html_path = html_dir / f"{name}-{paper}.html"
        pdf_path = OUT_DIR / paper / f"{name}.pdf"
        html_path.write_text(chapter_html(chapter, paper, Review(), final,
                                          single_sided), encoding="utf-8")
        print_pdf(html_path, pdf_path)
        numbers = find_page_numbers(pdf_path, chapter)
        review = Review()
        html_path.write_text(chapter_html(chapter, paper, review, final,
                                          single_sided, numbers),
                             encoding="utf-8")
        print_pdf(html_path, pdf_path)
        pages = len(PdfReader(pdf_path).pages)
        print(f"  {paper:6} {pdf_path.relative_to(SITE_DIR)} "
              f"({pages} pages)")
    write_review(chapter, name, review)


def write_review(chapter, name, review):
    lines = [f"# Review - Chapter {chapter['number']}, {chapter['title']}",
             "",
             "Generated by build_book.py; every change made to the web "
             "pages for print.  Wording fixes go in `book-build/edits.py`.", ""]
    for page, items in review.items.items():
        lines.append(f"## {page}")
        lines.append("")
        for kind, text in items:
            lines.append(f"- **{kind}:** {text}")
        lines.append("")
    path = OUT_DIR / f"Review-{name.removeprefix('SH-')}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    problems = sum(1 for items in review.items.values()
                   for kind, _ in items
                   if kind.startswith(("PROBLEM", "VIDEO", "WEB WORDING",
                                       "LEFT-OUT PAGE")))
    print(f"  review {path.relative_to(SITE_DIR)}"
          f"{f' - {problems} to look at' if problems else ''}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("chapters", nargs="*", type=int,
                        help="chapter numbers to build (default: "
                             "BUILD_BY_DEFAULT in chapters.py)")
    parser.add_argument("--final", action="store_true",
                        help="don't highlight things needing review")
    parser.add_argument("--single-sided", action="store_true",
                        help="wide margin on the left of every page")
    args = parser.parse_args()
    wanted = args.chapters or BUILD_BY_DEFAULT
    for chapter in all_chapters():
        if wanted and chapter["number"] not in wanted:
            continue
        print(f"Chapter {chapter['number']}: {chapter['title']}")
        build_chapter(chapter, args.final, args.single_sided)


if __name__ == "__main__":
    main()
