from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pynginx.config.loader import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config(Path("config/pynginx.conf"))

        self.assertEqual(config.servers[0].listen_port, 8080)
        self.assertEqual(config.servers[0].locations[1].proxy_pass, "http://127.0.0.1:9000")
        self.assertEqual(config.header_limit, 16384)

    def test_loads_ssl_server_options(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "pynginx.conf"
            config_path.write_text(
                """
[server:secure]
listen = 127.0.0.1:8443
server_name = secure.local
root = public
ssl = on
ssl_certfile = certs/server.crt
ssl_keyfile = certs/server.key
""".strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertTrue(config.servers[0].ssl_enabled)
            self.assertEqual(config.servers[0].ssl_certfile, Path("certs/server.crt"))
            self.assertEqual(config.servers[0].ssl_keyfile, Path("certs/server.key"))
