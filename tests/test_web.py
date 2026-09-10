"""Regression checks for the Pakistan-focused public site."""

import asyncio
import json
import mimetypes
import re
import os
from unittest.mock import AsyncMock, patch
import unittest
from pathlib import Path

import web


class PublicSiteTests(unittest.TestCase):
    def test_complete_bilingual_topic_library(self):
        self.assertEqual(len(web.TOPICS), 22)
        self.assertEqual(len(web.URDU_TOPICS), 22)
        for english_slug, topic in web.TOPICS.items():
            self.assertIn("urdu", topic, english_slug)
            urdu_slug = topic["urdu"]
            self.assertIn(urdu_slug, web.URDU_TOPICS)
            self.assertEqual(web.URDU_TOPICS[urdu_slug]["english"], english_slug)

    def test_home_has_complete_indexable_metadata_and_content(self):
        html = web.home_page()
        self.assertIn("<html lang=\"en-PK\"", html)
        self.assertRegex(html, r"<title>DilSe Pakistan \| [^<]+</title>")
        self.assertIn("rel=\"canonical\" href=\"https://www.baatdilse.com/\"", html)
        self.assertIn("hreflang=\"ur-PK\"", html)
        self.assertIn("Relationship conversation practice for Pakistani women", html)
        self.assertIn("/app/?auth=create", html)
        self.assertNotIn("India", html)
        self.assertNotIn("Hindi", html)

    def test_urdu_page_has_language_and_direction(self):
        html = web.urdu_page()
        self.assertIn("<html lang=\"ur-PK\" dir=\"rtl\">", html)
        self.assertIn("رشتوں کے بارے میں مشکل گفتگو کی تیاری", html)
        self.assertIn("hreflang=\"en-PK\"", html)
        for slug in web.URDU_TOPICS:
            self.assertIn(f'/ur/{slug}/', html)

    def test_topic_pages_are_distinct_and_canonical(self):
        for slug, topic in web.TOPICS.items():
            with self.subTest(slug=slug):
                html = web.topic_page(slug)
                self.assertIn(topic["heading"], html)
                self.assertIn(f"https://www.baatdilse.com/topics/{slug}/", html)
                self.assertIn("BreadcrumbList", html)
                self.assertIn("Related conversations", html)
                self.assertIn("Practise the words in your own voice", html)
                self.assertIn(f'/assets/topics/{slug}.webp', html)
                self.assertTrue((Path(web.ROOT) / "assets" / "topics" / f"{slug}.webp").is_file())
                for related_slug in topic["related"]:
                    self.assertIn(f'/topics/{related_slug}/', html)

    def test_topic_hub_links_every_guide(self):
        html = web.topic_hub_page()
        for slug in web.TOPICS:
            self.assertIn(f'/topics/{slug}/', html)

    def test_urdu_guides_have_reciprocal_hreflang(self):
        for slug, topic in web.URDU_TOPICS.items():
            with self.subTest(slug=slug):
                urdu_html = web.urdu_topic_page(slug)
                english_html = web.topic_page(topic["english"])
                self.assertIn('<html lang="ur-PK" dir="rtl">', urdu_html)
                self.assertIn(f'href="https://www.baatdilse.com/ur/{slug}/"', english_html)
                self.assertIn(f'href="https://www.baatdilse.com/topics/{topic["english"]}/"', urdu_html)
                for related_slug in web.TOPICS[topic["english"]]["related"]:
                    related_urdu_slug = web.TOPICS[related_slug]["urdu"]
                    self.assertIn(f'/ur/{related_urdu_slug}/', urdu_html)

    def test_structured_data_is_valid_json(self):
        html = web.topic_page("family-boundaries")
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        types = {item["@type"] for item in data["@graph"]}
        self.assertIn("BreadcrumbList", types)

    def test_sitemap_has_hub_urdu_guides_and_images(self):
        response = asyncio.run(web.sitemap())
        xml = response.body.decode()
        self.assertIn("/conversation-topics/", xml)
        self.assertIn("/about/", xml)
        self.assertIn("<image:image>", xml)
        for slug in web.URDU_TOPICS:
            self.assertIn(f"/ur/{slug}/", xml)

    def test_topic_images_use_webp_media_type(self):
        self.assertEqual(mimetypes.guess_type("topic.webp")[0], "image/webp")

    def test_content_css_prevents_mobile_card_overflow(self):
        css = (Path(web.ROOT) / "public" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: minmax(0,1fr)", css)
        self.assertIn("aspect-ratio: 3/2", css)
        self.assertIn(".breadcrumbs .breadcrumb-current", css)
        self.assertIn("@media (max-width: 380px)", css)

    def test_android_page_has_no_download_link(self):
        html = web.android_page()
        self.assertNotIn('class="button android-download"', html)
        self.assertNotIn('/downloads/DilSe-latest.apk', html)
        self.assertIn("Listener and Partner", html)
        self.assertNotIn("Google Play", html)

    def test_apk_download_has_the_android_package_media_type(self):
        self.assertEqual(
            mimetypes.guess_type("DilSe-latest.apk")[0],
            "application/vnd.android.package-archive",
        )

    def test_home_has_no_mobile_download_links(self):
        html = web.home_page()
        hero = html.split('</section>', 1)[0]
        self.assertNotIn("Download Android app", hero)
        self.assertNotIn('/downloads/DilSe-latest.apk', hero)
        self.assertNotIn('class="button button-app"', hero)
        self.assertNotIn('class="nav-app"', hero)

    def test_android_install_prompt_is_removed(self):
        html = web.home_page()
        self.assertNotIn('id="android-install-prompt"', html)
        self.assertNotIn("/Android/i.test(navigator.userAgent)", html)
        self.assertNotIn("Download app", html)
        self.assertNotIn("Not now", html)



    def test_same_origin_api_proxy_forwards_user_auth_headers(self):
        source = (Path(web.ROOT) / "web.py").read_text(encoding="utf-8")
        self.assertIn('@app.api_route("/api/{path:path}"', source)
        self.assertIn("key.lower() != \"host\"", source)
        self.assertNotIn('key.lower() == "x-user-token"', source)
        self.assertIn('target = f"{BACKEND_ORIGIN}/{path}{query}"', source)


    def test_websocket_forwards_only_a_valid_railway_edge_ip(self):
        railway_headers = {
            "cookie": "dilse_browser=test-browser",
            "x-railway-edge": "yyz1",
            "x-real-ip": "198.51.100.42",
            "x-forwarded-for": "203.0.113.99",
        }
        with patch.dict(
            os.environ, {"RAILWAY_ENVIRONMENT_ID": "production-environment"}
        ):
            self.assertEqual(
                web.streamlit_websocket_headers(railway_headers),
                {
                    "Cookie": "dilse_browser=test-browser",
                    "X-Real-IP": "198.51.100.42",
                },
            )
            self.assertEqual(
                web.streamlit_websocket_headers(
                    {**railway_headers, "x-real-ip": "not-an-ip"}
                ),
                {"Cookie": "dilse_browser=test-browser"},
            )
            self.assertEqual(
                web.streamlit_websocket_headers(
                    {
                        "cookie": "dilse_browser=test-browser",
                        "x-real-ip": "198.51.100.42",
                    }
                ),
                {"Cookie": "dilse_browser=test-browser"},
            )
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": ""}):
            self.assertEqual(
                web.streamlit_websocket_headers(railway_headers),
                {"Cookie": "dilse_browser=test-browser"},
            )


    def test_trusted_client_ip_uses_the_edge_in_production_and_socket_locally(self):
        headers = {
            "x-railway-edge": "yyz1",
            "x-real-ip": "::ffff:198.51.100.42",
        }
        with patch.dict(
            os.environ, {"RAILWAY_ENVIRONMENT_ID": "production-environment"}
        ):
            self.assertEqual(
                web.trusted_client_ip(headers, "10.0.0.5"), "198.51.100.42"
            )
            self.assertIsNone(
                web.trusted_client_ip(
                    {"x-real-ip": "198.51.100.42"}, "10.0.0.5"
                )
            )
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": ""}):
            self.assertEqual(
                web.trusted_client_ip(
                    {"x-real-ip": "203.0.113.99"}, "127.0.0.1"
                ),
                "127.0.0.1",
            )


    def test_gateway_checks_the_persistent_backend_ip_block_list(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"blocked": True}

        class FakeAsyncClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def post(self, url, **kwargs):
                self.url = url
                self.request_kwargs = kwargs
                return FakeResponse()

        web._ip_access_cache.clear()
        with patch.object(web, "VISITOR_TRACKING_SECRET", "test-tracking-secret"), patch(
            "web.httpx.AsyncClient", FakeAsyncClient
        ):
            blocked = asyncio.run(web.backend_ip_is_blocked("198.51.100.42"))
        self.assertTrue(blocked)


    def test_gateway_enforcement_covers_http_and_existing_app_connections(self):
        source = (Path(web.ROOT) / "web.py").read_text(encoding="utf-8")
        self.assertIn('@app.middleware("http")', source)
        self.assertIn("enforce_ip_block_list", source)
        self.assertIn("async def block_monitor()", source)
        self.assertIn("WEBSOCKET_BLOCK_CHECK_SECONDS", source)
        self.assertIn("forwarded_request_headers(request)", source)

        async def allowed_response(_request):
            return web.PlainTextResponse("Allowed")

        request = web.Request(
            {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "path": "/topics/family-boundaries/",
                "raw_path": b"/topics/family-boundaries/",
                "query_string": b"",
                "headers": [],
                "client": ("198.51.100.42", 41234),
                "server": ("testserver", 80),
            }
        )
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": ""}), patch(
            "web.backend_ip_is_blocked", new=AsyncMock(return_value=True)
        ) as blocked_check:
            response = asyncio.run(
                web.enforce_ip_block_list(request, allowed_response)
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, b"Access denied.")
        blocked_check.assert_awaited_once_with("198.51.100.42")


if __name__ == "__main__":
    unittest.main()
