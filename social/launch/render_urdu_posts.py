from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from render_posts import COLOURS, H, OUT, SANS, SERIF_BOLD, W, brand, footer, font, rounded


URDU_FONT = "Noto Nastaliq Urdu"


def pango_text(canvas, text, box, size, colour, align="right", line_spacing=1.2):
    x, y, width, height = box
    with tempfile.TemporaryDirectory(dir=OUT) as temp_dir:
        text_path = Path(temp_dir) / "text.png"
        command = [
            "pango-view",
            "--no-display",
            "--pixels",
            "--rtl",
            f"--align={align}",
            "--wrap=word-char",
            f"--font={URDU_FONT} {size}px",
            f"--foreground={colour}",
            "--background=transparent",
            "--margin=0",
            f"--width={width}",
            f"--height={height}",
            f"--line-spacing={line_spacing}",
            f"--output={text_path}",
            f"--text={text}",
        ]
        subprocess.run(command, check=True)
        layer = Image.open(text_path).convert("RGBA")
        canvas.paste(layer, (x, y), layer)


def latin_text(draw, xy, text, size, colour, anchor=None):
    draw.text(xy, text, font=font(SANS, size), fill=colour, anchor=anchor)


def post_5():
    canvas = Image.new("RGB", (W, H), COLOURS["dark_jam"])
    draw = ImageDraw.Draw(canvas)
    brand(draw, light=True)
    draw.ellipse((800, -105, 1190, 285), fill=COLOURS["teal"])
    pango_text(canvas, "دل کی بات کہنا مشکل ہو تو\nپہلے یہاں کہہ کر دیکھیں۔", (90, 265, 900, 380), 69, COLOURS["paper"], line_spacing=1.15)
    pango_text(canvas, "DilSe آپ کو بات سمجھنے، الفاظ چننے اور گفتگو کی مشق کرنے میں مدد دیتا ہے۔", (145, 695, 790, 225), 38, "#E3E3E3", line_spacing=1.25)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (298, 1000, 782, 1092), 46, COLOURS["soft_saffron"])
    pango_text(canvas, "بات شروع کریں", (350, 1004, 380, 80), 32, COLOURS["dark_jam"], align="center")
    draw = ImageDraw.Draw(canvas)
    footer(draw, 5, light=True)
    canvas.save(OUT / "05-urdu-start.png", quality=95)


def post_6():
    canvas = Image.new("RGB", (W, H), COLOURS["blush"])
    draw = ImageDraw.Draw(canvas)
    brand(draw)
    pango_text(canvas, "گفتگو شروع کرنے کے لیے", (90, 205, 900, 105), 34, COLOURS["rose"])
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (72, 350, 1008, 950), 46, COLOURS["paper"])
    draw.ellipse((845, 405, 933, 493), fill=COLOURS["teal"])
    pango_text(canvas, "د", (861, 406, 56, 68), 34, COLOURS["paper"], align="center")
    pango_text(canvas, "کیا ہم سکون سے اس بارے میں بات کر سکتے ہیں؟\nمیں چاہتی ہوں کہ ہم دونوں ایک دوسرے کی بات پوری سنیں۔", (130, 520, 800, 310), 45, COLOURS["dark_jam"], line_spacing=1.2)
    pango_text(canvas, "اپنی بات کے مطابق الفاظ بدل لیں۔", (130, 835, 800, 80), 28, COLOURS["rose"])
    pango_text(canvas, "اپنی بات کی مشق کریں", (130, 1010, 800, 82), 31, COLOURS["jam"], align="center")
    draw = ImageDraw.Draw(canvas)
    footer(draw, 6)
    canvas.save(OUT / "06-urdu-opener.png", quality=95)


def post_7():
    canvas = Image.new("RGB", (W, H), COLOURS["teal"])
    draw = ImageDraw.Draw(canvas)
    brand(draw, light=True)
    draw.ellipse((770, 115, 1120, 465), fill=COLOURS["rose"])
    pango_text(canvas, "آپ کی بات بھی اہم ہے۔", (90, 330, 900, 220), 78, COLOURS["paper"])
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((740, 580, 930, 588), fill=COLOURS["soft_saffron"])
    pango_text(canvas, "آپ جو محسوس کر رہی ہیں، پہلے اسے نام دیں۔\nہر جواب ابھی معلوم ہونا ضروری نہیں۔", (145, 635, 790, 270), 43, "#E8EEEE", line_spacing=1.2)
    pango_text(canvas, "دل کی بات کریں", (145, 1000, 790, 82), 32, COLOURS["soft_saffron"], align="center")
    draw = ImageDraw.Draw(canvas)
    footer(draw, 7, light=True)
    canvas.save(OUT / "07-urdu-your-voice.png", quality=95)


def post_8():
    canvas = Image.new("RGB", (W, H), COLOURS["cream"])
    draw = ImageDraw.Draw(canvas)
    brand(draw)
    draw.ellipse((-150, 945, 280, 1375), fill=COLOURS["rose"])
    draw.ellipse((830, -120, 1190, 240), fill=COLOURS["teal"])
    pango_text(canvas, "ہر رشتہ ایک جیسا نہیں ہوتا۔", (90, 285, 900, 230), 72, COLOURS["jam"])
    pango_text(canvas, "DilSe آپ کو اپنے رشتے، خاندان اور حدود کو سامنے رکھ کر بات کے الفاظ تیار کرنے میں مدد دیتا ہے۔", (145, 595, 790, 290), 42, COLOURS["dark_jam"], line_spacing=1.2)
    draw = ImageDraw.Draw(canvas)
    rounded(draw, (250, 985, 830, 1077), 46, COLOURS["jam"])
    pango_text(canvas, "اپنی صورتحال بیان کریں", (320, 990, 440, 78), 31, COLOURS["paper"], align="center")
    draw = ImageDraw.Draw(canvas)
    footer(draw, 8)
    canvas.save(OUT / "08-urdu-every-relationship.png", quality=95)


if __name__ == "__main__":
    post_5()
    post_6()
    post_7()
    post_8()
    print("Rendered four Urdu posts to", OUT)
