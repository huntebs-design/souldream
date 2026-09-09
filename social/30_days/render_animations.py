"""Render lightweight looping previews for DilSe social posts."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
sys.path.insert(0, str(ROOT / "social" / "launch"))

from render_posts import COLOURS, SANS, SERIF_BOLD, font, fit_lines, rounded  # noqa: E402


SIZE = (540, 960)
INK = COLOURS["ink"]
CREAM = COLOURS["cream"]
PAPER = COLOURS["paper"]
MAROON = COLOURS["dark_jam"]
TEAL = COLOURS["teal"]
ROSE = COLOURS["rose"]
SAFFRON = COLOURS["soft_saffron"]


ANIMATIONS = {
    3: [
        ("WHAT DO I EVEN SAY?", "“You never help.”", "Start with the frustration."),
        ("MAKE IT SPECIFIC", "“Can you handle school notices, forms, fees and follow-up this month?”", "Name the complete responsibility."),
        ("A CLEAR REQUEST", "Task · owner · deadline · follow-up", "Practise your version."),
    ],
    9: [
        ("BEFORE THE FAMILY VISIT", "Pressure is easier to handle with a shared plan.", "Prepare before the question comes up."),
        ("WORDS TO PRACTISE", "“If they ask about our decision, can you answer first?”", "Ask for the exact support you need."),
        ("PRACTISE FIRST", "Support can be decided before entering the room.", "Start at baatdilse.com."),
    ],
    16: [
        ("THREE WAYS TO BEGIN", "“Can I tell you what has been weighing on me?”", "01"),
        ("THREE WAYS TO BEGIN", "“Could we make one decision together tonight?”", "02"),
        ("THREE WAYS TO BEGIN", "“I want to explain what I need without blaming you.”", "03"),
        ("CHOOSE ONE", "Change the words until they sound like you.", "Practise at baatdilse.com."),
    ],
    23: [
        ("PRACTISE THE DIFFICULT REPLY", "“Tum meri family ko pasand nahi karti.”", "Rehearse what may be hard to hear."),
        ("RETURN TO THE POINT", "“Main family ko reject nahi kar rahi. Main us ek decision ki baat kar rahi hoon.”", "Keep the event and request clear."),
        ("TRY ANOTHER RESPONSE", "Rehearsal helps when the real conversation changes direction.", "Use The Partner at baatdilse.com."),
    ],
}


def block(draw, text, box, path, max_size, min_size, colour, gap=8, align="left"):
    x, y, width, height = box
    selected = font(path, min_size)
    lines = [text]
    for size in range(max_size, min_size - 1, -1):
        candidate = font(path, size)
        candidate_lines = fit_lines(draw, text, candidate, width)
        line_height = candidate.getbbox("Ag")[3] - candidate.getbbox("Ag")[1]
        if len(candidate_lines) * line_height + max(0, len(candidate_lines) - 1) * gap <= height:
            selected = candidate
            lines = candidate_lines
            break
    line_height = selected.getbbox("Ag")[3] - selected.getbbox("Ag")[1]
    cursor = y
    for line in lines:
        anchor = "ma" if align == "center" else "la"
        tx = x + width / 2 if align == "center" else x
        draw.text((tx, cursor), line, font=selected, fill=colour, anchor=anchor)
        cursor += line_height + gap


def frame(day, index, total, heading, message, note):
    dark = index % 2 == 0
    background = MAROON if dark else CREAM
    primary = PAPER if dark else MAROON
    accent = SAFFRON if dark else ROSE
    panel = TEAL if dark else PAPER
    canvas = Image.new("RGB", SIZE, background)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 36), "DilSe", font=font(SERIF_BOLD, 34), fill=primary)
    draw.text((36, 84), f"DAY {day:02d}  ·  LOOP", font=font(SANS, 12), fill=accent)
    rounded(draw, (30, 145, 510, 750), 30, panel)
    block(draw, heading, (62, 195, 400, 110), SERIF_BOLD, 38, 25, PAPER if dark else MAROON, gap=6)
    draw.line((62, 340, 190, 340), fill=accent, width=5)
    block(draw, message, (62, 385, 405, 235), SERIF_BOLD, 34, 22, PAPER if dark else INK, gap=8)
    block(draw, note, (62, 645, 400, 70), SANS, 20, 15, "#F1E5E8" if dark else INK, gap=5)
    rounded(draw, (70, 795, 470, 865), 35, accent)
    draw.text((270, 830), "BAATDILSE.COM", font=font(SANS, 18), fill=background, anchor="mm")
    for position in range(total):
        x1 = 36 + position * (468 / total)
        x2 = 36 + (position + 1) * (468 / total) - 6
        draw.rounded_rectangle((x1, 910, x2, 918), radius=4, fill=accent if position <= index else "#B79CA4")
    return canvas


def render():
    preview_images = []
    for day, content in ANIMATIONS.items():
        frames = [frame(day, index, len(content), *item) for index, item in enumerate(content)]
        day_dir = OUT / f"day-{day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)
        gif_path = day_dir / "animated-post.gif"
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=[1050] * (len(frames) - 1) + [1500],
            loop=0,
            optimize=True,
            disposal=2,
        )
        for index, image in enumerate(frames, start=1):
            image.save(day_dir / f"animation-frame-{index:02d}.png", optimize=True)
        preview_images.append(frames[0].resize((270, 480), Image.Resampling.LANCZOS))

    preview = Image.new("RGB", (1080, 480), "#D8CECA")
    for index, image in enumerate(preview_images):
        preview.paste(image, (index * 270, 0))
    preview.save(HERE / "animated-preview.png", optimize=True)
    print("Rendered", len(ANIMATIONS), "animated GIFs")


if __name__ == "__main__":
    render()
