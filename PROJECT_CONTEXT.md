# DilSe project context

## Purpose of this document

This document converts the supplied 46-page conversation history into working product context. It separates the user's stated goals from suggestions made by the previous assistant. Use the following source order when requirements conflict:

1. The user's latest explicit instruction
2. The current code and accepted configuration
3. Earlier user statements in the supplied conversation
4. Previous assistant suggestions, which are not decisions unless the user accepted them

The transcript includes internal analysis from another assistant. Treat that analysis as commentary, not as a product requirement or a factual source.

## Product definition

DilSe is a culturally aware relationship guidance and conversation-practice application for adult women in Pakistan. It gives users a place to discuss emotional connection, intimacy, conflict, trust, family pressure, boundaries, household responsibilities, money, career, parenting, and life transitions. Intimacy remains a product specialty, but it is not treated as the cause of every relationship problem.

The product should feel personal and culturally informed without assuming that every Pakistani woman has the same religion, family structure, sexuality, values, or relationship goals.

## Problem being addressed

The user's core observation is that some married women suppress feelings, preferences, boundaries, and sexual needs because of family expectations, modesty, financial dependence, fear of judgement, or concern about household harmony. This can make it difficult to address dissatisfaction, uneven responsibilities, money, parenting strain, loss of trust, or a loss of intimacy.

DilSe should help a user:

- name emotional, physical, and sexual needs without shame;
- understand a disagreement or relationship pattern from more than one perspective;
- discuss family influence, trust, money, household work, parenting, and major life changes;
- prepare a specific sentence or conversation opener;
- practise with an AI character before speaking to a real person;
- receive feedback after a practice conversation;
- try exercises that support communication and connection.

The application is a guidance and practice product. It must not claim to provide licensed therapy, medical advice, or emergency support.

## Confirmed brand direction

- Name: DilSe
- Working descriptor: SoulBridge
- Meaning: "from the heart"
- Intended character: warm, private, direct, emotionally safe, and culturally familiar
- Earlier visual direction: soft blush, warm rose, and deep maroon

Previous tagline ideas were suggestions, not confirmed brand decisions.

## Confirmed MVP architecture

- Backend: Python and FastAPI
- Frontend: Streamlit
- Listener provider: Groq API
- Listener model: `openai/gpt-oss-120b`
- Partner provider: Venice API
- Partner model: `gemma-4-uncensored`
- Local database: SQLite
- Backend port: 8000
- Frontend port: 8501
- Configuration: `.env`
- Admin protection: private `ADMIN_API_KEY`

Listener mode uses `openai/gpt-oss-120b` through Groq with low reasoning effort. Partner mode uses `gemma-4-uncensored` through Venice. `GROQ_MODEL`, `GROQ_REASONING_EFFORT`, `GROQ_MAX_CHAT_TOKENS`, `VENICE_PARTNER_MODEL`, and `VENICE_API_BASE_URL` remain configurable without editing application code.

## Confirmed interaction modes

### The Listener

The AI acts as a reflective relationship counsellor. It asks focused questions, helps the user examine a situation, offers practical perspective, and proposes scripts or exercises. It should ask one useful question at a time instead of presenting a long checklist.

### The Partner

The AI embodies a selected adult character for conversation practice. Current scenarios are:

- Practice intimacy
- Practice arguments
- Practice opening up
- Set a family boundary
- Reconnect emotionally
- Discuss trust and privacy
- Share responsibilities
- Discuss money or career
- Discuss parenting changes

The transcript also proposes husband, boyfriend, supportive partner, jealous partner, and traditional mother-in-law personas. These are product ideas until a final persona library is approved.

Roleplay uses three user-selected tones. Romantic is affectionate and suggestive, Direct speaks plainly about intimacy and boundaries, and Explicit permits detailed consensual adult roleplay. The user already confirmed that she is at least 18 by accepting the eligibility terms at account creation, so Explicit mode requires no additional checkbox or confirmation. The model should remain in character without repeated warnings solely because the content is explicit. Every sexualized character must still be an adult. The user can pause, stop, request feedback, withdraw consent, or establish a boundary at any time. A demanding character must remain within a mutually agreed adult scene and must not encourage real coercion or abuse.

## AI behaviour

The system prompt should be included in every model request. Its intended behaviour is:

- understand family pressure, marriage expectations, traditional gender roles, privacy concerns, and saving face;
- invite discussion of emotional and physical intimacy instead of avoiding it;
- follow the user's concern instead of treating intimacy as the default topic;
- support boundaries and autonomous decisions without assuming reconciliation is always the goal;
- recognize possible coercive control, sexual pressure, monitoring, financial restriction, and honour-based threats;
- use gentle but direct questions when the user has difficulty opening up;
- discuss consensual adult sexual topics plainly when the user chooses that direction;
- offer realistic scripts the user can adapt for a husband or partner;
- respond in the user's selected language; when Urdu or Roman Urdu is selected, use everyday Urdu-first Pakistani wording with natural English code-switching instead of Hindi-first or Sanskritised vocabulary;
- avoid cultural stereotypes and ask about the user's actual circumstances;
- distinguish guidance from clinical diagnosis;
- stop roleplay when immediate danger, abuse, suicide, or self-harm is disclosed and ask whether the user is safe now.

"Uncensored" in the earlier conversation should not be treated as a promise that the model or provider has no policies. The product requirement is to support frank, consensual adult discussion without unnecessary shame or euphemism.

The active prompt now uses a Pakistani family-systems frame. It considers extended-family roles, living arrangements, practical expressions of care, provider and daughter-in-law expectations, faith when chosen by the user, family reputation, and culturally workable communication. These are possible influences rather than assumptions. The research and calibration decisions are recorded in `CULTURAL_RESEARCH.md`.

Prompt version 11 replaces the accumulated all-purpose prompt with a structured decision order and conditional modules. The global core is limited to identity, evidence discipline, couple-first cultural reasoning, safety precedence, relationship scope, and the response contract. Listener, Partner, language, location, persona, intensity, and request-specific checks are injected only when relevant. An ordinary English Listener request now uses about 1,245 static prompt words instead of more than 3,400. Automated tests enforce a 1,500-word assembled static budget. Completion limits are 360 tokens for ordinary chat, 420 for safety planning, and 480 for Explicit roleplay. Local repairs remain for reversed intimacy perspective, mental-load ownership, career-meaning changes, overlong return-home plans, premature phone-privacy conclusions, and Urdu wording.

For an ambiguous physical interaction, the model must distinguish mutually familiar contact from unwanted restraint and ask about novelty, repetition, force, purpose, impact, fear, and escalation before reaching a conclusion. A threat combined with physical restraint remains concerning, but the model should not present abuse, motive, or future danger as certain from one incomplete account. Immediate danger still receives direct safety guidance.

## Current implementation status

Implemented in the local MVP:

- Mode-based model routing: Groq for Listener and Venice for Partner
- DilSe cultural system prompt on every request
- Listener and Partner modes
- Nine managed roleplay scenarios and seven managed character options
- SQLite message storage
- Conversation history sent to the model
- Admin JSON log endpoint
- Consent-aware user-first administrator case desk
- Searchable account list ordered by recent activity, followed by each current-Terms user's visible newest-first chat history
- Exact user-visible transcripts with message source, timestamp, and model metadata
- Separate account guidance, session guidance, and labelled human intervention controls
- Admin-key authentication
- Adult eligibility confirmation through the required sign-up terms, recorded in the consent table
- Privacy notice and session deletion
- Crisis, consent, non-coercion, and cultural anti-stereotyping instructions
- Pakistan safety context using verified local resources, with no guessed foreign emergency numbers
- Persona-tested response rules for concise Listener replies, context-first assessment of a first physical incident, natural Pakistani Roman Urdu agreement, complete household-domain ownership from the first mental-load disclosure, and fact-preserving roleplay
- Local setup documentation

The backend sends up to 20 previous messages by default. `CHAT_HISTORY_LIMIT` can set a value between 4 and 60. The final production value should be chosen using cost and conversation-quality tests.

## Improvements implemented on August 6, 2026

The second MVP now includes:

- account registration, login, logout, and account deletion;
- salted password hashing and expiring random login sessions;
- user-controlled language and retention settings, with required conversation storage and authorized administrator review disclosed during sign-up;
- administrator log review for current accounts, with a one-time Terms update required before older private settings change;
- system prompt versions with activation and rollback;
- administrator notes and a corrected-response research library;
- managed personas, scenarios, exercises, and conversation cards;
- generated feedback and user ratings after roleplay;
- per-user and administrator token reporting;
- administrator audit records for sensitive review and content changes.
- consent-based human handoff for active stored sessions;
- labelled administrator messages and explicit AI pause or release controls;
- internal account-level and session-level AI guidance that does not interrupt the user chat;
- saved better responses grouped by issue type for prompt research;
- a user-to-session case workflow with explicit control scope and audit records.

## Proposed work not yet implemented

These items appear in the conversation but are outside the current MVP:

- conversation summarisation for longer memory;
- mobile-native or PWA interface;
- cloud database and production hosting;
- subscription or payment features.

The original conversation mentioned Google OAuth, Supabase, PostgreSQL with vectors, React Native, Flutter, and React as possible future technologies. None was selected for this local MVP.

## Privacy and administration requirements

Chat logs may contain sexual, relationship, abuse, and family information. Administrator review therefore needs stronger controls than an ordinary analytics dashboard.

Before public use, the product needs:

- one clear sign-up agreement covering age eligibility, the terms, and the processing required to provide DilSe;
- required, explicit conversation storage and administrator review for every current account, with live human intervention kept as a separate optional setting;
- clear retention and deletion periods;
- authenticated user ownership of sessions;
- encryption in transit and at rest;
- role-based administrator access;
- an audit record of every log view and prompt change;
- redaction of names, phone numbers, addresses, and other identifiers;
- a process for access, export, correction, and deletion requests;
- rate limits and abuse monitoring;
- legal review for every country in which the service is offered.

Administrators should not silently write live responses as the AI. If human intervention is later introduced, the interface must identify that a person wrote or edited the message.

## Product decisions still needed

1. Market scope: Pakistan is the only launch market. India and broader South Asian targeting are out of scope for this release.
2. Relationship scope: confirm whether launch is limited to married women or includes dating, engaged, divorced, separated, and LGBTQ+ users.
3. Languages: the MVP offers English, Urdu, Roman Urdu, and a mixed English-Urdu option. Native-speaker testing is still required.
4. Privacy: obtain legal review for required storage and administrator review, retention periods, deletion rights, and launch-market privacy obligations.
5. Provider terms: obtain written confirmation that Venice permits consensual adult roleplay in a commercial relationship application before enabling Partner mode in production.
6. Prompt administration: decide who may edit prompts, how changes are tested, and how rollback works.
7. Roleplay feedback: decide whether feedback is automatic after every practice, requested by the user, or shown only when roleplay ends.
8. Exercises: choose the first three to five exercises and define the intended result of each.
9. Crisis handling: approve Pakistan-specific resources and escalation language before public launch.
10. Business model: decide whether the first release is free, subscription-based, or limited by message credits.

## Claims that require verification

Do not reuse earlier cost figures, model-policy claims, market-demand claims, or cultural generalisations as facts. Model availability, prices, privacy terms, and content rules must be checked against current provider documentation. Market claims need research. Cultural statements should be framed as possible experiences and validated through user research with the intended audience.

## Recommended next product milestone

Run a private usability test with five to ten adult participants using the current two-mode MVP. Test whether users understand account creation and the privacy disclosure, can choose a mode without explanation, feel able to stop roleplay, receive useful scripts, and recognize cultural assumptions that do not fit them. Use those sessions to revise the initial personas, exercises, language support, and memory length before adding payments or public deployment.
