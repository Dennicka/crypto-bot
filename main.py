from __future__ import annotations

import typer
import uvicorn
from pathlib import Path

from propbot import AppContext
from propbot.api import create_app

app_cli = typer.Typer(help="PropBot arbitrage bot CLI")


@app_cli.command()
def run(
    config: Path = typer.Option(Path("configs/config.paper.yaml"), help="Path to config"),
    env_file: Path | None = typer.Option(None, help="Optional .env file"),
    host: str = typer.Option("0.0.0.0", help="Host for the API server"),
    port: int = typer.Option(8000, help="Port for the API server"),
) -> None:
    """Launch the API server with the given configuration."""
    context = AppContext.from_file(config, env_file=env_file)
    app = create_app(context)
    uvicorn.run(app, host=host, port=port)


@app_cli.command()
def snapshot(config: Path = typer.Option(Path("configs/config.paper.yaml"))) -> None:
    """Print a snapshot of the engine state."""
    context = AppContext.from_file(config)
    print(context.engine.snapshot())


if __name__ == "__main__":
    app_cli()
