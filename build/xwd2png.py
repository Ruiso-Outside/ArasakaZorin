"""Converte os .xwd do preview_plymouth.sh em PNG (e monta uma folha de contato). Uso: python -I xwd2png.py <pasta> [colunas]"""
import struct, sys
from pathlib import Path
from PIL import Image
d = Path(sys.argv[1]); cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
frames = []
for f in sorted(d.glob("f-*.xwd")):
    b = f.read_bytes()
    hs, _, _, depth, w, h = struct.unpack(">6I", b[:24]); bpl = struct.unpack(">I", b[48:52])[0]; nc = struct.unpack(">I", b[76:80])[0]
    off = hs + nc * 12
    im = Image.frombuffer("RGBX", (w, h), b[off:off + bpl * h], "raw", "BGRX", bpl, 1).convert("RGB")
    im.save(f.with_suffix(".png")); f.unlink(); frames.append(im)
if frames:
    w, h = frames[0].size; s = 480 / w; tw, th = int(w * s), int(h * s)
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * 6, ((len(frames) + cols - 1) // cols) * (th + 6)), (40, 40, 40))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th)), ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
    sheet.save(d / "folha.png")
print(len(frames), "quadros")
