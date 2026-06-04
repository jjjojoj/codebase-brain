"""Run a real MCP stdio handshake against an installed Codebase Brain server."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["codebase-brain"]
    params = StdioServerParameters(
        command=server["command"],
        args=server.get("args", []),
        env=server.get("env", {}),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()

    names = sorted(tool.name for tool in tools.tools)
    expected = 23 if "index_git_history" in names else 21
    if len(names) != expected:
        raise RuntimeError(f"expected {expected} tools, got {len(names)}: {names}")
    instructions = initialized.instructions or ""
    if "without asking the user to name tools" not in instructions:
        raise RuntimeError("MCP server instructions do not define automatic orchestration")

    descriptions = {tool.name: tool.description or "" for tool in tools.tools}
    required = {
        "brain_context_for_task": "Automatically call first",
        "start_session": "Automatically call once after Context Pack",
        "record_decision": "Automatically record a finalized",
        "record_problem": "Automatically record a solved",
        "record_file_change": "Automatically record each meaningful",
        "end_session": "Automatically call once",
    }
    for name, expected_text in required.items():
        if expected_text not in descriptions.get(name, ""):
            raise RuntimeError(f"MCP tool description lacks decision trigger: {name}")

    print(
        "PASS: MCP stdio initialized; "
        f"tool_count={len(names)}; automatic_orchestration=true"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    asyncio.run(smoke(args.config))


if __name__ == "__main__":
    main()
