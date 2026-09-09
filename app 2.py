"""Streamlit frontend for DilSe (SoulBridge)."""

from __future__ import annotations

import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 90

st.set_page_config(page_title="DilSe | SoulBridge", page_icon="🌸", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background: #fffaf7; }
    [data-testid="stSidebar"] { background: #f8ecec; }
    .dilse-subtitle { color: #6f4a58; margin-top: -0.8rem; }
    .privacy-note { padding: .75rem; border-radius: .6rem; background: #f3e6dd; color: #4d3840; font-size: .88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []


def reset_conversation() -> None:
    old_session_id = st.session_state.session_id
    try:
        requests.delete(
            f"{BACKEND_URL}/sessions/{old_session_id}", timeout=10
        ).raise_for_status()
    except requests.RequestException:
        st.warning("The chat was cleared here, but the server could not confirm deletion.")
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []


with st.sidebar:
    st.header("Conversation setup")
    mode_label = st.selectbox(
        "Mode",
        ["The Listener (Counselor)", "The Partner (Roleplay)"],
    )
    mode = "listener" if mode_label.startswith("The Listener") else "partner"

    scenario = None
    character = None
    if mode == "partner":
        scenario_label = st.selectbox(
            "Scenario",
            ["Practice intimacy", "Practice arguments", "Practice opening up"],
        )
        scenario = {
            "Practice intimacy": "practice_intimacy",
            "Practice arguments": "practice_arguments",
            "Practice opening up": "practice_opening_up",
        }[scenario_label]
        character = st.text_input("Partner character", value="husband", max_chars=80)

    st.divider()
    st.markdown(
        '<div class="privacy-note">Chats are stored on this server and can be read by an administrator. Do not enter names, addresses, or other identifying details.</div>',
        unsafe_allow_html=True,
    )
    st.button("Clear and delete this chat", on_click=reset_conversation, use_container_width=True)

st.title("DilSe 🌸")
st.markdown(
    '<p class="dilse-subtitle">A private space to name what you need and practise saying it.</p>',
    unsafe_allow_html=True,
)

with st.expander("Before we begin"):
    st.write(
        "DilSe offers conversation practice and general relationship guidance. It is not a licensed therapist or emergency service. If you are in immediate danger or may harm yourself, contact local emergency services and a trusted person now."
    )
    adult_confirmed = st.checkbox("I am 18 or older and agree to consensual adult conversation.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input(
    "Share what is on your mind…",
    disabled=not adult_confirmed,
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "session_id": st.session_state.session_id,
        "message": prompt,
        "mode": mode,
        "scenario": scenario,
        "character": character,
    }
    with st.chat_message("assistant"):
        with st.spinner("DilSe is listening…"):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    json=payload,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                reply = response.json()["response"]
            except requests.HTTPError as exc:
                try:
                    detail = exc.response.json().get("detail", "The request failed.")
                except ValueError:
                    detail = "The request failed."
                reply = f"I could not respond: {detail}"
            except requests.RequestException:
                reply = "I cannot reach the DilSe server. Confirm that FastAPI is running on port 8000."
            st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

