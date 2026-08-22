"""Config validation tests — deterministic, no network."""

import os
import pathlib
import unittest
from unittest import mock

from wob import config as C


class TestConfig(unittest.TestCase):
    def test_load_from_env(self):
        env = {
            "WOB_EMAIL": "a@b.c",
            "WOB_PASSWORD": "x",
            "WOB_DATA_DIR": "/tmp/wob-data",
            "WOB_MIN_OFF": "0.80",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(C, "ENV_FILE", pathlib.Path("/nope")):
                with mock.patch.object(C, "ALT_ENV", pathlib.Path("/nope")):
                    cfg = C.load_config()
        self.assertEqual(cfg.wob_email, "a@b.c")
        self.assertEqual(cfg.data_dir, pathlib.Path("/tmp/wob-data"))
        self.assertAlmostEqual(cfg.min_off_default, 0.80)
        cfg.validate() if hasattr(cfg, "validate") else None

    def test_missing_creds_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(C, "ENV_FILE", pathlib.Path("/nope")):
                with mock.patch.object(C, "ALT_ENV", pathlib.Path("/nope")):
                    with self.assertRaises(SystemExit):
                        C.load_config()

    def test_bad_min_off(self):
        env = {"WOB_EMAIL": "a@b.c", "WOB_PASSWORD": "x", "WOB_MIN_OFF": "2"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(C, "ENV_FILE", pathlib.Path("/nope")):
                with mock.patch.object(C, "ALT_ENV", pathlib.Path("/nope")):
                    with self.assertRaises(SystemExit):
                        C.load_config()


if __name__ == "__main__":
    unittest.main()