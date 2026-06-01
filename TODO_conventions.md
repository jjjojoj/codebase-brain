# Task 1: conventions-mcp

Implement the conventions MCP server at packages/conventions-mcp/

## Purpose
让开发者写 Markdown 约定文件 → 向量化 → 存入 Milvus → AI 编程工具修改代码前自动检索相关约定。

## MCP Tools

### 1. add_convention(module: str, title: str, content: str) -> dict
- Generate unique ID
- Embed content using core embedder
- Store in Milvus conventions collection
- Return {"id": "...", "status": "stored"}

### 2. search_conventions(query: str, module_filter: str = None, top_k: int = 5) -> list
- Embed query
- Search Milvus conventions collection
- If module_filter, filter by module field
- Return list of {id, module, title, content, similarity}

### 3. list_conventions(module: str = None) -> list
- List all conventions, optionally filtered by module
- Return list of {id, module, title, created_at}

### 4. index_convention_files(path: str = None) -> dict
- Scan `.codebrain/conventions/` (or specified path) for .md files
- Parse frontmatter (module, title)
- Index all found conventions
- Return {"indexed": N, "files": [...]}

## Convention File Format (.codebrain/conventions/*.md)
```markdown
---
module: auth
title: 认证模块错误处理约定
tags: [error-handling, auth]
---

所有认证相关函数必须返回 AuthError 类型，不允许直接返回 error。
...
```

## Files
- Create: `packages/conventions-mcp/__init__.py`
- Create: `packages/conventions-mcp/server.py` (main MCP server using FastMCP)
- Create: `packages/conventions-mcp/templates/` (empty dir with README)

## Requirements
- Use core.mcp_base.BrainMCP as base
- Use core.milvus_client.MilvusClient for storage
- Use core.embedder.Embedder for embeddings
- Python 3.12, type hints, docstrings
- stdio transport for MCP
