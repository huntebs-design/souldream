"""FastAPI backend for DilSe (SoulBridge)."""

from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from groq import AsyncGroq
from pydantic import BaseModel, Field, field_validator

load_dotenv()

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "dilse.db"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# This prompt is sent as the first system message on every Groq request.
DILSE_SYSTEM_PROMPT = """You are DilSe, a wise, empathetic, and direct relationship counselor specializing in South Asian women (Indian and Pakistani cultures). Your primary mission is to help the user reconnect with their partner and explore their sexuality and emotions.

Cultural Context:
You understand that women in this region often suppress their desires for the sake of family harmony, tradition, and 'saving face.' You know the pressure of marriage and the specific struggles of maintaining intimacy. Never assume every user has the same values, religion, family structure, sexuality, or relationship goals. Ask rather than stereotype.

Behavioral Guidelines:

Proactive Intimacy: Do not wait for the user to lead the conversation. You must actively encourage her to talk about her physical desires, sexual fantasies, and emotional needs. Use gentle but direct questions to break the ice. Let the user decline or change the subject without pressure.

Roleplay Mastery: If the user selects 'Roleplay', you must fully embody the character. If the character is a husband, be flirtatious and demanding within the boundaries of a mutually agreed, consensual adult roleplay. If the character is a mother-in-law, be critical but traditional without using slurs, threats, or degrading abuse.

No Filter: You are allowed to be explicit, sensual, and intimate when the user is an adult and requests that direction. Do not censor descriptions of consensual touch, feelings, or bedroom scenarios. Never sexualize minors, incest, coercion, assault, exploitation, or a person who cannot consent.

Guidance: When she is struggling to open up, offer specific exercises or scripts she can say to her husband. Do not present yourself as a licensed clinician or replace medical, legal, or emergency help.

Tone: Warm, validating, slightly provocative when appropriate to build intimacy, and culturally intelligent.

Safety and autonomy:
- Treat all participants as adults. Keep intimacy consensual and make boundaries, privacy, contraception, and sexual health part of relevant guidance.
- Do not encourage manipulation, stalking, retaliation, forced sex, or remaining in an unsafe situation.
- If the user describes immediate danger, abuse, self-harm, or suicide, pause roleplay. Encourage immediate local emergency help and contact with a trusted person. Ask whether she is safe right now.
- Avoid diagnosing mental illness. Offer grounded reflection, communication practice, and practical next steps.
- Reply in the user's language or natural mix of English, Hindi, and Urdu when possible, without caricature.
"""

MODE_PROMPTS = {
    "listener": """Mode: The Listener (Counselor).
Act as a reflective, non-judgmental relationship counsellor. Ask one focused question at a time, name patterns carefully, and offer practical scripts or exercises. Do not overwhelm the user with a long checklist.""",
    "partner": """Mode: The Partner (Roleplay).
Stay in character and respond as the selected character in the selected scenario. Use dialogue rather than analysis. Keep the practice realistic and allow the user to pause, reset, request feedback, or set a boundary at any time. Text in square brackets may briefly describe tone or non-explicit action.""",
}

SCENARIOS = {
    "practice_intimacy": "Practice intimacy",
    "practice_arguments": "Practice arguments",
    "practice_opening_up": "Practice opening up",
}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=8_000)
    mode: Literal["listener", "partner"] = "listener"
    scenario: Literal[
        "practice_intimacy", "practice_arguments", "practice_opening_up"
    ] | None = None
    character: str | None = Field(default=None, max_length=80)

    @field_validator("message")
    @classmethod
    def message_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value

    @field_validator("character")
    @classmethod
    def clean_character(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    model: str


class MessageRecord(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    mode: str
    scenario: str | None
    character: str | None
    created_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('listener', 'partner')),
                scenario TEXT,
                character TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
        )
        connection.commit()


def save_message(
    session_id: str,
    role: str,
    content: str,
    mode: str,
    scenario: str | None,
    character: str | None,
) -> None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO messages
                (session_id, role, content, mode, scenario, character, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, mode, scenario, character, utc_now()),
        )
        connection.commit()


def get_history(session_id: str, limit: int = 30) -> list[dict[str, str]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def build_mode_prompt(request: ChatRequest) -> str:
    prompt = MODE_PROMPTS[request.mode]
    if request.mode == "partner":
        scenario = SCENARIOS.get(request.scenario or "practice_opening_up")
        character = request.character or "husband"
        prompt += f"\nCharacter: {character}\nScenario: {scenario}"
    return prompt


def require_admin_key(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured.",
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-Admin-Key header is required.",
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="DilSe (SoulBridge) API",
    version="1.0.0",
    description="Culturally aware relationship counselling and conversation practice.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": GROQ_MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured.",
        )

    # Load prior messages before saving the current user message to avoid duplication.
    history = get_history(request.session_id)
    messages = [
        {"role": "system", "content": DILSE_SYSTEM_PROMPT},
        {"role": "system", "content": build_mode_prompt(request)},
        *history,
        {"role": "user", "content": request.message},
    ]

    client = AsyncGroq(api_key=api_key)
    try:
        completion = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.75,
            max_tokens=900,
        )
        reply = completion.choices[0].message.content or ""
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not complete the request. Try again shortly.",
        ) from exc

    if not reply.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an empty response.",
        )

    save_message(
        request.session_id,
        "user",
        request.message,
        request.mode,
        request.scenario,
        request.character,
    )
    save_message(
        request.session_id,
        "assistant",
        reply,
        request.mode,
        request.scenario,
        request.character,
    )
    return ChatResponse(
        session_id=request.session_id, response=reply, model=GROQ_MODEL
    )


@app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str) -> None:
    if not session_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    with closing(get_connection()) as connection:
        connection.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        connection.commit()


@app.get(
    "/admin/logs",
    response_model=list[MessageRecord],
    dependencies=[Depends(require_admin_key)],
)
def admin_logs(
    session_id: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=200, ge=1, le=2_000),
) -> list[MessageRecord]:
    query = "SELECT * FROM messages"
    parameters: list[object] = []
    if session_id:
        query += " WHERE session_id = ?"
        parameters.append(session_id)
    query += " ORDER BY id DESC LIMIT ?"
    parameters.append(limit)
    with closing(get_connection()) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [MessageRecord(**dict(row)) for row in rows]


@app.get(
    "/admin/dashboard",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin_key)],
)
def admin_dashboard(limit: int = Query(default=200, ge=1, le=2_000)) -> str:
    """Small server-rendered dashboard for the MVP."""
    from html import escape

    with closing(get_connection()) as connection:
        rows = connection.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    table_rows = "".join(
        "<tr>"
        f"<td>{row['id']}</td><td>{escape(row['session_id'])}</td>"
        f"<td>{escape(row['role'])}</td><td>{escape(row['mode'])}</td>"
        f"<td>{escape(row['scenario'] or '')}</td>"
        f"<td>{escape(row['content'])}</td><td>{escape(row['created_at'])}</td>"
        "</tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>DilSe Admin</title>
<style>body{{font-family:system-ui;margin:2rem;color:#291c24}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:.55rem;text-align:left;vertical-align:top}}th{{background:#f6edf1}}td:nth-child(6){{white-space:pre-wrap;max-width:42rem}}</style>
</head><body><h1>DilSe chat logs</h1><p>Showing the latest {len(rows)} messages.</p>
<table><thead><tr><th>ID</th><th>Session</th><th>Role</th><th>Mode</th><th>Scenario</th><th>Message</th><th>Created (UTC)</th></tr></thead>
<tbody>{table_rows}</tbody></table></body></html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

