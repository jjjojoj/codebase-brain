# Task 1 v2: conventions-mcp (Updated with Claude-Context designs)

## New requirements (from claude-context analysis)

### 1. Hybrid Search for search_conventions
The `search_conventions` tool must use hybrid search:
- Accept BOTH `query` (natural language) AND `keywords` (optional, for exact matching)
- Call `milvus_client.hybrid_search()` to combine dense vector + BM25
- Return results ranked by RRF fusion score

### 2. Auto-reindex via file watch trigger
When `~/.codebrain/.sync-trigger` is touched:
- Automatically call `index_convention_files()` to re-index changed conventions
- Debounce: 2 seconds (multiple rapid touches → single re-index)

### 3. Convention file templates
Include 3 default templates in `packages/conventions-mcp/templates/`:
- `error-handling.md` — 错误处理约定模板
- `code-style.md` — 代码风格约定模板  
- `testing.md` — 测试约定模板
Each template has YAML frontmatter (module, title, tags) and example content in Chinese.

## Original MCP Tools (keep all)

### 1. add_convention(module, title, content) -> dict
### 2. search_conventions(query, keywords=None, module_filter=None, top_k=5) -> list
  - NEW: keywords parameter for BM25 boosting
  - NEW: uses hybrid_search internally
### 3. list_conventions(module=None) -> list
### 4. index_convention_files(path=None) -> dict
  - Scan .codebrain/conventions/ for .md files with frontmatter
  - Parse module, title, tags from frontmatter
  - Embed content, store in Milvus conventions collection

## Convention File Format
```yaml
---
module: auth
title: 认证模块错误处理约定
tags: [error-handling, auth]
---
内容...
```

## Files
- packages/conventions-mcp/__init__.py
- packages/conventions-mcp/server.py
- packages/conventions-mcp/templates/error-handling.md
- packages/conventions-mcp/templates/code-style.md
- packages/conventions-mcp/templates/testing.md
