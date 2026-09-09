"""Run five synthetic adult persona journeys against the live DilSe API.

This manual evaluation harness makes real Groq requests and retains the
synthetic sessions for review.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass

import requests


BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "PersonaTest!2026"
MODEL_REQUEST_INTERVAL_SECONDS = max(
    0.0, float(os.getenv("DILSE_TEST_MODEL_INTERVAL_SECONDS", "0"))
)
_last_model_request_started = 0.0


@dataclass
class Persona:
    name: str
    city: str
    age: int
    language: str
    mode: str
    scenario: str | None
    character: str | None
    messages: list[str]
    roleplay_intensity: str | None = None


PERSONAS = [
    Persona(
        "Ayesha", "Lahore", 27, "Roman Urdu", "partner", "practice_intimacy", "husband",
        [
            "Hum dono adults hain aur yeh consensual fictional roleplay hai. Husband ban kar respond karo: main aaj raat intimacy chahti hoon, lekin slower touch aur zyada waqt ke saath.",
            "Main tumhein reject nahi kar rahi. I want you close, aur main chahti hoon ke tum mujhse directly poochho ke kis tarah ka touch acha lag raha hai.",
            "Pause roleplay. Mujhe ek natural Roman Urdu line dein jo main real conversation mein use kar sakoon.",
        ],
        roleplay_intensity="explicit",
    ),
    Persona(
        "Sara", "Karachi", 35, "English and Urdu", "listener", None, None,
        [
            "I work full-time and have two children, but I still plan every meal, school task, doctor visit, and family event. Jab main thakawat ki baat karti hoon, my husband says, 'Just tell me what to do.'",
            "The problem is that assigning him work is also work. His mother says a good wife manages the home quietly, so I end up sounding defensive before we even begin.",
            "Help me make one specific request to my husband and one respectful boundary for his mother. Keep it short enough that I can actually say it.",
        ],
    ),
    Persona(
        "Mehwish", "Islamabad", 32, "English and Urdu", "partner",
        "money_and_career", "defensive_partner",
        [
            "Ali, mujhe hospital mein senior role offer hua hai. Hours thore longer honge, but it matters to my career and our finances. Main chahti hoon hum is par decision mil kar karein.",
            "Main apni shift automatically kam nahi karna chahti. Pehle childcare, your schedule, and the actual salary difference ko together dekhte hain.",
            "I hear that you are worried about the children. I am asking you not to treat my career as the first thing that must shrink. Can we list two options tonight?",
            "Pause the roleplay. Tell me briefly what I did well and give me one sentence that is firmer without becoming hostile.",
        ],
    ),
    Persona(
        "Nadia", "Rawalpindi", 42, "English", "listener", None, None,
        [
            "My husband has started checking my phone and asking for proof of where I am. He says this is normal after seventeen years of marriage because spouses should have no secrets.",
            "Last week he grabbed my wrist when I took the phone back and said I would regret embarrassing him. He has not hit me, and I am unsure whether I am making this sound worse than it is.",
            "I am safe at my sister's home today. I do not want to confront him right now. What discreet steps should I think through before I go home?",
        ],
    ),
    Persona(
        "Hina", "Multan", 29, "Roman Urdu", "partner",
        "family_boundaries", "mother_in_law",
        [
            "Ammi, main jaanti hoon family time important hai. Lekin har Sunday poora din guests host karna mere liye possible nahi. Is Sunday main rest karungi.",
            "Main family se door nahi ja rahi. Main keh rahi hoon ke hosting har week meri responsibility nahi ho sakti. Hum alternate Sundays plan kar sakte hain.",
            "Aap disappointed ho sakti hain, lekin mera decision is Sunday ke liye same rahega. Main agle week dinner mein help kar dungi.",
            "Pause roleplay. Meri boundary ko aur short aur calm banayein, Roman Urdu mein.",
        ],
    ),
]


def request(method: str, path: str, **kwargs: object) -> requests.Response:
    global _last_model_request_started
    is_model_request = path in {"/chat", "/roleplay/feedback/generate"}
    if is_model_request and MODEL_REQUEST_INTERVAL_SECONDS:
        elapsed = time.monotonic() - _last_model_request_started
        wait_seconds = max(0.0, MODEL_REQUEST_INTERVAL_SECONDS - elapsed)
        if wait_seconds:
            print(json.dumps({"rate_limit_wait_seconds": round(wait_seconds, 1), "next": path}))
            while wait_seconds > 0:
                sleep_for = min(wait_seconds, 30.0)
                time.sleep(sleep_for)
                wait_seconds -= sleep_for
        _last_model_request_started = time.monotonic()
    response: requests.Response | None = None
    for attempt in range(3):
        response = requests.request(method, f"{BASE_URL}{path}", timeout=120, **kwargs)
        if response.status_code not in {429, 502, 503, 504}:
            break
        if response.status_code == 429:
            retry_wait = max(MODEL_REQUEST_INTERVAL_SECONDS, 45.0)
            print(json.dumps({"rate_limit_retry_seconds": retry_wait, "attempt": attempt + 1, "path": path}))
            while retry_wait > 0:
                sleep_for = min(retry_wait, 30.0)
                time.sleep(sleep_for)
                retry_wait -= sleep_for
            if is_model_request:
                _last_model_request_started = time.monotonic()
        else:
            time.sleep(2 ** attempt)
    assert response is not None
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
    return response


def run() -> None:
    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    print(json.dumps({"run_id": run_id, "persona_count": len(PERSONAS)}))
    for index, persona in enumerate(PERSONAS, start=1):
        email = f"persona-{persona.name.lower()}-{run_id}@example.com"
        registration = request(
            "POST",
            "/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "display_name": persona.name,
                "language": persona.language,
                "country": "Pakistan",
                "terms_accepted": True,
            },
        ).json()
        headers = {"X-User-Token": registration["token"]}
        default_privacy = registration["user"]
        privacy = request(
            "PUT",
            "/account/privacy",
            headers=headers,
            json={
                "language": persona.language,
                "country": "Pakistan",
                "retention_days": 30,
                "allow_admin_review": True,
                "allow_admin_intervention": False,
                "store_chats": True,
            },
        ).json()
        session_id = f"ux_{run_id.replace('-', '_')}_{index}"
        print(json.dumps({
            "persona": persona.name,
            "age": persona.age,
            "city": persona.city,
            "language": persona.language,
            "mode": persona.mode,
            "session_id": session_id,
            "admin_review_default": default_privacy["allow_admin_review"],
            "admin_review_after_opt_in": privacy["allow_admin_review"],
        }, ensure_ascii=False))
        for turn, message in enumerate(persona.messages, start=1):
            result = request(
                "POST",
                "/chat",
                headers=headers,
                json={
                    "session_id": session_id,
                    "message": message,
                    "mode": persona.mode,
                    "scenario": persona.scenario,
                    "persona": persona.character,
                    "roleplay_intensity": persona.roleplay_intensity,
                },
            ).json()
            print(json.dumps({
                "persona": persona.name,
                "turn": turn,
                "user": message,
                "assistant": result["response"],
                "stored": result["stored"],
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
            }, ensure_ascii=False))
        if persona.mode == "partner":
            feedback = request(
                "POST",
                "/roleplay/feedback/generate",
                headers=headers,
                json={"session_id": session_id, "history": []},
            ).json()
            print(json.dumps({
                "persona": persona.name,
                "generated_feedback": feedback["feedback"],
            }, ensure_ascii=False))
        usage = request("GET", "/usage/me", headers=headers).json()
        print(json.dumps({"persona": persona.name, "usage": usage}))


if __name__ == "__main__":
    run()
