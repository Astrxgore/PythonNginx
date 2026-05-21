from pathlib import Path

from pynginx.config.loader import load_config


def test_load_example_config() -> None:
    config = load_config(Path("config/pynginx.conf"))

    assert config.servers[0].listen_port == 8080
    assert config.servers[0].locations[1].proxy_pass == "http://127.0.0.1:9000"
