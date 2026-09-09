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


def render_all():
    for day, (label, title, body, palette) in STATIC.items():
        card(day, "feed.png", label, title, body, palette)
    for day, (label, title, body, palette) in URDU.items():
        card(day, "feed-urdu.png", label, title, body, palette, urdu=True)
    for day, (label, title, body, palette) in REELS.items():
        card(day, "reel-cover.png", label, title, body, palette, size=VERTICAL)
    for day, slides in CAROUSELS.items():
        total = len(slides)
        palette_names = ["cream", "teal", "blush", "maroon"]
        for index, (label, title, body) in enumerate(slides, start=1):
            card(day, f"slide-{index:02d}.png", label, title, body, palette_names[(day + index) % 4], page=index, pages=total)
    for day, frames in STORIES.items():
        total = len(frames)
        palette_names = ["maroon", "cream", "teal", "blush"]
        for index, (label, title, body) in enumerate(frames, start=1):
            card(day, f"story-{index:02d}.png", label, title, body, palette_names[(day + index) % 4], size=VERTICAL, page=index, pages=total)
    print("Rendered complete 30-day campaign to", OUT)


if __name__ == "__main__":
    render_all()
