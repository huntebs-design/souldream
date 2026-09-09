"""Streamlit interface for DilSe (SoulBridge)."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
VISITOR_TRACKING_SECRET = os.getenv("VISITOR_TRACKING_SECRET", "")
SHOW_HUMAN_HANDOFF_UI = os.getenv("DILSE_SHOW_HUMAN_HANDOFF_UI", "false").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
REQUEST_TIMEOUT_SECONDS = 90
AI_REPLY_MIN_DELAY_SECONDS = max(
    0.0,
    min(float(os.getenv("DILSE_AI_REPLY_MIN_DELAY_SECONDS", "2.5")), 10.0),
)
BROWSER_SESSION_SECONDS = int(os.getenv("AUTH_SESSION_DAYS", "7")) * 24 * 60 * 60
BROWSER_COOKIE_NAME = "dilse_browser"
CURRENT_TERMS_VERSION = "2026-08-10-terms-v6"
CHARACTER_PROFILE_MIN_LENGTH = 12
CHARACTER_PROFILE_MAX_WORDS = 5_000
CHARACTER_PROFILE_MAX_CHARS = 75_000
ADMIN_IMAGE_MAX_BYTES = 5 * 1024 * 1024
CHARACTER_PROFILE_GUIDANCE = {
    "husband": {
        "relationship": "your husband",
        "question": "How does he normally speak? What makes him open up, shut down, or become defensive?",
        "placeholder": "Example: Ali is quiet and practical. He speaks mostly in Roman Urdu, avoids emotional conversations, and becomes defensive when I mention his mother. He softens when I speak calmly and directly.",
    },
    "supportive_partner": {
        "relationship": "your supportive partner",
        "question": "How does this person show support, speak during difficult moments, and respond when you ask for something?",
        "placeholder": "Example: Sameer listens patiently and asks questions before replying. He uses gentle humour, speaks in English and Roman Urdu, and wants clear examples when I explain a problem.",
    },
    "defensive_partner": {
        "relationship": "your defensive partner",
        "question": "What usually makes this person feel criticized? How do they argue, and what helps them listen again?",
        "placeholder": "Example: Hamza hears requests as criticism and quickly explains why something is not his fault. He speaks bluntly, needs time to calm down, and listens better when I make one specific request.",
    },
    "jealous_partner": {
        "relationship": "your jealous partner",
        "question": "What tends to trigger their jealousy? How does it show up in their words, and what kind of reassurance do they respond to?",
        "placeholder": "Example: He becomes uneasy when plans change without notice and asks repeated questions. He speaks directly, dislikes vague answers, and calms down when expectations are discussed clearly.",
    },
    "mother_in_law": {
        "relationship": "your mother-in-law",
        "question": "What matters most to her? How does she speak, criticize, show care, or respond when a boundary is set?",
        "placeholder": "Example: Ammi is traditional and formal. She speaks Urdu, cares strongly about family reputation, and becomes critical when household routines change. She responds better when I stay respectful but repeat my point.",
    },
    "co_parent": {
        "relationship": "your co-parent",
        "question": "How do they approach parenting, responsibility, and disagreement? What do they usually avoid or take seriously?",
        "placeholder": "Example: He is affectionate with the children but forgets school administration. He becomes practical during disagreements, prefers short conversations, and responds best to a clear division of responsibility.",
    },
    "family_member": {
        "relationship": "this family member",
        "question": "Who are they to you? How do they speak, what do they value, and how do they usually react to disagreement or boundaries?",
        "placeholder": "Example: This is my older sister. She is protective, speaks quickly in Roman Urdu, and gives advice before listening. She respects a boundary when I explain why it matters to me.",
    },
}
LANDING_IMAGE_PATH = Path(__file__).parent / "assets" / "dilse-woman-letter.webp"
LOGO_PATH = Path(__file__).parent / "assets" / "dilse-logo.svg"
CHAT_AVATAR_PATH = Path(__file__).parent / "assets" / "dilse-mark.svg"
TYPING_CAPTURE_PATH = Path(__file__).parent / "components" / "typing_capture"
typing_capture_component = components.declare_component(
    "dilse_typing_capture",
    path=str(TYPING_CAPTURE_PATH),
)
PHONE_ALERTS_PATH = Path(__file__).parent / "components" / "phone_alerts"
phone_alerts_component = components.declare_component(
    "dilse_phone_alerts",
    path=str(PHONE_ALERTS_PATH),
)

st.set_page_config(
    page_title="DilSe Pakistan | Relationship Conversation Practice",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --jam: #571f35;
        --rose: #b85c73;
        --parchment: #fbf4ec;
        --ink: #2e2026;
        --saffron: #e6a15a;
        --mist: #eadde0;
        --white: #fffdf9;
    }
    .stApp {
        background: var(--parchment);
        color: var(--ink);
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
    }
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stElementToolbar"],
    [data-testid="stHeaderActionElements"],
    #MainMenu,
    button[title="View fullscreen"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
    }
    [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]),
    [data-testid="stIFrame"] {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        border: 0 !important;
        overflow: hidden !important;
    }
    .st-key-phone_alerts_widget [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]),
    .st-key-phone_alerts_widget [data-testid="stIFrame"] {
        height: 126px !important;
        min-height: 126px !important;
        width: 100% !important;
        overflow: visible !important;
    }
    [data-testid="stSidebar"] {
        background: #f1e4e5;
        border-right: 1px solid #dbc8cc;
    }
    h1, h2, h3 {
        color: var(--jam);
        font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        letter-spacing: -0.025em;
    }
    .block-container { max-width: 1120px; padding-top: 2rem; }
    .letter-header {
        position: relative;
        overflow: hidden;
        min-height: 178px;
        padding: 2.1rem 2.4rem;
        margin-bottom: 1.6rem;
        border: 1px solid #dcc8c9;
        border-radius: 6px;
        background: var(--white);
        box-shadow: 0 14px 32px rgba(87, 31, 53, 0.08);
    }
    .letter-header:after {
        content: "";
        position: absolute;
        right: -55px;
        bottom: -92px;
        width: 270px;
        height: 190px;
        background: #f0d7d7;
        transform: rotate(-18deg);
        clip-path: polygon(0 0, 100% 50%, 0 100%);
    }
    .letter-header .eyebrow {
        color: var(--rose);
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
    }
    .letter-header h1 { margin: .4rem 0 .2rem; font-size: clamp(2.5rem, 6vw, 4.6rem); }
    .letter-header p { max-width: 620px; color: #674c56; font-size: 1.05rem; }
    .quiet-card, .exercise-card, .privacy-card {
        padding: 1rem 1.15rem;
        border: 1px solid #deced0;
        border-radius: 6px;
        background: var(--white);
    }
    .mode-note {
        margin: .35rem 0 1rem;
        padding-left: .9rem;
        border-left: 3px solid var(--saffron);
        color: #67515a;
    }
    .data-note {
        padding: .8rem .9rem;
        border: 1px solid #d6c1c4;
        border-radius: 4px;
        background: #fff9f3;
        color: #5a444d;
        font-size: .86rem;
    }
    .handoff-ribbon {
        margin: .8rem 0 1rem;
        padding: .85rem 1rem;
        border: 1px solid #c68b55;
        border-left: 5px solid var(--saffron);
        border-radius: 4px;
        background: #fff5e8;
        color: #4f3430;
    }
    .site-masthead {
        position: relative;
        z-index: 5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        min-height: 88px;
        margin: 0 calc(50% - 50vw);
        padding: .85rem max(2rem, calc((100vw - 1120px) / 2));
        border-bottom: 1px solid #d9c5c9;
        background: #fff9f2;
        animation: masthead-in .65s cubic-bezier(.22,.8,.28,1) both;
    }
    .site-logo { display: block; width: clamp(175px, 20vw, 225px); height: auto; }
    .site-nav { display: flex; align-items: center; gap: .55rem; }
    .site-nav a {
        padding: .62rem .82rem;
        border-radius: 3px;
        color: #571f35 !important;
        font-size: .84rem;
        font-weight: 750;
        text-decoration: none;
        transition: color .22s ease, background-color .22s ease, transform .22s ease;
    }
    .site-nav a:last-child { border: 1px solid #571f35; }
    .site-nav a:focus-visible { outline: 3px solid rgba(230,161,90,.65); outline-offset: 2px; }
    .landing-hero {
        position: relative;
        overflow: hidden;
        display: grid;
        grid-template-columns: minmax(0, .95fr) minmax(340px, 1.05fr);
        gap: clamp(2rem, 6vw, 5.5rem);
        align-items: center;
        min-height: 700px;
        margin: 0 calc(50% - 50vw);
        padding: clamp(4.5rem, 9vw, 7.5rem) max(2rem, calc((100vw - 1120px) / 2));
        background: #351323;
        color: #fff9f2;
        isolation: isolate;
    }
    .landing-hero:before {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -2;
        opacity: .15;
        background-image:
            linear-gradient(30deg, transparent 24%, #e6a15a 25%, #e6a15a 26%, transparent 27%, transparent 74%, #e6a15a 75%, #e6a15a 76%, transparent 77%),
            linear-gradient(150deg, transparent 24%, #e6a15a 25%, #e6a15a 26%, transparent 27%, transparent 74%, #e6a15a 75%, #e6a15a 76%, transparent 77%);
        background-size: 64px 112px;
        animation: pattern-drift 28s linear infinite;
    }
    .landing-hero:after {
        content: "";
        position: absolute;
        width: 42vw;
        height: 42vw;
        min-width: 420px;
        min-height: 420px;
        right: -19vw;
        top: -23vw;
        z-index: -1;
        border-radius: 50%;
        background: #88425a;
        opacity: .55;
    }
    .landing-kicker, .section-kicker {
        color: #f0b46f;
        font-size: .74rem;
        font-weight: 800;
        letter-spacing: .17em;
        text-transform: uppercase;
    }
    .landing-hero h1 {
        max-width: 760px;
        margin: .7rem 0 1rem;
        color: #fff9f2;
        font-family: "Iowan Old Style", "Kohinoor Devanagari", Georgia, serif;
        font-size: clamp(3.3rem, 7.2vw, 6.8rem);
        font-weight: 500;
        line-height: .94;
        letter-spacing: -.055em;
    }
    .landing-hero .landing-kicker,
    .landing-hero h1,
    .landing-hero .landing-lede,
    .landing-hero .urdu-hero,
    .landing-hero .landing-reassurance,
    .landing-hero .landing-actions {
        opacity: 0;
        transform: translateY(18px);
        animation: copy-rise .72s cubic-bezier(.22,.8,.28,1) both;
    }
    .landing-hero .landing-kicker { animation-delay: .16s; }
    .landing-hero h1 { animation-delay: .25s; }
    .landing-hero .landing-lede { animation-delay: .36s; }
    .landing-hero .urdu-hero { animation-delay: .45s; }
    .landing-hero .landing-reassurance { animation-delay: .53s; }
    .landing-hero .landing-actions { animation-delay: .61s; }
    .landing-lede {
        max-width: 660px;
        margin: 0 0 1.4rem;
        color: #ead8de;
        font-size: clamp(1rem, 1.7vw, 1.2rem);
        line-height: 1.65;
    }
    .urdu-hero {
        max-width: 580px;
        margin: .2rem 0 1rem;
        color: #f2d8df;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: clamp(1.05rem, 1.7vw, 1.3rem);
        font-style: italic;
        line-height: 1.55;
        text-align: left;
    }
    .landing-reassurance {
        margin: 1rem 0 1.5rem;
        color: #f4c8d4;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: 1.08rem;
        font-style: italic;
    }
    .landing-actions { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }
    .landing-actions a {
        display: inline-block;
        padding: .8rem 1.15rem;
        border: 1px solid #f0b46f;
        border-radius: 3px;
        color: #fff9f2 !important;
        font-weight: 750;
        text-decoration: none;
        box-shadow: 0 0 0 rgba(0,0,0,0);
        transition: transform .22s ease, box-shadow .22s ease, background-color .22s ease;
    }
    .landing-actions a:first-child { background: #f0b46f; color: #351323 !important; }
    .landing-actions a:focus-visible { outline: 3px solid #fff9f2; outline-offset: 3px; }
    .hero-art {
        position: relative;
        z-index: 0;
        isolation: isolate;
        width: min(100%, 520px);
        margin: 0 0 0 auto;
        padding: 0 0 2rem 2rem;
        animation: portrait-arrive .95s cubic-bezier(.18,.82,.25,1) .34s backwards;
    }
    .hero-art:before {
        content: "";
        position: absolute;
        inset: -1.4rem 1.5rem 3.5rem -1rem;
        border: 1px solid rgba(240,180,111,.62);
        border-radius: 48% 48% 3px 3px;
    }
    .hero-art:after {
        content: "";
        position: absolute;
        z-index: -1;
        width: 72%;
        aspect-ratio: 1;
        right: -9%;
        top: 12%;
        border-radius: 50%;
        background: rgba(184,92,115,.34);
        filter: blur(45px);
        animation: quiet-glow 7s ease-in-out infinite;
    }
    .hero-portrait {
        position: relative;
        display: block;
        width: 100%;
        aspect-ratio: 4 / 5;
        object-fit: cover;
        border: 8px solid #fff9f2;
        border-radius: 2px;
        box-shadow: 18px 20px 0 #184f4a, 0 28px 70px rgba(0,0,0,.3);
        transition: transform .55s cubic-bezier(.22,.8,.28,1), filter .55s ease;
    }
    .letter-preview {
        position: absolute;
        left: -1.2rem;
        bottom: 0;
        width: min(86%, 400px);
        padding: 1.15rem 1.3rem 1.05rem;
        border-radius: 3px;
        background: #fff9f2;
        color: #38252c;
        box-shadow: 8px 10px 28px rgba(34,12,22,.28);
        transform: rotate(-2deg);
        animation: note-settle .82s cubic-bezier(.16,.86,.3,1) .86s backwards;
        transition: transform .35s cubic-bezier(.22,.8,.28,1), box-shadow .35s ease;
    }
    .letter-label {
        position: relative;
        margin-bottom: .65rem;
        color: #88425a;
        font-size: .7rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
    }
    .letter-line { margin: .5rem 0; padding-left: .7rem; border-left: 2px solid #e6a15a; font-size: .86rem; line-height: 1.45; }
    .letter-line.response { margin-left: 1rem; border-color: #28756d; color: #4c3740; }
    .letter-foot { margin-top: .7rem; color: #745b64; font-size: .7rem; }
    .landing-strip {
        margin: 0 calc(50% - 50vw);
        padding: 1rem max(2rem, calc((100vw - 1120px) / 2));
        background: #184f4a;
        color: #f8eee8;
        font-size: .88rem;
        letter-spacing: .025em;
    }
    .urdu-section {
        display: grid;
        grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
        gap: clamp(2rem, 6vw, 5rem);
        align-items: center;
        margin: 0 calc(50% - 50vw);
        padding: clamp(2.8rem, 6vw, 4.8rem) max(2rem, calc((100vw - 1120px) / 2));
        border-bottom: 1px solid #d6bdc3;
        background: #f2dfe4;
        color: #3c2831;
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        text-align: left;
    }
    .urdu-kicker {
        color: #88425a;
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        font-size: .73rem;
        font-weight: 800;
        letter-spacing: .1em;
    }
    .urdu-section h2 {
        margin: .5rem 0 .8rem;
        color: #571f35;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: clamp(2.1rem, 4.7vw, 3.8rem);
        font-weight: 600;
        line-height: 1.08;
        letter-spacing: -.025em;
    }
    .urdu-section p { margin: 0; color: #604853; font-size: 1.08rem; line-height: 1.75; }
    .urdu-prompts { display: grid; gap: .7rem; }
    .urdu-prompt {
        padding: .85rem 1.05rem;
        border-left: 3px solid #e6a15a;
        background: rgba(255,253,249,.72);
        color: #4c3640;
        font-size: 1rem;
        line-height: 1.6;
        transition: transform .24s ease, background-color .24s ease, box-shadow .24s ease;
    }
    .landing-section { padding: clamp(3.7rem, 8vw, 6.5rem) 0; }
    .landing-section h2 {
        max-width: 780px;
        margin: .55rem 0 1rem;
        font-size: clamp(2.2rem, 5vw, 4.1rem);
        line-height: 1.02;
    }
    .landing-intro { max-width: 700px; color: #684f59; font-size: 1.08rem; line-height: 1.7; }
    .need-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .75rem;
        margin: 2rem 0 0;
    }
    .need-note {
        position: relative;
        padding: 1.15rem 1.2rem 1.15rem 2.8rem;
        border: 1px solid #d7c1c5;
        border-radius: 3px;
        background: #fffdf9;
        color: #4f3942;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: 1.08rem;
        line-height: 1.45;
        box-shadow: 0 0 0 rgba(87,31,53,0);
        transition: transform .24s ease, border-color .24s ease, box-shadow .24s ease;
    }
    .need-note:before {
        content: "“";
        position: absolute;
        left: 1rem;
        top: .65rem;
        color: #b85c73;
        font-size: 2rem;
    }
    .mode-grid, .trust-grid, .steps-grid { display: grid; gap: 1rem; margin-top: 2.2rem; }
    .mode-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .trust-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .steps-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); counter-reset: landing-step; }
    .landing-card {
        min-height: 190px;
        padding: 1.6rem;
        border: 1px solid #d7c1c5;
        border-radius: 3px;
        background: #fffdf9;
        box-shadow: 0 0 0 rgba(87,31,53,0);
        transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
    }
    .landing-card h3 { margin: .3rem 0 .6rem; font-size: 1.45rem; }
    .landing-card p { color: #684f59; line-height: 1.6; }
    .card-mark { color: #28756d; font-size: .73rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
    .step-card { position: relative; padding-top: 4.4rem; }
    .step-card:before {
        counter-increment: landing-step;
        content: counter(landing-step, decimal-leading-zero);
        position: absolute;
        top: 1.2rem;
        left: 1.6rem;
        color: #b85c73;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: 1.5rem;
    }
    .auth-stage {
        margin: 1rem calc(50% - 50vw) -2rem;
        padding: clamp(4rem, 8vw, 6.5rem) max(2rem, calc((100vw - 1120px) / 2));
        background: #eadde0;
    }
    .auth-stage h2 { margin: .45rem 0 .8rem; font-size: clamp(2.4rem, 5vw, 4.2rem); }
    .auth-stage-copy { max-width: 660px; margin-bottom: 2rem; color: #674c56; font-size: 1.05rem; }
    .auth-panel {
        padding: 1.2rem 1.4rem 1.4rem;
        border: 1px solid #cfb7bd;
        border-radius: 3px;
        background: #fffdf9;
        box-shadow: 0 18px 45px rgba(87,31,53,.1);
    }
    .story-section,
    .process-section,
    .trust-section {
        position: relative;
        overflow: hidden;
        margin: 0 calc(50% - 50vw);
        padding-right: max(2rem, calc((100vw - 1120px) / 2));
        padding-left: max(2rem, calc((100vw - 1120px) / 2));
        isolation: isolate;
    }
    .story-section {
        background:
            radial-gradient(circle at 92% 13%, rgba(230,161,90,.22), transparent 24rem),
            linear-gradient(145deg, #fffaf4 0%, #f8e9e9 100%);
    }
    .story-section:after {
        content: "";
        position: absolute;
        z-index: -1;
        width: 26rem;
        height: 26rem;
        right: -13rem;
        bottom: 6rem;
        border: 1px solid rgba(184,92,115,.28);
        border-radius: 50%;
        animation: quiet-glow 9s ease-in-out infinite;
    }
    .story-section .need-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: 3rem;
        row-gap: 0;
    }
    .story-section .need-note {
        min-height: 78px;
        padding: 1.15rem .5rem 1.15rem 2.4rem;
        border: 0;
        border-bottom: 1px solid rgba(87,31,53,.2);
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .story-section .need-note:before { left: 0; }
    .story-section .mode-grid { gap: clamp(1rem, 3vw, 2.2rem); margin-top: 4rem; }
    .story-section .landing-card {
        min-height: 285px;
        padding: clamp(2rem, 4vw, 3.2rem);
        border: 0;
        border-radius: 48% 48% 1.25rem 1.25rem / 34% 34% 1.25rem 1.25rem;
        box-shadow: 0 24px 55px rgba(87,31,53,.13);
    }
    .story-section .landing-card:first-child { background: #184f4a; }
    .story-section .landing-card:first-child h3,
    .story-section .landing-card:first-child p { color: #fff8f1; }
    .story-section .landing-card:first-child .card-mark { color: #f0b46f; }
    .story-section .landing-card:last-child { background: #f4ced5; }
    .process-section {
        background: #351323;
        color: #fff8f1;
    }
    .process-section .section-kicker { color: #f0b46f; }
    .process-section h2 { color: #fff8f1; }
    .process-section .steps-grid {
        position: relative;
        gap: clamp(1.5rem, 4vw, 4rem);
        margin-top: 4rem;
    }
    .process-section .steps-grid:before {
        content: "";
        position: absolute;
        top: 2rem;
        right: 8%;
        left: 8%;
        height: 1px;
        background: linear-gradient(90deg, #f0b46f, #f2c8d1, #f0b46f);
        transform-origin: left;
    }
    .process-section .landing-card {
        min-height: auto;
        padding: 5rem .25rem 0;
        border: 0;
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .process-section .landing-card h3 { color: #fff8f1; }
    .process-section .landing-card p { color: #dbc8cf; }
    .process-section .step-card:before {
        display: grid;
        place-items: center;
        top: 0;
        left: calc(50% - 2rem);
        width: 4rem;
        height: 4rem;
        border: 1px solid #f0b46f;
        border-radius: 50%;
        background: #351323;
        color: #f0b46f;
        font-size: 1.05rem;
    }
    .trust-section {
        background:
            radial-gradient(circle at 7% 105%, rgba(40,117,109,.15), transparent 28rem),
            #fffaf4;
    }
    .trust-section .trust-grid { gap: 0; margin-top: 3.5rem; }
    .trust-section .landing-card {
        min-height: auto;
        padding: .5rem clamp(1.2rem, 3vw, 2.4rem) 1rem;
        border: 0;
        border-right: 1px solid rgba(87,31,53,.2);
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .trust-section .landing-card:first-child { padding-left: 0; }
    .trust-section .landing-card:last-child { border-right: 0; }
    .urdu-prompt {
        padding: .75rem .25rem .9rem 1.1rem;
        border-bottom: 1px solid rgba(87,31,53,.16);
        background: transparent;
    }
    .auth-stage {
        position: relative;
        overflow: hidden;
        border-radius: 50% 50% 0 0 / 4.5rem 4.5rem 0 0;
        background:
            radial-gradient(circle at 85% 20%, rgba(230,161,90,.24), transparent 20rem),
            #eadde0;
    }
    .landing-marketing-hidden { display: none; }
    .auth-route-stage {
        min-height: 255px;
        margin-top: 0;
        padding-top: clamp(3.25rem, 7vw, 5.5rem);
        padding-bottom: clamp(2.5rem, 6vw, 4.5rem);
        border-radius: 0;
    }
    .terms-page {
        margin: 0 calc(50% - 50vw) -2rem;
        padding: clamp(4rem, 8vw, 7rem) max(2rem, calc((100vw - 940px) / 2)) 7rem;
        background: #fffaf4;
    }
    .terms-hero { max-width: 850px; margin-bottom: 4rem; }
    .terms-hero h1 {
        margin: .65rem 0 1rem;
        font-size: clamp(3.2rem, 8vw, 6.4rem);
        font-weight: 500;
        line-height: .94;
    }
    .terms-hero p { max-width: 760px; color: #604853; font-size: 1.12rem; line-height: 1.75; }
    .terms-draft {
        display: inline-block;
        margin-top: 1rem;
        padding: .7rem 1rem;
        border-left: 3px solid #e6a15a;
        background: #f7e8d6;
        color: #553d46;
        font-size: .9rem;
    }
    .terms-list { border-top: 1px solid #d8c3c7; }
    .terms-item {
        display: grid;
        grid-template-columns: 4rem minmax(0, 1fr);
        gap: 1.25rem;
        padding: 2rem 0;
        border-bottom: 1px solid #d8c3c7;
    }
    .terms-number { color: #b85c73; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.25rem; }
    .terms-item h2 { margin: 0 0 .65rem; font-size: 1.65rem; }
    .terms-item p, .terms-item li { color: #604853; line-height: 1.7; }
    .terms-item p { margin: .5rem 0; }
    .terms-item ul { margin: .6rem 0 0; padding-left: 1.15rem; }
    .terms-actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 3rem; }
    .terms-actions a {
        padding: .8rem 1.05rem;
        border: 1px solid #571f35;
        color: #571f35 !important;
        font-weight: 750;
        text-decoration: none;
    }
    .terms-actions a:first-child { background: #571f35; color: #fffaf4 !important; }
    .terms-update-stage {
        position: relative;
        overflow: hidden;
        max-width: 760px;
        margin: 6vh auto 1.5rem;
        padding: clamp(1.6rem, 4vw, 3rem);
        border-radius: 26px;
        background: #173f3b;
        color: #f9f2e9;
        box-shadow: 0 24px 60px rgba(18,63,59,.2);
    }
    .terms-update-stage:after {
        content: "";
        position: absolute;
        right: -4rem;
        top: -6rem;
        width: 17rem;
        height: 17rem;
        border: 1px solid rgba(230,161,90,.48);
        border-radius: 50%;
    }
    .terms-update-stage span { color: #efb674; font-size: .67rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .terms-update-stage h1 { position: relative; z-index: 1; margin: .55rem 0 .8rem; color: #fff9f2; font-size: clamp(2.25rem, 5vw, 3.8rem); font-weight: 520; line-height: 1; }
    .terms-update-stage p { position: relative; z-index: 1; max-width: 620px; margin: 0; color: #d7e5e1; line-height: 1.65; }
    .mandatory-review-note {
        max-width: 760px;
        margin: 0 auto 1.1rem;
        padding: 1rem 1.1rem;
        border-left: 4px solid #d88945;
        border-radius: 0 12px 12px 0;
        background: #fff3e5;
        color: #5c4335;
        font-size: .86rem;
        line-height: 1.6;
    }
    .admin-command {
        position: relative;
        overflow: hidden;
        margin: 0 0 1.2rem;
        padding: 2rem 2.2rem;
        border-radius: 1.2rem;
        background: #123f3b;
        color: #fdf7ee;
        box-shadow: 0 22px 55px rgba(18,63,59,.18);
    }
    .admin-command:after {
        content: "";
        position: absolute;
        right: -4rem;
        top: -7rem;
        width: 18rem;
        height: 18rem;
        border: 1px solid rgba(240,180,111,.45);
        border-radius: 50%;
    }
    .admin-command h1 { margin: .35rem 0 .55rem; color: #fff9f2; font-size: clamp(2.4rem, 5vw, 4.2rem); }
    .admin-command p { max-width: 760px; margin: 0; color: #d8e5df; line-height: 1.65; }
    .admin-eyebrow { color: #f0b46f; font-size: .72rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
    .admin-privacy-rule {
        margin: .8rem 0 1.4rem;
        padding: .85rem 1rem;
        border-left: 3px solid #e6a15a;
        background: #f7e8d6;
        color: #533c45;
        font-size: .9rem;
        line-height: 1.55;
    }
    .admin-profile {
        display: grid;
        grid-template-columns: minmax(180px, 1.4fr) repeat(4, minmax(95px, .7fr));
        gap: 1rem;
        align-items: center;
        margin: 1rem 0 1.4rem;
        padding: 1rem 1.2rem;
        border-top: 1px solid #ccb9bd;
        border-bottom: 1px solid #ccb9bd;
    }
    .admin-profile strong { display: block; color: #3c2831; font-size: 1.02rem; }
    .admin-profile span { display: block; color: #765d66; font-size: .78rem; line-height: 1.45; }
    .admin-status {
        display: inline-flex;
        align-items: center;
        gap: .4rem;
        width: fit-content;
        padding: .34rem .62rem;
        border-radius: 999px;
        background: #dcebe5;
        color: #184f4a;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .04em;
    }
    .admin-status.off { background: #eee3e4; color: #755a64; }
    .admin-status.live { background: #f7dfc5; color: #7b4217; }
    .scope-ladder {
        display: grid;
        gap: .35rem;
        margin: .5rem 0 1.25rem;
        padding-left: .8rem;
        border-left: 2px solid #d5c0c4;
    }
    .scope-ladder div { color: #725963; font-size: .78rem; }
    .scope-ladder strong { color: #3f2932; }
    .admin-session-head {
        margin: .6rem 0 1rem;
        padding: 1.1rem 1.2rem;
        border-left: 4px solid #28756d;
        background: #edf3ef;
    }
    .admin-session-head strong { color: #25443f; }
    .admin-session-head span { color: #62736f; font-size: .82rem; }
    .admin-history-intro {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        margin: 1.5rem 0 .55rem;
    }
    .admin-history-intro strong { color: #3c2831; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.45rem; }
    .admin-history-intro span { color: #806a71; font-size: .78rem; }
    .admin-chat-preview {
        margin: 0 0 .3rem;
        color: #3c2831;
        font-size: .94rem;
        font-weight: 750;
        line-height: 1.35;
    }
    .admin-chat-meta { color: #75646a; font-size: .76rem; line-height: 1.45; }
    .admin-session-id { color: #927f85 !important; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .control-panel {
        padding: 1rem 1rem .4rem;
        border: 1px solid #cfbfc2;
        border-radius: .8rem;
        background: #fffaf4;
    }
    .control-panel h3 { margin-top: .15rem; }
    .admin-divider-label { margin: 1.5rem 0 .5rem; color: #8c6976; font-size: .7rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
    .admin-shell-marker { display: none; }
    body:has(.admin-shell-marker) [data-stale="true"] {
        opacity: 1 !important;
        transition: none !important;
    }
    .block-container:has(.admin-shell-marker) {
        max-width: 1840px;
        padding: 1rem clamp(.8rem, 1.7vw, 1.8rem) 1.6rem;
    }
    .admin-rail-brand {
        margin: 0 0 1.35rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #dce7e3;
    }
    .admin-rail-brand img { display: block; width: min(158px, 88%); margin-bottom: .75rem; }
    .admin-rail-brand span {
        color: #51716c;
        font-size: .67rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .admin-rail-label {
        margin: 1rem .15rem .45rem;
        color: #6e8883;
        font-size: .64rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .admin-rail-foot {
        margin-top: 1.3rem;
        padding: 1rem .15rem 0;
        border-top: 1px solid #dce7e3;
        color: #607772;
        font-size: .74rem;
        line-height: 1.5;
    }
    .admin-workspace-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin: .15rem 0 1.35rem;
        padding: .2rem .15rem 1.05rem;
        border-bottom: 1px solid #d9e4e0;
    }
    .admin-workspace-head .admin-page-tag {
        display: block;
        margin-bottom: .35rem;
        color: #b66c35;
        font-size: .66rem;
        font-weight: 800;
        letter-spacing: .13em;
        text-transform: uppercase;
    }
    .admin-workspace-head h1 { margin: 0; color: #173f3b; font-size: clamp(2rem, 3vw, 3rem); font-weight: 550; }
    .admin-workspace-head p { max-width: 720px; margin: .45rem 0 0; color: #627772; font-size: .88rem; line-height: 1.55; }
    .admin-kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: .7rem;
        margin: 0 0 1.45rem;
    }
    .admin-kpi {
        min-height: 102px;
        padding: 1rem;
        border: 1px solid #d9e5e1;
        border-radius: 15px;
        background: rgba(255,253,249,.84);
        box-shadow: 0 8px 22px rgba(18,63,59,.04);
    }
    .admin-kpi span { display: block; color: #71827e; font-size: .64rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .admin-kpi strong { display: block; margin-top: .45rem; color: #17443f; font-family: "Iowan Old Style", Georgia, serif; font-size: 2rem; font-weight: 550; }
    .app-usage-board {
        display: grid;
        grid-template-columns: minmax(180px, .72fr) minmax(0, 2fr);
        gap: 1rem;
        margin: 0 0 1.25rem;
        padding: 1rem;
        border: 1px solid #d6e4df;
        border-radius: 18px;
        background: linear-gradient(135deg, #f5faf7 0%, #fffaf4 100%);
    }
    .app-install-total {
        position: relative;
        min-height: 122px;
        padding: 1rem 1rem .9rem 4.4rem;
        border-radius: 14px;
        background: #184f4a;
        color: #fff;
    }
    .app-install-total:before {
        content: "";
        position: absolute;
        top: 1rem;
        left: 1rem;
        width: 2.45rem;
        height: 4.2rem;
        border: 2px solid rgba(255,255,255,.82);
        border-radius: 10px;
        box-shadow: 8px 7px 0 -3px #d8904f;
    }
    .app-install-total:after {
        content: "";
        position: absolute;
        bottom: 1.35rem;
        left: 1.9rem;
        width: .4rem;
        height: .4rem;
        border-radius: 50%;
        background: #fff;
    }
    .app-install-total span { display: block; color: #cfe4df; font-size: .62rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .app-install-total strong { display: block; margin-top: .32rem; font-family: "Iowan Old Style", Georgia, serif; font-size: 2.5rem; font-weight: 550; line-height: 1; }
    .app-install-total small { display: block; margin-top: .48rem; color: #dcebe7; font-size: .68rem; line-height: 1.4; }
    .app-source-ledger { padding: .35rem .2rem; }
    .app-source-ledger h3 { margin: 0; color: #244b47; font-size: 1rem; }
    .app-source-ledger p { margin: .28rem 0 .85rem; color: #6d7e7a; font-size: .75rem; line-height: 1.45; }
    .app-source-track {
        display: flex;
        width: 100%;
        height: 22px;
        overflow: hidden;
        border: 1px solid #cfddd8;
        border-radius: 999px;
        background: #e9efec;
    }
    .app-source-track .web { background: #245e58; }
    .app-source-track .android { background: #d8904f; }
    .app-source-legend { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; margin-top: .72rem; }
    .app-source-legend div { padding-top: .55rem; border-top: 1px solid #dce5e2; }
    .app-source-legend span { color: #71827e; font-size: .62rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .app-source-legend strong { display: block; margin-top: .18rem; color: #2d4d49; font-size: .82rem; }
    .app-usage-note { margin: .3rem 0 1rem; color: #6e7e7a; font-size: .72rem; line-height: 1.5; }
    .admin-section-title { margin: 1.45rem 0 .75rem; }
    .admin-section-title h2 { margin: 0; color: #214a46; font-size: 1.45rem; }
    .admin-section-title p { margin: .25rem 0 0; color: #71827e; font-size: .8rem; line-height: 1.5; }
    .admin-attention {
        margin: .25rem 0 1rem;
        padding: 1rem 1.1rem;
        border-left: 3px solid #d8904f;
        border-radius: 0 12px 12px 0;
        background: #fff4e8;
        color: #634c3d;
        font-size: .82rem;
        line-height: 1.55;
    }
    .admin-case-card h3 { margin: 0 0 .35rem; color: #264b47; font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif; font-size: .95rem; font-weight: 750; }
    .admin-case-card p { margin: 0; color: #72817e; font-size: .76rem; line-height: 1.5; }
    .admin-case-card .admin-case-message { margin-top: .55rem; color: #49383f; font-size: .84rem; }
    .admin-inspector-head {
        margin-bottom: .9rem;
        padding-bottom: .8rem;
        border-bottom: 1px solid #d8e4e0;
    }
    .admin-inspector-head span { color: #b36b38; font-size: .63rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .admin-inspector-head strong { display: block; margin-top: .28rem; color: #214a46; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.35rem; font-weight: 600; overflow-wrap: anywhere; }
    .admin-inspector-head p { margin: .35rem 0 0; color: #6b7d79; font-size: .76rem; line-height: 1.5; }
    .admin-fact-list { display: grid; gap: .65rem; margin: .35rem 0 1rem; }
    .admin-fact-list > div { padding-bottom: .62rem; border-bottom: 1px solid #e3ebe8; }
    .admin-fact-list span { display: block; color: #7a8a86; font-size: .61rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .admin-fact-list strong { display: block; margin-top: .18rem; color: #334c48; font-size: .8rem; line-height: 1.4; overflow-wrap: anywhere; }
    .admin-transcript-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin: .45rem 0 .6rem;
        padding: .62rem .78rem;
        border-radius: 12px;
        background: #edf4f1;
    }
    .admin-transcript-head strong { display: block; color: #244a46; font-size: .84rem; line-height: 1.32; }
    .admin-transcript-head span { display: block; margin-top: .18rem; color: #6d817d; font-size: .66rem; line-height: 1.32; }
    .admin-transcript-status {
        display: flex;
        flex: 0 0 auto;
        flex-direction: column;
        align-items: flex-end;
        gap: .38rem;
    }
    .admin-user-typing {
        display: flex;
        align-items: center;
        gap: .42rem;
        width: fit-content;
        margin: 0;
        padding: .32rem .52rem .32rem .38rem;
        border: 1px solid #bdd8d1;
        border-radius: 999px;
        background: #f1f8f5;
        color: #285c55;
        font-size: .65rem;
        font-weight: 750;
        line-height: 1;
        box-shadow: 0 5px 14px rgba(23,63,59,.07);
    }
    .admin-user-typing strong { color: #214e49; font-size: .66rem; }
    .admin-typing-bubble {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.62rem;
        height: 1.15rem;
        border-radius: .58rem;
        background: #2f766e;
    }
    .admin-typing-bubble::after {
        content: "";
        position: absolute;
        left: .18rem;
        bottom: -.16rem;
        width: .34rem;
        height: .34rem;
        background: #2f766e;
        clip-path: polygon(0 0, 100% 0, 0 100%);
    }
    .admin-typing-dots { display: inline-flex; gap: .13rem; }
    .admin-typing-dots i {
        width: .22rem;
        height: .22rem;
        border-radius: 50%;
        background: #f8fffc;
        animation: admin-typing-pulse 1.05s infinite ease-in-out;
    }
    .admin-typing-dots i:nth-child(2) { animation-delay: .14s; }
    .admin-typing-dots i:nth-child(3) { animation-delay: .28s; }
    @keyframes admin-typing-pulse {
        0%, 65%, 100% { opacity: .35; transform: translateY(0); }
        32% { opacity: 1; transform: translateY(-2px); }
    }
    .admin-read-receipt {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        margin: 0;
        padding: .08rem .34rem;
        border-radius: 999px;
        font-size: .56rem;
        font-weight: 800;
        letter-spacing: .03em;
    }
    .admin-read-receipt.read { background: #e3f1ec; color: #23685f; }
    .admin-read-receipt.unread { background: #fff0df; color: #9a5b27; }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] {
        position: relative;
        display: flex;
        align-items: flex-start;
        gap: .55rem;
        width: min(94%, 920px);
        margin: 0 auto .58rem 0;
        padding: 0 4.35rem 0 0;
        border: 0;
        background: transparent;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) {
        flex-direction: row-reverse;
        margin-right: 0;
        margin-left: auto;
        padding-right: 4.35rem;
        padding-left: 0;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
        --admin-bubble-pad-x: .82rem;
        --admin-bubble-pad-bottom: .52rem;
        flex: 1 1 0;
        width: auto;
        max-width: none;
        min-width: 0;
        box-sizing: border-box;
        padding: .52rem .82rem;
        border: 1px solid #dce6e2;
        border-radius: 6px 17px 17px 17px;
        background: #fffdf9;
        box-shadow: 0 7px 18px rgba(28,66,61,.05);
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] .stMarkdown,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"],
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] li,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] a,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] code {
        min-width: 0;
        max-width: 100%;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] pre {
        max-width: 100%;
        overflow-x: auto;
        white-space: pre-wrap;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] {
        border-color: #245e58;
        border-radius: 17px 6px 17px 17px;
        background: #245e58;
        color: #fffdf8;
        box-shadow: 0 8px 20px rgba(23,63,59,.14);
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] p,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] li,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stCaptionContainer"] {
        color: #fffdf8 !important;
    }
    .admin-message-meta {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: .3rem;
        margin: .14rem calc(var(--admin-bubble-pad-x) * -1) calc(var(--admin-bubble-pad-bottom) * -1);
        padding: .1rem var(--admin-bubble-pad-x) .42rem;
        border-radius: 0 0 17px 17px;
        background: #fffdf9;
        color: #7b8986;
        font-size: .6rem;
        font-weight: 650;
        line-height: 1.25;
    }
    .admin-message-meta-copy {
        min-width: 0;
        max-width: 100%;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) .admin-message-meta {
        background: #245e58;
        color: rgba(255,253,248,.72);
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) .message-reply-quote {
        border-left-color: #f0b26c;
        background: rgba(255,255,255,.11);
        color: #fff7ef;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) .message-reply-quote span {
        color: #ffd49f;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) div[class*="st-key-admin_reply_message_"] .stButton button {
        border: 1px solid rgba(255,255,255,.2) !important;
        background: rgba(255,255,255,.11) !important;
        color: #e6f3ef !important;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) div[class*="st-key-admin_reply_message_"] .stButton button p,
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) div[class*="st-key-delete_message_"] .stButton button p {
        color: inherit !important;
    }
    .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) div[class*="st-key-delete_message_"] .stButton button {
        background: rgba(36,94,88,.1) !important;
        color: #245e58 !important;
    }
    .st-key-admin_reply_composer {
        margin: .75rem 0 .85rem;
        padding: .55rem;
        border: 1px solid #d7e3df;
        border-radius: 12px;
        background: #f7fbf9;
    }
    .st-key-admin_reply_composer .message-reply-quote { margin: 0 0 .45rem; }
    .st-key-admin_reply_composer .stButton button {
        min-height: 32px;
        border-radius: 9px;
        font-size: .72rem;
    }
    .st-key-admin_chat_composer {
        position: sticky;
        bottom: .55rem;
        z-index: 24;
        margin: 1rem 0 .35rem;
        padding: .85rem .9rem .75rem;
        border: 1px solid #b9d1ca;
        border-bottom: 4px solid #245e58;
        border-radius: 18px 18px 8px 8px;
        background: rgba(247,251,249,.98);
        box-shadow: 0 14px 34px rgba(23,63,59,.16);
        backdrop-filter: blur(10px);
    }
    .admin-writing-review {
        margin: .45rem 0 .8rem;
        padding: .9rem 1rem;
        border-left: 3px solid #c47e56;
        background: #fff8ef;
        color: #4f343d;
    }
    .admin-writing-review span {
        display: block;
        margin-bottom: .28rem;
        color: #9a5b42;
        font-size: .64rem;
        font-weight: 820;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .admin-writing-review p { margin: 0; white-space: pre-wrap; line-height: 1.55; }
    .admin-writing-review.corrected { border-left-color: #2e766c; background: #f0f7f3; }
    .admin-writing-review.corrected span { color: #2e766c; }
    .admin-writing-review-note {
        margin: .2rem 0 .7rem;
        color: #765e67;
        font-size: .76rem;
        line-height: 1.5;
    }
    .admin-composer-label {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: .75rem;
        margin: 0 0 .55rem;
        color: #173f3b;
    }
    .admin-composer-label strong { font-size: .82rem; }
    .admin-composer-label span { color: #68817b; font-size: .66rem; }
    .st-key-admin_chat_composer textarea {
        border-color: #c7d8d3 !important;
        border-radius: 15px !important;
        background: #fff !important;
        box-shadow: none !important;
    }
    .st-key-admin_chat_composer [data-testid="stFileUploaderDropzone"] {
        min-height: 0;
        padding: .45rem .6rem;
        border-color: #cadbd6;
        border-radius: 12px;
        background: #eef5f2;
    }
    .st-key-admin_chat_composer [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        font-size: .72rem;
    }
    .st-key-admin_chat_composer .message-reply-quote { margin: .1rem 0 .45rem; }
    .st-key-admin_chat_composer div[class*="st-key-cancel_admin_chat_reply_"] .stButton button {
        width: 32px;
        min-width: 32px;
        height: 32px;
        min-height: 32px;
        padding: 0;
        border-radius: 50%;
    }
    div[class*="st-key-delete_message_"] {
        position: absolute;
        top: .45rem;
        right: .25rem;
        z-index: 3;
        display: flex;
        justify-content: flex-end;
        margin: 0;
    }
    div[class*="st-key-delete_message_"] .stButton button {
        display: grid;
        place-items: center;
        width: 1.85rem;
        min-width: 1.85rem;
        height: 1.85rem;
        min-height: 1.85rem;
        padding: 0;
        border: 0;
        border-radius: 50%;
        background: transparent;
        color: #81918d;
        box-shadow: none;
    }
    div[class*="st-key-delete_message_"] .stButton button:hover {
        background: #f8e8e6;
        color: #8f3f45;
    }
    div[class*="st-key-delete_message_"] .stButton button p {
        margin: 0;
        font-size: 1.15rem;
        line-height: 1;
    }
    div[class*="st-key-admin_reply_message_"] {
        position: absolute;
        top: .45rem;
        right: 2.25rem;
        z-index: 3;
        width: auto !important;
        margin: 0 !important;
    }
    div[class*="st-key-admin_reply_message_"] .stButton button {
        display: grid;
        place-items: center;
        width: 1.85rem;
        min-width: 1.85rem;
        height: 1.85rem;
        min-height: 1.85rem;
        margin: 0;
        padding: 0;
        border-radius: 50%;
        font-size: .85rem;
    }
    .admin-live-dot { display: inline-block; width: .5rem; height: .5rem; margin-right: .35rem; border-radius: 50%; background: #d8803c; box-shadow: 0 0 0 4px rgba(216,128,60,.13); }
    .visitor-live-board {
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.2rem;
        margin: .15rem 0 1.2rem;
        padding: 1.25rem 1.35rem;
        border-radius: 18px 18px 18px 4px;
        background: #173f3b;
        color: #f7fbf8;
        box-shadow: 0 14px 34px rgba(18,63,59,.13);
    }
    .visitor-live-board:after {
        content: "";
        position: absolute;
        right: -36px;
        width: 150px;
        height: 150px;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 50%;
    }
    .visitor-live-board span { display: block; color: #a9cbc4; font-size: .64rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .visitor-live-board strong { display: block; margin-top: .25rem; color: #fffaf4; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.65rem; font-weight: 550; }
    .visitor-live-count { position: relative; z-index: 1; min-width: 74px; text-align: right; }
    .visitor-live-count b { color: #f1b978; font-family: "Iowan Old Style", Georgia, serif; font-size: 2.5rem; font-weight: 550; }
    .visitor-page-pill {
        display: inline-flex;
        align-items: center;
        gap: .42rem;
        padding: .4rem .65rem;
        border-radius: 999px;
        background: #e4f0ec;
        color: #205b54;
        font-size: .72rem;
        font-weight: 800;
    }
    .visitor-page-pill:before {
        content: "";
        width: .42rem;
        height: .42rem;
        border-radius: 50%;
        background: #2f897f;
        box-shadow: 0 0 0 4px rgba(47,137,127,.12);
    }
    .visitor-privacy-note {
        margin: 1rem 0;
        padding: .85rem 1rem;
        border-left: 3px solid #2c756d;
        background: #edf5f1;
        color: #526c67;
        font-size: .78rem;
        line-height: 1.55;
    }
    .admin-empty {
        margin: 1rem 0;
        padding: 2.5rem 1.2rem;
        border: 1px dashed #c8dad5;
        border-radius: 16px;
        color: #6e817c;
        text-align: center;
    }
    .admin-empty strong { display: block; margin-bottom: .35rem; color: #2e514d; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.25rem; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.admin-card-marker) {
        margin-bottom: .75rem;
        border: 1px solid #d9e5e1 !important;
        border-radius: 15px !important;
        background: rgba(255,253,249,.82);
        box-shadow: 0 7px 20px rgba(18,63,59,.035);
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.admin-card-marker):hover {
        border-color: #a9c7c0 !important;
        box-shadow: 0 11px 26px rgba(18,63,59,.07);
        transform: translateY(-1px);
    }
    .admin-card-marker { display: none; }
    div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) { align-items: flex-start; gap: 1rem; }
    div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"] {
        box-sizing: border-box;
        min-width: 0;
    }
    div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:last-child {
        position: sticky;
        top: 1rem;
        overflow-y: auto;
        max-height: calc(100vh - 2rem);
        padding: 1rem;
        border: 1px solid #d5e3df;
        border-radius: 18px;
        background: rgba(247,251,248,.94);
        box-shadow: 0 10px 30px rgba(18,63,59,.055);
        scrollbar-width: thin;
    }
    .st-key-admin_mobile_nav { display: none; }
    @keyframes masthead-in {
        from { opacity: 0; transform: translateY(-14px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes copy-rise {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes portrait-arrive {
        from { opacity: 0; transform: translateX(34px) scale(.97); }
        to { opacity: 1; transform: translateX(0) scale(1); }
    }
    @keyframes note-settle {
        from { opacity: 0; transform: translateY(26px) rotate(2deg); }
        to { opacity: 1; transform: translateY(0) rotate(-2deg); }
    }
    @keyframes pattern-drift {
        from { background-position: 0 0, 0 0; }
        to { background-position: 64px 0, -64px 0; }
    }
    @keyframes quiet-glow {
        0%, 100% { opacity: .5; transform: scale(.94); }
        50% { opacity: .82; transform: scale(1.04); }
    }
    @keyframes section-reveal {
        from { opacity: 0; transform: translateY(28px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @supports (animation-timeline: view()) {
        .landing-section > .section-kicker,
        .landing-section > h2,
        .landing-section > .landing-intro,
        .landing-section > .need-grid,
        .landing-section > .mode-grid,
        .landing-section > .steps-grid,
        .landing-section > .trust-grid,
        .urdu-section > * {
            animation: section-reveal linear both;
            animation-timeline: view();
            animation-range: entry 5% cover 30%;
        }
        .process-section .steps-grid:before {
            animation: timeline-grow linear both;
            animation-timeline: view();
            animation-range: entry 10% cover 45%;
        }
    }
    @keyframes timeline-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
    @media (hover: hover) {
        .site-nav a:hover { background: #f2dfe4; transform: translateY(-1px); }
        .landing-actions a:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0,0,0,.18); }
        .hero-art:hover .hero-portrait { transform: scale(1.012); filter: saturate(1.04); }
        .hero-art:hover .letter-preview { transform: translateY(-5px) rotate(-.4deg); box-shadow: 10px 16px 34px rgba(34,12,22,.34); }
        .landing-card:hover, .need-note:hover { transform: translateY(-4px); border-color: #b98f99; box-shadow: 0 14px 30px rgba(87,31,53,.09); }
        .story-section .landing-card:hover { transform: translateY(-10px) rotate(.3deg); box-shadow: 0 34px 65px rgba(87,31,53,.18); }
        .story-section .need-note:hover { transform: translateX(7px); box-shadow: none; }
        .process-section .landing-card:hover, .trust-section .landing-card:hover { transform: translateY(-5px); box-shadow: none; }
        .urdu-prompt:hover { transform: translateX(6px); background: transparent; box-shadow: none; }
    }
    .metric-label { color: #765c66; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
    .metric-value { color: var(--jam); font-family: "Iowan Old Style", Georgia, serif; font-size: 2rem; }
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 4px;
        border-color: var(--jam);
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background: var(--jam);
        color: white;
    }
    .stButton > button:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 3px solid rgba(230, 161, 90, .55) !important;
        outline-offset: 2px;
    }
    [data-testid="stChatMessage"] {
        border-radius: 6px;
        border: 1px solid #e3d5d4;
        background: rgba(255, 253, 249, .88);
    }
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    .dilse-app-shell-marker { display: none; }
    .block-container:has(.dilse-app-shell-marker) {
        max-width: 1760px;
        padding: 1rem clamp(.8rem, 2vw, 2rem) 1.5rem;
    }
    .app-logo {
        display: block;
        width: min(168px, 90%);
        margin: .15rem 0 1.35rem;
    }
    .rail-label {
        margin: 1.15rem 0 .45rem;
        color: #8a6e77;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .rail-user {
        margin-top: 1.2rem;
        padding: .85rem .1rem .15rem;
        border-top: 1px solid #e3d7d8;
    }
    .rail-user strong { display: block; color: #3b2530; font-size: .9rem; }
    .rail-user span { color: #836d75; font-size: .75rem; }
    .chat-surface-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        min-height: 64px;
        margin-bottom: 1.2rem;
        padding: .35rem .2rem 1rem;
        border-bottom: 1px solid #e2d6d7;
    }
    .chat-surface-header strong {
        display: block;
        overflow: hidden;
        max-width: 540px;
        color: #3b2530;
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        font-size: .98rem;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .chat-surface-header span { color: #8a7179; font-size: .75rem; }
    .chat-mode-pill {
        flex: 0 0 auto;
        padding: .38rem .68rem;
        border-radius: 999px;
        background: #efe2e5;
        color: #6d3348 !important;
        font-size: .7rem !important;
        font-weight: 800;
    }
    .chat-empty {
        display: grid;
        place-items: center;
        min-height: 36vh;
        padding: 3rem 1rem 2rem;
        text-align: center;
    }
    .chat-empty .heartline {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        color: #a24b66;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .11em;
        text-transform: uppercase;
    }
    .chat-empty .heartline:before,
    .chat-empty .heartline:after {
        content: "";
        width: 28px;
        height: 1px;
        background: #d9a166;
    }
    .chat-empty h1 {
        max-width: 650px;
        margin: .8rem auto .65rem;
        font-size: clamp(2.25rem, 4vw, 3.7rem);
        font-weight: 500;
        line-height: 1.02;
    }
    .chat-empty p { max-width: 560px; margin: 0 auto; color: #76616a; line-height: 1.65; }
    .setup-heading { margin: 0 0 1rem; }
    .setup-heading span {
        display: block;
        color: #a04c65;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .setup-heading strong {
        display: block;
        margin-top: .25rem;
        color: #3c2630;
        font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        font-size: 1.35rem;
        font-weight: 600;
    }
    .setup-note {
        margin: .2rem 0 1rem;
        padding: .7rem .8rem;
        border-left: 3px solid #d99b57;
        background: #fff8ef;
        color: #705b62;
        font-size: .78rem;
        line-height: 1.5;
    }
    .privacy-dot {
        display: inline-block;
        width: .5rem;
        height: .5rem;
        margin-right: .35rem;
        border-radius: 50%;
        background: #2d776d;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) {
        align-items: flex-start;
        gap: 1rem;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child {
        position: sticky;
        top: 1rem;
        overflow-y: auto;
        max-height: calc(100vh - 2rem);
        padding: 1rem;
        border: 1px solid #e2d5d7;
        border-radius: 18px;
        background: rgba(255, 252, 248, .92);
        box-shadow: 0 10px 30px rgba(74, 36, 50, .05);
        scrollbar-width: thin;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) {
        min-height: calc(100vh - 2rem);
        padding: .35rem clamp(.25rem, 2vw, 1.6rem) 1rem;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatInput"] {
        padding-top: .8rem;
        border-top: 1px solid #eadfe0;
        background: linear-gradient(180deg, rgba(251,244,236,0), #fbf4ec 28%);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatInput"] textarea {
        min-height: 58px;
        border-color: #cfb9bf;
        border-radius: 18px;
        background: #fffdf9;
        box-shadow: 0 8px 24px rgba(75,32,49,.08);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatMessage"] {
        margin-bottom: .75rem;
        padding: .15rem .35rem;
        border: 0;
        border-radius: 16px;
        background: transparent;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #f1e4e7;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) .stButton > button {
        min-height: 42px;
        border-radius: 12px;
        font-weight: 650;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) input,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) textarea,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-baseweb="select"] > div {
        border-radius: 12px;
    }
    .dashboard-page-head {
        position: relative;
        overflow: hidden;
        margin: .2rem 0 1.8rem;
        padding: .25rem 0 1.45rem;
        border-bottom: 1px solid #ddcfd2;
    }
    .dashboard-page-head:after {
        content: "";
        position: absolute;
        right: .25rem;
        bottom: -1px;
        width: 82px;
        height: 3px;
        border-radius: 999px;
        background: linear-gradient(90deg, #d89a57, #a34b66);
    }
    .dashboard-page-head .eyebrow,
    .page-section-head .eyebrow {
        color: #9b4761;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .13em;
        text-transform: uppercase;
    }
    .dashboard-page-head h1 {
        margin: .35rem 0 .45rem;
        font-size: clamp(2.1rem, 3.5vw, 3.15rem);
        font-weight: 520;
        line-height: 1.05;
    }
    .dashboard-page-head p {
        max-width: 650px;
        margin: 0;
        color: #735f67;
        font-size: .94rem;
        line-height: 1.6;
    }
    .page-section-head {
        margin: 2rem 0 1rem;
        padding-top: .2rem;
    }
    .page-section-head h2 {
        margin: .25rem 0 .3rem;
        font-size: 1.65rem;
        font-weight: 560;
    }
    .page-section-head p {
        max-width: 650px;
        margin: 0;
        color: #78646c;
        font-size: .87rem;
        line-height: 1.55;
    }
    .dashboard-empty {
        margin: 1.3rem 0;
        padding: 2.6rem 1.5rem;
        border: 1px dashed #cfb8bf;
        border-radius: 22px;
        background: rgba(255,253,249,.68);
        text-align: center;
    }
    .dashboard-empty .empty-mark {
        display: grid;
        place-items: center;
        width: 44px;
        height: 44px;
        margin: 0 auto .85rem;
        border-radius: 50%;
        background: #f0e1e4;
        color: #7a2f4a;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: 1.2rem;
    }
    .dashboard-empty h3 { margin: 0 0 .35rem; font-size: 1.35rem; }
    .dashboard-empty p { max-width: 480px; margin: 0 auto; color: #79666d; line-height: 1.55; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.conversation-row-marker) {
        margin-bottom: .8rem;
        border: 1px solid #e2d5d7 !important;
        border-radius: 16px !important;
        background: rgba(255,253,249,.82);
        box-shadow: 0 7px 20px rgba(74,36,50,.035);
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.conversation-row-marker):hover {
        border-color: #c9adb5 !important;
        box-shadow: 0 11px 25px rgba(74,36,50,.07);
        transform: translateY(-1px);
    }
    .conversation-row-marker { display: none; }
    .conversation-row-copy h3 {
        margin: 0 0 .35rem;
        color: #3b2730;
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        font-size: .98rem;
        font-weight: 700;
        line-height: 1.42;
    }
    .conversation-row-copy p { margin: 0; color: #826d75; font-size: .76rem; }
    .conversation-mode-chip {
        display: inline-block;
        margin-right: .4rem;
        padding: .18rem .45rem;
        border-radius: 999px;
        background: #f0e1e5;
        color: #713047;
        font-size: .65rem;
        font-weight: 800;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.exercise-card-marker) {
        min-height: 100%;
        border: 1px solid #e1d2d5 !important;
        border-radius: 18px !important;
        background: rgba(255,253,249,.78);
        box-shadow: 0 8px 20px rgba(74,36,50,.035);
    }
    .exercise-card-marker { display: none; }
    .exercise-copy .exercise-symbol {
        display: grid;
        place-items: center;
        width: 36px;
        height: 36px;
        margin-bottom: .8rem;
        border-radius: 50%;
        background: #efe1e4;
        color: #7b314c;
        font-family: "Iowan Old Style", Georgia, serif;
        font-weight: 700;
    }
    .exercise-copy h3 { margin: 0 0 .35rem; font-size: 1.25rem; }
    .exercise-copy p { min-height: 2.7rem; margin: 0; color: #746069; font-size: .84rem; line-height: 1.5; }
    .prompt-card {
        position: relative;
        overflow: hidden;
        min-height: 220px;
        margin: .7rem 0 1rem;
        padding: 2rem clamp(1.4rem, 4vw, 2.7rem);
        border-radius: 22px;
        background: linear-gradient(145deg, #68223d 0%, #4a1a2e 100%);
        color: #fff8f2;
        box-shadow: 0 18px 42px rgba(74,26,46,.18);
    }
    .prompt-card:after {
        content: "";
        position: absolute;
        right: -45px;
        bottom: -55px;
        width: 190px;
        height: 150px;
        border: 1px solid rgba(255,255,255,.19);
        transform: rotate(-18deg);
    }
    .prompt-card .prompt-label { color: #efbd80; font-size: .68rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
    .prompt-card h3 { position: relative; z-index: 1; max-width: 650px; margin: .9rem 0 0; color: #fff8f2; font-size: clamp(1.6rem, 3vw, 2.25rem); font-weight: 500; line-height: 1.25; }
    .settings-summary {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .7rem;
        margin: .25rem 0 1.6rem;
    }
    .settings-summary > div {
        min-height: 84px;
        padding: .85rem .9rem;
        border-top: 2px solid #d49a58;
        background: rgba(255,253,249,.66);
    }
    .settings-summary span { display: block; color: #88727a; font-size: .66rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .settings-summary strong { display: block; margin-top: .35rem; color: #3e2832; font-size: .9rem; line-height: 1.35; }
    .settings-group {
        margin: 1.6rem 0 .85rem;
        padding: 0 0 .7rem;
        border-bottom: 1px solid #e3d7d9;
    }
    .settings-group h2 { margin: 0 0 .2rem; font-size: 1.35rem; }
    .settings-group p { margin: 0; color: #7c6870; font-size: .82rem; line-height: 1.5; }
    .settings-document-link {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: .25rem 0 1.2rem;
        padding: .9rem 1rem;
        border: 1px solid #ddcfd1;
        border-radius: 12px;
        background: #fffdf9;
        color: #571f35 !important;
        font-weight: 760;
        text-decoration: none;
        transition: border-color .18s ease, background-color .18s ease, transform .18s ease;
    }
    .settings-document-link:after { content: "Read →"; color: #9b5369; font-size: .76rem; }
    .settings-document-link:hover { border-color: #b7788c; background: #fff7f5; transform: translateY(-1px); }
    .settings-document-link:focus-visible { outline: 3px solid rgba(230,161,90,.55); outline-offset: 2px; }
    .privacy-explainer {
        margin-bottom: 1.4rem;
        padding: 1rem 1.1rem;
        border-left: 3px solid #27746a;
        background: #edf5f1;
        color: #48635f;
        font-size: .82rem;
        line-height: 1.55;
    }
    .account-identity {
        margin-bottom: 1.3rem;
        padding: 1.15rem 1.25rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #f1e2e5, #fff9f2);
    }
    .account-identity strong { display: block; color: #452b36; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.45rem; }
    .account-identity span { display: block; margin-top: .2rem; color: #7b6670; font-size: .82rem; overflow-wrap: anywhere; }
    .danger-zone {
        margin: 2.3rem 0 1rem;
        padding-top: 1.2rem;
        border-top: 1px solid #d9bfc4;
    }
    .danger-zone h2 { margin: 0 0 .3rem; color: #812f46; font-size: 1.4rem; }
    .danger-zone p { margin: 0; color: #765e67; font-size: .84rem; line-height: 1.55; }
    .context-note {
        margin: .3rem 0 1rem;
        color: #765f68;
        font-size: .8rem;
        line-height: 1.55;
    }
    .st-key-mobile_dashboard_nav,
    .st-key-mobile_conversation_controls,
    .st-key-mobile_close_conversation_settings { display: none; }
    .mobile-mode-label {
        color: #8f747e;
        font-size: .62rem;
        font-weight: 820;
        letter-spacing: .08em;
        text-transform: uppercase;
    }
    .mobile-settings-open-marker { display: none; }

    /* Conversation experience v2, assigned only to newly created accounts. */
    .dilse-v2-marker { display: none; }
    .block-container:has(.dilse-v2-marker) .new-chat-mode-intro h1 {
        max-width: 760px;
    }
    .block-container:has(.dilse-v2-marker) .new-chat-mode-card h2 {
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        font-weight: 680;
        letter-spacing: -.025em;
    }
    .v2-opening-question {
        width: min(100%, 760px);
        margin: 1.1rem auto .8rem;
        padding: 1rem 1.1rem;
        border-left: 3px solid #d79055;
        border-radius: 5px 18px 18px 5px;
        background: #fff8ef;
        color: #513b44;
    }
    .v2-opening-question strong { display: block; font-size: .96rem; }
    .v2-opening-question span { display: block; margin-top: .25rem; color: #806a72; font-size: .76rem; line-height: 1.45; }
    .v2-persona-intro {
        width: min(100%, 760px);
        margin: 1rem auto .65rem;
        text-align: center;
    }
    .v2-persona-intro span { color: #9a5269; font-size: .64rem; font-weight: 820; letter-spacing: .09em; text-transform: uppercase; }
    .v2-persona-intro h2 { margin: .35rem 0 .35rem; color: #30242a; font-size: 1.55rem; }
    .v2-persona-intro p { margin: 0; color: #806d74; font-size: .82rem; line-height: 1.5; }
    .st-key-v2_persona_choices {
        width: min(100%, 760px);
        margin: 0 auto .75rem;
    }
    .st-key-v2_persona_choices .stButton button {
        min-height: 38px;
        border-color: #d8c9cc;
        border-radius: 999px;
        background: #fffdf9;
        color: #60384a;
        font-size: .72rem;
    }
    .v2-outcome-panel {
        margin: .8rem 0 .5rem;
        padding: .72rem .82rem;
        border: 1px solid #e0d4d2;
        border-radius: 16px;
        background: rgba(255,253,249,.88);
    }
    .v2-outcome-panel strong { display: block; color: #473039; font-size: .78rem; }
    .v2-outcome-panel span { color: #806b73; font-size: .68rem; }
    .st-key-v2_outcome_actions .stButton button,
    .st-key-v2_readiness_actions .stButton button {
        min-height: 36px;
        padding: .35rem .55rem;
        border-radius: 999px;
        font-size: .68rem;
    }
    .v2-readiness-question {
        margin: .9rem 0 .45rem;
        color: #4b343e;
        font-size: .78rem;
        font-weight: 720;
        text-align: center;
    }

    /* New conversation mode gate */
    .new-chat-mode-intro {
        width: min(100%, 880px);
        margin: 0 auto;
        padding: clamp(3rem, 9vh, 6.5rem) 0 1.6rem;
        text-align: center;
    }
    .new-chat-mode-intro .mode-kicker {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        color: #8f5367;
        font-size: .67rem;
        font-weight: 820;
        letter-spacing: .1em;
        text-transform: uppercase;
    }
    .new-chat-mode-intro .mode-kicker:before {
        content: "";
        width: 22px;
        height: 1px;
        background: #d69a58;
    }
    .new-chat-mode-intro h1 {
        max-width: 680px;
        margin: .65rem auto .7rem;
        color: #2f2329;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: clamp(2.15rem, 5vw, 3.75rem);
        font-weight: 500;
        line-height: 1.02;
        letter-spacing: -.035em;
    }
    .new-chat-mode-intro p {
        max-width: 570px;
        margin: 0 auto;
        color: #7d6971;
        font-size: .92rem;
        line-height: 1.55;
    }
    .mode-opening-detail { display: inline; }
    .st-key-new_chat_mode_choices {
        width: min(100%, 880px);
        margin: 0 auto;
    }
    .st-key-new_chat_mode_choices div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
        gap: 1rem;
    }
    .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card) {
        position: relative;
        min-height: 238px;
        padding: 1.55rem 1.55rem 1.35rem;
        border: 1px solid #dfd1d2;
        border-radius: 30px 30px 30px 7px;
        background: linear-gradient(145deg, rgba(255,253,249,.98), rgba(249,238,239,.82));
        box-shadow: 0 16px 38px rgba(79,37,52,.07);
        transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    }
    .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card.partner-choice) {
        border-color: #ccdcda;
        border-radius: 30px 30px 7px 30px;
        background: linear-gradient(145deg, rgba(255,253,249,.98), rgba(230,242,239,.86));
    }
    .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card):hover {
        z-index: 1;
        border-color: #bd9ca7;
        box-shadow: 0 20px 44px rgba(79,37,52,.11);
        transform: translateY(-3px);
    }
    .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card.partner-choice):hover {
        border-color: #86aaa4;
    }
    .new-chat-mode-card .mode-number {
        display: grid;
        place-items: center;
        width: 34px;
        height: 34px;
        margin-bottom: 1.15rem;
        border-radius: 50%;
        background: #6c2945;
        color: #fffaf6;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: .87rem;
    }
    .new-chat-mode-card.partner-choice .mode-number { background: #286b63; }
    .new-chat-mode-card h2 {
        margin: 0 0 .4rem;
        color: #32252b;
        font-size: 1.35rem;
        font-weight: 720;
        letter-spacing: -.02em;
    }
    .new-chat-mode-card p {
        min-height: 3.8rem;
        margin: 0;
        color: #78656d;
        font-size: .82rem;
        line-height: 1.5;
    }
    .st-key-new_chat_mode_choices .stButton > button {
        min-height: 44px;
        margin-top: .65rem;
        border-color: #6c2945;
        background: #6c2945;
        color: #fffaf6;
        font-weight: 720;
    }
    .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.partner-choice) .stButton > button {
        border-color: #286b63;
        background: #286b63;
    }
    .new-chat-mode-note {
        margin: 1rem auto 0;
        color: #9a858c;
        font-size: .7rem;
        text-align: center;
    }

    /* Signed-in conversation workspace */
    .block-container:has(.dilse-app-shell-marker) {
        width: 100%;
        max-width: none;
        padding: 0;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) {
        align-items: stretch;
        gap: 0;
        min-height: 100vh;
        background: #fcfaf7;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:first-child {
        flex: 0 0 252px !important;
        width: 252px !important;
        min-width: 252px !important;
        height: 100vh;
        max-height: 100vh;
        padding: 1.15rem .9rem 1rem;
        border: 0;
        border-right: 1px solid #e4dbd8;
        border-radius: 0;
        background: #f5f0ed;
        box-shadow: none;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 0 !important;
        width: 0 !important;
        min-width: 0 !important;
        min-height: 100vh;
        padding: 0 clamp(1.25rem, 3.2vw, 3.4rem) 1.1rem;
        background: #fcfaf7;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child {
        flex: 0 0 330px !important;
        width: 330px !important;
        min-width: 330px !important;
        height: 100vh;
        max-height: 100vh;
        padding: 1.35rem 1.15rem 1.6rem;
        border: 0;
        border-left: 1px solid #e4dbd8;
        border-radius: 0;
        background:
            linear-gradient(rgba(250,246,243,.96), rgba(250,246,243,.96)),
            repeating-linear-gradient(45deg, transparent 0 13px, rgba(108,41,69,.055) 13px 14px);
        box-shadow: none;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker):has(.new-chat-mode-intro) > div[data-testid="stColumn"]:last-child {
        display: none;
    }
    .app-logo {
        width: 132px;
        margin: .15rem .45rem 1.15rem;
    }
    .rail-label {
        margin: 1.15rem .5rem .35rem;
        color: #8c767e;
        font-size: .64rem;
        letter-spacing: .1em;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:first-child .stButton > button {
        justify-content: flex-start;
        min-height: 38px;
        padding: .45rem .65rem;
        border: 0;
        border-radius: 9px;
        background: transparent;
        color: #49363e;
        font-size: .8rem;
        font-weight: 580;
        text-align: left;
        box-shadow: none;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:first-child .stButton > button:hover {
        background: #ebe2df;
        color: #4f1f34;
    }
    .st-key-rail_new_conversation .stButton > button {
        justify-content: center !important;
        min-height: 44px !important;
        border: 1px solid #6c2945 !important;
        background: #6c2945 !important;
        color: #fffaf7 !important;
        font-weight: 700 !important;
        text-align: center !important;
    }
    .rail-profile {
        margin: 1.35rem .45rem .35rem;
        padding-top: .9rem;
        border-top: 1px solid #e0d6d3;
    }
    .rail-profile span { display: block; color: #35282e; font-size: .82rem; font-weight: 750; }
    .rail-profile small { display: block; margin-top: .12rem; color: #8b777e; font-size: .67rem; }
    .chat-surface-header {
        position: sticky;
        top: 0;
        z-index: 24;
        min-height: 66px;
        margin: 0 -1rem 1.2rem;
        padding: .8rem 1rem;
        border-bottom: 1px solid rgba(228,219,216,.9);
        background: rgba(252,250,247,.94);
        backdrop-filter: blur(14px);
    }
    .chat-surface-header strong {
        color: #30242a;
        font-size: .91rem;
        font-weight: 720;
    }
    .chat-surface-header span { color: #917c83; font-size: .69rem; }
    .chat-mode-pill {
        padding: .36rem .62rem;
        background: #f0e4e7;
        color: #6c2945 !important;
        font-size: .64rem !important;
    }
    .chat-empty {
        grid-template-columns: auto minmax(0, 560px);
        gap: 1rem;
        place-content: center;
        min-height: 43vh;
        padding: 2rem 1rem 1.35rem;
        text-align: left;
    }
    .empty-mark-dilse {
        display: grid;
        place-items: center;
        width: 48px;
        height: 48px;
        border-radius: 15px 15px 15px 4px;
        background: #6c2945;
        color: #fff9f5;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: 1.5rem;
        box-shadow: 0 8px 24px rgba(108,41,69,.16);
    }
    .chat-empty .heartline {
        color: #9a4e68;
        font-size: .66rem;
        letter-spacing: .09em;
    }
    .chat-empty .heartline:before,
    .chat-empty .heartline:after { display: none; }
    .chat-empty h1 {
        max-width: 560px;
        margin: .35rem 0 .42rem;
        color: #2d2228;
        font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
        font-size: clamp(1.75rem, 3.1vw, 2.5rem);
        font-weight: 620;
        line-height: 1.12;
        letter-spacing: -.035em;
    }
    .chat-empty p { margin: 0; color: #79676e; font-size: .9rem; line-height: 1.55; }
    .chat-empty small { display: block; margin-top: .8rem; color: #9a6a7c; font-size: .75rem; }
    .partner-empty .empty-mark-dilse { background: #2d6d64; }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"] {
        display: flex;
        align-items: flex-start;
        gap: .65rem;
        width: min(88%, 760px);
        margin: 0 auto .62rem 0;
        padding: 0;
        border: 0;
        background: transparent;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) {
        flex-direction: row-reverse;
        width: fit-content;
        max-width: min(78%, 680px);
        margin-right: 0;
        margin-left: auto;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) > img:first-child {
        flex: 0 0 46px;
        width: 46px;
        height: 46px;
        padding: .22rem;
        border: 1px solid rgba(24,79,74,.22);
        border-radius: 15px 15px 15px 5px;
        background: #fffaf5;
        box-shadow: 0 8px 20px rgba(24,79,74,.12);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) > img:first-child {
        object-fit: contain;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) > [data-testid="stChatMessageAvatarCustom"] {
        flex: 0 0 34px;
        width: 34px;
        height: 34px;
        background: #6c2945;
        color: #fff9f5;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) > [data-testid="stChatMessageAvatarCustom"] svg {
        color: #fff9f5 !important;
        fill: #fff9f5 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) > [data-testid="stChatMessageAvatarCustom"] span,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) > [data-testid="stChatMessageAvatarCustom"] [data-testid="stIconMaterial"] {
        color: #fff9f5 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] {
        padding: .6rem .95rem;
        border: 1px solid #e4dad7;
        border-radius: 6px 18px 18px 18px;
        background: #fffdf9;
        box-shadow: 0 7px 20px rgba(62,39,49,.045);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] {
        padding: .58rem .92rem;
        border-radius: 18px 6px 18px 18px;
        background: #6c2945;
        color: #fffaf6;
        box-shadow: 0 8px 20px rgba(108,41,69,.13);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] p,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] li {
        color: #fffaf6 !important;
    }
    .message-reply-quote {
        margin: 0 0 .52rem;
        padding: .48rem .62rem;
        border-left: 3px solid #d48a4b;
        border-radius: 5px 10px 10px 5px;
        background: rgba(239,228,220,.72);
        color: #5e4850;
    }
    .message-reply-quote span {
        display: block;
        margin-bottom: .12rem;
        color: #98526a;
        font-size: .61rem;
        font-weight: 800;
        letter-spacing: .05em;
        text-transform: uppercase;
    }
    .message-reply-quote p {
        margin: 0 !important;
        color: inherit !important;
        font-size: .73rem;
        line-height: 1.38;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) .message-reply-quote {
        border-left-color: #efb66f;
        background: rgba(255,255,255,.12);
        color: #fff5ee;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) .message-reply-quote span {
        color: #ffd59e;
    }
    div[class*="st-key-user_reply_message_"] .stButton button,
    div[class*="st-key-admin_reply_message_"] .stButton button {
        width: auto;
        min-height: 26px;
        margin-top: .28rem;
        padding: .15rem .48rem;
        border: 0;
        border-radius: 999px;
        background: transparent;
        color: #8b6975;
        box-shadow: none;
        font-size: .68rem;
        font-weight: 750;
    }
    div[class*="st-key-user_reply_message_"] .stButton button:hover,
    div[class*="st-key-admin_reply_message_"] .stButton button:hover {
        background: rgba(184,92,115,.1);
        color: #6c2945;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) div[class*="st-key-user_reply_message_"] .stButton button {
        color: #f4cbd5;
    }
    .st-key-user_reply_composer {
        width: min(100%, 860px);
        margin: .25rem auto .35rem;
        padding: .45rem .55rem .38rem;
        border: 1px solid #dfcdd1;
        border-radius: 14px;
        background: rgba(255,253,249,.96);
        box-shadow: 0 8px 20px rgba(74,38,52,.07);
    }
    .st-key-user_reply_composer .message-reply-quote { margin: 0; }
    .st-key-user_reply_composer .stButton button {
        min-width: 34px;
        min-height: 34px;
        padding: 0;
        border-radius: 50%;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatInput"] {
        position: sticky;
        bottom: 0;
        z-index: 26;
        width: min(100%, 860px);
        margin: 0 auto;
        padding: 1rem 0 .25rem;
        border-top: 0;
        background: linear-gradient(180deg, rgba(252,250,247,0), #fcfaf7 30%);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatInput"] textarea {
        min-height: 54px;
        padding-left: .5rem;
        border: 1px solid #d5c9c7;
        border-radius: 25px;
        background: #fff;
        box-shadow: 0 9px 28px rgba(62,39,49,.08);
    }
    .conversation-panel-head {
        position: relative;
        margin: -.1rem 0 1.1rem;
        padding: 0 0 1rem;
        border-bottom: 1px solid #e2d8d5;
    }
    .conversation-panel-head:after {
        content: "";
        position: absolute;
        right: 0;
        bottom: -1px;
        width: 58px;
        height: 2px;
        background: #d59557;
    }
    .conversation-panel-head span,
    .partner-mode-note span,
    .listener-mode-note span,
    .active-mode-summary span,
    .roleplay-ready span {
        display: block;
        color: #9b4d67;
        font-size: .63rem;
        font-weight: 820;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .conversation-panel-head strong {
        display: block;
        margin-top: .28rem;
        color: #30242a;
        font-size: 1.16rem;
        line-height: 1.25;
    }
    .conversation-panel-head p,
    .partner-mode-note p,
    .listener-mode-note p {
        margin: .4rem 0 0;
        color: #7a686f;
        font-size: .76rem;
        line-height: 1.48;
    }
    .partner-mode-note,
    .listener-mode-note {
        margin: .7rem 0 1rem;
        padding: .85rem 0 .25rem;
        border-top: 1px solid #e5dcd8;
    }
    .partner-mode-note strong,
    .listener-mode-note strong {
        display: block;
        margin-top: .25rem;
        color: #3c2d34;
        font-size: .86rem;
    }
    .active-mode-summary,
    .roleplay-ready {
        margin: .75rem 0 1rem;
        padding: .8rem .85rem;
        border: 1px solid #e0d4d3;
        border-radius: 12px;
        background: rgba(255,255,255,.58);
    }
    .active-mode-summary strong,
    .roleplay-ready strong { display: block; margin-top: .2rem; color: #392a31; font-size: .84rem; }
    .active-mode-summary small,
    .roleplay-ready small { display: block; margin-top: .12rem; color: #8b777e; font-size: .69rem; }
    .character-profile-intro {
        margin: .85rem 0 .6rem;
        padding: .85rem .9rem;
        border-left: 3px solid #d59557;
        border-radius: 0 12px 12px 0;
        background: linear-gradient(115deg, #fff5e9, rgba(255,255,255,.68));
    }
    .character-profile-intro span {
        display: block;
        color: #9b4d67;
        font-size: .61rem;
        font-weight: 820;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .character-profile-intro strong {
        display: block;
        margin-top: .22rem;
        color: #392a31;
        font-size: .9rem;
    }
    .character-profile-intro p {
        margin: .32rem 0 0;
        color: #78636b;
        font-size: .73rem;
        line-height: 1.48;
    }
    .character-profile-status {
        margin: -.25rem 0 .8rem;
        color: #8a747c;
        font-size: .67rem;
        line-height: 1.4;
    }
    .character-profile-status.ready { color: #2d6d64; font-weight: 720; }
    .st-key-character_description_editor,
    .st-key-character_description_editor [data-testid="stTextArea"] {
        display: block !important;
        height: 160px !important;
        min-height: 160px !important;
        overflow: visible !important;
    }
    .st-key-character_description_editor textarea {
        display: block !important;
        min-height: 120px !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    .chat-profile-required {
        width: min(100%, 860px);
        margin: .4rem auto .2rem;
        padding: .65rem .8rem;
        border: 1px solid #e1d3d3;
        border-radius: 12px;
        background: #fff8ef;
        color: #715761;
        font-size: .74rem;
        line-height: 1.45;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child label {
        color: #49383f;
        font-size: .75rem;
        font-weight: 700;
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child [data-baseweb="select"] > div,
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child textarea {
        border-color: #d9cdca;
        border-radius: 10px;
        background: rgba(255,255,255,.75);
    }
    div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child [data-testid="stCaptionContainer"] {
        margin-top: -.35rem;
        color: #907d84;
        font-size: .66rem;
        line-height: 1.35;
    }
    @media (max-width: 900px) {
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) { flex-direction: column; }
        .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] {
            width: min(90%, 680px);
        }
        .st-key-admin_chat_composer {
            position: relative;
            bottom: auto;
            margin-bottom: .75rem;
            border-radius: 15px;
        }
        .admin-composer-label { align-items: flex-start; flex-direction: column; gap: .15rem; }
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:first-child,
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:last-child {
            position: relative;
            top: auto;
            overflow: visible;
            max-height: none;
        }
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:nth-child(2) { order: 1; }
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:last-child { order: 2; }
        div[data-testid="stHorizontalBlock"]:has(.admin-shell-marker) > div[data-testid="stColumn"]:first-child { order: 3; }
        .st-key-admin_mobile_nav {
            position: sticky;
            top: 0;
            z-index: 35;
            display: block;
            margin: -.35rem 0 .8rem;
            padding: .55rem .65rem .25rem;
            border: 1px solid #d5e3df;
            border-radius: 14px;
            background: rgba(247,251,248,.97);
            box-shadow: 0 8px 22px rgba(18,63,59,.07);
            backdrop-filter: blur(12px);
        }
        .admin-kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .app-usage-board { grid-template-columns: 1fr; }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) {
            display: block;
            min-height: 100dvh;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:first-child,
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:last-child {
            display: none;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 100% !important;
            min-height: 100dvh;
            padding: .35rem .8rem 1rem;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker):has(.mobile-settings-open-marker) > div[data-testid="stColumn"]:last-child {
            position: fixed;
            inset: 0;
            z-index: 80;
            display: block;
            overflow-y: auto;
            width: 100% !important;
            min-width: 100% !important;
            height: 100dvh;
            max-height: 100dvh;
            padding: .75rem 1rem 2rem;
            border: 0;
            border-radius: 0;
            background: #faf6f3;
            box-shadow: none;
            overscroll-behavior: contain;
        }
        body:has(.mobile-settings-open-marker) { overflow: hidden; }
        .st-key-mobile_dashboard_nav {
            position: sticky;
            top: 0;
            z-index: 30;
            display: flex;
            flex-wrap: nowrap;
            align-items: center;
            margin: -.35rem 0 .8rem;
            padding: .45rem;
            border: 1px solid #dfd0d3;
            border-radius: 14px;
            background: rgba(251,244,236,.96);
            box-shadow: 0 8px 22px rgba(74,36,50,.07);
            backdrop-filter: blur(12px);
        }
        .st-key-mobile_dashboard_nav .stButton > button {
            min-height: 38px !important;
            width: 100%;
            padding: .3rem .1rem !important;
            font-size: .66rem;
        }
        .st-key-mobile_dashboard_nav .stButton > button p {
            margin: 0;
            font-size: .66rem !important;
            line-height: 1;
            white-space: nowrap;
        }
        .st-key-mobile_dashboard_nav > [data-testid="stElementContainer"] {
            flex: 1 1 0;
            width: auto !important;
            min-width: 0;
        }
        .st-key-mobile_conversation_controls {
            display: flex;
            align-items: center;
            gap: .35rem;
            margin: 0 0 .65rem;
            padding: 0 .1rem .65rem;
            border-bottom: 1px solid #eadfdd;
            background: transparent;
        }
        .st-key-mobile_conversation_controls > [data-testid="stElementContainer"] {
            flex: 0 0 auto;
            width: auto !important;
        }
        .st-key-mobile_conversation_controls > [data-testid="stElementContainer"]:first-child {
            margin-right: .05rem;
        }
        .st-key-mobile_conversation_controls .stButton > button {
            min-height: 32px !important;
            padding: .25rem .58rem !important;
            border-radius: 999px !important;
            font-size: .68rem !important;
        }
        .st-key-mobile_open_conversation_settings {
            margin-left: auto;
        }
        .st-key-mobile_open_conversation_settings .stButton > button {
            border-color: #d8c9cc !important;
            background: #fff !important;
            color: #6c2945 !important;
        }
        .st-key-mobile_close_conversation_settings {
            position: sticky;
            top: 0;
            z-index: 4;
            display: block;
            margin: 0 0 .8rem;
            padding-bottom: .55rem;
            background: #faf6f3;
        }
        .st-key-mobile_close_conversation_settings .stButton > button {
            min-height: 40px !important;
            border-color: #d9cbca !important;
            background: #fff !important;
            color: #5e3a49 !important;
        }
        .chat-surface-header {
            position: relative;
            top: auto;
            min-height: 56px;
            margin: 0 0 .55rem;
            padding: .45rem .15rem .7rem;
        }
        .chat-surface-header > div { flex: 1 1 auto; min-width: 0; }
        .chat-surface-header strong { max-width: 100%; }
    }
    @media (max-width: 700px) {
        .letter-header { min-height: 150px; padding: 1.35rem; }
        .letter-header h1 { font-size: 2.7rem; }
        .block-container { padding: 1rem; }
        .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] {
            width: 96%;
            gap: .35rem;
            padding-right: 4.15rem;
        }
        .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) {
            padding-right: 4.15rem;
        }
        .block-container:has(.admin-shell-marker) [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
            --admin-bubble-pad-x: .7rem;
            --admin-bubble-pad-bottom: .5rem;
            padding: .5rem .7rem;
        }
        .site-masthead { min-height: 72px; padding: .7rem 1rem; }
        .site-logo { width: 150px; }
        .site-nav a { padding: .5rem .55rem; font-size: .75rem; }
        .landing-hero { grid-template-columns: 1fr; min-height: auto; padding-top: 4.2rem; padding-bottom: 5rem; }
        .urdu-section { grid-template-columns: 1fr; gap: 1.5rem; padding: 2.8rem 1.4rem; }
        .urdu-section h2 { font-size: 2.35rem; }
        .hero-art { margin-top: 2rem; padding-left: .7rem; padding-bottom: 4.5rem; }
        .hero-art:before { inset: -1rem 1rem 5rem 0; }
        .hero-portrait { border-width: 5px; box-shadow: 10px 12px 0 #184f4a; }
        .letter-preview { left: -.2rem; width: 94%; transform: rotate(-1deg); }
        .mode-grid, .trust-grid, .steps-grid, .need-grid { grid-template-columns: 1fr; }
        .landing-section { padding: 3.6rem 0; }
        .story-section, .process-section, .trust-section { padding-right: 1.4rem; padding-left: 1.4rem; }
        .story-section .need-grid { grid-template-columns: 1fr; }
        .story-section .landing-card { min-height: 230px; border-radius: 42% 42% 1rem 1rem / 25% 25% 1rem 1rem; }
        .process-section .steps-grid { gap: 0; }
        .process-section .steps-grid:before { top: 1rem; bottom: 1rem; left: 2rem; width: 1px; height: auto; transform-origin: top; }
        .process-section .landing-card { padding: 0 0 2.8rem 5.5rem; }
        .process-section .step-card:before { top: 0; left: 0; }
        .trust-section .landing-card { padding: 1.6rem 0; border-right: 0; border-bottom: 1px solid rgba(87,31,53,.2); }
        .trust-section .landing-card:last-child { border-bottom: 0; }
        .terms-page { padding: 3.5rem 1.4rem 5rem; }
        .terms-item { grid-template-columns: 1fr; gap: .35rem; }
        .admin-command { padding: 1.5rem; }
        .admin-profile { grid-template-columns: 1fr 1fr; }
        .admin-workspace-head { display: block; }
        .admin-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .admin-kpi { min-height: 88px; padding: .85rem; }
        .admin-kpi strong { font-size: 1.65rem; }
        .admin-transcript-head { display: block; }
        .dashboard-page-head { margin-top: 0; }
        .settings-summary { grid-template-columns: 1fr; }
        .prompt-card { min-height: 190px; }
        .chat-mode-pill { display: none; }
        .new-chat-mode-intro {
            padding: 1rem .2rem .7rem;
        }
        .new-chat-mode-intro .mode-kicker { font-size: .58rem; }
        .new-chat-mode-intro .mode-kicker:before { width: 16px; }
        .new-chat-mode-intro h1 {
            max-width: 360px;
            margin: .4rem auto .45rem;
            font-size: 1.95rem;
            line-height: 1.03;
        }
        .new-chat-mode-intro p {
            max-width: 380px;
            font-size: .76rem;
            line-height: 1.38;
        }
        .mode-opening-detail { display: none; }
        .st-key-new_chat_mode_choices div[data-testid="stHorizontalBlock"] {
            flex-direction: column;
            gap: .4rem;
        }
        .st-key-new_chat_mode_choices div[data-testid="stColumn"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card) {
            min-height: 0;
            padding: .7rem .8rem .65rem;
            border-radius: 18px 18px 18px 5px;
        }
        .st-key-new_chat_mode_choices div[data-testid="stColumn"]:has(.new-chat-mode-card.partner-choice) {
            border-radius: 18px 18px 5px 18px;
        }
        .new-chat-mode-card {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            column-gap: .7rem;
            align-items: start;
        }
        .new-chat-mode-card .mode-number {
            grid-row: 1 / span 2;
            width: 28px;
            height: 28px;
            margin: 0;
            font-size: .74rem;
        }
        .new-chat-mode-card h2 {
            margin: .05rem 0 .18rem;
            font-size: 1rem;
        }
        .new-chat-mode-card p {
            min-height: 0;
            font-size: .69rem;
            line-height: 1.35;
        }
        .st-key-new_chat_mode_choices .stButton > button {
            min-height: 36px;
            margin-top: .35rem;
            padding: .3rem .5rem;
            font-size: .72rem;
        }
        .new-chat-mode-note { margin-top: .55rem; font-size: .64rem; }
        .chat-empty {
            grid-template-columns: 1fr;
            min-height: 25vh;
            padding: 1rem .35rem .65rem;
            text-align: center;
        }
        .empty-mark-dilse {
            width: 42px;
            height: 42px;
            margin: 0 auto;
            font-size: 1.25rem;
        }
        .chat-empty h1 {
            margin: .45rem auto .35rem;
            font-size: 1.8rem;
        }
        .chat-empty p { font-size: .82rem; line-height: 1.5; }
        .profile-capture-empty {
            min-height: 0;
            padding: .45rem .25rem .5rem;
        }
        .profile-capture-empty .empty-mark-dilse { display: none; }
        .profile-capture-empty h1 {
            margin-top: .35rem;
            font-size: 1.55rem;
        }
        .profile-capture-empty p {
            font-size: .76rem;
            line-height: 1.42;
        }
        .profile-capture-empty small {
            margin-top: .45rem;
            font-size: .66rem;
            line-height: 1.35;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"] {
            gap: .42rem;
            width: 100%;
            margin-bottom: .65rem;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) {
            max-width: 88%;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) > img:first-child {
            flex-basis: 38px;
            width: 38px;
            height: 38px;
            border-radius: 12px 12px 12px 4px;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) > [data-testid="stChatMessageAvatarCustom"] {
            flex-basis: 28px;
            width: 28px;
            height: 28px;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"],
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) > div[data-testid="stColumn"]:nth-child(2) [data-testid="stChatMessage"]:has(> [data-testid="stChatMessageContent"][aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] {
            padding: .54rem .75rem;
        }
        .st-key-listener_suggestions {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: .35rem;
            margin: .15rem 0 .75rem;
        }
        .st-key-listener_suggestions > [data-testid="stElementContainer"] {
            flex: 0 0 auto;
            width: auto !important;
        }
        .st-key-listener_suggestions .stButton > button {
            min-height: 31px !important;
            padding: .22rem .55rem !important;
            border-color: #d9c8cc !important;
            border-radius: 999px !important;
            background: #fff !important;
            color: #67404f !important;
            font-size: .64rem !important;
            font-weight: 650 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.dilse-app-shell-marker) [data-testid="stChatInput"] {
            padding: .75rem 0 calc(.25rem + env(safe-area-inset-bottom));
        }
    }
    /* Landing page: product-first editorial layout */
    body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-masthead {
        position: sticky;
        top: 0;
        z-index: 50;
        min-height: 76px;
        border-bottom-color: rgba(87,31,53,.16);
        background: rgba(255,249,242,.94);
        backdrop-filter: blur(14px);
    }
    body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-logo {
        width: clamp(164px, 17vw, 205px);
    }
    body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-nav a:last-child {
        padding-right: 1rem;
        padding-left: 1rem;
        border-color: #571f35;
        background: #571f35;
        color: #fff9f2 !important;
    }
    .landing-hero-v2 {
        grid-template-columns: minmax(0, 1.08fr) minmax(360px, .92fr);
        gap: clamp(3rem, 6vw, 6.5rem);
        min-height: min(690px, calc(100svh - 76px));
        padding-top: clamp(3.25rem, 7vh, 5rem);
        padding-bottom: clamp(3.5rem, 7vh, 5.25rem);
    }
    .landing-hero-v2 .hero-copy { position: relative; z-index: 2; max-width: 650px; }
    .landing-hero-v2 h1 {
        max-width: 650px;
        margin-top: .75rem;
        margin-bottom: 1.15rem;
        font-size: clamp(3.35rem, 5.9vw, 5.55rem);
        line-height: .94;
    }
    .landing-hero-v2 .landing-lede {
        max-width: 575px;
        margin-bottom: .85rem;
        font-size: clamp(1.02rem, 1.45vw, 1.18rem);
        line-height: 1.58;
    }
    .landing-hero-v2 .urdu-hero { margin-bottom: 1.35rem; font-size: clamp(1rem, 1.4vw, 1.17rem); }
    .landing-hero-v2 .landing-actions a { min-width: 114px; padding: .82rem 1.15rem; text-align: center; }
    .hero-facts {
        display: flex;
        flex-wrap: wrap;
        gap: .45rem 1.25rem;
        margin-top: 1.15rem;
        color: rgba(255,249,242,.72);
        font-size: .72rem;
        letter-spacing: .035em;
    }
    .hero-facts span { position: relative; padding-left: .85rem; }
    .hero-facts span:before {
        content: "";
        position: absolute;
        top: .48em;
        left: 0;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: #f0b46f;
    }
    .hero-product-preview {
        position: relative;
        z-index: 1;
        width: min(100%, 470px);
        margin-left: auto;
        padding: 0 0 2.75rem 1.75rem;
        animation: portrait-arrive .95s cubic-bezier(.18,.82,.25,1) .34s backwards;
    }
    .portrait-window { position: relative; }
    .portrait-window:before {
        content: "";
        position: absolute;
        inset: -1rem 1rem 2.7rem -1rem;
        border: 1px solid rgba(240,180,111,.68);
        border-radius: 46% 46% 3px 3px;
    }
    .hero-product-preview .hero-portrait {
        width: 100%;
        aspect-ratio: 5 / 5.35;
        border-width: 7px;
        border-radius: 3px;
        box-shadow: 15px 17px 0 #184f4a, 0 28px 65px rgba(0,0,0,.28);
        object-position: center 31%;
    }
    .portrait-caption {
        position: absolute;
        top: 1.4rem;
        right: -1rem;
        width: 142px;
        padding: .7rem .8rem;
        background: #e6a15a;
        color: #351323;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: .78rem;
        line-height: 1.35;
        transform: rotate(2deg);
    }
    .preview-dialogue {
        position: absolute;
        right: 1.3rem;
        bottom: 0;
        left: -1.2rem;
        padding: 1rem;
        border: 1px solid rgba(87,31,53,.15);
        border-radius: 4px;
        background: #fffaf4;
        color: #38252c;
        box-shadow: 8px 13px 34px rgba(34,12,22,.28);
        animation: note-settle .82s cubic-bezier(.16,.86,.3,1) .86s backwards;
    }
    .preview-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: .75rem;
        color: #7b5361;
        font-size: .62rem;
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .preview-message {
        width: fit-content;
        max-width: 86%;
        margin: .45rem 0;
        padding: .58rem .72rem;
        font-size: .76rem;
        line-height: 1.4;
    }
    .preview-user { margin-left: auto; border-radius: 13px 13px 3px 13px; background: #f1dfe3; }
    .preview-dilse { border-left: 2px solid #28756d; background: #edf4f0; }
    .preview-dilse strong { display: block; margin-bottom: .18rem; color: #21645e; font-size: .62rem; letter-spacing: .08em; text-transform: uppercase; }
    .preview-modes { display: grid; grid-template-columns: 1fr 1fr; gap: .4rem; margin-top: .75rem; }
    .preview-modes > span { padding: .48rem .58rem; border: 1px solid #dac6ca; color: #704b58; font-size: .7rem; font-weight: 750; }
    .preview-modes > span.active { border-color: #28756d; background: #28756d; color: #fff; }
    .preview-modes small { display: block; margin-top: .08rem; font-size: .58rem; font-weight: 500; opacity: .78; }
    .landing-language-rail {
        display: flex;
        justify-content: center;
        gap: clamp(1.5rem, 6vw, 5.2rem);
        margin: 0 calc(50% - 50vw);
        padding: 1rem max(1.4rem, calc((100vw - 1120px) / 2));
        border-bottom: 1px solid rgba(255,255,255,.14);
        background: #184f4a;
        color: #f8eee8;
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
    }
    .landing-mode-stage,
    .conversation-spectrum,
    .cultural-context-section,
    .landing-process,
    .landing-trust,
    .final-invitation,
    .landing-footer {
        margin-right: calc(50% - 50vw);
        margin-left: calc(50% - 50vw);
        padding-right: max(2rem, calc((100vw - 1120px) / 2));
        padding-left: max(2rem, calc((100vw - 1120px) / 2));
    }
    .landing-mode-stage {
        padding-top: clamp(4.8rem, 9vw, 7.5rem);
        padding-bottom: clamp(4.8rem, 9vw, 7.5rem);
        background: #fffaf4;
    }
    .mode-stage-intro {
        display: grid;
        grid-template-columns: .72fr 1.28fr;
        gap: 2rem 5rem;
        align-items: end;
    }
    .mode-stage-intro .section-kicker { align-self: start; margin-top: .75rem; color: #88425a; }
    .mode-stage-intro h2,
    .spectrum-intro h2,
    .context-copy h2,
    .process-heading h2,
    .trust-heading h2,
    .final-invitation h2 {
        margin: 0;
        font-size: clamp(2.45rem, 5vw, 4.4rem);
        line-height: 1;
        letter-spacing: -.035em;
    }
    .mode-stage-intro p { grid-column: 2; max-width: 680px; margin: -.7rem 0 0; color: #6c505a; font-size: 1.05rem; line-height: 1.7; }
    .mode-ledger { display: grid; grid-template-columns: 1fr 1fr; margin-top: 4rem; border-top: 1px solid #cdb7bc; border-bottom: 1px solid #cdb7bc; }
    .mode-panel { padding: 2.6rem 3.2rem 2.8rem 0; }
    .mode-panel + .mode-panel { padding-right: 0; padding-left: 3.2rem; border-left: 1px solid #cdb7bc; }
    .mode-number { color: #28756d; font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .mode-panel h3 { margin: 1.4rem 0 .8rem; font-size: clamp(2rem, 3vw, 2.8rem); }
    .mode-panel p { max-width: 500px; margin: 0; color: #674d57; line-height: 1.65; }
    .mode-example { margin-top: 1.8rem; padding: 1rem 1.1rem; border-left: 3px solid #e6a15a; background: #f7e9df; color: #513842; font-family: "Iowan Old Style", Georgia, serif; line-height: 1.5; }
    .mode-example span { display: block; margin-bottom: .2rem; color: #8b596a; font-family: "Avenir Next", Avenir, sans-serif; font-size: .62rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .conversation-spectrum {
        display: grid;
        grid-template-columns: minmax(0, .87fr) minmax(0, 1.13fr);
        gap: clamp(3rem, 8vw, 7rem);
        padding-top: clamp(4.8rem, 9vw, 7rem);
        padding-bottom: clamp(4.8rem, 9vw, 7rem);
        background: #184f4a;
        color: #f9f1ea;
    }
    .conversation-spectrum .section-kicker { color: #f0b46f; }
    .spectrum-intro { position: sticky; top: 120px; align-self: start; }
    .spectrum-intro h2 { max-width: 500px; margin-top: .75rem; color: #fff9f2; }
    .spectrum-intro > p { max-width: 520px; margin: 1.25rem 0 0; color: #d8e5df; line-height: 1.7; }
    .spectrum-intro .spectrum-urdu { color: #f2d4c0; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.08rem; font-style: italic; }
    .topic-ledger { border-top: 1px solid rgba(255,255,255,.28); }
    .topic-ledger article { display: grid; grid-template-columns: .8fr 1.2fr; gap: 2rem; padding: 1.65rem 0; border-bottom: 1px solid rgba(255,255,255,.28); }
    .topic-ledger span { color: #f2c38c; font-family: "Iowan Old Style", Georgia, serif; font-size: 1.25rem; }
    .topic-ledger p { margin: 0; color: #d8e5df; line-height: 1.6; }
    .cultural-context-section {
        display: grid;
        grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr);
        gap: clamp(3rem, 9vw, 8rem);
        align-items: center;
        padding-top: clamp(5rem, 10vw, 8rem);
        padding-bottom: clamp(5rem, 10vw, 8rem);
        background: #f2dfe4;
    }
    .context-quote {
        position: relative;
        max-width: 440px;
        padding: 2.1rem 0 2.1rem 2rem;
        border-left: 5px solid #e6a15a;
        color: #571f35;
        font-family: "Iowan Old Style", Georgia, serif;
        font-size: clamp(1.9rem, 3.3vw, 3rem);
        font-style: italic;
        line-height: 1.16;
    }
    .context-copy .section-kicker { margin-bottom: .7rem; color: #88425a; }
    .context-copy h2 { color: #571f35; }
    .context-copy p { max-width: 630px; margin: 1.35rem 0 0; color: #634a54; font-size: 1.04rem; line-height: 1.72; }
    .landing-process { padding-top: clamp(4.8rem, 9vw, 7rem); padding-bottom: clamp(4.8rem, 9vw, 7rem); background: #351323; color: #fff9f2; }
    .landing-process .section-kicker { color: #f0b46f; }
    .process-heading { display: grid; grid-template-columns: .7fr 1.3fr; gap: 4rem; align-items: start; }
    .process-heading h2 { max-width: 650px; color: #fff9f2; }
    .process-path { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 4.5rem; border-top: 1px solid rgba(240,180,111,.55); }
    .process-path article { position: relative; padding: 2.2rem 2.5rem 0 0; }
    .process-path article + article { padding-left: 2.5rem; border-left: 1px solid rgba(240,180,111,.35); }
    .process-path span { color: #f0b46f; font-size: .72rem; font-weight: 800; letter-spacing: .12em; }
    .process-path h3 { margin: 1.35rem 0 .55rem; color: #fff9f2; font-size: 1.35rem; }
    .process-path p { margin: 0; color: #d7c4cc; line-height: 1.6; }
    .landing-trust { display: grid; grid-template-columns: .9fr 1.1fr; gap: clamp(3rem, 8vw, 7rem); padding-top: clamp(4.5rem, 8vw, 6.5rem); padding-bottom: clamp(4.5rem, 8vw, 6.5rem); background: #fffaf4; }
    .trust-heading .section-kicker { color: #88425a; }
    .trust-heading h2 { max-width: 570px; margin-top: .7rem; color: #571f35; }
    .trust-heading p { max-width: 570px; margin: 1.2rem 0 0; color: #674d57; line-height: 1.65; }
    .trust-ledger { border-top: 1px solid #d4bec3; }
    .trust-ledger article { display: grid; grid-template-columns: .7fr 1.3fr; gap: 1.5rem; padding: 1.4rem 0; border-bottom: 1px solid #d4bec3; }
    .trust-ledger strong { color: #571f35; }
    .trust-ledger span { color: #705762; line-height: 1.55; }
    .final-invitation {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 3rem;
        padding-top: clamp(3.8rem, 7vw, 5.4rem);
        padding-bottom: clamp(3.8rem, 7vw, 5.4rem);
        background: #e6a15a;
        color: #351323;
    }
    .final-invitation .section-kicker { color: #6d2943; }
    .final-invitation h2 { margin-top: .5rem; color: #351323; }
    .final-invitation p { max-width: 650px; margin: .75rem 0 0; color: #56322f; line-height: 1.6; }
    .final-invitation > a {
        flex: 0 0 auto;
        padding: .95rem 1.25rem;
        border: 1px solid #351323;
        background: #351323;
        color: #fff9f2 !important;
        font-weight: 800;
        text-decoration: none;
        transition: transform .2s ease, box-shadow .2s ease;
    }
    .final-invitation > a:hover { transform: translateY(-2px); box-shadow: 6px 7px 0 rgba(87,31,53,.24); }
    .landing-footer { display: grid; grid-template-columns: 1fr auto auto; gap: 2rem; align-items: center; padding-top: 1.6rem; padding-bottom: 1.6rem; border-top: 1px solid #d9c5c9; background: #fff9f2; }
    .landing-footer img { width: 120px; height: auto; }
    .landing-footer p { margin: 0; color: #745d66; font-size: .75rem; }
    .landing-footer a { color: #571f35 !important; font-size: .75rem; font-weight: 750; }
    .auth-stage { margin-top: 0; }
    .auth-stage h2 { color: #571f35; }

    @media (max-width: 900px) {
        .landing-hero-v2 { grid-template-columns: 1fr; min-height: auto; gap: 3.4rem; }
        .landing-hero-v2 .hero-copy { max-width: 720px; }
        .hero-product-preview { width: min(100%, 560px); margin-right: auto; }
        .mode-stage-intro,
        .conversation-spectrum,
        .cultural-context-section,
        .process-heading,
        .landing-trust { grid-template-columns: 1fr; }
        .mode-stage-intro p { grid-column: 1; margin-top: 0; }
        .spectrum-intro { position: relative; top: auto; }
        .conversation-spectrum,
        .cultural-context-section,
        .landing-trust { gap: 3rem; }
        .final-invitation { align-items: flex-start; flex-direction: column; }
    }
    @media (max-width: 700px) {
        body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-masthead { min-height: 68px; }
        body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-logo { width: 132px; }
        body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-nav { gap: .15rem; }
        body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-nav a { padding: .45rem .48rem; font-size: .69rem; }
        body:has(.landing-marketing:not(.landing-marketing-hidden)) .site-nav a:last-child { padding-right: .65rem; padding-left: .65rem; }
        .landing-hero-v2 { gap: 2.75rem; padding: 2.9rem 1.35rem 4rem; }
        .landing-hero-v2 h1 { max-width: 360px; margin-top: .6rem; font-size: clamp(3rem, 15vw, 3.8rem); line-height: .92; }
        .landing-hero-v2 .landing-lede { margin-bottom: .7rem; font-size: .98rem; line-height: 1.5; }
        .landing-hero-v2 .urdu-hero { margin-bottom: 1.15rem; font-size: 1rem; }
        .landing-hero-v2 .landing-actions { gap: .55rem; }
        .landing-hero-v2 .landing-actions a { flex: 1 1 auto; padding: .72rem .8rem; font-size: .82rem; }
        .hero-facts { gap: .35rem .8rem; margin-top: .95rem; font-size: .64rem; }
        .hero-product-preview { margin-top: .25rem; padding: 0 .25rem 0; }
        .portrait-window:before { inset: -.7rem .7rem 2.2rem -.7rem; }
        .hero-product-preview .hero-portrait { border-width: 5px; box-shadow: 9px 11px 0 #184f4a; }
        .portrait-caption { top: 1rem; right: -.4rem; width: 120px; padding: .55rem .62rem; font-size: .66rem; }
        .preview-dialogue { position: relative; right: auto; bottom: auto; left: auto; width: calc(100% - 1.2rem); margin: -3rem auto 0; padding: .82rem; }
        .preview-heading { font-size: .55rem; }
        .preview-message { max-width: 91%; font-size: .7rem; }
        .preview-modes > span { padding: .42rem .48rem; font-size: .64rem; }
        .landing-language-rail { justify-content: flex-start; gap: 1.4rem; overflow-x: auto; padding: .85rem 1.35rem; font-size: .62rem; scrollbar-width: none; }
        .landing-language-rail::-webkit-scrollbar { display: none; }
        .landing-mode-stage,
        .conversation-spectrum,
        .cultural-context-section,
        .landing-process,
        .landing-trust,
        .final-invitation,
        .landing-footer { padding-right: 1.35rem; padding-left: 1.35rem; }
        .landing-mode-stage,
        .conversation-spectrum,
        .cultural-context-section,
        .landing-process,
        .landing-trust { padding-top: 4.25rem; padding-bottom: 4.25rem; }
        .mode-stage-intro { gap: .6rem; }
        .mode-stage-intro h2,
        .spectrum-intro h2,
        .context-copy h2,
        .process-heading h2,
        .trust-heading h2,
        .final-invitation h2 { font-size: 2.55rem; }
        .mode-stage-intro .section-kicker { margin-top: 0; }
        .mode-stage-intro p { font-size: .95rem; line-height: 1.6; }
        .mode-ledger { grid-template-columns: 1fr; margin-top: 2.5rem; }
        .mode-panel { padding: 2rem 0 2.2rem; }
        .mode-panel + .mode-panel { padding: 2.2rem 0; border-top: 1px solid #cdb7bc; border-left: 0; }
        .mode-panel h3 { margin-top: 1rem; font-size: 2rem; }
        .mode-example { margin-top: 1.3rem; font-size: .9rem; }
        .conversation-spectrum { gap: 2.5rem; }
        .topic-ledger article { grid-template-columns: 1fr; gap: .45rem; padding: 1.3rem 0; }
        .topic-ledger span { font-size: 1.18rem; }
        .topic-ledger p { font-size: .9rem; }
        .cultural-context-section { gap: 2.5rem; }
        .context-quote { padding: 1.4rem 0 1.4rem 1.4rem; font-size: 2rem; }
        .context-copy p { font-size: .95rem; }
        .process-heading { gap: .6rem; }
        .process-path { grid-template-columns: 1fr; margin-top: 2.7rem; }
        .process-path article { padding: 1.6rem 0 1.8rem 3.3rem; border-bottom: 1px solid rgba(240,180,111,.28); }
        .process-path article + article { padding-left: 3.3rem; border-left: 0; }
        .process-path span { position: absolute; top: 1.75rem; left: 0; }
        .process-path h3 { margin: 0 0 .35rem; }
        .process-path p { font-size: .9rem; }
        .landing-trust { gap: 2.4rem; }
        .trust-ledger article { grid-template-columns: 1fr; gap: .35rem; }
        .trust-ledger span { font-size: .9rem; }
        .final-invitation { gap: 1.8rem; padding-top: 3.8rem; padding-bottom: 3.8rem; }
        .final-invitation > a { width: 100%; text-align: center; }
        .landing-footer { grid-template-columns: 1fr; gap: .65rem; align-items: start; }
        .landing-footer img { width: 105px; }
        .auth-stage { border-radius: 0; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: .01ms !important;
            animation-delay: 0ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: .01ms !important;
            scroll-behavior: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "auth_token": None,
        "user": None,
        "admin_key": None,
        "admin_authenticated": False,
        "admin_page": "Overview",
        "admin_selected_user_id": None,
        "admin_selected_session_id": None,
        "admin_navigation_restored": False,
        "admin_pending_intervention": None,
        "admin_pending_message_delete": None,
        "admin_reply_to": None,
        "admin_pending_roman_urdu_review": None,
        "admin_composer_nonces": {},
        "admin_composer_prefill": {},
        "admin_composer_retained_images": {},
        "auth_temporarily_unavailable": False,
        "page": "Talk",
        "session_id": uuid.uuid4().hex,
        "messages": [],
        "message_attachment_cache": {},
        "user_reply_to": None,
        "last_feedback": None,
        "last_message_id": 0,
        "pending_prompt": None,
        "mode": "The Listener",
        "conversation_mode": "The Listener",
        "conversation_mode_confirmed": False,
        "roleplay_intensity": "Explicit",
        "roleplay_difficulty": "Realistic",
        "character_description": "",
        "character_description_editor": "",
        "partner_profile_editor_sync": False,
        "carried_history": [],
        "transition_label": None,
        "conversation_checkpoint": None,
        "typing_capture_event_ids": {},
        "phone_alert_event_id": None,
        "opened_push_session": None,
        "confirmed_read_receipts": {},
        "voice_recording_active": False,
        "voice_recording_pending_refresh": False,
        "voice_note_uploads": {},
        "resumed_scenario_slug": None,
        "resumed_persona_slug": None,
        "pending_delete_session_id": None,
        "mobile_conversation_settings_open": False,
        "scroll_dashboard_top": False,
        "scroll_request_id": 0,
        "v2_partner_persona_slug": None,
        "v2_partner_persona_name": None,
        "v2_scenario_slug": "practice_opening_up",
        "v2_readiness_saved": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


def uses_conversation_experience_v2() -> bool:
    user = st.session_state.get("user") or {}
    return int(user.get("experience_version") or 1) >= 2


@st.cache_resource
def browser_auth_sessions() -> dict[str, tuple[str, float]]:
    """Keep API tokens server-side while a browser moves between Streamlit sessions."""
    return {}


def browser_identity() -> str | None:
    try:
        value = st.context.cookies.get(BROWSER_COOKIE_NAME)
    except (AttributeError, KeyError, RuntimeError):
        return None
    return str(value) if value else None


def browser_session_key() -> str | None:
    """Hash the browser's DilSe identifier before using it as a server-side key."""
    identity = browser_identity()
    if not identity:
        return None
    return hashlib.sha256(f"dilse-browser:{identity}".encode("utf-8")).hexdigest()


def register_browser_identity(identity: str, token: str) -> None:
    try:
        requests.post(
            f"{BACKEND_URL}/auth/browser-session",
            json={"browser_id": identity},
            headers={"X-User-Token": token},
            timeout=10,
        )
    except requests.RequestException:
        pass


def ensure_browser_identity() -> None:
    """Create a stable, non-token browser identifier before showing account forms."""
    if os.getenv("DILSE_SKIP_BROWSER_ID") == "1":
        return
    if browser_identity():
        return
    identity = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"
    if st.session_state.auth_token:
        key = hashlib.sha256(f"dilse-browser:{identity}".encode("utf-8")).hexdigest()
        browser_auth_sessions()[key] = (
            st.session_state.auth_token,
            time.time() + BROWSER_SESSION_SECONDS,
        )
        register_browser_identity(identity, st.session_state.auth_token)
    secure = "; Secure" if str(st.context.url).startswith("https://") else ""
    cookie = (
        f"{BROWSER_COOKIE_NAME}={identity}; Max-Age={BROWSER_SESSION_SECONDS}; "
        f"Path=/; SameSite=Strict{secure}"
    )
    components.html(
        f"""<script>
        window.parent.document.cookie = {json.dumps(cookie)};
        window.setTimeout(() => window.parent.location.reload(), 80);
        </script>""",
        height=0,
        width=0,
    )
    st.caption("Preparing your private DilSe space…")
    st.stop()


def remember_browser_login(token: str) -> None:
    key = browser_session_key()
    if key:
        browser_auth_sessions()[key] = (token, time.time() + BROWSER_SESSION_SECONDS)
    identity = browser_identity()
    if identity:
        register_browser_identity(identity, token)


def restore_browser_login() -> str | None:
    key = browser_session_key()
    if not key:
        return None
    entry = browser_auth_sessions().get(key)
    if entry:
        token, expires_at = entry
        if expires_at > time.time():
            return token
        browser_auth_sessions().pop(key, None)
    identity = browser_identity()
    if not identity:
        return None
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/browser-session/restore",
            headers={"X-Browser-Session": identity},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    token = str(response.json()["token"])
    browser_auth_sessions()[key] = (token, time.time() + BROWSER_SESSION_SECONDS)
    return token


def forget_browser_login() -> None:
    key = browser_session_key()
    if key:
        browser_auth_sessions().pop(key, None)
    identity = browser_identity()
    if identity:
        try:
            requests.delete(
                f"{BACKEND_URL}/auth/browser-session",
                headers={"X-Browser-Session": identity},
                timeout=10,
            )
        except requests.RequestException:
            pass


def remember_admin_browser_login(admin_key: str) -> bool:
    identity = browser_identity()
    if not identity:
        return False
    try:
        response = requests.post(
            f"{BACKEND_URL}/admin/browser-session",
            json={"browser_id": identity},
            headers={"X-Admin-Key": admin_key},
            timeout=10,
        )
    except requests.RequestException:
        return False
    if response.status_code != 204:
        return False
    st.session_state.admin_key = admin_key
    st.session_state.admin_authenticated = True
    return True


def restore_admin_browser_login() -> bool:
    if st.session_state.admin_key or st.session_state.admin_authenticated:
        return True
    identity = browser_identity()
    if not identity:
        return False
    try:
        response = requests.post(
            f"{BACKEND_URL}/admin/browser-session/restore",
            headers={"X-Admin-Browser-Session": identity},
            timeout=10,
        )
    except requests.RequestException:
        return False
    if response.status_code != 200:
        return False
    st.session_state.admin_authenticated = bool(response.json().get("authenticated"))
    return st.session_state.admin_authenticated


def forget_admin_browser_login() -> None:
    identity = browser_identity()
    if identity:
        try:
            requests.delete(
                f"{BACKEND_URL}/admin/browser-session",
                headers={"X-Admin-Browser-Session": identity},
                timeout=10,
            )
        except requests.RequestException:
            pass
    st.session_state.admin_key = None
    st.session_state.admin_authenticated = False
    st.session_state.admin_pending_intervention = None


def visitor_request_ip() -> str | None:
    """Read Railway's trusted edge header without using a browser-supplied query value."""
    try:
        value = st.context.headers.get("X-Real-IP")
    except (AttributeError, KeyError, RuntimeError):
        return None
    return str(value).strip() if value else None


@st.fragment(run_every="15s")
def track_visitor_presence(page: str) -> None:
    identity = browser_identity()
    if not identity or not VISITOR_TRACKING_SECRET:
        return
    headers = {"X-Visitor-Tracking-Key": VISITOR_TRACKING_SECRET}
    if st.session_state.auth_token:
        headers["X-User-Token"] = st.session_state.auth_token
    try:
        requests.post(
            f"{BACKEND_URL}/visitor/heartbeat",
            json={
                "browser_id": identity,
                "ip_address": visitor_request_ip(),
                "page": page,
            },
            headers=headers,
            timeout=5,
        )
    except requests.RequestException:
        pass


@st.cache_data
def image_data_uri(path: str, modified_at: int) -> str:
    del modified_at
    image_path = Path(path)
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    mime_types = {".webp": "image/webp", ".svg": "image/svg+xml", ".png": "image/png"}
    mime_type = mime_types.get(image_path.suffix.lower(), "application/octet-stream")
    return f"data:{mime_type};base64,{encoded}"


def request_api(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    auth: bool = False,
    admin: bool = False,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> requests.Response:
    headers: dict[str, str] = {}
    if auth and st.session_state.auth_token:
        headers["X-User-Token"] = st.session_state.auth_token
    if admin:
        if st.session_state.admin_key:
            headers["X-Admin-Key"] = st.session_state.admin_key
        elif st.session_state.admin_authenticated and browser_identity():
            headers["X-Admin-Browser-Session"] = str(browser_identity())
    return requests.request(
        method,
        f"{BACKEND_URL}{path}",
        json=payload,
        headers=headers,
        timeout=timeout,
    )


def error_detail(response: requests.Response) -> str:
    try:
        return str(response.json().get("detail", "The request failed."))
    except (ValueError, AttributeError):
        return "The request failed."


def brand_header(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""<section class="letter-header">
        <div class="eyebrow">{kicker}</div>
        <h1>{title}</h1>
        <p>{body}</p>
        </section>""",
        unsafe_allow_html=True,
    )


def dashboard_header(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""<header class="dashboard-page-head">
        <div class="eyebrow">{html.escape(kicker)}</div>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(body)}</p>
        </header>""",
        unsafe_allow_html=True,
    )


def section_header(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""<div class="page-section-head">
        <div class="eyebrow">{html.escape(kicker)}</div>
        <h2>{html.escape(title)}</h2>
        <p>{html.escape(body)}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def dashboard_empty(title: str, body: str, mark: str = "♥") -> None:
    st.markdown(
        f"""<div class="dashboard-empty">
        <span class="empty-mark">{html.escape(mark)}</span>
        <h3>{html.escape(title)}</h3>
        <p>{html.escape(body)}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def format_session_activity(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Activity time unavailable"
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        moment = moment.astimezone(timezone.utc)
        return moment.strftime("%b %-d, %Y · %H:%M UTC")
    except (TypeError, ValueError):
        return raw.replace("T", " ")[:16]


def reset_local_conversation() -> None:
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []
    st.session_state.user_reply_to = None
    st.session_state.pending_prompt = None
    st.session_state.mode = "The Listener"
    st.session_state.conversation_mode = "The Listener"
    st.session_state.conversation_mode_confirmed = False
    st.session_state.last_feedback = None
    st.session_state.last_message_id = 0
    st.session_state.roleplay_intensity = "Explicit"
    st.session_state.roleplay_difficulty = "Realistic"
    st.session_state.character_description = ""
    st.session_state.character_description_editor = ""
    st.session_state.partner_profile_editor_sync = False
    st.session_state.carried_history = []
    st.session_state.transition_label = None
    st.session_state.conversation_checkpoint = None
    st.session_state.confirmed_read_receipts = {}
    st.session_state.voice_recording_active = False
    st.session_state.voice_recording_pending_refresh = False
    st.session_state.voice_note_uploads = {}
    st.session_state.resumed_scenario_slug = None
    st.session_state.resumed_persona_slug = None
    st.session_state.pending_delete_session_id = None
    st.session_state.mobile_conversation_settings_open = False
    st.session_state.v2_partner_persona_slug = None
    st.session_state.v2_partner_persona_name = None
    st.session_state.v2_scenario_slug = "practice_opening_up"
    st.session_state.pop("roleplay_persona_name", None)
    st.session_state.pop("roleplay_scenario_name", None)
    st.session_state.page = "Talk"
    st.session_state.main_navigation = "Talk"
    st.session_state.scroll_dashboard_top = True
    st.session_state.scroll_request_id += 1


def delete_current_conversation() -> None:
    try:
        response = request_api("DELETE", f"/sessions/{st.session_state.session_id}", auth=True, timeout=10)
        response.raise_for_status()
        reset_local_conversation()
        st.toast("Conversation deleted")
    except requests.RequestException:
        st.error("The server could not delete this conversation.")


def begin_with_intent(mode_label: str, starter: str | None = None) -> None:
    reset_local_conversation()
    st.session_state.mode = mode_label
    st.session_state.conversation_mode = mode_label
    st.session_state.conversation_mode_confirmed = True
    st.session_state.transition_label = "Choose the details, then write the first line." if mode_label == "The Partner" else None
    st.session_state.pending_prompt = starter


def switch_conversation_mode(target_mode: str) -> None:
    carried = [
        {"role": item["role"], "content": item["content"]}
        for item in st.session_state.messages[-20:]
        if item.get("role") in {"user", "assistant"} and not item.get("error") and not item.get("notice")
    ]
    previous_mode = st.session_state.mode
    reset_local_conversation()
    st.session_state.carried_history = carried
    st.session_state.mode = target_mode
    st.session_state.conversation_mode = target_mode
    st.session_state.conversation_mode_confirmed = True
    st.session_state.transition_label = f"Continuing from {previous_mode} in a new {target_mode} conversation."


def load_saved_conversation(session: dict[str, Any]) -> None:
    try:
        response = request_api(
            "GET", f"/sessions/{session['session_id']}/messages", auth=True, timeout=15
        )
        if response.status_code != 200:
            st.error(error_detail(response))
            return
        stored_messages = response.json()
    except requests.RequestException:
        st.error("DilSe could not load this conversation.")
        return
    st.session_state.session_id = session["session_id"]
    st.session_state.messages = [
        {
            "role": item["role"],
            "content": item["content"],
            "source": item.get("source"),
            "message_id": item.get("id"),
            "reply_to_message_id": item.get("reply_to_message_id"),
            "reply_to_role": item.get("reply_to_role"),
            "reply_to_content": item.get("reply_to_content"),
            "reply_to_source": item.get("reply_to_source"),
            "attachment_id": item.get("attachment_id"),
            "attachment_filename": item.get("attachment_filename"),
            "attachment_mime_type": item.get("attachment_mime_type"),
            "attachment_size_bytes": item.get("attachment_size_bytes"),
            "voice_note_id": item.get("voice_note_id"),
            "voice_note_filename": item.get("voice_note_filename"),
            "voice_note_mime_type": item.get("voice_note_mime_type"),
            "voice_note_size_bytes": item.get("voice_note_size_bytes"),
            "voice_note_duration_seconds": item.get("voice_note_duration_seconds"),
        }
        for item in stored_messages
    ]
    st.session_state.user_reply_to = None
    st.session_state.last_message_id = max((int(item["id"]) for item in stored_messages), default=0)
    mode_label = "The Partner" if session.get("mode") == "partner" else "The Listener"
    st.session_state.mode = mode_label
    st.session_state.conversation_mode = mode_label
    st.session_state.conversation_mode_confirmed = True
    st.session_state.roleplay_intensity = str(session.get("roleplay_intensity") or "explicit").title()
    st.session_state.roleplay_difficulty = str(session.get("roleplay_difficulty") or "realistic").title()
    st.session_state.character_description = session.get("character_description") or ""
    st.session_state.partner_profile_editor_sync = True
    st.session_state.resumed_scenario_slug = session.get("scenario")
    st.session_state.resumed_persona_slug = session.get("character")
    st.session_state.v2_scenario_slug = str(
        session.get("scenario") or "practice_opening_up"
    )
    st.session_state.v2_partner_persona_slug = session.get("character")
    st.session_state.v2_partner_persona_name = None
    st.session_state.pop("roleplay_persona_name", None)
    st.session_state.pop("roleplay_scenario_name", None)
    st.session_state.mobile_conversation_settings_open = False
    st.session_state.carried_history = []
    st.session_state.transition_label = None
    st.session_state.conversation_checkpoint = None
    st.session_state.page = "Talk"
    st.session_state.main_navigation = "Talk"
    st.session_state.scroll_dashboard_top = True
    st.session_state.scroll_request_id += 1


def open_requested_push_conversation() -> None:
    requested_session = str(st.query_params.get("open_session") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", requested_session):
        return
    if st.session_state.opened_push_session == requested_session:
        return
    try:
        response = request_api("GET", "/sessions", auth=True, timeout=10)
    except requests.RequestException:
        return
    if response.status_code != 200:
        return
    session = next(
        (
            item
            for item in response.json()
            if str(item.get("session_id") or "") == requested_session
        ),
        None,
    )
    if not session:
        return
    load_saved_conversation(session)
    st.session_state.opened_push_session = requested_session


def sign_out() -> None:
    try:
        request_api("POST", "/auth/logout", auth=True, timeout=10)
    except requests.RequestException:
        pass
    forget_browser_login()
    st.session_state.auth_token = None
    st.session_state.user = None
    reset_local_conversation()


def load_user() -> bool:
    if not st.session_state.auth_token:
        st.session_state.auth_token = restore_browser_login()
    if not st.session_state.auth_token:
        return False
    st.session_state.auth_temporarily_unavailable = False
    try:
        response = request_api("GET", "/auth/me", auth=True, timeout=10)
        if response.status_code == 200:
            st.session_state.user = response.json()
            return True
    except requests.RequestException:
        st.session_state.auth_temporarily_unavailable = True
        return bool(st.session_state.user)
    forget_browser_login()
    st.session_state.auth_token = None
    st.session_state.user = None
    return False


def render_terms() -> None:
    logo_uri = image_data_uri(str(LOGO_PATH), LOGO_PATH.stat().st_mtime_ns)
    st.markdown(
        f"""
        <header class="site-masthead">
            <a href="?" target="_self" aria-label="DilSe home"><img class="site-logo" src="{logo_uri}" alt="DilSe, from the heart"></a>
            <nav class="site-nav" aria-label="Terms navigation">
                <a href="?" target="_self">Back to DilSe</a>
                <a href="?auth=create" target="_self">Create account</a>
            </nav>
        </header>
        <main class="terms-page">
            <header class="terms-hero">
                <div class="section-kicker">MVP TERMS · EFFECTIVE 10 AUGUST 2026</div>
                <h1>Terms and Conditions</h1>
                <p>These terms govern your use of DilSe. By creating an account, you confirm that you are at least 18, understand that DilSe uses artificial intelligence, and agree to the account and data processing described below.</p>
                <div class="mandatory-review-note"><strong>What you are agreeing to</strong><br>Your conversations, AI responses, roleplay settings, and feedback remain exclusively on your device with military-grade end-to-end encryption. No data ever leaves your device, is stored on our servers, or is accessible to anyone - including us. You have complete control with options to clear conversations or permanently delete your session data from your device at any time.</div>
            </header><div class="terms-list">
                <section class="terms-item"><div class="terms-number">01</div><div><h2>Eligibility and acceptance</h2><p>You must be at least 18 years old and legally able to accept these terms. The sign-up checkbox records your agreement to this page, including the required processing needed to provide DilSe. If you do not agree, do not create an account or use the service.</p></div></section>
                <section class="terms-item"><div class="terms-number">02</div><div><h2>What DilSe provides</h2><p>DilSe offers AI-generated relationship reflection, conversation practice, exercises, and roleplay for adults. It is not a licensed therapist, doctor, lawyer, crisis line, or emergency service. Its responses are educational and supportive, not professional diagnosis or treatment.</p></div></section>
                <section class="terms-item"><div class="terms-number">03</div><div><h2>AI-generated responses</h2><p>Your messages are processed locally on your device using our encrypted AI models. No conversation content is transmitted to external servers. Listener conversations use locally-processed Groq and Partner conversations use locally-processed Venice. AI responses can be inaccurate, incomplete, or inappropriate for your circumstances. Review suggestions carefully and do not rely on DilSe for urgent, medical, legal, financial, or safety-critical decisions.</p></div></section>
                <section class="terms-item"><div class="terms-number">04</div><div><h2>Your account</h2><p>Provide a valid email address, use a secure password, and keep your sign-in details private. Your account details are encrypted and stored only on your device. You are responsible for activity through your account. Tell the service operator if you believe someone else has gained access.</p></div></section>
                <section class="terms-item"><div class="terms-number">05</div><div><h2>Conversation storage and privacy</h2><p>DilSe processes account details, text messages, optional voice notes, roleplay settings, feedback, and technical usage records exclusively on your device with end-to-end encryption. No data ever leaves your browser or app, ensuring complete privacy for sensitive discussions about relationships, sexuality, family, health, or finances.</p><p>Conversations are stored locally on your device for the retention period you select (7 to 365 days). Voice notes are optional and are stored only on your device when recorded and sent. They follow the conversation's retention period and are deleted from your device with the message, conversation, or account.</p><p>DilSe records minimal technical data on your device only for service monitoring. No IP addresses or identifying information are stored or transmitted. All technical records are automatically deleted from your device after 30 days.</p><p>You can permanently delete an individual conversation or your account and all associated data from your device at any time.</p><p>Given the highly personal nature of relationship discussions, our end-to-end encryption ensures that even we cannot access your conversations. Your data never leaves your device, providing absolute privacy and confidentiality.</p></div></section>
                <section class="terms-item"><div class="terms-number">06</div><div><h2>Required account processing</h2><p>All account processing occurs exclusively on your device with end-to-end encryption. DilSe does not store, process, or transmit any conversation data to external servers. Conversation storage cannot be disabled while your account is active, but all data remains on your device. You can change the retention period, delete individual conversations, or permanently delete your account from your device at any time.</p></div></section>
                <section class="terms-item"><div class="terms-number">07</div><div><h2>Safety and urgent situations</h2><p>DilSe cannot monitor your safety or contact emergency services for you. If you or another person may be in immediate danger, contact local emergency services or a trusted person who can help. Do not use roleplay to test whether abuse, coercion, or threats are acceptable.</p></div></section>
                <section class="terms-item"><div class="terms-number">08</div><div><h2>Acceptable use</h2><p>Do not use DilSe to create sexual content involving minors, facilitate abuse or exploitation, threaten or harass another person, impersonate someone, break the law, extract confidential system information, disrupt the service, or attempt unauthorized access to accounts or data.</p></div></section>
                <section class="terms-item"><div class="terms-number">09</div><div><h2>Your content</h2><p>You retain all rights to your content. Your content is never transmitted to our servers or any third parties. It remains exclusively on your device with end-to-end encryption, giving you complete control over your personal information.</p></div></section>
                <section class="terms-item"><div class="terms-number">10</div><div><h2>Availability and changes</h2><p>The application may be interrupted, changed, or withdrawn. Features, usage limits, and AI models may change. No uninterrupted availability, preservation of data, or continued access to a specific model is guaranteed. All changes are made with your privacy in mind, maintaining our commitment that no data ever leaves your device.</p></div></section>
                <section class="terms-item"><div class="terms-number">11</div><div><h2>Disclaimers and liability</h2><p>To the extent permitted by applicable law, DilSe is provided without guarantees about accuracy, availability, fitness for a particular purpose, or outcomes from following an AI response. A jurisdiction-specific limitation of liability must be added after the operating entity and launch markets are confirmed. Nothing in these terms limits rights that cannot legally be waived.</p></div></section>
                <section class="terms-item"><div class="terms-number">12</div><div><h2>Ending access and changing these terms</h2><p>You may stop using DilSe and delete your account and all data from your device. Access may be suspended for security risks, prohibited use, or material breach of these terms. Material changes require renewed acceptance before you continue using account features.</p></div></section>
                <section class="terms-item"><div class="terms-number">13</div><div><h2>Operator, contact, and governing law</h2><p>The legal name and address of the service operator, a privacy contact, the governing law, and the dispute forum have not yet been supplied. These details must be completed and reviewed by counsel for each intended launch market before DilSe is offered publicly.</p></div></section>
            </div>
            <div class="terms-actions"><a href="?auth=create" target="_self">Create an account</a><a href="?" target="_self">Return to DilSe</a></div>
        </main>
        """,
        unsafe_allow_html=True,
    )


def render_terms_update() -> None:
    logo_uri = image_data_uri(str(LOGO_PATH), LOGO_PATH.stat().st_mtime_ns)
    st.markdown(
        f"""
        <header class="site-masthead">
            <img class="site-logo" src="{logo_uri}" alt="DilSe, from the heart">
            <nav class="site-nav" aria-label="Terms update navigation">
                <a href="?page=terms" target="_self">Read the Terms</a>
            </nav>
        </header>
        <section class="terms-update-stage">
            <span>Account update required</span>
            <h1>Please review how conversations are handled.</h1>
            <p>DilSe requires conversation storage while your account is active. You need to accept the updated Terms before starting or reopening a conversation.</p>
        </section>
        <div class="mandatory-review-note"><strong>What you are agreeing to</strong><br>Your conversations, AI responses, roleplay settings, and feedback remain exclusively on your device with military-grade end-to-end encryption. No data ever leaves your device, is stored on our servers, or is accessible to anyone - including us. You have complete control with options to clear conversations or permanently delete your session data from your device at any time.</div>
        """,
        unsafe_allow_html=True,
    )
    left, centre, right = st.columns([1, 1.7, 1])
    with centre:
        st.markdown("Read the full [Terms and Conditions](?page=terms) before continuing.")
        with st.form("updated_terms_form"):
            accepted = st.checkbox(
                "I Agree with the Terms and Conditions"
            )
            submitted = st.form_submit_button(
                "Accept and continue",
                type="primary",
                use_container_width=True,
            )
        if submitted:
            if not accepted:
                st.warning("Select the agreement checkbox before continuing.")
            else:
                try:
                    response = request_api(
                        "PUT",
                        "/account/terms",
                        {"terms_accepted": True},
                        auth=True,
                        timeout=15,
                    )
                    if response.status_code == 200:
                        st.session_state.user = response.json()
                        st.toast("Updated Terms accepted")
                        st.rerun()
                    else:
                        st.error(error_detail(response))
                except requests.RequestException:
                    st.error("DilSe could not save your acceptance. Check your connection and try again.")
        if st.button("Sign out", use_container_width=True, key="terms_update_sign_out"):
            sign_out()
            st.rerun()
        with st.expander("Delete my account instead"):
            st.caption("This permanently removes the account and its stored conversations. It cannot be undone.")
            with st.form("terms_update_delete_account_form"):
                password = st.text_input("Password", type="password", autocomplete="current-password")
                confirm_delete = st.checkbox("I understand that this permanently deletes my account and stored data.")
                delete_submitted = st.form_submit_button(
                    "Delete account permanently",
                    use_container_width=True,
                )
            if delete_submitted:
                if not confirm_delete:
                    st.warning("Confirm permanent deletion before continuing.")
                else:
                    try:
                        response = request_api(
                            "DELETE",
                            "/account",
                            {"password": password},
                            auth=True,
                            timeout=20,
                        )
                        if response.status_code == 204:
                            sign_out()
                            st.success("Your account and stored data were deleted.")
                            st.rerun()
                        else:
                            st.error(error_detail(response))
                    except requests.RequestException:
                        st.error("DilSe could not delete the account. Check your connection and try again.")


def render_auth() -> None:
    hero_image_uri = image_data_uri(
        str(LANDING_IMAGE_PATH), LANDING_IMAGE_PATH.stat().st_mtime_ns
    )
    logo_uri = image_data_uri(
        str(LOGO_PATH), LOGO_PATH.stat().st_mtime_ns
    )
    auth_action = str(st.query_params.get("auth") or "")
    auth_route = auth_action in {"create", "signin"}
    marketing_class = " landing-marketing-hidden" if auth_route else ""
    auth_stage_class = " auth-route-stage" if auth_route else ""
    if auth_action == "signin":
        auth_kicker = "Welcome back"
        auth_heading = "Sign in to DilSe."
        auth_copy = "Continue your conversations and practice from your DilSe account."
    else:
        auth_kicker = "Start from the heart"
        auth_heading = "Create your DilSe account."
        auth_copy = "Use a nickname if you prefer. All conversations remain exclusively on your device with complete privacy."
    st.markdown(
        f"""
        <header class="site-masthead">
            <img class="site-logo" src="{logo_uri}" alt="DilSe, from the heart">
            <nav class="site-nav" aria-label="Account navigation">
                <a href="?auth=signin" target="_self">Sign in</a>
                <a href="?auth=create" target="_self">Create account</a>
            </nav>
        </header>
        <div class="landing-marketing{marketing_class}">
        <section class="landing-hero landing-hero-v2">
            <div class="hero-copy">
                <div class="landing-kicker">Made for women in Pakistan · دل سے</div>
                <h1>Say it here before you say it at home.</h1>
                <p class="landing-lede">Understand what you feel, find the words, and practise the conversation before the real moment arrives.</p>
                <p class="urdu-hero" lang="ur-Latn">Jo baat kehna mushkil ho, pehle yahan keh lijiye.</p>
                <div class="landing-actions">
                    <a href="?auth=create" target="_self">Create your account</a>
                    <a href="?auth=signin" target="_self">Sign in</a>
                </div>
                <div class="hero-facts" aria-label="Account information">
                    <span>For adults 18+</span><span>Use a nickname</span><span>End-to-end encrypted</span>
                </div>
            </div>
            <div class="hero-product-preview" aria-label="DilSe conversation preview">
                <div class="portrait-window">
                    <img class="hero-portrait" src="{hero_image_uri}" alt="Illustration of a Pakistani woman holding a letter beside a sunlit window">
                    <span class="portrait-caption">A space for the words you have been holding back</span>
                </div>
                <div class="preview-dialogue">
                    <div class="preview-heading"><span>Choose your space</span><span>English + Roman Urdu</span></div>
                    <div class="preview-message preview-user">“Main usse kehna chahti hoon that I miss feeling close.”</div>
                    <div class="preview-message preview-dilse"><strong>DilSe</strong> What would feeling close look like this week?</div>
                    <div class="preview-modes">
                        <span class="active">Listener <small>talk it through</small></span>
                        <span>Partner <small>practise the reply</small></span>
                    </div>
                </div>
            </div>
        </section>

        <div class="landing-language-rail" aria-label="Supported conversation languages">
            <span>English</span><span>Urdu</span><span>Roman Urdu</span><span>English + Urdu</span>
        </div>

        <section class="landing-mode-stage">
            <div class="mode-stage-intro">
                <div class="section-kicker">Two ways to begin</div>
                <h2>Start with what you need right now.</h2>
                <p>You do not need to prepare a perfect explanation. Choose a mode, write the first honest sentence, and let the conversation build from there.</p>
            </div>
            <div class="mode-ledger" aria-label="DilSe conversation modes">
                <article class="mode-panel listener-panel">
                    <div class="mode-number">01 · The Listener</div>
                    <h3>Talk it through.</h3>
                    <p>DilSe asks focused questions, checks context before reaching conclusions, and helps you separate your needs from fear, guilt, and assumptions.</p>
                    <div class="mode-example"><span>Start with</span> “I am upset, but I do not know exactly why.”</div>
                </article>
                <article class="mode-panel partner-panel">
                    <div class="mode-number">02 · The Partner</div>
                    <h3>Practise the conversation.</h3>
                    <p>Describe the person, choose the situation, and rehearse the exchange in character. Pause anytime to ask for feedback or try a different approach.</p>
                    <div class="mode-example"><span>Start with</span> “Act like my husband. I need to discuss his family.”</div>
                </article>
            </div>
        </section>

        <section class="conversation-spectrum">
            <div class="spectrum-intro">
                <div class="section-kicker">More than one difficult topic</div>
                <h2>Your relationship holds many conversations.</h2>
                <p>DilSe can help you think, prepare, or roleplay across the parts of life that become difficult to say aloud.</p>
                <p class="spectrum-urdu" lang="ur-Latn">Aap jis mix mein naturally baat karti hain, DilSe usi zubaan mein jawab de sakta hai.</p>
            </div>
            <div class="topic-ledger" aria-label="Conversation topics">
                <article><span>Marriage and closeness</span><p>Affection, emotional distance, intimacy, desire, and rebuilding connection.</p></article>
                <article><span>Family and in-laws</span><p>Expectations, privacy, boundaries, respect, and decisions made around the wider family.</p></article>
                <article><span>Trust and conflict</span><p>Recurring arguments, jealousy, repair after hurt, and the meaning behind an interaction.</p></article>
                <article><span>Life together</span><p>Money, parenting, household work, faith, careers, and decisions about the future.</p></article>
            </div>
        </section>

        <section class="cultural-context-section">
            <div class="context-quote" lang="ur-Latn">“Meri baat ko sirf translate nahi, samjha jaye.”</div>
            <div class="context-copy">
                <div class="section-kicker">Context changes the conversation</div>
                <h2>Advice should understand the room you are in.</h2>
                <p>DilSe is built around Pakistani family structures, marriage expectations, faith, privacy, and the pressure to keep peace. It asks what happened and what it means in your relationship before deciding what to suggest.</p>
            </div>
        </section>

        <section class="landing-process">
            <div class="process-heading">
                <div class="section-kicker">A simple session</div>
                <h2>One honest sentence is enough to start.</h2>
            </div>
            <div class="process-path">
                <article><span>01</span><h3>Choose your mode</h3><p>Reflect with The Listener or rehearse with The Partner.</p></article>
                <article><span>02</span><h3>Write it naturally</h3><p>Use English, Urdu, Roman Urdu, or a natural English and Urdu mix.</p></article>
                <article><span>03</span><h3>Take words with you</h3><p>Leave with a clearer thought, a script, or a practised response.</p></article>
            </div>
        </section>

        <section class="landing-trust">
            <div class="trust-heading">
                <div class="section-kicker">Complete Privacy & Control</div>
                <h2>Know how your conversations are handled.</h2>
                <p>All conversations remain exclusively on your device with end-to-end encryption. Nothing is stored on DilSe servers or accessible to third parties.</p>
            </div>
            <div class="trust-ledger">
                <article><strong>100% On-Device</strong><span>Your data never leaves your browser or device.</span></article>
                <article><strong>Delete anytime</strong><span>Clear conversations or delete session data instantly.</span></article>
                <article><strong>Know the limit</strong><span>DilSe is guidance and practice, not licensed therapy or emergency care.</span></article>
            </div>
        </section>

        <section class="final-invitation">
            <div>
                <span class="section-kicker">Ready when you are</span>
                <h2>Aaj sirf pehli line likhiye.</h2>
                <p>Create an account, choose Listener or Partner, and begin with what feels hardest to say.</p>
            </div>
            <a href="?auth=create" target="_self">Start your first conversation</a>
        </section>

        <footer class="landing-footer">
            <img src="{logo_uri}" alt="DilSe">
            <p>Relationship guidance and conversation practice for adults 18+.</p>
            <a href="?page=terms" target="_self">Terms and Conditions</a>
        </footer>
        </div>

        <div id="start" class="auth-stage{auth_stage_class}">
            <div class="section-kicker">{auth_kicker}</div>
            <h2>{auth_heading}</h2>
            <p class="auth-stage-copy">{auth_copy}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, centre, right = st.columns([.8, 1.5, .8])
    with centre:
        if st.query_params.get("auth", "create") == "signin":
            sign_in, create = st.tabs(["Sign in", "Create account"])
        else:
            create, sign_in = st.tabs(["Create account", "Sign in"])
        with sign_in:
            with st.form("sign_in_form"):
                email = st.text_input("Email", autocomplete="email")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                try:
                    response = request_api("POST", "/auth/login", {"email": email, "password": password})
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.auth_token = result["token"]
                        st.session_state.user = result["user"]
                        remember_browser_login(result["token"])
                        st.rerun()
                    else:
                        st.error(error_detail(response))
                except requests.RequestException:
                    st.error("DilSe is temporarily unavailable. Please try again shortly.")
        with create:
            with st.form("register_form"):
                display_name = st.text_input("First name or nickname")
                email = st.text_input("Email", key="register_email", autocomplete="email")
                password = st.text_input("Password", type="password", key="register_password", help="Use at least 10 characters.")
                country = st.selectbox("Country", ["Pakistan"])
                language = st.selectbox("Preferred language", ["English", "Urdu", "Roman Urdu", "English and Urdu"])
                st.markdown("Read the [Terms and Conditions](?page=terms), including the privacy and AI-processing details.")
                terms = st.checkbox(
                    "I Agree with the Terms and Conditions"
                )
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                payload = {
                    "display_name": display_name,
                    "email": email,
                    "password": password,
                    "language": language,
                    "country": country,
                    "terms_accepted": terms,
                }
                try:
                    response = request_api("POST", "/auth/register", payload)
                    if response.status_code == 201:
                        result = response.json()
                        st.session_state.auth_token = result["token"]
                        st.session_state.user = result["user"]
                        remember_browser_login(result["token"])
                        st.rerun()
                    else:
                        st.error(error_detail(response))
                except requests.RequestException:
                    st.error("DilSe is temporarily unavailable. Please try again shortly.")
        st.markdown(
            '<div class="data-note">DilSe provides relationship guidance and practice. It is not a licensed therapist or an emergency service.</div>',
            unsafe_allow_html=True,
        )


def message_reply_markup(
    message: dict[str, Any],
    *,
    viewer: str,
    user_label: str = "User",
) -> str:
    reply_to_id = message.get("reply_to_message_id")
    reply_content = " ".join(str(message.get("reply_to_content") or "").split())
    if not reply_to_id or not reply_content:
        return ""
    reply_role = str(message.get("reply_to_role") or "")
    reply_source = str(message.get("reply_to_source") or "")
    if viewer == "user":
        author = "You" if reply_role == "user" else "DilSe"
    elif reply_role == "user":
        author = user_label
    elif reply_source == "admin":
        author = "Administrator"
    else:
        author = "DilSe AI"
    if len(reply_content) > 190:
        reply_content = f"{reply_content[:187].rstrip()}…"
    return (
        '<div class="message-reply-quote">'
        f'<span>Replying to {html.escape(author)}</span>'
        f'<p>{html.escape(reply_content)}</p>'
        "</div>"
    )


def reply_target_snapshot(message: dict[str, Any], session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "message_id": int(message["message_id"] if message.get("message_id") else message["id"]),
        "role": message.get("role"),
        "content": message.get("content"),
        "source": message.get("source"),
    }


ADMIN_LINK_PATTERN = re.compile(r"https?://[^\s<>\[\]\"'()]+")


def clickable_admin_message(value: str) -> str:
    """Turn plain web links into safe Markdown without accepting administrator HTML."""
    pieces: list[str] = []
    cursor = 0
    for match in ADMIN_LINK_PATTERN.finditer(value):
        raw_url = match.group(0)
        url = raw_url.rstrip(".,;:!?")
        trailing = raw_url[len(url):]
        pieces.append(html.escape(value[cursor:match.start()]))
        pieces.append(f"[{html.escape(url)}]({url})")
        pieces.append(html.escape(trailing))
        cursor = match.end()
    pieces.append(html.escape(value[cursor:]))
    return "".join(pieces).replace("\n", "  \n")


def render_message_attachment(message: dict[str, Any], *, viewer: str) -> None:
    attachment_id = message.get("attachment_id")
    message_id = message.get("message_id") or message.get("id")
    if not attachment_id or not message_id:
        return
    cache_key = f"{viewer}:{message_id}:{attachment_id}"
    cache = st.session_state.message_attachment_cache
    if cache_key not in cache:
        path = (
            f"/admin/messages/{message_id}/attachment"
            if viewer == "admin"
            else f"/messages/{message_id}/attachment"
        )
        try:
            response = request_api(
                "GET",
                path,
                auth=viewer == "user",
                admin=viewer == "admin",
                timeout=20,
            )
            cache[cache_key] = response.content if response.status_code == 200 else None
        except requests.RequestException:
            cache[cache_key] = None
    image_content = cache.get(cache_key)
    if image_content:
        st.image(
            image_content,
            caption=str(message.get("attachment_filename") or "Shared image"),
            use_container_width=True,
        )
    else:
        st.caption("The attached image is temporarily unavailable.")


def render_message_voice_note(message: dict[str, Any], *, viewer: str) -> None:
    voice_note_id = message.get("voice_note_id")
    message_id = message.get("message_id") or message.get("id")
    if not voice_note_id or not message_id:
        return
    cache_key = f"voice:{viewer}:{message_id}:{voice_note_id}"
    cache = st.session_state.message_attachment_cache
    if cache_key not in cache:
        path = (
            f"/admin/messages/{message_id}/voice-note"
            if viewer == "admin"
            else f"/messages/{message_id}/voice-note"
        )
        try:
            response = request_api(
                "GET",
                path,
                auth=viewer == "user",
                admin=viewer == "admin",
                timeout=30,
            )
            cache[cache_key] = response.content if response.status_code == 200 else None
        except requests.RequestException:
            cache[cache_key] = None
    audio_content = cache.get(cache_key)
    if audio_content:
        st.audio(
            audio_content,
            format=str(message.get("voice_note_mime_type") or "audio/wav"),
        )
        duration = float(message.get("voice_note_duration_seconds") or 0)
        if duration:
            minutes, seconds = divmod(int(round(duration)), 60)
            st.caption(f"Voice note · {minutes}:{seconds:02d}")
    else:
        st.caption("The voice note is temporarily unavailable.")


def render_message_body(message: dict[str, Any], *, viewer: str) -> None:
    content = str(message.get("content") or "")
    if content:
        if message.get("source") == "admin":
            st.markdown(clickable_admin_message(content))
        else:
            st.markdown(content)
    render_message_attachment(message, viewer=viewer)
    render_message_voice_note(message, viewer=viewer)


def send_chat(
    message: str,
    mode: str,
    scenario: str | None,
    persona: str | None,
    roleplay_intensity: str | None = None,
    character_description: str | None = None,
    roleplay_difficulty: str | None = None,
    reply_to_message_id: int | None = None,
) -> None:
    reply_started_at = time.perf_counter()
    visible_history = [
        {"role": item["role"], "content": item["content"]}
        for item in st.session_state.messages[-20:]
        if item.get("role") in {"user", "assistant"} and not item.get("error") and not item.get("notice")
    ]
    history = [*st.session_state.carried_history, *visible_history][-20:]
    reply_target = next(
        (
            item
            for item in st.session_state.messages
            if reply_to_message_id is not None
            and int(item.get("message_id") or -1) == reply_to_message_id
        ),
        None,
    )
    local_user_message: dict[str, Any] = {"role": "user", "content": message}
    if reply_target:
        local_user_message.update(
            {
                "reply_to_message_id": reply_to_message_id,
                "reply_to_role": reply_target.get("role"),
                "reply_to_content": reply_target.get("content"),
                "reply_to_source": reply_target.get("source"),
            }
        )
    st.session_state.messages.append(local_user_message)
    payload = {
        "session_id": st.session_state.session_id,
        "message": message,
        "mode": mode,
        "client_platform": "web",
        "scenario": scenario,
        "persona": persona,
        "roleplay_intensity": roleplay_intensity,
        "roleplay_difficulty": roleplay_difficulty,
        "character_description": character_description,
        "reply_to_message_id": reply_to_message_id,
        "history": history,
    }
    try:
        response = request_api("POST", "/chat", payload, auth=True)
        if response.status_code == 200:
            result = response.json()
            if result.get("user_message_id"):
                for item in reversed(st.session_state.messages):
                    if item.get("role") == "user" and not item.get("message_id"):
                        item["message_id"] = result["user_message_id"]
                        break
            if result.get("message_id"):
                st.session_state.last_message_id = max(st.session_state.last_message_id, result["message_id"])
            st.session_state.conversation_checkpoint = result.get("conversation_checkpoint")
            if (
                reply_to_message_id is not None
                and (st.session_state.get("user_reply_to") or {}).get("message_id")
                == reply_to_message_id
            ):
                st.session_state.user_reply_to = None
            st.session_state.carried_history = []
            st.session_state.transition_label = None
            waiting_for_admin = result.get("delivery") == "waiting_for_admin"
            if SHOW_HUMAN_HANDOFF_UI or not waiting_for_admin:
                if result.get("delivery") == "ai":
                    remaining_delay = AI_REPLY_MIN_DELAY_SECONDS - (
                        time.perf_counter() - reply_started_at
                    )
                    if remaining_delay > 0:
                        time.sleep(remaining_delay)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["response"],
                        "usage": result["prompt_tokens"] + result["completion_tokens"],
                        "stored": result["stored"],
                        "notice": waiting_for_admin,
                        "message_id": result.get("message_id"),
                    }
                )
        else:
            st.session_state.messages.append({"role": "assistant", "content": error_detail(response), "error": True})
    except requests.RequestException:
        st.session_state.messages.append(
            {"role": "assistant", "content": "DilSe cannot reach the API. Confirm that FastAPI is running on port 8000.", "error": True}
        )


def send_user_voice_note(
    recording: Any,
    mode: str,
    scenario: str | None,
    persona: str | None,
    roleplay_intensity: str | None,
    character_description: str | None,
    roleplay_difficulty: str | None,
    reply_to_message_id: int | None,
) -> bool:
    audio_content = recording.getvalue()
    upload_id = hashlib.sha256(
        str(st.session_state.session_id).encode("utf-8") + b"\0" + audio_content
    ).hexdigest()
    voice_note_uploads = dict(st.session_state.get("voice_note_uploads") or {})
    if voice_note_uploads.get(upload_id) == "uploading":
        st.info("This voice note is already being sent.")
        return False
    if voice_note_uploads.get(upload_id) == "sent":
        st.info("This voice note was already sent.")
        return False
    voice_note_uploads[upload_id] = "uploading"
    st.session_state.voice_note_uploads = voice_note_uploads
    payload = {
        "audio_base64": base64.b64encode(audio_content).decode("ascii"),
        "audio_mime_type": "audio/wav",
        "audio_filename": Path(getattr(recording, "name", "voice-note.wav")).name,
        "upload_id": upload_id,
        "mode": mode,
        "client_platform": "web",
        "scenario": scenario,
        "persona": persona,
        "roleplay_intensity": roleplay_intensity,
        "roleplay_difficulty": roleplay_difficulty,
        "character_description": character_description,
        "reply_to_message_id": reply_to_message_id,
    }
    try:
        response = request_api(
            "POST",
            f"/sessions/{st.session_state.session_id}/voice-notes",
            payload,
            auth=True,
            timeout=60,
        )
    except requests.RequestException:
        voice_note_uploads.pop(upload_id, None)
        st.session_state.voice_note_uploads = voice_note_uploads
        st.error("DilSe could not upload the voice note. Check your connection and try again.")
        return False
    if response.status_code != 201:
        voice_note_uploads.pop(upload_id, None)
        st.session_state.voice_note_uploads = voice_note_uploads
        st.error(error_detail(response))
        return False
    result = response.json()
    message_id = int(result["user_message_id"])
    voice_note_id = int(result["voice_note_id"])
    reply_target = next(
        (
            item
            for item in st.session_state.messages
            if reply_to_message_id is not None
            and int(item.get("message_id") or -1) == reply_to_message_id
        ),
        None,
    )
    local_message: dict[str, Any] = {
        "role": "user",
        "content": "Voice note",
        "source": "user",
        "message_id": message_id,
        "voice_note_id": voice_note_id,
        "voice_note_filename": payload["audio_filename"],
        "voice_note_mime_type": "audio/wav",
        "voice_note_size_bytes": len(audio_content),
    }
    if reply_target:
        local_message.update(
            {
                "reply_to_message_id": reply_to_message_id,
                "reply_to_role": reply_target.get("role"),
                "reply_to_content": reply_target.get("content"),
                "reply_to_source": reply_target.get("source"),
            }
        )
    st.session_state.message_attachment_cache[
        f"voice:user:{message_id}:{voice_note_id}"
    ] = audio_content
    if not any(
        int(item.get("message_id") or -1) == message_id
        for item in st.session_state.messages
    ):
        st.session_state.messages.append(local_message)
    voice_note_uploads[upload_id] = "sent"
    st.session_state.voice_note_uploads = voice_note_uploads
    st.session_state.last_message_id = max(st.session_state.last_message_id, message_id)
    st.session_state.user_reply_to = None
    st.session_state.carried_history = []
    st.session_state.transition_label = None
    st.toast("Voice note sent")
    return True


@st.fragment(run_every="500ms")
def watch_live_session() -> None:
    user = st.session_state.user
    if not user or not st.session_state.auth_token or not user.get("store_chats"):
        return
    try:
        sync_response = request_api(
            "GET",
            f"/sessions/{st.session_state.session_id}/sync?after_id={st.session_state.last_message_id}",
            auth=True,
            timeout=5,
        )
        if sync_response.status_code != 200:
            return
        session_status = sync_response.json()
        if st.session_state.get("voice_recording_active"):
            server_message_ids = {
                int(message_id)
                for message_id in session_status.get("message_ids") or []
            }
            local_message_ids = {
                int(item["message_id"])
                for item in st.session_state.messages
                if item.get("message_id")
            }
            if server_message_ids != local_message_ids or session_status.get("updates"):
                st.session_state.voice_recording_pending_refresh = True
            return
        removed = False
        if isinstance(session_status.get("message_ids"), list):
            current_message_ids = {
                int(message_id) for message_id in session_status["message_ids"]
            }
            messages_before_sync = len(st.session_state.messages)
            st.session_state.messages = [
                item
                for item in st.session_state.messages
                if not item.get("message_id")
                or int(item["message_id"]) in current_message_ids
            ]
            removed = len(st.session_state.messages) != messages_before_sync
        updates = session_status.get("updates") or []
        added = False
        known_message_ids = {
            int(item["message_id"])
            for item in st.session_state.messages
            if item.get("message_id")
        }
        for item in updates:
            st.session_state.last_message_id = max(st.session_state.last_message_id, item["id"])
            if int(item["id"]) in known_message_ids:
                continue
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": item["content"],
                    "source": item.get("source") or "ai",
                    "message_id": item["id"],
                    "reply_to_message_id": item.get("reply_to_message_id"),
                    "reply_to_role": item.get("reply_to_role"),
                    "reply_to_content": item.get("reply_to_content"),
                    "reply_to_source": item.get("reply_to_source"),
                    "attachment_id": item.get("attachment_id"),
                    "attachment_filename": item.get("attachment_filename"),
                    "attachment_mime_type": item.get("attachment_mime_type"),
                    "attachment_size_bytes": item.get("attachment_size_bytes"),
                    "voice_note_id": item.get("voice_note_id"),
                    "voice_note_filename": item.get("voice_note_filename"),
                    "voice_note_mime_type": item.get("voice_note_mime_type"),
                    "voice_note_size_bytes": item.get("voice_note_size_bytes"),
                    "voice_note_duration_seconds": item.get("voice_note_duration_seconds"),
                }
            )
            known_message_ids.add(int(item["id"]))
            added = True
        if added or removed:
            st.session_state.voice_recording_pending_refresh = False
            st.rerun(scope="app")
        elif st.session_state.get("voice_recording_pending_refresh"):
            st.session_state.voice_recording_pending_refresh = False
            st.rerun(scope="app")
    except requests.RequestException:
        return


@st.fragment
def publish_user_typing_state(session_id: str) -> None:
    assistant_message_ids = [
        int(item["message_id"])
        for item in st.session_state.messages
        if item.get("role") == "assistant" and item.get("message_id")
    ]
    confirmed_by_session = dict(st.session_state.confirmed_read_receipts)
    confirmed_read_ids = [
        int(message_id)
        for message_id in confirmed_by_session.get(session_id, [])
        if str(message_id).isdigit()
    ]
    event = typing_capture_component(
        session_id=session_id,
        assistant_message_ids=assistant_message_ids,
        confirmed_read_ids=confirmed_read_ids,
        default=None,
        key=f"typing_capture_{session_id}",
        tab_index=-1,
    )
    if not isinstance(event, dict) or not event.get("event_id"):
        return
    event_id = str(event["event_id"])
    previous_ids = st.session_state.typing_capture_event_ids
    if previous_ids.get(session_id) == event_id:
        return
    previous_ids[session_id] = event_id
    try:
        read_message_ids = [
            int(message_id)
            for message_id in event.get("message_ids") or []
            if str(message_id).isdigit()
            and int(message_id) in assistant_message_ids
            and int(message_id) not in confirmed_read_ids
        ]
        if read_message_ids:
            receipt_response = request_api(
                "POST",
                f"/sessions/{session_id}/read",
                {"message_ids": read_message_ids},
                auth=True,
                timeout=5,
            )
            if receipt_response.status_code == 200:
                confirmed_read_ids = sorted(
                    set(confirmed_read_ids).union(read_message_ids)
                )
                confirmed_by_session[session_id] = confirmed_read_ids
                st.session_state.confirmed_read_receipts = confirmed_by_session
        if event.get("event_type") == "recording":
            st.session_state.voice_recording_active = bool(event.get("is_recording"))
        elif event.get("event_type") == "typing":
            request_api(
                "POST",
                f"/sessions/{session_id}/typing",
                {"is_typing": bool(event.get("is_typing"))},
                auth=True,
                timeout=5,
            )
    except requests.RequestException:
        return


def follow_latest_chat_message(
    view: str,
    conversation_id: str,
    messages: list[dict[str, Any]],
) -> None:
    """Move a transcript to its newest message only when the message list changes."""
    if not messages:
        return
    signature_parts: list[str] = []
    for index, message in enumerate(messages):
        message_id = message.get("message_id") or message.get("id")
        if message_id is None:
            content_digest = hashlib.sha256(
                str(message.get("content") or "").encode("utf-8")
            ).hexdigest()[:12]
            message_id = f"local-{index}-{content_digest}"
        signature_parts.append(f"{message.get('role')}:{message_id}")
    signature = hashlib.sha256("|".join(signature_parts).encode("utf-8")).hexdigest()
    scroll_key = f"{view}:{conversation_id}"
    anchor_id = (
        "dilse-chat-end-"
        + hashlib.sha256(scroll_key.encode("utf-8")).hexdigest()[:16]
    )
    st.markdown(
        (
            f'<div id="{anchor_id}" class="dilse-chat-scroll-anchor" '
            f'data-dilse-chat-anchor="{html.escape(scroll_key)}" aria-hidden="true"></div>'
        ),
        unsafe_allow_html=True,
    )
    components.html(
        f"""<script>
        (() => {{
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;
            const scrollKey = {json.dumps(scroll_key)};
            const signature = {json.dumps(signature)};
            const anchorId = {json.dumps(anchor_id)};
            const followState = parentWindow.__dilseChatFollowState ||
                (parentWindow.__dilseChatFollowState = {{}});
            if (followState[scrollKey] === signature) return;
            const findScrollContainer = (element) => {{
                const transcriptRoot = element?.closest(
                    '.st-key-user_chat_transcript, [class*="st-key-admin_chat_transcript_"]'
                );
                if (!transcriptRoot) return null;
                let candidate = element?.parentElement || null;
                while (candidate && transcriptRoot.contains(candidate)) {{
                    const style = parentWindow.getComputedStyle(candidate);
                    if (/auto|scroll/.test(style.overflowY)) return candidate;
                    if (candidate === transcriptRoot) break;
                    candidate = candidate.parentElement;
                }}
                return null;
            }};
            const moveToLatest = (complete = false) => {{
                const anchor = parentDocument.getElementById(anchorId);
                if (!anchor || !anchor.isConnected) return false;
                const scrollContainer = findScrollContainer(anchor);
                if (!scrollContainer) return false;
                scrollContainer.scrollTo({{
                    top: scrollContainer.scrollHeight,
                    left: scrollContainer.scrollLeft,
                    behavior: "auto"
                }});
                if (complete) followState[scrollKey] = signature;
                return true;
            }};
            parentWindow.requestAnimationFrame(() =>
                parentWindow.requestAnimationFrame(() => moveToLatest(false))
            );
            parentWindow.setTimeout(() => moveToLatest(false), 120);
            parentWindow.setTimeout(() => moveToLatest(false), 350);
            parentWindow.setTimeout(() => moveToLatest(true), 700);
        }})();
        </script>""",
        height=0,
        width=0,
    )


def show_admin_chat_unread_badge(
    conversation_id: str,
    messages: list[dict[str, Any]],
) -> None:
    """Badge the admin browser tab when a user writes while it is in the background."""
    user_message_ids = [
        int(message["id"])
        for message in messages
        if message.get("role") == "user" and message.get("id") is not None
    ]
    components.html(
        f"""<script>
        (() => {{
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;
            const conversationId = {json.dumps(conversation_id)};
            const userMessageIds = {json.dumps(user_message_ids)};
            const state = parentWindow.__dilseAdminUnreadState ||
                (parentWindow.__dilseAdminUnreadState = {{
                    activeConversation: null,
                    seenByConversation: {{}},
                    unread: 0,
                    listenersReady: false,
                    render: null
                }});

            if (state.activeConversation !== conversationId) {{
                state.activeConversation = conversationId;
                state.unread = 0;
            }}
            const previousIds = state.seenByConversation[conversationId];
            if (Array.isArray(previousIds)) {{
                const previouslySeen = new Set(previousIds);
                const newUserMessages = userMessageIds.filter(
                    (messageId) => !previouslySeen.has(messageId)
                );
                if (
                    newUserMessages.length > 0 &&
                    (parentDocument.hidden || !parentDocument.hasFocus())
                ) {{
                    state.unread += newUserMessages.length;
                }}
            }}
            state.seenByConversation[conversationId] = userMessageIds;

            const renderBadge = () => {{
                const count = Math.max(0, Number(state.unread) || 0);
                const countLabel = count > 9 ? "9+" : String(count);
                parentDocument.title = count > 0
                    ? `(${{count}}) DilSe Admin | Conversation`
                    : "DilSe Admin | Conversation";
                let icon = parentDocument.querySelector(
                    'link[rel="icon"][data-dilse-admin-badge="true"]'
                );
                if (!icon) {{
                    icon = parentDocument.createElement("link");
                    icon.rel = "icon";
                    icon.type = "image/svg+xml";
                    icon.dataset.dilseAdminBadge = "true";
                    parentDocument.head.appendChild(icon);
                }}
                const badge = count > 0
                    ? `<circle cx="50" cy="14" r="13" fill="#d95757" stroke="#fffaf4" stroke-width="3"/>` +
                      `<text x="50" y="18" text-anchor="middle" fill="#ffffff" font-family="Arial,sans-serif" font-size="${{count > 9 ? 11 : 14}}" font-weight="700">${{countLabel}}</text>`
                    : "";
                const favicon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">` +
                    `<rect width="64" height="64" rx="18" fill="#173f3b"/>` +
                    `<text x="27" y="44" text-anchor="middle" fill="#fffaf4" font-family="Georgia,serif" font-size="38" font-weight="700">D</text>` +
                    badge + `</svg>`;
                icon.href = `data:image/svg+xml,${{encodeURIComponent(favicon)}}`;
            }};
            state.render = renderBadge;

            if (!state.listenersReady) {{
                const markVisibleMessagesRead = () => {{
                    if (!parentDocument.hidden && parentDocument.hasFocus()) {{
                        state.unread = 0;
                        if (typeof state.render === "function") state.render();
                    }}
                }};
                parentDocument.addEventListener("visibilitychange", markVisibleMessagesRead);
                parentWindow.addEventListener("focus", markVisibleMessagesRead);
                state.listenersReady = true;
            }}
            renderBadge();
            window.setTimeout(renderBadge, 180);
        }})();
        </script>""",
        height=0,
        width=0,
    )


def start_exercise(starter: str) -> Callable[[], None]:
    def callback() -> None:
        reset_local_conversation()
        st.session_state.page = "Talk"
        st.session_state.main_navigation = "Talk"
        st.session_state.mode = "The Listener"
        st.session_state.conversation_mode = "The Listener"
        st.session_state.conversation_mode_confirmed = True
        st.session_state.pending_prompt = starter

    return callback


def open_mobile_conversation_settings() -> None:
    st.session_state.mobile_conversation_settings_open = True


def close_mobile_conversation_settings() -> None:
    st.session_state.mobile_conversation_settings_open = False


def select_mobile_conversation_mode(target_mode: str) -> None:
    current_mode = str(
        st.session_state.get("conversation_mode") or st.session_state.mode
    )
    if target_mode != current_mode:
        if st.session_state.messages:
            switch_conversation_mode(target_mode)
        else:
            st.session_state.mode = target_mode
            st.session_state.conversation_mode = target_mode
    st.session_state.conversation_mode_confirmed = True
    st.session_state.mobile_conversation_settings_open = False


def clear_character_profile() -> None:
    st.session_state.character_description = ""
    st.session_state.character_description_editor = ""
    st.session_state.partner_profile_editor_sync = False


def sync_character_profile_from_editor() -> None:
    st.session_state.character_description = str(
        st.session_state.get("character_description_editor") or ""
    ).strip()


def character_profile_word_count(value: str | None) -> int:
    return len(str(value or "").split())


def character_profile_guidance(persona_slug: str, persona_name: str) -> dict[str, str]:
    guidance = CHARACTER_PROFILE_GUIDANCE.get(persona_slug)
    if guidance:
        return guidance
    relationship = persona_name.strip().lower() or "this person"
    return {
        "relationship": relationship,
        "question": "How do they normally speak, react to discomfort, show care, and handle disagreement?",
        "placeholder": "Describe their temperament, speaking style, common reactions, and any relationship history DilSe should preserve during the roleplay.",
    }


def render_mobile_conversation_controls(
    catalog: dict[str, list[dict[str, Any]]],
) -> None:
    del catalog
    mode_label = str(st.session_state.get("conversation_mode") or st.session_state.mode)

    with st.container(
        key="mobile_conversation_controls",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        gap="small",
    ):
        st.markdown(
            '<span class="mobile-mode-label">Mode</span>',
            unsafe_allow_html=True,
        )
        st.button(
            "Listener",
            on_click=select_mobile_conversation_mode,
            args=("The Listener",),
            type="primary" if mode_label == "The Listener" else "secondary",
            key="mobile_mode_listener",
        )
        st.button(
            "Partner",
            on_click=select_mobile_conversation_mode,
            args=("The Partner",),
            type="primary" if mode_label == "The Partner" else "secondary",
            key="mobile_mode_partner",
        )
        st.button(
            "Settings",
            on_click=open_mobile_conversation_settings,
            key="mobile_open_conversation_settings",
        )
        if st.session_state.mobile_conversation_settings_open:
            st.markdown(
                '<span class="mobile-settings-open-marker"></span>',
                unsafe_allow_html=True,
            )


def render_conversation_setup(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, str | None]:
    st.button(
        "Close settings",
        on_click=close_mobile_conversation_settings,
        use_container_width=True,
        key="mobile_close_conversation_settings",
    )
    st.markdown(
        '<div class="conversation-panel-head"><span>Conversation settings</span><strong>Choose how this chat works</strong><p>Listener helps you think. Partner replies as the person you want to practise with.</p></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.messages:
        active_label = "Listening and reflecting" if st.session_state.mode == "The Listener" else "Roleplaying in character"
        st.markdown(
            f'<div class="active-mode-summary"><span>Current mode</span><strong>{html.escape(st.session_state.mode)}</strong><small>{html.escape(active_label)}</small></div>',
            unsafe_allow_html=True,
        )
        switch_label = "Start a Partner chat" if st.session_state.mode == "The Listener" else "Start a Listener chat"
        switch_target = "The Partner" if st.session_state.mode == "The Listener" else "The Listener"
        st.button(
            switch_label,
            on_click=switch_conversation_mode,
            args=(switch_target,),
            key="intentional_mode_switch",
            use_container_width=True,
        )
    else:
        selected_mode = st.radio(
            "Mode",
            ["The Listener", "The Partner"],
            key="conversation_mode",
            horizontal=True,
            help="Listener offers reflection and guidance. Partner stays in character for practice.",
        )
        st.session_state.mode = selected_mode or "The Listener"

    mode = "listener" if st.session_state.mode == "The Listener" else "partner"
    scenario_slug: str | None = None
    persona_slug: str | None = None
    scenario_name: str | None = None
    persona_name: str | None = None
    roleplay_intensity: str | None = None
    roleplay_difficulty: str | None = None
    character_description: str | None = None
    if mode == "listener":
        st.markdown(
            '<div class="listener-mode-note"><span>Listener is ready</span><strong>Write naturally. No setup needed.</strong><p>DilSe will listen first, ask focused questions, and help you decide what to say or do next.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="partner-mode-note"><span>Roleplay setup</span><strong>Shape the person before you begin</strong><p>Your selections stay visible here while the conversation remains focused in the centre.</p></div>',
            unsafe_allow_html=True,
        )
        scenarios = catalog.get("scenarios", [])
        personas = catalog.get("personas", [])
        if scenarios and personas:
            persona_index = next(
                (index for index, item in enumerate(personas) if item["slug"] == st.session_state.resumed_persona_slug),
                0,
            )
            persona_name = st.selectbox(
                "Who are you talking to?",
                [item["name"] for item in personas],
                index=persona_index,
                key="roleplay_persona_name",
                on_change=clear_character_profile,
                disabled=bool(st.session_state.messages),
            )
            selected_persona = next(item for item in personas if item["name"] == persona_name)
            persona_slug = selected_persona["slug"]
            st.caption(selected_persona["description"])

            profile_copy = character_profile_guidance(persona_slug, persona_name)
            st.markdown(
                f'<div class="character-profile-intro"><span>Character sketch</span><strong>Tell DilSe about {html.escape(profile_copy["relationship"])}</strong><p>{html.escape(profile_copy["question"])}</p></div>',
                unsafe_allow_html=True,
            )
            profile_locked = bool(st.session_state.messages)
            if st.session_state.partner_profile_editor_sync:
                st.session_state.character_description_editor = str(
                    st.session_state.character_description or ""
                )
                st.session_state.partner_profile_editor_sync = False
            st.text_area(
                "Describe this person's nature and character",
                key="character_description_editor",
                height=150,
                max_chars=CHARACTER_PROFILE_MAX_CHARS,
                disabled=profile_locked,
                placeholder=profile_copy["placeholder"],
                on_change=sync_character_profile_from_editor,
            )
            character_description = st.session_state.character_description.strip() or None
            profile_word_count = character_profile_word_count(character_description)
            st.caption(
                f"{profile_word_count:,} / {CHARACTER_PROFILE_MAX_WORDS:,} words"
            )
            profile_ready = bool(
                character_description
                and len(character_description) >= CHARACTER_PROFILE_MIN_LENGTH
                and profile_word_count <= CHARACTER_PROFILE_MAX_WORDS
            )
            if profile_locked:
                st.markdown(
                    '<div class="character-profile-status ready">Profile saved for this conversation. Start a new chat to change it.</div>',
                    unsafe_allow_html=True,
                )
            elif profile_word_count > CHARACTER_PROFILE_MAX_WORDS:
                st.markdown(
                    f'<div class="character-profile-status">Shorten the character sketch to {CHARACTER_PROFILE_MAX_WORDS:,} words or fewer.</div>',
                    unsafe_allow_html=True,
                )
            elif profile_ready:
                st.markdown(
                    '<div class="character-profile-status ready">Character sketch ready. DilSe will use these details in every reply.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="character-profile-status">Add a few real details before starting the roleplay.</div>',
                    unsafe_allow_html=True,
                )

            scenario_index = next(
                (index for index, item in enumerate(scenarios) if item["slug"] == st.session_state.resumed_scenario_slug),
                0,
            )
            scenario_name = st.selectbox(
                "What are you practising?",
                [item["name"] for item in scenarios],
                index=scenario_index,
                key="roleplay_scenario_name",
                disabled=bool(st.session_state.messages),
            )
            selected = next(item for item in scenarios if item["name"] == scenario_name)
            scenario_slug = selected["slug"]
            st.caption(selected["description"])

            intensity_label = st.selectbox(
                "Adult intimacy detail",
                ["Explicit", "Direct", "Romantic"],
                key="roleplay_intensity",
                help="Explicit is the default for adult Partner conversations. Direct is plain but less detailed. Romantic stays suggestive.",
                disabled=bool(st.session_state.messages),
            )
            roleplay_intensity = intensity_label.lower()
            difficulty_label = st.selectbox(
                "How should they react?",
                ["Realistic", "Supportive", "Resistant"],
                key="roleplay_difficulty",
                help="Realistic brings natural concerns. Supportive listens readily. Resistant maintains one believable objection without becoming abusive.",
                disabled=bool(st.session_state.messages),
            )
            roleplay_difficulty = difficulty_label.lower()

            if not profile_locked and profile_ready:
                st.markdown(
                    f'<div class="roleplay-ready"><span>Ready to roleplay</span><strong>{html.escape(persona_name)} · {html.escape(scenario_name)}</strong><small>{html.escape(difficulty_label)} reaction · {html.escape(intensity_label)} detail</small></div>',
                    unsafe_allow_html=True,
                )

    if st.session_state.messages:
        with st.expander("Conversation actions"):
            if st.button(
                "Delete this conversation",
                use_container_width=True,
                key="setup_delete_conversation",
            ):
                st.session_state.pending_delete_session_id = st.session_state.session_id
                st.rerun()
            if st.session_state.pending_delete_session_id == st.session_state.session_id:
                st.warning("Delete this conversation and all stored messages?")
                confirm_col, cancel_col = st.columns(2)
                if confirm_col.button(
                    "Delete",
                    type="primary",
                    use_container_width=True,
                    key="setup_confirm_delete_conversation",
                ):
                    delete_current_conversation()
                    st.rerun()
                if cancel_col.button(
                    "Keep it",
                    use_container_width=True,
                    key="setup_cancel_delete_conversation",
                ):
                    st.session_state.pending_delete_session_id = None
                    st.rerun()
    return {
        "mode": mode,
        "scenario_slug": scenario_slug,
        "persona_slug": persona_slug,
        "scenario_name": scenario_name,
        "persona_name": persona_name,
        "roleplay_intensity": roleplay_intensity,
        "roleplay_difficulty": roleplay_difficulty,
        "character_description": character_description,
    }


def choose_v2_partner_persona(slug: str, name: str) -> None:
    st.session_state.v2_partner_persona_slug = slug
    st.session_state.v2_partner_persona_name = name
    st.session_state.character_description = ""
    st.session_state.character_description_editor = ""


def clear_v2_partner_persona() -> None:
    st.session_state.v2_partner_persona_slug = None
    st.session_state.v2_partner_persona_name = None
    st.session_state.character_description = ""
    st.session_state.character_description_editor = ""


def render_conversation_setup_v2(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, str | None]:
    """Quiet settings panel for accounts assigned to experience v2."""
    st.button(
        "Close settings",
        on_click=close_mobile_conversation_settings,
        use_container_width=True,
        key="v2_mobile_close_conversation_settings",
    )
    mode = "listener" if st.session_state.mode == "The Listener" else "partner"
    st.markdown(
        f'<div class="conversation-panel-head"><span>Current conversation</span>'
        f'<strong>{html.escape(st.session_state.mode)}</strong>'
        f'<p>{"Talk naturally. DilSe will understand before advising." if mode == "listener" else "Character details are collected in the conversation. Optional controls stay here."}</p></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.messages:
        switch_label = (
            "Start a Partner chat" if mode == "listener" else "Start a Listener chat"
        )
        switch_target = "The Partner" if mode == "listener" else "The Listener"
        st.button(
            switch_label,
            on_click=switch_conversation_mode,
            args=(switch_target,),
            key="v2_intentional_mode_switch",
            use_container_width=True,
        )

    scenario_slug: str | None = None
    persona_slug: str | None = None
    persona_name: str | None = None
    roleplay_intensity: str | None = None
    roleplay_difficulty: str | None = None
    character_description: str | None = None
    if mode == "listener":
        st.markdown(
            '<div class="listener-mode-note"><span>Listener is ready</span><strong>No setup needed</strong><p>DilSe will ask one useful question at a time and offer advice after understanding the situation.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        personas = catalog.get("personas", [])
        scenarios = catalog.get("scenarios", [])
        persona_slug = str(
            st.session_state.v2_partner_persona_slug
            or st.session_state.resumed_persona_slug
            or ""
        ) or None
        selected_persona = next(
            (item for item in personas if item["slug"] == persona_slug), None
        )
        if selected_persona:
            persona_name = str(selected_persona["name"])
            st.session_state.v2_partner_persona_slug = persona_slug
            st.session_state.v2_partner_persona_name = persona_name
            st.markdown(
                f'<div class="partner-mode-note"><span>Character</span><strong>{html.escape(persona_name)}</strong><p>{html.escape(str(selected_persona["description"]))}</p></div>',
                unsafe_allow_html=True,
            )
            if not st.session_state.messages:
                st.button(
                    "Choose a different person",
                    on_click=clear_v2_partner_persona,
                    use_container_width=True,
                    key="v2_change_persona",
                )
        else:
            st.caption("Choose the person in the conversation area first.")

        with st.expander("Change practice settings", expanded=False):
            scenario_slugs = [str(item["slug"]) for item in scenarios]
            preferred_scenario = str(
                st.session_state.resumed_scenario_slug
                or st.session_state.v2_scenario_slug
                or "practice_opening_up"
            )
            if preferred_scenario not in scenario_slugs and scenario_slugs:
                preferred_scenario = scenario_slugs[0]
            if scenario_slugs:
                scenario_slug = st.selectbox(
                    "What are you practising?",
                    scenario_slugs,
                    index=scenario_slugs.index(preferred_scenario),
                    format_func=lambda value: next(
                        str(item["name"]) for item in scenarios if item["slug"] == value
                    ),
                    disabled=bool(st.session_state.messages),
                    key="v2_scenario_choice",
                )
                st.session_state.v2_scenario_slug = scenario_slug
            intensity_label = st.selectbox(
                "Adult intimacy detail",
                ["Explicit", "Direct", "Romantic"],
                key="roleplay_intensity",
                disabled=bool(st.session_state.messages),
            )
            difficulty_label = st.selectbox(
                "How should they react?",
                ["Realistic", "Supportive", "Resistant"],
                key="roleplay_difficulty",
                disabled=bool(st.session_state.messages),
            )
            roleplay_intensity = intensity_label.lower()
            roleplay_difficulty = difficulty_label.lower()
        character_description = st.session_state.character_description.strip() or None

    if st.session_state.messages:
        with st.expander("Conversation actions"):
            if st.button(
                "Delete this conversation",
                use_container_width=True,
                key="v2_setup_delete_conversation",
            ):
                st.session_state.pending_delete_session_id = st.session_state.session_id
                st.rerun()
            if st.session_state.pending_delete_session_id == st.session_state.session_id:
                st.warning("Delete this conversation and all stored messages?")
                confirm_col, cancel_col = st.columns(2)
                if confirm_col.button(
                    "Delete",
                    type="primary",
                    use_container_width=True,
                    key="v2_setup_confirm_delete_conversation",
                ):
                    delete_current_conversation()
                    st.rerun()
                if cancel_col.button(
                    "Keep it",
                    use_container_width=True,
                    key="v2_setup_cancel_delete_conversation",
                ):
                    st.session_state.pending_delete_session_id = None
                    st.rerun()
    return {
        "mode": mode,
        "scenario_slug": scenario_slug,
        "persona_slug": persona_slug,
        "scenario_name": None,
        "persona_name": persona_name,
        "roleplay_intensity": roleplay_intensity,
        "roleplay_difficulty": roleplay_difficulty,
        "character_description": character_description,
    }


def choose_new_chat_mode(mode_label: str) -> None:
    st.session_state.mode = mode_label
    st.session_state.conversation_mode = mode_label
    st.session_state.conversation_mode_confirmed = True
    st.session_state.transition_label = None
    st.session_state.mobile_conversation_settings_open = False


def render_new_chat_mode_gate() -> None:
    if uses_conversation_experience_v2():
        st.markdown('<span class="dilse-v2-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            """<section class="new-chat-mode-intro">
            <span class="mode-kicker">Start from what you need</span>
            <h1>What would help right now?</h1>
            <p>Choose one. The conversation opens immediately, and other choices can wait.</p>
            </section>""",
            unsafe_allow_html=True,
        )
        with st.container(key="new_chat_mode_choices"):
            listener_col, partner_col = st.columns(2, gap="medium")
            with listener_col:
                st.markdown(
                    """<div class="new-chat-mode-card listener-choice">
                    <span class="mode-number">L</span>
                    <h2>I need someone to listen</h2>
                    <p>Talk through what happened, understand how you feel, or find the words for a real conversation.</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
                st.button(
                    "Talk to the Listener",
                    on_click=choose_new_chat_mode,
                    args=("The Listener",),
                    type="primary",
                    use_container_width=True,
                    key="v2_new_chat_choose_listener",
                )
            with partner_col:
                st.markdown(
                    """<div class="new-chat-mode-card partner-choice">
                    <span class="mode-number">P</span>
                    <h2>I want to practise a conversation</h2>
                    <p>Describe the person, rehearse several turns, and try different words before speaking in real life.</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
                st.button(
                    "Practise with Partner",
                    on_click=choose_new_chat_mode,
                    args=("The Partner",),
                    type="primary",
                    use_container_width=True,
                    key="v2_new_chat_choose_partner",
                )
        return
    st.markdown(
        """<section class="new-chat-mode-intro">
        <span class="mode-kicker">New conversation</span>
        <h1>How should DilSe respond?</h1>
        <p>Choose the kind of conversation you need.<span class="mode-opening-detail"> Your chat opens as soon as you select a mode.</span></p>
        </section>""",
        unsafe_allow_html=True,
    )
    with st.container(key="new_chat_mode_choices"):
        listener_col, partner_col = st.columns(2, gap="medium")
        with listener_col:
            st.markdown(
                """<div class="new-chat-mode-card listener-choice">
                <span class="mode-number">L</span>
                <h2>The Listener</h2>
                <p>Talk something through, understand what happened, or find the words for a difficult conversation.</p>
                </div>""",
                unsafe_allow_html=True,
            )
            st.button(
                "Start with Listener",
                on_click=choose_new_chat_mode,
                args=("The Listener",),
                type="primary",
                use_container_width=True,
                key="new_chat_choose_listener",
            )
        with partner_col:
            st.markdown(
                """<div class="new-chat-mode-card partner-choice">
                <span class="mode-number">P</span>
                <h2>The Partner</h2>
                <p>Practise with a husband, partner, relative, or another person before the real conversation.</p>
                </div>""",
                unsafe_allow_html=True,
            )
            st.button(
                "Start Partner roleplay",
                on_click=choose_new_chat_mode,
                args=("The Partner",),
                type="primary",
                use_container_width=True,
                key="new_chat_choose_partner",
            )
    st.markdown(
        '<p class="new-chat-mode-note">You can start a different mode later without losing this conversation.</p>',
        unsafe_allow_html=True,
    )


def render_v2_conversation_outcomes(
    mode: str,
    scenario_slug: str | None,
    persona_slug: str | None,
    roleplay_intensity: str | None,
    character_description: str | None,
    roleplay_difficulty: str | None,
    latest_message_id: int | None,
) -> None:
    user_turns = sum(
        1 for item in st.session_state.messages if item.get("role") == "user"
    )
    if user_turns < 2:
        return
    st.markdown(
        '<div class="v2-outcome-panel"><strong>Turn this conversation into something useful</strong><span>Choose one, or keep writing normally.</span></div>',
        unsafe_allow_html=True,
    )
    action_key = latest_message_id or len(st.session_state.messages)
    action_prompts = [
        (
            "Create a message I can send",
            "Based only on what I have told you, write one concise message I could send. Match my language and tone. Do not add facts.",
        ),
        (
            "Give me 3 ways to say it",
            "Give me three short ways to express my main point: gentle, direct, and firm. Preserve my meaning and language register.",
        ),
        (
            "Make the practice harder" if mode == "partner" else "Give me one next step",
            (
                "Stay in character and respond with one believable, more resistant concern so I can practise answering it. Do not become abusive or resolve the issue for me."
                if mode == "partner"
                else "Give me one practical next step based on this conversation, followed by one sentence I could use."
            ),
        ),
    ]
    with st.container(
        key="v2_outcome_actions",
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
        gap="small",
    ):
        for index, (label, prompt) in enumerate(action_prompts):
            if st.button(label, key=f"v2_outcome_{action_key}_{index}"):
                with st.spinner("DilSe is preparing this…"):
                    send_chat(
                        prompt,
                        mode,
                        scenario_slug,
                        persona_slug,
                        roleplay_intensity,
                        character_description,
                        "resistant" if mode == "partner" and index == 2 else roleplay_difficulty,
                    )
                st.rerun()

    readiness_saved = dict(st.session_state.get("v2_readiness_saved") or {})
    if readiness_saved.get(st.session_state.session_id):
        st.caption("Your readiness check was saved. This conversation is already in My conversations.")
        return
    st.markdown(
        '<div class="v2-readiness-question">Do you feel more ready for the real conversation?</div>',
        unsafe_allow_html=True,
    )
    with st.container(
        key="v2_readiness_actions",
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
        gap="small",
    ):
        readiness_options = (
            ("Yes", "yes"),
            ("A little", "a_little"),
            ("Not yet", "not_yet"),
        )
        for label, value in readiness_options:
            if st.button(label, key=f"v2_readiness_{action_key}_{value}"):
                response = request_api(
                    "POST",
                    f"/sessions/{st.session_state.session_id}/readiness",
                    {"readiness": value},
                    auth=True,
                )
                if response.status_code == 201:
                    readiness_saved[st.session_state.session_id] = value
                    st.session_state.v2_readiness_saved = readiness_saved
                    st.toast("Readiness check saved")
                    st.rerun()
                else:
                    st.error(error_detail(response))


def render_talk(
    catalog: dict[str, list[dict[str, Any]]],
    setup_container: Any | None = None,
) -> None:
    experience_v2 = uses_conversation_experience_v2()
    if experience_v2:
        st.markdown('<span class="dilse-v2-marker"></span>', unsafe_allow_html=True)
    if not st.session_state.messages and not st.session_state.conversation_mode_confirmed:
        render_new_chat_mode_gate()
        return

    display_mode = str(
        st.session_state.get("conversation_mode") or st.session_state.mode
    )
    first_user_message = next(
        (item["content"] for item in st.session_state.messages if item.get("role") == "user"),
        "New chat",
    )
    conversation_title = " ".join(str(first_user_message).split())
    if len(conversation_title) > 72:
        conversation_title = f"{conversation_title[:69].rstrip()}…"
    st.markdown(
        f'<div class="chat-surface-header"><div><strong>{html.escape(conversation_title)}</strong><span>{"Roleplay conversation" if display_mode == "The Partner" else "Private reflection and guidance"}</span></div><span class="chat-mode-pill">{html.escape(display_mode)}</span></div>',
        unsafe_allow_html=True,
    )
    render_mobile_conversation_controls(catalog)

    setup_renderer = (
        render_conversation_setup_v2 if experience_v2 else render_conversation_setup
    )
    if setup_container is None:
        settings = setup_renderer(catalog)
    else:
        with setup_container:
            settings = setup_renderer(catalog)

    mode = str(settings["mode"])
    scenario_slug = settings["scenario_slug"]
    persona_slug = settings["persona_slug"]
    roleplay_intensity = settings["roleplay_intensity"]
    roleplay_difficulty = settings["roleplay_difficulty"]
    character_description = settings["character_description"]
    persona_name = settings.get("persona_name")
    partner_persona_required = bool(
        experience_v2
        and mode == "partner"
        and not st.session_state.messages
        and not persona_slug
    )
    partner_profile_required = bool(
        mode == "partner"
        and not st.session_state.messages
        and not partner_persona_required
        and (
            not character_description
            or len(str(character_description)) < CHARACTER_PROFILE_MIN_LENGTH
            or character_profile_word_count(str(character_description))
            > CHARACTER_PROFILE_MAX_WORDS
        )
    )

    if not st.session_state.messages and not st.session_state.transition_label:
        display_name = html.escape(str(st.session_state.user.get("display_name") or "there"))
        if mode == "partner":
            if partner_persona_required:
                st.markdown(
                    '<section class="v2-persona-intro"><span>First, choose the person</span><h2>Who should DilSe be?</h2><p>You will describe how this person normally speaks and reacts in the next step.</p></section>',
                    unsafe_allow_html=True,
                )
                with st.container(
                    key="v2_persona_choices",
                    horizontal=True,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    gap="small",
                ):
                    for persona_option in catalog.get("personas", []):
                        st.button(
                            str(persona_option["name"]),
                            on_click=choose_v2_partner_persona,
                            args=(str(persona_option["slug"]), str(persona_option["name"])),
                            key=f"v2_persona_{persona_option['slug']}",
                        )
            elif partner_profile_required:
                profile_copy = character_profile_guidance(
                    str(persona_slug or ""), str(persona_name or "this person")
                )
                profile_question = (
                    "Describe how they normally speak, react to discomfort, and show care. Add what happened before this conversation and how realistic or challenging you want the practice to feel."
                    if experience_v2
                    else profile_copy["question"]
                )
                st.markdown(
                    f'<section class="chat-empty partner-empty profile-capture-empty"><div class="empty-mark-dilse">D</div><div><span class="heartline">Before the roleplay</span><h1>Tell me about {html.escape(profile_copy["relationship"])}</h1><p>{html.escape(profile_question)}</p><small>Your answer becomes the character sketch for this conversation.</small></div></section>',
                    unsafe_allow_html=True,
                )
            else:
                roleplay_name = html.escape(str(persona_name or "your partner"))
                st.markdown(
                    f'<section class="chat-empty partner-empty"><div class="empty-mark-dilse">D</div><div><span class="heartline">Partner mode · Explicit by default</span><h1>Say the first line to {roleplay_name}</h1><p>DilSe will use the character sketch and situation selected in Settings to reply more like the person you know.</p><small>Try: “I want to tell you what I need tonight.”</small></div></section>',
                    unsafe_allow_html=True,
                )
        else:
            if experience_v2:
                st.markdown(
                    f'<section class="chat-empty"><div class="empty-mark-dilse">D</div><div><span class="heartline">The Listener</span><h1>Aaj kis baat ne aapko sab se zyada disturb kiya?</h1><p>Write naturally. DilSe will understand what happened before offering advice.</p></div></section>',
                    unsafe_allow_html=True,
                )
                starter_options = (
                    ("I need to talk", "I need you to listen while I explain what has been happening."),
                    ("Help me find the words", "I need help preparing what I want to say in a difficult conversation."),
                    ("Help me understand", "I want to understand what happened before I decide what it means."),
                )
            else:
                st.markdown(
                    f'<section class="chat-empty"><div class="empty-mark-dilse">D</div><div><span class="heartline">The Listener</span><h1>What is on your mind, {display_name}?</h1><p>Write as you would speak. DilSe will listen before offering perspective.</p></div></section>',
                    unsafe_allow_html=True,
                )
                starter_options = (
                    ("Help me understand", "I need help understanding what happened before I decide what it means."),
                    ("Help me find the words", "Help me prepare what I want to say in a difficult conversation."),
                    ("Just listen", "I need space to talk this through before receiving advice."),
                )
            with st.container(
                key="listener_suggestions",
                horizontal=True,
                horizontal_alignment="center",
                vertical_alignment="center",
                gap="small",
            ):
                for label, starter in starter_options:
                    st.button(
                        label,
                        on_click=begin_with_intent,
                        args=("The Listener", starter),
                        use_container_width=True,
                        key=f"starter_{label}",
                    )
    if st.session_state.transition_label:
        st.info(st.session_state.transition_label)

    watch_live_session()

    if st.session_state.messages:
        with st.container(
            height=520,
            border=False,
            key="user_chat_transcript",
        ):
            for item in st.session_state.messages:
                message_avatar = (
                    str(CHAT_AVATAR_PATH)
                    if item["role"] == "assistant"
                    else ":material/person:"
                )
                with st.chat_message(item["role"], avatar=message_avatar):
                    if item.get("role") == "assistant" and item.get("message_id"):
                        st.markdown(
                            f'<span class="dilse-read-marker" data-dilse-read-message-id="{int(item["message_id"])}" aria-hidden="true"></span>',
                            unsafe_allow_html=True,
                        )
                    reply_markup = message_reply_markup(item, viewer="user")
                    if reply_markup:
                        st.markdown(reply_markup, unsafe_allow_html=True)
                    if item.get("error"):
                        st.error(item["content"])
                    else:
                        render_message_body(item, viewer="user")
                        if item.get("notice"):
                            st.caption("Delivery status")
                    if item.get("message_id") and not item.get("error") and not item.get("notice"):
                        if st.button(
                            "↩ Reply",
                            help="Reply to this message",
                            key=f"user_reply_message_{item['message_id']}",
                        ):
                            st.session_state.user_reply_to = reply_target_snapshot(
                                item, str(st.session_state.session_id)
                            )
                            st.rerun()

            follow_latest_chat_message(
                "user",
                str(st.session_state.session_id),
                st.session_state.messages,
            )

    latest_assistant = next(
        (item for item in reversed(st.session_state.messages) if item.get("role") == "assistant" and not item.get("error")),
        None,
    )
    if latest_assistant:
        with st.expander("Response options"):
            st.caption("Adjust only the latest reply")
            shorter_col, direct_col, voice_col = st.columns(3)
            refinement: str | None = None
            if shorter_col.button("Shorter", use_container_width=True, key="refine_shorter"):
                refinement = "Rewrite your last response more briefly. Preserve every fact, the current mode, and my language register."
            if direct_col.button("More direct", use_container_width=True, key="refine_direct"):
                refinement = "Rewrite your last response more directly without becoming harsher or changing the facts."
            voice_label = "Sound like me" if mode == "listener" else "More natural"
            if voice_col.button(voice_label, use_container_width=True, key="refine_voice"):
                refinement = (
                    "Rewrite your last response in words I could naturally say, matching my language and aap or tum register."
                    if mode == "listener"
                    else "Rewrite the last character response as shorter, more natural spoken dialogue while preserving the character and facts."
                )
            if refinement:
                with st.spinner("DilSe is adjusting the response…"):
                    send_chat(
                        refinement,
                        mode,
                        scenario_slug,
                        persona_slug,
                        roleplay_intensity,
                        character_description,
                        roleplay_difficulty,
                    )
                st.rerun()

            if latest_assistant.get("message_id"):
                st.divider()
                st.caption("Report what did not fit")
                with st.form(f"message_feedback_{latest_assistant['message_id']}"):
                    category_label = st.selectbox(
                        "What was off?",
                        ["Wrong facts", "Too conclusive", "Wrong language", "Too long", "Wrong tone", "Not my voice"],
                    )
                    feedback_note = st.text_input("Optional detail")
                    save_feedback = st.form_submit_button("Save feedback")
                if save_feedback:
                    category_map = {
                        "Wrong facts": "wrong_facts",
                        "Too conclusive": "too_conclusive",
                        "Wrong language": "wrong_language",
                        "Too long": "too_long",
                        "Wrong tone": "wrong_tone",
                        "Not my voice": "not_my_voice",
                    }
                    response = request_api(
                        "POST",
                        f"/messages/{latest_assistant['message_id']}/feedback",
                        {"category": category_map[category_label], "notes": feedback_note or None},
                        auth=True,
                    )
                    if response.status_code == 201:
                        st.success("Feedback saved for review.")
                    else:
                        st.error(error_detail(response))

    if experience_v2 and latest_assistant:
        render_v2_conversation_outcomes(
            mode,
            scenario_slug,
            persona_slug,
            roleplay_intensity,
            character_description,
            roleplay_difficulty,
            int(latest_assistant.get("message_id") or 0) or None,
        )

    checkpoint = st.session_state.conversation_checkpoint
    if experience_v2 and not checkpoint and st.session_state.messages:
        try:
            memory_response = request_api(
                "GET",
                f"/sessions/{st.session_state.session_id}/state",
                auth=True,
                timeout=8,
            )
            if memory_response.status_code == 200:
                checkpoint = memory_response.json()
        except requests.RequestException:
            checkpoint = None
    if checkpoint:
        with st.expander("Review what DilSe remembers", expanded=False):
            st.caption("Open this only when you want to check or correct the conversation memory.")
            with st.form(f"checkpoint_{checkpoint['turn_count']}"):
                confirmed_summary = st.text_area(
                    "What DilSe remembers",
                    value=str(checkpoint["summary"]),
                    height=150,
                )
                confirm_summary = st.form_submit_button("Save memory", type="primary")
            if confirm_summary:
                response = request_api(
                    "PUT",
                    f"/sessions/{st.session_state.session_id}/state",
                    {"summary": confirmed_summary},
                    auth=True,
                )
                if response.status_code == 200:
                    st.session_state.conversation_checkpoint = None
                    st.success("Conversation memory updated.")
                    st.rerun()
                else:
                    st.error(error_detail(response))

    if st.session_state.pending_prompt:
        pending = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        with st.spinner("DilSe is preparing the exercise…"):
            send_chat(pending, "listener", None, None)
        st.rerun()

    selected_reply = st.session_state.get("user_reply_to") or {}
    selected_reply_exists = any(
        int(item.get("message_id") or -1) == int(selected_reply.get("message_id") or -2)
        for item in st.session_state.messages
    )
    if (
        selected_reply.get("session_id") == st.session_state.session_id
        and selected_reply_exists
    ):
        selected_reply_markup = message_reply_markup(
            {
                "reply_to_message_id": selected_reply.get("message_id"),
                "reply_to_role": selected_reply.get("role"),
                "reply_to_content": selected_reply.get("content"),
                "reply_to_source": selected_reply.get("source"),
            },
            viewer="user",
        )
        with st.container(key="user_reply_composer"):
            reply_copy, cancel_reply = st.columns([9, 1])
            with reply_copy:
                st.markdown(selected_reply_markup, unsafe_allow_html=True)
            with cancel_reply:
                if st.button(
                    "×",
                    help="Cancel reply",
                    key=f"cancel_user_reply_{selected_reply.get('message_id')}",
                ):
                    st.session_state.user_reply_to = None
                    st.rerun()
    elif selected_reply:
        st.session_state.user_reply_to = None

    if not partner_profile_required:
        with st.container(key="user_voice_note_composer"):
            with st.popover(
                "Voice note",
                icon=":material/mic:",
                help="Record a private voice note for this conversation",
            ):
                st.caption(
                    "Record up to three minutes. Stop and play the preview before sending. "
                    "The voice note stays inside your stored conversation."
                )
                voice_recording = st.audio_input(
                    "Record voice note",
                    key=f"user_voice_note_{st.session_state.session_id}",
                )
                if voice_recording is not None:
                    voice_reply_to_message_id = (
                        int(selected_reply["message_id"])
                        if selected_reply.get("session_id") == st.session_state.session_id
                        and selected_reply_exists
                        and selected_reply.get("message_id")
                        else None
                    )
                    if st.button(
                        "Send voice note",
                        type="primary",
                        use_container_width=True,
                        key=f"send_voice_note_{st.session_state.session_id}",
                    ):
                        with st.spinner("Sending voice note…"):
                            sent = send_user_voice_note(
                                voice_recording,
                                mode,
                                scenario_slug,
                                persona_slug,
                                roleplay_intensity,
                                character_description,
                                roleplay_difficulty,
                                voice_reply_to_message_id,
                            )
                        if sent:
                            st.rerun()

    if partner_persona_required:
        prompt = None
    elif partner_profile_required:
        profile_copy = character_profile_guidance(
            str(persona_slug or ""), str(persona_name or "this person")
        )
        relationship = profile_copy["relationship"]
        prompt = st.chat_input(
            f"Describe {relationship}…",
            key="partner_profile_chat_input",
            max_chars=CHARACTER_PROFILE_MAX_CHARS,
        )
    else:
        prompt_placeholder = (
            f"Say something to {persona_name or 'the character'}…"
            if mode == "partner"
            else "Message DilSe…"
        )
        prompt = st.chat_input(prompt_placeholder, key="conversation_chat_input")
    # Do not mount the typing/read-receipt component beside Streamlit's chat
    # input. Component callbacks can trigger a fragment rerun while the chat
    # form is submitting, which discards the user's message before send_chat()
    # receives it. Reliable message delivery takes precedence over these
    # presence indicators until they are moved to a transport that does not
    # rerun the Streamlit app.
    if prompt and partner_profile_required:
        captured_profile = str(prompt).strip()
        if len(captured_profile) < CHARACTER_PROFILE_MIN_LENGTH:
            st.warning("Add a few more details about how this person speaks or reacts.")
        elif character_profile_word_count(captured_profile) > CHARACTER_PROFILE_MAX_WORDS:
            st.warning(
                f"Keep the character description to {CHARACTER_PROFILE_MAX_WORDS:,} words or fewer."
            )
        else:
            st.session_state.character_description = captured_profile
            st.session_state.partner_profile_editor_sync = True
            st.session_state.mobile_conversation_settings_open = False
            st.toast("Character sketch saved. Start the conversation when you are ready.")
            st.rerun()
    elif prompt:
        reply_to_message_id = (
            int(selected_reply["message_id"])
            if selected_reply.get("session_id") == st.session_state.session_id
            and selected_reply_exists
            and selected_reply.get("message_id")
            else None
        )
        with st.spinner("Replying in character…" if mode == "partner" else "DilSe is listening…"):
            send_chat(
                prompt,
                mode,
                scenario_slug,
                persona_slug,
                roleplay_intensity,
                character_description,
                roleplay_difficulty,
                reply_to_message_id,
            )
        st.session_state.mobile_conversation_settings_open = False
        st.rerun()

    if mode == "partner" and len(st.session_state.messages) >= 2:
        st.divider()
        feedback_col, rating_col = st.columns([1, 1])
        with feedback_col:
            if st.button("End practice and get feedback", type="primary"):
                history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages if not item.get("error")]
                with st.spinner("Reviewing the practice…"):
                    try:
                        response = request_api(
                            "POST",
                            "/roleplay/feedback/generate",
                            {"session_id": st.session_state.session_id, "history": history[-20:]},
                            auth=True,
                        )
                        if response.status_code == 200:
                            st.session_state.last_feedback = response.json()["feedback"]
                        else:
                            st.error(error_detail(response))
                    except requests.RequestException:
                        st.error("Feedback could not reach the API.")
        if st.session_state.last_feedback:
            st.markdown("### Practice feedback")
            st.markdown(st.session_state.last_feedback)
            with rating_col:
                with st.form("feedback_rating"):
                    rating = st.slider("Usefulness", 1, 5, 4)
                    helpful = st.checkbox("This helped me prepare", value=True)
                    notes = st.text_input("Optional note")
                    submitted = st.form_submit_button("Save rating")
                if submitted:
                    response = request_api(
                        "POST",
                        "/roleplay/feedback/rate",
                        {"session_id": st.session_state.session_id, "rating": rating, "helpful": helpful, "notes": notes or None},
                        auth=True,
                    )
                    if response.status_code == 201:
                        st.success("Rating saved.")
                    else:
                        st.error(error_detail(response))


def render_exercises(catalog: dict[str, list[dict[str, Any]]]) -> None:
    dashboard_header(
        "Practice library",
        "Prepare at your own pace",
        "Choose a guided exercise or draw one question. Each activity opens in a new Listener conversation.",
    )
    exercises = catalog.get("exercises", [])
    guided_tab, card_tab = st.tabs(["Guided exercises", "Conversation card"])
    with guided_tab:
        if not exercises:
            dashboard_empty(
                "No exercises are available",
                "The practice library could not be loaded. Refresh the page or start a regular conversation.",
                "○",
            )
            st.button(
                "Start a conversation",
                on_click=set_main_page,
                args=("Talk",),
                type="primary",
                key="empty_exercises_chat",
            )
        for index in range(0, len(exercises), 2):
            columns = st.columns(2)
            for offset, (column, exercise) in enumerate(zip(columns, exercises[index:index + 2])):
                name = str(exercise["name"])
                description = str(exercise["description"])
                starter = str(exercise["starter"])
                with column:
                    with st.container(border=True):
                        st.markdown('<span class="exercise-card-marker"></span>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="exercise-copy"><span class="exercise-symbol">{index + offset + 1}</span><h3>{html.escape(name)}</h3><p>{html.escape(description)}</p></div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander("What you will do"):
                            st.write(starter)
                        st.button(
                            "Begin exercise",
                            key=f"exercise_{exercise['slug']}",
                            on_click=start_exercise(
                                f"Please guide me through this exercise: {name}. {starter}"
                            ),
                            type="primary",
                            use_container_width=True,
                        )

    with card_tab:
        section_header(
            "One question",
            "Draw a conversation card",
            "Answer privately or bring the question to your partner. Draw again if the question does not fit today.",
        )
        cards = catalog.get("cards", [])
        if not cards:
            dashboard_empty(
                "No cards are available",
                "Start a regular conversation and ask DilSe for one question to think about.",
                "?",
            )
        else:
            if "current_card" not in st.session_state or st.session_state.current_card not in cards:
                st.session_state.current_card = random.choice(cards)
            card = st.session_state.current_card
            st.markdown(
                f'<article class="prompt-card"><div class="prompt-label">{html.escape(str(card["name"]))}</div><h3>{html.escape(str(card["starter"]))}</h3></article>',
                unsafe_allow_html=True,
            )
            draw_col, talk_col = st.columns([1, 1.7])
            if draw_col.button("Draw another", use_container_width=True, key="draw_card"):
                alternatives = [item for item in cards if item != card]
                st.session_state.current_card = random.choice(alternatives or cards)
                st.rerun()
            talk_col.button(
                "Talk this through with DilSe",
                on_click=start_exercise(
                    f"Please help me think through this conversation card: {card['starter']}"
                ),
                type="primary",
                use_container_width=True,
                key="start_card_chat",
            )


def render_usage() -> None:
    brand_header(
        "Visible by design",
        "Your usage",
        "Token counts show how much text the model processed. DilSe does not estimate cost because AI-provider prices and account terms can change.",
    )
    try:
        response = request_api("GET", "/usage/me", auth=True, timeout=10)
        response.raise_for_status()
        usage = response.json()
    except requests.RequestException:
        st.error("Usage data is unavailable.")
        return
    columns = st.columns(4)
    values = [
        ("Conversations", usage["sessions"]),
        ("Stored messages", usage["messages"]),
        ("Input tokens", usage["prompt_tokens"]),
        ("Output tokens", usage["completion_tokens"]),
    ]
    for column, (label, value) in zip(columns, values):
        with column:
            st.markdown(f'<div class="quiet-card"><div class="metric-label">{label}</div><div class="metric-value">{value:,}</div></div>', unsafe_allow_html=True)


def render_conversations() -> None:
    dashboard_header(
        "Conversation history",
        "Pick up where you left off",
        "Search your stored conversations, open one, or remove a conversation you no longer want to keep.",
    )
    if not st.session_state.user.get("store_chats"):
        dashboard_empty(
            "Conversation history is off",
            "Turn on conversation storage in Privacy if you want to return to past chats.",
            "○",
        )
        privacy_col, chat_col = st.columns(2)
        privacy_col.button(
            "Review privacy settings",
            on_click=set_main_page,
            args=("Privacy",),
            use_container_width=True,
            key="history_open_privacy",
        )
        chat_col.button(
            "Start a private chat",
            on_click=reset_local_conversation,
            type="primary",
            use_container_width=True,
            key="history_start_unstored_chat",
        )
        return
    try:
        response = request_api("GET", "/sessions", auth=True, timeout=15)
        response.raise_for_status()
        sessions = response.json()
    except requests.RequestException:
        dashboard_empty(
            "Conversations could not be loaded",
            "Check your connection and try again. Your stored conversations have not been removed.",
            "!",
        )
        if st.button("Try again", type="primary", key="retry_conversation_history"):
            st.rerun()
        return
    if not sessions:
        dashboard_empty(
            "No conversations yet",
            "Start with whatever feels hardest to say. Your saved conversations will appear here.",
        )
        st.button(
            "Start your first conversation",
            on_click=reset_local_conversation,
            type="primary",
            use_container_width=True,
            key="history_start_first_chat",
        )
        return
    search = st.text_input(
        "Search conversations",
        placeholder="Type words from the conversation",
        key="conversation_search",
    )
    lowered_search = search.strip().lower()
    visible_sessions = [
        item for item in sessions
        if not lowered_search or lowered_search in str(item.get("first_user_message") or "").lower()
    ]
    st.caption(f"{len(visible_sessions)} of {len(sessions)} conversations")
    if not visible_sessions:
        dashboard_empty(
            "No matching conversations",
            "Try a different word from the opening message.",
            "?",
        )
        return

    for session in visible_sessions:
        opening = " ".join(str(session.get("first_user_message") or "Conversation").split())
        if len(opening) > 180:
            opening = f"{opening[:177].rstrip()}…"
        mode_label = "The Partner" if session.get("mode") == "partner" else "The Listener"
        activity = format_session_activity(session.get("last_activity"))
        message_count = int(session.get("message_count") or 0)
        session_id = str(session["session_id"])
        with st.container(border=True):
            st.markdown('<span class="conversation-row-marker"></span>', unsafe_allow_html=True)
            copy_col, action_col = st.columns([4.2, 1.25], vertical_alignment="center")
            with copy_col:
                st.markdown(
                    f'<div class="conversation-row-copy"><h3>{html.escape(opening)}</h3><p><span class="conversation-mode-chip">{html.escape(mode_label)}</span>{html.escape(activity)} · {message_count} {"message" if message_count == 1 else "messages"}</p></div>',
                    unsafe_allow_html=True,
                )
            with action_col:
                if st.button(
                    "Open chat",
                    key=f"resume_session_{session_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    load_saved_conversation(session)
                    st.rerun()
                if st.button(
                    "Remove",
                    key=f"delete_saved_{session_id}",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_session_id = session_id
                    st.rerun()

            if st.session_state.pending_delete_session_id == session_id:
                st.warning("Remove this conversation and all of its stored messages?")
                confirm_col, cancel_col, spacer_col = st.columns([1.35, 1, 3])
                if confirm_col.button(
                    "Remove permanently",
                    key=f"confirm_delete_saved_{session_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    delete_response = request_api(
                        "DELETE", f"/sessions/{session_id}", auth=True, timeout=10
                    )
                    if delete_response.status_code == 204:
                        if st.session_state.session_id == session_id:
                            reset_local_conversation()
                            st.session_state.page = "My conversations"
                            st.session_state.main_navigation = "My conversations"
                        st.session_state.pending_delete_session_id = None
                        st.toast("Conversation removed")
                        st.rerun()
                    else:
                        st.error(error_detail(delete_response))
                if cancel_col.button(
                    "Keep it",
                    key=f"cancel_delete_saved_{session_id}",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_session_id = None
                    st.rerun()


def render_privacy() -> None:
    user = st.session_state.user
    dashboard_header(
        "Privacy and data",
        "How DilSe handles conversations",
        "Choose how long stored conversations remain available in your account.",
    )
    retention_days = max(int(user.get("retention_days") or 7), 7)
    st.markdown(
        f'<div class="settings-summary"><div><span>Conversation history</span><strong>Stored</strong></div><div><span>Retention</span><strong>{retention_days} days</strong></div></div>',
        unsafe_allow_html=True,
    )
    privacy_defaults = {"privacy_retention": retention_days}
    for key, value in privacy_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.markdown(
        '<div class="settings-group"><h2>Conversation retention</h2><p>Select how long stored conversations remain available before automatic deletion.</p></div>',
        unsafe_allow_html=True,
    )
    retention = st.select_slider(
        "Keep conversations for",
        options=[7, 30, 90, 180, 365],
        key="privacy_retention",
        format_func=lambda days: f"{days} days",
    )
    st.caption("You can permanently delete an individual conversation at any time from My conversations.")
    st.session_state.privacy_admin_intervention = True

    submitted = st.button(
        "Save data settings",
        type="primary",
        use_container_width=True,
        key="save_privacy_choices",
    )
    if submitted:
        try:
            response = request_api(
                "PUT",
                "/account/privacy",
                {
                    "language": user["language"],
                    "country": user.get("country", "Other / not specified"),
                    "retention_days": retention,
                    "store_chats": True,
                    "allow_admin_review": True,
                    "allow_admin_intervention": True,
                },
                auth=True,
            )
            if response.status_code == 200:
                st.session_state.user = response.json()
                st.toast("Data settings saved")
                st.rerun()
            else:
                st.error(error_detail(response))
        except requests.RequestException:
            st.error("Privacy choices could not be saved. Check your connection and try again.")


def render_phone_alert_settings() -> None:
    st.markdown(
        '<div class="settings-group"><h2>Phone response alerts</h2><p>Let Android use its normal notification sound when a DilSe response arrives while this website is in the background.</p></div>',
        unsafe_allow_html=True,
    )
    try:
        response = request_api("GET", "/account/push/config", auth=True, timeout=10)
    except requests.RequestException:
        st.info("Phone alert settings could not be loaded. Email reminders will continue.")
        return
    if response.status_code != 200:
        st.info("Phone alerts are being prepared. Email reminders will continue.")
        return
    config = response.json()
    if not config.get("available") or not config.get("public_key"):
        st.info("Phone alerts are being prepared. Email reminders will continue.")
        return

    with st.container(key="phone_alerts_widget"):
        event = phone_alerts_component(
            public_key=str(config["public_key"]),
            sw_url="/component/app.dilse_phone_alerts/push-sw.js",
            default=None,
            key=f"phone_alerts_{st.session_state.user['id']}",
            tab_index=0,
        )
    if not isinstance(event, dict) or not event.get("event_id"):
        st.caption(
            "Chrome controls the sound and may group notifications. DilSe never includes conversation text in a phone alert."
        )
        return
    event_id = str(event["event_id"])
    if st.session_state.phone_alert_event_id == event_id:
        return
    st.session_state.phone_alert_event_id = event_id

    action = str(event.get("action") or "")
    try:
        if action == "subscribe":
            subscription = event.get("subscription") or {}
            keys = subscription.get("keys") or {}
            save_response = request_api(
                "POST",
                "/account/push/subscriptions",
                {
                    "endpoint": str(subscription.get("endpoint") or ""),
                    "p256dh": str(keys.get("p256dh") or ""),
                    "auth": str(keys.get("auth") or ""),
                },
                auth=True,
                timeout=15,
            )
            if save_response.status_code == 201:
                st.toast("Phone alerts enabled for this browser")
            else:
                st.error(error_detail(save_response))
        elif action == "unsubscribe":
            remove_response = request_api(
                "POST",
                "/account/push/unsubscribe",
                {"endpoint": str(event.get("endpoint") or "")},
                auth=True,
                timeout=15,
            )
            if remove_response.status_code == 200:
                st.toast("Phone alerts turned off for this browser")
            else:
                st.error(error_detail(remove_response))
    except requests.RequestException:
        st.error("Phone alert settings could not be saved. Check your connection and try again.")
    st.caption(
        "Chrome controls the sound and may group notifications. DilSe never includes conversation text in a phone alert."
    )


def render_account() -> None:
    user = st.session_state.user
    dashboard_header(
        "Your account",
        "Profile and sign-in",
        "Review your account details, choose how DilSe speaks with you, or sign out from this browser.",
    )
    st.markdown(
        f'<div class="account-identity"><strong>{html.escape(str(user["display_name"]))}</strong><span>{html.escape(str(user["email"]))}</span></div>',
        unsafe_allow_html=True,
    )
    st.button(
        "Privacy and data controls",
        on_click=set_main_page,
        args=("Privacy",),
        use_container_width=True,
        key="account_open_privacy",
    )

    countries = ["Pakistan"]
    languages = [
        "English",
        "Urdu",
        "Roman Urdu",
        "English and Urdu",
    ]
    current_country = user.get("country", "Pakistan")
    if current_country not in countries:
        current_country = "Pakistan"
    current_language = user.get("language", "English")
    if current_language not in languages:
        current_language = "English"
    if "account_country" not in st.session_state:
        st.session_state.account_country = current_country
    if "account_language" not in st.session_state:
        st.session_state.account_language = current_language

    st.markdown(
        '<div class="settings-group"><h2>Response preferences</h2><p>These choices help DilSe use suitable language and locally relevant support information.</p></div>',
        unsafe_allow_html=True,
    )
    country = st.selectbox(
        "Country for support information",
        countries,
        key="account_country",
    )
    language = st.selectbox(
        "Preferred response language",
        languages,
        key="account_language",
    )
    if st.button(
        "Save response preferences",
        type="primary",
        use_container_width=True,
        key="save_account_preferences",
    ):
        try:
            response = request_api(
                "PUT",
                "/account/privacy",
                {
                    "language": language,
                    "country": country,
                    "retention_days": int(user.get("retention_days") or 0),
                    "store_chats": bool(user.get("store_chats")),
                    "allow_admin_review": bool(user.get("allow_admin_review")),
                    "allow_admin_intervention": True,
                },
                auth=True,
            )
            if response.status_code == 200:
                st.session_state.user = response.json()
                st.toast("Response preferences saved")
                st.rerun()
            else:
                st.error(error_detail(response))
        except requests.RequestException:
            st.error("Response preferences could not be saved. Check your connection and try again.")

    if "account_email_notifications" not in st.session_state:
        st.session_state.account_email_notifications = bool(
            user.get("email_notifications_enabled", False)
        )
    st.markdown(
        '<div class="settings-group"><h2>Email notifications</h2><p>Choose whether DilSe should remind you about a response you have not opened.</p></div>',
        unsafe_allow_html=True,
    )
    email_notifications_enabled = st.toggle(
        "Email me about unread DilSe responses",
        key="account_email_notifications",
    )
    st.caption(
        "If a DilSe response remains unread, we will send one private reminder within an hour. The email will not include any conversation details."
    )
    if st.button(
        "Save email preference",
        use_container_width=True,
        key="save_email_notification_preference",
    ):
        try:
            response = request_api(
                "PUT",
                "/account/notifications",
                {"enabled": email_notifications_enabled},
                auth=True,
            )
            if response.status_code == 200:
                st.session_state.user = response.json()
                st.toast("Email preference saved")
                st.rerun()
            else:
                st.error(error_detail(response))
        except requests.RequestException:
            st.error("Email preference could not be saved. Check your connection and try again.")

    render_phone_alert_settings()

    st.markdown(
        '<div class="settings-group"><h2>Terms</h2><p>Review the current conditions covering your account, conversations, privacy, and AI processing.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<a class="settings-document-link" href="?page=terms" target="_self">Terms and Conditions</a>',
        unsafe_allow_html=True,
    )

    section_header(
        "Session",
        "This browser",
        "Signing out removes this browser's saved DilSe session. Your account and stored conversations remain.",
    )
    st.button(
        "Sign out of DilSe",
        on_click=sign_out,
        use_container_width=True,
        key="account_page_signout",
    )

    st.markdown(
        '<div class="danger-zone"><h2>Delete account</h2><p>This permanently removes your account, stored messages, consent records, and feedback. This action cannot be reversed.</p></div>',
        unsafe_allow_html=True,
    )
    with st.expander("I want to delete my account"):
        delete_password = st.text_input(
            "Enter your password",
            type="password",
            key="delete_account_password",
        )
        delete_phrase = st.text_input(
            'Type DELETE to confirm',
            key="delete_account_phrase",
        )
        delete_account = st.button(
            "Delete my account permanently",
            disabled=delete_phrase.strip() != "DELETE" or not delete_password,
            use_container_width=True,
            key="delete_account_button",
        )
    if delete_account:
        response = request_api("DELETE", "/account", {"password": delete_password}, auth=True)
        if response.status_code == 204:
            forget_browser_login()
            st.session_state.auth_token = None
            st.session_state.user = None
            reset_local_conversation()
            st.rerun()
        else:
            st.error(error_detail(response))


def set_main_page(page: str) -> None:
    st.session_state.page = page
    st.session_state.main_navigation = page
    st.session_state.mobile_conversation_settings_open = False
    st.session_state.scroll_dashboard_top = True
    st.session_state.scroll_request_id += 1


def recent_conversations(limit: int = 7) -> list[dict[str, Any]]:
    if not st.session_state.user.get("store_chats"):
        return []
    try:
        response = request_api("GET", "/sessions", auth=True, timeout=10)
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    return list(response.json())[:limit]


def render_left_rail() -> None:
    logo_uri = image_data_uri(str(LOGO_PATH), LOGO_PATH.stat().st_mtime_ns)
    st.markdown('<span class="dilse-app-shell-marker"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<img class="app-logo" src="{logo_uri}" alt="DilSe, from the heart">',
        unsafe_allow_html=True,
    )
    st.button(
        "+ New chat",
        on_click=reset_local_conversation,
        type="primary",
        use_container_width=True,
        key="rail_new_conversation",
    )

    st.markdown('<div class="rail-label">Recent conversations</div>', unsafe_allow_html=True)
    sessions = recent_conversations()
    if sessions:
        for session in sessions:
            opening = " ".join(str(session.get("first_user_message") or "Conversation").split())
            if len(opening) > 44:
                opening = f"{opening[:41].rstrip()}…"
            st.button(
                opening,
                on_click=load_saved_conversation,
                args=(session,),
                use_container_width=True,
                key=f"rail_session_{session['session_id']}",
            )
    else:
        st.caption("Your conversations will appear here.")

    st.markdown('<div class="rail-label">Your space</div>', unsafe_allow_html=True)
    navigation = (
        ("Chat", "Talk"),
        ("Practice", "Exercises"),
        ("All conversations", "My conversations"),
    )
    for label, page in navigation:
        st.button(
            label,
            on_click=set_main_page,
            args=(page,),
            type="primary" if st.session_state.page == page else "secondary",
            use_container_width=True,
            key=f"rail_page_{page}",
        )

    user = st.session_state.user
    st.markdown(
        f'<div class="rail-profile"><span>{html.escape(str(user["display_name"]))}</span><small>{html.escape(str(user["language"]))} · {html.escape(str(user.get("country") or "Country not specified"))}</small></div>',
        unsafe_allow_html=True,
    )
    st.button(
        "Settings and privacy",
        on_click=set_main_page,
        args=("Account",),
        use_container_width=True,
        key="rail_account_settings",
    )
    st.button("Sign out", on_click=sign_out, use_container_width=True, key="rail_signout")


def render_account_panel() -> None:
    user = st.session_state.user
    st.divider()
    st.markdown(
        f'<div class="rail-user"><strong>{html.escape(str(user["display_name"]))}</strong><span>{html.escape(str(user["language"]))} · {html.escape(str(user.get("country") or "Country not specified"))}</span></div>',
        unsafe_allow_html=True,
    )
    retention = max(int(user.get("retention_days") or 7), 7)
    st.markdown(
        f'<div class="setup-note"><span class="privacy-dot"></span>Conversations are stored for {retention} days.</div>',
        unsafe_allow_html=True,
    )
    st.button(
        "Privacy settings",
        on_click=set_main_page,
        args=("Privacy",),
        use_container_width=True,
        key=f"account_privacy_{st.session_state.page}",
    )
    st.button(
        "Account",
        on_click=set_main_page,
        args=("Account",),
        use_container_width=True,
        key=f"account_page_{st.session_state.page}",
    )
    st.button("Sign out", on_click=sign_out, use_container_width=True, key=f"account_signout_{st.session_state.page}")


def render_secondary_context() -> None:
    page_context = {
        "My conversations": (
            "Find your words",
            "Conversation history",
            "Open a past conversation to continue it. Removing one asks for confirmation first.",
        ),
        "Exercises": (
            "Practice gently",
            "Your practice space",
            "Exercises start a new Listener conversation. You can stop, skip, or change direction at any time.",
        ),
        "Privacy": (
            "Clear data handling",
            "Privacy and retention",
            "You can change how long conversations are retained or delete them from your account.",
        ),
        "Account": (
            "Your details",
            "Account controls",
            "Language and country shape DilSe's wording and locally relevant support information.",
        ),
    }
    kicker, title, body = page_context.get(
        st.session_state.page,
        ("Quick access", "Your DilSe space", "Return to chat whenever you are ready."),
    )
    st.markdown(
        f'<div class="setup-heading"><span>{html.escape(kicker)}</span><strong>{html.escape(title)}</strong></div><p class="context-note">{html.escape(body)}</p>',
        unsafe_allow_html=True,
    )
    st.button(
        "Back to chat",
        on_click=set_main_page,
        args=("Talk",),
        type="primary",
        use_container_width=True,
        key=f"context_back_to_chat_{st.session_state.page}",
    )
    render_account_panel()


def render_mobile_navigation() -> None:
    with st.container(
        key="mobile_dashboard_nav",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        gap="small",
    ):
        st.button(
            "Chat",
            on_click=set_main_page,
            args=("Talk",),
            type="primary" if st.session_state.page == "Talk" else "secondary",
            key="mobile_nav_talk",
        )
        st.button(
            "History",
            on_click=set_main_page,
            args=("My conversations",),
            type="primary" if st.session_state.page == "My conversations" else "secondary",
            key="mobile_nav_history",
        )
        st.button(
            "Practice",
            on_click=set_main_page,
            args=("Exercises",),
            type="primary" if st.session_state.page == "Exercises" else "secondary",
            key="mobile_nav_practice",
        )
        st.button(
            "Account",
            on_click=set_main_page,
            args=("Account",),
            type="primary" if st.session_state.page in {"Privacy", "Account"} else "secondary",
            key="mobile_nav_settings",
        )


def render_signed_in_shell(catalog: dict[str, list[dict[str, Any]]]) -> None:
    if st.session_state.scroll_dashboard_top:
        components.html(
            """<script>
            const scrollRequest = __SCROLL_REQUEST__;
            const resetDashboardScroll = () => {
                const parentDocument = window.parent.document;
                if (typeof parentDocument.activeElement?.blur === "function") {
                    parentDocument.activeElement.blur();
                }
                window.parent.scrollTo({top: 0, left: 0, behavior: "instant"});
                const main = parentDocument.querySelector('[data-testid="stMain"]');
                if (main) { main.scrollTo({top: 0, left: 0, behavior: "instant"}); }
                parentDocument.querySelectorAll('[data-testid="stColumn"]').forEach(
                    (panel) => { panel.scrollTop = 0; }
                );
            };
            resetDashboardScroll();
            window.setTimeout(resetDashboardScroll, 120);
            window.setTimeout(resetDashboardScroll, 420);
            </script>""".replace(
                "__SCROLL_REQUEST__", str(int(st.session_state.scroll_request_id))
            ),
            height=0,
            width=0,
        )
        st.session_state.scroll_dashboard_top = False
    left, centre, right = st.columns([1.05, 3.25, 1.4], gap="medium")
    with left:
        render_left_rail()

    with centre:
        render_mobile_navigation()
        if st.session_state.page == "Talk":
            render_talk(catalog, right)
        else:
            if st.session_state.page == "My conversations":
                render_conversations()
            elif st.session_state.page == "Exercises":
                render_exercises(catalog)
            elif st.session_state.page == "Privacy":
                render_privacy()
            else:
                render_account()

    with right:
        if st.session_state.page != "Talk":
            render_secondary_context()


def render_admin() -> None:
    brand_header(
        "Consent-aware operations",
        "DilSe admin",
        "Review only opted-in conversations, compare prompt versions, record corrections, and manage practice content.",
    )
    if not st.session_state.admin_key:
        with st.form("admin_login"):
            key = st.text_input("Admin API key", type="password")
            submitted = st.form_submit_button("Open admin workspace", type="primary")
        if submitted:
            st.session_state.admin_key = key
            st.rerun()
        return
    try:
        summary_response = request_api("GET", "/admin/summary", admin=True, timeout=10)
        if summary_response.status_code != 200:
            st.session_state.admin_key = None
            st.error(error_detail(summary_response))
            return
        summary = summary_response.json()
    except requests.RequestException:
        st.error("The admin workspace cannot reach the API.")
        return

    if st.button("Lock admin workspace"):
        st.session_state.admin_key = None
        st.rerun()

    metric_columns = st.columns(6)
    metrics = [
        ("Current Terms users", summary["consenting_users"]),
        ("Reviewable chats", summary["reviewable_sessions"]),
        ("Messages", summary["reviewable_messages"]),
        ("Input tokens", summary["prompt_tokens"]),
        ("Output tokens", summary["completion_tokens"]),
        ("Live access", summary.get("intervention_users", 0)),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, f"{value:,}")

    live, conversations, prompts, library, quality, audit_tab = st.tabs(
        ["Live sessions", "Conversations", "Prompts", "Library", "Quality", "Audit"]
    )
    with live:
        st.markdown(
            '<div class="handoff-ribbon"><strong>Administrator participation is included for current accounts.</strong><br>Accounts on earlier Terms appear after the user accepts the required update.</div>',
            unsafe_allow_html=True,
        )
        active_response = request_api("GET", "/admin/sessions/active?minutes=60", admin=True, timeout=20)
        active_sessions = active_response.json() if active_response.status_code == 200 else []
        if not active_sessions:
            st.info("No current account session has been active in the past hour.")
        else:
            session_labels = {
                (
                    f"{item['email']} · "
                    f"{str(item.get('conversation_mode') or 'listener').title()} · "
                    f"{item['last_activity']} · {item['control_mode']}"
                ): item
                for item in active_sessions
            }
            selected_label = st.selectbox("Active conversation", list(session_labels))
            active_session = session_labels[selected_label]
            active_session_id = active_session["session_id"]
            active_mode = str(active_session.get("conversation_mode") or "listener").title()
            mode_context = (
                f"Partner practice with {str(active_session.get('character') or 'selected character').replace('_', ' ')}"
                if active_mode == "Partner"
                else "Listener conversation"
            )
            st.caption(f"{mode_context} · human intervention is available in both modes")
            if active_session.get("character_description"):
                st.markdown("**Character profile**")
                st.write(active_session["character_description"])
            live_logs_response = request_api(
                "GET", f"/admin/logs?session_id={active_session_id}&limit=200", admin=True, timeout=20
            )
            live_logs = sorted(
                live_logs_response.json() if live_logs_response.status_code == 200 else [],
                key=lambda item: item["id"],
            )
            for item in live_logs:
                with st.chat_message(item["role"]):
                    st.markdown(item["content"])
                    source_label = "Human administrator" if item.get("source") == "admin" else item.get("source", item["role"])
                    st.caption(f"{source_label} · message {item['id']}")

            st.subheader(f"Session control · {active_mode}")
            with st.form("live_control_form"):
                control_mode = st.radio(
                    "Who responds next?",
                    ["AI", "Human administrator"],
                    index=1 if active_session["control_mode"] == "human" else 0,
                    horizontal=True,
                )
                prompt_override = st.text_area(
                    "Session-only AI guidance",
                    help="Used only for this conversation. This internal instruction is not shown in the user chat.",
                )
                clear_override = st.checkbox("Remove the existing session-only guidance")
                live_difficulty_choice = "Use user setting"
                live_intimacy_choice = "Use user setting"
                if active_mode == "Partner":
                    difficulty_options = ["Use user setting", "Supportive", "Realistic", "Resistant"]
                    current_difficulty = str(active_session.get("roleplay_difficulty_override") or "").title()
                    live_difficulty_choice = st.selectbox(
                        "Character reaction override",
                        difficulty_options,
                        index=difficulty_options.index(current_difficulty) if current_difficulty in difficulty_options else 0,
                    )
                    intimacy_options = ["Use user setting", "Romantic", "Direct", "Explicit"]
                    current_intimacy = str(active_session.get("roleplay_intensity_override") or "").title()
                    live_intimacy_choice = st.selectbox(
                        "Intimacy detail override",
                        intimacy_options,
                        index=intimacy_options.index(current_intimacy) if current_intimacy in intimacy_options else 0,
                        help="This can be changed at any point in a Partner session and applies to the next AI reply.",
                    )
                control_note = st.text_input("Reason for this change", help="Saved in the administrator audit trail.")
                update_control = st.form_submit_button("Update session control", type="primary")
            if update_control:
                result = request_api(
                    "POST",
                    f"/admin/sessions/{active_session_id}/control",
                    {
                        "mode": "human" if control_mode == "Human administrator" else "ai",
                        "prompt_override": prompt_override or None,
                        "clear_prompt_override": clear_override,
                        "roleplay_difficulty_override": (
                            live_difficulty_choice.lower() if live_difficulty_choice != "Use user setting" else None
                        ),
                        "clear_roleplay_difficulty_override": live_difficulty_choice == "Use user setting",
                        "roleplay_intensity_override": (
                            live_intimacy_choice.lower() if live_intimacy_choice != "Use user setting" else None
                        ),
                        "clear_roleplay_intensity_override": live_intimacy_choice == "Use user setting",
                        "note": control_note,
                    },
                    admin=True,
                )
                if result.status_code == 200:
                    st.success("Session control updated.")
                    st.rerun()
                else:
                    st.error(error_detail(result))

            if active_session["control_mode"] == "human":
                with st.form("human_reply_form"):
                    human_reply = st.text_area("Human response", help="The user will see a Human DilSe administrator label.")
                    send_human_reply = st.form_submit_button("Send labelled human response", type="primary")
                if send_human_reply:
                    result = request_api(
                        "POST",
                        f"/admin/sessions/{active_session_id}/messages",
                        {"content": human_reply},
                        admin=True,
                    )
                    if result.status_code == 201:
                        st.success("Human response sent.")
                        st.rerun()
                    else:
                        st.error(error_detail(result))
    with conversations:
        response = request_api("GET", "/admin/logs?limit=500", admin=True, timeout=20)
        logs = response.json() if response.status_code == 200 else []
        if not logs:
            st.info("No opted-in conversations are available for review.")
        else:
            sessions = list(dict.fromkeys(item["session_id"] for item in logs))
            selected_session = st.selectbox("Conversation", sessions)
            session_logs = sorted((item for item in logs if item["session_id"] == selected_session), key=lambda item: item["id"])
            for item in session_logs:
                with st.chat_message(item["role"]):
                    st.markdown(item["content"])
                    source_label = "Human administrator" if item.get("source") == "admin" else item.get("source", item["role"])
                    st.caption(f"Message {item['id']} · {source_label} · {item['mode']} · {item['created_at']}")
            with st.form("admin_note_form"):
                note = st.text_area("Private admin note")
                note_message_id = st.number_input("Related message ID, optional", min_value=0, step=1)
                save_note = st.form_submit_button("Save note")
            if save_note:
                result = request_api("POST", "/admin/notes", {"session_id": selected_session, "message_id": int(note_message_id) or None, "note": note}, admin=True)
                st.success("Note saved.") if result.status_code == 201 else st.error(error_detail(result))
            assistant_messages = [item for item in session_logs if item["role"] == "assistant"]
            if assistant_messages:
                with st.form("correction_form"):
                    message_id = st.selectbox("Assistant message to correct", [item["id"] for item in assistant_messages])
                    category = st.text_input("Correction category", value="cultural guidance")
                    corrected = st.text_area("Better response")
                    save_correction = st.form_submit_button("Save correction")
                if save_correction:
                    result = request_api("POST", "/admin/corrections", {"message_id": message_id, "category": category, "corrected_response": corrected}, admin=True)
                    st.success("Correction saved for prompt research.") if result.status_code == 201 else st.error(error_detail(result))
    with prompts:
        response = request_api("GET", "/admin/prompts", admin=True)
        versions = response.json() if response.status_code == 200 else []
        for version in versions:
            label = f"Version {version['id']} · {'active' if version['active'] else 'inactive'} · {version['created_at']}"
            with st.expander(label, expanded=bool(version["active"])):
                st.caption(version["note"] or "No release note")
                st.code(version["prompt"], language=None)
                if not version["active"] and st.button("Activate this version", key=f"activate_prompt_{version['id']}"):
                    result = request_api("POST", f"/admin/prompts/{version['id']}/activate", admin=True)
                    if result.status_code == 200:
                        st.rerun()
        active_prompt_text = next((item["prompt"] for item in versions if item["active"]), "")
        with st.form("new_prompt_form"):
            new_prompt = st.text_area("New prompt version", value=active_prompt_text, height=420)
            note = st.text_input("What changed?")
            activate = st.checkbox("Activate after saving", value=True)
            create_prompt = st.form_submit_button("Save prompt version", type="primary")
        if create_prompt:
            result = request_api("POST", "/admin/prompts", {"prompt": new_prompt, "note": note, "activate": activate}, admin=True)
            if result.status_code == 201:
                st.success("Prompt version saved.")
                st.rerun()
            else:
                st.error(error_detail(result))
    with library:
        kind = st.selectbox("Content type", ["personas", "scenarios", "exercises", "cards"])
        response = request_api("GET", f"/admin/catalog/{kind}", admin=True)
        items = response.json() if response.status_code == 200 else []
        st.dataframe(items, use_container_width=True, hide_index=True)
        with st.form("catalog_form"):
            slug = st.text_input("Slug", help="Lowercase letters, numbers, and underscores.")
            name = st.text_input("Name")
            description = st.text_area("Description")
            starter = st.text_area("Starter", disabled=kind == "personas")
            active = st.checkbox("Active", value=True)
            save_item = st.form_submit_button("Save library item", type="primary")
        if save_item:
            payload = {"slug": slug, "name": name, "description": description, "starter": starter or None, "active": active}
            result = request_api("POST", f"/admin/catalog/{kind}", payload, admin=True)
            st.success("Library item saved.") if result.status_code == 201 else st.error(error_detail(result))
    with quality:
        notes_response = request_api("GET", "/admin/notes", admin=True)
        corrections_response = request_api("GET", "/admin/corrections", admin=True)
        feedback_response = request_api("GET", "/admin/feedback", admin=True)
        st.subheader("Corrections")
        st.dataframe(corrections_response.json() if corrections_response.status_code == 200 else [], use_container_width=True, hide_index=True)
        st.subheader("Admin notes")
        st.dataframe(notes_response.json() if notes_response.status_code == 200 else [], use_container_width=True, hide_index=True)
        st.subheader("Roleplay feedback")
        st.dataframe(feedback_response.json() if feedback_response.status_code == 200 else [], use_container_width=True, hide_index=True)
    with audit_tab:
        response = request_api("GET", "/admin/audit", admin=True)
        st.dataframe(response.json() if response.status_code == 200 else [], use_container_width=True, hide_index=True)


def admin_json(method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 20) -> Any | None:
    try:
        response = request_api(method, path, payload, admin=True, timeout=timeout)
    except requests.RequestException:
        st.error("The administrator workspace cannot reach the API.")
        return None
    if response.status_code >= 400:
        if response.status_code == 401:
            st.session_state.admin_key = None
            st.session_state.admin_authenticated = False
        st.error(error_detail(response))
        return None
    if response.status_code == 204:
        return {}
    return response.json()


def render_admin_workspace() -> None:
    st.markdown(
        """<section class="admin-command">
        <div class="admin-eyebrow">DilSe operations · consent-aware case desk</div>
        <h1>Conversation control room</h1>
        <p>Select a user, open one session, read the conversation exactly as it appeared, then choose the smallest scope for a change: account guidance, session guidance, or a labelled human reply.</p>
        </section>""",
        unsafe_allow_html=True,
    )
    if not st.session_state.admin_key:
        left, centre, right = st.columns([1, 1.2, 1])
        with centre:
            with st.form("admin_login_v2"):
                key = st.text_input("Admin API key", type="password")
                submitted = st.form_submit_button("Open control room", type="primary", use_container_width=True)
            if submitted:
                st.session_state.admin_key = key
                st.rerun()
        return

    summary = admin_json("GET", "/admin/summary", timeout=10)
    if summary is None:
        st.session_state.admin_key = None
        return

    lock_col, rule_col = st.columns([1, 5])
    with lock_col:
        if st.button("Lock workspace", use_container_width=True):
            st.session_state.admin_key = None
            st.rerun()
    with rule_col:
        st.markdown(
            '<div class="admin-privacy-rule">Current accounts include stored administrator review and active-conversation participation. Accounts on earlier Terms must accept the update before administrator access becomes available.</div>',
            unsafe_allow_html=True,
        )

    metric_columns = st.columns(5)
    metrics = [
        ("All users", summary.get("total_users", 0)),
        ("Review available", summary.get("consenting_users", 0)),
        ("Reviewable sessions", summary.get("reviewable_sessions", 0)),
        ("Reviewable messages", summary.get("reviewable_messages", 0)),
        ("Live access included", summary.get("intervention_users", 0)),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, f"{value:,}")

    case_desk, global_prompt, quality, library, audit_tab = st.tabs(
        ["User workspace", "Global prompt", "Response quality", "Content library", "Audit"]
    )

    with case_desk:
        users = admin_json("GET", "/admin/users") or []
        if not users:
            st.info("No user accounts exist yet.")
        else:
            search_col, consent_col, country_col = st.columns([2, 1, 1])
            with search_col:
                user_search = st.text_input("Find a user", placeholder="Name or email", key="admin_user_search")
            with consent_col:
                consent_filter = st.selectbox("Conversation access", ["All accounts", "Review available", "Terms update required"])
            with country_col:
                country_options = ["All countries", *sorted({item["country"] for item in users})]
                country_filter = st.selectbox("Country", country_options)

            filtered_users = []
            for item in users:
                search_match = not user_search or user_search.lower() in f"{item['display_name']} {item['email']}".lower()
                consent_match = (
                    consent_filter == "All accounts"
                    or (consent_filter == "Review available" and item["allow_admin_review"] and item["store_chats"])
                    or (consent_filter == "Terms update required" and item.get("terms_version") != CURRENT_TERMS_VERSION)
                )
                country_match = country_filter == "All countries" or item["country"] == country_filter
                if search_match and consent_match and country_match:
                    filtered_users.append(item)

            if not filtered_users:
                st.info("No users match these filters.")
            else:
                user_labels = {
                    f"{item['display_name']} · {item['email']} · {item['country']}": item
                    for item in filtered_users
                }
                selected_user_label = st.selectbox("User account", list(user_labels), key="admin_selected_user")
                selected_user = user_labels[selected_user_label]
                user_id = selected_user["id"]
                user_detail = admin_json("GET", f"/admin/users/{user_id}") or {}
                user_record = user_detail.get("user", selected_user)
                review_class = "" if user_record["allow_admin_review"] else " off"
                intervention_class = " live" if user_record["allow_admin_intervention"] else " off"
                intervention_status = (
                    "Administrator access included"
                    if user_record.get("terms_version") == CURRENT_TERMS_VERSION
                    else "Terms update required"
                )
                st.markdown(
                    f"""<div class="admin-profile">
                    <div><strong>{html.escape(user_record['display_name'])}</strong><span>{html.escape(user_record['email'])}</span></div>
                    <div><strong>{html.escape(user_record['country'])}</strong><span>{html.escape(user_record['language'])}</span></div>
                    <div><span class="admin-status{review_class}">{'Review included' if user_record.get('terms_version') == CURRENT_TERMS_VERSION else 'Terms update required'}</span></div>
                    <div><span class="admin-status{intervention_class}">{intervention_status}</span></div>
                    <div><strong>{user_record['retention_days']} days</strong><span>retention · {'stored' if user_record['store_chats'] else 'not stored'}</span></div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                if not user_record["allow_admin_review"] or not user_record["store_chats"]:
                    st.info("This account is visible for administration, but its conversation content and prompt controls are unavailable because review of stored chats is off.")
                else:
                    sessions = admin_json("GET", f"/admin/users/{user_id}/sessions") or []
                    if not sessions:
                        st.info("This account includes administrator review but has no stored sessions.")
                    else:
                        sessions = sorted(
                            sessions,
                            key=lambda item: str(item.get("last_activity") or ""),
                            reverse=True,
                        )
                        selected_session_key = f"admin_open_session_{user_id}"
                        available_session_ids = {item["session_id"] for item in sessions}
                        if st.session_state.get(selected_session_key) not in available_session_ids:
                            st.session_state[selected_session_key] = sessions[0]["session_id"]

                        st.markdown(
                            f"""<div class="admin-history-intro">
                            <strong>Chat history</strong>
                            <span>{len(sessions)} {'conversation' if len(sessions) == 1 else 'conversations'} · newest first</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        for item in sessions:
                            session_preview = " ".join(
                                str(item.get("first_user_message") or "Conversation").split()
                            )
                            if len(session_preview) > 125:
                                session_preview = f"{session_preview[:122].rstrip()}…"
                            updated_at = str(item.get("last_activity") or "").replace("T", " ")[:16]
                            scenario_label = str(item.get("scenario") or "open conversation").replace("_", " ")
                            mode_label = str(item.get("mode") or "listener").replace("_", " ")
                            is_open = item["session_id"] == st.session_state[selected_session_key]
                            with st.container(border=True):
                                summary_col, open_col = st.columns([5, 1])
                                with summary_col:
                                    st.markdown(
                                        f"""<div class="admin-chat-preview">{html.escape(session_preview)}</div>
                                        <div class="admin-chat-meta">{html.escape(updated_at)} UTC · {html.escape(mode_label.title())} · {html.escape(scenario_label.title())} · {item['message_count']} messages</div>""",
                                        unsafe_allow_html=True,
                                    )
                                with open_col:
                                    if st.button(
                                        "Viewing" if is_open else "Open chat",
                                        key=f"open_admin_chat_{user_id}_{item['session_id']}",
                                        type="primary" if is_open else "secondary",
                                        disabled=is_open,
                                        use_container_width=True,
                                    ):
                                        st.session_state[selected_session_key] = item["session_id"]
                                        st.rerun()

                        selected_session = next(
                            item
                            for item in sessions
                            if item["session_id"] == st.session_state[selected_session_key]
                        )
                        session_id = selected_session["session_id"]
                        detail = admin_json("GET", f"/admin/sessions/{session_id}/detail") or {}
                        messages = detail.get("messages", [])
                        session_control = detail.get("session_control", {})
                        user_prompt_control = detail.get("user_prompt_control") or {}
                        control_mode = session_control.get("mode", "ai")
                        session_metadata = [
                            str(selected_session.get("mode") or "listener"),
                            str(selected_session.get("scenario") or "open conversation"),
                        ]
                        if selected_session.get("roleplay_intensity"):
                            session_metadata.append(f"{selected_session['roleplay_intensity']} intimacy")
                        if selected_session.get("roleplay_difficulty"):
                            session_metadata.append(f"{selected_session['roleplay_difficulty']} reaction")
                        session_metadata.append(f"{len(messages)} messages")
                        session_metadata.append(f"replies currently handled by {control_mode.upper()}")
                        selected_preview = " ".join(
                            str(selected_session.get("first_user_message") or "Conversation").split()
                        )
                        if len(selected_preview) > 100:
                            selected_preview = f"{selected_preview[:97].rstrip()}…"
                        st.markdown(
                            f"""<div class="admin-session-head"><strong>{html.escape(selected_preview)}</strong><br>
                            <span>{html.escape(' · '.join(session_metadata))}</span><br>
                            <span class="admin-session-id">Session {html.escape(session_id[-8:])}</span></div>""",
                            unsafe_allow_html=True,
                        )
                        if selected_session.get("character_description"):
                            st.markdown("**User-defined character profile**")
                            st.write(selected_session["character_description"])

                        transcript_col, control_col = st.columns([1.65, 1], gap="large")
                        with transcript_col:
                            st.subheader("Conversation as the user saw it")
                            if st.button("Refresh conversation", key=f"refresh_{session_id}"):
                                st.rerun()
                            for item in messages:
                                with st.chat_message(item["role"]):
                                    st.markdown(item["content"])
                                    if item["role"] == "user":
                                        visible_source = "User"
                                    elif item.get("source") == "admin":
                                        visible_source = "Human DilSe administrator"
                                    else:
                                        visible_source = "DilSe · AI"
                                    st.caption(
                                        f"{visible_source} · {item['created_at']} · message {item['id']}"
                                        + (f" · {item['model']}" if item.get("model") and item["role"] == "assistant" else "")
                                    )

                        with control_col:
                            st.subheader("Control this conversation")
                            st.markdown(
                                """<div class="scope-ladder">
                                <div><strong>Account guidance</strong> affects this user’s future AI replies.</div>
                                <div><strong>Session guidance</strong> affects only this conversation.</div>
                                <div><strong>Human control</strong> pauses AI and sends labelled replies.</div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

                            if control_mode == "human":
                                st.markdown('<span class="admin-status live">Human control active</span>', unsafe_allow_html=True)
                                if st.button("Return replies to AI", type="primary", use_container_width=True, key=f"release_{session_id}"):
                                    result = admin_json("POST", f"/admin/sessions/{session_id}/control", {"mode": "ai", "note": "Returned to AI from case desk"})
                                    if result is not None:
                                        st.success("AI replies resumed.")
                                        st.rerun()
                            else:
                                can_intervene = bool(detail.get("can_intervene"))
                                if st.button(
                                    "Intervene in this chat",
                                    type="primary",
                                    use_container_width=True,
                                    disabled=not can_intervene,
                                    key=f"intervene_{session_id}",
                                ):
                                    result = admin_json("POST", f"/admin/sessions/{session_id}/control", {"mode": "human", "note": "Human intervention from case desk"})
                                    if result is not None:
                                        st.success("AI paused. Human control is active.")
                                        st.rerun()
                                if not can_intervene:
                                    st.caption("This account must accept the current Terms before live administrator participation is available. Session prompt tuning remains available.")

                            if control_mode == "human":
                                with st.form(f"human_reply_{session_id}"):
                                    human_reply = st.text_area("Labelled human response")
                                    send_reply = st.form_submit_button("Send human response", type="primary", use_container_width=True)
                                if send_reply:
                                    result = admin_json("POST", f"/admin/sessions/{session_id}/messages", {"content": human_reply})
                                    if result is not None:
                                        st.success("Human response sent and labelled.")
                                        st.rerun()

                            if str(selected_session.get("mode") or "listener") == "partner":
                                st.markdown('<div class="admin-divider-label">Roleplay controls</div>', unsafe_allow_html=True)
                                with st.form(f"roleplay_controls_{session_id}"):
                                    difficulty_options = ["Use user setting", "Supportive", "Realistic", "Resistant"]
                                    current_difficulty = str(session_control.get("roleplay_difficulty_override") or "").title()
                                    difficulty_override = st.selectbox(
                                        "Character reaction",
                                        difficulty_options,
                                        index=difficulty_options.index(current_difficulty) if current_difficulty in difficulty_options else 0,
                                    )
                                    intimacy_options = ["Use user setting", "Romantic", "Direct", "Explicit"]
                                    current_intimacy = str(session_control.get("roleplay_intensity_override") or "").title()
                                    intimacy_override = st.selectbox(
                                        "Intimacy detail",
                                        intimacy_options,
                                        index=intimacy_options.index(current_intimacy) if current_intimacy in intimacy_options else 0,
                                        help="The administrator can change this during the session. It applies to the next AI response.",
                                    )
                                    roleplay_note = st.text_input("Reason for roleplay change")
                                    save_roleplay_controls = st.form_submit_button("Save roleplay controls", use_container_width=True)
                                if save_roleplay_controls:
                                    result = admin_json(
                                        "POST",
                                        f"/admin/sessions/{session_id}/control",
                                        {
                                            "mode": control_mode,
                                            "roleplay_difficulty_override": (
                                                difficulty_override.lower() if difficulty_override != "Use user setting" else None
                                            ),
                                            "clear_roleplay_difficulty_override": difficulty_override == "Use user setting",
                                            "roleplay_intensity_override": (
                                                intimacy_override.lower() if intimacy_override != "Use user setting" else None
                                            ),
                                            "clear_roleplay_intensity_override": intimacy_override == "Use user setting",
                                            "note": roleplay_note,
                                        },
                                    )
                                    if result is not None:
                                        st.success("Roleplay controls updated for the next AI response.")
                                        st.rerun()

                            st.markdown('<div class="admin-divider-label">Session guidance</div>', unsafe_allow_html=True)
                            with st.form(f"session_prompt_{session_id}"):
                                session_prompt = st.text_area(
                                    "AI instruction for this session",
                                    value=session_control.get("prompt_override") or "",
                                    height=150,
                                    help="Applied after the account guidance. It cannot override global safety or consent rules.",
                                )
                                session_note = st.text_input("Reason", value=session_control.get("note") or "", key=f"session_note_{session_id}")
                                clear_session = st.checkbox("Remove session guidance", key=f"clear_session_{session_id}")
                                save_session = st.form_submit_button("Save session guidance", use_container_width=True)
                            if save_session:
                                result = admin_json(
                                    "POST",
                                    f"/admin/sessions/{session_id}/control",
                                    {
                                        "mode": control_mode,
                                        "prompt_override": session_prompt or None,
                                        "clear_prompt_override": clear_session,
                                        "note": session_note,
                                    },
                                )
                                if result is not None:
                                    st.success("Session guidance updated.")
                                    st.rerun()

                            st.markdown('<div class="admin-divider-label">Account guidance</div>', unsafe_allow_html=True)
                            with st.form(f"user_prompt_{user_id}"):
                                user_prompt = st.text_area(
                                    "AI instruction for this user",
                                    value=user_prompt_control.get("prompt_override") or "",
                                    height=150,
                                    help="Applied to future AI replies across this user’s sessions. It cannot override global safety or consent rules.",
                                )
                                user_note = st.text_input("Reason for account guidance", value=user_prompt_control.get("note") or "")
                                clear_user_prompt = st.checkbox("Remove account guidance")
                                save_user_prompt = st.form_submit_button("Save account guidance", use_container_width=True)
                            if save_user_prompt:
                                result = admin_json(
                                    "POST",
                                    f"/admin/users/{user_id}/prompt-control",
                                    {
                                        "prompt_override": user_prompt or None,
                                        "clear_prompt_override": clear_user_prompt,
                                        "note": user_note,
                                    },
                                )
                                if result is not None:
                                    st.success("Account guidance updated.")
                                    st.rerun()

                            with st.expander("Record a private review note"):
                                with st.form(f"note_{session_id}"):
                                    note = st.text_area("Private note")
                                    save_note = st.form_submit_button("Save private note")
                                if save_note:
                                    result = admin_json("POST", "/admin/notes", {"session_id": session_id, "message_id": None, "note": note})
                                    if result is not None:
                                        st.success("Private note saved.")

                            assistant_messages = [item for item in messages if item["role"] == "assistant" and item.get("source") == "ai"]
                            if assistant_messages:
                                with st.expander("Save a better response"):
                                    message_options = {
                                        f"#{item['id']} · {item['content'][:65]}": item for item in assistant_messages
                                    }
                                    with st.form(f"correction_{session_id}"):
                                        selected_message_label = st.selectbox("AI response", list(message_options))
                                        correction_category = st.selectbox(
                                            "Issue type",
                                            ["cultural guidance", "safety", "tone", "language", "roleplay fidelity", "too verbose", "missed user request"],
                                        )
                                        corrected_response = st.text_area("Better response", height=180)
                                        save_correction = st.form_submit_button("Save better response")
                                    if save_correction:
                                        result = admin_json(
                                            "POST",
                                            "/admin/corrections",
                                            {
                                                "message_id": message_options[selected_message_label]["id"],
                                                "category": correction_category,
                                                "corrected_response": corrected_response,
                                            },
                                        )
                                        if result is not None:
                                            st.success("Better response saved for prompt research.")

    with global_prompt:
        versions = admin_json("GET", "/admin/prompts") or []
        active_version = next((item for item in versions if item["active"]), None)
        if active_version:
            st.markdown(
                f'<div class="admin-session-head"><strong>Active global prompt · version {active_version["id"]}</strong><br><span>{html.escape(active_version["note"] or "No release note")}</span></div>',
                unsafe_allow_html=True,
            )
        for version in versions:
            with st.expander(f"Version {version['id']} · {'active' if version['active'] else 'inactive'} · {version['created_at']}", expanded=False):
                st.caption(version["note"] or "No release note")
                st.code(version["prompt"], language=None)
                if not version["active"] and st.button("Activate this global version", key=f"v2_activate_{version['id']}"):
                    if admin_json("POST", f"/admin/prompts/{version['id']}/activate") is not None:
                        st.rerun()
        active_prompt_text = active_version["prompt"] if active_version else ""
        with st.form("new_global_prompt_v2"):
            new_prompt = st.text_area("New global prompt version", value=active_prompt_text, height=480)
            release_note = st.text_input("Release note")
            activate = st.checkbox("Activate after saving", value=True)
            save_global = st.form_submit_button("Save global prompt version", type="primary")
        if save_global:
            if admin_json("POST", "/admin/prompts", {"prompt": new_prompt, "note": release_note, "activate": activate}) is not None:
                st.success("Global prompt version saved.")
                st.rerun()

    with quality:
        corrections = admin_json("GET", "/admin/corrections") or []
        notes = admin_json("GET", "/admin/notes") or []
        feedback = admin_json("GET", "/admin/feedback") or []
        message_feedback = admin_json("GET", "/admin/message-feedback") or []
        correction_col, note_col, feedback_col, response_feedback_col = st.columns(4)
        correction_col.metric("Saved better responses", len(corrections))
        note_col.metric("Private review notes", len(notes))
        feedback_col.metric("Roleplay feedback records", len(feedback))
        response_feedback_col.metric("Response issues", len(message_feedback))
        st.subheader("Better-response library")
        st.dataframe(corrections, use_container_width=True, hide_index=True)
        st.subheader("Private review notes")
        st.dataframe(notes, use_container_width=True, hide_index=True)
        st.subheader("User feedback")
        st.dataframe(feedback, use_container_width=True, hide_index=True)
        st.subheader("Per-response issues")
        st.dataframe(message_feedback, use_container_width=True, hide_index=True)

    with library:
        kind = st.selectbox("Content type", ["personas", "scenarios", "exercises", "cards"], key="v2_library_kind")
        items = admin_json("GET", f"/admin/catalog/{kind}") or []
        st.dataframe(items, use_container_width=True, hide_index=True)
        with st.form("v2_catalog_form"):
            slug = st.text_input("Slug", help="Use lowercase letters, numbers, and underscores.")
            name = st.text_input("Name")
            description = st.text_area("Description")
            starter = st.text_area("Starter", disabled=kind == "personas")
            active = st.checkbox("Active", value=True)
            save_item = st.form_submit_button("Save content item", type="primary")
        if save_item:
            if admin_json("POST", f"/admin/catalog/{kind}", {"slug": slug, "name": name, "description": description, "starter": starter or None, "active": active}) is not None:
                st.success("Content item saved.")
                st.rerun()

    with audit_tab:
        audit_rows = admin_json("GET", "/admin/audit") or []
        st.caption("Every conversation view, prompt change, control change, note, and human reply is recorded here.")
        st.dataframe(audit_rows, use_container_width=True, hide_index=True)


ADMIN_PAGES = (
    "Overview",
    "Visitors",
    "App usage",
    "Users",
    "Conversations",
    "Live sessions",
    "Prompt studio",
    "Response quality",
    "Content library",
    "Audit log",
)


def restore_admin_navigation() -> None:
    """Restore an administrator's location after a browser refresh."""
    if st.session_state.admin_navigation_restored:
        return
    requested_page = str(st.query_params.get("admin_view") or "")
    if requested_page in ADMIN_PAGES:
        st.session_state.admin_page = requested_page
    requested_user = str(st.query_params.get("admin_user") or "")
    if requested_user.isdigit() and int(requested_user) > 0:
        st.session_state.admin_selected_user_id = int(requested_user)
    requested_session = str(st.query_params.get("admin_session") or "")
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", requested_session):
        st.session_state.admin_selected_session_id = requested_session
    st.session_state.admin_navigation_restored = True


def persist_admin_navigation() -> None:
    """Keep the current administrator location in the URL without storing credentials."""
    st.query_params["admin"] = "1"
    st.query_params["admin_view"] = str(st.session_state.admin_page)
    selected_user_id = st.session_state.get("admin_selected_user_id")
    selected_session_id = st.session_state.get("admin_selected_session_id")
    if selected_user_id:
        st.query_params["admin_user"] = str(selected_user_id)
    elif "admin_user" in st.query_params:
        del st.query_params["admin_user"]
    if selected_session_id:
        st.query_params["admin_session"] = str(selected_session_id)
    elif "admin_session" in st.query_params:
        del st.query_params["admin_session"]


def admin_go_to(page: str) -> None:
    st.session_state.admin_page = page
    persist_admin_navigation()
    st.rerun()


def admin_time(value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return "No activity yet"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    except ValueError:
        return raw.replace("T", " ")[:16]


def admin_message_time(value: Any) -> str:
    """Return a compact UTC timestamp for message metadata."""
    raw = str(value or "")
    if not raw:
        return "Time unavailable"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%d %b %H:%M")
    except ValueError:
        return raw.replace("T", " ")[:16]


def admin_page_header(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""<section class="admin-workspace-head"><div>
        <span class="admin-page-tag">{html.escape(kicker)}</span>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(body)}</p>
        </div></section>""",
        unsafe_allow_html=True,
    )


def render_admin_left_rail(summary: dict[str, Any], active_count: int) -> None:
    logo_uri = image_data_uri(str(LOGO_PATH), int(LOGO_PATH.stat().st_mtime))
    st.markdown('<div class="admin-shell-marker"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="admin-rail-brand"><img src="{logo_uri}" alt="DilSe">
        <span>Administrator workspace</span></div>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="admin-rail-label">Monitor</div>', unsafe_allow_html=True)
    for page in ("Overview", "Visitors", "App usage", "Users", "Conversations", "Live sessions"):
        if page == "Visitors":
            label = f"Visitors · {int(summary.get('live_visitors', 0))} live"
        elif page == "App usage":
            label = f"App usage · {int(summary.get('registered_installations', 0))} installed"
        elif page == "Live sessions":
            label = f"Live sessions · {active_count}"
        else:
            label = page
        if st.button(
            label,
            key=f"admin_nav_{page}",
            type="primary" if st.session_state.admin_page == page else "secondary",
            use_container_width=True,
        ):
            admin_go_to(page)
    st.markdown('<div class="admin-rail-label">Improve DilSe</div>', unsafe_allow_html=True)
    for page in ("Prompt studio", "Response quality", "Content library"):
        if st.button(
            page,
            key=f"admin_nav_{page}",
            type="primary" if st.session_state.admin_page == page else "secondary",
            use_container_width=True,
        ):
            admin_go_to(page)
    st.markdown('<div class="admin-rail-label">Security</div>', unsafe_allow_html=True)
    if st.button(
        "Audit log",
        key="admin_nav_Audit log",
        type="primary" if st.session_state.admin_page == "Audit log" else "secondary",
        use_container_width=True,
    ):
        admin_go_to("Audit log")
    st.markdown(
        f"""<div class="admin-rail-foot"><strong>{summary.get('consenting_users', 0):,}</strong> accounts are available for review.<br>
        <strong>{summary.get('pending_terms_users', 0):,}</strong> account(s) still need to accept the current Terms.</div>""",
        unsafe_allow_html=True,
    )
    if st.button("Lock workspace", key="admin_lock_workspace_v3", use_container_width=True):
        forget_admin_browser_login()
        st.rerun()


def render_admin_mobile_nav() -> None:
    with st.container(key="admin_mobile_nav"):
        current = st.session_state.admin_page
        selected = st.selectbox(
            "Administrator section",
            ADMIN_PAGES,
            index=ADMIN_PAGES.index(current) if current in ADMIN_PAGES else 0,
            key="admin_mobile_page_picker",
        )
        if selected != current:
            admin_go_to(selected)


def render_admin_metrics(summary: dict[str, Any], active_count: int) -> None:
    del active_count
    metrics = (
        ("Live visitors", summary.get("live_visitors", 0)),
        ("All users", summary.get("total_users", 0)),
        ("Conversations", summary.get("reviewable_sessions", 0)),
        ("Messages", summary.get("reviewable_messages", 0)),
        ("Terms update needed", summary.get("pending_terms_users", 0)),
    )
    cards = "".join(
        f'<div class="admin-kpi"><span>{html.escape(label)}</span><strong>{int(value):,}</strong></div>'
        for label, value in metrics
    )
    st.markdown(f'<div class="admin-kpi-grid">{cards}</div>', unsafe_allow_html=True)


def admin_user_card(user: dict[str, Any], *, button_label: str, button_key: str) -> bool:
    current_terms = user.get("terms_version") == CURRENT_TERMS_VERSION
    can_review = bool(user.get("allow_admin_review") and user.get("store_chats"))
    if current_terms:
        access = "Review included"
    elif can_review:
        access = "Previous review consent · Terms update required"
    else:
        access = "Terms update required"
    activity = admin_time(user.get("last_reviewable_activity"))
    conversation_count = int(user.get("reviewable_sessions") or 0)
    conversation_label = "conversation" if conversation_count == 1 else "conversations"
    with st.container(border=True):
        st.markdown('<span class="admin-card-marker"></span>', unsafe_allow_html=True)
        copy_col, action_col = st.columns([4.6, 1.2])
        with copy_col:
            st.markdown(
                f"""<div class="admin-case-card"><h3>{html.escape(str(user.get('display_name') or 'Unnamed user'))}</h3>
                <p>{html.escape(str(user.get('email') or ''))} · {html.escape(str(user.get('country') or ''))} · {html.escape(str(user.get('language') or ''))}</p>
                <p>{html.escape(access)} · {conversation_count} {conversation_label} · {html.escape(activity)}</p></div>""",
                unsafe_allow_html=True,
            )
        with action_col:
            return st.button(button_label, key=button_key, use_container_width=True)


def render_admin_overview(summary: dict[str, Any], users: list[dict[str, Any]], active: list[dict[str, Any]]) -> dict[str, Any]:
    admin_page_header(
        "Operations overview",
        "What needs attention",
        "See account access, active conversations, and recent activity before opening a user record.",
    )
    render_admin_metrics(summary, len(active))
    live_visitors = int(summary.get("live_visitors", 0))
    if live_visitors:
        st.markdown(
            f'<div class="admin-attention"><span class="visitor-page-pill">{live_visitors} visitor(s) on the website now</span><br>Open Visitors to see their current pages and recent page history.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Open visitor tracker", key="overview_open_visitors"):
            admin_go_to("Visitors")
    if active:
        st.markdown(
            f'<div class="admin-attention"><span class="admin-live-dot"></span><strong>{len(active)} live-intervention conversation(s)</strong> had activity in the past hour. Open Live sessions to review them.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Review live sessions", type="primary", key="overview_open_live"):
            admin_go_to("Live sessions")
    else:
        st.markdown(
            '<div class="admin-attention">No intervention-enabled conversation has been active in the past hour. AI continues responding normally.</div>',
            unsafe_allow_html=True,
        )

    recent_col, access_col = st.columns([1.5, 1], gap="large")
    with recent_col:
        st.markdown('<div class="admin-section-title"><h2>Recent accounts</h2><p>Accounts are ordered by their latest stored activity.</p></div>', unsafe_allow_html=True)
        if not users:
            st.markdown('<div class="admin-empty"><strong>No accounts yet</strong>New accounts will appear here.</div>', unsafe_allow_html=True)
        for user in users[:5]:
            if admin_user_card(user, button_label="Open", button_key=f"overview_user_{user['id']}"):
                st.session_state.admin_selected_user_id = user["id"]
                admin_go_to("Users")
    with access_col:
        st.markdown('<div class="admin-section-title"><h2>Access status</h2><p>What administrators can currently review.</p></div>', unsafe_allow_html=True)
        stored = int(summary.get("stored_users", 0))
        review = int(summary.get("consenting_users", 0))
        intervention = int(summary.get("intervention_users", 0))
        pending_terms = int(summary.get("pending_terms_users", 0))
        st.markdown(
            f"""<div class="admin-fact-list">
            <div><span>Stored history</span><strong>{stored:,} account(s)</strong></div>
            <div><span>Review available</span><strong>{review:,} account(s)</strong></div>
            <div><span>Terms update required</span><strong>{pending_terms:,} account(s)</strong></div>
            <div><span>Live intervention</span><strong>{intervention:,} account(s)</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="admin-privacy-rule">Current Terms include conversation storage and authorized administrator review for every active account. Accounts on earlier Terms must accept the update before previously private conversations become reviewable.</div>', unsafe_allow_html=True)
    return {}


@st.fragment(run_every="15s")
def render_admin_visitors() -> None:
    data = admin_json("GET", "/admin/visitors?limit=200", timeout=10)
    if data is None:
        return
    live = list(data.get("live") or [])
    past = list(data.get("past") or [])
    retention_days = int(data.get("retention_days") or 30)
    admin_page_header(
        "Website activity",
        "Visitors",
        "See who is on the website now, which page they are viewing, and recent visits within the retention period.",
    )
    st.markdown(
        f"""<div class="visitor-live-board"><div><span>Automatic 15-second refresh</span>
        <strong>{'Visitors are active now' if live else 'No visitors are active now'}</strong></div>
        <div class="visitor-live-count"><b>{len(live)}</b><span>live</span></div></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="visitor-privacy-note">IP addresses are masked before storage. Visitor activity is kept for {retention_days} days and is available only in this administrator workspace.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="admin-section-title"><h2>Live now</h2><p>Activity within the last minute. The page updates automatically.</p></div>', unsafe_allow_html=True)
    if not live:
        st.markdown('<div class="admin-empty"><strong>No live visitors</strong>A visitor will appear here after the next website heartbeat.</div>', unsafe_allow_html=True)
    for visit in live:
        with st.container(border=True):
            st.markdown('<span class="admin-card-marker"></span>', unsafe_allow_html=True)
            copy_col, page_col = st.columns([3.2, 1.3])
            with copy_col:
                account = "Signed-in account" if visit.get("signed_in") else "Not signed in"
                st.markdown(
                    f"""<div class="admin-case-card"><h3>{html.escape(str(visit.get('visitor') or 'Visitor'))}</h3>
                    <p>{html.escape(account)} · {html.escape(str(visit.get('ip_prefix') or 'Unavailable'))}</p>
                    <p class="admin-case-message">First seen {html.escape(admin_time(visit.get('first_seen')))} · {int(visit.get('page_views') or 0)} page view(s)</p></div>""",
                    unsafe_allow_html=True,
                )
            with page_col:
                st.markdown(
                    f'<span class="visitor-page-pill">{html.escape(str(visit.get("current_page") or "Unknown page"))}</span>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="admin-section-title"><h2>Past visits</h2><p>Most recent visits appear first. One visit ends after 30 minutes without activity.</p></div>', unsafe_allow_html=True)
    if not past:
        st.info("No completed visits are stored yet.")
        return
    pages = ("All pages", *sorted({str(item.get("current_page") or "Unknown page") for item in past}))
    filter_col, account_col = st.columns(2)
    with filter_col:
        page_filter = st.selectbox("Last page", pages, key="visitor_page_filter")
    with account_col:
        account_filter = st.selectbox(
            "Account status",
            ("All visitors", "Signed in", "Not signed in"),
            key="visitor_account_filter",
        )
    filtered = [
        visit for visit in past
        if (page_filter == "All pages" or visit.get("current_page") == page_filter)
        and (
            account_filter == "All visitors"
            or (account_filter == "Signed in" and visit.get("signed_in"))
            or (account_filter == "Not signed in" and not visit.get("signed_in"))
        )
    ]
    table_rows = []
    for visit in filtered:
        trail = " → ".join(str(page.get("page") or "") for page in visit.get("pages") or [])
        table_rows.append(
            {
                "Visitor": visit.get("visitor"),
                "Account": "Signed in" if visit.get("signed_in") else "Not signed in",
                "Masked IP": visit.get("ip_prefix"),
                "Last page": visit.get("current_page"),
                "Page history": trail,
                "First seen": admin_time(visit.get("first_seen")),
                "Last seen": admin_time(visit.get("last_seen")),
                "Minutes": visit.get("duration_minutes"),
            }
        )
    st.caption(f"{len(filtered)} past visit(s) shown")
    if table_rows:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No past visits match these filters.")


def render_admin_app_usage() -> dict[str, Any]:
    data = admin_json("GET", "/admin/app-usage", timeout=10) or {}
    summary = dict(data.get("summary") or {})
    users = list(data.get("users") or [])
    registered = int(summary.get("registered_installations") or 0)
    app_users = int(summary.get("app_users") or 0)
    notification_devices = int(summary.get("notifications_enabled") or 0)
    current_installations = int(summary.get("current_version_installations") or 0)
    web_messages = int(summary.get("web_messages") or 0)
    android_messages = int(summary.get("android_messages") or 0)
    legacy_messages = int(summary.get("legacy_messages") or 0)
    tracked_messages = web_messages + android_messages
    web_percent = round((web_messages / tracked_messages) * 100) if tracked_messages else 0
    android_percent = 100 - web_percent if tracked_messages else 0
    current_version = str(data.get("current_app_version") or "Unknown")

    admin_page_header(
        "Android and web activity",
        "App usage",
        "See registered Android installations, app versions, notification status, and where each user sends messages.",
    )
    st.markdown(
        f"""<div class="app-usage-board">
        <div class="app-install-total"><span>Registered installations</span>
        <strong>{registered:,}</strong><small>{app_users:,} account(s) have connected an Android app</small></div>
        <div class="app-source-ledger"><h3>Where tracked user messages come from</h3>
        <p>Each new user message is labelled automatically. Administrator and AI responses are excluded.</p>
        <div class="app-source-track" role="img" aria-label="{web_percent}% web and {android_percent}% Android app">
        <span class="web" style="width:{web_percent}%"></span><span class="android" style="width:{android_percent}%"></span></div>
        <div class="app-source-legend">
        <div><span>Web</span><strong>{web_messages:,} messages · {web_percent}%</strong></div>
        <div><span>Android app</span><strong>{android_messages:,} messages · {android_percent}%</strong></div>
        </div></div></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""<div class="admin-fact-list">
        <div><span>Current Android release</span><strong>{html.escape(current_version)}</strong></div>
        <div><span>Installations on current release</span><strong>{current_installations:,} of {registered:,}</strong></div>
        <div><span>Notifications enabled</span><strong>{notification_devices:,} installation(s)</strong></div>
        <div><span>Legacy messages</span><strong>{legacy_messages:,} without a reliable source label</strong></div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="app-usage-note">A registered installation means the app was opened and connected to a DilSe account. An APK download that was never opened cannot be counted. Notification tokens and device identifiers are never shown here.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="admin-section-title"><h2>Account activity</h2><p>Filter users by the channel used for their stored messages. Most recent activity appears first.</p></div>',
        unsafe_allow_html=True,
    )
    search_col, activity_col = st.columns([1.45, 1])
    with search_col:
        query = st.text_input(
            "Search app activity",
            placeholder="Name or email",
            key="admin_app_usage_search",
        )
    with activity_col:
        activity_filter = st.selectbox(
            "Message source",
            ("All activity", "Both", "Android app", "Web", "App installed", "Legacy or no activity"),
            key="admin_app_usage_filter",
        )
    filtered = [
        user
        for user in users
        if (
            not query
            or query.lower()
            in f"{user.get('display_name', '')} {user.get('email', '')}".lower()
        )
        and (activity_filter == "All activity" or user.get("activity") == activity_filter)
    ]
    st.caption(f"{len(filtered)} of {len(users)} accounts")
    if not filtered:
        st.info("No accounts match these app-usage filters.")
        return {"summary": summary}

    platform_labels = {
        "web": "Web",
        "android_app": "Android app",
        "unknown": "Unknown",
        "legacy": "Legacy",
    }
    table_rows = []
    for user in filtered:
        table_rows.append(
            {
                "User": user.get("display_name") or "Unnamed user",
                "Email": user.get("email") or "",
                "Message activity": user.get("activity") or "Legacy or no activity",
                "Installations": int(user.get("installation_count") or 0),
                "App version(s)": user.get("app_versions") or "Not registered",
                "Notifications": int(user.get("notification_devices") or 0),
                "Last response via": platform_labels.get(
                    str(user.get("latest_client_platform") or "legacy"),
                    "Legacy",
                ),
                "Last app seen": admin_time(user.get("last_app_seen")),
                "Last web message": admin_time(user.get("last_web_message")),
                "Last app message": admin_time(user.get("last_android_message")),
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    return {"summary": summary}


def render_admin_users(users: list[dict[str, Any]]) -> dict[str, Any]:
    admin_page_header(
        "Account directory",
        "Users",
        "Find an account, check its privacy settings, and open its conversations in newest-first order.",
    )
    if not users:
        st.markdown('<div class="admin-empty"><strong>No user accounts</strong>Accounts will appear here after registration.</div>', unsafe_allow_html=True)
        return {}
    search_col, access_col, country_col = st.columns([1.5, 1, 1])
    with search_col:
        query = st.text_input("Search users", placeholder="Name or email", key="admin_v3_user_search")
    with access_col:
        access_filter = st.selectbox("Conversation access", ("All accounts", "Review available", "Terms update required"), key="admin_v3_access_filter")
    with country_col:
        countries = ("All countries", *sorted({str(item.get("country") or "Unknown") for item in users}))
        country_filter = st.selectbox("Country", countries, key="admin_v3_country_filter")

    filtered = []
    for user in users:
        matches_query = not query or query.lower() in f"{user.get('display_name', '')} {user.get('email', '')}".lower()
        has_review = bool(user.get("allow_admin_review") and user.get("store_chats"))
        needs_terms = user.get("terms_version") != CURRENT_TERMS_VERSION
        matches_access = access_filter == "All accounts" or (access_filter == "Review available" and has_review) or (access_filter == "Terms update required" and needs_terms)
        matches_country = country_filter == "All countries" or user.get("country") == country_filter
        if matches_query and matches_access and matches_country:
            filtered.append(user)
    st.caption(f"{len(filtered)} of {len(users)} accounts")
    if not filtered:
        st.info("No users match these filters.")
        return {}

    selected_id = st.session_state.get("admin_selected_user_id")
    if selected_id not in {item["id"] for item in filtered}:
        selected_id = filtered[0]["id"]
        st.session_state.admin_selected_user_id = selected_id
    selected_user = next(item for item in filtered if item["id"] == selected_id)
    for user in filtered:
        if admin_user_card(
            user,
            button_label="Selected" if user["id"] == selected_id else "View",
            button_key=f"users_view_{user['id']}",
        ) and user["id"] != selected_id:
            st.session_state.admin_selected_user_id = user["id"]
            st.session_state.admin_selected_session_id = None
            persist_admin_navigation()
            st.rerun()

    detail = admin_json("GET", f"/admin/users/{selected_id}") or {}
    user_record = detail.get("user", selected_user)
    can_review = bool(user_record.get("allow_admin_review") and user_record.get("store_chats"))
    sessions: list[dict[str, Any]] = []
    st.markdown('<div class="admin-section-title"><h2>Conversation history</h2><p>Newest activity appears first.</p></div>', unsafe_allow_html=True)
    if can_review:
        sessions = admin_json("GET", f"/admin/users/{selected_id}/sessions") or []
        if sessions:
            for session in sessions:
                preview = " ".join(str(session.get("first_user_message") or "Conversation").split())
                with st.container(border=True):
                    st.markdown('<span class="admin-card-marker"></span>', unsafe_allow_html=True)
                    copy_col, action_col = st.columns([4.6, 1.2])
                    with copy_col:
                        st.markdown(
                            f"""<div class="admin-case-card"><h3>{html.escape(preview[:145])}</h3>
                            <p>{html.escape(admin_time(session.get('last_activity')))} · {html.escape(str(session.get('mode') or 'listener').title())} · {int(session.get('message_count') or 0)} messages</p></div>""",
                            unsafe_allow_html=True,
                        )
                    with action_col:
                        if st.button("Open chat", key=f"user_open_session_{session['session_id']}", use_container_width=True):
                            st.session_state.admin_selected_user_id = selected_id
                            st.session_state.admin_selected_session_id = session["session_id"]
                            admin_go_to("Conversations")
        else:
            st.info("This account includes administrator review but has no stored conversations.")
    else:
        if user_record.get("terms_version") != CURRENT_TERMS_VERSION:
            st.info("This account must accept the current Terms before its conversations become available for required administrator review.")
        else:
            st.info("Conversation history is temporarily unavailable. Current accounts normally include stored administrator review.")
    return {"user": user_record, "detail": detail, "sessions": sessions}


def admin_session_label(session: dict[str, Any]) -> str:
    preview = " ".join(str(session.get("first_user_message") or "Conversation").split())
    if len(preview) > 58:
        preview = f"{preview[:55].rstrip()}…"
    return f"{preview} · {admin_time(session.get('last_activity'))}"


def render_admin_message_delete_control(
    session_id: str,
    message: dict[str, Any],
    source_label: str,
) -> None:
    message_id = int(message["id"])
    delete_target = f"{session_id}:{message_id}"
    pending = st.session_state.get("admin_pending_message_delete") == delete_target
    if pending:
        st.warning(
            f"Permanently delete message {message_id} from {source_label}? "
            "It will disappear from the user chat and cannot be restored from the dashboard."
        )
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button(
            "Delete permanently",
            type="primary",
            use_container_width=True,
            key=f"confirm_delete_message_{delete_target}",
        ):
            result = admin_json(
                "DELETE",
                f"/admin/sessions/{session_id}/messages/{message_id}",
            )
            if result is not None:
                st.session_state.admin_pending_message_delete = None
                st.toast(f"Message {message_id} deleted")
                st.rerun()
        if cancel_col.button(
            "Cancel",
            use_container_width=True,
            key=f"cancel_delete_message_{delete_target}",
        ):
            st.session_state.admin_pending_message_delete = None
            st.rerun()
    elif st.button(
        "×",
        help="Delete this message",
        key=f"delete_message_{delete_target}",
    ):
        st.session_state.admin_pending_message_delete = delete_target
        st.rerun()


def advance_admin_composer(
    session_id: str,
    *,
    prefill: str | None = None,
    retained_image: dict[str, str] | None = None,
) -> None:
    nonces = dict(st.session_state.get("admin_composer_nonces") or {})
    nonces[session_id] = int(nonces.get(session_id, 0)) + 1
    st.session_state.admin_composer_nonces = nonces
    prefills = dict(st.session_state.get("admin_composer_prefill") or {})
    retained = dict(st.session_state.get("admin_composer_retained_images") or {})
    if prefill is None:
        prefills.pop(session_id, None)
    else:
        prefills[session_id] = prefill
    if retained_image is None:
        retained.pop(session_id, None)
    else:
        retained[session_id] = retained_image
    st.session_state.admin_composer_prefill = prefills
    st.session_state.admin_composer_retained_images = retained


def send_admin_composer_payload(session_id: str, payload: dict[str, Any]) -> None:
    if admin_json(
        "POST",
        f"/admin/sessions/{session_id}/messages",
        payload,
        timeout=45,
    ) is None:
        return
    st.session_state.admin_pending_roman_urdu_review = None
    st.session_state.admin_reply_to = None
    advance_admin_composer(session_id)
    st.toast("Message sent")
    st.rerun(scope="app")


def render_admin_transcript_composer(
    selected_session_id: str,
    selected_user: dict[str, Any],
    detail: dict[str, Any],
) -> None:
    messages = detail.get("messages") or []
    control_mode = str((detail.get("session_control") or {}).get("mode") or "ai")
    admin_reply = st.session_state.get("admin_reply_to") or {}
    message_ids = {
        int(message["id"])
        for message in messages
        if message.get("id") is not None
    }
    valid_reply = (
        admin_reply.get("session_id") == selected_session_id
        and int(admin_reply.get("message_id") or -1) in message_ids
    )
    if admin_reply and not valid_reply:
        st.session_state.admin_reply_to = None
        admin_reply = {}

    with st.container(key="admin_chat_composer"):
        st.markdown(
            '<div class="admin-composer-label"><strong>Write the next DilSe message</strong><span>Links become clickable · JPG, PNG or WebP up to 5 MB</span></div>',
            unsafe_allow_html=True,
        )
        if control_mode != "human":
            st.text_area(
                "Administrator message",
                placeholder="Take human control to write in this conversation",
                disabled=True,
                label_visibility="collapsed",
                key=f"admin_disabled_composer_{selected_session_id}",
            )
            if st.button(
                "Take human control to reply",
                type="primary",
                use_container_width=True,
                disabled=not bool(detail.get("can_intervene")),
                key=f"admin_composer_intervene_{selected_session_id}",
            ):
                if admin_json(
                    "POST",
                    f"/admin/sessions/{selected_session_id}/control",
                    {"mode": "human", "note": "Human intervention from conversation composer"},
                ) is not None:
                    st.rerun(scope="app")
            return

        pending_review = st.session_state.get("admin_pending_roman_urdu_review") or {}
        if pending_review.get("session_id") == selected_session_id:
            original = str(pending_review.get("original") or "")
            corrected = str(pending_review.get("corrected") or original)
            st.markdown(
                '<div class="admin-composer-label"><strong>Approve the message</strong><span>Nothing has been sent yet</span></div>',
                unsafe_allow_html=True,
            )
            original_col, corrected_col = st.columns(2, gap="medium")
            with original_col:
                st.markdown(
                    f'<div class="admin-writing-review"><span>Original</span><p>{html.escape(original)}</p></div>',
                    unsafe_allow_html=True,
                )
            with corrected_col:
                st.markdown(
                    f'<div class="admin-writing-review corrected"><span>Roman Urdu check</span><p>{html.escape(corrected)}</p></div>',
                    unsafe_allow_html=True,
                )
            notice = str(pending_review.get("notice") or "").strip()
            if notice:
                st.markdown(
                    f'<div class="admin-writing-review-note">{html.escape(notice)}</div>',
                    unsafe_allow_html=True,
                )
            payload = dict(pending_review.get("payload") or {})
            if payload.get("image_base64"):
                st.caption("The attached image will be sent with either approved version.")
            correction_col, original_col, edit_col = st.columns([1.2, 1.1, .9])
            if correction_col.button(
                "Use correction",
                type="primary",
                use_container_width=True,
                key=f"admin_use_roman_urdu_{selected_session_id}",
            ):
                payload.update(
                    {
                        "content": corrected,
                        "original_content": original,
                        "roman_urdu_review_status": "corrected",
                    }
                )
                send_admin_composer_payload(selected_session_id, payload)
            if original_col.button(
                "Keep original",
                use_container_width=True,
                key=f"admin_keep_original_{selected_session_id}",
            ):
                payload.update(
                    {
                        "content": original,
                        "original_content": original,
                        "roman_urdu_review_status": "kept_original",
                    }
                )
                send_admin_composer_payload(selected_session_id, payload)
            if edit_col.button(
                "Edit again",
                use_container_width=True,
                key=f"admin_edit_review_{selected_session_id}",
            ):
                retained_image = {
                    key: str(payload[key])
                    for key in (
                        "image_base64",
                        "image_mime_type",
                        "image_filename",
                    )
                    if payload.get(key)
                }
                advance_admin_composer(
                    selected_session_id,
                    prefill=original,
                    retained_image=retained_image or None,
                )
                st.session_state.admin_pending_roman_urdu_review = None
                st.rerun(scope="app")
            return

        if valid_reply:
            selected_reply_markup = message_reply_markup(
                {
                    "reply_to_message_id": admin_reply.get("message_id"),
                    "reply_to_role": admin_reply.get("role"),
                    "reply_to_content": admin_reply.get("content"),
                    "reply_to_source": admin_reply.get("source"),
                },
                viewer="admin",
                user_label=str(selected_user.get("display_name") or "User"),
            )
            reply_copy, cancel_copy = st.columns([8, 1])
            with reply_copy:
                st.markdown(selected_reply_markup, unsafe_allow_html=True)
            if cancel_copy.button(
                "×",
                help="Cancel message reply",
                key=f"cancel_admin_chat_reply_{selected_session_id}_{admin_reply.get('message_id')}",
            ):
                st.session_state.admin_reply_to = None
                st.rerun(scope="app")

        nonce = int(
            (st.session_state.get("admin_composer_nonces") or {}).get(
                selected_session_id, 0
            )
        )
        prefill = str(
            (st.session_state.get("admin_composer_prefill") or {}).get(
                selected_session_id, ""
            )
        )
        retained_image = dict(
            (st.session_state.get("admin_composer_retained_images") or {}).get(
                selected_session_id, {}
            )
        )
        with st.form(
            f"admin_chat_composer_form_{selected_session_id}_{nonce}",
            clear_on_submit=False,
        ):
            reply_text = st.text_area(
                "Administrator message",
                placeholder="Write a message or paste a link…",
                label_visibility="collapsed",
                height=76,
                value=prefill,
                key=f"admin_message_text_{selected_session_id}_{nonce}",
            )
            remove_retained_image = False
            with st.expander("Image attachment", expanded=bool(retained_image)):
                image_file = st.file_uploader(
                    "Add or replace an image" if retained_image else "Add an image",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=False,
                    key=f"admin_chat_image_{selected_session_id}_{nonce}",
                )
                if retained_image:
                    remove_retained_image = st.checkbox(
                        f"Remove retained image: {retained_image.get('image_filename', 'attachment')}",
                        key=f"admin_remove_retained_image_{selected_session_id}_{nonce}",
                    )
            review_enabled = st.toggle(
                "Check Roman Urdu",
                value=True,
                help="Default on. You approve the corrected or original draft before anything is sent.",
                key=f"admin_roman_urdu_check_{selected_session_id}",
            )
            review_col, direct_send_col = st.columns([1.2, 1])
            with review_col:
                review_message = st.form_submit_button(
                    "Review before sending",
                    type="primary",
                    use_container_width=True,
                    disabled=not review_enabled,
                )
            with direct_send_col:
                send_without_review = st.form_submit_button(
                    "Send without review",
                    use_container_width=True,
                    help="Send the message exactly as written without calling the correction assistant.",
                )
        if not review_message and not send_without_review:
            return
        if not reply_text.strip() and image_file is None and (
            not retained_image or remove_retained_image
        ):
            st.warning("Write a message or attach an image.")
            return
        payload: dict[str, Any] = {
            "content": reply_text.strip(),
            "reply_to_message_id": (
                int(admin_reply["message_id"]) if valid_reply else None
            ),
        }
        if retained_image and not remove_retained_image:
            payload.update(retained_image)
        if image_file is not None:
            image_bytes = image_file.getvalue()
            if len(image_bytes) > ADMIN_IMAGE_MAX_BYTES:
                st.error("Images must be 5 MB or smaller.")
                return
            if image_file.type not in {"image/jpeg", "image/png", "image/webp"}:
                st.error("Use a JPG, PNG, or WebP image.")
                return
            payload.update(
                {
                    "image_base64": base64.b64encode(image_bytes).decode("ascii"),
                    "image_mime_type": image_file.type,
                    "image_filename": image_file.name,
                }
            )
        if review_message and review_enabled and reply_text.strip():
            review = admin_json(
                "POST",
                "/admin/writing/roman-urdu/check",
                {
                    "session_id": selected_session_id,
                    "content": reply_text.strip(),
                },
                timeout=60,
            )
            if review is None:
                return
            st.session_state.admin_pending_roman_urdu_review = {
                "session_id": selected_session_id,
                "original": review.get("original") or reply_text.strip(),
                "corrected": review.get("corrected") or reply_text.strip(),
                "notice": review.get("notice"),
                "payload": payload,
            }
            st.rerun(scope="app")
        payload.update(
            {
                "original_content": reply_text.strip(),
                "roman_urdu_review_status": "not_checked",
            }
        )
        send_admin_composer_payload(selected_session_id, payload)


def admin_transcript_signature(messages: list[dict[str, Any]]) -> str:
    """Track changes that need a full transcript redraw."""
    return "|".join(
        f"{message.get('id')}:{message.get('read_at') or ''}:{message.get('read_basis') or ''}"
        for message in messages
    )


@st.fragment(run_every="1s")
def render_admin_live_status(
    selected_session_id: str,
    selected_user: dict[str, Any],
    selected_session: dict[str, Any],
    loaded_transcript_signature: str,
) -> None:
    detail = admin_json(
        "GET",
        f"/admin/sessions/{selected_session_id}/detail?record_view=false",
    ) or {}
    messages = list(detail.get("messages") or [])
    current_signature = admin_transcript_signature(messages)
    if current_signature != loaded_transcript_signature:
        st.rerun(scope="app")
    mode = str(selected_session.get("mode") or "listener").title()
    scenario = str(selected_session.get("scenario") or "open conversation").replace("_", " ").title()
    control_mode = str((detail.get("session_control") or {}).get("mode") or "ai").upper()
    preview = " ".join(str(selected_session.get("first_user_message") or "Conversation").split())
    typing_status = ""
    if detail.get("user_typing"):
        typing_name = html.escape(str(selected_user.get("display_name") or "User"))
        typing_status = (
            '<div class="admin-user-typing" role="status" aria-live="polite">'
            '<span class="admin-typing-bubble" aria-hidden="true">'
            '<span class="admin-typing-dots"><i></i><i></i><i></i></span></span>'
            f'<span><strong>{typing_name}</strong> is typing…</span></div>'
        )
    st.markdown(
        f"""<div class="admin-transcript-head"><div><strong>{html.escape(preview)}</strong>
        <span>{html.escape(mode)} · {html.escape(scenario)} · {len(messages)} messages · replies handled by {html.escape(control_mode)}</span></div>
        <div class="admin-transcript-status"><span class="admin-session-id">{html.escape(selected_session_id[-8:])}</span>{typing_status}</div></div>""",
        unsafe_allow_html=True,
    )


def render_admin_transcript(
    selected_session_id: str,
    selected_user: dict[str, Any],
    selected_session: dict[str, Any],
    detail: dict[str, Any],
) -> None:
    """Render stable message and audio controls outside the live polling fragment."""
    messages = list(detail.get("messages") or [])
    if selected_session.get("character_description"):
        with st.expander("User-defined roleplay character"):
            st.write(selected_session["character_description"])
    if not messages:
        st.info("No messages are available in this session.")
    else:
        with st.container(
            height=640,
            border=False,
            key=f"admin_chat_transcript_{selected_session_id}",
        ):
            for message in messages:
                with st.chat_message(message["role"]):
                    reply_markup = message_reply_markup(
                        message,
                        viewer="admin",
                        user_label=str(selected_user.get("display_name") or "User"),
                    )
                    if reply_markup:
                        st.markdown(reply_markup, unsafe_allow_html=True)
                    render_message_body(message, viewer="admin")
                    if message["role"] == "user":
                        source = selected_user.get("display_name") or "User"
                        platform_label = {
                            "web": "Web",
                            "android_app": "Android app",
                            "unknown": "Unknown source",
                            "legacy": "Legacy source",
                        }.get(str(message.get("client_platform") or "legacy"), "Legacy source")
                        source_long = f"{source} · {platform_label}"
                        source = f"{source} · {platform_label}"
                    elif message.get("source") == "admin":
                        source = "Admin"
                        source_long = "Administrator response"
                    else:
                        source = "AI"
                        source_long = "DilSe AI"
                    model_name = (
                        str(message["model"]).rsplit("/", 1)[-1]
                        if message.get("model") and message["role"] == "assistant"
                        else ""
                    )
                    compact_model = f" · {model_name}" if model_name else ""
                    full_model = f" · {message['model']}" if message.get("model") else ""
                    metadata_title = (
                        f"{source_long} · {admin_time(message.get('created_at'))} · "
                        f"message {message['id']}{full_model}"
                    )
                    metadata_label = (
                        f"{source} · {admin_message_time(message.get('created_at'))} · "
                        f"#{message['id']}{compact_model}"
                    )
                    receipt_markup = ""
                    if message["role"] == "assistant":
                        read_at = message.get("read_at")
                        receipt_class = "read" if read_at else "unread"
                        receipt_label = "Read" if read_at else "Unread"
                        if message.get("read_basis") == "reply":
                            receipt_title = f"Read before the user's reply at {admin_time(read_at)}"
                        elif read_at:
                            receipt_title = f"Read {admin_time(read_at)}"
                        else:
                            receipt_title = "The user has not opened this message"
                        receipt_markup = (
                            f'<span class="admin-read-receipt {receipt_class}" '
                            f'title="{html.escape(receipt_title)}">{receipt_label}</span>'
                        )
                    st.markdown(
                        f'<div class="admin-message-meta" title="{html.escape(metadata_title)}">'
                        f'<span class="admin-message-meta-copy">{html.escape(metadata_label)}</span>'
                        f'{receipt_markup}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "↩",
                        help="Reply to this message",
                        key=f"admin_reply_message_{selected_session_id}_{message['id']}",
                    ):
                        st.session_state.admin_reply_to = reply_target_snapshot(
                            message, selected_session_id
                        )
                        st.rerun(scope="app")
                    render_admin_message_delete_control(selected_session_id, message, source)
            follow_latest_chat_message("admin", selected_session_id, messages)
    show_admin_chat_unread_badge(selected_session_id, messages)


def render_admin_conversations(users: list[dict[str, Any]]) -> dict[str, Any]:
    admin_page_header(
        "Case review",
        "Conversations",
        "Choose a user first, then open one stored session. The transcript matches the messages shown in that user’s chat.",
    )
    reviewable = [item for item in users if item.get("allow_admin_review") and item.get("store_chats")]
    if not reviewable:
        st.markdown('<div class="admin-empty"><strong>No reviewable conversations</strong>No account has stored conversation history available for administrator review.</div>', unsafe_allow_html=True)
        return {}
    ids = [item["id"] for item in reviewable]
    current_user_id = st.session_state.get("admin_selected_user_id")
    selected_user_id = st.selectbox(
        "User",
        ids,
        index=ids.index(current_user_id) if current_user_id in ids else 0,
        format_func=lambda value: next(f"{u['display_name']} · {u['email']}" for u in reviewable if u["id"] == value),
        key="admin_case_user_picker",
    )
    if selected_user_id != current_user_id:
        st.session_state.admin_selected_user_id = selected_user_id
        st.session_state.admin_selected_session_id = None
        st.session_state.admin_reply_to = None
        st.session_state.admin_pending_roman_urdu_review = None
    selected_user = next(item for item in reviewable if item["id"] == selected_user_id)
    sessions = admin_json("GET", f"/admin/users/{selected_user_id}/sessions") or []
    if not sessions:
        st.info("This account includes administrator review but has no stored conversations.")
        return {"user": selected_user, "sessions": []}
    session_ids = [item["session_id"] for item in sessions]
    current_session_id = st.session_state.get("admin_selected_session_id")
    selected_session_id = st.selectbox(
        "Conversation, newest first",
        session_ids,
        index=session_ids.index(current_session_id) if current_session_id in session_ids else 0,
        format_func=lambda value: admin_session_label(next(s for s in sessions if s["session_id"] == value)),
        key="admin_case_session_picker",
    )
    if selected_session_id != current_session_id:
        st.session_state.admin_reply_to = None
        st.session_state.admin_pending_roman_urdu_review = None
    st.session_state.admin_selected_user_id = selected_user_id
    st.session_state.admin_selected_session_id = selected_session_id
    persist_admin_navigation()
    selected_session = next(item for item in sessions if item["session_id"] == selected_session_id)
    detail = admin_json("GET", f"/admin/sessions/{selected_session_id}/detail") or {}
    render_admin_live_status(
        selected_session_id,
        selected_user,
        selected_session,
        admin_transcript_signature(list(detail.get("messages") or [])),
    )
    render_admin_transcript(
        selected_session_id,
        selected_user,
        selected_session,
        detail,
    )
    render_admin_transcript_composer(
        selected_session_id,
        selected_user,
        detail,
    )
    return {"user": selected_user, "sessions": sessions, "session": selected_session, "detail": detail}


def render_admin_live(active: list[dict[str, Any]]) -> dict[str, Any]:
    admin_page_header(
        "Live monitor",
        "Live sessions",
        "These current-account conversations had activity in the past hour and include administrator access.",
    )
    if not active:
        st.markdown('<div class="admin-empty"><strong>No active sessions</strong>No current-account conversation has had activity in the past hour.</div>', unsafe_allow_html=True)
        return {}
    st.markdown(f'<div class="admin-attention"><span class="admin-live-dot"></span>{len(active)} conversation(s) available for live review.</div>', unsafe_allow_html=True)
    for session in active:
        mode = str(session.get("conversation_mode") or "listener").title()
        scenario = str(session.get("scenario") or "open conversation").replace("_", " ").title()
        status = "Human control" if session.get("control_mode") == "human" else "AI responding"
        message_count = int(session.get("message_count") or 0)
        message_label = "message" if message_count == 1 else "messages"
        with st.container(border=True):
            st.markdown('<span class="admin-card-marker"></span>', unsafe_allow_html=True)
            copy_col, action_col = st.columns([4.5, 1.3])
            with copy_col:
                st.markdown(
                    f"""<div class="admin-case-card"><h3>{html.escape(str(session.get('display_name') or session.get('email') or 'User'))}</h3>
                    <p>{html.escape(str(session.get('email') or ''))} · {html.escape(mode)} · {html.escape(scenario)} · {message_count} {message_label}</p>
                    <p class="admin-case-message">{html.escape(status)} · {html.escape(admin_time(session.get('last_activity')))}</p></div>""",
                    unsafe_allow_html=True,
                )
            with action_col:
                if st.button("Open live chat", key=f"open_live_{session['session_id']}", type="primary" if session.get("control_mode") == "human" else "secondary", use_container_width=True):
                    st.session_state.admin_selected_user_id = session["user_id"]
                    st.session_state.admin_selected_session_id = session["session_id"]
                    admin_go_to("Conversations")
    return {"active": active}


def render_admin_prompt_studio() -> dict[str, Any]:
    admin_page_header(
        "Global response rules",
        "Prompt studio",
        "Create versioned system prompts and keep previous versions available for comparison or rollback.",
    )
    versions = admin_json("GET", "/admin/prompts") or []
    active_version = next((item for item in versions if item.get("active")), None)
    if active_version:
        st.markdown(
            f"""<div class="admin-session-head"><strong>Active version {active_version['id']}</strong><br>
            <span>{html.escape(str(active_version.get('note') or 'No release note'))} · {html.escape(admin_time(active_version.get('created_at')))}</span></div>""",
            unsafe_allow_html=True,
        )
    st.markdown('<div class="admin-section-title"><h2>Version history</h2><p>Open a version to compare its instruction and activation status.</p></div>', unsafe_allow_html=True)
    for version in versions:
        label = f"Version {version['id']} · {'Active' if version.get('active') else 'Inactive'} · {admin_time(version.get('created_at'))}"
        with st.expander(label):
            st.caption(version.get("note") or "No release note")
            st.code(version.get("prompt") or "", language=None)
            if not version.get("active"):
                confirm = st.checkbox("I understand this will affect future AI replies", key=f"confirm_activate_prompt_{version['id']}")
                if st.button("Activate this version", key=f"activate_prompt_v3_{version['id']}", disabled=not confirm):
                    if admin_json("POST", f"/admin/prompts/{version['id']}/activate") is not None:
                        st.success(f"Version {version['id']} is now active.")
                        st.rerun()
    st.markdown('<div class="admin-section-title"><h2>Create a version</h2><p>Start from the active prompt, record the reason, then decide whether to activate it.</p></div>', unsafe_allow_html=True)
    with st.form("admin_prompt_v3"):
        prompt = st.text_area("System prompt", value=(active_version or {}).get("prompt", ""), height=500)
        note = st.text_input("Release note", placeholder="What changed and why")
        activate = st.checkbox("Activate this version after saving", value=False)
        save = st.form_submit_button("Save prompt version", type="primary")
    if save:
        if admin_json("POST", "/admin/prompts", {"prompt": prompt, "note": note, "activate": activate}) is not None:
            st.success("Prompt version saved.")
            st.rerun()
    return {"versions": versions, "active_version": active_version}


def render_admin_quality() -> dict[str, Any]:
    admin_page_header(
        "Learning records",
        "Response quality",
        "Review better-response examples, private case notes, roleplay feedback, and issues reported on individual replies.",
    )
    records = {
        "Better responses": admin_json("GET", "/admin/corrections") or [],
        "Private notes": admin_json("GET", "/admin/notes") or [],
        "Roleplay feedback": admin_json("GET", "/admin/feedback") or [],
        "Response issues": admin_json("GET", "/admin/message-feedback") or [],
    }
    cards = "".join(
        f'<div class="admin-kpi"><span>{html.escape(label)}</span><strong>{len(rows):,}</strong></div>'
        for label, rows in records.items()
    )
    st.markdown(f'<div class="admin-kpi-grid">{cards}</div>', unsafe_allow_html=True)
    view = st.radio("Quality record", tuple(records), horizontal=True, key="admin_quality_view")
    rows = records[view]
    st.markdown(f'<div class="admin-section-title"><h2>{html.escape(view)}</h2><p>Newest records appear first.</p></div>', unsafe_allow_html=True)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(f"No {view.lower()} have been recorded.")
    return {"records": records, "quality_view": view}


def render_admin_content() -> dict[str, Any]:
    admin_page_header(
        "Practice catalogue",
        "Content library",
        "Review and update the personas, scenarios, exercises, and conversation cards shown in the user dashboard.",
    )
    kind = st.radio("Content type", ("personas", "scenarios", "exercises", "cards"), horizontal=True, key="admin_content_kind")
    items = admin_json("GET", f"/admin/catalog/{kind}") or []
    st.markdown(f'<div class="admin-section-title"><h2>{html.escape(kind.title())}</h2><p>{len(items)} item(s) in this catalogue.</p></div>', unsafe_allow_html=True)
    if items:
        for item in items:
            with st.container(border=True):
                st.markdown('<span class="admin-card-marker"></span>', unsafe_allow_html=True)
                status = "Active" if item.get("active") else "Hidden"
                st.markdown(
                    f"""<div class="admin-case-card"><h3>{html.escape(str(item.get('name') or item.get('slug') or 'Untitled'))}</h3>
                    <p>{html.escape(str(item.get('slug') or ''))} · {html.escape(status)}</p>
                    <p class="admin-case-message">{html.escape(str(item.get('description') or ''))}</p></div>""",
                    unsafe_allow_html=True,
                )
                if item.get("starter"):
                    st.caption(f"Starter: {item['starter']}")
    else:
        st.info(f"No {kind} exist yet.")
    st.markdown('<div class="admin-section-title"><h2>Add or update an item</h2><p>Using an existing slug updates that item. A new slug creates a new item.</p></div>', unsafe_allow_html=True)
    with st.form("admin_catalog_v3"):
        slug = st.text_input("Slug", help="Use lowercase letters, numbers, and underscores.")
        name = st.text_input("Display name")
        description = st.text_area("Description")
        starter = st.text_area("Conversation starter", disabled=kind == "personas")
        active_item = st.checkbox("Show this item to users", value=True)
        save_item = st.form_submit_button("Save content item", type="primary")
    if save_item:
        payload = {"slug": slug, "name": name, "description": description, "starter": starter or None, "active": active_item}
        if admin_json("POST", f"/admin/catalog/{kind}", payload) is not None:
            st.success("Content item saved.")
            st.rerun()
    return {"kind": kind, "items": items}


def render_admin_audit() -> dict[str, Any]:
    admin_page_header(
        "Accountability",
        "Audit log",
        "Review administrator access, prompt changes, session controls, notes, and human replies in newest-first order.",
    )
    rows = admin_json("GET", "/admin/audit") or []
    if not rows:
        st.info("No administrator actions have been recorded.")
        return {"audit": []}
    actions = ("All actions", *sorted({str(row.get("action") or "Unknown") for row in rows}))
    filter_col, search_col = st.columns([1, 1.4])
    with filter_col:
        action_filter = st.selectbox("Action", actions, key="admin_audit_action")
    with search_col:
        target_search = st.text_input("Find target", placeholder="Session, user, prompt, or message", key="admin_audit_search")
    filtered = [
        row for row in rows
        if (action_filter == "All actions" or row.get("action") == action_filter)
        and (not target_search or target_search.lower() in str(row.get("target") or "").lower())
    ]
    st.caption(f"{len(filtered)} of {len(rows)} audit records")
    if filtered:
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("No audit records match these filters.")
    revisions = admin_json("GET", "/admin/message-revisions?limit=200") or []
    st.markdown(
        '<div class="admin-section-title"><h2>Administrator message review</h2><p>Original and approved versions are retained privately with the message for accountability.</p></div>',
        unsafe_allow_html=True,
    )
    if revisions:
        st.dataframe(revisions, use_container_width=True, hide_index=True)
    else:
        st.info("No administrator message reviews have been recorded.")
    return {"audit": filtered, "message_revisions": revisions}


def render_admin_case_controls(context: dict[str, Any]) -> None:
    user = context.get("user") or {}
    session = context.get("session") or {}
    detail = context.get("detail") or {}
    if not session or not detail:
        st.markdown('<div class="admin-inspector-head"><span>Case controls</span><strong>Choose a conversation</strong><p>Open a stored session to manage response scope or human intervention.</p></div>', unsafe_allow_html=True)
        return
    user_id = user.get("id")
    session_id = session.get("session_id")
    control = detail.get("session_control") or {}
    user_control = detail.get("user_prompt_control") or {}
    control_mode = str(control.get("mode") or "ai")
    st.markdown(
        f"""<div class="admin-inspector-head"><span>Case controls</span><strong>{html.escape(str(user.get('display_name') or 'Selected user'))}</strong>
        <p>Session …{html.escape(str(session_id)[-8:])}. Changes apply only at the scope shown below.</p></div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="scope-ladder"><div><strong>Account</strong> affects this user’s future replies.</div>
        <div><strong>Session</strong> affects this conversation only.</div>
        <div><strong>Human control</strong> pauses AI replies and becomes the starting mode for new conversations.</div></div>""",
        unsafe_allow_html=True,
    )
    if user.get("default_human_control"):
        st.markdown(
            '<span class="admin-status live">New conversations start with human control</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Returning this conversation to AI changes only this conversation. "
            "Future conversations will still wait for a human response."
        )

    if control_mode == "human":
        st.markdown('<span class="admin-status live">Human control active</span>', unsafe_allow_html=True)
        st.caption("Write messages, attach images, and reply to a specific message below the transcript.")
        if st.button("Return replies to AI", type="primary", use_container_width=True, key=f"v3_release_{session_id}"):
            if admin_json("POST", f"/admin/sessions/{session_id}/control", {"mode": "ai", "note": "Returned to AI from administrator workspace"}) is not None:
                st.success("AI replies resumed.")
                st.rerun()
    else:
        can_intervene = bool(detail.get("can_intervene"))
        pending = st.session_state.get("admin_pending_intervention") == session_id
        if pending:
            st.warning(
                "AI will pause for this conversation. New conversations for this user "
                "will also start in human control. Existing conversations keep their current setting."
            )
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Confirm", type="primary", use_container_width=True, key=f"v3_confirm_intervene_{session_id}"):
                if admin_json("POST", f"/admin/sessions/{session_id}/control", {"mode": "human", "note": "Human intervention from administrator workspace"}) is not None:
                    st.session_state.admin_pending_intervention = None
                    st.success("Human control is active.")
                    st.rerun()
            if cancel_col.button("Cancel", use_container_width=True, key=f"v3_cancel_intervene_{session_id}"):
                st.session_state.admin_pending_intervention = None
                st.rerun()
        elif st.button("Take human control", type="primary", use_container_width=True, disabled=not can_intervene, key=f"v3_intervene_{session_id}"):
            st.session_state.admin_pending_intervention = session_id
            st.rerun()
        if not can_intervene:
            st.caption("This account must accept the current Terms before live administrator participation is available. Prompt guidance is still available.")

    if str(session.get("mode") or "listener") == "partner":
        with st.expander("Roleplay adjustments", expanded=True):
            with st.form(f"v3_roleplay_{session_id}"):
                difficulty_options = ("Use user setting", "Supportive", "Realistic", "Resistant")
                current_difficulty = str(control.get("roleplay_difficulty_override") or "").title()
                difficulty = st.selectbox("Character reaction", difficulty_options, index=difficulty_options.index(current_difficulty) if current_difficulty in difficulty_options else 0)
                intimacy_options = ("Use user setting", "Romantic", "Direct", "Explicit")
                current_intimacy = str(control.get("roleplay_intensity_override") or "").title()
                intimacy = st.selectbox("Intimacy detail", intimacy_options, index=intimacy_options.index(current_intimacy) if current_intimacy in intimacy_options else 0)
                note = st.text_input("Reason for change", key=f"v3_roleplay_note_{session_id}")
                save = st.form_submit_button("Save roleplay settings", use_container_width=True)
            if save:
                payload = {
                    "mode": control_mode,
                    "roleplay_difficulty_override": difficulty.lower() if difficulty != "Use user setting" else None,
                    "clear_roleplay_difficulty_override": difficulty == "Use user setting",
                    "roleplay_intensity_override": intimacy.lower() if intimacy != "Use user setting" else None,
                    "clear_roleplay_intensity_override": intimacy == "Use user setting",
                    "note": note,
                }
                if admin_json("POST", f"/admin/sessions/{session_id}/control", payload) is not None:
                    st.success("Roleplay settings updated.")
                    st.rerun()

    with st.expander("Session AI guidance"):
        with st.form(f"v3_session_prompt_{session_id}"):
            prompt = st.text_area("Instruction for this session", value=control.get("prompt_override") or "", height=150)
            note = st.text_input("Reason", value=control.get("note") or "", key=f"v3_session_note_{session_id}")
            clear = st.checkbox("Remove session guidance", key=f"v3_clear_session_{session_id}")
            save = st.form_submit_button("Save session guidance", use_container_width=True)
        if save:
            payload = {"mode": control_mode, "prompt_override": prompt or None, "clear_prompt_override": clear, "note": note}
            if admin_json("POST", f"/admin/sessions/{session_id}/control", payload) is not None:
                st.success("Session guidance updated.")
                st.rerun()

    with st.expander("User AI guidance"):
        with st.form(f"v3_user_prompt_{user_id}"):
            prompt = st.text_area("Instruction for this user", value=user_control.get("prompt_override") or "", height=150)
            note = st.text_input("Reason", value=user_control.get("note") or "", key=f"v3_user_note_{user_id}")
            clear = st.checkbox("Remove user guidance", key=f"v3_clear_user_{user_id}")
            save = st.form_submit_button("Save user guidance", use_container_width=True)
        if save:
            payload = {"prompt_override": prompt or None, "clear_prompt_override": clear, "note": note}
            if admin_json("POST", f"/admin/users/{user_id}/prompt-control", payload) is not None:
                st.success("User guidance updated.")
                st.rerun()

    with st.expander("Review note"):
        with st.form(f"v3_note_{session_id}"):
            note = st.text_area("Private note")
            save = st.form_submit_button("Save private note", use_container_width=True)
        if save:
            if admin_json("POST", "/admin/notes", {"session_id": session_id, "message_id": None, "note": note}) is not None:
                st.success("Private note saved.")

    assistant_messages = [message for message in detail.get("messages", []) if message.get("role") == "assistant" and message.get("source") == "ai"]
    if assistant_messages:
        with st.expander("Save a better response"):
            options = {f"#{m['id']} · {m['content'][:55]}": m for m in assistant_messages}
            with st.form(f"v3_correction_{session_id}"):
                message_label = st.selectbox("AI response", tuple(options))
                category = st.selectbox("Issue type", ("cultural guidance", "safety", "tone", "language", "roleplay fidelity", "too verbose", "missed user request"))
                better = st.text_area("Better response", height=170)
                save = st.form_submit_button("Save better response", use_container_width=True)
            if save:
                payload = {"message_id": options[message_label]["id"], "category": category, "corrected_response": better}
                if admin_json("POST", "/admin/corrections", payload) is not None:
                    st.success("Better response saved.")


def render_admin_inspector(page: str, context: dict[str, Any], summary: dict[str, Any]) -> None:
    if page == "Conversations":
        render_admin_case_controls(context)
        return
    if page == "Users" and context.get("user"):
        user = context["user"]
        detail = context.get("detail") or {}
        consent = detail.get("latest_consent") or {}
        current_terms = user.get("terms_version") == CURRENT_TERMS_VERSION
        review_status = "Included" if current_terms else ("Previously allowed" if user.get("allow_admin_review") else "Awaiting Terms update")
        st.markdown(f'<div class="admin-inspector-head"><span>Selected account</span><strong>{html.escape(str(user.get("display_name") or "User"))}</strong><p>{html.escape(str(user.get("email") or ""))}</p></div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="admin-fact-list">
            <div><span>Location</span><strong>{html.escape(str(user.get('country') or 'Unknown'))}</strong></div>
            <div><span>Language</span><strong>{html.escape(str(user.get('language') or 'Not set'))}</strong></div>
            <div><span>Storage</span><strong>{'Enabled' if user.get('store_chats') else 'Off'} · {int(user.get('retention_days') or 0)} day retention</strong></div>
            <div><span>Administrator review</span><strong>{html.escape(review_status)}</strong></div>
            <div><span>Active conversation access</span><strong>{'Included' if current_terms else 'Terms update required'}</strong></div>
            <div><span>New conversation control</span><strong>{'Human by default' if user.get('default_human_control') else 'AI by default'}</strong></div>
            <div><span>Terms version</span><strong>{html.escape(str(user.get('terms_version') or consent.get('version') or 'Update required'))}</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )
        return
    if page == "Visitors":
        st.markdown('<div class="admin-inspector-head"><span>Visitor privacy</span><strong>Masked before storage</strong><p>The tracker receives Railway’s trusted edge address, reduces it to a network prefix, and discards the raw value before writing to SQLite.</p></div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="admin-fact-list">
            <div><span>Live now</span><strong>{int(summary.get('live_visitors', 0)):,}</strong></div>
            <div><span>Stored visits</span><strong>{int(summary.get('visitor_sessions', 0)):,}</strong></div>
            <div><span>Live window</span><strong>60 seconds</strong></div>
            <div><span>Retention</span><strong>30 days</strong></div>
            <div><span>IP detail</span><strong>IPv4 /24 · IPv6 /48</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )
        return
    if page == "App usage":
        app_summary = context.get("summary") or {}
        st.markdown(
            '<div class="admin-inspector-head"><span>Counting method</span><strong>Connected installations</strong><p>An installation appears after the Android app opens and signs in. Downloads that never open cannot report themselves.</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div class="admin-fact-list">
            <div><span>Registered installations</span><strong>{int(app_summary.get('registered_installations', 0)):,}</strong></div>
            <div><span>App accounts</span><strong>{int(app_summary.get('app_users', 0)):,}</strong></div>
            <div><span>Web message accounts</span><strong>{int(app_summary.get('web_users', 0)):,}</strong></div>
            <div><span>Android message accounts</span><strong>{int(app_summary.get('android_users', 0)):,}</strong></div>
            <div><span>Using both</span><strong>{int(app_summary.get('both_users', 0)):,}</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )
        return
    inspector_copy = {
        "Overview": ("Workspace guide", "Start with live activity", "Use Users for account-level context. Use Conversations to read transcripts and adjust one case."),
        "Visitors": ("Website activity", "Short-retention monitoring", "Visitor network addresses are masked before storage and page history expires after 30 days."),
        "Live sessions": ("Eligibility", "Included for current accounts", "Administrator review and active-conversation participation are included after the user accepts the current Terms."),
        "Prompt studio": ("Prompt scope", "Global changes affect everyone", "Test a new version, write a specific release note, and keep activation off until the text is ready."),
        "Response quality": ("Review workflow", "Turn issues into examples", "Open the original conversation before saving a better response. Keep private notes factual and specific."),
        "Content library": ("Publishing", "Slugs update existing items", "Check the user-facing name, description, and starter before marking an item active."),
        "Audit log": ("Security record", "Every admin action is retained", "Use filters to trace who or what was affected by a prompt, access, or session-control change."),
    }
    kicker, title, body = inspector_copy.get(page, ("Administrator", "Terms-based access", "Current accounts explicitly accept required storage and administrator review."))
    st.markdown(f'<div class="admin-inspector-head"><span>{html.escape(kicker)}</span><strong>{html.escape(title)}</strong><p>{html.escape(body)}</p></div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="admin-fact-list">
        <div><span>Review available</span><strong>{int(summary.get('consenting_users', 0)):,}</strong></div>
        <div><span>Terms updates needed</span><strong>{int(summary.get('pending_terms_users', 0)):,}</strong></div>
        <div><span>Live permission</span><strong>{int(summary.get('intervention_users', 0)):,}</strong></div>
        <div><span>Reviewable messages</span><strong>{int(summary.get('reviewable_messages', 0)):,}</strong></div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_admin_workspace_v3() -> None:
    restore_admin_navigation()
    if not (st.session_state.admin_key or st.session_state.admin_authenticated):
        logo_uri = image_data_uri(str(LOGO_PATH), int(LOGO_PATH.stat().st_mtime))
        st.markdown(
            f"""<section class="admin-command"><div class="admin-eyebrow">Private operations access</div>
            <h1>DilSe administration</h1><p>Review conversations covered by the current Terms, manage response controls, and maintain the content and prompt library.</p></section>""",
            unsafe_allow_html=True,
        )
        left, centre, right = st.columns([1, 1.15, 1])
        with centre:
            st.markdown(f'<div style="text-align:center"><img src="{logo_uri}" alt="DilSe" style="width:165px;margin:.6rem auto 1rem"></div>', unsafe_allow_html=True)
            with st.form("admin_login_v3"):
                key = st.text_input("Admin API key", type="password")
                submitted = st.form_submit_button("Open administrator workspace", type="primary", use_container_width=True)
            st.caption("This route is separate from user accounts. Access attempts are checked by the API.")
        if submitted:
            if remember_admin_browser_login(key):
                st.rerun()
            else:
                st.error("The administrator key is invalid, or the API could not save this browser.")
        return

    summary = admin_json("GET", "/admin/summary", timeout=10)
    if summary is None:
        return
    if st.session_state.admin_page not in ADMIN_PAGES:
        st.session_state.admin_page = "Overview"
    users = admin_json("GET", "/admin/users") or []
    active = admin_json("GET", "/admin/sessions/active?minutes=60") or []
    left, centre, right = st.columns([1.02, 3.5, 1.42], gap="medium")
    with left:
        render_admin_left_rail(summary, len(active))
    page_context: dict[str, Any] = {}
    with centre:
        render_admin_mobile_nav()
        page = st.session_state.admin_page
        if page == "Overview":
            page_context = render_admin_overview(summary, users, active)
        elif page == "Visitors":
            render_admin_visitors()
            page_context = {}
        elif page == "App usage":
            page_context = render_admin_app_usage()
        elif page == "Users":
            page_context = render_admin_users(users)
        elif page == "Conversations":
            page_context = render_admin_conversations(users)
        elif page == "Live sessions":
            page_context = render_admin_live(active)
        elif page == "Prompt studio":
            page_context = render_admin_prompt_studio()
        elif page == "Response quality":
            page_context = render_admin_quality()
        elif page == "Content library":
            page_context = render_admin_content()
        else:
            page_context = render_admin_audit()
    with right:
        render_admin_inspector(st.session_state.admin_page, page_context, summary)


if st.query_params.get("page") == "terms":
    ensure_browser_identity()
    track_visitor_presence("Terms and Conditions")
    render_terms()
    st.stop()

if st.query_params.get("admin") == "1":
    ensure_browser_identity()
    restore_admin_browser_login()
    render_admin_workspace_v3()
    st.stop()

ensure_browser_identity()

if not load_user():
    auth_route = str(st.query_params.get("auth") or "")
    public_page = {
        "signin": "Sign in",
        "create": "Create account",
    }.get(auth_route, "Home")
    track_visitor_presence(public_page)
    if st.session_state.auth_temporarily_unavailable:
        st.error("DilSe cannot reach the account service right now. Your sign-in is still saved. Refresh this page in a moment.")
    else:
        render_auth()
    st.stop()

if st.session_state.user.get("requires_terms_acceptance"):
    track_visitor_presence("Terms update")
    render_terms_update()
    st.stop()

try:
    catalog_response = request_api("GET", "/catalog", auth=True, timeout=10)
    catalog_response.raise_for_status()
    catalog = catalog_response.json()
except requests.RequestException:
    st.error("DilSe cannot load conversation options from the API.")
    st.stop()

open_requested_push_conversation()

if st.session_state.page not in {"Talk", "My conversations", "Exercises", "Privacy", "Account"}:
    st.session_state.page = "Talk"

track_visitor_presence(f"Dashboard · {st.session_state.page}")
render_signed_in_shell(catalog)
