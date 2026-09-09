from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "social" / "launch"))

from render_posts import COLOURS, SANS, SERIF, SERIF_BOLD, font, fit_lines, letterspaced, rounded  # noqa: E402


FEED = (1080, 1350)
VERTICAL = (1080, 1920)
URL = "www.baatdilse.com"

PALETTES = {
    "cream": (COLOURS["cream"], COLOURS["jam"], COLOURS["rose"], COLOURS["teal"]),
    "blush": (COLOURS["blush"], COLOURS["jam"], COLOURS["rose"], COLOURS["teal"]),
    "teal": (COLOURS["teal"], COLOURS["paper"], COLOURS["soft_saffron"], COLOURS["rose"]),
    "maroon": (COLOURS["dark_jam"], COLOURS["paper"], COLOURS["soft_saffron"], COLOURS["teal"]),
}


def brand(draw, light, scale=1.0):
    primary = COLOURS["paper"] if light else COLOURS["jam"]
    accent = COLOURS["soft_saffron"] if light else COLOURS["rose"]
    draw.text((72, 56), "DilSe", font=font(SERIF_BOLD, int(56 * scale)), fill=primary)
    letterspaced(draw, (75, 124), "FROM THE HEART  ·  DIL SE", font(SANS, int(14 * scale)), accent, 2)


def footer(draw, day, light, height, page=None, pages=None):
    colour = COLOURS["paper"] if light else COLOURS["jam"]
    y = height - 88
    draw.line((72, y, 1008, y), fill=colour, width=2)
    draw.text((72, y + 18), URL, font=font(SANS, 17), fill=colour)
    suffix = f"{page}/{pages}" if page and pages else f"DAY {day:02d}"
    draw.text((1008, y + 18), suffix, font=font(SANS, 17), fill=colour, anchor="ra")


def text_block(draw, text, box, path, max_size, min_size, colour, line_gap=13, align="left"):
    x, y, width, height = box
    for size in range(max_size, min_size - 1, -2):
        fnt = font(path, size)
        lines = fit_lines(draw, text, fnt, width)
        line_height = fnt.getbbox("Ag")[3] - fnt.getbbox("Ag")[1]
        total = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
        if total <= height:
            break
    cursor = y
    for line in lines:
        if align == "center":
            tx = x + width / 2
            anchor = "ma"
        elif align == "right":
            tx = x + width
            anchor = "ra"
        else:
            tx = x
            anchor = "la"
        draw.text((tx, cursor), line, font=fnt, fill=colour, anchor=anchor)
        cursor += line_height + line_gap
    return cursor


def decorate(draw, size, accent, secondary, variant):
    w, h = size
    if variant % 4 == 0:
        draw.ellipse((w - 210, -95, w + 95, 210), fill=accent)
        draw.ellipse((-180, h - 250, 210, h + 140), fill=secondary)
    elif variant % 4 == 1:
        draw.ellipse((w - 190, 120, w + 115, 425), fill=secondary)
        draw.rectangle((0, h - 230, 280, h), fill=accent)
    elif variant % 4 == 2:
        draw.ellipse((w - 205, -110, w + 100, 195), fill=accent)
        draw.ellipse((w - 245, h - 320, w + 120, h + 45), fill=secondary)
    else:
        draw.rectangle((w - 125, 0, w, 280), fill=accent)
        draw.ellipse((-190, h - 280, 170, h + 80), fill=secondary)


def pango_text(canvas, text, box, size, colour, align="right", line_spacing=1.2):
    x, y, width, height = box
    with tempfile.TemporaryDirectory(dir=OUT) as temp_dir:
        text_path = Path(temp_dir) / "urdu.png"
        command = [
            "pango-view", "--no-display", "--pixels", "--rtl",
            f"--align={align}", "--wrap=word-char",
            f"--font=Noto Nastaliq Urdu {size}px", f"--foreground={colour}",
            "--background=transparent", "--margin=0", f"--width={width}",
            f"--height={height}", f"--line-spacing={line_spacing}",
            f"--output={text_path}", f"--text={text}",
        ]
        subprocess.run(command, check=True)
        layer = Image.open(text_path).convert("RGBA")
        if layer.size != (width, height):
            clipped = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            clipped.alpha_composite(layer.crop((0, 0, min(width, layer.width), min(height, layer.height))))
            layer = clipped
        canvas.paste(layer, (x, y), layer)


def card(day, filename, label, title, body="", palette="cream", size=FEED, page=None, pages=None, urdu=False):
    bg, primary, accent, secondary = PALETTES[palette]
    light = palette in {"teal", "maroon"}
    canvas = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(canvas)
    decorate(draw, size, secondary, accent, day + (page or 0))
    brand(draw, light)
    label_y = 210 if size == FEED else 255
    letterspaced(draw, (74, label_y), label.upper(), font(SANS, 17), accent, 4)
    title_y = label_y + 58
    title_h = 420 if size == FEED else 640
    if urdu:
        pango_text(canvas, title, (90, title_y, 780, title_h), 66 if size == FEED else 74, primary, line_spacing=1.18)
        if body:
            pango_text(canvas, body, (145, title_y + title_h + 25, 735, 250 if size == FEED else 390), 34 if size == FEED else 40, primary, line_spacing=1.25)
    else:
        title_end = text_block(draw, title, (72, title_y, 810, title_h), SERIF_BOLD, 72 if size == FEED else 84, 42, primary, 14)
        if body:
            text_block(draw, body, (74, title_end + 38, 780, 300 if size == FEED else 500), SANS, 29 if size == FEED else 34, 20, primary, 10)
    draw = ImageDraw.Draw(canvas)
    pill_y = size[1] - 230
    rounded(draw, (72, pill_y, 485, pill_y + 74), 37, accent)
    draw.text((278, pill_y + 37), "START A CONVERSATION", font=font(SANS, 18), fill=bg, anchor="mm")
    footer(draw, day, light, size[1], page, pages)
    path = OUT / f"day-{day:02d}" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=95)


STATIC = {
    1: ("A PLACE TO BEGIN", "Say the thing you have been rehearsing in your head.", "Culturally aware relationship guidance and conversation practice for South Asian women.", "maroon"),
    4: ("TWO WAYS TO BEGIN", "Talk it through. Then practise it.", "Use The Listener to organize your thoughts. Use The Partner to rehearse the conversation.", "cream"),
    7: ("WORDS TO PRACTISE", "Ask for ownership, not vague help.", "“Can we talk about school planning? I need one of us to own notices, forms, fees, and follow-up.”", "blush"),
    10: ("A CLEAR BOUNDARY", "Respect does not require silence.", "You can value family unity while asking for privacy, shared decisions, or different treatment.", "teal"),
    15: ("AN ORDINARY CONVERSATION", "You do not need a crisis to ask for a better conversation.", "Repeated interruptions, uneven planning, emotional distance, or a delayed money decision are enough places to begin.", "cream"),
    18: ("SPEAK NATURALLY", "Choose the language that helps you speak honestly.", "English, Urdu, Roman Urdu, Hindi, Roman Hindi, and mixed-language options are available.", "blush"),
    21: ("WORDS TO PRACTISE", "A money conversation can begin with shared information.", "“Could we look at the numbers together before either of us decides?”", "teal"),
    24: ("KNOW BEFORE YOU SHARE", "Read the Terms before sharing personal details.", "Conversations are stored under your retention setting and may be reviewed by authorized administrators as disclosed at sign-up.", "cream"),
    28: ("WORDS TO PRACTISE", "Define privacy together.", "“Can we agree on a rule about phone privacy and openness that applies to both of us?”", "blush"),
    30: ("ONE HONEST SENTENCE", "The conversation can begin here.", "Name the conversation you have postponed. Then take the first step.", "maroon"),
}

URDU = {
    5: ("URDU", "دل کی بات کہنا مشکل ہو تو پہلے یہاں کہہ کر دیکھیں۔", "DilSe آپ کو بات سمجھنے، الفاظ چننے اور گفتگو کی مشق کرنے میں مدد دیتا ہے۔", "maroon"),
    12: ("URDU · WORDS TO PRACTISE", "کیا ہم سکون سے اس بارے میں بات کر سکتے ہیں؟", "میں چاہتی ہوں کہ ہم دونوں ایک دوسرے کی بات پوری سنیں۔", "blush"),
    19: ("URDU", "آپ کی بات بھی اہم ہے۔", "آپ جو محسوس کر رہی ہیں، پہلے اسے نام دیں۔ ہر جواب ابھی معلوم ہونا ضروری نہیں۔", "teal"),
    26: ("URDU", "ہر رشتہ ایک جیسا نہیں ہوتا۔", "اپنے رشتے، خاندان اور حدود کو سامنے رکھ کر بات کے الفاظ تیار کریں۔", "cream"),
}

REELS = {
    3: ("REEL", "What do I even say?", "Watch a vague complaint become a specific request.", "maroon"),
    9: ("REEL", "Before the family visit", "Practise asking your partner to support a shared decision.", "teal"),
    16: ("REEL", "Three ways to begin", "Open the conversation without saying “we need to talk.”", "blush"),
    23: ("REEL", "Practise the difficult reply", "Rehearse supportive, realistic, and resistant responses.", "maroon"),
}

CAROUSELS = {
    2: [
        ("CAROUSEL", "Five conversations we often postpone", "Which one has been sitting in your mind?"),
        ("01", "Sharing household work", "Ask who owns the planning, remembering, doing, and follow-up."),
        ("02", "Setting a family boundary", "Decide what needs to stay between the couple and what can be shared."),
        ("03", "Discussing money", "Put the numbers, choices, and consequences in the same conversation."),
        ("04", "Rebuilding trust", "Name the event, the effect, and the information you still need."),
        ("05", "Talking about intimacy", "Describe what helps you feel close, comfortable, and respected."),
        ("BEGIN", "Choose one conversation", "Start with what happened and what you want to say next."),
    ],
    8: [
        ("CAROUSEL", "A boundary can be respectful and still be clear.", "Use four parts to prepare the wording."),
        ("01", "Name the situation", "Describe the specific visit, question, decision, or behaviour."),
        ("02", "Explain the effect", "Say what changes for you without assigning a motive."),
        ("03", "State the boundary", "Be clear about what you will accept, share, or do next."),
        ("04", "Propose the next step", "Offer a time, decision, or action that can move the conversation forward."),
        ("ADAPT", "Make the words sound like you", "A useful boundary must fit your actual circumstances."),
    ],
    11: [
        ("CAROUSEL", "What happens after your first message?", "A short look at the DilSe conversation flow."),
        ("01", "Choose a mode", "Talk it through with The Listener or rehearse with The Partner."),
        ("02", "Describe the situation", "Share only the details needed to understand the concern."),
        ("03", "Answer one focused question", "Clarify what happened, what is uncertain, or what you need."),
        ("04", "Review possible words", "Receive a conversation opener or a specific request to consider."),
        ("05", "Adapt and practise", "Change the wording until it sounds natural in your voice."),
        ("NOTE", "Guidance and practice", "DilSe does not provide licensed therapy or emergency support."),
    ],
    14: [
        ("CAROUSEL", "Vague request versus clear request", "Specific wording gives both people something concrete to discuss."),
        ("VAGUE", "“You never help.”", "The listener may not know which task, standard, or change you mean."),
        ("CLEAR", "“Can you own school planning this month?”", "Name notices, forms, fees, dates, and follow-up."),
        ("OWNERSHIP", "Complete responsibility includes the invisible work.", "Planning and remembering count alongside doing."),
        ("TRY IT", "Name one complete area", "Draft the request before the real conversation."),
    ],
    17: [
        ("CAROUSEL", "Family advice, couple decision", "Both can exist in the same relationship."),
        ("CARE", "Family advice can provide care and perspective.", "It may carry experience, practical help, or concern."),
        ("PRESSURE", "Advice can also feel difficult to refuse.", "Ask what the couple actually wants and what feels realistic."),
        ("DECISION", "Choose what works inside your household.", "Respecting family does not require outsourcing every decision."),
        ("ASK", "What input helps, and what decision belongs to us?", "Prepare the question together."),
    ],
    22: [
        ("CAROUSEL", "When you want closeness but do not know how to ask", "Begin with a small, specific request."),
        ("TIME", "Ask for uninterrupted time", "“Can we sit together for 20 minutes after dinner?”"),
        ("AFFECTION", "Describe what you miss", "Name the affection or attention instead of testing whether they notice."),
        ("PREFERENCE", "Ask what helps each person feel close", "Do not assume that closeness means the same action to both people."),
        ("STEP", "Agree on one next step", "Choose something small enough to try this week."),
        ("BEGIN", "Say what closeness means to you", "Use DilSe to prepare or rehearse the conversation."),
    ],
    25: [
        ("CAROUSEL", "A conversation is not a verdict", "One difficult moment may need more context."),
        ("EVENT", "What happened?", "Describe the observable event before assigning a motive."),
        ("PATTERN", "Is it new or repeated?", "Frequency and escalation can change what the event means."),
        ("IMPACT", "How did it affect you?", "Name fear, confusion, hurt, restriction, or another actual effect."),
        ("GOAL", "What do you want next?", "Understanding, a boundary, information, distance, or support may lead to different steps."),
        ("SAFETY", "Active danger needs immediate support.", "Use local emergency services or contact a trusted person nearby."),
        ("BEGIN", "Sort through what happened", "Share only what you feel able to share."),
    ],
    29: [
        ("CAROUSEL", "What can you bring to DilSe?", "You do not need a finished explanation."),
        ("01", "A recent disagreement", "Start with the part you keep replaying."),
        ("02", "A repeated pattern", "Describe what happens and what usually follows."),
        ("03", "A sentence you cannot finish", "Write the first few words and work from there."),
        ("04", "A boundary you need to set", "Name the situation and what needs to change."),
        ("05", "A conversation you want to rehearse", "Practise how you will begin and how you might respond."),
        ("BEGIN", "Bring one thought", "Start a conversation at baatdilse.com."),
    ],
}

STORIES = {
    6: [
        ("STORY POLL", "Which conversation feels hardest right now?", "Tap through to choose."),
        ("POLL", "Family boundaries or household work?", "Use the poll sticker here."),
        ("POLL", "Money, trust, or intimacy?", "Use a question sticker, then link to DilSe."),
    ],
    13: [
        ("QUESTION BOX", "What is one sentence you wish you could say?", "Do not include names or identifying details."),
        ("PROMPT", "Start with: “I want you to understand…”", "Add a question box here."),
        ("NEXT STEP", "Need help finding the words?", "Use a link sticker to visit baatdilse.com."),
    ],
    20: [
        ("STORY QUIZ", "Which request is easier to act on?", "Tap to compare."),
        ("A OR B", "A: “Be more present.”\n\nB: “Can we put our phones away for 20 minutes after dinner?”", "Add the quiz sticker here."),
        ("ANSWER", "B names an action and a time.", "Build your own specific request at baatdilse.com."),
    ],
    27: [
        ("READINESS", "How ready do you feel for the conversation?", "Add an emoji slider here."),
        ("NOT READY", "Write out what happened.", "You do not need to decide what to do yet."),
        ("PARTLY READY", "Choose one opening sentence.", "Keep it specific and in your own voice."),
        ("READY", "Rehearse the first two minutes.", "Practise at baatdilse.com."),
    ],
}


def draw_wordmark(draw, light=False, y=54):
    primary = COLOURS["paper"] if light else COLOURS["jam"]
    accent = COLOURS["soft_saffron"] if light else COLOURS["rose"]
    draw.text((72, y), "DilSe", font=font(SERIF_BOLD, 60), fill=primary)
    letterspaced(draw, (75, y + 72), "FROM THE HEART  ·  DIL SE", font(SANS, 17), accent, 2)


def draw_day_tag(draw, day, label, colour, y=190):
    draw.text((74, y), f"DAY {day:02d}", font=font(SANS, 22), fill=colour)
    draw.line((174, y + 15, 230, y + 15), fill=colour, width=3)
    letterspaced(draw, (252, y), label.upper(), font(SANS, 18), colour, 3)


def draw_url(draw, colour, y, centered=False, size=28):
    x = 540 if centered else 72
    draw.text((x, y), URL, font=font(SANS, size), fill=colour, anchor="ma" if centered else "la")


def draw_cta(draw, bg, fg, y, text="START A CONVERSATION", width=520):
    x1 = (1080 - width) // 2
    rounded(draw, (x1, y, x1 + width, y + 92), 46, bg)
    draw.text((540, y + 46), text, font=font(SANS, 27), fill=fg, anchor="mm")


def draw_texture(draw, bg_light=True, vertical=False):
    colour = "#E4D2D5" if bg_light else "#6A3349"
    h = 1920 if vertical else 1350
    for y in range(250, h - 150, 90):
        draw.line((900, y, 1008, y), fill=colour, width=2)
    for x in range(72, 360, 48):
        draw.ellipse((x, h - 118, x + 6, h - 112), fill=colour)


def paste_hero(canvas, box):
    x1, y1, x2, y2 = box
    woman = Image.open(ROOT / "assets" / "dilse-woman-letter.png").convert("RGB")
    target_ratio = (x2 - x1) / (y2 - y1)
    source_ratio = woman.width / woman.height
    if source_ratio > target_ratio:
        crop_w = int(woman.height * target_ratio)
        left = max(0, woman.width - crop_w)
        woman = woman.crop((left, 0, left + crop_w, woman.height))
    else:
        crop_h = int(woman.width / target_ratio)
        top = max(0, (woman.height - crop_h) // 2)
        woman = woman.crop((0, top, woman.width, top + crop_h))
    woman = woman.resize((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)
    mask = Image.new("L", woman.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, woman.width, woman.height), radius=70, fill=255)
    canvas.paste(woman, (x1, y1), mask)


def render_static_new(day, label, title, body, palette):
    bg, primary, accent, secondary = PALETTES[palette]
    light = palette in {"teal", "maroon"}
    canvas = Image.new("RGB", FEED, bg)
    draw = ImageDraw.Draw(canvas)
    draw_texture(draw, not light)
    draw_wordmark(draw, light)
    draw_day_tag(draw, day, label, accent)

    if day in {1, 30}:
        paste_hero(canvas, (535, 245, 1080, 1350))
        draw = ImageDraw.Draw(canvas)
        panel = COLOURS["dark_jam"] if day == 1 else COLOURS["teal"]
        draw.rounded_rectangle((44, 270, 650, 1075), radius=54, fill=panel)
        text_block(draw, title, (86, 325, 490, 380), SERIF_BOLD, 65, 48, COLOURS["paper"], 14)
        text_block(draw, body, (88, 735, 430, 210), SANS, 38, 32, "#F2E7E8", 12)
        draw_cta(draw, COLOURS["soft_saffron"], panel, 1110, width=455)
        draw_url(draw, COLOURS["paper"], 1225)
    elif day in {7, 21, 28}:
        text_block(draw, title, (72, 270, 880, 210), SERIF_BOLD, 65, 48, primary, 12)
        rounded(draw, (72, 505, 1008, 1015), 52, COLOURS["paper"] if light else "#FFFFFF")
        draw.ellipse((118, 555, 212, 649), fill=secondary)
        draw.text((165, 602), "D", font=font(SERIF_BOLD, 43), fill=COLOURS["paper"], anchor="mm")
        text_block(draw, body, (246, 570, 690, 330), SERIF, 47, 38, COLOURS["ink"], 16)
        draw.line((118, 935, 350, 935), fill=accent, width=7)
        draw.text((380, 918), "ADAPT THE WORDS TO YOUR VOICE", font=font(SANS, 22), fill=COLOURS["rose"])
        draw_cta(draw, accent, bg, 1080)
        draw_url(draw, primary, 1215, centered=True)
    elif day in {4, 18, 24}:
        draw.rounded_rectangle((62, 275, 1018, 1045), radius=58, fill=COLOURS["paper"])
        draw.rectangle((62, 275, 330, 1045), fill=secondary)
        draw.text((196, 420), f"{day:02d}", font=font(SERIF_BOLD, 116), fill=COLOURS["paper"], anchor="mm")
        draw.text((196, 535), "DILSE", font=font(SANS, 24), fill=COLOURS["paper"], anchor="mm")
        text_block(draw, title, (385, 340, 550, 300), SERIF_BOLD, 62, 44, COLOURS["jam"], 14)
        text_block(draw, body, (388, 690, 535, 240), SANS, 38, 31, COLOURS["ink"], 12)
        draw_cta(draw, accent, bg, 1085)
        draw_url(draw, primary, 1218, centered=True)
    else:
        draw.rounded_rectangle((62, 285, 1018, 1018), radius=60, fill=COLOURS["paper"] if light else "#FFFFFF")
        draw.rectangle((62, 285, 1018, 395), fill=secondary)
        draw.text((110, 323), label.upper(), font=font(SANS, 23), fill=COLOURS["paper"])
        text_block(draw, title, (110, 455, 850, 300), SERIF_BOLD, 64, 46, COLOURS["jam"], 14)
        draw.line((110, 778, 300, 778), fill=accent, width=8)
        text_block(draw, body, (110, 820, 820, 145), SANS, 38, 30, COLOURS["ink"], 10)
        draw_cta(draw, accent, bg, 1075)
        draw_url(draw, primary, 1210, centered=True)

    path = OUT / f"day-{day:02d}" / "feed.png"
    canvas.save(path, quality=95)


def render_urdu_new(day, label, title, body, palette):
    bg, primary, accent, secondary = PALETTES[palette]
    light = palette in {"teal", "maroon"}
    canvas = Image.new("RGB", FEED, bg)
    draw = ImageDraw.Draw(canvas)
    draw_texture(draw, not light)
    draw_wordmark(draw, light)
    draw_day_tag(draw, day, label, accent)
    panel = COLOURS["paper"] if light else "#FFFFFF"
    rounded(draw, (62, 285, 1018, 1035), 58, panel)
    draw.rectangle((62, 285, 1018, 405), fill=secondary)
    pango_text(canvas, "دل سے بات", (300, 302, 480, 88), 31, COLOURS["paper"], align="center", line_spacing=1.0)
    title_sizes = {5: 52, 12: 50, 19: 59, 26: 57}
    pango_text(canvas, title, (125, 430, 830, 280), title_sizes[day], COLOURS["jam"], align="right", line_spacing=1.12)
    draw = ImageDraw.Draw(canvas)
    draw.line((730, 725, 930, 725), fill=accent, width=8)
    pango_text(canvas, body, (145, 755, 790, 205), 35, COLOURS["ink"], align="right", line_spacing=1.15)
    urdu_ctas = {
        5: "بات شروع کریں",
        12: "اپنی بات کی مشق کریں",
        19: "دل کی بات کریں",
        26: "اپنی صورتحال بیان کریں",
    }
    rounded(draw, (275, 1080, 805, 1180), 50, accent)
    pango_text(canvas, urdu_ctas[day], (335, 1088, 410, 82), 34, bg, align="center", line_spacing=1.0)
    draw = ImageDraw.Draw(canvas)
    draw_url(draw, primary, 1225, centered=True, size=29)
    canvas.save(OUT / f"day-{day:02d}" / "feed-urdu.png", quality=95)


def progress_bar(draw, page, pages, colour, y=1190):
    gap = 12
    total_w = 936
    segment = (total_w - gap * (pages - 1)) / pages
    for i in range(pages):
        x1 = 72 + i * (segment + gap)
        fill = colour if i < page else "#D9C9CC"
        draw.rounded_rectangle((x1, y, x1 + segment, y + 12), radius=6, fill=fill)


def render_carousel_new(day, slides):
    total = len(slides)
    colours = ["cream", "teal", "blush", "maroon"]
    for page, (label, title, body) in enumerate(slides, start=1):
        palette = colours[(day + page) % 4]
        bg, primary, accent, secondary = PALETTES[palette]
        light = palette in {"teal", "maroon"}
        canvas = Image.new("RGB", FEED, bg)
        draw = ImageDraw.Draw(canvas)
        draw_texture(draw, not light)
        draw_wordmark(draw, light)
        draw_day_tag(draw, day, label, accent)

        if page == 1:
            draw.rounded_rectangle((62, 285, 1018, 1035), radius=62, fill=secondary)
            draw.text((118, 350), f"{total - 2 if total > 5 else total - 1}", font=font(SERIF_BOLD, 180), fill=accent)
            text_block(draw, title, (118, 560, 810, 260), SERIF_BOLD, 68, 48, COLOURS["paper"], 14)
            text_block(draw, body, (120, 855, 760, 105), SANS, 38, 30, "#F1E5E8", 10)
            draw.text((855, 972), "SWIPE", font=font(SANS, 25), fill=accent)
            draw.polygon([(950, 984), (900, 955), (900, 1013)], fill=accent)
            progress_bar(draw, page, total, accent)
            draw_url(draw, primary, 1240, size=24)
        elif page == total:
            draw.rounded_rectangle((62, 285, 1018, 1100), radius=62, fill=secondary)
            draw.ellipse((750, 340, 965, 555), fill=accent)
            draw.text((857, 448), "D", font=font(SERIF_BOLD, 88), fill=secondary, anchor="mm")
            text_block(draw, title, (118, 430, 600, 270), SERIF_BOLD, 68, 48, COLOURS["paper"], 14)
            text_block(draw, body, (120, 740, 760, 140), SANS, 40, 31, "#F1E5E8", 11)
            rounded(draw, (118, 920, 735, 1025), 52, accent)
            draw.text((426, 972), "START A CONVERSATION", font=font(SANS, 27), fill=secondary, anchor="mm")
            progress_bar(draw, page, total, accent)
            draw_url(draw, primary, 1240, size=24)
        else:
            rail = secondary
            draw.rounded_rectangle((62, 285, 1018, 1085), radius=58, fill=COLOURS["paper"])
            draw.rounded_rectangle((62, 285, 260, 1085), radius=58, fill=rail)
            draw.rectangle((180, 285, 260, 1085), fill=rail)
            badge = f"{page - 1:02d}"
            draw.text((160, 450), badge, font=font(SERIF_BOLD, 72), fill=accent, anchor="mm")
            draw.line((115, 530, 205, 530), fill=accent, width=8)
            draw.text((160, 580), f"{page}/{total}", font=font(SANS, 24), fill=COLOURS["paper"], anchor="mm")
            text_block(draw, title, (320, 365, 600, 260), SERIF_BOLD, 61, 43, COLOURS["jam"], 14)
            draw.line((320, 650, 520, 650), fill=accent, width=8)
            text_block(draw, body, (320, 705, 610, 250), SANS, 40, 32, COLOURS["ink"], 13)
            if day == 25 and label == "SAFETY":
                rounded(draw, (320, 955, 890, 1035), 40, COLOURS["jam"])
                draw.text((605, 995), "CONTACT LOCAL EMERGENCY SUPPORT", font=font(SANS, 23), fill=COLOURS["paper"], anchor="mm")
            progress_bar(draw, page, total, accent)
            draw_url(draw, primary, 1240, size=24)

        canvas.save(OUT / f"day-{day:02d}" / f"slide-{page:02d}.png", quality=95)


def render_reel_new(day, label, title, body, palette):
    bg, primary, accent, secondary = PALETTES[palette]
    light = palette in {"teal", "maroon"}
    canvas = Image.new("RGB", VERTICAL, bg)
    draw = ImageDraw.Draw(canvas)
    draw_wordmark(draw, light, y=90)
    draw_day_tag(draw, day, label, accent, y=255)
    draw.rounded_rectangle((72, 350, 1008, 1515), radius=70, fill=secondary)
    text_block(draw, title, (125, 430, 680, 330), SERIF_BOLD, 82, 56, COLOURS["paper"], 16)
    text_block(draw, body, (128, 785, 650, 180), SANS, 42, 34, "#F1E5E8", 13)
    # Phone-style conversation preview fills the lower portion.
    rounded(draw, (470, 950, 930, 1435), 50, COLOURS["paper"])
    rounded(draw, (520, 1010, 860, 1100), 30, COLOURS["blush"])
    rounded(draw, (565, 1140, 880, 1230), 30, accent)
    rounded(draw, (520, 1270, 820, 1360), 30, COLOURS["blush"])
    draw.ellipse((500, 1030, 520, 1050), fill=COLOURS["rose"])
    draw.ellipse((845, 1170, 865, 1190), fill=COLOURS["teal"])
    draw_cta(draw, accent, bg, 1580, text="VISIT BAATDILSE.COM", width=600)
    draw.text((540, 1810), "REEL COVER", font=font(SANS, 21), fill=primary, anchor="mm")
    canvas.save(OUT / f"day-{day:02d}" / "reel-cover.png", quality=95)


def render_story_new(day, frames):
    total = len(frames)
    colours = ["maroon", "cream", "teal", "blush"]
    for page, (label, title, body) in enumerate(frames, start=1):
        palette = colours[(day + page) % 4]
        bg, primary, accent, secondary = PALETTES[palette]
        light = palette in {"teal", "maroon"}
        canvas = Image.new("RGB", VERTICAL, bg)
        draw = ImageDraw.Draw(canvas)
        draw_wordmark(draw, light, y=90)
        draw_day_tag(draw, day, label, accent, y=260)
        draw.rounded_rectangle((72, 360, 1008, 1500), radius=68, fill=COLOURS["paper"] if light else "#FFFFFF")
        text_block(draw, title, (125, 445, 830, 390), SERIF_BOLD, 80, 52, COLOURS["jam"], 16)

        clean_body = body
        for phrase in ["Use the poll sticker here.", "Use a question sticker, then link to DilSe.", "Add a question box here.", "Use a link sticker to visit baatdilse.com.", "Add the quiz sticker here.", "Add an emoji slider here."]:
            clean_body = clean_body.replace(phrase, "").strip()
        if clean_body:
            text_block(draw, clean_body, (128, 860, 780, 170), SANS, 42, 34, COLOURS["ink"], 13)

        # Native-looking interaction zone. It remains useful even before a platform sticker is applied.
        if label in {"POLL", "A OR B"}:
            option_labels = {
                (6, 2): ("FAMILY BOUNDARIES", "HOUSEHOLD WORK"),
                (6, 3): ("MONEY", "TRUST OR INTIMACY"),
                (20, 2): ("BE MORE PRESENT", "20 MINUTES PHONE-FREE"),
            }
            option_a, option_b = option_labels.get((day, page), ("OPTION A", "OPTION B"))
            rounded(draw, (150, 1085, 930, 1200), 56, COLOURS["blush"], COLOURS["rose"], 3)
            rounded(draw, (150, 1235, 930, 1350), 56, "#EDF4F1", COLOURS["teal"], 3)
            draw.text((540, 1142), option_a, font=font(SANS, 28), fill=COLOURS["rose"], anchor="mm")
            draw.text((540, 1292), option_b, font=font(SANS, 28), fill=COLOURS["teal"], anchor="mm")
        elif label in {"QUESTION BOX", "PROMPT"}:
            rounded(draw, (150, 1085, 930, 1350), 46, "#FFFFFF", COLOURS["rose"], 4)
            draw.text((540, 1217), "TYPE YOUR ANSWER", font=font(SANS, 29), fill="#8C6C76", anchor="mm")
        elif page < total:
            rounded(draw, (150, 1120, 930, 1315), 50, "#F7E8EC", COLOURS["rose"], 3)
            draw.text((540, 1217), "TAP TO CONTINUE", font=font(SANS, 29), fill=COLOURS["rose"], anchor="mm")

        if page == total:
            draw_cta(draw, accent, bg, 1570, text="VISIT BAATDILSE.COM", width=610)
        else:
            draw.text((540, 1610), "TAP FOR THE NEXT FRAME", font=font(SANS, 26), fill=primary, anchor="mm")
        progress_bar(draw, page, total, accent, y=1780)
        canvas.save(OUT / f"day-{day:02d}" / f"story-{page:02d}.png", quality=95)


def render_all():
    for day, (label, title, body, palette) in STATIC.items():
        render_static_new(day, label, title, body, palette)
    for day, (label, title, body, palette) in URDU.items():
        render_urdu_new(day, label, title, body, palette)
    for day, (label, title, body, palette) in REELS.items():
        render_reel_new(day, label, title, body, palette)
    for day, slides in CAROUSELS.items():
        render_carousel_new(day, slides)
    for day, frames in STORIES.items():
        render_story_new(day, frames)
    print("Rendered complete 30-day campaign to", OUT)


if __name__ == "__main__":
    render_all()
