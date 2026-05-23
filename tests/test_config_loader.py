from pathlib import Path
import unittest

from pynginx.config.loader import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config(Path("config/pynginx.conf"))

        self.assertEqual(config.servers[0].listen_port, 8080)
        self.assertEqual(config.servers[0].locations[1].proxy_pass, "http://127.0.0.1:9000")
        self.assertEqual(config.header_limit, 16384)
