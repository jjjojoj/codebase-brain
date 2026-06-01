# Task 2: session-memory-mcp

Implement the session memory MCP server at packages/session-memory-mcp/

## Purpose
AI编程会话开始/结束时自动记录上下文，下次会话自动召回。解决"长链条任务走丢"痛点。

## MCP Tools

### 1. start_session(task_description: str) -> dict
- Generate unique session_id
- Embed task_description
- Search Milvus session_memory collection for similar past sessions
- Return {"session_id": "...", "related_sessions": [...], "suggestion": "..."}

### 2. record_decision(decision: str, reason: str = "") -> dict
- Store decision in current session context
- Return {"status": "recorded"}

### 3. record_problem(problem: str, solution: str, files: str = "") -> dict
- Record a problem and how it was solved
- Return {"status": "recorded"}

### 4. record_file_change(file_path: str, change_type: str, description: str) -> dict
- Track modified files and why. change_type: created/modified/deleted
- Return {"status": "recorded"}

### 5. end_session(summary: str = "") -> dict
- Compile all: task, files_modified, decisions, problems
- Embed summary, store in Milvus
- Return {"session_id": "...", "status": "saved"}

### 6. recall_context(task_description: str, top_k: int = 5) -> list
- Search Milvus for similar past sessions
- Return past sessions with relevance scores

## Internal State
- In-memory dict: {session_id, task, files[], decisions[], problems[], start_time}
- On end_session, persist to Milvus

## Files
- Create: packages/session-memory-mcp/__init__.py
- Create: packages/session-memory-mcp/server.py

## Requirements
- Use core.mcp_base.BrainMCP as base
- Python 3.12, type hints, docstrings
