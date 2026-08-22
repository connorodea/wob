"""Connector health tests — deterministic, no network, no creds required."""

import pathlib
import unittest
from unittest import mock

from wob import providers


class TestHealth(unittest.TestCase):
    def test_reports_all_modules(self):
        from wob import config as C

        with (
            mock.patch.object(C, "ENV_FILE", pathlib.Path("/nope")),
            mock.patch.object(C, "ALT_ENV", pathlib.Path("/nope2")),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            rows = providers.health()
        names = {r["name"] for r in rows}
        self.assertIn("openlibrary", names)
        self.assertIn("googlebooks", names)
        self.assertIn("amazon", names)
        self.assertIn("ebay", names)

    def test_key_gated_disabled_without_creds(self):
        from wob import config as C

        with (
            mock.patch.object(C, "ENV_FILE", pathlib.Path("/nope")),
            mock.patch.object(C, "ALT_ENV", pathlib.Path("/nope2")),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            rows = {r["name"]: r for r in providers.health()}
        self.assertFalse(rows["ebay"]["enabled"])
        self.assertEqual(rows["ebay"]["missing"], "ebay_app_id+ebay_access_token")
        self.assertTrue(rows["openlibrary"]["enabled"])


if __name__ == "__main__":
    unittest.main()
