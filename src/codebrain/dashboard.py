"""Small local dashboard for Codebase Brain configuration and status."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

from codebrain.config import Settings
from codebrain.core.di import init_container
from codebrain.domains.brain import tools as brain_tools


def run_dashboard(host: str = "127.0.0.1", port: int = 8765, repo_path: str = ".") -> None:
    """Run the local dashboard HTTP server."""
    settings = Settings()
    init_container(settings)
    handler = _make_handler(settings, str(Path(repo_path).expanduser().resolve()))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Codebase Brain dashboard: http://{host}:{port}")
    server.serve_forever()


def build_dashboard_payload(settings: Settings, repo_path: str) -> dict[str, Any]:
    """Build dashboard data without starting HTTP, useful for tests."""
    status = brain_tools.brain_status(repo_path)
    sync = brain_tools.brain_sync_status(repo_path)
    command = _command_hint()
    return {
        "ok": True,
        "repo_path": str(Path(repo_path).expanduser().resolve()),
        "status": status,
        "sync": sync,
        "mcp_config": {
            "mcpServers": {
                "codebase-brain": {
                    "command": command,
                    "args": ["serve"],
                    "env": {
                        "CODEBRAIN_DB_PATH": str(settings.resolved_db_path),
                        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": settings.default_conventions_path,
                        "CODEBRAIN_CODEBASE_MEMORY_BINARY": settings.codebase_memory_binary,
                    },
                }
            }
        },
        "environment": {
            "CODEBRAIN_VECTOR_STORE_BACKEND": settings.vector_store_backend,
            "CODEBRAIN_MILVUS_URI": settings.milvus_uri,
            "CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS": str(settings.allow_cloud_embeddings).lower(),
            "CODEBRAIN_GIT_HISTORY_INDEX_ENABLED": str(
                settings.git_history_index_enabled
            ).lower(),
        },
    }


def render_dashboard_html() -> str:
    """Return the single-page dashboard shell."""
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codebase Brain Dashboard</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --line: #d6d9dd;
      --accent: #0f766e;
      --warn: #b45309;
      --error: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      border-bottom: 1px solid var(--line);
      padding: 20px 28px 14px;
      background: var(--panel);
    }
    h1 { margin: 0 0 6px; font-size: 22px; letter-spacing: 0; }
    h2 { margin: 0 0 10px; font-size: 15px; letter-spacing: 0; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
      gap: 16px;
      padding: 18px 28px 28px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }
    .stack { display: grid; gap: 16px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-height: 74px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 18px; font-weight: 650; margin-top: 4px; overflow-wrap: anywhere; }
    .ok { color: var(--accent); }
    .warn { color: var(--warn); }
    .error { color: var(--error); }
    pre {
      margin: 0;
      padding: 12px;
      overflow: auto;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: rgba(15, 23, 42, 0.06);
      max-height: 360px;
    }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      padding: 7px 10px;
      cursor: pointer;
    }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 14px; }
      header { padding: 16px 14px 12px; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Codebase Brain</h1>
    <div id="repo" class="label">loading</div>
  </header>
  <main>
    <div class="stack">
      <section>
        <h2>状态</h2>
        <div class="grid">
          <div class="metric"><div class="label">Graph sidecar</div><div id="graph" class="value">-</div></div>
          <div class="metric"><div class="label">Sync</div><div id="sync" class="value">-</div></div>
          <div class="metric"><div class="label">Vector backend</div><div id="vector" class="value">-</div></div>
        </div>
      </section>
      <section>
        <h2>文件过滤快照</h2>
        <pre id="snapshot">loading</pre>
      </section>
      <section>
        <h2>MCP 配置</h2>
        <div class="toolbar"><button id="copy">Copy JSON</button></div>
        <pre id="mcp">loading</pre>
      </section>
    </div>
    <div class="stack">
      <section>
        <h2>隐私开关</h2>
        <pre id="privacy">loading</pre>
      </section>
      <section>
        <h2>Milvus 语义层</h2>
        <pre id="milvus">loading</pre>
      </section>
      <section>
        <h2>推荐动作</h2>
        <pre id="actions">loading</pre>
      </section>
    </div>
  </main>
  <script>
    let payload = null;
    const setText = (id, value) => { document.getElementById(id).textContent = value; };
    const cssStatus = (el, status) => {
      el.className = "value " + (status === "ready" || status === "fresh" ? "ok" : "warn");
    };
    fetch("/api/status").then(r => r.json()).then(data => {
      payload = data;
      setText("repo", data.repo_path);
      const graph = document.getElementById("graph");
      graph.textContent = data.status.graph.status;
      cssStatus(graph, data.status.graph.status);
      const sync = document.getElementById("sync");
      sync.textContent = data.sync.reason;
      cssStatus(sync, data.sync.reason);
      setText("vector", data.status.knowledge.vector_store_backend);
      setText("snapshot", JSON.stringify(data.sync.snapshot, null, 2));
      setText("mcp", JSON.stringify(data.mcp_config, null, 2));
      setText("privacy", JSON.stringify(data.status.privacy, null, 2));
      setText("milvus", JSON.stringify(data.status.knowledge.milvus, null, 2));
      setText("actions", JSON.stringify(data.status.recommended_tools, null, 2));
    }).catch(err => {
      setText("snapshot", String(err));
    });
    document.getElementById("copy").addEventListener("click", () => {
      if (payload) navigator.clipboard.writeText(JSON.stringify(payload.mcp_config, null, 2));
    });
  </script>
</body>
</html>
"""


def _make_handler(settings: Settings, repo_path: str) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                _send(self, HTTPStatus.OK, render_dashboard_html(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/status":
                payload = build_dashboard_payload(settings, repo_path)
                _send_json(self, HTTPStatus.OK, payload)
                return
            if parsed.path == "/healthz":
                _send_json(self, HTTPStatus.OK, {"ok": True})
                return
            _send_json(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler


def _send_json(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    payload: dict[str, Any],
) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    _send(handler, status, body, "application/json; charset=utf-8")


def _send(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    body: str,
    content_type: str,
) -> None:
    data = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _command_hint() -> str:
    candidate = Path(sys.argv[0]).expanduser()
    if candidate.exists():
        return str(candidate.resolve())
    return "codebrain"
