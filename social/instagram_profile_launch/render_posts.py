from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "social" / "launch"))

from render_posts import (  # noqa: E402
    COLOURS,
    SANS,
    SERIF_BOLD,
    font,
    letterspaced,
    paragraph,
    rounded,
)


W, H = 1080, 1350
URL = "www.baatdilse.com"


def brand(draw, light=False):
    primary = COLOURS["paper"] if light else COLOURS["jam"]
    accent = COLOURS["soft_saffron"] if light else COLOURS["rose"]
    draw.text((72, 58), "DilSe", font=font(SERIF_BOLD, 58), fill=primary)
    letterspaced(draw, (75, 128), "FROM THE HEART  ·  DIL SE", font(SANS, 14), accent, 2)


def header(draw, post_number, label, light=False):
    primary = COLOURS["paper"] if light else COLOURS["jam"]
    accent = COLOURS["soft_saffron"] if light else COLOURS["rose"]
    draw.text((74, 202), f"POST {post_number:02d}", font=font(SANS, 18), fill=accent)
    draw.line((182, 215, 238, 215), fill=accent, width=3)
    letterspaced(draw, (260, 202), label.upper(), font(SANS, 16), accent, 3)
    return primary, accent


def footer(draw, post_number, light=False, page=None, pages=None):
    colour = COLOURS["paper"] if light else COLOURS["jam"]
    draw.line((72, 1254, 1008, 1254), fill=colour, width=2)
    draw.text((72, 1273), URL, font=font(SANS, 20), fill=colour)
    suffix = f"{page}/{pages}" if page and pages else f"{post_number:02d}"
    draw.text((1008, 1273), suffix, font=font(SANS, 20), fill=colour, anchor="ra")


def cta(draw, background, foreground, text="START A CONVERSATION"):
    rounded(draw, (72, 1104, 490, 1188), 42, background)
    draw.text((281, 1146), text, font=font(SANS, 20), fill=foreground, anchor="mm")


def render_post_1():
    canvas = Image.new("RGB", (W, H), COLOURS["dark_jam"])
    draw = ImageDraw.Draw(canvas)

    woman = Image.open(ROOT / "assets" / "dilse-woman-letter.png").convert("RGB")
    crop = woman.crop((230, 0, 1122, 1402)).resize((615, 968), Image.Resampling.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, crop.width, crop.height), radius=140, fill=255)
    canvas.paste(crop, (465, 382), mask)

    draw.ellipse((850, 105, 1150, 405), fill=COLOURS["teal"])
    draw.rectangle((0, 978, 535, 1350), fill=COLOURS["jam"])
    brand(draw, light=True)
    header(draw, 1, "Who DilSe is for", light=True)
    y = paragraph(
        draw,
        (72, 275),
        "A place to find the words for a difficult conversation.",
        font(SERIF_BOLD, 55),
        COLOURS["paper"],
        410,
        12,
    )
    paragraph(
        draw,
        (74, y + 30),
        "AI relationship guidance and conversation practice for women in Pakistan.",
        font(SANS, 24),
        "#EAD8DE",
        355,
        9,
    )
    cta(draw, COLOURS["soft_saffron"], COLOURS["dark_jam"])
    footer(draw, 1, light=True)
    canvas.save(OUT / "01-who-dilse-is-for.png", quality=95)


def render_post_2():
    canvas = Image.new("RGB", (W, H), COLOURS["cream"])
    draw = ImageDraw.Draw(canvas)
    brand(draw)
    header(draw, 2, "Two ways to begin")
    paragraph(
        draw,
        (72, 275),
        "Talk it through. Then practise it.",
        font(SERIF_BOLD, 66),
        COLOURS["jam"],
        900,
        12,
    )

    rounded(draw, (72, 505, 1008, 785), 42, COLOURS["teal"])
    draw.ellipse((112, 557, 190, 635), fill=COLOURS["soft_saffron"])
    draw.text((151, 596), "1", font=font(SERIF_BOLD, 40), fill=COLOURS["teal"], anchor="mm")
    draw.text((226, 548), "The Listener", font=font(SERIF_BOLD, 42), fill=COLOURS["paper"])
    paragraph(
        draw,
        (226, 617),
        "Sort through what happened, name what you need, and find a clear way to say it.",
        font(SANS, 26),
        "#E3EFEB",
        690,
        10,
    )

    rounded(draw, (72, 815, 1008, 1095), 42, COLOURS["blush"], COLOURS["rose"], 2)
    draw.ellipse((112, 867, 190, 945), fill=COLOURS["jam"])
    draw.text((151, 906), "2", font=font(SERIF_BOLD, 40), fill=COLOURS["paper"], anchor="mm")
    draw.text((226, 858), "The Partner", font=font(SERIF_BOLD, 42), fill=COLOURS["jam"])
    paragraph(
        draw,
        (226, 927),
        "Rehearse the conversation with a character before you speak to the real person.",
        font(SANS, 26),
        "#604853",
        690,
        10,
    )
    footer(draw, 2)
    canvas.save(OUT / "02-listener-and-partner.png", quality=95)


CAROUSEL = [
    ("HOW DILSE WORKS", "Start with one message.", "See what happens after you begin."),
    ("01", "Choose a mode", "Talk it through with The Listener\nor rehearse with The Partner."),
    ("02", "Describe the situation", "Share only the details needed to\nunderstand the concern."),
    ("03", "Answer one focused question", "Clarify what happened, what is\nuncertain, or what you need."),
    ("04", "Review and adapt the words", "Change the suggested wording\nuntil it sounds natural in your voice."),
    ("PLEASE NOTE", "Guidance and practice", "DilSe does not provide licensed therapy or emergency support."),
]


def progress(draw, page, pages, colour):
    gap = 12
    total_width = 936
    segment = (total_width - gap * (pages - 1)) / pages
    for index in range(pages):
        x1 = 72 + index * (segment + gap)
        fill = colour if index < page else "#D9C9CC"
        draw.rounded_rectangle((x1, 1190, x1 + segment, 1202), radius=6, fill=fill)


def render_post_3():
    palettes = [
        (COLOURS["teal"], COLOURS["paper"], COLOURS["soft_saffron"], True),
        (COLOURS["cream"], COLOURS["jam"], COLOURS["rose"], False),
        (COLOURS["blush"], COLOURS["jam"], COLOURS["rose"], False),
        (COLOURS["dark_jam"], COLOURS["paper"], COLOURS["soft_saffron"], True),
        (COLOURS["cream"], COLOURS["jam"], COLOURS["rose"], False),
        (COLOURS["teal"], COLOURS["paper"], COLOURS["soft_saffron"], True),
    ]
    pages = len(CAROUSEL)

    for page, ((label, title, body), (background, primary, accent, light)) in enumerate(zip(CAROUSEL, palettes), start=1):
        canvas = Image.new("RGB", (W, H), background)
        draw = ImageDraw.Draw(canvas)
        brand(draw, light=light)
        header(draw, 3, label, light=light)

        if page == 1:
            rounded(draw, (62, 290, 1018, 1065), 62, COLOURS["jam"])
            draw.text((118, 345), "4", font=font(SERIF_BOLD, 175), fill=accent)
            paragraph(draw, (118, 570), title, font(SERIF_BOLD, 72), COLOURS["paper"], 800, 14)
            paragraph(draw, (120, 790), body, font(SANS, 36), "#F1E5E8", 760, 10)
            draw.text((800, 982), "SWIPE", font=font(SANS, 24), fill=accent)
            draw.polygon([(930, 994), (885, 968), (885, 1020)], fill=accent)
        elif page == pages:
            rounded(draw, (62, 290, 1018, 1080), 62, COLOURS["jam"])
            draw.ellipse((755, 345, 965, 555), fill=accent)
            draw.text((860, 450), "D", font=font(SERIF_BOLD, 86), fill=COLOURS["jam"], anchor="mm")
            paragraph(draw, (118, 425), title, font(SERIF_BOLD, 67), COLOURS["paper"], 600, 14)
            paragraph(draw, (120, 735), body, font(SANS, 37), "#F1E5E8", 760, 11)
            rounded(draw, (118, 930, 735, 1035), 52, accent)
            draw.text((426, 982), "START A CONVERSATION", font=font(SANS, 25), fill=COLOURS["jam"], anchor="mm")
        else:
            rounded(draw, (62, 290, 1018, 1080), 58, COLOURS["paper"])
            rounded(draw, (62, 290, 260, 1080), 58, COLOURS["teal"])
            draw.rectangle((180, 290, 260, 1080), fill=COLOURS["teal"])
            draw.text((160, 445), label, font=font(SERIF_BOLD, 70), fill=accent, anchor="mm")
            draw.line((115, 525, 205, 525), fill=accent, width=8)
            draw.text((160, 575), f"{page}/{pages}", font=font(SANS, 23), fill=COLOURS["paper"], anchor="mm")
            paragraph(draw, (320, 370), title, font(SERIF_BOLD, 60), COLOURS["jam"], 600, 14)
            draw.line((320, 655, 520, 655), fill=accent, width=8)
            draw.multiline_text(
                (320, 710),
                body,
                font=font(SANS, 36),
                fill=COLOURS["ink"],
                spacing=14,
            )

        progress(draw, page, pages, accent)
        footer(draw, 3, light=light, page=page, pages=pages)
        canvas.save(OUT / f"03-how-dilse-works-slide-{page:02d}.png", quality=95)


def render_all():
    render_post_1()
    render_post_2()
    render_post_3()
    print(f"Rendered Instagram profile launch set to {OUT}")


if __name__ == "__main__":
    render_all()
