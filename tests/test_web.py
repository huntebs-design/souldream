"""Regression checks for the Pakistan-focused public site."""

import asyncio
import json
import mimetypes
import re
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
        self.assertIn("<title>DilSe Pakistan | Relationship Conversation Practice for Women</title>", html)
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

    def test_android_page_uses_the_signed_first_party_download(self):
        html = web.android_page()
        self.assertIn("Download DilSe for Android", html)
        self.assertIn('/downloads/DilSe-latest.apk', html)
        self.assertIn("Listener and Partner", html)
        self.assertNotIn("Google Play", html)

    def test_apk_download_has_the_android_package_media_type(self):
        self.assertEqual(
            mimetypes.guess_type("DilSe-latest.apk")[0],
            "application/vnd.android.package-archive",
        )

    def test_home_offers_the_android_app_above_the_fold(self):
        html = web.home_page()
        hero = html.split('</section>', 1)[0]
        self.assertIn("Download Android app", hero)
        self.assertIn('/downloads/DilSe-latest.apk', hero)
        self.assertIn('class="button button-app"', hero)
        self.assertIn('class="nav-app"', hero)

    def test_android_browsers_receive_a_dismissible_install_prompt(self):
        html = web.home_page()
        self.assertIn('id="android-install-prompt"', html)
        self.assertIn("/Android/i.test(navigator.userAgent)", html)
        self.assertIn("Download app", html)
        self.assertIn("Not now", html)


if __name__ == "__main__":
    unittest.main()
