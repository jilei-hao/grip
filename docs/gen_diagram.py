"""Generate grip communication diagram as PNG (polling-only architecture)."""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 780
img = Image.new("RGB", (W, H), (16, 18, 30))
d = ImageDraw.Draw(img)

MONO   = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def font(size, bold=False):
    return ImageFont.truetype(MONO_B if bold else MONO, size)

# ── Palette ──────────────────────────────────────────────────────────
BG_LOCAL  = (20, 24, 46)
BDR_LOCAL = (55, 75, 140)
BG_BOX    = (26, 32, 60)
BG_SLACK  = (54, 18, 60)
BDR_SLACK = (140, 50, 160)
BG_CLAUDE = (55, 20, 14)
BDR_CLAUDE= (180, 80, 40)
BG_LOG    = (20, 50, 32)
BDR_LOG   = (50, 140, 70)
BG_PROF   = (36, 28, 56)
BDR_PROF  = (100, 70, 160)

C_WHITE  = (240, 242, 255)
C_DIM    = (140, 148, 190)
C_GREEN  = (80, 210, 120)
C_BLUE   = (80, 160, 255)
C_ORANGE = (230, 170, 50)
C_CYAN   = (60, 200, 210)


def rbox(x, y, w, h, bg, border, radius=10, title=None, lines=None):
    d.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=bg, outline=border, width=2)
    ty = y + 14
    if title:
        d.text((x+w//2, ty), title, fill=C_WHITE, font=font(13, bold=True), anchor="mt")
        ty += 22
    if lines:
        for ln in lines:
            d.text((x+w//2, ty), ln, fill=C_DIM, font=font(11), anchor="mt")
            ty += 16


def arrowhead(x2, y2, angle, color, size=9):
    for sign in [1, -1]:
        ax = x2 - size * math.cos(angle - sign * 0.42)
        ay = y2 - size * math.sin(angle - sign * 0.42)
        d.line([(x2, y2), (ax, ay)], fill=color, width=2)


def draw_arrow(p1, p2, color, label=None, loff=(0, -13), dashed=False, width=2):
    x1, y1 = p1
    x2, y2 = p2
    angle = math.atan2(y2 - y1, x2 - x1)
    if dashed:
        length = math.hypot(x2-x1, y2-y1)
        dash, gap = 9, 5
        t = 0
        while t < length:
            t0, t1 = t, min(t+dash, length)
            sx = x1 + (x2-x1)*t0/length
            sy = y1 + (y2-y1)*t0/length
            ex = x1 + (x2-x1)*t1/length
            ey = y1 + (y2-y1)*t1/length
            d.line([(sx,sy),(ex,ey)], fill=color, width=width)
            t += dash + gap
    else:
        d.line([p1, p2], fill=color, width=width)
    arrowhead(x2, y2, angle, color)
    if label:
        mx = (x1+x2)//2 + loff[0]
        my = (y1+y2)//2 + loff[1]
        bb = font(10).getbbox(label)
        pw, ph = bb[2]-bb[0]+6, bb[3]-bb[1]+4
        d.rectangle([mx-pw//2, my-ph//2, mx+pw//2, my+ph//2], fill=(16,18,30))
        d.text((mx, my), label, fill=color, font=font(10), anchor="mm")


# ══════════════════════════════════════════════════════════════════════
# Layout
# ══════════════════════════════════════════════════════════════════════

# Local machine backdrop
d.rounded_rectangle([18, 30, 800, 740], radius=18, fill=BG_LOCAL, outline=BDR_LOCAL, width=2)
d.text((409, 42), "LOCAL MACHINE", fill=(70, 90, 170), font=font(12, bold=True), anchor="mt")

# Title
d.text((W//2, 6), "GRIP  ·  Communication Architecture", fill=C_WHITE, font=font(16, bold=True), anchor="mt")

# grip CLI
GX, GY, GW, GH = 50, 70, 340, 210
rbox(GX, GY, GW, GH, BG_BOX, BDR_LOCAL, title="grip  (CLI)", lines=[
    "grip run",
    "  1. fetch papers from sources",
    "  2. score & rank with Claude",
    "  3. post digest to Slack",
    "grip --update-profile",
    "  4. poll Slack for reactions",
    "  5. read feedback_log/",
    "  6. update profile via Claude",
])

# Paper Fetchers
FX, FY, FW, FH = 430, 70, 330, 100
rbox(FX, FY, FW, FH, BG_BOX, (50, 90, 150), title="Paper Fetchers", lines=[
    "arXiv · PubMed",
    "bioRxiv · Semantic Scholar",
])

# feedback_log
LX, LY, LW, LH = 290, 410, 240, 80
rbox(LX, LY, LW, LH, BG_LOG, BDR_LOG, title="feedback_log/", lines=[
    "YYYY-MM-DD.jsonl",
])

# interest_profile
PX, PY, PW, PH = 290, 570, 240, 70
rbox(PX, PY, PW, PH, BG_PROF, BDR_PROF, title="interest_profile.txt", lines=[
    "updated weekly by Claude",
])

# ── External boxes ────────────────────────────────────────────────────────────

# Slack
KX, KY, KW, KH = 880, 100, 280, 220
rbox(KX, KY, KW, KH, BG_SLACK, BDR_SLACK, title="Slack", lines=[
    "receives digest posts",
    "",
    "poll endpoint:",
    "  reactions:read",
    "  channels:history",
    "(thread replies)",
])

# Claude API
CX, CY, CW, CH = 880, 400, 280, 160
rbox(CX, CY, CW, CH, BG_CLAUDE, BDR_CLAUDE, title="Claude  API", lines=[
    "• score & rank papers",
    "• generate summaries",
    "• update interest profile",
    "  (weekly, from feedback)",
])

# ══════════════════════════════════════════════════════════════════════
# Arrows
# ══════════════════════════════════════════════════════════════════════

# grip → Fetchers
draw_arrow((GX+GW, GY+40), (FX, FY+40), C_CYAN, label="fetch papers", loff=(0,-13))
# Fetchers → grip (papers back)
draw_arrow((FX, FY+62), (GX+GW, GY+62), C_DIM, label="papers", loff=(0,13))

# grip → Slack (post digest)
draw_arrow((GX+GW, GY+100), (KX, KY+60), C_BLUE, label="POST digest", loff=(0,-13))

# grip → Claude (score + profile update)
draw_arrow((GX+GW//2, GY+GH), (GX+GW//2, 700), C_ORANGE)
draw_arrow((GX+GW//2, 700), (CX, CY+CH//2), C_ORANGE, label="score papers / update profile", loff=(0,-13))

# grip → Slack (poll reactions, dashed)
draw_arrow((GX+GW, GY+160), (KX, KY+180), C_ORANGE, label="poll reactions (HTTPS)", loff=(0,13), dashed=True)

# Slack poll result → feedback_log
draw_arrow((KX, KY+200), (LX+LW, LY+40), C_ORANGE, label="reactions / thread replies", loff=(0,-13), dashed=True)

# feedback_log → grip (read)
draw_arrow((LX+LW//2, LY), (GX+GW//2, GY+GH), C_GREEN, label="read log", loff=(50, 0))

# feedback_log → interest_profile
draw_arrow((LX+LW//2, LY+LH), (PX+PW//2, PY), C_GREEN)

# interest_profile → grip (load)
draw_arrow((PX, PY+PH//2), (GX, GY+GH-30), C_DIM, label="load profile", loff=(-55, 0))

# ── Legend ─────────────────────────────────────────────────────────────
ly = 716
items = [
    (C_CYAN,   False, "fetch / data"),
    (C_BLUE,   False, "Slack notify"),
    (C_ORANGE, False, "Claude API calls"),
    (C_ORANGE, True,  "Slack polling"),
    (C_GREEN,  False, "feedback log I/O"),
    (C_DIM,    False, "profile load"),
]
d.text((40, ly-16), "Legend:", fill=C_WHITE, font=font(11, bold=True))
for i, (c, dash, txt) in enumerate(items):
    cx = 40 + i * 185
    p1, p2 = (cx+65, ly+6), (cx+105, ly+6)
    draw_arrow(p1, p2, c, dashed=dash)
    d.text((cx+108, ly+6), txt, fill=C_DIM, font=font(10), anchor="lm")

out = "/home/jileihao/dev/grip/docs/architecture.png"
img.save(out)
print(f"Saved: {out}  ({W}×{H})")
