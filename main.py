from __future__ import annotations

import os
from pathlib import Path

import typer
import uvicorn

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
    if env_file is None:
        default_env = Path(".env")
        if default_env.exists():
            env_file = default_env
    resolved_config = config
    if config == Path("configs/config.paper.yaml"):
        default_profile = os.environ.get("DEFAULT_PROFILE")
        candidate = Path(f"configs/config.{default_profile}.yaml") if default_profile else None
        if candidate and candidate.exists():
            resolved_config = candidate
    context = AppContext.from_file(resolved_config, env_file=env_file)
    app = create_app(context)
    uvicorn.run(app, host=host, port=port)


@app_cli.command()
def snapshot(config: Path = typer.Option(Path("configs/config.paper.yaml"))) -> None:
    """Print a snapshot of the engine state."""
    context = AppContext.from_file(config)
    print(context.engine.snapshot())


if __name__ == "__main__":
    app_cli()
