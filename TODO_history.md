# Task 3: history-mcp

Implement the git history MCP server at packages/history-mcp/

## Purpose
索引 git log/blame 信息，让 AI 理解代码的修改历史、为什么这么写、谁写的、经常和哪些文件一起改。

## MCP Tools

### 1. search_history(query: str, file_filter: str = None, top_k: int = 10) -> list
- Embed query
- Search Milvus git_history collection
- Optionally filter by file_path
- Return {commit_hash, commit_msg, author, date, file_path, code_snippet, similarity}

### 2. get_blame(file_path: str, start_line: int, end_line: int) -> list
- Run git blame on the file
- Return list of {line, author, date, commit_hash, commit_msg}

### 3. get_co_changed_files(file_path: str, limit: int = 10) -> list
- Analyze git log for files frequently changed together with file_path
- Return list of {file, co_change_count, last_changed_together}

### 4. get_recent_changes(file_path: str, limit: int = 10) -> list
- Get recent commits touching file_path
- Return list of {commit_hash, commit_msg, author, date}

### 5. index_git_history(repo_path: str = ".", max_commits: int = 500) -> dict
- Parse git log: hash, author, date, message, changed files
- For each changed file, create an entry with the commit context
- Embed commit_message + file_path + code context
- Store in Milvus git_history collection
- Return {"indexed_commits": N, "indexed_entries": M}

## Files
- Create: packages/history-mcp/__init__.py
- Create: packages/history-mcp/server.py
- Create: packages/history-mcp/git_indexer.py

## git_indexer.py
- parse_git_log(repo_path, max_commits) -> list of commit dicts
- get_blame_info(repo_path, file_path, start, end) -> list
- get_co_changed(repo_path, file_path, limit) -> list
- run git commands via subprocess

## Requirements
- Use core.mcp_base.BrainMCP as base
- Git commands via subprocess (not libgit2)
- Python 3.12, type hints, docstrings
- Handle repos with no git history gracefully
