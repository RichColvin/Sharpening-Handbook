"""Wording changes for the printed book only - the web pages are untouched.

Use this where a sentence only makes sense on the web, e.g. one pointing
to a video.  Each entry is (text as it is in the page's HTML, text to
print instead).  An empty replacement removes the text.  The build
reports any entry whose text it can't find, so a change to the web page
doesn't silently undo one of these.

Example:
    "GT-Hoe.html": [
        ("To help you understand the oscillating movement, this is a "
         "video of an <a href=\"https://youtu.be/efaQykJnLQ8?si=RNbn60z-6yckd0I0\" "
         "target=\"new\">oscillating hoe in action</a>.",
         "Several makers show oscillating hoes in action on YouTube."),
    ],
"""

import re

from bs4 import BeautifulSoup

# The (old, new) pairs can also be (re.compile(...), new) for a longer
# block, matched as a regular expression - and then new can be a
# function of the match, for rearranging a block rather than rewording it.


def picture_beside_text(match):
    """A two-cell layout table (picture | text) becomes the picture
    floated right, with the text running beside it."""
    table = BeautifulSoup(match.group(0), "html.parser")
    row = table.find("tr")
    picture_cell, text_cell = row.find_all("td", recursive=False)[:2]
    return ('<div style="float: right; width: 300px; margin: 0 0 10px 12px; '
            'padding: 0 0 5px 5px; border: 1px solid darkgray;">'
            + picture_cell.decode_contents() + '</div>'
            + text_cell.decode_contents()
            + '<div style="clear: both;"></div>')


def crack_weeder_layout(match):
    """The Crack Weeder page's opening: its layout table (picture | text |
    edge angle and quote) becomes the picture on the left with the text
    flowing around it, the bullet points as plain paragraphs."""
    table = BeautifulSoup(match.group(0), "html.parser")
    picture = table.find("img", src=re.compile("GT-CrackWeeder")).find_parent("div")
    angle = table.find("img", src=re.compile("GT-Knives")).find_parent("td")
    quote = table.find("td", style=re.compile("background-color"))
    text = picture.find_parent("td").find_next_sibling("td")
    intro = text.find("p")
    points = [li.decode_contents() for li in text.find_all("li")]
    debate = text.find_all("p")[-1]
    for tag in intro.find_all(["ul", "li", "hr", "p"]):
        tag.extract()
    for tag in debate.find_all(["ul", "li", "hr"]):
        tag.extract()
    picture["style"] = ("float: left; width: 165px; margin: 0 12px 8px 0; "
                        "padding: 0 0 5px 5px; border: 1px solid darkgray;")
    return (
        str(picture)
        + '<div style="float: right; width: 300px; margin: 0 0 8px 12px;">'
        + '<div style="padding: 5px; border: 1px solid darkgray;">'
        + angle.decode_contents() + '</div>'
        + '<div style="margin-top: 8px; padding: 5px; background-color: '
        '#b5edb5;">' + quote.decode_contents() + '</div></div>'
        + '<p style="margin-top: 0;">' + intro.decode_contents() + '</p>'
        + "".join(f"<p>{point}</p>" for point in points)
        + '<hr class="style2"><p>' + debate.decode_contents() + '</p>'
        + '<div style="clear: both;"></div>')


PRINTING_RIGHTS = (
    '<div class="rights-note"><b>Printing this book.</b>  This book is '
    'made from the Sharpening Handbook web site, SharpeningHandbook.info.  '
    'You may print it, or any part of it, for your own personal use.  No '
    'rights are granted to print it, or any part of it, for sale.</div>')

# The Seneca quote box, moved up and to the right on About this Book so
# it isn't split across two pages.
SENECA_BOX = (
    '<div style="float: right; width: 250px; break-inside: avoid; '
    'margin: 0 0 10px 12px; padding: 3px; border: 1px solid black; '
    'text-align: left; background-color: Moccasin;">'
    'Nothing will ever please me, no matter how excellent or beneficial, '
    'if I must retain the knowledge of it to myself. And if wisdom were '
    'given me under the express condition that it must be kept hidden and '
    'not uttered, I should refuse it. No good thing is pleasant to '
    'possess, without friends to share it.'
    '<p class="indented" style="margin-bottom: 0;">From Seneca the '
    'Younger&rsquo;s &ldquo;Moral Letters&rdquo; to Lucilius, letter 6 '
    'titled, <i>&ldquo;On Sharing Knowledge&rdquo;</i></p></div>')

EDITS = {
    "indexAbout.html": [
        (re.compile(r'<div style="float: left; width: 250px;.*?'
                    r'On Sharing Knowledge&rdquo;</I>\s*</div>', re.S), ''),
        ('<p>I have not used other systems',
         SENECA_BOX + '<p>I have not used other systems'),
        ('>About this Site</p>', '>About this Book</p>'),
        # Up front, as the first thing in the book after the title page.
        ('<p><IMG SRC="Images/Art-Pupini',
         PRINTING_RIGHTS + '<p><IMG SRC="Images/Art-Pupini'),
        ('This site is meant as a reference tool',
         'This book, made from the web site, is meant as a reference tool'),
        # The (i) circles link to the information pages, which aren't in
        # the book: keep only the pointer to the recommended books.
        (re.compile(r'<div style="float: left;\s+margin-left: 0px; '
                    r'margin-right: 10px;[^>]*>\s*<span style="color: '
                    r'black; font-size: 24px;">&#9432;</span>\s*</div>\s*'
                    r'For many topics, there is a link to information '
                    r'about recommended processes for the noted tools\.  '
                    r'This is a quick overview\.  If'), 'If'),
        ('sharpening books, videos, & web sites</a> noted on this site',
         'sharpening books, videos, & web sites</a> noted on the web site'),
        # The blue-to-green note under the signature.
        (re.compile(r'<table style="width: 100%; background-color: '
                    r'#5D6532;">.*?</table>', re.S), ''),
    ],
    "TormekTipsTricksTechniques.html": [
        # "Types of Grinding Wheels"
        (re.compile(r'<h2 id="Grinding_Wheels".*?'
                    r'(?=<h2 id="Grindstone_Rotation_Direction")', re.S), ''),
        # "Learn to Sharpen a Chisel First", "Practice on Second-Hand
        # Knives" and "Identify a Way to Quantify Sharp"
        (re.compile(r'<h2 id="Sharpening_Chisels".*?(?=<h2 id="WaterTray")',
                    re.S), ''),
    ],
    "Grindstones-StoneLife.html": [
        # Its video isn't in the book.
        ('In the  video below from Dan @ <a href="http://www.exactblade.com" '
         'target="new">Exact Blade</a>, Dan notes',
         'Dan @ <a href="http://www.exactblade.com" target="new">Exact '
         'Blade</a> notes'),
        (re.compile(r'<p>The video below is from Dan at <a href="http://'
                    r'www\.exactblade\.com" target="new">Exact Blade</a>\.'
                    r'.*?grindstone investment\.', re.S), ''),
    ],
    "Grindstones-Affixing.html": [
        # The picture beside this text is on the right.
        ('The picture to the left shows an area in light purple',
         'The picture to the right shows an area in light purple'),
        # Smaller diagrams (their labels still readable).
        ('<div style="float: right; width: 500px;',
         '<div style="float: right; width: 370px;'),
        ('<div style="float: right; width: 525px;',
         '<div style="float: right; width: 390px;'),
        ('<div style="float: right; width: 550px;',
         '<div style="float: right; width: 400px;'),
    ],
    "GT-Knives-OutdoorPocket.html": [
        # A wider Blade Thickness column, each range on one line:
        # "1.6mm to 2.5mm" over "0.063" to 0.100"".
        (re.compile(r'\s*<br>to\s*<br>'), ' to '),
        # Smaller SEM pictures, so the end box fits on the page before.
        (re.compile(r'<div style="float: right; width: 300px;(?=[^>]*>\s*'
                    r'<a href="GT-Knives-Ripped-Burr\.html"><IMG SRC="'
                    r'Images/zdp-159burr\.jpg")'),
         '<div style="float: right; width: 190px;'),
        (re.compile(r'(zdp-159burr(?:_cross-grain_cut)?\.jpg" alt="no image '
                    r'file" style="width: 48%; height: )150px'), r'\g<1>90px'),
        (re.compile(r'(<th style="width: )75px;(?=[^<]*<div[^>]*>\s*'
                    r'<p class="TextTableHdrNorm" style="margin: 0;">'
                    r'<b>Blade<br>Thickness)'), r'\g<1>140px;'),
    ],
    "WW-Saws-Hand.html": [
        # Sharpening steps in one column, not two.
        # No crosscut / rip tooth pictures in the General Guidelines
        # table, so it's short enough to start on the page before.
        ('<p style="margin-bottom: 0;"><img src="Images/Saw-Crosscut.png" '
         'alt="no image file" style="width: 75px;">', ''),
        ('<p style="margin-bottom: 0;"><img src="Images/Saw-Rip.png" '
         'alt="no image file" style="width: 75px;">', ''),
        # "Saw Purpose" set level, not turned on its side: a much
        # shorter header row.
        ('<div style="writing-mode: vertical-rl; transform: rotate(180deg); '
         'white-space: nowrap; hyphens: none; margin: 0 auto; text-align: '
         'left;">\n            <p class="TextTableHdrNorm" style="margin: 0;">'
         '<b>Saw<br>Purpose</b></p>',
         '<div>\n            <p class="TextTableHdrNorm" style="margin: 0;">'
         '<b>Saw<br>Purpose</b></p>'),
        # A smaller pole pruner picture, so the text after it runs the
        # full width and the end box fits on the page before.
        (re.compile(r'width:100px;(\s*padding: 5px; border: 1px solid gray; '
                    r'text-align: left; margin-top: 5px;">\s*<IMG SRC="Images/'
                    r'GT-Pole-Pruner-Saw\.png")'), r'width:60px;\1'),
        (re.compile(r'(Sharpening steps:</h3>\s*<table>\s*<tr[^>]*>\s*'
                    r'<td style="width: )50%(;">.*?)</td>\s*'
                    r'<td style="width: 50%;">', re.S),
         r'\g<1>100%\g<2>'),
    ],
    "GT-DrillBits-Twist.html": [
        # Grindstones Which Work Best: full width (it left room for a
        # picture beside it on the web page).
        ('<h3 style="margin-bottom: 0;">Grindstones Which Work Best</h3>\n'
         '<table style="width: calc(100% - 250px);',
         '<h3 style="margin-bottom: 0;">Grindstones Which Work Best</h3>\n'
         '<table style="width: 100%;'),
    ],
    "Hand-File-Identification.html": [
        # The "File Identification Chart" subsection (a link to a PDF).
        (re.compile(r'<h2>File Identification Chart</h2>.*?'
                    r'(?=<!-- #+ -->\s*<!-- Footer)', re.S), ''),
    ],
    "indexToolMaintenance.html": [
        # The More Information section at the end.
        (re.compile(r'<!-- More Information -->\s*<hr class="style1">\s*'
                    r'<h2>More Information</h2>.*?'
                    r'(?=<!-- #+ -->\s*<!-- Footer)', re.S), ''),
    ],
    "indexTormekMaintenance.html": [
        # The Alan Holtham video at the end.
        (re.compile(r'<table style="width: 100%;">\s*<tr>\s*<td style="'
                    r'text-align: left; vertical-align: top; ">\s*This video '
                    r'from Alan Holtham.*?</table>', re.S), ''),
    ],
    "GT-FirefighterCombiTool.html": [
        # The Shovel end and Pick end pictures side by side in one box,
        # under one shared credit (in the Shovel End note); the Pick End
        # note's own box goes.
        (re.compile(r'<div style=" float: right; Width: 100px;[^>]*>\s*'
                    r'<img src="Images/GT-FirefighterCombiTool-1\.png".*?'
                    r'</div>', re.S),
         '<table style="float: right; width: 240px; margin: 0 0 10px 10px; '
         'border-collapse: collapse; border: 1px solid darkgray;"><tr>'
         '<td style="width: 50%; vertical-align: bottom; padding: 5px;">'
         '<img src="Images/GT-FirefighterCombiTool-1.png" style="width: '
         '100%;"><p class="TextSMImage"><b><i>Shovel end</i></b></p></td>'
         '<td style="width: 50%; vertical-align: bottom; padding: 5px;">'
         '<img src="Images/GT-FirefighterCombiTool-2.png" style="width: '
         '100%;"><p class="TextSMImage"><b><i>Pick end</i></b></p></td>'
         '</tr><tr><td colspan="2" style="padding: 0 5px 5px 5px;">'
         '<p class="TextSMImage"><i>Images courtesy Council Tool</i></p>'
         '</td></tr></table>'),
        (re.compile(r'<div style=" float: right; Width: 100px;[^>]*>\s*'
                    r'<img src="Images/GT-FirefighterCombiTool-2\.png".*?'
                    r'</div>', re.S), ''),
        ('(as shown in the picture in the right;',
         '(as shown in the Pick end picture to the right;'),
    ],
    "GT-McLeodTool.html": [
        # The Fun fact box on the left, under the picture; the text runs
        # around it.
        (re.compile(r'\s*<tr>\s*<td style="width: 100%;[^>]*background-color:'
                    r' #DFD7C8; ">.*?</tr>', re.S), ''),
        ('    <p class="TextSMImage"><i>Image courtesy Council Tool</i></p>\n'
         '</div>\n',
         '    <p class="TextSMImage"><i>Image courtesy Council Tool</i></p>\n'
         '</div>\n<div style="float: left; clear: left; width: 195px; '
         'margin: 0 10px 10px 0; padding: 5px; background-color: #DFD7C8;">'
         '<p style="margin-top: 0; margin-bottom: 0; font-size: 15px;">'
         '<b>Fun fact:</b> The nut which holds the tool&rsquo;s head onto the '
         'shaft can be removed using the wrench supplied with most chainsaws.'
         '</p></div>\n'),
    ],
    "GT-CrackWeeder.html": [
        (re.compile(r'(?<=<!-- Guidance Information -->)\s*<table.*?</table>',
                    re.S), crack_weeder_layout),
    ],
    "GT-LawnMower.html": [
        # The Lawn Edger Blade first, beside the Edge Angle picture.
        (re.compile(r'(<table>\s*<tr>\s*<td>\s*<div style="float: left; '
                    r'width: 450px;.*?</table>)\s*(<table>\s*<tr>\s*<td>\s*'
                    r'<div style="float: left; width: 250px;.*?</table>)',
                    re.S), r'\2\n\1'),
    ],
    "GT-PickMattock_PickAx.html": [
        ('; click on the picture to see a larger version.)', '.)'),
    ],
    "GT-PruningKnifeTrees.html": [
        # A narrower quote box, moved up beside "Sharpen the outside
        # edges" so the text runs around it, and no blank line before the
        # General Guidelines table.
        (re.compile(r'(<hr class="style2">\s*)(<p>Sharpen the outside edges.*?)'
                    r'<div style=" float: right; margin-left: 10px; '
                    r'margin-right: 0px; margin-bottom: 10px; width: 450px;'
                    r'(.*?</div>)\s*<hr class="style2">', re.S),
         r'\1<div style=" float: right; margin-left: 10px; margin-right: 0px;'
         r' margin-bottom: 10px; width: 260px;\3\2'),
        (re.compile(r'(gardening activity\.?\s*(?:</p>)?)\s*<p>&nbsp;'), r'\1'),
        # "Micro bevel Notes: A micro bevel is not recommended..." on one
        # line, so the end box fits on the page before.
        (re.compile(r'<p><b>Micro bevel Notes</b>:\s*<p>'),
         '<p><b>Micro bevel Notes</b>: '),
    ],
    "GT-Pruner.html": [
        # The coplanar pictures up beside the first paragraph, on the
        # right.
        (re.compile(r'(<p style="margin-top: 0; ">A critical aspect.*?)'
                    r'<table style="border-collapse: collapse;(.*?</table>)',
                    re.S),
         r'<table style="float: right; margin: 0 0 8px 12px; '
         r'border-collapse: collapse;\2\1'),
        # The saw-blade pole pruner on the left too, under the other
        # pictures, with the text to its right.
        ('<div style="float: right; margin-left: 10px; margin-right: 0px; '
         'margin-bottom: 10px; width:125px;  padding: 5px; border: 1px solid '
         'gray; text-align: left; margin-top: 5px',
         '<div style="float: left; clear: left; margin-left: 0px; '
         'margin-right: 10px; margin-bottom: 10px; width:125px;  padding: 5px;'
         ' border: 1px solid gray; text-align: left; margin-top: 5px'),
        ('saw blade attached as shown in the picture to the right,',
         'saw blade attached as shown in the picture to the left,'),
    ],
    "GT-Shovel.html": [
        # Angle ranges on one line: "40° - 45°".
        (re.compile(r'&deg;\s*<br>\s*-\s*<br>\s*'), '&deg; - '),
    ],
    "GT-Shovel-Square.html": [
        (re.compile(r'&deg;\s*<br>\s*-\s*<br>\s*'), '&deg; - '),
    ],
    "GT-Weeding-Sickle-Japanese.html": [
        # A narrower quote box, moved up beside the hand-file paragraph so
        # the rule above that paragraph runs into it.
        (re.compile(r'(<hr class="style2">\s*<p>A 6&quot; smooth cut.*?)'
                    r'<div style=" float: right; margin-left: 10px; '
                    r'margin-right: 0px; margin-bottom: 10px; width: 450px;'
                    r'(.*?</div>)', re.S),
         r'<div style=" float: right; margin-left: 10px; margin-right: 0px; '
         r'margin-bottom: 10px; width: 280px;\2\1'),
    ],
    "WW-Chisels.html": [
        # Bevel-width ranges on one line, without the decimal inches:
        # "1/16" (1.5 mm) - 1/8" (3 mm)".
        (re.compile(r'\(0\.\d+&rdquo; / '), '('),
        (re.compile(r'\s*&nbsp; &nbsp; to\s*<br>\s*'), ' - '),
    ],
    "WW-Router-Plane.html": [
        # The Woodpecker jig picture moves up above the rule, kept whole
        # with its caption.
        (re.compile(r'(<hr class="style3">\s*)(<h4 style="margin-top: 3px; '
                    r'margin-bottom: 0;">3D-Printed Jigs for Sharpening '
                    r'Woodpecker Blades</h4>\s*)(<table style="float: left;)'
                    r'(.*?</table>)', re.S),
         r'\3 break-inside: avoid;\4\1\2'),
    ],
    "WW-Bedan.html": [
        # A quote box as wide as the Edge Angle picture, so "Edges to be
        # honed" moves up beside them.
        ('<table style="float: right; margin-left: 10px; margin-right: 0px; '
         'margin-bottom: 10px; width: 350px; \n\t\tborder: 0px solid grey;',
         '<table style="float: right; margin-left: 10px; margin-right: 0px; '
         'margin-bottom: 10px; width: 310px; \n\t\tborder: 0px solid grey;'),
        ('<table style="float: right; margin-left: 10px; margin-right: 0px; '
         'margin-bottom: 10px; width: 350px; \n            \t\tmargin-top: 10px;',
         '<table style="float: right; margin-left: 10px; margin-right: 0px; '
         'margin-bottom: 10px; width: 300px; \n            \t\tmargin-top: 10px;'),
    ],
    "WW-BowlGouge.html": [
        # "40/40 Grind Using a Tormek" moves up into the 40/40 row's notes,
        # so it prints with the other 40° Grind notes.
        (re.compile(r'<p>Henrik Franck Stampe provided a set of instructions '
                    r'for <a href="#4040">.*?</a>\.(.*?)<!-- #+ -->\s*'
                    r'<!-- 40/40 Grind -->\s*<a id="4040"></a>\s*<h3[^>]*>'
                    r'40/40 Grind Using a Tormek</h3>(.*?)(?=<!-- #+ -->)',
                    re.S),
         r'<h4>40/40 Grind Using a Tormek</h4>\2\1'),
    ],
    "WW-FlutelessGouge.html": [
        # The picture on the right, so the bullet points line up.
        ('<!-- Top Grind -->\n<hr class="style2">\n<div style="float: left; '
         'width: 250px;\n        margin-left: 0px; margin-right: 10px; ',
         '<!-- Top Grind -->\n<hr class="style2">\n<div style="float: right; '
         'width: 250px;\n        margin-left: 10px; margin-right: 0px; '),
        ('to do this (as shown in the picture to the left)',
         'to do this (as shown in the picture to the right)'),
    ],
    "WW-Parting-Tool-Diamond.html": [
        # The quote box on the left, under the text, so the picture on the
        # right sits beside both.
        ('<table style="float: right;\n            \t\twidth: 450px;\n'
         '            \t\tmargin-top: 10px; margin-bottom: 10px;\n'
         '            \t\tmargin-left: 10px; margin-right: 0px;',
         '<table style="float: left; clear: left;\n            \t\twidth: 300px;\n'
         '            \t\tmargin-top: 10px; margin-bottom: 10px;\n'
         '            \t\tmargin-left: 0px; margin-right: 10px;'),
        # The picture on the right, not in a table with the text.
        (re.compile(r'<table style="width: 100%;">\s*<tr style="vertical-'
                    r'align: top;">\s*<td style="width: 350px;.*?</table>\s*'
                    r'</td>\s*</tr>\s*</table>', re.S), picture_beside_text),
    ],
    "GT-HiveTools.html": [
        # Notes & Comments starts on a new page (5-5), not at the foot
        # of the table's page.
        ('<h2>Notes &amp; Comments</h2>',
         '<h2 style="break-before: page;">Notes &amp; Comments</h2>'),
    ],
    # A smaller picture, so the box of chapter references fits on the
    # page's first sheet (5-3) instead of spilling onto a second.
    "GT-CombCutters.html": [
        ('<div style="float: left; width: 175px;',
         '<div style="float: left; width: 110px;'),
    ],
}
