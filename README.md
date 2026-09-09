# DilSe (SoulBridge)

DilSe is a Pakistan-focused relationship guidance and conversation-practice application for adult women. A server-rendered public site provides crawlable English and Urdu pages, while the private Streamlit application runs under `/app/`. Listener mode uses GPT-OSS 120B through Groq. Partner mode uses Venice Role Play Uncensored. SQLite provides local storage.

## Included features

- Listener and Partner conversation modes
- Guidance for intimacy, emotional connection, conflict, family boundaries, trust, shared responsibilities, money, career, and parenting changes
- Server-rendered English and Urdu public pages for the Pakistani market
- Pakistan-focused topic pages, metadata, canonical URLs, `hreflang`, structured data, sitemap, and robots rules
- Editorial, full-width landing sections with staged motion, scroll reveals, a process timeline, and reduced-motion accessibility
- A dedicated MVP Terms and Conditions page with one required sign-up agreement
- Managed roleplay personas and scenarios
- Separate Supportive, Realistic, and Resistant character reactions in Partner mode
- Romantic, Direct, and Explicit intimacy detail for intimacy practice, available to accounts that accepted the 18+ eligibility terms at sign-up
- Administrator session controls that can change character reaction or intimacy detail before any later AI reply
- Safety instructions for coercion, abuse, immediate danger, suicide, and self-harm disclosures
- Guided exercises and conversation cards
- Guided first-conversation choices and deliberate Listener-to-Partner or Partner-to-Listener handoffs
- A user-owned conversation history with resume, search, and deletion controls
- Per-response controls for shorter, more direct, or user-voiced rewrites, plus categorized issue reporting
- Compact session memory with editable checkpoints that the user can confirm before later responses rely on them
- Feedback after roleplay practice
- Email and password accounts with salted `scrypt` password hashes
- Expiring authentication sessions
- English, Urdu, Roman Urdu, and mixed English-Urdu preferences
- Pakistan-only country context and verified local safety routing
- Required conversation storage and authorized administrator review, disclosed in the Terms, with user-selected retention and deletion controls
- Human administrator participation in active stored sessions, disclosed in the Terms
- AI pause and release controls with a consistent DilSe identity in the user chat
- Optional private Telegram administration with one topic per session, pinned context cards, audited replies, AI controls, and deletion jobs
- A native Android app with the full user chat flow, voice notes, private phone notifications, and signed updates downloaded from `baatdilse.com`
- Internal account-level and session-level AI guidance that does not change the global prompt
- Token reporting without unreliable cost estimates
- Consent-aware administrator conversation review
- Versioned system prompts with activation and rollback
- Administrator notes and corrected-response library
- Managed personas, scenarios, exercises, and cards
- Prompt rules derived from repeated Pakistani persona tests: one-question Listener replies, complete mental-load ownership, fact-preserving roleplay, realistic character resistance, and Urdu-first Pakistani Roman Urdu
- A request-specific response-quality guard plus local fallbacks for premature phone-privacy conclusions, first wrist-contact and threat calibration, first-response length, Hindi-first wording, Roman Urdu register and agreement, hidden persona labels, character gender, invented relatives, reversed script perspective, mental-load ownership from the first disclosure, career-meaning changes, unsafe return-home advice, and unsupported emotions
- Structured prompt modules that load Listener, Partner, Urdu, location, persona, intensity, and situation-specific instructions only when needed
- A tested 1,500-word static prompt budget for ordinary Listener requests
- Administrator feedback and audit views

## Project layout

```text
dilse/
├── .env.example          # Configuration template
├── .gitignore
├── .streamlit/
│   └── config.toml       # DilSe theme and local browser settings
├── assets/               # Logo files, landing artwork, and web-ready image assets
├── app.py                # Streamlit user and admin interface
├── CULTURAL_RESEARCH.md  # Evidence and decisions behind cultural prompt rules
├── main.py               # FastAPI API, model routing, authentication, and storage
├── mobile/               # Flutter Android application (`com.baatdilse.app`)
├── web.py                # Public SEO pages and proxy to the private Streamlit app
├── public/               # Public-site stylesheet
├── PROJECT_CONTEXT.md    # Product decisions and unresolved questions
├── README.md
├── requirements.txt
├── tests/
│   └── test_api.py       # API regression tests
└── dilse.db              # Created and migrated when the API starts
```

## Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add the Groq key from <https://console.groq.com/keys> and the Venice key from <https://venice.ai/settings/api> to `.env`. Replace `ADMIN_API_KEY` with a long random value. Keep all three secrets out of source control.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_REASONING_EFFORT=low
GROQ_MAX_CHAT_TOKENS=700
VENICE_API_KEY=your_venice_api_key
VENICE_PARTNER_MODEL=gemma-4-uncensored
VENICE_API_BASE_URL=https://api.venice.ai/api/v1
ADMIN_API_KEY=your_long_random_admin_secret
TELEGRAM_BOT_TOKEN=your_botfather_token
TELEGRAM_ADMIN_USER_IDS=your_numeric_telegram_user_id
BACKEND_URL=http://127.0.0.1:8000
DILSE_SHOW_HUMAN_HANDOFF_UI=false
DATABASE_PATH=dilse.db
AUTH_SESSION_DAYS=7
CHAT_HISTORY_LIMIT=20
```

`DILSE_SHOW_HUMAN_HANDOFF_UI=false` keeps the user-facing chat identity consistent while administrator message sources and audit records remain available internally.

Listener mode uses `openai/gpt-oss-120b` through Groq. Partner mode uses `gemma-4-uncensored` through Venice with Venice's default system prompt disabled, leaving DilSe's instructions in control. Low reasoning controls GPT-OSS token use. Ordinary requests are capped at 360 completion tokens, safety planning at 420, and Explicit roleplay at 480, subject to the configured maximum.

## Run locally

Start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Start the interface in a second terminal:

```bash
streamlit run app.py --server.port 8501
```

For the complete public-site setup, run `uvicorn web:app --host 0.0.0.0 --port 8501` instead of the direct Streamlit command. Open <http://localhost:8501>; the private application is at <http://localhost:8501/app/>. API documentation is at <http://localhost:8000/docs>.

## Deploy from this computer to Railway

The private-beta deployment uses two Railway services in one project:

- `dilse-web` runs the public FastAPI gateway and its private Streamlit child process;
- `dilse-api` runs FastAPI on Railway's private network;
- a volume mounted at `/data` stores a fresh production SQLite database.

The API service uses:

```env
PORT=8000
DATABASE_PATH=/data/dilse.db
RAILPACK_START_CMD=uvicorn main:app --host 0.0.0.0 --port 8000
```

The web service uses:

```env
PORT=8501
BACKEND_URL=http://dilse-api.railway.internal:8000
APP_URL=https://www.baatdilse.com/app
RAILPACK_START_CMD=uvicorn web:app --host 0.0.0.0 --port 8501
```

Keep `GROQ_API_KEY`, `VENICE_API_KEY`, `ADMIN_API_KEY`, and `TELEGRAM_BOT_TOKEN` only on the API service. The `.railwayignore` file prevents local secrets, databases, tests, temporary previews, and duplicate backup files from being uploaded by `railway up`.

Direct CLI deployments are manual. After changing the application, deploy each service explicitly:

```bash
railway up --service dilse-api
./scripts/deploy_web_release.sh
```

Do not upload the local `dilse.db`.

Use the web release script instead of a plain `railway up` for `dilse-web`.
The script includes the Git-ignored signed APK and the local Streamlit component
directories while excluding Android build caches and local secrets.

### Weekly Hobby-plan laptop backup

Railway's Hobby plan does not include managed volume backup schedules. The local backup script creates a consistent SQLite snapshot through the running API service, downloads it to `backups/railway/`, verifies it with `PRAGMA quick_check`, and writes a SHA-256 checksum:

```bash
./scripts/backup_railway_sqlite.sh
```

The dedicated private key is stored under `.railway/` and its public key is registered with Railway as `DilSe-Weekly-Backup`. Both the key and downloaded backups are excluded from Git and Railway uploads. The laptop must be awake, online, and signed into the Railway CLI when the scheduled backup runs.

## Administrator workspace

Open `http://localhost:8501/?admin=1` and enter `ADMIN_API_KEY`. The public website does not display an administrator link.

The **User workspace** lists accounts by most recent activity with search, country, and Terms-status filters. Current accounts include conversation storage and authorized administrator review. Existing accounts created under earlier Terms must explicitly accept the updated disclosure before previously private conversations become reviewable. After selecting an eligible account, the page shows that user's chat history as a visible newest-first list. Each entry includes the opening message, activity time, mode, scenario, and message count. The administrator can open any entry to see the exact transcript, message source, timestamps, model name, and current control state.

The control panel has four scopes:

- account guidance affects future AI replies for one user across sessions;
- session guidance affects only the selected conversation;
- roleplay controls change the character reaction or intimacy detail for the selected Partner session;
- human control pauses AI and permits messages labelled as a human DilSe administrator.

Account and session guidance are internal and never override global safety or consent instructions. Conversation review and live administrator participation are included with every account that has accepted the current Terms. Neither setting has a user-facing off switch. Accounts created under earlier Terms must accept the update before administrator access becomes available.

The **Response quality** tab collects private notes, roleplay ratings, categorized per-response issues, and administrator-written better responses. Global prompt edits create immutable versions. Activating an earlier version provides rollback without deleting newer work. Saved notes and corrections do not silently change a user's chat.

### Telegram administration

Telegram administration is inactive unless `TELEGRAM_BOT_TOKEN` is configured on the API service. Create the bot through `@BotFather`, add the token to Railway, and deploy the API. Send `/whoami` to the bot to obtain the numeric Telegram user ID, add that value to `TELEGRAM_ADMIN_USER_IDS`, and redeploy the API.

Create a private Telegram supergroup, enable Topics, and add the bot as an administrator with permission to manage topics, pin messages, and delete messages. Send `/connect` in the group. The bot records the private group ID in SQLite and creates one topic for each DilSe session as new messages arrive.

Each topic includes a pinned context card with the mode, country, language, control state, Partner character settings, a character preview, and saved conversation memory. Use `/character`, `/recent`, `/memory`, or `/settings` for additional context. Sending ordinary text inside the topic automatically takes human control and sends the text to the user as a DilSe response. Use `/ai` to resume AI responses and `/prompt [guidance]` to change session-specific AI guidance.

Only Telegram user IDs listed in `TELEGRAM_ADMIN_USER_IDS` can operate the bridge. DilSe does not relay account email addresses. Deleting a DilSe session or account queues deletion of its linked Telegram topic, subject to Telegram's own retention and device behaviour.

## Tests

```bash
python -m unittest discover -s tests -v
python -m py_compile main.py app.py
```

The tests use a temporary SQLite database and fake both model clients. They do not send requests to Groq or Venice.

## Android app

The Android app uses the same accounts and conversations as the website. The
administrator workspace remains on the web. Its default API address is
`https://www.baatdilse.com/api`, which the public web service proxies to the
private Railway API.

Create the signing key once on the release laptop:

```bash
./scripts/create_android_signing_key.sh
```

Back up `mobile/android/dilse-release.jks` securely. Android will reject future
updates signed with a different key. The script stores its generated password in
macOS Keychain and writes an ignored local `mobile/android/key.properties` file.

Copy `.env.android.example` to `.env.android` and add the four public Firebase
Android client values if phone notifications are configured. Then build:

```bash
FLUTTER_BIN=/path/to/flutter/bin/flutter ./scripts/build_android_release.sh
```

The script tests the app, creates a release APK, and copies it to
`downloads/DilSe-latest.apk`. Deploy the web service after each release so the
download at `https://www.baatdilse.com/android/` serves the new file. Configure
the API service with the matching Firebase service-account JSON and increment
`ANDROID_LATEST_BUILD` whenever `mobile/pubspec.yaml` receives a higher build
number.

## Privacy limits

This remains a local MVP. A public service handling sexual, relationship, abuse, or health-related information requires a reviewed privacy policy, transport and database encryption, production identity management, rate limits, country-specific crisis resources, security monitoring, backups, and legal review for every launch market.

SQLite retention cleanup occurs when a user chats or updates privacy settings. A scheduled cleanup task is required in production so inactive accounts also follow the selected retention period.
