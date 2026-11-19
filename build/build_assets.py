#!/usr/bin/env python3
"""
ARASAKA // Gerador de assets do tema para Zorin OS.

Gera: logo (SVG/PNG), wallpapers, fundo do login, tema do GRUB (imagens),
imagens do Plymouth, cursores Xcursor, icones, sons e o logo ASCII do terminal.

Requer apenas Pillow (pip install pillow). Roda em Windows ou Linux.
Uso: python build/build_assets.py
"""
import math
import os
import random
import struct
import wave
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "theme"

# ---------------------------------------------------------------- paleta
RED = (227, 18, 31)
RED_HI = (255, 36, 54)
RED_DIM = (90, 8, 14)
BLACK = (5, 5, 6)
WHITE = (236, 236, 240)
GRAY = (130, 130, 140)
GRAY_D = (70, 70, 78)
CYAN = (0, 220, 255)

random.seed(2077)

# ---------------------------------------------------------------- fontes
WINF = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
FONT_CANDIDATES = {
    "cedge": [T / "fonts/cedge1.ttf"],
    "ui": [WINF / "bahnschrift.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")],
    "mono": [WINF / "consola.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")],
    "monob": [WINF / "consolab.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")],
    "jp": [WINF / "YuGothB.ttc", WINF / "msgothic.ttc",
           Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")],
}


def font(kind, size, variation=None):
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            f = ImageFont.truetype(str(p), size)
            if variation:
                try:
                    f.set_variation_by_name(variation)
                except Exception:
                    pass
            return f
    raise SystemExit(f"Fonte '{kind}' nao encontrada")


def ui(size, weight="SemiBold"):
    return font("ui", size, weight)


# ---------------------------------------------------------------- utilitarios
def save(img, rel):
    p = T / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p, optimize=True)
    return p


def colorize(mask, color, opacity=1.0):
    """mask L -> imagem RGBA na cor dada."""
    im = Image.new("RGBA", mask.size, color + (0,))
    a = mask if opacity >= 1 else mask.point(lambda v: int(v * opacity))
    im.putalpha(a)
    return im


def text_size(txt, fnt, spacing=0):
    w = 0
    for ch in txt:
        w += fnt.getlength(ch) + spacing
    w -= spacing if txt else 0
    asc, desc = fnt.getmetrics()
    return int(math.ceil(w)), asc + desc


def draw_text(img, xy, txt, fnt, fill, spacing=0, anchor="lt"):
    """Texto com espacamento entre letras. anchor: l/m/r + t/m/b."""
    d = ImageDraw.Draw(img)
    w, h = text_size(txt, fnt, spacing)
    x, y = xy
    if anchor[0] == "m":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    for ch in txt:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + spacing
    return w, h


def text_image(txt, fnt, color, spacing=0, pad=4):
    w, h = text_size(txt, fnt, spacing)
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    draw_text(im, (pad, pad), txt, fnt, color + (255,) if len(color) == 3 else color, spacing)
    return im


def paste(dst, src, center):
    """Compoe 'src' centralizado em 'center' (aceita sair das bordas)."""
    x = int(round(center[0] - src.width / 2))
    y = int(round(center[1] - src.height / 2))
    tmp = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    tmp.paste(src, (x, y))
    dst.alpha_composite(tmp)


# ---------------------------------------------------------------- logo
# Geometria medida do logo de referencia (sistema de 1000 unidades).
RING_C, RING_R, RING_IN = (499.5, 499.5), 463, 399
CIRCLES = [(499, 263, 144), (262, 463, 144.5), (737, 463, 144.5)]
STEM = (464, 263, 535, 884)
ARMS = [((262, 463), (499.5, 700.5)), ((737, 463), (499.5, 700.5))]
ARM_W = 71


def logo_mask(size, ring=True, ss=4):
    """Mascara L do logo; 'size' = diametro externo do anel em px."""
    S = size * ss
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    k = S / (RING_R * 2)
    ox, oy = RING_C[0] - RING_R, RING_C[1] - RING_R

    def P(x, y):
        return ((x - ox) * k, (y - oy) * k)

    def circ(cx, cy, r, fill=255):
        x, y = P(cx, cy)
        d.ellipse([x - r * k, y - r * k, x + r * k, y + r * k], fill=fill)

    if ring:
        circ(*RING_C, RING_R)
        circ(*RING_C, RING_IN, fill=0)
    for c in CIRCLES:
        circ(*c)
    d.rectangle([*P(STEM[0], STEM[1]), *P(STEM[2], STEM[3])], fill=255)
    for (x0, y0), (x1, y1) in ARMS:
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / L * ARM_W / 2, (x1 - x0) / L * ARM_W / 2
        d.polygon([P(x0 + nx, y0 + ny), P(x1 + nx, y1 + ny), P(x1 - nx, y1 - ny), P(x0 - nx, y0 - ny)], fill=255)
    return im.resize((size, size), Image.LANCZOS)


def logo(size, color=RED, ring=True, opacity=1.0):
    return colorize(logo_mask(size, ring), color, opacity)


def logo_glow(size, pad, color=RED, blur=None, strength=1.4):
    m = logo_mask(size)
    canvas = Image.new("L", (size + pad * 2, size + pad * 2), 0)
    canvas.paste(m, (pad, pad))
    a = canvas.filter(ImageFilter.GaussianBlur(blur or size / 14)).point(lambda v: min(255, int(v * strength)))
    return colorize(a, color)


def logo_svg(color="#e3121f", ring=True, bg=None, view=1000, extra=""):
    ox, oy = RING_C[0] - RING_R, RING_C[1] - RING_R
    k = view / (RING_R * 2)

    def p(x, y):
        return f"{(x - ox) * k:.1f},{(y - oy) * k:.1f}"

    parts = []
    if bg:
        parts.append(bg)
    if ring:
        c = view / 2
        r_mid = (RING_R + RING_IN) / 2 * k
        parts.append(f'<circle cx="{c}" cy="{c}" r="{r_mid:.1f}" fill="none" stroke="{color}" '
                     f'stroke-width="{(RING_R - RING_IN) * k:.1f}"/>')
    for cx, cy, r in CIRCLES:
        x, y = p(cx, cy).split(",")
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r * k:.1f}" fill="{color}"/>')
    x0, y0 = p(STEM[0], STEM[1]).split(",")
    x1, y1 = p(STEM[2], STEM[3]).split(",")
    parts.append(f'<rect x="{x0}" y="{y0}" width="{float(x1) - float(x0):.1f}" '
                 f'height="{float(y1) - float(y0):.1f}" fill="{color}"/>')
    for (ax, ay), (bx, by) in ARMS:
        L = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / L * ARM_W / 2, (bx - ax) / L * ARM_W / 2
        pts = " ".join([p(ax + nx, ay + ny), p(bx + nx, by + ny), p(bx - nx, by - ny), p(ax - nx, ay - ny)])
        parts.append(f'<polygon points="{pts}" fill="{color}"/>')
    parts.append(extra)
    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{view}" height="{view}" '
            f'viewBox="0 0 {view} {view}">\n  {body}\n</svg>\n')


# ---------------------------------------------------------------- fundos
def base_bg(W, H, center=(0.5, 0.5), tint=(48, 3, 6), grid=True, noise=True, scan=True, gstep=64):
    im = Image.new("RGBA", (W, H), BLACK + (255,))
    # brilho radial vermelho escuro
    rg = Image.radial_gradient("L").resize((W * 2, H * 2), Image.BICUBIC)
    rg = rg.crop((W - int(W * center[0]), H - int(H * center[1]),
                  W - int(W * center[0]) + W, H - int(H * center[1]) + H))
    rg = rg.point(lambda v: max(0, 255 - int(v * 1.25)))
    im.alpha_composite(colorize(rg, tint))
    d = ImageDraw.Draw(im)
    if grid:
        for x in range(0, W, gstep):
            d.line([(x, 0), (x, H)], fill=(255, 30, 45, 15 if x % (gstep * 4) else 30))
        for y in range(0, H, gstep):
            d.line([(0, y), (W, y)], fill=(255, 30, 45, 15 if y % (gstep * 4) else 30))
    if noise:
        n = Image.effect_noise((W, H), 28).point(lambda v: max(0, v - 128) * 2)
        im.alpha_composite(colorize(n, (255, 255, 255), 0.045))
    if scan:
        sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sl)
        for y in range(0, H, 3):
            sd.line([(0, y), (W, y)], fill=(0, 0, 0, 60))
        im.alpha_composite(sl)
    # vinheta
    vg = Image.radial_gradient("L").resize((W, H), Image.BICUBIC).point(lambda v: max(0, int((v - 120) * 1.6)))
    im.alpha_composite(colorize(vg, (0, 0, 0), 0.85))
    return im


def brackets(im, m, L, w, color, alpha=255):
    d = ImageDraw.Draw(im)
    W, H = im.size
    c = color + (alpha,)
    for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        d.line([(x, y), (x + sx * L, y)], fill=c, width=w)
        d.line([(x, y), (x, y + sy * L)], fill=c, width=w)


def barcode(im, x, y, w, h, color, seed=1):
    r = random.Random(seed)
    d = ImageDraw.Draw(im)
    cx = x
    while cx < x + w:
        bw = r.choice([1, 1, 2, 3, 4])
        if r.random() > 0.35:
            d.rectangle([cx, y, cx + bw - 1, y + h], fill=color)
        cx += bw + r.choice([1, 2, 2, 3])


def cut_frame(im, box, cut, color, width=2):
    """Moldura com cantos cortados (estilo HUD)."""
    x0, y0, x1, y1 = box
    pts = [(x0 + cut, y0), (x1, y0), (x1, y1 - cut), (x1 - cut, y1), (x0, y1), (x0, y0 + cut), (x0 + cut, y0)]
    ImageDraw.Draw(im).line(pts, fill=color, width=width, joint="curve")


def hex_lines(r, n, cols):
    return [" ".join(f"{r.randrange(16 ** 4):04X}" for _ in range(cols)) for _ in range(n)]


def wallpaper_core(W=2560, H=1440):
    im = base_bg(W, H, center=(0.5, 0.42))
    s = 560
    cy = int(H * 0.42)
    paste(im, logo_glow(s, 160, strength=1.1), (W // 2, cy))
    paste(im, logo(s), (W // 2, cy))
    draw_text(im, (W // 2, cy + s // 2 + 90), "ARASAKA", font("cedge", 128), WHITE, spacing=34, anchor="mt")
    draw_text(im, (W // 2, cy + s // 2 + 260), "荒坂", font("jp", 44), RED, spacing=14, anchor="mt")
    draw_text(im, (W // 2, cy + s // 2 + 330), "SECURITY  ·  TECHNOLOGY  ·  ORDER", ui(22), GRAY,
              spacing=9, anchor="mt")
    brackets(im, 70, 90, 3, RED)
    f = font("mono", 19)
    draw_text(im, (110, 100), "SYS://ARASAKA.NET  /  SECURE NODE 0451", f, GRAY)
    draw_text(im, (110, 128), "SUBNET  NC-WATSON-07  ·  ENCRYPTION AES-4096", f, GRAY_D)
    draw_text(im, (W - 110, 100), "CLEARANCE LEVEL 05", f, RED, anchor="rt")
    draw_text(im, (W - 110, 128), "STATUS  ONLINE", f, GRAY_D, anchor="rt")
    draw_text(im, (110, H - 100), "© 2077 ARASAKA CORPORATION  ·  TOKYO  ·  NIGHT CITY", f, GRAY_D, anchor="lb")
    barcode(im, W - 420, H - 128, 310, 28, GRAY_D + (255,), seed=7)
    return im


def wallpaper_crimson(W=2560, H=1440):
    im = Image.new("RGBA", (W, H))
    top, bot = (205, 16, 28), (110, 5, 12)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    n = Image.effect_noise((W, H), 30).point(lambda v: max(0, v - 128) * 2)
    im.alpha_composite(colorize(n, (0, 0, 0), 0.10))
    big = logo(1750, (8, 4, 5), opacity=0.93)
    paste(im, big, (int(W * 0.70), int(H * 0.56)))
    jp = font("jp", 250)
    draw_text(im, (250, 170), "荒", jp, WHITE)
    draw_text(im, (250, 450), "坂", jp, WHITE)
    d = ImageDraw.Draw(im)
    d.line([(200, 160), (200, 760)], fill=WHITE, width=4)
    draw_text(im, (200, H - 250), "ARASAKA", font("cedge", 150), WHITE, spacing=30, anchor="lt")
    draw_text(im, (206, H - 100), "SECURITY  ·  TECHNOLOGY  ·  ORDER", ui(26), (20, 4, 6), spacing=10, anchor="lb")
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(0, H, 4):
        sd.line([(0, y), (W, y)], fill=(0, 0, 0, 22))
    im.alpha_composite(sl)
    return im


def glitchify(layer, r, bands=26, maxoff=60, split=10):
    W, H = layer.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # separacao de cor (fantasma ciano deslocado)
    a = layer.getchannel("A")
    cyan = colorize(a, CYAN, 0.45)
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tmp.paste(cyan, (-split, 0))
    out.alpha_composite(tmp)
    out.alpha_composite(layer)
    # fatias deslocadas
    y = 0
    res = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    while y < H:
        h = r.choice([2, 4, 6, 10, 18, 30, 50])
        off = r.randint(-maxoff, maxoff) if r.random() < 0.35 else 0
        band = out.crop((0, y, W, min(H, y + h)))
        res.paste(band, (off, y))
        y += h
    return res


def wallpaper_glitch(W=2560, H=1440):
    im = base_bg(W, H, grid=False, tint=(30, 2, 4))
    r = random.Random(13)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    paste(layer, logo(720), (W // 2, int(H * 0.44)))
    draw_text(layer, (W // 2, int(H * 0.44) + 470), "ARASAKA", font("cedge", 110), WHITE, spacing=30, anchor="mt")
    g = glitchify(layer, r, maxoff=50, split=12)
    im.alpha_composite(colorize(g.getchannel("A").filter(ImageFilter.GaussianBlur(30)), RED, 0.6))
    im.alpha_composite(g)
    d = ImageDraw.Draw(im)
    for _ in range(20):  # blocos de corrupcao
        x, y = r.randrange(W), r.randrange(H)
        w, h = r.randint(20, 380), r.randint(2, 14)
        c = r.choice([RED + (r.randint(40, 160),), CYAN + (r.randint(20, 90),), WHITE + (r.randint(10, 60),)])
        d.rectangle([x, y, x + w, y + h], fill=c)
    f = font("mono", 20)
    draw_text(im, (110, H - 140), "!! SIGNAL INTEGRITY: 37%", f, RED)
    draw_text(im, (110, H - 110), "!! UNAUTHORIZED NEURAL ACCESS DETECTED — TRACE ACTIVE", f, GRAY)
    for i, line in enumerate(hex_lines(r, 6, 6)):
        draw_text(im, (W - 110, 100 + i * 26), line, f, GRAY_D, anchor="rt")
    return im


def hud_rings(im, c, radii, color):
    d = ImageDraw.Draw(im)
    cx, cy = c
    for i, rr in enumerate(radii):
        box = [cx - rr, cy - rr, cx + rr, cy + rr]
        if i % 2 == 0:
            d.ellipse(box, outline=color + (110,), width=2)
        else:
            for a in range(0, 360, 12):
                d.arc(box, a, a + 7, fill=color + (150,), width=3)
    # marcacoes
    R = radii[-1] + 24
    for a in range(0, 360, 5):
        L = 22 if a % 45 == 0 else 9
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        d.line([(cx + ca * R, cy + sa * R), (cx + ca * (R + L), cy + sa * (R + L))],
               fill=color + (200 if a % 45 == 0 else 90,), width=2)


def wallpaper_hud(W=2560, H=1440):
    im = base_bg(W, H, center=(0.5, 0.5), tint=(36, 3, 6), gstep=80)
    c = (W // 2, H // 2)
    hud_rings(im, c, [230, 300, 380, 470], RED)
    paste(im, logo_glow(300, 100, strength=1.2), c)
    paste(im, logo(300), c)
    d = ImageDraw.Draw(im)
    d.line([(0, H // 2), (c[0] - 540, H // 2)], fill=RED + (120,), width=1)
    d.line([(c[0] + 540, H // 2), (W, H // 2)], fill=RED + (120,), width=1)
    r = random.Random(5)
    f = font("mono", 18)
    fb = font("monob", 20)
    draw_text(im, (120, 160), "TELEMETRY // NC-HQ", fb, RED)
    for i, line in enumerate(hex_lines(r, 14, 5)):
        draw_text(im, (120, 200 + i * 26), line, f, GRAY_D)
    labels = [("CORE TEMP", "34.1°C"), ("NET LOAD", "71%"), ("ICE LAYERS", "12/12"),
              ("DAEMONS", "ACTIVE"), ("SATELLITES", "06 LINKED"), ("THREAT", "LOW")]
    draw_text(im, (W - 120, 160), "SYSTEM STATUS", fb, RED, anchor="rt")
    for i, (k, v) in enumerate(labels):
        draw_text(im, (W - 420, 210 + i * 34), k, f, GRAY)
        draw_text(im, (W - 120, 210 + i * 34), v, f, WHITE, anchor="rt")
    draw_text(im, (W // 2, H - 120), "ARASAKA", font("cedge", 64), WHITE, spacing=20, anchor="mb")
    brackets(im, 60, 70, 2, RED)
    return im


def wallpaper_login(W=2560, H=1440):
    im = base_bg(W, H, center=(0.5, 0.5), tint=(40, 3, 6))
    paste(im, logo(1100, RED, opacity=0.10), (W // 2, H // 2))
    hud_rings(im, (W // 2, H // 2), [620, 660], RED_DIM)
    brackets(im, 70, 110, 3, RED)
    draw_text(im, (W // 2, 120), "ARASAKA", font("cedge", 72), WHITE, spacing=22, anchor="mt")
    draw_text(im, (W // 2, 225), "SECURE ACCESS TERMINAL", ui(24), RED, spacing=12, anchor="mt")
    draw_text(im, (W // 2, H - 110), "AUTHORIZED PERSONNEL ONLY  ·  ALL ACTIVITY IS MONITORED", ui(20),
              GRAY, spacing=8, anchor="mb")
    return im


# ---------------------------------------------------------------- GRUB
GRUB_W, GRUB_H = 1920, 1080
# caixa do menu em % (igual ao theme.txt)
MENU = dict(left=0.48, top=0.30, width=0.44, height=0.44)


def grub_assets():
    W, H = GRUB_W, GRUB_H
    im = base_bg(W, H, center=(0.25, 0.45), tint=(50, 3, 7), gstep=48)
    lc = (470, 450)
    paste(im, logo_glow(400, 130, strength=1.2), lc)
    paste(im, logo(400), lc)
    draw_text(im, (lc[0], lc[1] + 270), "ARASAKA", font("cedge", 78), WHITE, spacing=22, anchor="mt")
    draw_text(im, (lc[0], lc[1] + 380), "荒坂", font("jp", 32), RED, spacing=10, anchor="mt")
    x0 = int(W * MENU["left"]) - 26
    y0 = int(H * MENU["top"]) - 26
    x1 = int(W * (MENU["left"] + MENU["width"])) + 26
    y1 = int(H * (MENU["top"] + MENU["height"])) + 26
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 150))
    im.alpha_composite(panel)
    cut_frame(im, (x0, y0, x1, y1), 22, RED + (220,), 2)
    draw_text(im, (x0, y0 - 66), "BOOT SEQUENCE", ui(30, "Bold"), WHITE, spacing=8)
    draw_text(im, (x0, y0 - 30), "SELECT OPERATING SYSTEM  //  NODE 0451", font("mono", 16), GRAY)
    barcode(im, x1 - 220, y0 - 58, 220, 22, GRAY_D + (255,), seed=3)
    brackets(im, 40, 60, 2, RED)
    draw_text(im, (40 + 20, H - 50), "© ARASAKA CORPORATION  ·  SECURE BOOT LOADER", font("mono", 15), GRAY_D,
              anchor="lb")
    save(im.convert("RGB"), "grub/arasaka/background.png")

    def px(name, size, color):
        save(Image.new("RGBA", size, color), f"grub/arasaka/{name}.png")

    sel = (227, 18, 31, 80)
    for n in ["c", "n", "s"]:
        px(f"select_{n}", (4, 4) if n == "c" else (4, 1), sel)
    for n in ["w", "nw", "sw"]:
        px(f"select_{n}", (6, 4) if n == "w" else (6, 1), RED + (255,))
    for n in ["e", "ne", "se"]:
        px(f"select_{n}", (2, 4) if n == "e" else (2, 1), RED + (150,))
    for n in ["n", "s", "e", "w", "nw", "ne", "sw", "se"]:
        px(f"terminal_box_{n}", (2, 2), RED + (255,))
    px("terminal_box_c", (4, 4), (0, 0, 0, 235))
    for n in ["c", "n", "s"]:
        px(f"thumb_{n}", (4, 4) if n == "c" else (4, 1), RED + (255,))
    for n in ["c", "n", "s"]:
        px(f"scroll_{n}", (4, 4) if n == "c" else (4, 1), (40, 40, 46, 255))


# ---------------------------------------------------------------- Plymouth
PLY_STATUS_BOOT = [
    "INITIALIZING ARASAKA SUBSYSTEMS",
    "LOADING NEURAL KERNEL",
    "DECRYPTING SECURE PARTITIONS",
    "DEPLOYING ICE COUNTERMEASURES",
    "SYNCHRONIZING ORBITAL UPLINK",
    "ESTABLISHING NETWATCH HANDSHAKE",
    "VERIFYING EMPLOYEE CREDENTIALS",
    "SYSTEM READY",
]
PLY_STATUS_DOWN = ["TERMINATING SESSION", "PURGING VOLATILE MEMORY", "SECURING CORE"]


def hud_ring(D, symmetric, style, color=RED, ss=3):
    """Anel de HUD (D px) com simetria de 'symmetric' partes: girando 360/symmetric graus ele volta igual."""
    S = D * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    step = 360 / symmetric
    if style == "outer":
        r = S / 2 - 6 * ss
        for k in range(symmetric):
            a0 = k * step
            d.arc([c - r, c - r, c + r, c + r], a0 + 4, a0 + step * 0.55, fill=color + (235,), width=3 * ss)
            d.arc([c - r, c - r, c + r, c + r], a0 + step * 0.62, a0 + step * 0.70, fill=color + (150,), width=3 * ss)
            r2 = r - 14 * ss
            d.arc([c - r2, c - r2, c + r2, c + r2], a0 + step * 0.15, a0 + step * 0.40, fill=color + (110,), width=1 * ss)
            # marcador triangular na ponta de cada arco
            ang = math.radians(a0 + step * 0.55)
            px, py = c + (r + 9 * ss) * math.cos(ang), c + (r + 9 * ss) * math.sin(ang)
            d.ellipse([px - 3 * ss, py - 3 * ss, px + 3 * ss, py + 3 * ss], fill=color + (255,))
    else:
        r = S / 2 - 4 * ss
        for k in range(symmetric * 4):
            ang = math.radians(k * step / 4)
            long = k % 4 == 0
            r0 = r - (16 if long else 8) * ss
            d.line([(c + r0 * math.cos(ang), c + r0 * math.sin(ang)), (c + r * math.cos(ang), c + r * math.sin(ang))],
                   fill=color + (220 if long else 120,), width=(3 if long else 2) * ss)
        r3 = r - 26 * ss
        for k in range(symmetric):
            a0 = k * step
            d.arc([c - r3, c - r3, c + r3, c + r3], a0, a0 + step * 0.3, fill=color + (90,), width=2 * ss)
    im = im.resize((D, D), Image.LANCZOS)
    glow = im.filter(ImageFilter.GaussianBlur(D / 90))
    out = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out


def plymouth_assets():
    base = "plymouth/arasaka/"
    pdir = T / base
    for f in pdir.glob("*.png"):  # recomeça do zero (sobras de versões antigas não vão para o initramfs)
        f.unlink()
    # tudo desenhado para 1080p; o script escala para a tela
    S, C = 400, 440  # logo e o quadro dele
    lg = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    paste(lg, logo(S), (C // 2, C // 2))
    save(lg, base + "logo.png")
    cy = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    paste(cy, logo(S, color=CYAN, opacity=0.8), (C // 2, C // 2))
    save(cy, base + "logo_c.png")
    hot = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    paste(hot, logo(S, color=(255, 214, 214)), (C // 2, C // 2))
    save(hot, base + "logo_hot.png")
    G = 820
    gl = Image.new("RGBA", (G, G), (0, 0, 0, 0))
    paste(gl, logo_glow(S, (G - S) // 2, blur=46, strength=0.9), (G // 2, G // 2))
    save(gl, base + "glow.png")
    # anéis de HUD: 12 quadros de 5° (anel de 6 partes) e 6 quadros de 5° (anel de 12 partes)
    ra, rb = hud_ring(620, 6, "outer"), hud_ring(520, 12, "inner")
    for i in range(12):
        save(ra.rotate(-5 * i, resample=Image.BICUBIC).quantize(48, method=Image.FASTOCTREE), base + f"ringa{i:02d}.png")
    for i in range(6):
        save(rb.rotate(5 * i, resample=Image.BICUBIC).quantize(48, method=Image.FASTOCTREE), base + f"ringb{i}.png")
    # CRT: ponto e linha de luz
    dot = Image.radial_gradient("L").resize((140, 140), Image.BICUBIC).point(lambda v: max(0, 255 - int(v * 1.15)) ** 2 // 255)
    dimg = Image.new("RGBA", (140, 140), (255, 230, 230, 0))
    dimg.putalpha(dot)
    halo = colorize(Image.radial_gradient("L").resize((140, 140), Image.BICUBIC).point(lambda v: max(0, 255 - v)), RED)
    halo.alpha_composite(dimg)
    save(halo, base + "dot.png")
    L = Image.new("RGBA", (1200, 60), (0, 0, 0, 0))
    ld = ImageDraw.Draw(L)
    for y in range(60):
        k = math.exp(-((y - 29.5) / 9.0) ** 2)
        ld.line([(0, y), (1199, y)], fill=RED + (int(200 * k),))
    ld.rectangle([0, 28, 1199, 31], fill=(255, 225, 225, 255))
    fade = Image.linear_gradient("L").rotate(90, expand=True).resize((1200, 60))
    edge = fade.point(lambda v: min(255, int(min(v, 255 - v) * 4)))
    L.putalpha(ImageChops.multiply(L.getchannel("A"), edge))
    save(L, base + "line.png")
    # fundo 1080p (grade de neon, ruído, linhas de varredura, vinheta)
    # fundo 1080p: brilho radial, linhas de varredura leves e, por cima, a grade uniforme (a varredura não apaga a grade)
    bg = base_bg(1920, 1080, tint=(70, 4, 8), grid=False, noise=False, scan=False)
    sl = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(0, 1080, 4):
        sd.line([(0, y), (1919, y)], fill=(0, 0, 0, 38))
    bg.alpha_composite(sl)
    gr = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gr)
    for x in range(0, 1920, 60):
        gd.line([(x, 0), (x, 1079)], fill=(255, 40, 50, 11 if x % 240 else 22))
    for y in range(30, 1080, 60):
        gd.line([(0, y), (1919, y)], fill=(255, 40, 50, 11 if (y - 30) % 240 else 22))
    vg = Image.radial_gradient("L").resize(bg.size, Image.BICUBIC).point(lambda v: max(0, 255 - int(v * 1.3)))
    gr.putalpha(ImageChops.multiply(gr.getchannel("A"), vg))
    bg.alpha_composite(gr)
    save(bg.convert("RGB"), base + "bg.png")
    # textos
    save(text_image("ARASAKA", font("cedge", 68), WHITE, spacing=24), base + "title.png")
    save(text_image("荒坂", font("jp", 28), RED, spacing=10), base + "kanji.png")
    save(text_image("SECURITY  ·  TECHNOLOGY  ·  ORDER", ui(15), GRAY_D, spacing=6), base + "motto.png")
    f = ui(16)
    for i, st in enumerate(PLY_STATUS_BOOT):
        save(text_image(st, f, GRAY, spacing=5), base + f"status{i}.png")
    for i, st in enumerate(PLY_STATUS_DOWN):
        save(text_image(st, f, GRAY, spacing=5), base + f"down{i}.png")
    save(text_image("ARASAKA  //  OFFLINE", font("mono", 17), RED, spacing=4), base + "offline.png")
    fm = font("monob", 22)
    for n in range(10):
        save(text_image(str(n), fm, RED_HI), base + f"d{n}.png")
    save(text_image("%", fm, RED), base + "pct.png")
    save(text_image("ENTER DECRYPTION KEY", ui(17), RED, spacing=5), base + "pw_label.png")
    save(text_image("ARASAKA CORPORATION  //  SECURE BOOT", font("mono", 14), GRAY_D, spacing=1), base + "footer.png")
    save(Image.new("RGBA", (1, 1), (60, 14, 18, 255)), base + "bar_bg.png")
    save(Image.new("RGBA", (1, 1), RED + (255,)), base + "bar_fg.png")
    tip = Image.new("L", (60, 20), 0)
    ImageDraw.Draw(tip).ellipse([6, 6, 54, 14], fill=255)
    tipc = colorize(tip.filter(ImageFilter.GaussianBlur(4)), RED_HI)
    ImageDraw.Draw(tipc).rectangle([28, 9, 31, 10], fill=(255, 235, 235, 255))
    save(tipc, base + "bar_tip.png")
    box = Image.new("RGBA", (440, 50), (0, 0, 0, 230))
    cut_frame(box, (1, 1, 438, 48), 10, RED + (255,), 2)
    save(box, base + "pw_box.png")
    b = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    ImageDraw.Draw(b).rectangle([1, 1, 10, 10], fill=RED + (255,))
    save(b, base + "bullet.png")
    # feixe do scanner (linha fina passando pelo logo)
    beam = Image.new("RGBA", (4, 24), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    for y in range(24):
        bd.line([(0, y), (3, y)], fill=RED_HI + (int(170 * math.exp(-((y - 11.5) / 4.0) ** 2)),))
    save(beam, base + "beam.png")
    for name, (sx, sy) in {"tl": (1, 1), "tr": (-1, 1), "bl": (1, -1), "br": (-1, -1)}.items():
        c = Image.new("RGBA", (44, 44), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        x = 1 if sx > 0 else 42
        y = 1 if sy > 0 else 42
        d.line([(x, y), (x + sx * 40, y)], fill=RED + (230,), width=2)
        d.line([(x, y), (x, y + sy * 40)], fill=RED + (230,), width=2)
        save(c, base + f"corner_{name}.png")


def grub_bootlog():
    """theme/grub/arasaka/09_arasaka: painel de validação na caixa do terminal do GRUB (sobre o painel do menu)."""
    oks = [("Firmware handshake", "ACCEPTED"), ("Secure boot chain", "TRUSTED"), ("Microcode patch level", "CURRENT"),
           ("Kernel signature", "SHA-512 MATCH"), ("Initramfs integrity", "VERIFIED"), ("Memory sanitization", "COMPLETE"),
           ("ICE countermeasures", "ARMED"), ("Netwatch uplink", "AUTHORIZED"), ("Operator credentials", "VALIDATED")]
    rnd = random.Random(2077)
    hexrows = []
    for i, tag in enumerate(["KERNEL", "INITRD", "CMDLINE", "NEURAL"]):
        addr = 0x00100000 + i * 0x00400000
        bts = " ".join(f"{rnd.randrange(256):02X}" for _ in range(8))
        hexrows.append((f"0x{addr:08X}", bts, tag))
    q = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')
    out = []
    c = lambda col: out.append(f"  set color_normal={col}/black")
    e = lambda txt, nl=True: out.append(f'  echo {"" if nl else "-n "}"{q(txt)}"')
    c("light-red"); e(""); e("  ARASAKA SECURE BOOT LOADER  //  BUILD 2077.18")
    c("red"); e("  " + "-" * 56)
    c("dark-gray"); e("  TARGET    ", False); c("white"); out.append('  echo "$chosen"')
    c("dark-gray"); e("  PLATFORM  ", False); c("light-gray"); out.append('  echo "${grub_cpu}-${grub_platform}   ROOT ${root}"')
    e("")
    for a, b in oks:
        c("dark-gray"); e("  [", False); c("light-green"); e(" OK ", False); c("dark-gray"); e("]  ", False)
        c("light-gray"); e(a + " ", False); c("dark-gray"); e("." * max(3, 27 - len(a)) + " ", False); c("light-red"); e(b)
    e("")
    for addr, bts, tag in hexrows:
        c("red"); e(f"  {addr}  ", False); c("dark-gray"); e(f"{bts}  ", False); c("light-gray"); e(f"{tag:<8}", False)
        c("light-green"); e("  MAPPED")
    e("")
    c("light-red"); e("  >> ", False); c("white"); e("HANDING OFF TO NEURAL KERNEL", False); c("light-red"); e(" _")
    e("")
    c("light-red"); e("  [" + "|" * 36, False); c("dark-gray"); e("." * 10, False); c("light-red"); e("]  78%")
    body = "\n".join(out)
    script = f"""#! /bin/sh
# ARASAKA // painel de validação na caixa do terminal do GRUB (instalado em /etc/grub.d/09_arasaka pelo tema)
# Gerado por build/build_assets.py (parte "grub"); não edite à mão.
#
# Depois que uma entrada é escolhida, o GRUB mostra a caixa do terminal enquanto carrega o kernel e o
# initramfs, e com o boot silencioso ela ficava vazia. Toda entrada do Linux chama "load_video" logo no
# começo; este script roda depois do 00_header e redefine essa função: ela carrega o vídeo do mesmo jeito
# e, em seguida, desenha o logo Arasaka em ASCII e uma "validação de inicialização" colorida.
# Desligar: ./install.sh --sem-grub-log (ou apague /etc/grub.d/09_arasaka e rode sudo update-grub).
set -e

cat <<'EOF'
### ARASAKA: painel de validação de inicialização (tema Arasaka) ###
function arasaka_boot_log {{
  set arasaka_saved_color="$color_normal"
{body}
  set color_normal="$arasaka_saved_color"
}}
EOF

# a mesma função do 00_header, mais o painel no fim
if [ -n "${{GRUB_VIDEO_BACKEND}}" ]; then
  cat <<EOF
function load_video {{
  insmod ${{GRUB_VIDEO_BACKEND}}
  arasaka_boot_log
}}
EOF
else
  cat <<'EOF'
function load_video {{
  if [ x$feature_all_video_module = xy ]; then
    insmod all_video
  else
    insmod efi_gop
    insmod efi_uga
    insmod ieee1275_fb
    insmod vbe
    insmod vga
    insmod video_bochs
    insmod video_cirrus
  fi
  arasaka_boot_log
}}
EOF
fi
"""
    f = T / "grub/arasaka/09_arasaka"
    f.write_text(script, encoding="utf-8")
    f.chmod(0o755)


def extension_assets():
    """Ícone simbólico (uma cor, recolorido pelo GNOME) que a Arasaka FX põe no botão do menu do Zorin."""
    # o GNOME recolore ícones simbólicos forçando preenchimento em tudo: o anel vira uma coroa preenchida
    # (círculo de fora menos o de dentro, evenodd) em vez de um contorno, senão ele vira um disco cheio
    v, col = 16, "#333333"
    k = v / (RING_R * 2)
    c, ro, ri = v / 2, RING_R * k, RING_IN * k
    ring = (f'<path fill="{col}" fill-rule="evenodd" d="M{c - ro:.2f},{c:.2f} a{ro:.2f},{ro:.2f} 0 1,0 {2 * ro:.2f},0 '
            f'a{ro:.2f},{ro:.2f} 0 1,0 {-2 * ro:.2f},0 Z M{c - ri:.2f},{c:.2f} a{ri:.2f},{ri:.2f} 0 1,0 {2 * ri:.2f},0 '
            f'a{ri:.2f},{ri:.2f} 0 1,0 {-2 * ri:.2f},0 Z"/>')
    out = T / "extension/arasaka-fx@arasaka.local/arasaka-symbolic.svg"
    out.write_text(logo_svg(color=col, ring=False, view=v, extra=ring), encoding="utf-8")


# ---------------------------------------------------------------- cursores
def xcursor_write(path, frames_by_size):
    """frames_by_size: {nominal: [(img RGBA, xhot, yhot, delay_ms), ...]}"""
    chunks = []
    for nominal, frames in sorted(frames_by_size.items()):
        for img, xh, yh, delay in frames:
            w, h = img.size
            px = img.load()
            data = bytearray()
            for y in range(h):
                for x in range(w):
                    r, g, b, a = px[x, y]
                    r, g, b = r * a // 255, g * a // 255, b * a // 255  # pre-multiplicado
                    data += struct.pack("<I", (a << 24) | (r << 16) | (g << 8) | b)
            hdr = struct.pack("<IIIIIIIII", 36, 0xFFFD0002, nominal, 1, w, h, xh, yh, delay)
            chunks.append((nominal, hdr + bytes(data)))
    ntoc = len(chunks)
    out = bytearray(struct.pack("<4sIII", b"Xcur", 16, 0x10000, ntoc))
    pos = 16 + ntoc * 12
    for nominal, c in chunks:
        out += struct.pack("<III", 0xFFFD0002, nominal, pos)
        pos += len(c)
    for _, c in chunks:
        out += c
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


CUR_SS = 8


class Cur:
    """Desenha um cursor num grid de 32 unidades e renderiza em varios tamanhos."""

    def __init__(self):
        self.ops = []

    def poly(self, pts, fill=None, outline=None, width=0):
        self.ops.append(("poly", pts, fill, outline, width))
        return self

    def line(self, pts, fill, width):
        self.ops.append(("line", pts, fill, None, width))
        return self

    def ellipse(self, box, fill=None, outline=None, width=0):
        self.ops.append(("ell", box, fill, outline, width))
        return self

    def arc(self, box, a0, a1, fill, width):
        self.ops.append(("arc", (box, a0, a1), fill, None, width))
        return self

    def render(self, size, rot=0):
        S = size * CUR_SS
        k = S / 32
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for op, g, fill, outline, w in self.ops:
            ww = max(1, int(round(w * k)))
            if op == "poly":
                pts = [(x * k, y * k) for x, y in g]
                if fill:
                    d.polygon(pts, fill=fill)
                if outline:
                    d.line(pts + [pts[0]], fill=outline, width=ww, joint="curve")
            elif op == "line":
                d.line([(x * k, y * k) for x, y in g], fill=fill, width=ww, joint="curve")
            elif op == "ell":
                d.ellipse([v * k for v in g], fill=fill, outline=outline, width=ww)
            elif op == "arc":
                box, a0, a1 = g
                d.arc([v * k for v in box], a0, a1, fill=fill, width=ww)
        if rot:
            im = im.rotate(-rot, resample=Image.BICUBIC, center=(S / 2, S / 2))
        return im.resize((size, size), Image.LANCZOS)


R4 = RED + (255,)
K4 = (8, 8, 10, 255)
W4 = WHITE + (255,)


def cursor_shapes():
    s = {}
    arrow = [(3, 2), (3, 25), (9, 19.5), (13, 28), (17, 26.2), (13, 18), (21, 18)]
    s["default"] = (Cur().poly(arrow, fill=K4, outline=R4, width=1.6).line([(5.5, 7), (5.5, 18)], R4, 1.2), 3, 2)
    s["pointer"] = (Cur().poly(arrow, fill=R4, outline=K4, width=1.6).line([(5.5, 7), (5.5, 18)], W4, 1.2), 3, 2)
    ib = [(10, 4), (14, 4), (16, 6), (18, 4), (22, 4)]
    s["text"] = (Cur().line([(10, 4), (14, 4), (16, 6), (18, 4), (22, 4)], K4, 4.2)
                 .line([(10, 28), (14, 28), (16, 26), (18, 28), (22, 28)], K4, 4.2)
                 .line([(16, 6), (16, 26)], K4, 4.2)
                 .line(ib, R4, 1.8).line([(10, 28), (14, 28), (16, 26), (18, 28), (22, 28)], R4, 1.8)
                 .line([(16, 6), (16, 26)], R4, 1.8), 16, 16)
    s["crosshair"] = (Cur().line([(16, 2), (16, 12)], K4, 3.6).line([(16, 20), (16, 30)], K4, 3.6)
                      .line([(2, 16), (12, 16)], K4, 3.6).line([(20, 16), (30, 16)], K4, 3.6)
                      .line([(16, 2), (16, 12)], R4, 1.6).line([(16, 20), (16, 30)], R4, 1.6)
                      .line([(2, 16), (12, 16)], R4, 1.6).line([(20, 16), (30, 16)], R4, 1.6)
                      .ellipse([14.5, 14.5, 17.5, 17.5], fill=W4, outline=K4, width=0.8), 16, 16)
    s["not-allowed"] = (Cur().ellipse([4, 4, 28, 28], outline=K4, width=6).line([(8.5, 23.5), (23.5, 8.5)], K4, 6)
                        .ellipse([5, 5, 27, 27], outline=R4, width=3).line([(9, 23), (23, 9)], R4, 3), 16, 16)

    def dbl(c):  # seta dupla horizontal
        h = [(2, 16), (9, 9), (9, 13.5), (23, 13.5), (23, 9), (30, 16), (23, 23), (23, 18.5), (9, 18.5), (9, 23)]
        return c.poly(h, fill=R4, outline=K4, width=1.4)

    s["ew-resize"] = (dbl(Cur()), 16, 16)
    s["move"] = (Cur().poly([(16, 2), (21, 8), (18, 8), (18, 14), (24, 14), (24, 11), (30, 16), (24, 21), (24, 18),
                             (18, 18), (18, 24), (21, 24), (16, 30), (11, 24), (14, 24), (14, 18), (8, 18), (8, 21),
                             (2, 16), (8, 11), (8, 14), (14, 14), (14, 8), (11, 8)],
                            fill=R4, outline=K4, width=1.3), 16, 16)
    s["help"] = (Cur().poly(arrow, fill=K4, outline=R4, width=1.6)
                 .arc([18, 3, 28, 13], 180, 400, W4, 2.2).line([(25.8, 11.5), (23, 13.5), (23, 16)], W4, 2.2)
                 .ellipse([21.8, 18, 24.2, 20.4], fill=W4), 3, 2)
    s["grab"] = (Cur().poly([(8, 12), (8, 24), (12, 29), (22, 29), (26, 22), (26, 12), (23, 12), (23, 9), (20, 9),
                             (20, 7), (17, 7), (17, 9), (14, 9), (14, 12)], fill=K4, outline=R4, width=1.6)
                 .line([(14, 13), (14, 19)], R4, 1.2).line([(17, 10), (17, 19)], R4, 1.2)
                 .line([(20, 10), (20, 19)], R4, 1.2).line([(23, 13), (23, 19)], R4, 1.2), 16, 16)
    s["grabbing"] = (Cur().poly([(8, 14), (8, 24), (12, 29), (22, 29), (26, 22), (26, 14), (8, 14)],
                                fill=R4, outline=K4, width=1.6)
                     .line([(12, 14), (12, 18)], K4, 1.2).line([(16, 14), (16, 18)], K4, 1.2)
                     .line([(20, 14), (20, 18)], K4, 1.2), 16, 16)
    s["copy"] = (Cur().poly(arrow, fill=K4, outline=R4, width=1.6).ellipse([18, 18, 30, 30], fill=R4)
                 .line([(24, 20.5), (24, 27.5)], W4, 1.8).line([(20.5, 24), (27.5, 24)], W4, 1.8), 3, 2)
    s["alias"] = (Cur().poly(arrow, fill=K4, outline=R4, width=1.6).ellipse([18, 18, 30, 30], fill=R4)
                  .line([(21, 27), (27, 21)], W4, 1.8).line([(23, 21), (27, 21), (27, 25)], W4, 1.8), 3, 2)
    s["context-menu"] = (Cur().poly(arrow, fill=K4, outline=R4, width=1.6)
                         .poly([(18, 18), (30, 18), (30, 30), (18, 30)], fill=K4, outline=R4, width=1.2)
                         .line([(20.5, 22), (27.5, 22)], W4, 1.2).line([(20.5, 26), (27.5, 26)], W4, 1.2), 3, 2)
    s["pencil"] = (Cur().poly([(3, 29), (5, 22), (22, 5), (27, 10), (10, 27)], fill=K4, outline=R4, width=1.5)
                   .line([(19, 8), (24, 13)], R4, 1.4), 3, 29)
    return s


def spinner_frames(size, with_arrow, n=12):
    frames = []
    for i in range(n):
        c = Cur()
        if with_arrow:
            arrow = [(3, 2), (3, 25), (9, 19.5), (13, 28), (17, 26.2), (13, 18), (21, 18)]
            c.poly(arrow, fill=K4, outline=R4, width=1.6)
            box = [17, 17, 30, 30]
            c.ellipse(box, outline=(40, 40, 46, 255), width=3)
            c.arc(box, i * 30, i * 30 + 110, R4, 3)
        else:
            box = [4, 4, 28, 28]
            c.ellipse(box, outline=(30, 30, 36, 255), width=5)
            c.arc(box, i * 30, i * 30 + 100, R4, 5)
            c.arc([10, 10, 22, 22], -i * 45, -i * 45 + 160, W4, 2)
        frames.append(c.render(size))
    return frames


# nomes Xcursor/CSS -> forma base
CURSOR_LINKS = {
    "default": ["left_ptr", "arrow", "top_left_arrow", "x-cursor", "X_cursor", "draft_large", "draft_small",
                "right_ptr", "center_ptr", "cell", "plus", "vertical-text", "zoom-in", "zoom-out",
                "dnd-none", "dnd-move", "no-drop", "all-scroll"],
    "pointer": ["hand1", "hand2", "pointing_hand", "e29285e634086352946a0e7090d73106",
                "9d800788f1b08800ae810202380a0822"],
    "text": ["xterm", "ibeam"],
    "crosshair": ["cross", "tcross", "cross_reverse", "diamond_cross", "target", "dotbox", "icon"],
    "not-allowed": ["circle", "crossed_circle", "forbidden", "03b6e0fcb3499374a867c041f52298f0", "pirate"],
    "move": ["fleur", "size_all", "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"],
    "help": ["question_arrow", "whats_this", "left_ptr_help", "d9ce0ab605698f320427677b458ad60b",
             "5c6cd98b3f3ebcb1f9c7f1c204630408"],
    "grab": ["openhand", "fcf1c3c7cd4491d801f1e1c78f100000", "5aca4d189052212118709018842178c0"],
    "grabbing": ["closedhand", "dnd-none-grabbing", "208530c400c041818281048008011002"],
    "copy": ["dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872"],
    "alias": ["dnd-link", "link", "3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f"],
    "context-menu": [],
    "pencil": ["draft"],
    "wait": ["watch", "clock"],
    "progress": ["left_ptr_watch", "half-busy", "08e8e1c95fe2fc01f976f1e063a24ccd",
                 "3ecb610c1bf2410f44200f48c40d3599", "00000000000000020006000e7e9ffc3f"],
}
RESIZE = {  # nome: (rotacao em graus da seta dupla horizontal, aliases)
    "ew-resize": (0, ["sb_h_double_arrow", "h_double_arrow", "col-resize", "e-resize", "w-resize", "left_side",
                      "right_side", "size_hor", "split_h", "14fef782d02440884392942c11205230",
                      "028006030e0e7ebffc7f7070c0600140"]),
    "ns-resize": (90, ["sb_v_double_arrow", "v_double_arrow", "row-resize", "n-resize", "s-resize", "top_side",
                       "bottom_side", "size_ver", "split_v", "2870a09082c103050810ffdffffe0204",
                       "00008160000006810000408080010102"]),
    "nwse-resize": (45, ["bd_double_arrow", "nw-resize", "se-resize", "top_left_corner", "bottom_right_corner",
                         "size_fdiag", "c7088f0f3e6c8088236ef8e1e3e70000"]),
    "nesw-resize": (-45, ["fd_double_arrow", "ne-resize", "sw-resize", "top_right_corner", "bottom_left_corner",
                          "size_bdiag", "fcf1c3c7cd4491d801f1e1c78f100000x"]),
}


def cursor_assets():
    out = T / "cursors/Arasaka-Cursors/cursors"
    sizes = [24, 32, 48, 64]
    shapes = cursor_shapes()
    links = []
    for name, (cur, hx, hy) in shapes.items():
        if name == "ew-resize":
            continue
        fr = {sz: [(cur.render(sz), round(hx * sz / 32), round(hy * sz / 32), 0)] for sz in sizes}
        xcursor_write(out / name, fr)
        links += [(alias, name) for alias in CURSOR_LINKS.get(name, [])]
    dbl_shape = shapes["ew-resize"][0]
    for name, (rot, aliases) in RESIZE.items():
        fr = {sz: [(dbl_shape.render(sz, rot), sz // 2, sz // 2, 0)] for sz in sizes}
        xcursor_write(out / name, fr)
        links += [(a, name) for a in aliases if not a.endswith("x")]
    for name, arrow in [("wait", False), ("progress", True)]:
        fr = {}
        for sz in sizes:
            hx, hy = (round(3 * sz / 32), round(2 * sz / 32)) if arrow else (sz // 2, sz // 2)
            fr[sz] = [(f, hx, hy, 50) for f in spinner_frames(sz, arrow)]
        xcursor_write(out / name, fr)
        links += [(a, name) for a in CURSOR_LINKS[name]]
    (T / "cursors/Arasaka-Cursors/links.txt").write_text("\n".join(f"{a} {b}" for a, b in links) + "\n")
    (T / "cursors/Arasaka-Cursors/index.theme").write_text(
        "[Icon Theme]\nName=Arasaka-Cursors\nComment=Arasaka Corporation cursor set\nInherits=Adwaita\n")
    prev = Image.new("RGBA", (64 * 9 + 20, 150), (12, 12, 14, 255))
    x = 10
    for name in ["default", "pointer", "text", "crosshair", "move", "not-allowed", "help", "grab", "copy"]:
        prev.alpha_composite(shapes[name][0].render(64), (x, 10))
        x += 64
    x = 10
    for f in spinner_frames(64, False)[:3] + spinner_frames(64, True)[:3] + \
            [dbl_shape.render(64, r) for r in (0, 90, 45)]:
        prev.alpha_composite(f, (x, 80))
        x += 64
    save(prev, "../build/preview/cursores.png")


# ---------------------------------------------------------------- icones
def icon_assets():
    base = T / "icons/Arasaka"
    red_logo = logo_svg("#e3121f")
    for n in ["start-here", "distributor-logo", "zorin-logo", "zorin-os-logo", "arasaka"]:
        p = base / "scalable/apps" / f"{n}.svg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(red_logo, encoding="utf-8")
    sym = logo_svg("#bebebe", view=16)
    for n in ["start-here-symbolic", "distributor-logo-symbolic", "zorin-logo-symbolic"]:
        p = base / "symbolic/apps" / f"{n}.svg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sym, encoding="utf-8")
    term = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">\n'
        '  <path d="M14 10 H114 L120 16 V104 L106 118 H8 V16 Z" fill="#0a0a0c" stroke="#e3121f" stroke-width="4"/>\n'
        '  <rect x="8" y="10" width="112" height="16" fill="#e3121f"/>\n'
        '  <rect x="16" y="15" width="6" height="6" fill="#0a0a0c"/><rect x="26" y="15" width="6" height="6" '
        'fill="#0a0a0c"/>\n'
        '  <path d="M24 46 L44 62 L24 78" fill="none" stroke="#ff2436" stroke-width="8" stroke-linecap="square"/>\n'
        '  <rect x="52" y="74" width="30" height="8" fill="#ececf0"/>\n'
        '  <g transform="translate(84 80) scale(0.032)" opacity="0.9">'
        + logo_svg("#e3121f").split(">", 1)[1].rsplit("</svg>", 1)[0] + '</g>\n'
        '</svg>\n')
    for n in ["utilities-terminal", "org.gnome.Terminal", "org.gnome.Console", "org.gnome.Ptyxis", "terminal"]:
        (base / "scalable/apps" / f"{n}.svg").write_text(term, encoding="utf-8")
    # logos para outros usos
    (T / "logo").mkdir(exist_ok=True)
    (T / "logo/arasaka.svg").write_text(red_logo, encoding="utf-8")
    (T / "logo/arasaka-white.svg").write_text(logo_svg("#ececf0"), encoding="utf-8")
    save(logo(256), "logo/arasaka-256.png")
    save(logo(512), "logo/arasaka-512.png")
    # logo da tela de login (GDM): logo + nome
    g = Image.new("RGBA", (520, 120), (0, 0, 0, 0))
    paste(g, logo(100), (60, 60))
    draw_text(g, (140, 60), "ARASAKA", font("cedge", 52), WHITE, spacing=14, anchor="lm")
    save(g, "logo/arasaka-gdm.png")


# ---------------------------------------------------------------- sons
SR = 44100


def env_adsr(n, a, d, s, r):
    out = []
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    for i in range(n):
        if i < A:
            v = i / max(1, A)
        elif i < A + D:
            v = 1 - (1 - s) * (i - A) / max(1, D)
        elif i < n - R:
            v = s
        else:
            v = s * (n - i) / max(1, R)
        out.append(v)
    return out


def osc(freq, dur, kind="sine", f_end=None, detune=0.0):
    n = int(dur * SR)
    ph = 0.0
    out = []
    for i in range(n):
        f = freq if f_end is None else freq + (f_end - freq) * i / n
        f *= 1 + detune
        ph += f / SR
        x = ph % 1.0
        if kind == "sine":
            v = math.sin(2 * math.pi * x)
        elif kind == "square":
            v = 1.0 if x < 0.5 else -1.0
        elif kind == "saw":
            v = 2 * x - 1
        else:  # triangle
            v = 4 * abs(x - 0.5) - 1
        out.append(v)
    return out


def noise(dur):
    r = random.Random(int(dur * 1000))
    return [r.uniform(-1, 1) for _ in range(int(dur * SR))]


def mul(a, b):
    return [x * y for x, y in zip(a, b)]


def mix(dst, src, at=0.0, gain=1.0):
    o = int(at * SR)
    need = o + len(src)
    if len(dst) < need:
        dst.extend([0.0] * (need - len(dst)))
    for i, v in enumerate(src):
        dst[o + i] += v * gain
    return dst


def lowpass(sig, k=0.15):
    y = 0.0
    out = []
    for v in sig:
        y += k * (v - y)
        out.append(y)
    return out


def echo(sig, delay=0.12, fb=0.35, n=3):
    out = list(sig)
    for j in range(1, n + 1):
        mix(out, sig, delay * j, fb ** j)
    return out


def note(freq, dur, kind="sine", a=0.005, d=0.05, s=0.6, r=0.08, f_end=None, detune=0.0):
    sig = osc(freq, dur, kind, f_end, detune)
    return mul(sig, env_adsr(len(sig), a, d, s, r))


def write_wav(name, sig, gain=0.8):
    peak = max(1e-6, max(abs(v) for v in sig))
    g = gain / peak
    p = T / "sounds/Arasaka/stereo" / f"{name}.wav"
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for i, v in enumerate(sig):
            s = int(max(-1, min(1, v * g)) * 32767)
            frames += struct.pack("<hh", s, s)
        w.writeframes(bytes(frames))


def sound_assets():
    # login: acorde subindo com brilho
    s = []
    for i, f in enumerate([110, 164.81, 220, 329.63, 440]):
        mix(s, lowpass(note(f, 2.2 - i * 0.15, "saw", a=0.25, d=0.6, s=0.4, r=0.9, detune=0.003), 0.08), i * 0.12, 0.35)
    mix(s, note(880, 0.9, "sine", a=0.01, d=0.3, s=0.2, r=0.5, f_end=1760), 0.55, 0.15)
    mix(s, lowpass(noise(0.4), 0.3), 0.0, 0.08)
    write_wav("desktop-login", echo(s, 0.18, 0.3), 0.7)
    # logout: descendo
    s = []
    for i, f in enumerate([440, 329.63, 220, 110]):
        mix(s, lowpass(note(f, 0.9, "saw", a=0.02, d=0.3, s=0.4, r=0.4), 0.1), i * 0.14, 0.35)
    write_wav("desktop-logout", echo(s, 0.16, 0.25), 0.7)
    write_wav("service-login", echo(note(660, 0.25, "square", r=0.15, f_end=990), 0.09, 0.3), 0.4)
    write_wav("service-logout", echo(note(660, 0.25, "square", r=0.15, f_end=440), 0.09, 0.3), 0.4)
    # notificacao: dois bips digitais
    s = []
    mix(s, lowpass(note(1318.5, 0.07, "square", r=0.03), 0.4), 0, 0.5)
    mix(s, lowpass(note(1760, 0.11, "square", r=0.06), 0.4), 0.09, 0.5)
    s = echo(s, 0.11, 0.25, 2)
    for n in ["message-new-instant", "message", "message-new-email", "message-sent-instant"]:
        write_wav(n, s, 0.45)
    # sino / terminal
    s = lowpass(note(987.8, 0.12, "triangle", r=0.08), 0.5)
    write_wav("bell", s, 0.4)
    write_wav("bell-terminal", lowpass(note(740, 0.06, "square", r=0.03), 0.35), 0.3)
    write_wav("bell-window-system", s, 0.4)
    # aviso / erro
    s = []
    mix(s, lowpass(note(330, 0.14, "saw", r=0.05), 0.2), 0, 0.6)
    mix(s, lowpass(note(330, 0.14, "saw", r=0.05), 0.2), 0.18, 0.6)
    write_wav("dialog-warning", s, 0.5)
    s = []
    for k in range(3):
        mix(s, lowpass(note(140, 0.12, "square", r=0.04), 0.12), k * 0.15, 0.6)
    write_wav("dialog-error", s, 0.5)
    write_wav("dialog-information", lowpass(note(880, 0.15, "sine", r=0.1, f_end=1100), 0.5), 0.4)
    write_wav("dialog-question", lowpass(note(700, 0.18, "sine", r=0.1, f_end=1000), 0.5), 0.4)
    # completo
    s = []
    for i, f in enumerate([880, 1174.7, 1760]):
        mix(s, lowpass(note(f, 0.12, "square", r=0.07), 0.35), i * 0.07, 0.4)
    write_wav("complete", echo(s, 0.1, 0.25), 0.45)
    # dispositivos
    write_wav("device-added", lowpass(note(500, 0.18, "square", r=0.1, f_end=1200), 0.3), 0.4)
    write_wav("device-removed", lowpass(note(1200, 0.18, "square", r=0.1, f_end=500), 0.3), 0.4)
    write_wav("power-plug", lowpass(note(300, 0.2, "saw", r=0.1, f_end=900), 0.2), 0.4)
    write_wav("power-unplug", lowpass(note(900, 0.2, "saw", r=0.1, f_end=300), 0.2), 0.4)
    write_wav("battery-low", echo(lowpass(note(220, 0.25, "square", r=0.1), 0.15), 0.3, 0.4), 0.5)
    # volume / clique
    write_wav("audio-volume-change", lowpass(note(1500, 0.035, "square", a=0.001, r=0.02), 0.5), 0.35)
    # captura de tela: obturador digital
    s = []
    mix(s, mul(lowpass(noise(0.08), 0.6), env_adsr(int(0.08 * SR), 0.001, 0.02, 0.3, 0.05)), 0, 0.6)
    mix(s, note(2000, 0.05, "square", r=0.03), 0.06, 0.2)
    write_wav("screen-capture", s, 0.4)
    write_wav("camera-shutter", s, 0.4)
    # lixeira
    s = mul(lowpass(noise(0.45), 0.25), env_adsr(int(0.45 * SR), 0.01, 0.1, 0.5, 0.3))
    write_wav("trash-empty", s, 0.4)
    write_wav("window-attention", lowpass(note(1046.5, 0.18, "triangle", r=0.1), 0.5), 0.4)
    (T / "sounds/Arasaka/index.theme").write_text(
        "[Sound Theme]\nName=Arasaka\nComment=Arasaka Corporation system sounds\n"
        "Inherits=freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n")


# ---------------------------------------------------------------- terminal
def terminal_logo():
    n = 40
    m = logo_mask(n * 4).resize((n, n), Image.LANCZOS)
    px = m.load()
    lines = []
    for y in range(0, n, 2):
        row = ""
        for x in range(n):
            top = px[x, y] > 110
            bot = px[x, y + 1] > 110 if y + 1 < n else False
            row += "█" if top and bot else "▀" if top else "▄" if bot else " "
        lines.append(row)
    p = T / "terminal/logo.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    """Sem argumentos gera tudo; com nomes (ex.: plymouth grub) gera só essas partes."""
    import sys
    only = set(sys.argv[1:])
    (ROOT / "build/preview").mkdir(parents=True, exist_ok=True)
    steps = [
        ("logo e icones", icon_assets),
        ("wallpapers", None),
        ("grub", grub_assets),
        ("grub-log", grub_bootlog),
        ("plymouth", plymouth_assets),
        ("extensao", extension_assets),
        ("cursores", cursor_assets),
        ("sons", sound_assets),
        ("logo do terminal", terminal_logo),
    ]
    for name, fn in steps:
        if only and name not in only and name.split()[0] not in only:
            continue
        print(f"[ARASAKA] gerando {name}...", flush=True)
        if fn:
            fn()
        else:
            for fname, f in [("arasaka-core", wallpaper_core), ("arasaka-crimson", wallpaper_crimson),
                             ("arasaka-glitch", wallpaper_glitch), ("arasaka-hud", wallpaper_hud),
                             ("arasaka-login", wallpaper_login)]:
                im = f().convert("RGB")
                save(im, f"backgrounds/{fname}.png")
                im.resize((640, 360), Image.LANCZOS).save(ROOT / f"build/preview/{fname}.png")
    print("[ARASAKA] pronto.")


if __name__ == "__main__":
    main()
