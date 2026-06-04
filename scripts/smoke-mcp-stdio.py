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
            await session.initialize()
            tools = await session.list_tools()

    names = sorted(tool.name for tool in tools.tools)
    expected = 23 if "index_git_history" in names else 21
    if len(names) != expected:
        raise RuntimeError(f"expected {expected} tools, got {len(names)}: {names}")
    print(f"PASS: MCP stdio initialized; tool_count={len(names)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    asyncio.run(smoke(args.config))


if __name__ == "__main__":
    main()
