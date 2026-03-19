"""Generate icon.ico for UltimatePing Windows exe."""
from PIL import Image, ImageDraw

sz = 256
img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

m = sz // 16
d.ellipse([m, m, sz - m, sz - m], fill=(15, 19, 25, 255))
d.ellipse([m, m, sz - m, sz - m], outline=(99, 102, 241, 255), width=8)

cx, cy = sz // 2, sz // 2
bolt = [
    (cx - 10, cy - 70), (cx + 30, cy - 10), (cx + 5, cy - 10),
    (cx + 20, cy + 70), (cx - 20, cy + 10), (cx - 2, cy + 10),
]
d.polygon(bolt, fill=(99, 102, 241, 255))

inner = [
    (cx - 5, cy - 55), (cx + 20, cy - 10), (cx + 5, cy - 5),
    (cx + 12, cy + 55), (cx - 12, cy + 12), (cx, cy + 12),
]
d.polygon(inner, fill=(129, 140, 248, 255))

img48 = img.resize((48, 48), Image.LANCZOS)
img32 = img.resize((32, 32), Image.LANCZOS)
img16 = img.resize((16, 16), Image.LANCZOS)

img.save(
    "icon.ico", format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    append_images=[img48, img32, img16],
)
print("icon.ico created")
