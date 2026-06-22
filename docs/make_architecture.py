"""Render the FoodieRobot system architecture diagram to docs/architecture.png.

Pure-Pillow renderer (no graphviz/matplotlib needed). Supersampled 2x for
crisp text and edges.
"""
import math
from PIL import Image, ImageDraw, ImageFont

SS = 2                      # supersample factor
W, H = 1760, 1180          # logical canvas
IMG = Image.new("RGB", (W * SS, H * SS), "#FFFFFF")
D = ImageDraw.Draw(IMG)

# ---- fonts -------------------------------------------------------------
def font(size, bold=False):
    candidates = (
        ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf"]
        if bold else
        ["/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]
    )
    for p in candidates:
        try:
            return ImageFont.truetype(p, size * SS)
        except Exception:
            continue
    return ImageFont.load_default()

F_TITLE = font(40, True)
F_SUB   = font(20)
F_BOX   = font(23, True)
F_SMALL = font(17)
F_TINY  = font(15)
F_TAG   = font(16, True)

# ---- colors ------------------------------------------------------------
ALI    = "#FF6A00"   # Alibaba Cloud orange
BLUE   = "#1F6FEB"   # backend
GREEN  = "#2DA44E"   # database
PURPLE = "#8957E5"   # AI / Qwen
TEAL   = "#0E7490"   # frontend
GRAY   = "#57606A"   # external
INK    = "#1B1F24"
LINE   = "#8C959F"

def lighten(hexc, f=0.90):
    r = int(hexc[1:3], 16); g = int(hexc[3:5], 16); b = int(hexc[5:7], 16)
    r = int(r + (255 - r) * f); g = int(g + (255 - g) * f); b = int(b + (255 - b) * f)
    return (r, g, b)

# ---- primitives (logical coords) --------------------------------------
def s(v): return int(v * SS)

def rrect(x, y, w, h, radius=14, fill="#FFFFFF", outline=INK, width=2):
    D.rounded_rectangle([s(x), s(y), s(x + w), s(y + h)],
                        radius=s(radius), fill=fill, outline=outline, width=max(1, s(width)))

def text_center(cx, y, txt, fnt, fill=INK):
    w = D.textlength(txt, font=fnt)
    D.text((s(cx) - w / 2, s(y)), txt, font=fnt, fill=fill)

def text_left(x, y, txt, fnt, fill=INK):
    D.text((s(x), s(y)), txt, font=fnt, fill=fill)

def box(cx, cy, w, h, title, lines, accent):
    x, y = cx - w / 2, cy - h / 2
    rrect(x, y, w, h, 14, fill=lighten(accent, 0.90), outline=accent, width=2)
    rrect(x, y, w, 6, 14, fill=accent, outline=accent, width=1)  # top accent bar
    text_center(cx, y + 14, title, F_BOX, INK)
    ty = y + 46
    for ln in lines:
        text_center(cx, ty, ln, F_SMALL, "#30363D")
        ty += 24
    return (x, y, x + w, y + h)

def arrow(p1, p2, color=LINE, width=3, two_way=False, label=None, dash=False):
    x1, y1 = s(p1[0]), s(p1[1]); x2, y2 = s(p2[0]), s(p2[1])
    if dash:
        # manual dashed line
        total = math.hypot(x2 - x1, y2 - y1); n = max(1, int(total / s(10)))
        for i in range(n):
            if i % 2: continue
            a = i / n; b = (i + 1) / n
            D.line([x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                    x1 + (x2 - x1) * b, y1 + (y2 - y1) * b], fill=color, width=max(1, s(width)))
    else:
        D.line([x1, y1, x2, y2], fill=color, width=max(1, s(width)))
    ang = math.atan2(y2 - y1, x2 - x1); ah = s(11)
    def head(hx, hy, a):
        D.polygon([(hx, hy),
                   (hx - ah * math.cos(a - 0.4), hy - ah * math.sin(a - 0.4)),
                   (hx - ah * math.cos(a + 0.4), hy - ah * math.sin(a + 0.4))], fill=color)
    head(x2, y2, ang)
    if two_way:
        head(x1, y1, ang + math.pi)
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        w = D.textlength(label, font=F_TINY)
        pad = 5
        D.rectangle([s(mx) - w/2 - s(pad), s(my) - s(10), s(mx) + w/2 + s(pad), s(my) + s(11)], fill="#FFFFFF")
        D.text((s(mx) - w/2, s(my) - s(8)), label, font=F_TINY, fill="#57606A")

# ---- header ------------------------------------------------------------
text_center(W/2, 28, "FoodieRobot — System Architecture", F_TITLE, INK)
text_center(W/2, 80, "WhatsApp food-ordering bot · Django backend on Alibaba Cloud · Qwen AI",
            F_SUB, "#57606A")

# ---- Alibaba Cloud boundary -------------------------------------------
AB_X, AB_Y, AB_W, AB_H = 470, 150, 1250, 900
rrect(AB_X, AB_Y, AB_W, AB_H, 22, fill="#FFF8F2", outline=ALI, width=3)
text_left(AB_X + 24, AB_Y + 16, "ALIBABA  CLOUD", F_TAG, ALI)

# ---- FRONTEND (left, outside cloud) -----------------------------------
b_users = box(220, 360, 250, 110, "WhatsApp Users",
              ["Customers chat via", "WhatsApp (mobile)"], TEAL)
b_wa = box(220, 560, 250, 120, "WhatsApp Business",
           ["Cloud API / webhooks", "(messaging frontend)"], TEAL)

# ---- ECS backend group -------------------------------------------------
EC_X, EC_Y, EC_W, EC_H = 520, 250, 430, 540
rrect(EC_X, EC_Y, EC_W, EC_H, 18, fill=lighten(BLUE, 0.94), outline=BLUE, width=2)
text_left(EC_X + 20, EC_Y + 14, "ECS  ·  Docker", F_TAG, BLUE)

cx_ec = EC_X + EC_W / 2
b_nginx = box(cx_ec, 370, 360, 86, "Nginx (TLS / HTTPS)",
              ["Reverse proxy · WebSocket"], BLUE)
b_web = box(cx_ec, 500, 360, 100, "Django App (Daphne ASGI)",
            ["REST + WhatsApp webhooks", "AI orchestrator & tools"], BLUE)
b_worker = box(cx_ec, 660, 360, 100, "Huey Worker",
               ["Async tasks: meal image", "analysis, embeddings"], BLUE)

# ---- Data tier ---------------------------------------------------------
b_pg = box(1180, 410, 300, 110, "RDS",
           ["PostgreSQL + PostGIS", "(app data, geo, vectors)"], GREEN)
b_redis = box(1180, 600, 300, 110, "Redis",
              ["Cache · task queue", "Channels layer"], GREEN)

# ---- Qwen Cloud --------------------------------------------------------
b_qwen = box(1180, 850, 360, 150, "Qwen Cloud",
             ["qwen-max  ·  chat + tool calling",
              "qwen-vl-max  ·  meal image vision",
              "text-embedding-v4  ·  embeddings"], PURPLE)

# ---- External SaaS -----------------------------------------------------
b_ext = box(1180, 215, 300, 96, "External SaaS",
            ["Cloudinary (media) · Vendy", " · Zoho (email)"], GRAY)

# ---- arrows ------------------------------------------------------------
# frontend chain
arrow((b_users[0]+125, b_users[3]), (b_wa[0]+125, b_wa[1]), TEAL, 3, two_way=True, label="messages")
# WhatsApp <-> nginx (into cloud)
arrow((b_wa[2], 560), (b_nginx[0], 372), TEAL, 3, two_way=True, label="HTTPS")
# nginx -> web
arrow((cx_ec, b_nginx[3]), (cx_ec, b_web[1]), BLUE, 3)
# web -> worker (enqueue via redis) shown as internal
arrow((cx_ec, b_web[3]), (cx_ec, b_worker[1]), BLUE, 3, two_way=True, label="enqueue")
# web -> postgres
arrow((b_web[2], 500), (b_pg[0], 410), GREEN, 3, two_way=True, label="SQL")
# web/worker -> redis
arrow((b_worker[2], 645), (b_redis[0], 600), GREEN, 3, two_way=True, label="queue/cache")
# web -> qwen
arrow((b_web[2], 520), (b_qwen[0], 845), PURPLE, 3, two_way=True, label="chat / embed")
# worker -> qwen (vision)
arrow((b_worker[2], 670), (b_qwen[0]+40, b_qwen[1]), PURPLE, 3, two_way=True, label="vision")
# web -> external
arrow((b_web[2], 480), (b_ext[0], 230), GRAY, 2, two_way=True, dash=True)

# ---- legend ------------------------------------------------------------
ly = 1095
items = [("Frontend / messaging", TEAL), ("Backend (ECS)", BLUE),
         ("Database & cache", GREEN), ("Qwen AI", PURPLE),
         ("External SaaS", GRAY)]
lx = 120
for name, c in items:
    D.rectangle([s(lx), s(ly), s(lx+26), s(ly+18)], fill=lighten(c,0.55), outline=c, width=s(2))
    D.text((s(lx+34), s(ly-1)), name, font=F_SMALL, fill=INK)
    lx += int(D.textlength(name, font=F_SMALL)/SS) + 90

# ---- save --------------------------------------------------------------
out = IMG.resize((W, H), Image.LANCZOS)
out.save("docs/architecture.png", "PNG")
print("wrote docs/architecture.png", out.size)
