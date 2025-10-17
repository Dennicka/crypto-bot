from pathlib import Path

from propbot.context import AppContext


def make_context(tmp_path: Path) -> AppContext:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mode: paper
safe_mode:
  enabled: false
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
    return AppContext.from_file(config_path)


def test_opportunity_generation(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    ctx.engine_state.order_books = {
        "binance": {"bid": 100.0, "ask": 100.1},
        "okx": {"bid": 101.0, "ask": 101.1},
    }
    ctx.engine.evaluate()
    assert ctx.engine_state.opportunities


def test_safe_mode_blocks_execution(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    ctx.control_state.toggle_safe_mode(True)
    ctx.engine_state.order_books = {
        "binance": {"bid": 100.0, "ask": 100.1},
        "okx": {"bid": 101.0, "ask": 101.1},
    }
    ctx.engine.evaluate()
    assert all(not record.executed for record in ctx.engine_state.executions)
