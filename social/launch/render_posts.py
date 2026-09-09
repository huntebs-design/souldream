from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
W, H = 1080, 1350

COLOURS = {
    "jam": "#571F35",
    "dark_jam": "#351323",
    "rose": "#B85C73",
    "blush": "#F1E4E5",
    "cream": "#FBF4EC",
    "paper": "#FFF9F2",
    "ink": "#2E2026",
    "teal": "#184F4A",
    "saffron": "#E6A15A",
    "soft_saffron": "#F0B46F",
}

SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SERIF_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
SANS = "/System/Library/Fonts/Avenir Next.ttc"


def font(path, size, index=0):
    return ImageFont.truetype(path, size=size, index=index)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def fit_lines(draw, text, fnt, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paragraph(draw, xy, text, fnt, fill, max_width, line_gap=12):
    x, y = xy
    lines = fit_lines(draw, text, fnt, max_width)
    line_h = fnt.getbbox("Ag")[3] - fnt.getbbox("Ag")[1]
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h + line_gap
    return y


def letterspaced(draw, xy, text, fnt, fill, spacing=3):
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=fnt, fill=fill)
        x += draw.textlength(char, font=fnt) + spacing


def brand(draw, light=False, x=72, y=65):
    primary = COLOURS["paper"] if light else COLOURS["jam"]
    accent = COLOURS["soft_saffron"] if light else COLOURS["rose"]
    draw.text((x, y), "DilSe", font=font(SERIF_BOLD, 58), fill=primary)
    letterspaced(draw, (x + 3, y + 69), "FROM THE HEART  ·  DIL SE", font(SANS, 14), accent, 2)


def footer(draw, number, light=False):
    c = COLOURS["paper"] if light else COLOURS["jam"]
    draw.line((72, 1264, 1008, 1264), fill=c, width=2)
    draw.text((72, 1280), "www.baatdilse.com", font=font(SANS, 22), fill=c)
    draw.text((957, 1280), f"0{number}", font=font(SANS, 20), fill=c)


def post_1():
    canvas = Image.new("RGB", (W, H), COLOURS["dark_jam"])
    draw = ImageDraw.Draw(canvas)

    woman = Image.open(ROOT / "assets/dilse-woman-letter.png").convert("RGB")
    crop = woman.crop((230, 0, 1122, 1402)).resize((644, 1012), Image.Resampling.LANCZOS)
    mask = Image.new("L", crop.size, 0)
    m = ImageDraw.Draw(mask)
    m.rounded_rectangle((0, 0, crop.width, crop.height), radius=150, fill=255)
    canvas.paste(crop, (436, 338), mask)

    draw.ellipse((860, 106, 1150, 396), fill=COLOURS["teal"])
    draw.rectangle((0, 968, 518, 1350), fill=COLOURS["jam"])
    brand(draw, light=True)
    letterspaced(draw, (74, 214), "A PLACE TO BEGIN", font(SANS, 17), COLOURS["soft_saffron"], 4)
    y = paragraph(draw, (72, 270), "Say the thing you have been rehearsing in your head.", font(SERIF_BOLD, 57), COLOURS["paper"], 395, 12)
    paragraph(draw, (74, y + 30), "Culturally aware relationship guidance and conversation practice for South Asian women.", font(SANS, 22), "#EAD8DE", 335, 9)
    rounded(draw, (73, 1077, 420, 1153), 38, COLOURS["soft_saffron"])
    draw.text((109, 1097), "START A CONVERSATION", font=font(SANS, 19), fill=COLOURS["dark_jam"])
    footer(draw, 1, light=True)
    canvas.save(OUT / "01-brand-launch.png", quality=95)


def post_2():
    canvas = Image.new("RGB", (W, H), COLOURS["cream"])
    draw = ImageDraw.Draw(canvas)
    brand(draw)
    letterspaced(draw, (73, 210), "TWO WAYS TO BEGIN", font(SANS, 17), COLOURS["rose"], 4)
    paragraph(draw, (72, 258), "Talk it through. Then practise it.", font(SERIF_BOLD, 68), COLOURS["jam"], 900, 12)

    rounded(draw, (72, 500, 1008, 780), 42, COLOURS["teal"])
    draw.ellipse((112, 552, 190, 630), fill=COLOURS["soft_saffron"])
    draw.text((139, 557), "1", font=font(SERIF_BOLD, 43), fill=COLOURS["teal"])
    draw.text((226, 543), "The Listener", font=font(SERIF_BOLD, 43), fill=COLOURS["paper"])
    paragraph(draw, (226, 611), "Sort through what happened, name what you need, and find a clear way to say it.", font(SANS, 26), "#E3EFEB", 690, 10)

    rounded(draw, (72, 816, 1008, 1096), 42, COLOURS["blush"], COLOURS["rose"], 2)
    draw.ellipse((112, 868, 190, 946), fill=COLOURS["jam"])
    draw.text((137, 873), "2", font=font(SERIF_BOLD, 43), fill=COLOURS["paper"])
    draw.text((226, 859), "The Partner", font=font(SERIF_BOLD, 43), fill=COLOURS["jam"])
    paragraph(draw, (226, 927), "Rehearse the conversation with a character before you speak to the real person.", font(SANS, 26), "#604853", 690, 10)
    footer(draw, 2)
    canvas.save(OUT / "02-listener-partner.png", quality=95)


def post_3():
    canvas = Image.new("RGB", (W, H), COLOURS["teal"])
    draw = ImageDraw.Draw(canvas)
    brand(draw, light=True)
    draw.ellipse((780, -90, 1150, 280), fill=COLOURS["rose"])
    draw.ellipse((-210, 1020, 260, 1490), fill=COLOURS["saffron"])

    draw.text((72, 262), "“", font=font(SERIF_BOLD, 170), fill=COLOURS["soft_saffron"])
    y = paragraph(draw, (122, 398), "Some conversations are hard because the whole family is in the room, even when they are not.", font(SERIF_BOLD, 62), COLOURS["paper"], 820, 17)
    draw.line((122, y + 34, 270, y + 34), fill=COLOURS["soft_saffron"], width=8)
    paragraph(draw, (122, y + 83), "DilSe helps you find words that respect your relationship, your family context, and your boundaries.", font(SANS, 27), "#DCEBE5", 780, 12)
    footer(draw, 3, light=True)
    canvas.save(OUT / "03-family-context.png", quality=95)


def post_4():
    canvas = Image.new("RGB", (W, H), COLOURS["blush"])
    draw = ImageDraw.Draw(canvas)
    brand(draw)
    letterspaced(draw, (73, 210), "WORDS TO PRACTISE", font(SANS, 17), COLOURS["rose"], 4)
    paragraph(draw, (72, 258), "You do not have to find the perfect words alone.", font(SERIF_BOLD, 62), COLOURS["jam"], 870, 13)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = ImageDraw.Draw(shadow)
    s.rounded_rectangle((107, 547, 973, 1077), radius=48, fill=(53, 19, 35, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    canvas.paste(shadow, (0, 0), shadow)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (88, 526, 992, 1056), 48, COLOURS["paper"])
    draw.ellipse((132, 577, 210, 655), fill=COLOURS["teal"])
    draw.text((158, 583), "D", font=font(SERIF_BOLD, 38), fill=COLOURS["paper"])
    letterspaced(draw, (238, 584), "A CONVERSATION OPENER", font(SANS, 15), COLOURS["rose"], 3)
    paragraph(draw, (132, 688), "“Can we talk about how school planning is shared? I need one of us to own the whole task, including notices, forms, fees, and follow-up.”", font(SERIF, 40), COLOURS["ink"], 790, 14)
    paragraph(draw, (132, 966), "Adapt the words until they sound like you.", font(SANS, 22), "#765D66", 720, 8)
    footer(draw, 4)
    canvas.save(OUT / "04-script-example.png", quality=95)


if __name__ == "__main__":
    post_1()
    post_2()
    post_3()
    post_4()
    print("Rendered 4 social posts to", OUT)
