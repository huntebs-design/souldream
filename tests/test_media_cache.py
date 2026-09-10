"""Regression tests for bounded Streamlit message-media storage."""

import unittest

from media_cache import media_cache_bytes, store_bounded_media


class MediaCacheTests(unittest.TestCase):
    def test_evicts_oldest_payloads_to_stay_under_byte_limit(self) -> None:
        cache: dict[str, bytes | None] = {}

        self.assertTrue(
            store_bounded_media(cache, "first", b"a" * 6, max_bytes=10, max_items=4)
        )
        self.assertTrue(
            store_bounded_media(cache, "second", b"b" * 6, max_bytes=10, max_items=4)
        )

        self.assertEqual(cache, {"second": b"b" * 6})
        self.assertLessEqual(media_cache_bytes(cache), 10)

    def test_evicts_oldest_entries_to_stay_under_item_limit(self) -> None:
        cache: dict[str, bytes | None] = {}
        store_bounded_media(cache, "first", None, max_bytes=10, max_items=2)
        store_bounded_media(cache, "second", b"b", max_bytes=10, max_items=2)
        store_bounded_media(cache, "third", b"c", max_bytes=10, max_items=2)

        self.assertEqual(list(cache), ["second", "third"])

    def test_does_not_retain_a_payload_larger_than_the_total_budget(self) -> None:
        cache: dict[str, bytes | None] = {"existing": b"a"}

        retained = store_bounded_media(
            cache,
            "oversized",
            b"b" * 11,
            max_bytes=10,
            max_items=2,
        )

        self.assertFalse(retained)
        self.assertEqual(cache, {"existing": b"a"})


if __name__ == "__main__":
    unittest.main()
