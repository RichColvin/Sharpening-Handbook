"""What goes in the printed Sharpening Handbook, and in what order.

Each chapter is printed as its own PDF, so a chapter can be replaced in
a 3-ring binder without reprinting the others.  Page numbers restart in
every chapter and carry its number (5-1, 5-2, ...).

The planned order is:
    1  Introduction (sharpness scale, standards, micro-bevels, grind profiles)
    2  Grindstones and Tormek tips
    3  Jigs
    4  Ongoing Maintenance
    5+ one chapter per group on the home page (index.html), in its order:
       5 Beekeeping Tools, 6 Bench Tools, ... 9 Gardening Tools, ...
       17 Wood Lathe Tools, ... 20 Reference Materials (with the glossary,
       Dictionary.html)

Chapters 5 onward come from the home page itself (see site_index.py):
each group's list - its tools, its "see" lines and its sub-groups - is
that chapter's contents, so adding a tool to the home page adds it to
the book.  CHAPTERS below only adds settings for them.
"""

EDITION = "2026 Edition"

# Printed in the footer of every page of a chapter, so a reader can tell
# whether the copy in their binder is current.  A chapter can set its own.
DEFAULT_REVISED = "November 2026"

# The first home-page group (Beekeeping Tools) is this chapter.
GROUP_FIRST_CHAPTER = 5

# The chapters built when no chapter numbers are given (None = all).
BUILD_BY_DEFAULT = None

# Pages whose General Guidelines table keeps its notes in the table,
# rather than moving them to Notes & Comments: they're short, and read
# best beside their row.
KEEP_TABLE_NOTES = {"SharpnessScale.html"}

# Pages whose General Guidelines table may run across a page break
# (rows whole, headers repeated) rather than move whole to the next
# page: it's long, and moving it left a mostly empty page.
BREAKABLE_TABLES = {"GT-Knives-OutdoorPocket.html", "GT-Hoe.html",
                    "WW-RoseEngineFlyCutter-Rod.html", "GT-Scissors-Sewing.html",
                    "WW-Chisels.html", "WW-Plane.html",
                    "WW-Chisels-Japanese.html"}

# Pages whose moved table notes (Notes & Comments) run around a picture
# beside them, rather than each starting below it.
WRAP_MOVED_NOTES = {"GT-FirefighterCombiTool.html", "GT-Pruner.html"}

# Chapters where each Tormek video is listed by its
# title only - the description after "(YouTube video)" is left out.
SHORT_TORMEK_VIDEOS = {10, 16, 17, 18}

# General Guidelines tables whose first column's pictures are set to
# the right, with the tool's name top-left.  For the "diagram" pages the
# tool photo is dropped and the edge-angle diagram from the row's notes
# takes its place (the photos stay on the web site).
ROW_PICTURES = {
    "GT-Knives-Gardening.html": "right",
    "GT-Hoe.html": "diagram",
    "GT-PickMattock_PickAx.html": "to_notes",
    "WW-RoseEngineFlyCutter-Rod.html": "none",
}

# Pages left out of the book altogether: the calculators (they only work
# on the web), and pages Rich chose to leave on the web site only.
# Their lines on the home page are left out of the contents, and links
# to them say "(on the web site)".
EXCLUDED_PAGES = {
    "indexCalc.html",
    "Grindstones-Comparison-Hardness.html",
    "Grindstones-Tormek.html",
    "Grindstones-CaringFor.html",
    "PurchasedAnOldTormek.html",
    "indexBooksVideosWebSites.html",
    "indexPictures.html",
}

# Chapters 1-4 are set out here in full: "pages" are handbook pages in
# order; "sections" are include files (or parts of a page) printed as
# sections of their own.  A page here that's also on the home page
# (most of Reference Materials' are) is printed here, and the Reference
# Materials contents point to it.  For chapters 5 onward, an entry only
# adds settings to the home-page group with that number.
CHAPTERS = [
    {
        "number": 1,
        "title": "Introduction",
        "pages": [
            "indexAbout.html",
            "SharpnessScale.html",
            "MicroBevels.html",
            "info-EffectiveAngle.html",
            "GrindProfiles.html",
        ],
    },
    {
        "number": 2,
        "title": "Grindstones and the Tormek",
        "pages": [
            "Grindstones.html",
            "Grindstones-QuickSelect.html",
            "Grindstones-Affixing.html",
            "Grindstones-Storing.html",
            "Grindstones-StoneLife.html",
            "TormekTipsTricksTechniques.html",
            "TimeSavingTipsForTheTormek.html",
            "indexTormekMaintenance.html",
        ],
    },
    {
        "number": 3,
        "title": "Jigs, Fixtures, and Modifications",
        # Only a title page listing them: the jig pages depend on their
        # 3D-print files and downloads, so they stay on the web site.
        # Links to them from other pages say "(see Chapter 3)".  In the
        # order of the site's Jigs page (indexJigs.html).
        "intro": "The jigs, fixtures, and modifications below make "
                 "sharpening on the Tormek easier.  Their descriptions, "
                 "drawings, and 3D-print files to download are on the "
                 "web site, under Jigs, Fixtures, & Modifications.",
        "web_only": [
            "Jigs-DBS22.html",
            "Jigs-DBS22-Setting-Templates.html",
            "Jigs-DBS22-USB-Spacer.html",
            "Jigs-FVB.html",
            "Jigs-HanJig.html",
            "Jigs-KenJig.html",
            "Jigs-KnifeAngleSetter.html",
            "Jigs-LaserGoniometer.html",
            "Jigs-Platform.html",
            "Jigs-RotaryKnife.html",
            "Jigs-Goniostat.html",
            "Jigs-PivotJig.html",
            "Jigs-SE-77-Alignment.html",
            "Jigs-ProjectionTTS-100.html",
            "Jigs-RouterPlaneBlade-Traditional.html",
            "Jigs-RouterPlaneBlade-Woodpeckers.html",
            "Jigs-AngleGauge.html",
            "Jigs-Break-InJig.html",
            "Jigs-DripTray.html",
            "Jigs-GrindstoneStand.html",
            "Jigs-GrindstoneWasher.html",
            "Jigs-HoningSupportBar.html",
            "Jigs-StoneSpacer.html",
            "Jigs-TiltFeet-Taller.html",
            "Jigs-Software.html",
        ],
    },
    {
        "number": 4,
        "title": "Ongoing Maintenance",
        "intro": "Most tools in this handbook share the same care once "
                 "they are sharp.  Rather than repeat it on every page, "
                 "it is gathered here, one section per kind of tool.  "
                 "Each tool's page says which section applies.",
        # In alphabetic order.
        "sections": [
            # Not a shared include on the web site: Cell Punch's own
            # maintenance text, written for beekeeping (wax, propolis,
            # diseased bees; no bleach).  The book prints it here and
            # cuts it from the Cell Punch page.
            {"title": "Beekeeping Tools",
             "page": "GT-CellPunch.html",
             "from": "<!-- Ongoing Maintenance -->",
             "to": "<!-- More Information -->"},
            {"title": "Garden Tools",
             "include": "include-GT-OngoingMaintenance.html",
             # Pages using just part of it (Spud Bars, Turf Edgers -
             # no wooden handle) point here too.
             "also": ["include-GT-OngoingMaintenance_Part-1.html",
                      "include-GT-OngoingMaintenance_Part-3.html"]},
            {"title": "Knives",
             "include": "include-Knife-OngoingMaintenance.html"},
            {"title": "Metalworking Tools",
             "include": "include-MW-OngoingMaintenance.html"},
            {"title": "Woodworking Tools",
             "include": "include-WW-OngoingMaintenance.html"},
        ],
    },
    {
        "number": 5,                    # Beekeeping Tools
        # Its pages point here for maintenance, rather than to the
        # garden-tools include some of them use on the web site.  (Comb
        # Cutters keeps its own short note: no oil, it would taint the
        # honey.)
        "maintenance": "Beekeeping Tools",
    },
    {
        "number": 11,                   # Metal Lathe Tools
        # Notes that are the same on every tool page (high-speed grinding
        # and carbide inserts, the contour gauge, More Information) are
        # printed once, at the start of the chapter, and cut from each
        # page; each page's end box points to them.
        "common": {
            "title": "Notes for All Metal Lathe Tools",
            "page": "MW-Lathe-Tools-BoringBars.html",
            "from": "<p>If grinding this on a high speed grinder",
            "to": "<!-- Footer",
            "cut": [
                r'(<div style=" float: left;\s+width: 40px;[^>]*>\s*<img '
                r'src="Razor%20Pictures/razor-blade-red\.png"[^>]*>\s*</div>'
                r'\s*)?(<p>)?If grinding this on a high speed grinder.*?'
                r'(?=<!-- #+ -->\s*<!-- Ongoing Maintenance -->)',
                r'<!-- More Information -->.*?(?=<!-- #+ -->\s*<!-- Footer)',
            ],
        },
    },
    {
        "number": 12,                   # Rose Engine Tools
        # Newer Sharpening Tools and More Information are printed once,
        # at the start of the chapter (taken from the Traditional Fly
        # Cutter page, from Newer Sharpening Tools to its end), and cut
        # from each page.
        "common": {
            "title": "Notes for All Rose Engine Tools",
            "page": "WW-RoseEngineFlyCutter-Traditional.html",
            "from": "<!-- Newer Sharpening Tools -->",
            "to": "<!-- Footer",
            "cut": [
                r'<!-- Newer Sharpening Tools -->.*?(?=<!-- #+ -->)',
                r'<!-- More Information -->.*?(?=<!-- #+ -->\s*<!-- Footer)',
            ],
        },
    },
    {
        "number": 14,                   # Scissors
        # Jigs, Grindstone Rotation, Diamond Grinding Wheels, Tip
        # Shortening and More Information, printed once (from the Sewing
        # Scissors page, which has the fullest versions) and cut from
        # each page.
        "common": {
            "title": "Notes for All Scissors",
            "page": "GT-Scissors-Sewing.html",
            "from": "<!-- Jigs -->",
            "to": "<!-- Footer",
            "cut": [
                r'<!-- (Jigs|Grindstone Rotation|Diamond Grinding Wheels|'
                r'Tip Shortening) -->.*?(?=<!-- #+ -->)',
                r'<!-- More Information -->.*?(?=<!-- #+ -->\s*<!-- Footer)',
                # The same jig pictures and note, without their own
                # heading, on the General and Kitchen pages.
                r'<div style="float: left; width: 150px;[^>]*>\s*<p[^>]*>'
                r'<a href="ShowPicture\.html\?ImgNm=Images//SC-60\.png".*?'
                r'</div>\s*<p style="margin-top: 0;">The Tormek SC-60 '
                r'Scissors jig is the best to use for these\.[^<]*',
            ],
        },
    },
    {
        "number": 17,                   # Wood Lathe Tools
        # High Speed Grinders (heating and cooling the steel), the same on
        # seven tool pages, printed once and cut from each.
        "common": {
            "title": "Notes for All Wood Lathe Tools",
            "page": "WW-Scraper-NRS.html",
            "from": "<!-- High Speed Grinders -->",
            "to": "<!-- ####",
            "cut": [
                r'<!-- High Speed Grinders -->.*?(?=<!-- #+ -->)',
            ],
        },
    },
    {
        "number": 18,                   # Woodworking Bench Tools
        # Jigs for Sharpening Chisels on the Tormek, the same on the
        # Chisels, Hand Planes and Japanese Chisels pages, printed once.
        "common": {
            "title": "Notes for All Woodworking Bench Tools",
            "page": "WW-Chisels.html",
            "from": "<!-- Jigs for Sharpening Chisels on the Tormek -->",
            "to": "<!-- Replacing Wooden Handles -->",
            "cut": [
                r'<!-- Jigs for Sharpening Chisels on the Tormek -->.*?'
                r'(?=<!-- #+ -->\s*<!-- (?!\*)[A-Z])',
            ],
        },
    },
    {
        "number": 20,                   # Reference Materials
        # Its contents list only the pages printed in it - not the home
        # page's other reference lines, which point to Chapters 1-3 or
        # the web site.
        "contents_own_only": True,
    },
]

# Pages in neither CHAPTERS nor the home page that other pages link to,
# and the chapter to point those links at.  (The build reports any
# linked page it can't place.)
PLANNED_CHAPTER = {
    "indexJigs.html": 3,
}
