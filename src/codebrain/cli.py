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
    project: str = typer.Option(".", help="Path to project root"),
    max_commits: int = typer.Option(500, help="Max git commits to index"),
) -> None:
    """Index a project codebase into the vector store."""
    from codebrain.config import Settings
    from codebrain.core.di import init_container
    from codebrain.core.repository import Repository
    from codebrain.domains.history.logic import index_git_history

    settings = Settings()
    container = init_container(settings)
    repo = Repository(container.vector_store, container.embedder)

    typer.echo(f"Indexing git history for {project}...")
    result = index_git_history(repo, project, max_commits)
    typer.echo(f"  Indexed {result['indexed_commits']} commits, {result['indexed_entries']} entries")


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
