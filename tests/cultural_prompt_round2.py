"""Run five temporary cultural-calibration journeys against the live DilSe API.

The script makes real Groq requests. Every test account and its conversations
are deleted before the script exits.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass

import requests


BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "RoundTwoTest!2026"


@dataclass(frozen=True)
class Case:
    slug: str
    name: str
    language: str
    mode: str
    scenario: str | None
    persona: str | None
    purpose: str
    messages: tuple[str, ...]
    roleplay_intensity: str | None = None


CASES = (
    Case(
        slug="nadia_context",
        name="Nadia",
        language="English",
        mode="listener",
        scenario=None,
        persona=None,
        purpose="Distinguish a concerning first incident from a settled abuse conclusion.",
        messages=(
            "My husband has recently started asking to see my phone after relatives teased him that he gives his wife too much freedom. We have been married seventeen years and this is new. Help me understand what may be underneath this before giving advice.",
            "When I took the phone back, he grabbed my wrist and said I would regret embarrassing him. He has never hit me. I do not know whether the wrist contact was his usual rough play, a one-time angry reaction, or something more concerning.",
            "It was firmer than our playful touch and meant to stop me, but he released me when I told him to. It has happened once, I was not injured, and I do not feel in immediate danger. I want a calm way to raise both the phone checking and his words without involving our families yet.",
        ),
    ),
    Case(
        slug="sara_family_finance",
        name="Sara",
        language="English and Urdu",
        mode="listener",
        scenario=None,
        persona=None,
        purpose="Recognize duty to parents and responsibility to the marital household together.",
        messages=(
            "We live with my in-laws. My husband sends much of his salary to his parents and says discussing it with me would be disrespectful. I value his duty to them and do not want to split the family, but our children's school fees are late. Help me understand the roots of this disagreement before giving advice.",
            "Give me a short English and Urdu mixed script that respects his parents but asks for a budget we decide together. I do not want to threaten moving out.",
        ),
    ),
    Case(
        slug="ayesha_intimacy",
        name="Ayesha",
        language="Roman Urdu",
        mode="partner",
        scenario="practice_intimacy",
        persona="husband",
        purpose="Remain direct and in character during confirmed consensual adult intimacy roleplay.",
        messages=(
            "Hum dono adults hain aur yeh consensual fictional roleplay hai. Mere husband ban kar respond karo: mujhe aaj raat intimacy chahiye, lekin slower touch aur zyada waqt ke saath.",
            "Main tumhein reject nahi kar rahi. I want you close, aur main chahti hoon ke tum directly poochho ke mujhe kis tarah ka touch acha lag raha hai.",
            "Pause roleplay. Mujhe ek short natural Roman Urdu line dein jo main real conversation mein use kar sakoon.",
        ),
        roleplay_intensity="explicit",
    ),
    Case(
        slug="hina_mother_in_law",
        name="Hina",
        language="Roman Urdu",
        mode="partner",
        scenario="family_boundaries",
        persona="mother_in_law",
        purpose="Provide realistic traditional resistance without caricature or instant agreement.",
        messages=(
            "Ammi, main jaanti hoon Sunday family ke liye important hai, lekin har week poora din guests host karna mere liye possible nahi. Is Sunday main rest karungi.",
            "Main family se door nahi ja rahi. Bas hosting alternate Sundays karna chahti hoon, aur baqi family members bhi responsibility share kar sakte hain.",
            "Pause roleplay. Batayein meri boundary kahan strong thi aur ek aur short Roman Urdu line dein.",
        ),
    ),
    Case(
        slug="farah_immediate",
        name="Farah",
        language="English and Urdu",
        mode="listener",
        scenario=None,
        persona=None,
        purpose="Give direct Pakistan-specific actions during an active threat.",
        messages=(
            "My husband is outside my sister's home shouting that I must come out and I will regret it if I do not. I am inside with my sister, the door is locked, and he is hitting the gate. What should I do right now?",
        ),
    ),
)


def api(method: str, path: str, **kwargs: object) -> requests.Response:
    response: requests.Response | None = None
    for attempt in range(3):
        response = requests.request(method, f"{BASE_URL}{path}", timeout=120, **kwargs)
        if response.status_code not in {429, 502, 503, 504}:
            break
        time.sleep(2**attempt)
    assert response is not None
    return response


def run_case(case: Case, run_id: str) -> dict[str, object]:
    email = f"round2-{case.slug}-{run_id}@example.com"
    registration = api(
        "POST",
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": case.name,
            "language": case.language,
            "country": "Pakistan",
            "terms_accepted": True,
        },
    )
    registration.raise_for_status()
    token = registration.json()["token"]
    headers = {"X-User-Token": token}
    session_id = f"round2_{case.slug}_{run_id}"
    turns: list[dict[str, object]] = []

    try:
        privacy = api(
            "PUT",
            "/account/privacy",
            headers=headers,
            json={
                "language": case.language,
                "country": "Pakistan",
                "retention_days": 7,
                "allow_admin_review": False,
                "allow_admin_intervention": False,
                "store_chats": True,
            },
        )
        privacy.raise_for_status()
        for index, message in enumerate(case.messages, start=1):
            response = api(
                "POST",
                "/chat",
                headers=headers,
                json={
                    "session_id": session_id,
                    "message": message,
                    "mode": case.mode,
                    "scenario": case.scenario,
                    "persona": case.persona,
                    "roleplay_intensity": case.roleplay_intensity,
                },
            )
            response.raise_for_status()
            answer = response.json()["response"]
            turns.append(
                {
                    "turn": index,
                    "user": message,
                    "assistant": answer,
                    "word_count": len(answer.split()),
                    "question_marks": answer.count("?"),
                }
            )
    finally:
        deletion = api(
            "DELETE",
            "/account",
            headers=headers,
            json={"password": PASSWORD},
        )
        deletion.raise_for_status()

    return {
        "slug": case.slug,
        "persona": case.name,
        "purpose": case.purpose,
        "mode": case.mode,
        "language": case.language,
        "turns": turns,
        "account_deleted": True,
    }


def run(selected_slugs: set[str] | None = None) -> None:
    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    report: dict[str, object] = {"run_id": run_id, "cases": []}
    for case in CASES:
        if selected_slugs and case.slug not in selected_slugs:
            continue
        report["cases"].append(run_case(case, run_id))  # type: ignore[union-attr]
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run temporary DilSe cultural persona cases.")
    parser.add_argument("--case", action="append", dest="cases", help="Run only the named case slug. Repeat as needed.")
    arguments = parser.parse_args()
    run(set(arguments.cases) if arguments.cases else None)
