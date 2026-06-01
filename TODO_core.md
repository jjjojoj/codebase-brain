# Task 0: Core Library for Codebase Brain

Implement the shared core library at packages/core/ for 3 MCP servers.

## What to build

### 1. packages/core/config.py
- Config class with defaults:
  - MILVUS_DB_PATH: ~/.codebrain/milvus.db (Milvus Lite embedded)
  - EMBEDDING_MODEL: BAAI/bge-m3
  - OLLAMA_HOST: http://localhost:11434
- Load from env vars with fallback to defaults
- Singleton pattern

### 2. packages/core/embedder.py
- Embedder class using sentence-transformers
- __init__ loads model from config
- embed(text: str) -> list[float]
- embed_batch(texts: list[str]) -> list[list[float]]
- Model: BAAI/bge-m3, dim=1024

### 3. packages/core/milvus_client.py
- MilvusClient class wrapping pymilvus (Milvus Lite)
- init_collections() creates 3 collections if not exist:
  - conventions: id(str,PK), module(str), title(str), content(str), embedding(FLOAT_VECTOR,1024), created_at(str)
  - session_memory: id(str,PK), task(str), files_modified(str), decisions(str), assumptions(str), problems(str), embedding(FLOAT_VECTOR,1024), created_at(str)
  - git_history: id(str,PK), file_path(str), commit_hash(str), commit_msg(str), author(str), date(str), code_snippet(str), embedding(FLOAT_VECTOR,1024)
- insert methods for each collection
- search methods that take embedding + top_k, return results

### 4. packages/core/__init__.py
- Export Config, Embedder, MilvusClient

### 5. pyproject.toml at root
```toml
[project]
name = "codebase-brain"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0.0",
    "pymilvus>=2.4.0",
    "sentence-transformers>=3.0.0",
    "pyyaml>=6.0",
]
```

### 6. packages/core/mcp_base.py
- BrainMCP class wrapping FastMCP from mcp package
- Auto-initializes Milvus collections on startup
- Provides get_milvus() and get_embedder() helpers
- Standard error handling

## Requirements
- Python 3.12
- Use type hints
- Add docstrings
- Handle errors gracefully (Milvus not available, model not loaded)
- Don't use ollama API for embeddings, use sentence-transformers directly (local)
