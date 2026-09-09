# DilSe (SoulBridge)

DilSe is a FastAPI and Streamlit MVP for culturally aware relationship guidance and consensual adult conversation practice. It uses Groq for Llama inference and SQLite for local chat storage.

## Project layout

```text
dilse/
├── .env.example       # Configuration template
├── app.py             # Streamlit UI, port 8501
├── main.py            # FastAPI API, Groq client, prompt, and admin endpoints
├── requirements.txt   # Python dependencies
└── dilse.db            # Created on first backend start
```

## Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Groq key from <https://console.groq.com/keys> to `.env`. Replace `ADMIN_API_KEY` with a long random value. The model can be changed through `GROQ_MODEL` without editing the code.

The requested `llama-3.3-70b-versatile` model is the default. Groq has scheduled its free and developer-tier shutdown for August 16, 2026. If Groq removes it from your account, set `GROQ_MODEL` to a model currently enabled for your Groq project. This keeps the application working, but the replacement will no longer satisfy a strict Llama 3 requirement.

Start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal, start the UI:

```bash
streamlit run app.py --server.port 8501
```

Open <http://localhost:8501>. API documentation is available at <http://localhost:8000/docs>.

## Admin access

Chat logs contain sensitive personal information. Admin routes require the `X-Admin-Key` header and return an error if `ADMIN_API_KEY` is not configured.

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_KEY" http://localhost:8000/admin/logs
curl -H "X-Admin-Key: YOUR_ADMIN_KEY" http://localhost:8000/admin/dashboard
```

The HTML dashboard is intentionally simple for the MVP. Entering its URL directly in a browser will not supply the required header. Use an API client, a browser extension that sets request headers, or put the endpoint behind an authenticated reverse proxy.

## Privacy notes

- SQLite is suitable for a local MVP, not a public deployment handling sensitive counselling records.
- Before production use, add user accounts, encryption, retention limits, audit logs, consent records, rate limits, abuse monitoring, and a reviewed crisis-resource flow for each supported country.
- The session deletion route supports the UI's delete button. It relies on possession of the random session ID for this MVP; production should require an authenticated user.
