from pathlib import Path

from propbot.config import load_config


def test_load_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
venues:
  binance:
    name: binance
    trading_pairs: ["BTC/USDT"]
  okx:
    name: okx
    trading_pairs: ["BTC/USDT"]
        """,
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.mode == "paper"
    assert "binance" in config.venues
