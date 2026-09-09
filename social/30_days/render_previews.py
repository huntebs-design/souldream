"""Build contact sheets for quick review of the DilSe campaign."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
BACKGROUND = "#DDD4D0"


def lead_asset(day):
    folder = ASSETS / f"day-{day:02d}"
    for name in ("editorial-feed.png", "feed.png", "feed-urdu.png", "slide-01.png", "reel-cover.png", "story-01.png"):
        path = folder / name
        if path.exists():
            return path
    raise FileNotFoundError(folder)


def thumbnail(path, size):
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#F6F1EC")
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def campaign_preview():
    cell = (216, 290)
    canvas = Image.new("RGB", (cell[0] * 6, cell[1] * 5), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    label_font = ImageFont.load_default(size=14)
    for index, day in enumerate(range(1, 31)):
        x = (index % 6) * cell[0]
        y = (index // 6) * cell[1]
        canvas.paste(thumbnail(lead_asset(day), (200, 250)), (x + 8, y + 5))
        draw.text((x + 8, y + 262), f"Day {day:02d}", font=label_font, fill="#24181D")
    canvas.save(HERE / "campaign-preview.png", optimize=True)


def carousel_preview():
    slides = sorted(ASSETS.glob("day-*/slide-*.png"))
    columns = 8
    cell = (160, 220)
    rows = (len(slides) + columns - 1) // columns
    canvas = Image.new("RGB", (cell[0] * columns, cell[1] * rows), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    label_font = ImageFont.load_default(size=11)
    for index, path in enumerate(slides):
        x = (index % columns) * cell[0]
        y = (index // columns) * cell[1]
        canvas.paste(thumbnail(path, (148, 185)), (x + 6, y + 4))
        draw.text((x + 6, y + 194), f"{path.parent.name} · {path.stem}", font=label_font, fill="#24181D")
    canvas.save(HERE / "carousel-preview.png", optimize=True)


if __name__ == "__main__":
    campaign_preview()
    carousel_preview()
    print("Updated campaign and carousel previews")
