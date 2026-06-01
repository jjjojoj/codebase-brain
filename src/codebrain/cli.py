"""CodeBrain CLI — Typer entry point."""

from __future__ import annotations

import typer

app = typer.Typer(name="codebrain", help="CodeBrain — MCP server for codebase intelligence")


@app.command()
def serve() -> None:
    """Run the MCP server (stdio transport)."""
    from codebrain.server import main as run_server
    run_server()


@app.command()
def index(
    path: str = typer.Option(
        ".codebrain/conventions",
        help="Path to a directory of markdown convention files",
    ),
) -> None:
    """Index project convention files into the local store."""
    from codebrain.config import Settings
    from codebrain.core.di import init_container
    from codebrain.core.repository import Repository
    from codebrain.domains.conventions.logic import index_convention_files

    settings = Settings()
    container = init_container(settings)
    repo = Repository(container.vector_store, container.embedder)

    typer.echo(f"Indexing convention files from {path}...")
    result = index_convention_files(repo, path)
    typer.echo(
        f"  Indexed {result['indexed']} files, skipped {result['skipped']} files"
    )
    if result["errors"]:
        typer.echo("  Errors:")
        for error in result["errors"]:
            typer.echo(f"    {error['path']}: {error['error']}")


@app.command()
def info() -> None:
    """Show configuration and store stats."""
    from codebrain.config import Settings
    from codebrain.core.di import init_container

    settings = Settings()
    container = init_container(settings)

    typer.echo(f"Embedder provider:   {settings.embedder_provider}")
    typer.echo(f"Embedder model:       {settings.embedder_model}")
    typer.echo(f"Vector store backend: {settings.vector_store_backend}")
    typer.echo(f"DB path:              {settings.resolved_db_path}")

    vs = container.vector_store
    for coll in ("conventions", "session_memory", "git_history"):
        try:
            n = vs.count(coll)
            typer.echo(f"  {coll}: {n} entries")
        except Exception:
            pass


if __name__ == "__main__":
    app()
