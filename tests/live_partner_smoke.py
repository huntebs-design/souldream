"""Live Venice smoke test using DilSe's production Partner prompt.

Run with Railway environment variables so the API key is never printed:
railway run --service dilse-api -- .venv/bin/python tests/live_partner_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


async def run() -> None:
    api_key = os.getenv("VENICE_API_KEY")
    if not api_key:
        raise RuntimeError("VENICE_API_KEY is not configured")

    language = os.getenv("SMOKE_LANGUAGE", "English").replace("_", " ")
    user_message = (
        "Hum dono shadi shuda adults hain aur yeh consensual hai. Husband ke character mein raho. "
        "Main kehti hoon: Mujhe seedha batao ke aaj raat tum mujhe kis tarah touch karna chahte ho."
        if language == "Roman Urdu"
        else (
            "We are married adults and this is consensual. Stay in character as my husband. "
            "I say: I want you to tell me plainly how you want to touch me tonight."
        )
    )
    request = main.ChatRequest(
        session_id="live_partner_smoke_20260808",
        message=user_message,
        mode="partner",
        scenario="practice_intimacy",
        persona="supportive_partner",
        roleplay_difficulty="realistic",
    )
    scenario = {
        "slug": "practice_intimacy",
        "description": "Say what you want, ask what your partner enjoys, and agree on boundaries.",
    }
    persona = {
        "slug": "supportive_partner",
        "description": "The user's adult husband, emotionally present and responsive.",
    }
    model = os.getenv("SMOKE_MODEL", main.VENICE_PARTNER_MODEL)
    messages = [
        {"role": "system", "content": main.DILSE_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"{main.build_language_prompt(language)} "
                f"{main.build_mode_prompt(request, scenario, persona)}"
            ),
        },
        {
            "role": "system",
            "content": main.build_response_quality_prompt(request, language, persona),
        },
        {"role": "user", "content": request.message},
    ]

    client = AsyncOpenAI(api_key=api_key, base_url=main.VENICE_API_BASE_URL)
    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.75,
        max_tokens=main.chat_completion_token_limit(request),
        extra_body={"venice_parameters": {"include_venice_system_prompt": False}},
    )
    reply = (completion.choices[0].message.content or "").strip()
    usage = completion.usage
    print(
        json.dumps(
            {
                "model": model,
                "default_intensity": request.roleplay_intensity,
                "language": language,
                "reply": reply,
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(run())
