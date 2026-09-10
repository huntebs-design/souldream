"""Widget-level tests for the DilSe Streamlit conversation controls."""

from __future__ import annotations

import base64
import ast
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

os.environ["DILSE_SKIP_BROWSER_ID"] = "1"


USER = {
    "id": 1,
    "email": "ui@example.com",
    "display_name": "UI Tester",
    "language": "Roman Urdu",
    "country": "Pakistan",
    "retention_days": 30,
    "allow_admin_review": True,
    "allow_admin_intervention": True,
    "store_chats": True,
    "email_notifications_enabled": True,
    "terms_version": "2026-08-10-terms-v6",
    "requires_terms_acceptance": False,
    "access_status": "active",
    "preferred_time_slot": "flexible",
    "created_at": "2026-08-07T00:00:00+00:00",
}

CATALOG = {
    "scenarios": [
        {
            "slug": "practice_intimacy",
            "name": "Practice intimacy",
            "description": "Say what you want and agree on boundaries.",
            "starter": "Start an intimacy conversation.",
        }
    ],
    "personas": [
        {
            "slug": "husband",
            "name": "Husband",
            "description": "A spouse responding in a realistic, emotionally present way.",
        },
        {
            "slug": "mother_in_law",
            "name": "Traditional mother-in-law",
            "description": "A traditional elder responding from her values and family expectations.",
        },
        {
            "slug": "crush",
            "name": "Crush",
            "description": "An adult romantic interest who is warm, curious, lightly flirtatious, and a little uncertain about mutual feelings.",
        },
        {
            "slug": "fantasy_partner",
            "name": "Fantasy Partner",
            "description": "A fictional adult partner who is confident, attentive, affectionate, expressive, and playful.",
        },
    ],
    "exercises": [],
    "cards": [],
}

ADMIN_USER = {
    "id": 7,
    "email": "nadia@example.com",
    "display_name": "Nadia",
    "language": "Roman Urdu",
    "country": "Pakistan",
    "retention_days": 30,
    "allow_admin_review": True,
    "allow_admin_intervention": True,
    "default_human_control": True,
    "store_chats": True,
    "terms_version": "2026-08-10-terms-v6",
    "requires_terms_acceptance": False,
    "access_status": "active",
    "preferred_time_slot": "evening",
    "access_approved_at": "2026-08-07T00:05:00+00:00",
    "created_at": "2026-08-07T00:00:00+00:00",
    "reviewable_sessions": 1,
    "reviewable_messages": 2,
    "last_reviewable_activity": "2026-08-08T12:05:00+00:00",
    "user_prompt_adjusted": 0,
}

ADMIN_SESSION = {
    "session_id": "admin_ui_session_123",
    "started_at": "2026-08-08T12:00:00+00:00",
    "last_activity": "2026-08-08T12:05:00+00:00",
    "message_count": 2,
    "user_messages": 1,
    "first_user_message": "Mere husband ne kal meri kalai pakri.",
    "latest_message_preview": "Kya yeh pehli baar hua?",
    "mode": "listener",
    "scenario": "open_conversation",
    "character": None,
    "roleplay_intensity": None,
    "roleplay_difficulty": None,
    "character_description": None,
    "control_mode": "ai",
    "session_prompt_adjusted": 0,
}

ADMIN_DETAIL = {
    "session_id": ADMIN_SESSION["session_id"],
    "user": ADMIN_USER,
    "message_count": 2,
    "transcript_revision": "2:2:2026-08-08T12:05:00+00:00:",
    "user_typing": False,
    "can_intervene": True,
    "session_control": {
        "mode": "ai",
        "prompt_override": None,
        "roleplay_intensity_override": None,
        "roleplay_difficulty_override": None,
        "note": "",
        "updated_at": None,
    },
    "user_prompt_control": None,
    "messages": [
        {
            "id": 1,
            "role": "user",
            "content": "Mere husband ne kal meri kalai pakri.",
            "mode": "listener",
            "scenario": "open_conversation",
            "created_at": "2026-08-08T12:00:00+00:00",
            "model": None,
            "source": "user",
            "client_platform": "android_app",
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "Kya yeh pehli baar hua, ya pehle kabhi playful andaaz mein bhi hua hai?",
            "mode": "listener",
            "scenario": "open_conversation",
            "created_at": "2026-08-08T12:05:00+00:00",
            "model": "openai/gpt-oss-120b",
            "source": "ai",
        },
    ],
}


class StubResponse:
    def __init__(self, body: object, status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code
        self.text = ""

    def json(self) -> object:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def fake_request(method: str, url: str, **_: object) -> StubResponse:
    if method == "GET" and url.endswith("/auth/me"):
        return StubResponse(USER)
    if method == "GET" and url.endswith("/catalog"):
        return StubResponse(CATALOG)
    if method == "GET" and url.endswith("/account/push/config"):
        return StubResponse(
            {"available": False, "public_key": "", "active_devices": 0}
        )
    if method == "GET" and url.endswith("/sessions/unread"):
        return StubResponse({"total_unread": 0, "conversations": []})
    if method == "GET" and url.endswith("/sessions") and "/admin/" not in url:
        return StubResponse([])
    if method == "GET" and "/sessions/" in url and "/sync?" in url:
        return StubResponse(
            {
                "mode": "human",
                "message_count": 1,
                "message_ids": [501],
                "updates": [],
            }
        )
    if method == "POST" and url.endswith("/chat"):
        return StubResponse(
            {
                "response": "Your message is waiting for a DilSe response.",
                "delivery": "waiting_for_admin",
                "user_message_id": 501,
                "message_id": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "stored": True,
                "conversation_checkpoint": None,
            }
        )
    if method == "GET" and url.endswith("/admin/summary"):
        return StubResponse(
            {
                "total_users": 1,
                "stored_users": 1,
                "consenting_users": 1,
                "reviewable_sessions": 1,
                "reviewable_messages": 2,
                "prompt_tokens": 100,
                "completion_tokens": 30,
                "intervention_users": 1,
                "pending_terms_users": 0,
                "pending_access_users": 0,
                "live_visitors": 1,
                "visitor_sessions": 2,
                "registered_installations": 1,
                "app_users": 1,
            }
        )
    if method == "GET" and url.endswith("/admin/access-settings"):
        return StubResponse({"require_approval_for_new_accounts": True})
    if method == "GET" and url.endswith("/admin/visitors?limit=200"):
        return StubResponse(
            {
                "live": [
                    {
                        "visit_id": 1,
                        "visitor": "UI Tester",
                        "signed_in": True,
                        "email": "ui@example.com",
                        "ip_prefix": "198.51.100.xxx",
                        "current_page": "Dashboard · Talk",
                        "first_seen": "2026-08-08T12:00:00+00:00",
                        "last_seen": "2026-08-08T12:05:00+00:00",
                        "duration_minutes": 5,
                        "page_views": 2,
                        "live": True,
                        "pages": [
                            {"page": "Home", "viewed_at": "2026-08-08T12:00:00+00:00"},
                            {"page": "Dashboard · Talk", "viewed_at": "2026-08-08T12:01:00+00:00"},
                        ],
                    }
                ],
                "past": [
                    {
                        "visit_id": 2,
                        "visitor": "Visitor A1B2C3D4",
                        "signed_in": False,
                        "email": None,
                        "ip_prefix": "203.0.113.xxx",
                        "current_page": "Create account",
                        "first_seen": "2026-08-07T10:00:00+00:00",
                        "last_seen": "2026-08-07T10:03:00+00:00",
                        "duration_minutes": 3,
                        "page_views": 2,
                        "live": False,
                        "pages": [
                            {"page": "Home", "viewed_at": "2026-08-07T10:00:00+00:00"},
                            {"page": "Create account", "viewed_at": "2026-08-07T10:02:00+00:00"},
                        ],
                    }
                ],
                "stored_session_count": 2,
                "retention_days": 30,
                "live_window_seconds": 60,
            }
        )
    if method == "GET" and url.endswith("/admin/app-usage"):
        return StubResponse(
            {
                "current_app_version": "1.0.2+3",
                "summary": {
                    "registered_installations": 1,
                    "app_users": 1,
                    "notifications_enabled": 1,
                    "current_version_installations": 1,
                    "web_messages": 3,
                    "android_messages": 2,
                    "legacy_messages": 1,
                    "web_users": 1,
                    "android_users": 1,
                    "both_users": 1,
                },
                "users": [
                    {
                        **ADMIN_USER,
                        "activity": "Both",
                        "installation_count": 1,
                        "notification_devices": 1,
                        "app_versions": "1.0.2+3",
                        "last_app_seen": "2026-08-08T12:05:00+00:00",
                        "last_web_message": "2026-08-08T12:02:00+00:00",
                        "last_android_message": "2026-08-08T12:05:00+00:00",
                        "latest_client_platform": "android_app",
                    }
                ],
            }
        )
    if method == "GET" and url.endswith("/admin/users"):
        return StubResponse([ADMIN_USER])
    if method == "GET" and url.endswith("/admin/sessions/active?minutes=60"):
        return StubResponse([])
    if method == "GET" and url.endswith("/admin/inbox?limit=20"):
        return StubResponse({"total_unread": 0, "conversations": []})
    if method == "GET" and url.endswith(f"/admin/users/{ADMIN_USER['id']}"):
        return StubResponse(
            {
                "user": ADMIN_USER,
                "prompt_control": None,
                "latest_consent": {"version": "2026-07-31"},
            }
        )
    if method == "GET" and url.endswith(f"/admin/users/{ADMIN_USER['id']}/sessions"):
        return StubResponse([ADMIN_SESSION])
    if method == "GET" and url.endswith(
        f"/admin/sessions/{ADMIN_SESSION['session_id']}/typing"
    ):
        return StubResponse(
            {
                "session_id": ADMIN_SESSION["session_id"],
                "user_typing": ADMIN_DETAIL.get("user_typing", False),
            }
        )
    if method == "GET" and url.endswith(
        f"/admin/sessions/{ADMIN_SESSION['session_id']}/status"
    ):
        return StubResponse(
            {
                "session_id": ADMIN_SESSION["session_id"],
                "message_count": ADMIN_DETAIL["message_count"],
                "transcript_revision": ADMIN_DETAIL["transcript_revision"],
                "control_mode": ADMIN_DETAIL["session_control"]["mode"],
                "user_typing": ADMIN_DETAIL.get("user_typing", False),
            }
        )
    if method == "GET" and url.split("?", 1)[0].endswith(f"/admin/sessions/{ADMIN_SESSION['session_id']}/detail"):
        return StubResponse(ADMIN_DETAIL)
    if method == "DELETE" and "/admin/sessions/" in url and "/messages/" in url:
        return StubResponse({}, 204)
    if method == "GET" and url.endswith("/admin/prompts"):
        return StubResponse(
            [
                {
                    "id": 3,
                    "prompt": "Test prompt",
                    "note": "Current test version",
                    "active": 1,
                    "created_at": "2026-08-08T00:00:00+00:00",
                }
            ]
        )
    if method == "GET" and any(
        url.endswith(path)
        for path in (
            "/admin/corrections",
            "/admin/notes",
            "/admin/feedback",
            "/admin/message-feedback",
            "/admin/audit",
            "/admin/message-revisions?limit=200",
        )
    ):
        return StubResponse([])
    if method == "GET" and "/admin/catalog/" in url:
        return StubResponse([])
    return StubResponse({"detail": "Unexpected UI test request"}, 500)


class DilSeStreamlitTests(unittest.TestCase):
    def test_admin_incoming_message_does_not_unmount_recording_draft(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
        function = next(
            node for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef) and node.name == "render_admin_live_status"
        )
        function.decorator_list = []
        state = {
            "admin_composer_nonces": {"fixture": 2},
            "admin_draft_source_fixture_2": "Record",
        }
        streamlit = SimpleNamespace(session_state=state, rerun=Mock(), markdown=Mock())
        namespace = {
            "st": streamlit, "Any": object, "html": __import__("html"),
            "admin_json": lambda *args: {"message_count": 3},
            "admin_transcript_signature": lambda status: "new-message",
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
        refresh = namespace["render_admin_live_status"]
        refresh("fixture", {}, "previous-message")
        streamlit.rerun.assert_not_called()
        state["admin_draft_source_fixture_2"] = "Type"
        refresh("fixture", {}, "previous-message")
        streamlit.rerun.assert_called_once_with(scope="app")

    def test_internal_landing_links_stay_in_the_current_tab(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")
        internal_link_attributes = re.findall(r'<a href="\?[^\"]*"([^>]*)>', source)

        self.assertTrue(internal_link_attributes)
        self.assertTrue(
            all('target="_self"' in attributes for attributes in internal_link_attributes)
        )

    def test_auth_links_open_a_dedicated_form_route(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertNotRegex(source, r'href="\?auth=(?:create|signin)#start"')
        self.assertIn('class="landing-marketing{marketing_class}"', source)
        self.assertIn('class="auth-stage{auth_stage_class}"', source)

        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["auth"] = "signin"
            app.run()

            self.assertEqual(app.tabs[0].label, "Sign in")
            self.assertTrue(any(item.label == "Sign in" for item in app.button))
        self.assertTrue(any(item.label == "Create account" for item in app.button))

    def test_public_terms_page_preserves_existing_sections(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["page"] = "terms"
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertNotIn("Draft for private MVP testing", markdown)
            self.assertIn("What you are agreeing to", markdown)
            self.assertNotIn("administrator", markdown.lower())
            self.assertIn("Required account processing", markdown)
            self.assertEqual(
                app_path.read_text(encoding="utf-8").count("Required account processing"),
                1,
            )

    def test_signup_keeps_processing_disclosure_on_terms_page_only(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["auth"] = "create"
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            checkbox_labels = {item.label for item in app.checkbox}
            self.assertNotIn("Required account processing", markdown)
            self.assertNotIn(
                "DilSe stores your conversations and authorized administrators may review them",
                markdown,
            )
            self.assertIn("I Agree with the Terms and Conditions", checkbox_labels)

    def test_waitlisted_account_sees_availability_message_without_admin_wording(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        pending_user = {
            **USER,
            "access_status": "pending",
            "preferred_time_slot": "evening",
        }

        def waitlist_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/auth/me"):
                return StubResponse(pending_user)
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=waitlist_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "waitlist-test-token"
            app.session_state["user"] = pending_user
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown).lower()
            waitlist_copy = markdown.rsplit('<main class="waitlist-stage">', 1)[-1]
            self.assertIn("your account is on the dilse waitlist", waitlist_copy)
            self.assertIn("check back in a few hours", waitlist_copy)
            self.assertIn("6:00 pm to 10:00 pm pkt", waitlist_copy)
            self.assertNotIn("admin", waitlist_copy)
            self.assertTrue(any(item.label == "Check access again" for item in app.button))
            self.assertFalse(any(item.label == "Account options" for item in app.expander))

        source = app_path.read_text(encoding="utf-8")
        self.assertIn('admin_json("GET", "/admin/access-settings")', source)
        self.assertIn("Activate account", source)
        self.assertIn("Starting reply mode", source)
        self.assertNotIn("popular usage", source.lower())
        self.assertNotIn("server capacity", source.lower())

    def test_terms_link_moves_from_public_header_to_signed_in_settings(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            public_app = AppTest.from_file(str(app_path), default_timeout=10)
            public_app.run()
            public_markdown = "\n".join(str(item.value) for item in public_app.markdown)
            masthead = public_markdown.split('<div class="landing-marketing', 1)[0]
            self.assertNotIn('href="?page=terms"', masthead)
            self.assertIn('href="?auth=signin"', masthead)
            self.assertIn('href="?auth=create"', masthead)

            settings_app = AppTest.from_file(str(app_path), default_timeout=10)
            settings_app.run()
            settings_app.session_state["auth_token"] = "ui-test-token"
            settings_app.session_state["user"] = USER
            settings_app.session_state["page"] = "Account"
            settings_app.run()
            settings_markdown = "\n".join(
                str(item.value) for item in settings_app.markdown
            )
            self.assertIn(
                '<a class="settings-document-link" href="?page=terms" target="_self">Terms and Conditions</a>',
                settings_markdown,
            )
            self.assertNotIn(".site-nav a:first-child { display: none; }", app_path.read_text(encoding="utf-8"))

    def test_explicit_tone_is_immediately_available_to_adult_account(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")
        self.assertIn(".st-key-character_description_editor", source)
        self.assertIn("height: 160px !important", source)
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            button_labels = {item.label for item in app.button}
            self.assertIn("+ New chat", button_labels)
            self.assertIn("All conversations", button_labels)
            self.assertIn("Practice", button_labels)
            self.assertIn("Settings and privacy", button_labels)
            self.assertIn("Sign out", button_labels)
            self.assertIn("Start with Listener", button_labels)
            self.assertIn("Start Partner roleplay", button_labels)

            app.button(key="new_chat_choose_listener").click().run()

            self.assertTrue(any(item.label == "Help me understand" for item in app.button))
            self.assertTrue(
                any("Choose how this chat works" in item.value for item in app.markdown)
            )

            conversation_mode = next(
                item for item in app.radio if item.label == "Mode"
            )
            conversation_mode.set_value("The Partner").run()
            difficulty = next(
                item for item in app.selectbox if item.label == "How should they react?"
            )
            tone = next(
                item for item in app.selectbox if item.label == "Adult intimacy detail"
            )
            character_profile = next(
                item
                for item in app.text_area
                if item.label == "Describe this person's nature and character"
            )

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Tell DilSe about your husband", markdown)
            self.assertIn("Tell me about your husband", markdown)
            self.assertTrue(
                any(
                    "chat-surface-header" in str(item.value)
                    and "Roleplay conversation" in str(item.value)
                    and "The Partner" in str(item.value)
                    for item in app.markdown
                )
            )
            self.assertFalse(app.chat_input[0].disabled)
            self.assertIn("Describe your husband", app.chat_input[0].placeholder)
            self.assertFalse(character_profile.disabled)
            self.assertEqual(difficulty.value, "Realistic")
            self.assertEqual(tone.value, "Explicit")
            character_profile.set_value(
                "Ali is quiet, speaks in Roman Urdu, and needs a calm opening before he talks about feelings."
            ).run()
            self.assertFalse(app.chat_input[0].disabled)
            self.assertTrue(
                any(
                    "Character sketch ready" in str(item.value)
                    for item in app.markdown
                )
            )
            self.assertFalse(
                any(
                    item.label.startswith("I confirm that every character is 18 or older")
                    for item in app.checkbox
                )
            )

    def test_first_partner_message_becomes_the_character_sketch(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        profile = (
            "Ali is quiet and practical. He speaks Roman Urdu and opens up when I stay calm."
        )
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            app.button(key="new_chat_choose_partner").click().run()
            app.chat_input[0].set_value(profile).run()

            self.assertEqual(app.session_state["character_description"], profile)
            self.assertEqual(app.session_state["messages"], [])
            self.assertIn("Say something to Husband", app.chat_input[0].placeholder)
            editor = next(
                item
                for item in app.text_area
                if item.label == "Describe this person's nature and character"
            )
            self.assertEqual(editor.value, profile)
            self.assertTrue(
                any("Character sketch ready" in str(item.value) for item in app.markdown)
            )

    def test_first_partner_character_sketch_has_a_5000_word_limit(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        oversized_profile = " ".join(["detail"] * 5_001)
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            app.button(key="new_chat_choose_partner").click().run()
            app.chat_input[0].set_value(oversized_profile).run()

            self.assertEqual(app.session_state["character_description"], "")
            self.assertTrue(
                any("5,000 words or fewer" in str(item.value) for item in app.warning)
            )

    def test_mobile_chat_switches_mode_and_opens_one_settings_drawer(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            app.button(key="new_chat_choose_listener").click().run()
            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("mobile-mode-label", markdown)
            partner_mode = next(
                item for item in app.button if item.label == "Partner"
            )
            partner_mode.click().run()
            self.assertEqual(app.session_state["conversation_mode"], "The Partner")
            self.assertEqual(app.session_state["mode"], "The Partner")
            self.assertFalse(app.session_state["mobile_conversation_settings_open"])
            drawer_markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertFalse(
                any(
                    str(item.value).strip()
                    == '<span class="mobile-settings-open-marker"></span>'
                    for item in app.markdown
                )
            )
            self.assertIn("Tell me about your husband", drawer_markdown)

            open_settings = next(
                item for item in app.button if item.label == "Settings"
            )
            open_settings.click().run()

            self.assertTrue(app.session_state["mobile_conversation_settings_open"])
            drawer_markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertTrue(
                any(
                    str(item.value).strip()
                    == '<span class="mobile-settings-open-marker"></span>'
                    for item in app.markdown
                )
            )
            close_settings = next(
                item for item in app.button if item.label == "Close settings"
            )
            close_settings.click().run()
            self.assertFalse(app.session_state["mobile_conversation_settings_open"])

        source = app_path.read_text(encoding="utf-8")
        self.assertIn(":has(.mobile-settings-open-marker)", source)
        self.assertIn("height: 100dvh", source)
        self.assertIn("flex: 1 1 100% !important", source)
        self.assertIn(".mode-opening-detail { display: none; }", source)
        self.assertIn("grid-template-columns: auto minmax(0, 1fr);", source)

    def test_partner_character_prompt_changes_with_selected_persona(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            app.button(key="new_chat_choose_partner").click().run()
            persona = next(
                item for item in app.selectbox if item.label == "Who are you talking to?"
            )
            persona.set_value("Traditional mother-in-law").run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            character_profile = next(
                item
                for item in app.text_area
                if item.label == "Describe this person's nature and character"
            )
            self.assertIn("Tell DilSe about your mother-in-law", markdown)
            self.assertIn("Ammi is traditional", character_profile.placeholder)
            self.assertEqual(character_profile.value, "")
            self.assertFalse(app.chat_input[0].disabled)
            self.assertIn("Describe your mother-in-law", app.chat_input[0].placeholder)

    def test_every_user_dashboard_page_has_the_new_shell(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        expected_copy = {
            "My conversations": "Pick up where you left off",
            "Exercises": "Prepare at your own pace",
            "Privacy": "How DilSe handles conversations",
            "Account": "Profile and sign-in",
        }

        with patch("requests.request", side_effect=fake_request):
            for page, heading in expected_copy.items():
                app = AppTest.from_file(str(app_path), default_timeout=10)
                app.run()
                app.session_state["auth_token"] = "ui-test-token"
                app.session_state["user"] = USER
                app.session_state["page"] = page
                app.run()

                markdown_values = [str(item.value) for item in app.markdown]
                self.assertTrue(any(heading in value for value in markdown_values), page)
                button_labels = {item.label for item in app.button}
                self.assertIn("Back to chat", button_labels)
                self.assertIn("Account", button_labels)

    def test_privacy_page_hides_administrator_wording(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.session_state["page"] = "Privacy"
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            checkbox_labels = {item.label for item in app.checkbox}
            self.assertNotIn("administrator", markdown.lower())
            self.assertNotIn("Save future conversations", checkbox_labels)
            self.assertFalse(any("administrator" in label.lower() for label in checkbox_labels))
            self.assertIn("Conversation retention", markdown)

    def test_existing_account_sees_explicit_terms_update_gate(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        legacy_user = {
            **USER,
            "allow_admin_review": False,
            "store_chats": True,
            "terms_version": "2026-08-06-terms-v2",
            "requires_terms_acceptance": True,
        }

        def legacy_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/auth/me"):
                return StubResponse(legacy_user)
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=legacy_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "legacy-test-token"
            app.session_state["user"] = legacy_user
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            checkbox_labels = {item.label for item in app.checkbox}
            button_labels = {item.label for item in app.button}
            self.assertIn("Account update required", markdown)
            self.assertIn("conversation storage while your account is active", markdown)
            self.assertNotIn("administrator", markdown.lower())
            self.assertIn(
                "I Agree with the Terms and Conditions",
                checkbox_labels,
            )
            accept_button = next(item for item in app.button if item.label == "Accept and continue")
            self.assertFalse(accept_button.disabled)
            self.assertNotIn("+ New chat", button_labels)

    def test_streamlit_production_toolbar_is_hidden(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn('header[data-testid="stHeader"]', source)
        self.assertIn('[data-testid="stToolbar"]', source)
        self.assertIn('#MainMenu', source)

    def test_chat_uses_branded_left_and_right_message_layout(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")
        avatar_path = app_path.parent / "assets" / "dilse-mark.svg"

        self.assertTrue(avatar_path.exists())
        self.assertIn("CHAT_AVATAR_PATH", source)
        self.assertIn('avatar=message_avatar', source)
        self.assertIn('aria-label="Chat message from assistant"', source)
        self.assertIn('aria-label="Chat message from user"', source)
        self.assertIn('[data-testid="stChatMessageAvatarCustom"]', source)
        self.assertIn("flex-direction: row-reverse", source)


    def test_mobile_chat_prioritizes_messages_voice_and_composer(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("def is_mobile_browser() -> bool:", source)
        self.assertIn(
            "if mobile_browser and not st.session_state.mobile_conversation_settings_open:",
            source,
        )
        self.assertIn("settings = current_conversation_settings(catalog, experience_v2)", source)
        self.assertIn("Response options", source)
        self.assertNotIn("Reply tools", source)
        self.assertNotIn("render_response_options_panel", source)
        self.assertIn("refine_shorter", source)
        self.assertIn("refine_direct", source)
        self.assertIn("refine_voice", source)
        self.assertNotIn("user_response_options", source)
        self.assertNotIn("if checkpoint and not mobile_browser:", source)
        self.assertIn(".st-key-user_voice_note_composer", source)
        self.assertIn(".st-key-user_compact_composer", source)
        self.assertIn('"Record voice note" if mobile_browser else "Voice note"', source)
        self.assertIn("padding-left: 3rem !important", source)
        self.assertIn("height: clamp(330px, calc(100dvh - 225px), 640px)", source)
        self.assertIn("justify-content: safe flex-end", source)
        self.assertIn(
            '.st-key-user_chat_transcript > [data-testid="stVerticalBlockBorderWrapper"]',
            source,
        )
        self.assertIn(
            '.st-key-user_chat_transcript > [data-testid="stElementContainer"]:has(.dilse-chat-scroll-anchor)',
            source,
        )
        self.assertIn('div[class*="st-key-transcript_history_"]', source)
        self.assertIn("def scroll_mobile_chat_to_composer(", source)
        self.assertIn("composer.scrollIntoView", source)
        self.assertIn("st.session_state.scroll_chat_composer = True", source)
        self.assertIn("st.session_state.scroll_dashboard_top = False", source)
        self.assertIn(
            'if st.session_state.get("scroll_chat_composer"):',
            source,
        )

    def test_user_and_admin_chats_follow_new_messages(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertNotIn("components.html(", source)
        self.assertNotIn("st.iframe(", source)
        self.assertIn("unsafe_allow_javascript=True", source)
        self.assertIn("def follow_latest_chat_message(", source)
        self.assertIn("__dilseChatFollowState", source)
        self.assertIn("const findScrollContainer", source)
        self.assertIn("const transcriptRoot = element?.closest", source)
        self.assertIn("transcriptRoot.contains(candidate)", source)
        self.assertIn("scrollContainer.scrollTo", source)
        self.assertIn('behavior: "auto"', source)
        self.assertNotIn("target.scrollIntoView", source)
        self.assertIn('data-dilse-chat-anchor=', source)
        self.assertIn("historyWasPrepended", source)
        self.assertIn("followState[scrollKey] = {{signature, messageKeys}}", source)
        self.assertIn("parentWindow.setTimeout(() => moveToLatest(true), 700)", source)
        self.assertIn("def transcript_history_event(", source)
        self.assertNotIn("transcript_scroll_component(", source)
        self.assertNotIn('"dilse_transcript_scroll"', source)
        self.assertIn('"Load older messages"', source)
        self.assertIn("button.click();", source)
        self.assertIn("__dilseTranscriptPagingState", source)
        self.assertIn("load_earlier_user_messages(before_id)", source)
        self.assertIn("load_earlier_admin_messages(", source)
        self.assertNotIn("Load earlier messages", source)
        self.assertIn('key="user_chat_transcript"', source)
        self.assertIn('key=f"admin_chat_transcript_{selected_session_id}"', source)
        self.assertIn('height=520', source)
        self.assertIn('height=640', source)
        self.assertIn('follow_latest_chat_message(\n                "user",', source)
        self.assertIn('follow_latest_chat_message("admin", selected_session_id, messages)', source)
        self.assertIn('@st.fragment(run_every="1s")\ndef render_admin_live_status(', source)
        self.assertIn(f'/admin/sessions/{{selected_session_id}}/status', source)
        live_fragment = source[
            source.index('@st.fragment(run_every="1s")\ndef render_admin_live_status('):
            source.index("def render_admin_transcript(")
        ]
        self.assertNotIn("detail?record_view=false", live_fragment)
        self.assertIn(
            "_legacy_live_updates_component = components.declare_component(",
            source,
        )
        self.assertNotIn("live_event = live_updates_component(", source)

    def test_admin_composer_stays_outside_live_refresh_fragment(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")
        fragment_start = source.index(
            '@st.fragment(run_every="1s")\ndef render_admin_live_status('
        )
        transcript_start = source.index(
            "\ndef render_admin_transcript(", fragment_start
        )
        fragment_source = source[fragment_start:transcript_start]
        self.assertNotIn("render_admin_transcript_composer(", fragment_source)
        self.assertNotIn("render_message_body(", fragment_source)
        self.assertNotIn("st.audio(", fragment_source)
        self.assertIn(
            "render_admin_transcript(\n"
            "        selected_session_id,\n"
            "        selected_user,\n"
            "        selected_session,\n"
            "        detail,\n"
            "    )\n"
            "    render_admin_composer_typing_status(\n"
            "        selected_session_id,\n"
            "        selected_user,\n"
            "    )\n"
            "    render_admin_transcript_composer(",
            source,
        )

    def test_admin_chat_badges_background_user_messages_in_browser_tab(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("def show_admin_chat_unread_badge(", source)
        self.assertIn("__dilseAdminUnreadState", source)
        self.assertIn('message.get("role") == "user"', source)
        self.assertIn('parentDocument.addEventListener("visibilitychange"', source)
        self.assertIn("parentDocument.title = count > 0", source)
        self.assertIn('data-dilse-admin-badge="true"', source)
        self.assertIn("show_admin_chat_unread_badge(selected_session_id, messages)", source)

    def test_unread_notifications_link_users_and_admins_to_new_messages(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        def notification_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/sessions/unread"):
                return StubResponse(
                    {
                        "total_unread": 1,
                        "conversations": [
                            {
                                "session_id": ADMIN_SESSION["session_id"],
                                "unread_count": 1,
                                "latest_message_preview": "A new reply is waiting.",
                            }
                        ],
                    }
                )
            if method == "GET" and url.endswith("/admin/inbox?limit=20"):
                return StubResponse(
                    {
                        "total_unread": 1,
                        "conversations": [
                            {
                                "session_id": ADMIN_SESSION["session_id"],
                                "user_id": ADMIN_USER["id"],
                                "display_name": ADMIN_USER["display_name"],
                                "unread_count": 1,
                                "mode": "listener",
                                "latest_message_preview": "I sent a new message.",
                            }
                        ],
                    }
                )
            if method == "GET" and url.endswith("/admin/sessions/active?minutes=60"):
                return StubResponse(
                    [
                        {
                            **ADMIN_SESSION,
                            "user_id": ADMIN_USER["id"],
                            "email": ADMIN_USER["email"],
                            "display_name": ADMIN_USER["display_name"],
                            "conversation_mode": "listener",
                            "control_mode": "human",
                        }
                    ]
                )
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=notification_request):
            user_app = AppTest.from_file(str(app_path), default_timeout=10)
            user_app.run()
            user_app.session_state["auth_token"] = "ui-test-token"
            user_app.session_state["user"] = USER
            user_app.run()
            self.assertTrue(
                any(item.label == "Open conversation" for item in user_app.button)
            )
            self.assertTrue(
                any("A new reply is waiting." in str(item.value) for item in user_app.markdown)
            )

            admin_app = AppTest.from_file(str(app_path), default_timeout=10)
            admin_app.query_params["admin"] = "1"
            admin_app.run()
            admin_app.session_state["admin_key"] = "test-admin-key"
            admin_app.session_state["admin_page"] = "Overview"
            admin_app.run()
            self.assertTrue(
                any("I sent a new message." in str(item.value) for item in admin_app.markdown)
            )
            self.assertTrue(
                any("Needs reply · 1 new" in str(item.value) for item in admin_app.markdown)
            )
            admin_app.button(
                key=f"open_admin_unread_{ADMIN_SESSION['session_id']}"
            ).click().run()
            self.assertEqual(admin_app.session_state["admin_page"], "Conversations")
            self.assertEqual(
                admin_app.session_state["admin_selected_user_id"], ADMIN_USER["id"]
            )
            self.assertEqual(
                admin_app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )
            self.assertEqual(
                admin_app.session_state["admin_mobile_page_picker"],
                "Conversations",
            )
            self.assertEqual(
                admin_app.session_state["admin_case_user_picker"],
                ADMIN_USER["id"],
            )
            self.assertEqual(
                admin_app.session_state["admin_case_session_picker"],
                ADMIN_SESSION["session_id"],
            )
            admin_app.run()
            self.assertEqual(admin_app.session_state["admin_page"], "Conversations")
            self.assertTrue(
                any(
                    "Mere husband ne kal meri kalai pakri." in str(item.value)
                    for item in admin_app.markdown
                )
            )

        source = app_path.read_text(encoding="utf-8")
        self.assertIn('@st.fragment(run_every="5s")\ndef render_user_unread_bubble()', source)
        self.assertIn('@st.fragment(run_every="5s")\ndef render_admin_inbox_notification()', source)
        self.assertIn(".st-key-user_unread_bar", source)
        self.assertIn(".st-key-admin_inbox_bar", source)
        self.assertIn("background: #c83245", source)

    def test_admin_active_conversation_switcher_opens_each_chat(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        active_session = {
            **ADMIN_SESSION,
            "user_id": ADMIN_USER["id"],
            "email": ADMIN_USER["email"],
            "display_name": ADMIN_USER["display_name"],
            "conversation_mode": "listener",
            "control_mode": "human",
        }

        def active_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/admin/sessions/active?minutes=60"):
                return StubResponse([active_session])
            if method == "GET" and url.endswith("/admin/inbox?limit=20"):
                return StubResponse({"total_unread": 0, "conversations": []})
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=active_request):
            admin_app = AppTest.from_file(str(app_path), default_timeout=10)
            admin_app.query_params["admin"] = "1"
            admin_app.run()
            admin_app.session_state["admin_key"] = "test-admin-key"
            admin_app.session_state["admin_page"] = "Overview"
            admin_app.run()

            self.assertTrue(
                any(
                    ADMIN_SESSION["latest_message_preview"] in str(item.value)
                    for item in admin_app.markdown
                )
            )
            admin_app.button(
                key=f"open_admin_active_{ADMIN_SESSION['session_id']}"
            ).click().run()
            self.assertEqual(admin_app.session_state["admin_page"], "Conversations")
            self.assertEqual(
                admin_app.session_state["admin_selected_user_id"], ADMIN_USER["id"]
            )
            self.assertEqual(
                admin_app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )

        source = app_path.read_text(encoding="utf-8")
        self.assertIn("def open_admin_conversation_from_switcher(", source)
        self.assertIn("admin-conversation-switcher-marker", source)
        self.assertIn("admin-conversation-menu-item", source)
        self.assertIn('f"open_admin_active_{session_id}"', source)
        self.assertIn("Needs reply", source)

    def test_admin_user_history_opens_chat_and_stays_open(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        with patch("requests.request", side_effect=fake_request):
            admin_app = AppTest.from_file(str(app_path), default_timeout=10)
            admin_app.query_params["admin"] = "1"
            admin_app.run()
            admin_app.session_state["admin_key"] = "test-admin-key"
            admin_app.session_state["admin_page"] = "Users"
            admin_app.run()

            admin_app.button(
                key=f"user_open_session_{ADMIN_SESSION['session_id']}"
            ).click().run()
            self.assertEqual(admin_app.session_state["admin_page"], "Conversations")
            self.assertEqual(
                admin_app.session_state["admin_selected_user_id"], ADMIN_USER["id"]
            )
            self.assertEqual(
                admin_app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )
            self.assertTrue(
                any(
                    "Mere husband ne kal meri kalai pakri." in str(item.value)
                    for item in admin_app.markdown
                )
            )

            admin_app.run()
            self.assertEqual(admin_app.session_state["admin_page"], "Conversations")
            self.assertEqual(
                admin_app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )

    def test_browser_posts_read_and_typing_without_streamlit_callbacks(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("def mount_user_chat_transport(", source)
        self.assertIn(
            "mount_user_chat_transport(str(st.session_state.session_id))", source
        )
        self.assertIn('status.get("user_typing")', source)
        self.assertIn("is typing…", source)
        self.assertIn('class="admin-typing-bubble"', source)
        self.assertIn('role="status" aria-live="polite"', source)
        self.assertIn(
            '@st.fragment(run_every="2s")\n'
            'def render_admin_composer_typing_status(',
            source,
        )
        self.assertIn('f"/admin/sessions/{selected_session_id}/typing"', source)
        self.assertIn('.st-key-admin_composer_presence', source)
        self.assertNotIn("typing_capture_component(", source)
        self.assertNotIn('"dilse_typing_capture"', source)
        self.assertIn("__dilseChatTransport", source)
        self.assertIn("postSessionEvent", source)
        self.assertIn(
            '`/api/sessions/${{encodeURIComponent(sessionId)}}/${{eventName}}`',
            source,
        )
        self.assertIn('"X-User-Token": userToken', source)
        self.assertIn('postSessionEvent("typing", {{ is_typing: nextState }})', source)
        self.assertIn('"read",\n                            {{ message_ids: messageIds }}', source)
        self.assertNotIn('event.get("event_type") == "typing"', source)
        self.assertNotIn('f"/sessions/{session_id}/read"', source)
        self.assertNotIn('f"/sessions/{session_id}/typing"', source)
        self.assertNotIn("installRecordingGuard", source)
        self.assertNotIn("dilse:voice-recording", source)
        self.assertNotIn("recordingButton", source)
        self.assertNotIn('st.button("Voice recording started"', source)
        self.assertNotIn('st.button("Voice recording stopped"', source)
        self.assertIn("on_dismiss=close_user_voice_note_dialog", source)
        self.assertIn("st.session_state.voice_recording_active = True", source)
        self.assertIn("st.session_state.voice_recording_active = False", source)
        self.assertIn('st.session_state.get("voice_recording_active")', source)
        self.assertIn("voice_recording_pending_refresh", source)
        self.assertIn('[data-testid="stChatInput"] textarea', source)
        self.assertIn("assistantMessageIds", source)
        self.assertIn("sendReadReceipts", source)
        self.assertIn("state.suppressEventsUntil = Date.now() + 2500", source)
        self.assertIn("onComposerPointerDown", source)
        self.assertIn('sendTyping(false, true);', source)
        self.assertIn("pendingReadIds", source)
        self.assertIn("confirmedReadIds", source)
        self.assertIn("IntersectionObserver", source)
        self.assertIn("data-dilse-read-message-id", source)
        self.assertIn("admin-read-receipt", source)
        self.assertIn("admin-message-meta-copy", source)
        self.assertIn("--admin-bubble-pad-x", source)
        self.assertIn("background: #245e58", source)
        self.assertIn("overflow-wrap: anywhere", source)
        self.assertIn("white-space: pre-wrap", source)
        self.assertIn('with st.expander(image_label, expanded=False):', source)
        self.assertNotIn('st.button("Refresh transcript"', source)

        with patch.dict(ADMIN_DETAIL, {"user_typing": True}), patch(
            "requests.request", side_effect=fake_request
        ):
            admin_app = AppTest.from_file(str(app_path), default_timeout=10)
            admin_app.query_params["admin"] = "1"
            admin_app.run()
            admin_app.session_state["admin_key"] = "test-admin-key"
            admin_app.session_state["admin_page"] = "Conversations"
            admin_app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            admin_app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            admin_app.run()

            rendered = "\n".join(str(item.value) for item in admin_app.markdown)
            self.assertIn("Nadia</strong> is typing", rendered)
            self.assertIn("admin-typing-bubble", rendered)
            self.assertLess(
                rendered.index("Nadia</strong> is typing"),
                rendered.index("Write the next DilSe message"),
            )
            self.assertGreater(
                rendered.index("Nadia</strong> is typing"),
                rendered.index("Kya yeh pehli baar hua"),
            )
        conversation_renderer = source[
            source.index("def render_admin_conversations(") :
            source.index("def render_admin_live(")
        ]
        self.assertLess(
            conversation_renderer.index("render_admin_composer_typing_status("),
            conversation_renderer.index("render_admin_transcript_composer("),
        )
        self.assertIn('receipt_label = "Read" if read_at else "Unread"', source)
        self.assertIn('message.get("read_basis") == "reply"', source)

    def test_user_text_message_reaches_the_chat_api(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "ui-test-token"
            app.session_state["user"] = USER
            app.run()

            app.button(key="new_chat_choose_listener").click().run()
            app.chat_input[0].set_value("I need help with a difficult conversation.").run()
            self.assertEqual(list(app.exception), [])

            sent_messages = [
                item
                for item in app.session_state["messages"]
                if item.get("role") == "user"
            ]
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(sent_messages[0]["message_id"], 501)
            self.assertEqual(
                sent_messages[0]["content"],
                "I need help with a difficult conversation.",
            )

    def test_user_chat_auto_loads_every_new_assistant_response(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn('@st.fragment(run_every="1s")\ndef watch_live_session()', source)
        self.assertIn('if not user or not st.session_state.auth_token or not user.get("store_chats"):', source)
        self.assertIn('&known_count={known_count}', source)
        self.assertIn('"source": item.get("source") or "ai"', source)
        self.assertNotIn('if item["source"] == "admin":', source)
        self.assertNotIn("DilSe team", source)
        self.assertIn('st.rerun(scope="app")', source)

    def test_account_offers_private_unread_email_notifications(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("Email me about unread DilSe responses", source)
        self.assertIn("/account/notifications", source)
        self.assertIn("send one private reminder within an hour", source)

    def test_account_deletion_collects_a_reason_and_shows_a_receipt(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("Why are you leaving? (optional)", source)
        self.assertIn('"departure_reason": ACCOUNT_DELETION_REASONS[', source)
        self.assertIn("def complete_account_deletion(", source)
        self.assertIn("def render_account_deletion_confirmation(", source)
        self.assertIn("Your DilSe account has been deleted.", source)
        self.assertIn("Historical protected backups", source)
        self.assertIn("if response.status_code == 200:", source)
        account_section = source[
            source.index("def render_account()") : source.index("def set_main_page(")
        ]
        self.assertNotIn("if response.status_code == 204:", account_section)

        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["account_deletion_receipt"] = {
                "deleted_at": "2026-09-05T17:30:00+00:00",
                "confirmation_reference": "DIL-20260905-ABC123",
                "email_sent": True,
                "departure_reason": "Privacy or trust concerns",
            }
            app.run()

            rendered = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Your DilSe account has been deleted.", rendered)
            self.assertIn("DIL-20260905-ABC123", rendered)
            self.assertIn("Privacy or trust concerns", rendered)
            self.assertIn("A copy of this confirmation was sent", rendered)
            self.assertEqual(len(app.text_input), 0)

    def test_account_offers_private_android_phone_alerts_outside_chat(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        component_path = app_path.parent / "components" / "phone_alerts" / "index.html"
        worker_path = app_path.parent / "components" / "phone_alerts" / "push-sw.js"
        source = app_path.read_text(encoding="utf-8")
        component_source = component_path.read_text(encoding="utf-8")
        worker_source = worker_path.read_text(encoding="utf-8")

        self.assertIn("def render_phone_alert_settings()", source)
        self.assertIn('"/account/push/subscriptions"', source)
        self.assertIn('"/account/push/unsubscribe"', source)
        self.assertIn(
            'sw_url="/component/app.dilse_phone_alerts/push-sw.js"', source
        )
        self.assertIn("Notification.requestPermission()", component_source)
        self.assertIn("pushManager.subscribe", component_source)
        self.assertIn("No message text is shown", component_source)
        self.assertIn('self.addEventListener("push"', worker_source)
        self.assertIn('client.visibilityState === "visible"', worker_source)
        self.assertIn("A DilSe response is waiting for you.", worker_source)
        self.assertNotIn("administrator", worker_source.lower())

    def test_chat_offers_private_voice_notes_and_admin_playback(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn('st.audio_input(', source)
        self.assertIn('@st.dialog(', source)
        self.assertIn('"Voice note",', source)
        self.assertIn("on_dismiss=close_user_voice_note_dialog", source)
        self.assertIn("def render_user_voice_note_dialog(", source)
        self.assertNotIn('with st.popover(\n                "Record voice note"', source)
        self.assertIn('"Send voice note"', source)
        self.assertIn('/voice-notes"', source)
        self.assertIn('"upload_id": upload_id', source)
        self.assertIn('voice_note_uploads.get(upload_id) == "uploading"', source)
        self.assertIn('voice_note_uploads.get(upload_id) == "sent"', source)
        self.assertIn('f"/admin/messages/{message_id}/voice-note"', source)
        self.assertIn('st.audio(', source)
        self.assertIn('f"Play voice note{duration_label}"', source)
        self.assertIn('icon=":material/play_arrow:"', source)
        self.assertIn('"Close voice note"', source)
        self.assertIn('div[class*="st-key-open_voice_note_"] .stButton button', source)
        self.assertIn('-webkit-text-fill-color: #173f3b !important', source)
        self.assertIn('width: min(100%, 250px) !important', source)
        self.assertIn('[data-testid="stChatMessageContent"] [data-testid="stAudio"]', source)
        self.assertIn('width: min(78%, 680px)', source)
        self.assertIn(
            'DILSE_MESSAGE_MEDIA_CACHE_MAX_BYTES", str(100 * 1024 * 1024)',
            source,
        )
        self.assertIn(
            'DILSE_MESSAGE_MEDIA_MAX_OPEN_VOICE_NOTES", "6"',
            source,
        )
        self.assertIn(
            'set_message_media_scope(f"admin:{selected_session_id}")', source
        )
        self.assertIn(
            'set_message_media_scope(f"user:{st.session_state.session_id}")', source
        )
        self.assertIn("def admin_transcript_signature(", source)
        self.assertIn("def render_admin_live_status(", source)
        self.assertIn("def render_admin_transcript(", source)
        live_status = source[
            source.index("def render_admin_live_status(") :
            source.index("def render_admin_transcript(")
        ]
        self.assertNotIn("render_message_body(", live_status)
        self.assertNotIn("st.audio(", live_status)
        self.assertIn("Stop and play the preview before sending.", source)
        self.assertIn("will not include any conversation details", source)
        account_section = source[source.index("def render_account()") : source.index("def set_main_page(")]
        self.assertNotIn("administrator response", account_section.lower())

    def test_new_chat_requires_a_prominent_mode_choice_before_chat(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "test-token"
            app.session_state["user"] = USER
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("How should DilSe respond?", markdown)
            self.assertEqual(len(app.chat_input), 0)
            self.assertFalse(app.session_state["conversation_mode_confirmed"])

            app.button(key="new_chat_choose_listener").click().run()

            self.assertTrue(app.session_state["conversation_mode_confirmed"])
            self.assertEqual(app.session_state["conversation_mode"], "The Listener")
            self.assertGreater(len(app.chat_input), 0)

    def test_new_conversation_experience_is_isolated_from_legacy_users(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        v2_user = {**USER, "experience_version": 2}

        def v2_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/auth/me"):
                return StubResponse(v2_user)
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=v2_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.run()
            app.session_state["auth_token"] = "v2-test-token"
            app.session_state["user"] = v2_user
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("What would help right now?", markdown)
            self.assertNotIn("How should DilSe respond?", markdown)
            self.assertEqual(len(app.chat_input), 0)

            app.button(key="v2_new_chat_choose_partner").click().run()

            self.assertTrue(app.session_state["conversation_mode_confirmed"])
            self.assertEqual(app.session_state["conversation_mode"], "The Partner")
            self.assertTrue(any(item.key == "v2_persona_husband" for item in app.button))


    def test_login_persistence_and_three_panel_shell_are_present(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn("def remember_browser_login", source)
        self.assertIn("def restore_browser_login", source)
        self.assertIn("def remember_admin_browser_login", source)
        self.assertIn("def restore_admin_browser_login", source)
        self.assertIn("def forget_admin_browser_login", source)
        self.assertIn('BROWSER_COOKIE_NAME = "dilse_browser"', source)
        self.assertIn("def ensure_browser_identity", source)
        self.assertIn('f"{BACKEND_URL}/auth/browser-session/restore"', source)
        self.assertIn('f"{BACKEND_URL}/admin/browser-session/restore"', source)
        self.assertIn('headers["X-Admin-Browser-Session"]', source)
        self.assertIn("render_signed_in_shell(catalog)", source)
        self.assertIn("render_talk(catalog, right)", source)
        self.assertNotIn("with st.sidebar:", source)

    def test_admin_workspace_has_clear_navigation_and_overview(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.run()

            button_labels = {item.label for item in app.button}
            self.assertTrue(
                {
                    "Overview",
                    "App usage · 1 installed",
                    "Users",
                    "Conversations",
                    "Live sessions · 0",
                    "Prompt studio",
                    "Response quality",
                    "Content library",
                    "Audit log",
                    "Lock workspace",
                }.issubset(button_labels)
            )
            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("What needs attention", markdown)
            self.assertIn("Review available", markdown)
            self.assertIn("Recent accounts", markdown)

    def test_admin_can_start_a_partner_chat_with_a_selected_character(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        created_payloads: list[dict[str, object]] = []

        def start_chat_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "GET" and url.endswith("/admin/catalog/personas"):
                return StubResponse([{**item, "id": index + 1, "active": 1} for index, item in enumerate(CATALOG["personas"])])
            if method == "GET" and url.endswith("/admin/catalog/scenarios"):
                return StubResponse([{**item, "id": index + 1, "active": 1} for index, item in enumerate(CATALOG["scenarios"])])
            if method == "POST" and url.endswith("/admin/sessions"):
                created_payloads.append(dict(kwargs.get("json") or {}))
                return StubResponse(
                    {
                        "session_id": "admin_new_partner_123",
                        "message_id": 777,
                        "user_id": ADMIN_USER["id"],
                        "mode": "partner",
                        "persona": "crush",
                    },
                    201,
                )
            return fake_request(method, url, **kwargs)

        with patch("requests.request", side_effect=start_chat_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.query_params["admin_view"] = "Conversations"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.run()

            self.assertTrue(any(item.label == "Start a new chat" for item in app.expander))
            app.radio(key="admin_new_chat_mode").set_value("Partner").run()

            self.assertEqual(app.selectbox(key="admin_new_chat_persona").value, "husband")
            app.selectbox(key="admin_new_chat_persona").set_value("crush").run()
            app.text_area(key="admin_new_chat_character_details").set_value(
                "His name is Ayaan and he uses dry humour."
            )
            app.text_area(key="admin_new_chat_opening_message").set_value(
                "I was hoping you would message me tonight."
            )
            next(
                item
                for item in app.button
                if item.label == "Start chat and send message"
            ).click().run()

            self.assertEqual(len(created_payloads), 1)
            self.assertEqual(created_payloads[0]["user_id"], ADMIN_USER["id"])
            self.assertEqual(created_payloads[0]["mode"], "partner")
            self.assertEqual(created_payloads[0]["persona"], "crush")
            self.assertEqual(
                created_payloads[0]["opening_message"],
                "I was hoping you would message me tonight.",
            )

    def test_admin_app_usage_shows_installations_and_message_sources(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.query_params["admin_view"] = "App usage"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Registered installations", markdown)
            self.assertIn("Where tracked user messages come from", markdown)
            self.assertIn("Notifications enabled", markdown)
            self.assertIn("Connected installations", markdown)
            self.assertTrue(
                any(item.label == "Message source" for item in app.selectbox)
            )
            self.assertEqual(app.query_params["admin_view"], ["App usage"])

    def test_admin_refresh_restores_the_selected_conversation(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.query_params["admin_view"] = "Conversations"
            app.query_params["admin_user"] = str(ADMIN_USER["id"])
            app.query_params["admin_session"] = ADMIN_SESSION["session_id"]
            app.run()

            self.assertEqual(app.session_state["admin_page"], "Conversations")
            self.assertEqual(app.session_state["admin_selected_user_id"], ADMIN_USER["id"])
            self.assertEqual(
                app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )

            app.session_state["admin_key"] = "test-admin-key"
            app.run()
            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Mere husband ne kal meri kalai pakri.", markdown)
            self.assertIn("Android app", markdown)
            self.assertEqual(app.query_params["admin_view"], ["Conversations"])
            self.assertEqual(
                app.query_params["admin_session"],
                [ADMIN_SESSION["session_id"]],
            )

    def test_admin_conversation_shows_user_view_and_fixed_controls(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request) as request_mock:
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Conversations"
            app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            button_labels = {item.label for item in app.button}
            expander_labels = {item.label for item in app.expander}
            self.assertIn("Mere husband ne kal meri kalai pakri.", markdown)
            self.assertIn("Kya yeh pehli baar hua", markdown)
            self.assertIn("AI · 08 Aug 12:05 · #2 · gpt-oss-120b", markdown)
            self.assertIn("Case controls", markdown)
            self.assertIn("New conversations start with human control", markdown)
            self.assertIn("Write the next DilSe message", markdown)
            self.assertIn("Take human control", button_labels)
            self.assertIn("Take human control to reply", button_labels)
            self.assertIn("Session AI guidance", expander_labels)
            self.assertIn("User AI guidance", expander_labels)
            self.assertIn("Review note", expander_labels)
            self.assertIn("Save a better response", expander_labels)
            self.assertEqual(
                sum(item.label == "×" for item in app.button),
                2,
            )
            source = app_path.read_text(encoding="utf-8")
            self.assertIn('help="Delete this message"', source)
            self.assertIn('div[class*="st-key-delete_message_"] .stButton button', source)
            self.assertIn('.block-container:has(.admin-shell-marker) [data-testid="stChatMessage"]', source)
            self.assertIn('position: absolute;\n        top: .45rem;\n        right: .25rem;', source)
            self.assertIn('with st.container(key="admin_chat_composer")', source)
            self.assertIn('type=["jpg", "jpeg", "png", "webp"]', source)
            self.assertIn("clickable_admin_message(content)", source)
            self.assertIn('body:has(.admin-shell-marker) [data-stale="true"]', source)
            self.assertIn("opacity: 1 !important", source)
            self.assertIn("width: min(94%, 920px)", source)
            self.assertIn("flex: 1 1 0", source)
            self.assertIn("padding: .52rem .82rem", source)
            self.assertIn("padding: .6rem .95rem", source)
            self.assertIn("padding: .58rem .92rem", source)
            self.assertIn('class="admin-message-meta"', source)
            self.assertIn('rsplit("/", 1)[-1]', source)

            delete_target = f"{ADMIN_SESSION['session_id']}:2"
            app.button(key=f"delete_message_{delete_target}").click().run()
            self.assertTrue(
                any("Permanently delete message 2" in str(item.value) for item in app.warning)
            )
            app.button(key=f"confirm_delete_message_{delete_target}").click().run()
            self.assertTrue(
                any(
                    call.args[0] == "DELETE"
                    and call.args[1].endswith(
                        f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages/2"
                    )
                    for call in request_mock.call_args_list
                )
            )

    def test_human_control_composer_sends_from_below_the_transcript(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        def human_control_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "POST" and url.endswith("/admin/writing/roman-urdu/check"):
                original = str(kwargs["json"]["content"])
                return StubResponse(
                    {
                        "original": original,
                        "corrected": "Please review https://www.baatdilse.com/resources carefully",
                        "changed": True,
                        "notice": None,
                    }
                )
            if method == "POST" and url.endswith(
                f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
            ):
                return StubResponse({"id": 3, "attachment_id": None}, 201)
            return fake_request(method, url, **kwargs)

        with patch.dict(ADMIN_DETAIL["session_control"], {"mode": "human"}), patch(
            "requests.request", side_effect=human_control_request
        ) as request_mock:
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Conversations"
            app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            app.run()

            composer = next(
                item for item in app.text_area if item.label == "Administrator message"
            )
            self.assertFalse(composer.disabled)
            roman_urdu_check = next(
                item for item in app.toggle if item.label == "Roman Urdu"
            )
            self.assertTrue(roman_urdu_check.value)
            composer.input("Please review https://www.baatdilse.com/resources")
            app.button(
                key=(
                    "FormSubmitter:"
                    f"admin_chat_composer_form_{ADMIN_SESSION['session_id']}_0"
                    "-Review words"
                )
            ).click().run()

            self.assertFalse(
                any(
                    call.args[0] == "POST"
                    and call.args[1].endswith(
                        f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
                    )
                    for call in request_mock.call_args_list
                )
            )
            review_markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Nothing has been sent yet", review_markdown)
            self.assertIn("Roman Urdu check", review_markdown)
            review_buttons = {item.label for item in app.button}
            self.assertIn("Use correction", review_buttons)
            self.assertIn("Keep original", review_buttons)
            self.assertIn("Edit again", review_buttons)
            app.button(key=f"admin_use_roman_urdu_{ADMIN_SESSION['session_id']}").click().run()

            send_call = next(
                call
                for call in request_mock.call_args_list
                if call.args[0] == "POST"
                and call.args[1].endswith(
                    f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
                )
            )
            self.assertEqual(
                send_call.kwargs["json"]["content"],
                "Please review https://www.baatdilse.com/resources carefully",
            )
            self.assertEqual(
                send_call.kwargs["json"]["original_content"],
                "Please review https://www.baatdilse.com/resources",
            )
            self.assertEqual(
                send_call.kwargs["json"]["roman_urdu_review_status"],
                "corrected",
            )

    def test_admin_composer_offers_text_and_voice_delivery_modes(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn(
            'else ["Text", "Text + audio", "Audio only"]',
            source,
        )
        self.assertIn('options=["Type", "Record"]', source)
        self.assertIn('st.audio_input(', source)
        self.assertIn('"draft_source": draft_source', source)
        self.assertIn('"recording_base64": base64.b64encode(recording_bytes)', source)
        self.assertIn(
            'f"/admin/sessions/{selected_session_id}/voice-transcription"',
            source,
        )
        self.assertIn('["Natural", "Seductive"]', source)
        self.assertNotIn('if latest_mode == "partner"', source)
        self.assertIn(
            'Choose the Troy delivery style for this {latest_mode.title()} reply.',
            source,
        )
        self.assertIn('"delivery_mode": delivery_mode', source)
        self.assertIn('"voice_style": voice_style', source)
        self.assertIn('with st.spinner("Creating a private voice preview…"):', source)
        self.assertIn("Hear before sending", source)
        self.assertIn('"Send this audio"', source)
        self.assertIn('f"/admin/sessions/{session_id}/voice-preview"', source)
        self.assertIn(
            'content == "Voice note" and message.get("voice_note_id")',
            source,
        )

    def test_admin_record_source_reveals_recorder_immediately(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch.dict(ADMIN_DETAIL["session_control"], {"mode": "human"}), patch(
            "requests.request", side_effect=fake_request
        ):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Conversations"
            app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            app.run()

            draft_source = next(item for item in app.radio if item.label == "Draft with")
            draft_source.set_value("Record").run()

            self.assertTrue(
                any(
                    getattr(item, "label", None) == "Record voice draft"
                    for item in app.get("audio_input")
                )
            )
            delivery = next(item for item in app.radio if item.label == "Send as")
            self.assertEqual(delivery.options, ["Text + audio", "Audio only"])
            self.assertFalse(
                any(item.label == "Administrator message" for item in app.text_area)
            )

    def test_admin_can_send_without_roman_urdu_review(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        def direct_send_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "POST" and url.endswith(
                f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
            ):
                return StubResponse({"id": 3, "attachment_id": None}, 201)
            return fake_request(method, url, **kwargs)

        with patch.dict(ADMIN_DETAIL["session_control"], {"mode": "human"}), patch(
            "requests.request", side_effect=direct_send_request
        ) as request_mock:
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Conversations"
            app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            app.run()

            composer = next(
                item for item in app.text_area if item.label == "Administrator message"
            )
            composer.input("Meri apni wording bhej dein")
            app.button(
                key=(
                    "FormSubmitter:"
                    f"admin_chat_composer_form_{ADMIN_SESSION['session_id']}_0"
                    "-Send now"
                )
            ).click().run()

            writing_checks = [
                call
                for call in request_mock.call_args_list
                if call.args[0] == "POST"
                and call.args[1].endswith("/admin/writing/roman-urdu/check")
            ]
            self.assertEqual(writing_checks, [])
            send_call = next(
                call
                for call in request_mock.call_args_list
                if call.args[0] == "POST"
                and call.args[1].endswith(
                    f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
                )
            )
            self.assertEqual(send_call.kwargs["json"]["content"], "Meri apni wording bhej dein")
            self.assertEqual(
                send_call.kwargs["json"]["roman_urdu_review_status"],
                "not_checked",
            )
            self.assertEqual(app.session_state["admin_page"], "Conversations")
            self.assertEqual(
                app.session_state["admin_selected_session_id"],
                ADMIN_SESSION["session_id"],
            )
            self.assertEqual(
                app.session_state["admin_mobile_page_picker"],
                "Conversations",
            )
            app.run()
            self.assertEqual(app.session_state["admin_page"], "Conversations")

    def test_admin_hears_the_exact_voice_preview_before_sending(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        preview_audio = base64.b64encode(b"RIFFpreviewWAVE").decode("ascii")

        def preview_request(method: str, url: str, **kwargs: object) -> StubResponse:
            if method == "POST" and url.endswith(
                f"/admin/sessions/{ADMIN_SESSION['session_id']}/voice-preview"
            ):
                return StubResponse(
                    {
                        "transcript": kwargs["json"]["content"],
                        "audio_base64": preview_audio,
                        "audio_mime_type": "audio/wav",
                        "audio_filename": "dilse-troy-natural-preview.wav",
                        "duration_seconds": 1.2,
                        "voice_style": "conversational",
                    }
                )
            if method == "POST" and url.endswith(
                f"/admin/sessions/{ADMIN_SESSION['session_id']}/messages"
            ):
                return StubResponse(
                    {"id": 3, "attachment_id": None, "voice_note_id": 1},
                    201,
                )
            return fake_request(method, url, **kwargs)

        with patch.dict(ADMIN_DETAIL["session_control"], {"mode": "human"}), patch(
            "requests.request", side_effect=preview_request
        ) as request_mock:
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Conversations"
            app.session_state["admin_selected_user_id"] = ADMIN_USER["id"]
            app.session_state["admin_selected_session_id"] = ADMIN_SESSION["session_id"]
            app.run()

            delivery = next(item for item in app.radio if item.label == "Send as")
            delivery.set_value("Text + audio").run()
            voice_style = next(item for item in app.radio if item.label == "Voice style")
            self.assertEqual(voice_style.options, ["Natural", "Seductive"])
            composer = next(
                item for item in app.text_area if item.label == "Administrator message"
            )
            composer.input("Aap araam se batayein.")
            app.button(
                key=(
                    "FormSubmitter:"
                    f"admin_chat_composer_form_{ADMIN_SESSION['session_id']}_0"
                    "-Make voice preview"
                )
            ).click().run()

            preview_buttons = {item.label for item in app.button}
            self.assertIn("Send this audio", preview_buttons)
            self.assertIn("Regenerate", preview_buttons)
            self.assertIn("Edit", preview_buttons)
            self.assertEqual(
                [
                    call
                    for call in request_mock.call_args_list
                    if call.args[0] == "POST" and call.args[1].endswith("/messages")
                ],
                [],
            )
            app.button(
                key=f"admin_send_voice_preview_{ADMIN_SESSION['session_id']}"
            ).click().run()

            send_call = next(
                call
                for call in request_mock.call_args_list
                if call.args[0] == "POST" and call.args[1].endswith("/messages")
            )
            self.assertEqual(
                send_call.kwargs["json"]["voice_preview_base64"],
                preview_audio,
            )

    def test_admin_audit_includes_private_message_revision_history(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")

        self.assertIn('admin_json("GET", "/admin/message-revisions?limit=200")', source)
        self.assertIn("Administrator message review", source)
        self.assertIn("Original and approved versions are retained privately", source)

    def test_admin_visitor_tracker_shows_live_page_and_masked_history(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch("requests.request", side_effect=fake_request):
            app = AppTest.from_file(str(app_path), default_timeout=10)
            app.query_params["admin"] = "1"
            app.run()
            app.session_state["admin_key"] = "test-admin-key"
            app.session_state["admin_page"] = "Visitors"
            app.run()

            markdown = "\n".join(str(item.value) for item in app.markdown)
            self.assertIn("Website activity", markdown)
            self.assertIn("Visitors are active now", markdown)
            self.assertIn("Dashboard · Talk", markdown)
            self.assertIn("198.51.100.xxx", markdown)
            self.assertIn("Masked before storage", markdown)
            self.assertGreater(len(app.dataframe), 0)
            self.assertTrue(any(item.label == "Last page" for item in app.selectbox))
            self.assertIn('"Masked IP": visit.get("ip_prefix")', app_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
