#!/usr/bin/env python3
"""The World, 23 November 2026.

Draws a newspaper front page summing up Monday 23 November 2026 and
writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Pure Python standard library: the PNG encoder, the bitmap font and every
shape on the page are written here from scratch. No network access.
The program is deterministic: two runs write byte-identical files.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------- canvas
W, H = 1000, 1000

PAPER = (248, 244, 234)
INK = (22, 22, 20)
RED = (158, 32, 26)
NAVY = (24, 48, 88)
BLUE = (38, 84, 138)
SEA = (52, 96, 140)
SAND = (214, 196, 150)
GREY = (110, 108, 100)
ORANGE = (214, 110, 30)
GREEN = (46, 110, 60)

PIX = bytearray(W * H * 3)


def px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        PIX[i] = color[0]
        PIX[i + 1] = color[1]
        PIX[i + 2] = color[2]


def rect(x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            px(xx, yy, color)


def hline(x, y, w, color, t=1):
    rect(x, y, w, t, color)


def vline(x, y, h, color, t=1):
    rect(x, y, t, h, color)


def line(x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def circle(cx, cy, r, color, fill=False):
    x = 0
    y = r
    d = 3 - 2 * r
    while y >= x:
        if fill:
            for xx in range(cx - x, cx + x + 1):
                px(xx, cy + y, color)
                px(xx, cy - y, color)
            for xx in range(cx - y, cx + y + 1):
                px(xx, cy + x, color)
                px(xx, cy - x, color)
        else:
            for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                px(cx + sx, cy + sy, color)
        x += 1
        if d > 0:
            y -= 1
            d = d + 4 * (x - y) + 10
        else:
            d = d + 4 * x + 6


def triangle(x0, y0, x1, y1, x2, y2, color):
    # Fill a triangle by scanlines.
    pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
    (ax, ay), (bx, by), (cx, cy) = pts
    if ay == cy:
        return
    def edge(xa, ya, xb, yb, y):
        if yb == ya:
            return xa
        return xa + (xb - xa) * (y - ya) / (yb - ya)
    for y in range(ay, cy + 1):
        if y < by:
            xa = edge(ax, ay, bx, by, y)
            xb = edge(ax, ay, cx, cy, y)
        else:
            xa = edge(bx, by, cx, cy, y)
            xb = edge(ax, ay, cx, cy, y)
        lo, hi = int(min(xa, xb)), int(max(xa, xb))
        for xx in range(lo, hi + 1):
            px(xx, y, color)


# ---------------------------------------------------------------- font
# 5x7 bitmap font, uppercase only. '#' is a set pixel.
FONT = {
    'A': (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    'B': ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    'C': (" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"),
    'D': ("#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "),
    'E': ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    'F': ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    'G': (" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ### "),
    'H': ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    'I': ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"),
    'J': ("  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "),
    'K': ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    'L': ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    'M': ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    'N': ("#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"),
    'O': (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    'P': ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    'Q': (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    'R': ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    'S': (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    'T': ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    'U': ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    'V': ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    'W': ("#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"),
    'X': ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    'Y': ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    'Z': ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    '0': (" ### ", "#  ##", "# # #", "##  #", "#   #", "#   #", " ### "),
    '1': ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    '2': (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    '3': ("#### ", "    #", "    #", " ### ", "    #", "    #", "#### "),
    '4': ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    '5': ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    '6': (" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "),
    '7': ("#####", "    #", "   # ", "  #  ", "  #  ", "  #  ", "  #  "),
    '8': (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    '9': (" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "),
    '.': ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    ',': ("     ", "     ", "     ", "     ", " ##  ", " ##  ", " #   "),
    ':': ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "),
    ';': ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", " #   "),
    "'": ("  #  ", "  #  ", " #   ", "     ", "     ", "     ", "     "),
    '"': (" # # ", " # # ", "     ", "     ", "     ", "     ", "     "),
    '-': ("     ", "     ", "     ", " ### ", "     ", "     ", "     "),
    '(': ("   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "),
    ')': (" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "),
    '/': ("    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "),
    '%': ("#   #", "#  # ", "   # ", "  #  ", " #   ", "#  # ", "#   #"),
    '$': ("  #  ", " ####", "# #  ", " ### ", "  # #", "#### ", "  #  "),
    '&': (" ##  ", "#  # ", "#  # ", " #   ", "# # #", "#  # ", " ## #"),
    '!': ("  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "),
    '?': (" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "),
    '+': ("     ", "  #  ", "  #  ", " ### ", "  #  ", "  #  ", "     "),
    '=': ("     ", "     ", " ### ", "     ", " ### ", "     ", "     "),
    ' ': ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
}

CW = 6  # character advance in font units (5 px glyph + 1 px gap)


def text_w(s, scale):
    return len(s) * CW * scale - scale


def draw_char(x, y, ch, scale, color):
    glyph = FONT.get(ch)
    if glyph is None:
        return
    for row, bits in enumerate(glyph):
        for col, b in enumerate(bits):
            if b == '#':
                rect(x + col * scale, y + row * scale, scale, scale, color)


def draw_text(x, y, s, scale, color):
    cx = x
    for ch in s:
        draw_char(cx, y, ch, scale, color)
        cx += CW * scale
    return cx


def draw_centered(y, s, scale, color, cx=W // 2):
    x = cx - text_w(s, scale) // 2
    draw_text(x, y, s, scale, color)
    return x


def wrap(text, max_w, scale):
    """Greedy word wrap; returns a list of lines fitting max_w pixels."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if text_w(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def draw_para(x, y, text, max_w, scale, color, leading=None):
    if leading is None:
        leading = 9 * scale
    for ln in wrap(text, max_w, scale):
        draw_text(x, y, ln, scale, color)
        y += leading
    return y


# ---------------------------------------------------------------- icons
def icon_globe(x, y, s):
    circle(x + s // 2, y + s // 2, s // 2 - 2, NAVY)
    for dy in (-s // 4, 0, s // 4):
        line(x + 3, y + s // 2 + dy, x + s - 3, y + s // 2 + dy, NAVY)
    for dx in (-s // 4, 0, s // 4):
        line(x + s // 2 + dx, y + 3, x + s // 2 + dx, y + s - 3, NAVY)
    line(x + 4, y + s - 6, x + s - 4, y + 6, RED)  # the split


def icon_missile(x, y, s):
    triangle(x + s - 6, y + s // 2, x + 6, y + s // 2 - 8,
             x + 6, y + s // 2 + 8, INK)
    rect(x + 2, y + s // 2 - 3, 14, 6, INK)
    line(x + 10, y + s // 2 - 8, x + 2, y + s // 2 - 14, INK)
    line(x + 10, y + s // 2 + 8, x + 2, y + s // 2 + 14, INK)
    for i in range(3):
        px(x + s - 12 - i * 3, y + s // 2 - 4 - i, ORANGE)
        px(x + s - 12 - i * 3, y + s // 2 + 4 + i, ORANGE)


def icon_factory(x, y, s):
    rect(x + 4, y + s - 22, s - 8, 22, INK)
    for i in range(3):
        triangle(x + 6 + i * 16, y + s - 22, x + 14 + i * 16, y + s - 34,
                 x + 22 + i * 16, y + s - 22, INK)
    rect(x + s - 12, y + 4, 6, s - 22, INK)
    triangle(x + s - 16, y + 2, x + s - 4, y + 2, x + s - 10, y - 6, ORANGE)
    triangle(x + s - 14, y + 8, x + s - 6, y + 8, x + s - 10, y + 2, ORANGE)


def icon_boat(x, y, s):
    triangle(x + 4, y + s // 2, x + s - 4, y + s // 2,
             x + s - 14, y + s - 8, INK)
    triangle(x + 4, y + s // 2, x + s - 14, y + s - 8,
             x + 12, y + s - 8, INK)
    line(x + s // 2, y + 6, x + s // 2, y + s // 2, INK)
    line(x + s // 2, y + 6, x + s - 12, y + s // 2 - 6, INK)
    for i in range(3):
        line(x + 2 + i * 18, y + s - 4, x + 12 + i * 18, y + s - 4, BLUE)


def icon_building(x, y, s):
    rect(x + 8, y + 10, s - 16, s - 10, INK)
    triangle(x + 8, y + 10, x + s - 8, y + 10, x + s // 2, y + 2, INK)
    line(x + 10, y + 12, x + s // 2, y + s - 6, RED)
    line(x + s // 2, y + s - 6, x + s - 12, y + s // 2, RED)
    for r in range(3):
        for c in range(3):
            rect(x + 14 + c * 14, y + 18 + r * 14, 6, 6, PAPER)


def icon_ship(x, y, s):
    rect(x + 4, y + s // 2, s - 8, 14, INK)
    rect(x + s // 2 - 8, y + s // 2 - 12, 16, 12, INK)
    circle(x + s - 16, y + 8, 5, GREY, fill=True)
    circle(x + s - 22, y + 14, 4, GREY, fill=True)
    triangle(x + s - 24, y + 2, x + s - 14, y + 2, x + s - 19, y - 6, ORANGE)
    for i in range(3):
        line(x + 2 + i * 20, y + s - 4, x + 12 + i * 20, y + s - 4, BLUE)


def icon_mountain(x, y, s):
    triangle(x + 2, y + s - 4, x + s // 2 - 4, y + 6, x + s - 14, y + s - 4,
             INK)
    triangle(x + s // 2 + 2, y + s - 4, x + s - 8, y + 14,
             x + s - 2, y + s - 4, NAVY)
    line(x + s // 2 - 4, y + 6, x + s // 2 + 10, y + s - 4, RED)


# ---------------------------------------------------------------- page
def draw_page():
    rect(0, 0, W, H, PAPER)

    # ---- masthead
    draw_centered(18, "THE WORLD", 8, INK)
    hline(36, 88, W - 72, INK, 2)
    draw_centered(96, "MONDAY 23 NOVEMBER 2026", 3, INK)
    hline(36, 122, W - 72, INK, 4)
    hline(36, 128, W - 72, INK, 1)

    # ---- lead story
    y = 140
    draw_text(36, y, "GULF WAR WIDENS", 3, RED)
    y += 24
    y = draw_para(36, y,
                  "IRAN HITS US BASES IN BAHRAIN AS\n"
                  "TANKERS BURN IN HORMUZ",
                  W - 72, 4, INK, leading=30)
    y += 6
    lead_body = (
        "IRAN'S REVOLUTIONARY GUARD SAYS IT LAUNCHED MISSILE AND DRONE "
        "STRIKES ON US POSITIONS AT THE AL-RIFFA AND AWALI BASES IN "
        "BAHRAIN ON SATURDAY NIGHT, CLAIMING TWO PATRIOT RADARS "
        "DESTROYED. BAHRAIN SAYS ITS AIR DEFENCE INTERCEPTED SEVERAL "
        "ATTACKS, BUT A STRIKE HIT A CIVILIAN PLANT ON SITRA ISLAND, "
        "STARTING A FIRE; TWO PEOPLE WERE INJURED, ONE CRITICALLY. AT "
        "LEAST 25 TANKERS HAVE BEEN HIT IN AND AROUND THE STRAIT OF "
        "HORMUZ IN SEVEN DAYS, CHOKING OIL FLOWS THROUGH THE PASSAGE "
        "CARRYING A FIFTH OF THE WORLD'S OIL AND GAS."
    )
    body_w = 640
    # illustration: the strait, right of the lead body
    ix, iy, iw, ih = 700, y, 264, 150
    rect(ix, iy, iw, ih, SEA)
    rect(ix, iy + 110, iw, 40, SAND)  # shore
    # three tankers
    for tx, tw in ((ix + 14, 66), (ix + 96, 78), (ix + 186, 58)):
        rect(tx, iy + 84, tw, 14, INK)
        rect(tx + tw // 2 - 7, iy + 70, 14, 14, INK)
        rect(tx + 4, iy + 98, tw - 8, 3, PAPER)
    # missile arcs
    line(ix + 24, iy + 62, ix + 76, iy + 20, RED)
    line(ix + 76, iy + 20, ix + 128, iy + 58, RED)
    line(ix + 156, iy + 52, ix + 200, iy + 16, RED)
    line(ix + 200, iy + 16, ix + 244, iy + 50, RED)
    circle(ix + 76, iy + 20, 4, RED, fill=True)
    circle(ix + 200, iy + 16, 4, RED, fill=True)
    draw_text(ix + 8, iy + 6, "BAHRAIN", 2, PAPER)
    draw_text(ix, iy + ih + 6, "STRAIT OF HORMUZ", 2, INK)
    y = draw_para(36, y, lead_body, body_w, 2, INK, leading=16)
    y += 8
    hline(36, y, W - 72, INK, 2)
    y += 10

    # ---- grid stories, two columns, flowing down from the lead
    def story(x, top, col_w, headline, body, icon):
        icon(x, top, 56)
        yy = top
        yy = draw_para(x + 68, yy, headline, col_w - 68, 2, INK, leading=17)
        yy = draw_para(x + 68, yy + 2, body, col_w - 68, 2, GREY, leading=16)
        return yy

    col_w = (W - 72 - 28) // 2
    y1 = story(36, y, col_w,
               "COP31 COLLAPSES AS FOSSIL-FUEL ROW SPLITS SUMMIT",
               "THE ANTALYA CLIMATE CONFERENCE COLLAPSED ON SUNDAY AFTER "
               "MORE THAN TWO WEEKS OF TALKS, THE LONGEST COP IN HISTORY. "
               "NEARLY 200 COUNTRIES FAILED TO AGREE ON THE 'ANTALYA "
               "PACT'.",
               icon_globe)
    y2 = story(36 + col_w + 28, y, col_w,
               "ALL THREE OBJECTS THAT HIT POLAND WERE RUSSIAN MISSILES",
               "POLISH PROSECUTORS SAID ON SUNDAY THE THREE OBJECTS THAT "
               "CRASHED IN THE SOUTH-EAST WERE KH-101 CRUISE "
               "MISSILES, MADE IN LATE 2026 AT DUBNA NEAR MOSCOW. NO ONE "
               "WAS HURT.",
               icon_missile)
    y = max(y1, y2) + 8
    hline(36, y, W - 72, INK, 1)
    y += 8

    y1 = story(36, y, col_w,
               "24 BODY BAGS PULLED FROM BURNT CANDY FACTORY",
               "POLICE REMOVED 24 BODY BAGS FROM THE BURNT CANDY FACTORY "
               "IN CIKANDE, BANTEN, ON SUNDAY. FIRE TORE THROUGH THE "
               "BUILDING WHILE ABOUT 300 WORKERS WERE INSIDE.",
               icon_factory)
    y2 = story(36 + col_w + 28, y, col_w,
               "AT LEAST 24 DEAD AS FUNERAL BOAT CAPSIZES",
               "AT LEAST 24 DIED WHEN AN OVERCROWDED BOAT CARRYING "
               "MOURNERS TO A FUNERAL CAPSIZED IN THE NUN RIVER IN "
               "BAYELSA ON FRIDAY. 24 SURVIVORS WERE RESCUED.",
               icon_boat)
    y = max(y1, y2) + 8
    hline(36, y, W - 72, INK, 1)
    y += 8

    y1 = story(36, y, col_w,
               "KRYVYI RIH TOLL RISES TO 73 INJURED",
               "THE INJURED TOLL FROM RUSSIA'S 'TRIPLE-TAP' STRIKE ON "
               "KRYVYI RIH HAS RISEN TO 73, INCLUDING NINE CHILDREN. TWO "
               "WERE KILLED: A BOY OF SEVEN AND A PARAMEDIC.",
               icon_building)
    y2 = story(36 + col_w + 28, y, col_w,
               "RUSSIAN CARGO SHIP STILL BURNING IN GULF OF FINLAND",
               "THE SANCTIONED SPARTA II WAS STILL ON FIRE ON SUNDAY "
               "AFTER TWO SUSPECTED UKRAINIAN DRONES STRUCK IT ON "
               "SATURDAY OFF THE RUSSIAN COAST. FINLAND WARNED THE BLAZE "
               "COULD BURN FOR DAYS.",
               icon_ship)
    y = max(y1, y2) + 8
    hline(36, y, W - 72, INK, 2)
    y += 10

    # ---- Peru, full width
    icon_mountain(36, y, 48)
    yy = draw_para(36 + 68, y, "PERU COUNTS COST OF JUNIN QUAKE: ONE DEAD, 853 HOMELESS",
                   W - 72 - 68, 2, INK, leading=16)
    yy = draw_para(36 + 68, yy + 2,
                   "PERU'S CIVIL DEFENCE AGENCY CONFIRMED ONE DEATH AND 16 "
                   "INJURED AFTER THE QUAKE SHOOK THE CENTRAL ANDES ON "
                   "FRIDAY. 152 HOMES WERE LEFT UNINHABITABLE.",
                   W - 72 - 68, 2, GREY, leading=16)
    y = yy + 8
    hline(36, y, W - 72, INK, 2)
    y += 10

    # ---- bottom strip
    bx = 36 + 470
    top = y
    vline(bx - 14, top, 60, INK, 1)
    y = draw_para(36, top,
                  "BITCOIN: REBOUNDS ABOVE $60,000 AFTER A TWO-YEAR LOW "
                  "NEAR $55,000, UP ABOUT 9%.",
                  440, 2, INK, leading=16)
    y2 = draw_para(bx, top,
                   "US HOUSE: DEMOCRATS WIN THEIR LARGEST MAJORITY SINCE "
                   "1992, 258 SEATS TO 173.",
                   440, 2, INK, leading=16)
    return max(y, y2)


# ---------------------------------------------------------------- png
def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body +
                struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    end_y = draw_page()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, W, H, PIX)
    print("wrote %s %d bytes, content ends at y=%d of %d" % (path, size, end_y, H))


if __name__ == "__main__":
    main()
