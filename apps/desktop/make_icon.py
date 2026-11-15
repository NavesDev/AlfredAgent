# Draws the app icon: Alfred's dark glass orb with a spectral band (same palette as CssOrb).
import sys
from PIL import Image, ImageDraw, ImageFilter

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ball = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(ball)
for r in range(470, 0, -2):
    t = r / 470
    c = int(4 + 14 * (1 - t))
    d.ellipse((S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r), fill=(c, c + 2, c + 6, 255))
band = Image.new("RGBA", (S, S), (0, 0, 0, 0))
stops = [(0.15, (217, 91, 86)), (0.35, (255, 162, 76)), (0.5, (255, 244, 224)), (0.62, (147, 241, 255)), (0.82, (53, 105, 250))]
bd = ImageDraw.Draw(band)
for x in range(S):
    f = x / S
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if a <= f <= b:
            k = (f - a) / (b - a)
            col = tuple(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
            break
    else:
        continue
    edge = min(f - 0.15, 0.82 - f) / 0.12
    h = 70 * max(0.0, min(1.0, edge))
    bd.line((x, S / 2 - h, x, S / 2 + h), fill=col + (255,))
band = band.filter(ImageFilter.GaussianBlur(28))
ball.alpha_composite(band)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse((42, 42, S - 42, S - 42), fill=255)
img.paste(ball, (0, 0), mask)
rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(rim).ellipse((44, 44, S - 44, S - 44), outline=(255, 255, 255, 70), width=6)
img.alpha_composite(rim.filter(ImageFilter.GaussianBlur(3)))
shine = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(shine).ellipse((300, 110, 640, 290), fill=(255, 255, 255, 46))
shine = shine.filter(ImageFilter.GaussianBlur(40))
img.paste(Image.alpha_composite(img, shine), (0, 0), mask)
img.save(sys.argv[1])
