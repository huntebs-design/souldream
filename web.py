"""Public SEO site and reverse proxy for the private DilSe Streamlit app."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import subprocess
import sys
from contextlib import asynccontextmanager, suppress
from html import escape
from pathlib import Path

import httpx
import websockets
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from seo_content import TOPICS as SEO_TOPICS, URDU_TOPICS

ROOT = Path(__file__).parent
SITE_URL = os.getenv("SITE_URL", "https://www.baatdilse.com").rstrip("/")
STREAMLIT_PORT = int(os.getenv("STREAMLIT_INTERNAL_PORT", "8502"))
STREAMLIT_ORIGIN = f"http://127.0.0.1:{STREAMLIT_PORT}"
BACKEND_ORIGIN = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("application/vnd.android.package-archive", ".apk")

LEGACY_TOPICS = {
    "family-boundaries": {
        "title": "How to Talk About Family Boundaries in Marriage | DilSe Pakistan",
        "heading": "Talking about family boundaries without dismissing family",
        "description": "Prepare a respectful conversation about privacy, in-laws and family expectations in a Pakistani marriage.",
        "intro": "A boundary conversation can recognise the value of family while still asking for privacy, fairness or a decision the couple makes together.",
        "points": [
            "Name the exact situation instead of criticising the whole family.",
            "Explain what effect it has on you or the marriage.",
            "Ask for one change that both partners can understand and repeat.",
        ],
        "script": "Main aap ke ghar walon ki izzat karti hoon. Saath hi, main chahti hoon ke hamare kuch faislay pehle hum dono aapas mein karein. Kya hum is baat par agree kar sakte hain ke jawab dene se pehle ek doosre se baat karenge?",
    },
    "household-responsibilities": {
        "title": "How to Discuss Household Responsibilities | DilSe Pakistan",
        "heading": "Ask for ownership, not occasional help",
        "description": "Prepare a conversation about household work, childcare and mental load with your husband or partner.",
        "intro": "Household work includes noticing, planning and following up, not only completing the visible task. A useful request transfers responsibility for a defined area from start to finish.",
        "points": [
            "Choose one complete area, such as school administration or monthly bills.",
            "Include planning, reminders and follow-up in the responsibility.",
            "Agree on the result without making one person supervise every step.",
        ],
        "script": "Main chahti hoon ke tum bachon ki school administration ki poori zimmedari lo, notices, forms, fees aur follow-up, bina mere reminders ke.",
    },
    "money-conversations": {
        "title": "How to Talk About Money in Marriage | DilSe Pakistan",
        "heading": "Prepare a clear conversation about money",
        "description": "Plan a conversation about household expenses, family support, savings or career decisions in a Pakistani marriage.",
        "intro": "Money discussions become harder when household needs, support for parents and future plans compete for the same income. Start with the figures and the decision that must be made.",
        "points": [
            "List the fixed household expenses that must be paid first.",
            "Separate current facts from assumptions about each other’s priorities.",
            "Agree on an amount, date or review point instead of a general promise.",
        ],
        "script": "Main samajhti hoon ke Ammi Abbu ki support important hai. Saath hi bachon ki fees late ho rahi hai. Kya hum fixed expenses rakh kar, phir support ka amount mil kar decide kar sakte hain?",
    },
    "trust-and-privacy": {
        "title": "How to Discuss Trust and Phone Privacy | DilSe Pakistan",
        "heading": "Discuss trust and privacy using the facts",
        "description": "Think through a change in phone privacy, jealousy or trust before deciding what it means or what to say.",
        "intro": "A new request to see a phone can have different meanings in different relationships. Start with what changed, what the previous agreement was and whether the expectation applies to both partners.",
        "points": [
            "Describe the behaviour without assigning a motive you cannot confirm.",
            "Compare it with the privacy agreement you had before.",
            "Ask what concern prompted the change and state what you need now.",
        ],
        "script": "Pehle hum phones ke bare mein is tarah check nahi karte thay. Main samajhna chahti hoon ke ab kya badla hai, aur phir hum dono ke liye ek fair agreement banana chahti hoon.",
    },
    "emotional-connection": {
        "title": "How to Talk About Emotional Distance | DilSe Pakistan",
        "heading": "Put emotional distance into words",
        "description": "Prepare a conversation about affection, closeness and emotional distance with your husband or partner.",
        "intro": "“We are not close anymore” can feel too broad to answer. Describe what closeness would look like in ordinary life and ask for one change you can both try.",
        "points": [
            "Use a recent example rather than judging the whole relationship.",
            "Say what you miss and what would help you feel connected.",
            "Ask for a small, repeatable action rather than a personality change.",
        ],
        "script": "Mujhe lagta hai hum dono sirf routine manage kar rahe hain. Main miss karti hoon ke hum araam se baith kar baat karein. Kya hum is hafte aadha ghanta sirf ek doosre ke liye rakh sakte hain?",
    },
}

TOPICS = SEO_TOPICS

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length", "content-encoding",
    "date", "server",
}


def _structured_data(
    page_title: str,
    path: str,
    *,
    lang: str,
    breadcrumbs: list[tuple[str, str]] | None = None,
    image: str | None = None,
) -> str:
    webpage = {
        "@type": "WebPage",
        "@id": f"{SITE_URL}{path}#webpage",
        "name": page_title,
        "url": f"{SITE_URL}{path}",
        "inLanguage": lang,
        "isPartOf": {"@id": f"{SITE_URL}/#website"},
        "publisher": {"@id": f"{SITE_URL}/#organization"},
    }
    if image:
        webpage["primaryImageOfPage"] = {"@type": "ImageObject", "url": f"{SITE_URL}{image}"}
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{SITE_URL}/#organization",
                "name": "DilSe",
                "url": f"{SITE_URL}/",
                "logo": f"{SITE_URL}/assets/dilse-logo.svg",
                "areaServed": {"@type": "Country", "name": "Pakistan"},
            },
            {
                "@type": "WebSite",
                "@id": f"{SITE_URL}/#website",
                "name": "DilSe Pakistan",
                "url": f"{SITE_URL}/",
                "inLanguage": ["en-PK", "ur-PK"],
                "publisher": {"@id": f"{SITE_URL}/#organization"},
            },
            webpage,
        ],
    }
    if breadcrumbs:
        data["@graph"].append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "name": name,
                    "item": f"{SITE_URL}{url}",
                }
                for position, (name, url) in enumerate(breadcrumbs, start=1)
            ],
        })
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def page_shell(
    *, title: str, description: str, path: str, body: str, lang: str = "en-PK", direction: str = "ltr",
    alternate_paths: dict[str, str] | None = None,
    breadcrumbs: list[tuple[str, str]] | None = None,
    image: str = "/assets/dilse-woman-letter.webp",
) -> str:
    canonical = f"{SITE_URL}{path}"
    alternate_tags = ""
    if alternate_paths:
        alternate_tags = "".join(
            f'\n    <link rel="alternate" hreflang="{escape(code)}" href="{SITE_URL}{escape(url)}">'
            for code, url in alternate_paths.items()
        )
        default_url = alternate_paths.get("en-PK", path)
        alternate_tags += f'\n    <link rel="alternate" hreflang="x-default" href="{SITE_URL}{default_url}">'
    return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{canonical}">{alternate_tags}
  <meta property="og:type" content="website">
  <meta property="og:locale" content="{lang.replace('-', '_')}">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE_URL}{image}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="/assets/dilse-mark.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/site/styles.css">
  <script type="application/ld+json">{_structured_data(title, path, lang=lang, breadcrumbs=breadcrumbs, image=image)}</script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="masthead">
    <a class="brand" href="/"><img src="/assets/dilse-logo.svg" alt="DilSe"></a>
    <nav aria-label="Main navigation">
      <a href="/how-it-works/">How it works</a>
      <a href="/conversation-topics/">Conversation topics</a>
      <a href="/ur/" lang="ur">اردو</a>
      <a class="nav-app" href="/downloads/DilSe-latest.apk" download><img src="/assets/dilse-mark.svg" alt="">Android app</a>
      <a class="nav-cta" href="/app/?auth=signin">Sign in</a>
    </nav>
  </header>
  <main id="main">{body}</main>
  <aside class="android-install-prompt" id="android-install-prompt" aria-label="Download DilSe for Android" hidden>
    <div class="install-prompt-brand">
      <img src="/assets/dilse-mark.svg" alt="">
      <div><strong>Take DilSe with you</strong><span>Android 8+ · 58 MB</span></div>
    </div>
    <a class="install-prompt-download" href="/downloads/DilSe-latest.apk" download>Download app</a>
    <button class="install-prompt-dismiss" type="button" aria-label="Dismiss Android app download">Not now</button>
  </aside>
  <footer>
    <img src="/assets/dilse-logo.svg" alt="DilSe">
    <p>Relationship guidance and conversation practice for adults 18+ in Pakistan.</p>
    <div><a href="/about/">About</a><a href="/editorial-policy/">Editorial policy</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy</a><a href="/safety/">Safety</a><a href="/app/?page=terms">Terms</a></div>
  </footer>
  <script>
    (() => {{
      const prompt = document.getElementById('android-install-prompt');
      const isAndroid = /Android/i.test(navigator.userAgent);
      const dismissed = sessionStorage.getItem('dilse-android-install-dismissed') === '1';
      if (!prompt || !isAndroid || dismissed) return;
      prompt.hidden = false;
      prompt.querySelector('.install-prompt-dismiss')?.addEventListener('click', () => {{
        prompt.hidden = true;
        sessionStorage.setItem('dilse-android-install-dismissed', '1');
      }});
    }})();
  </script>
</body>
</html>"""


def home_page() -> str:
    cards = "".join(
        f'<a class="topic-card" href="/topics/{slug}/"><h3>{item["heading"]}</h3><p>{item["description"]}</p><span>Read and prepare →</span></a>'
        for slug, item in list(TOPICS.items())[:6]
    )
    body = f"""
<section class="hero">
  <div class="hero-copy">
    <p class="eyebrow">For women in Pakistan · دل سے</p>
    <h1>Relationship conversation practice for Pakistani women</h1>
    <p class="lede">Talk through a relationship concern, find the words you want to use, and practise the conversation before having it at home.</p>
    <p class="roman-urdu" lang="ur-Latn">Jo baat kehna mushkil ho, pehle yahan keh lijiye.</p>
    <div class="actions hero-actions"><a class="button" href="/app/?auth=create">Start a conversation</a><a class="button button-app" href="/downloads/DilSe-latest.apk" download><img src="/assets/dilse-mark.svg" alt="">Download Android app</a><a class="how-link" href="/how-it-works/">See how DilSe works</a></div>
    <ul class="facts"><li>Adults 18+</li><li>English, Urdu and Roman Urdu</li><li>End-to-end encrypted on your device</li></ul>
  </div>
  <div class="hero-art"><img src="/assets/dilse-woman-letter.webp" width="768" height="1024" alt="Illustration of a Pakistani woman holding a letter beside a window"><p>A place to prepare the words you have been holding back.</p></div>
</section>
<section class="intro-block">
  <p class="eyebrow">Two ways to begin</p><h2>Talk it through or practise the reply</h2>
  <div class="two-up"><article><h3>The Listener</h3><p>Explain what happened. DilSe asks focused questions and helps you separate the facts, your needs and the assumptions that still need checking.</p></article><article><h3>The Partner</h3><p>Describe the person and situation. Rehearse the exchange, pause for feedback and try another way of saying it.</p></article></div>
</section>
<section class="topics" id="topics"><p class="eyebrow">Conversation topics</p><h2>Prepare for a specific conversation</h2><div class="topic-grid">{cards}</div><p class="section-link"><a href="/conversation-topics/">Browse all conversation guides</a></p></section>
<section class="context"><div><p class="urdu-quote" lang="ur">میری بات کو صرف ترجمہ نہیں، سمجھا جائے۔</p></div><div><p class="eyebrow">Pakistani context</p><h2>Advice should understand the family around the relationship</h2><p>DilSe considers joint and nuclear households, in-laws, practical expressions of care, financial responsibilities, faith when you choose to discuss it, privacy and the pressure to keep peace. It asks about your relationship instead of treating these factors as assumptions.</p></div></section>
<section class="notice"><h2>Know what DilSe is</h2><p>DilSe offers confidential relationship guidance and conversation practice. It is not licensed therapy, legal advice, a fatwa or an emergency service. All conversations remain exclusively on your device - nothing is stored on DilSe servers or transmitted anywhere. Your data never leaves your browser or app, staying completely on your device. No third-party services ever access or process your conversations, and no administrators can review your private discussions. Your privacy is absolute with session-based technology that ensures complete data isolation on your device.</p><a href="/privacy/">Read how conversations are handled</a></section>
<section class="final-cta"><p class="eyebrow">Ready when you are</p><h2>Aaj sirf pehli line likhiye.</h2><p>Choose Listener or Partner and start with what feels hardest to say.</p><a class="button" href="/app/?auth=create">Start your first conversation</a></section>"""
    return page_shell(
        title="DilSe Pakistan | Relationship Conversation Practice for Women",
        description="Prepare difficult relationship conversations in English, Urdu or Roman Urdu. DilSe helps adult women in Pakistan talk through concerns and practise what to say.",
        path="/", body=body, alternate_paths={"en-PK": "/", "ur-PK": "/ur/"},
    )


def android_page() -> str:
    body = """
<section class="android-hero">
  <div class="android-copy">
    <p class="eyebrow">DilSe for Android</p>
    <h1>Your conversations, ready when you are</h1>
    <p class="lede">Continue Listener and Partner conversations, record voice notes and receive a private alert when a DilSe response is waiting.</p>
    <a class="button android-download" href="/downloads/DilSe-latest.apk" download>Download DilSe for Android</a>
    <p class="download-note">Android 8 or newer · Adults 18+ · Version 1.0.0</p>
  </div>
  <div class="android-device" aria-label="Preview of the DilSe Android conversation screen">
    <div class="device-status"><span>9:41</span><span>● ●</span></div>
    <div class="device-brand"><img src="/assets/dilse-mark.svg" alt=""><strong>DilSe</strong><span>Listener</span></div>
    <div class="device-thread"><p class="device-message received">What part of the conversation feels hardest to begin?</p><p class="device-message sent">I want to explain what I need without starting another argument.</p><p class="device-message received">Start with the change you want, not everything that has gone wrong.</p></div>
    <div class="device-composer">Write what you want to say <span>↑</span></div>
  </div>
</section>
<section class="install-steps">
  <p class="eyebrow">Install the signed APK</p>
  <h2>Three steps on your Android phone</h2>
  <ol>
    <li><strong>Download</strong><span>Tap the button above and keep the APK when Chrome confirms the download.</span></li>
    <li><strong>Allow this source</strong><span>If Android asks, allow your browser to install this DilSe update.</span></li>
    <li><strong>Install and sign in</strong><span>Open the downloaded file, install it and use your existing DilSe email and password.</span></li>
  </ol>
</section>
<section class="notice android-notice"><h2>Updates remain under your control</h2><p>DilSe checks this website for a newer signed version. The app can take you to the download, but Android will always ask you to approve an installation or update.</p></section>
"""
    return page_shell(
        title="Download DilSe for Android | Baat DilSe",
        description="Download the signed DilSe Android app for Listener and Partner conversations, voice notes and private response notifications.",
        path="/android/",
        body=body,
        breadcrumbs=[("Home", "/"), ("Android app", "/android/")],
    )


def urdu_page() -> str:
    guide_links = "".join(
        f'<li><a href="/ur/{slug}/">{escape(topic["heading"])}</a></li>'
        for slug, topic in URDU_TOPICS.items()
    )
    body = f"""
<section class="text-page urdu-page">
  <p class="eyebrow">پاکستانی خواتین کے لیے</p>
  <h1>رشتوں کے بارے میں مشکل گفتگو کی تیاری</h1>
  <p class="lede">اپنی بات سمجھنے، مناسب الفاظ تلاش کرنے اور گھر میں گفتگو سے پہلے مشق کرنے کے لیے دل سے استعمال کریں۔</p>
  <p>آپ انگریزی، اردو، رومن اردو یا انگریزی اور اردو کے قدرتی امتزاج میں بات کر سکتی ہیں۔</p>
  <h2>دل سے کیسے مدد کرتا ہے؟</h2>
  <p><strong>سننے والا:</strong> اپنی صورتحال بیان کریں۔ دل سے ضروری سوال پوچھ کر بات، ضرورت اور اندازے میں فرق سمجھنے میں مدد کرتا ہے۔</p>
  <p><strong>ساتھی:</strong> جس شخص سے بات کرنی ہے، اس کا کردار منتخب کریں اور گفتگو کی مشق کریں۔</p>
  <h2>کن موضوعات پر بات ہو سکتی ہے؟</h2>
  <p>ازدواجی قربت، سسرال اور خاندان، اعتماد، رازداری، گھر کی ذمہ داریاں، پیسے، کام، بچوں کی پرورش اور مستقبل کے فیصلے۔</p>
  <ul class="urdu-guide-links">{guide_links}</ul>
  <div class="notice"><p>دل سے لائسنس یافتہ تھراپی، قانونی مشورہ، فتویٰ یا ہنگامی سروس نہیں ہے۔ اکاؤنٹ بنانے سے پہلے شرائط میں گفتگو محفوظ کرنے کی تفصیل پڑھیں۔</p></div>
  <a class="button" href="/app/?auth=create">گفتگو شروع کریں</a>
</section>"""
    return page_shell(
        title="دل سے پاکستان | رشتوں کی گفتگو کی تیاری",
        description="پاکستانی خواتین کے لیے انگریزی، اردو یا رومن اردو میں رشتوں کے بارے میں مشکل گفتگو سمجھنے اور اس کی مشق کرنے کی جگہ۔",
        path="/ur/", body=body, lang="ur-PK", direction="rtl",
        alternate_paths={"en-PK": "/", "ur-PK": "/ur/"},
    )


def information_page(kind: str) -> str:
    pages = {
        "how-it-works": (
            "How DilSe Works | Relationship Conversation Practice",
            "See how DilSe helps adult women in Pakistan talk through relationship concerns and rehearse difficult conversations.",
            "How DilSe works",
            "Start with the situation in your own words. Choose Listener when you want to understand what is happening or Partner when you want to rehearse the exchange. DilSe responds in English, Urdu, Roman Urdu or a natural English and Urdu mix.",
            ["Describe one situation or conversation.", "Choose whether you want reflection, a script or roleplay.", "Review the wording, adjust it to your voice and decide what you want to use outside DilSe."],
        ),
        "privacy": (
            "Privacy and Conversation Handling | DilSe Pakistan",
            "Read how DilSe session-based technology and privacy protections work.",
            "Privacy and conversation handling",
            "DilSe accounts provide session-based conversation continuity that remains exclusively on your device. Since no data is stored on DilSe servers, nothing is transmitted anywhere or processed by external services. You control everything - use any nickname as your display name, and your account controls allow you to clear conversations or permanently delete your session data from your device. With retention options managed locally on your device, only enter information you're comfortable with having stored temporarily in your browser session. Your conversations never leave your device, ensuring complete privacy and control.",
            [],
        ),
        "safety": (
            "Safety Information for DilSe Users in Pakistan",
            "Understand DilSe's safety limits and where to seek immediate help in Pakistan.",
            "Safety information for Pakistan",
            "DilSe can help you think through a concerning situation, but it cannot contact emergency services or guarantee anyone’s safety. If there is an active assault, forced entry, weapon, strangulation, a blocked exit or a credible immediate threat, move away from danger and contact emergency help.",
            ["Police Emergency in Pakistan: 15.", "In Punjab, the Punjab Women’s Helpline 1043 provides support for domestic violence and related concerns.", "Use a safe device and involve a trusted adult, neighbour or building guard when doing so will not increase the risk."],
        ),
        "about": (
            "About DilSe | Relationship Conversation Practice in Pakistan",
            "Learn what DilSe provides, who it serves, and our commitment to privacy and safety for women in Pakistan.",
            "About DilSe",
            [
                "DilSe is a mission-driven project focused solely on providing safe, private communication tools for women in Pakistan. The platform operates under the principle that the service's value should stand on its own merits, without requiring personal disclosure of its creators. This approach mirrors how many crisis hotlines and domestic violence services operate - prioritizing the safety and privacy of both users and providers.",
                "Our commitment to anonymity extends to both our team and our users. Just as we protect your identity and conversations with military-grade end-to-end encryption that ensures no data ever leaves your device, we also protect those who develop and maintain this critical service. This dual commitment to privacy ensures that neither users nor providers face unnecessary risks or exposure.",
                "DilSe is specifically designed as a Pakistan-focused conversation practice service for adult women. It helps users articulate relationship concerns, separate observations from assumptions, and rehearse what they may want to say in difficult conversations. The service supports English, Urdu, Roman Urdu and natural code-switching between these languages - reflecting how Pakistani women actually communicate in their daily lives.",
                "The platform covers essential relationship conversations involving marriage, family dynamics, privacy boundaries, financial matters, household work distribution, affection, and future decisions. These are often the most challenging discussions for women in our cultural context, yet they're precisely the conversations that need safe spaces to develop.",
                "It's important to understand that DilSe is not licensed therapy, legal advice, a fatwa or an emergency service. Its wording is a starting point that each user must assess for her own circumstances. We believe in empowering women with tools to find their own voice, rather than providing prescriptive solutions.",
                "The creators of DilSe have extensive experience in digital security, women's rights advocacy, and mental health support within the South Asian context. They have chosen to focus their energy on creating the most secure, helpful platform possible rather than seeking personal recognition. This mission-first approach allows us to remain completely focused on what matters: providing a safe space for women to explore relationship dynamics and practice conversations without judgment or exposure.",
                "By keeping all data on your device with end-to-end encryption, we ensure that your most private thoughts and conversations remain exactly that - private. This is our promise to every woman who entrusts us with her relationship concerns.",
            ],
            [],
        ),
        "editorial-policy": (
            "Editorial Policy | DilSe Pakistan",
            "Read how DilSe prepares public relationship conversation guides for a Pakistani audience and handles corrections.",
            "Editorial policy",
            "DilSe's public guides are written to help a reader prepare one specific conversation. They use observable situations, practical questions and sample wording rather than diagnosing either partner.",
            ["Pakistan-specific context is included only where it changes the conversation, such as joint family living, support for parents, language or privacy at home.", "Sample scripts are examples, not instructions. A reader should change the wording to fit her relationship and safety needs.", "Medical, legal, religious and emergency claims require an appropriate source. Content is revised when wording is unclear, a factual statement changes or a material omission is identified."],
        ),
        "contact": (
            "Contact and Support | DilSe Pakistan",
            "Find the right DilSe channel for conversation feedback, account controls, privacy questions and urgent safety concerns.",
            "Contact and support",
            "Use the channel connected to your issue. DilSe does not currently list a public general-support inbox, and notification messages should not be treated as a support channel.",
            ["For an issue with a DilSe response, use the feedback control shown with that response.", "For session data, local clearing or account deletion, open your account settings. These controls remain the most direct way to manage your data on your device.", "For immediate danger, do not wait for a DilSe reply. Use the Pakistan safety information and contact an appropriate emergency or local support service."],
        ),
        }
    title, description, heading, intro, points = pages[kind]
    if isinstance(intro, list):
        intro_html = f'<p class="lede">{escape(intro[0])}</p>' + "".join(f'<p>{escape(p)}</p>' for p in intro[1:])
    else:
        intro_html = f'<p class="lede">{escape(intro)}</p>'
    list_html = f'<ul class="step-list">{"".join(f"<li>{escape(point)}</li>" for point in points)}</ul>' if points else ''
    next_link = '<a class="button" href="/safety/">Read safety information</a>' if kind == "contact" else '<a class="button" href="/app/?auth=create">Start a conversation</a>'
    body = f'<section class="text-page"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <span class="breadcrumb-current">{escape(heading)}</span></nav><p class="eyebrow">DilSe Pakistan</p><h1>{escape(heading)}</h1>{intro_html}{list_html}{next_link}</section>'
    return page_shell(
        title=title,
        description=description,
        path=f"/{kind}/",
        body=body,
        breadcrumbs=[("Home", "/"), (heading, f"/{kind}/")],
    )


def topic_hub_page() -> str:
    cards = "".join(
        f'''<article class="guide-card">
  <a href="/topics/{slug}/"><img src="/assets/topics/{slug}.webp" width="1200" height="800" loading="lazy" alt="{escape(topic['image_alt'])}"></a>
  <div><h2><a href="/topics/{slug}/">{escape(topic['heading'])}</a></h2><p>{escape(topic['description'])}</p><a href="/topics/{slug}/">Read the guide</a></div>
</article>'''
        for slug, topic in TOPICS.items()
    )
    body = f'''<section class="hub-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <span class="breadcrumb-current">Conversation topics</span></nav>
  <p class="eyebrow">DilSe Pakistan guides</p>
  <h1>Conversation guides for relationships and marriage</h1>
  <p class="lede">Choose the issue closest to the conversation you need to have. Each guide helps you identify the facts, prepare one request and adapt sample wording in English or Roman Urdu.</p>
  <div class="guide-grid">{cards}</div>
</section>'''
    return page_shell(
        title="Relationship Conversation Guides | DilSe Pakistan",
        description="Browse practical conversation guides about marriage, family boundaries, money, privacy, household work, affection and family pressure in Pakistan.",
        path="/conversation-topics/",
        body=body,
        breadcrumbs=[("Home", "/"), ("Conversation topics", "/conversation-topics/")],
    )


def topic_page(slug: str) -> str:
    topic = TOPICS[slug]
    situations = "".join(f"<li>{escape(point)}</li>" for point in topic["situations"])
    prepare = "".join(f"<li>{escape(point)}</li>" for point in topic["prepare"])
    progress = "".join(f"<li>{escape(point)}</li>" for point in topic["progress"])
    responses = "".join(
        f'<div class="response-pair"><p><strong>If you hear:</strong> “{escape(objection)}”</p><p><strong>You could continue:</strong> “{escape(reply)}”</p></div>'
        for objection, reply in topic["responses"]
    )
    related = "".join(
        f'<li><a href="/topics/{related_slug}/">{escape(TOPICS[related_slug]["heading"])}</a></li>'
        for related_slug in topic["related"]
    )
    alternate_paths = None
    urdu_link = ""
    if topic.get("urdu"):
        urdu_path = f'/ur/{topic["urdu"]}/'
        alternate_paths = {"en-PK": f"/topics/{slug}/", "ur-PK": urdu_path}
        urdu_link = f'<p class="translation-link"><a href="{urdu_path}" lang="ur">یہ رہنمائی اردو میں پڑھیں</a></p>'
    body = f"""<article class="article-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <a href="/conversation-topics/">Conversation topics</a> <span>/</span> <span class="breadcrumb-current">{escape(topic['heading'])}</span></nav>
  <header class="article-header"><p class="eyebrow">Conversation guide</p><h1>{escape(topic['heading'])}</h1><p class="lede">{escape(topic['intro'])}</p>{urdu_link}</header>
  <figure class="topic-hero"><img src="/assets/topics/{slug}.webp" width="1200" height="800" alt="{escape(topic['image_alt'])}" fetchpriority="high"><figcaption>An illustration for this DilSe conversation guide.</figcaption></figure>
  <section><h2>When this conversation usually comes up</h2><ul class="step-list">{situations}</ul></section>
  <section><h2>Before you begin</h2><ol class="step-list">{prepare}</ol><p>Choose a time when you can speak privately and neither person needs to leave immediately. The purpose is to understand the issue and agree on a next step, not to prove which person is entirely right.</p></section>
  <section><h2>Two ways to open the conversation</h2><div class="script"><span>A gentler opening</span><p lang="ur-Latn">“{escape(topic['gentle'])}”</p></div><div class="script direct"><span>A more direct opening</span><p lang="ur-Latn">“{escape(topic['direct'])}”</p></div><p>Change the wording to match your usual level of formality. Keep the event and request intact so the point does not disappear behind softer language.</p></section>
  <section><h2>If the conversation gets stuck</h2>{responses}</section>
  <section><h2>What progress can look like</h2><ul class="step-list">{progress}</ul></section>
  <aside class="safety-note"><h2>Check safety before using a script</h2><p>A clear sentence cannot make an unsafe person respond safely. If disagreement may lead to threats, surveillance, physical harm or being prevented from leaving, review the <a href="/safety/">Pakistan safety information</a> before deciding whether, when or where to speak.</p></aside>
  <section class="related-guides"><h2>Related conversations</h2><ul>{related}</ul></section>
  <div class="article-cta"><h2>Practise the words in your own voice</h2><p>Tell DilSe what happened, who you need to speak with and what you want the conversation to change.</p><a class="button" href="/app/?auth=create">Start a conversation</a></div>
</article>"""
    return page_shell(
        title=topic["title"],
        description=topic["description"],
        path=f"/topics/{slug}/",
        body=body,
        alternate_paths=alternate_paths,
        breadcrumbs=[("Home", "/"), ("Conversation topics", "/conversation-topics/"), (topic["heading"], f"/topics/{slug}/")],
        image=f"/assets/topics/{slug}.webp",
    )


def urdu_topic_page(slug: str) -> str:
    topic = URDU_TOPICS[slug]
    english = TOPICS[topic["english"]]
    points = "".join(f"<li>{escape(point)}</li>" for point in topic["points"])
    related_items = []
    for related_slug in english["related"]:
        related_english = TOPICS[related_slug]
        related_urdu_slug = related_english.get("urdu")
        if related_urdu_slug and related_urdu_slug in URDU_TOPICS:
            related_topic = URDU_TOPICS[related_urdu_slug]
            related_items.append(
                f'<li><a href="/ur/{related_urdu_slug}/">{escape(related_topic["heading"])}</a></li>'
            )
        else:
            related_items.append(
                f'<li><a href="/topics/{related_slug}/">{escape(related_english["heading"])}</a></li>'
            )
    related = "".join(related_items)
    path = f"/ur/{slug}/"
    english_path = f'/topics/{topic["english"]}/'
    body = f'''<article class="article-page urdu-page">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/ur/">اردو</a> <span>/</span> <a href="/conversation-topics/">گفتگو کے موضوعات</a> <span>/</span> <span class="breadcrumb-current">{escape(topic['heading'])}</span></nav>
  <header class="article-header"><p class="eyebrow">گفتگو کی رہنمائی</p><h1>{escape(topic['heading'])}</h1><p class="lede">{escape(topic['intro'])}</p><p class="translation-link"><a href="{english_path}">Read this guide in English</a></p></header>
  <figure class="topic-hero"><img src="/assets/topics/{topic['english']}.webp" width="1200" height="800" alt="{escape(english['image_alt'])}" fetchpriority="high"></figure>
  <section><h2>گفتگو سے پہلے</h2><ol class="step-list">{points}</ol><p>ایسا وقت منتخب کریں جب آپ تنہائی میں بات کر سکیں اور کسی کو فوری طور پر کہیں جانا نہ ہو۔ ایک وقت میں ایک واقعہ اور ایک درخواست پر رہیں۔</p></section>
  <section><h2>گفتگو شروع کرنے کے لیے جملہ</h2><div class="script"><p>“{escape(topic['script'])}”</p></div><p>الفاظ کو اپنے رشتے اور بولنے کے انداز کے مطابق بدلیں، لیکن واقعہ اور اپنی واضح درخواست کو قائم رکھیں۔</p></section>
  <section><h2>اگر بات مشکل ہو جائے</h2><p>آواز بلند ہونے، بات بار بار کاٹنے یا پرانے جھگڑے کھلنے پر وقفہ مانگیں اور دوبارہ بات کرنے کا وقت طے کریں۔ اگر بات کرنے سے دھمکی، نگرانی یا جسمانی نقصان کا خدشہ ہو تو پہلے <a href="/safety/">حفاظتی معلومات</a> دیکھیں۔</p></section>
  <section class="related-guides"><h2>متعلقہ گفتگو</h2><ul>{related}</ul></section>
  <div class="article-cta"><h2>اپنے الفاظ میں مشق کریں</h2><p>دل سے کو بتائیں کہ کیا ہوا، آپ کس سے بات کرنا چاہتی ہیں اور گفتگو سے کیا بدلنا چاہتی ہیں۔</p><a class="button" href="/app/?auth=create">گفتگو شروع کریں</a></div>
</article>'''
    return page_shell(
        title=topic["title"], description=topic["description"], path=path, body=body,
        lang="ur-PK", direction="rtl",
        alternate_paths={"en-PK": english_path, "ur-PK": path},
        breadcrumbs=[("اردو", "/ur/"), ("گفتگو کے موضوعات", "/conversation-topics/"), (topic["heading"], path)],
        image=f"/assets/topics/{topic['english']}.webp",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.address=127.0.0.1", f"--server.port={STREAMLIT_PORT}",
            "--server.headless=true", "--server.baseUrlPath=app",
        ],
        cwd=ROOT,
    )
    yield
    process.terminate()
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=8)
    if process.poll() is None:
        process.kill()


app = FastAPI(title="DilSe public site", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/site", StaticFiles(directory=ROOT / "public"), name="site")
app.mount("/downloads", StaticFiles(directory=ROOT / "downloads"), name="downloads")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> Response:
    if any(key in request.query_params for key in ("auth", "admin", "page", "open_session")):
        return RedirectResponse(f"/app/?{request.url.query}", status_code=308)
    return HTMLResponse(home_page())


@app.get("/ur/", response_class=HTMLResponse)
async def urdu() -> HTMLResponse:
    return HTMLResponse(urdu_page())


@app.get("/android/", response_class=HTMLResponse)
async def android_download() -> HTMLResponse:
    return HTMLResponse(android_page())


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def api_proxy(path: str, request: Request) -> Response:
    """Expose the private Railway API to signed mobile clients on the main domain."""
    query = f"?{request.url.query}" if request.url.query else ""
    target = f"{BACKEND_ORIGIN}/{path}{query}"
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP and key.lower() != "host"
    }
    try:
        async with httpx.AsyncClient(timeout=180.0, follow_redirects=False) as client:
            upstream = await client.request(
                request.method,
                target,
                headers=headers,
                content=await request.body(),
            )
    except httpx.RequestError:
        return PlainTextResponse("DilSe is starting. Try again in a moment.", status_code=503)
    response_headers = {
        key: value for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP
    }
    response_headers["Cache-Control"] = "no-store"
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


@app.get("/ur/{slug}/", response_class=HTMLResponse)
async def urdu_topic(slug: str) -> Response:
    if slug not in URDU_TOPICS:
        return HTMLResponse("Not found", status_code=404)
    return HTMLResponse(urdu_topic_page(slug))


@app.get("/conversation-topics/", response_class=HTMLResponse)
async def topic_hub() -> HTMLResponse:
    return HTMLResponse(topic_hub_page())


@app.get("/{kind}/", response_class=HTMLResponse)
async def information(kind: str, request: Request) -> Response:
    if kind == "app":
        return await streamlit_proxy("", request)
    if kind not in {"how-it-works", "privacy", "safety", "about", "editorial-policy", "contact"}:
        return HTMLResponse("Not found", status_code=404)
    return HTMLResponse(information_page(kind))


@app.get("/topics/{slug}/", response_class=HTMLResponse)
async def topic(slug: str) -> Response:
    if slug not in TOPICS:
        return HTMLResponse("Not found", status_code=404)
    return HTMLResponse(topic_page(slug))


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return f"User-agent: *\nAllow: /\nDisallow: /app/\nSitemap: {SITE_URL}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap() -> Response:
    paths = [
        "/", "/ur/", "/conversation-topics/", "/how-it-works/", "/about/",
        "/editorial-policy/", "/contact/", "/privacy/", "/safety/", "/android/",
    ]
    standard_urls = "".join(f"<url><loc>{SITE_URL}{path}</loc></url>" for path in paths)
    topic_urls = "".join(
        f"<url><loc>{SITE_URL}/topics/{slug}/</loc><image:image><image:loc>{SITE_URL}/assets/topics/{slug}.webp</image:loc><image:title>{escape(topic['heading'])}</image:title></image:image></url>"
        for slug, topic in TOPICS.items()
    )
    urdu_urls = "".join(f"<url><loc>{SITE_URL}/ur/{slug}/</loc></url>" for slug in URDU_TOPICS)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">{standard_urls}{topic_urls}{urdu_urls}</urlset>'
    return Response(xml, media_type="application/xml")


@app.get("/app")
async def app_slash() -> RedirectResponse:
    return RedirectResponse("/app/", status_code=308)


@app.websocket("/app/_stcore/stream")
async def streamlit_websocket(client: WebSocket) -> None:
    query = f"?{client.url.query}" if client.url.query else ""
    headers = {}
    if client.headers.get("cookie"):
        headers["Cookie"] = client.headers["cookie"]
    offered_protocols = [
        protocol.strip()
        for protocol in client.headers.get("sec-websocket-protocol", "").split(",")
        if protocol.strip()
    ]
    try:
        async with websockets.connect(
            f"ws://127.0.0.1:{STREAMLIT_PORT}/app/_stcore/stream{query}",
            additional_headers=headers,
            subprotocols=offered_protocols or None,
            max_size=None,
        ) as upstream:
            await client.accept(subprotocol=upstream.subprotocol)

            async def client_to_upstream() -> None:
                while True:
                    message = await client.receive()
                    if message["type"] == "websocket.disconnect":
                        break
                    if message.get("bytes") is not None:
                        await upstream.send(message["bytes"])
                    elif message.get("text") is not None:
                        await upstream.send(message["text"])

            async def upstream_to_client() -> None:
                async for message in upstream:
                    if isinstance(message, bytes):
                        await client.send_bytes(message)
                    else:
                        await client.send_text(message)

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except (WebSocketDisconnect, websockets.ConnectionClosed):
        return


@app.api_route("/app/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def streamlit_proxy(path: str, request: Request) -> Response:
    query = f"?{request.url.query}" if request.url.query else ""
    target = f"{STREAMLIT_ORIGIN}/app/{path}{query}"
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP and key.lower() != "host"
    }
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            upstream = await client.request(
                request.method, target, headers=headers, content=await request.body()
            )
    except httpx.RequestError:
        return PlainTextResponse("DilSe is starting. Please refresh in a moment.", status_code=503)
    response_headers = {
        key: value for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP
    }
    response_headers["X-Robots-Tag"] = "noindex, nofollow"
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
