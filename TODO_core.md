# Task 0 v2: Core Library (Updated with Claude-Context designs)

## New requirements (from claude-context analysis)

### 1. Multi-Provider Embedder (IMPORTANT)
`packages/core/embedder.py` must support strategy pattern:
- `SentenceTransformerEmbedder` (BAAI/bge-m3, local, default)
- `OllamaEmbedder` (bge-m3 via Ollama REST API, local)
- `OpenAIEmbedder` (text-embedding-3-small, cloud, needs API key)
- Common interface: `embed(text) -> list[float]`, `embed_batch(texts) -> list[list[float]]`
- Config: `EMBEDDING_PROVIDER` env var (sentence_transformers|ollama|openai)
- Auto-detect: if OPENAI_API_KEY set, use OpenAI; if OLLAMA_HOST set, use Ollama; default sentence-transformers

### 2. Hybrid Search for MilvusClient
`packages/core/milvus_client.py` must support hybrid search:
- Method: `hybrid_search(collection, query_text, embedding, top_k, filter_expr=None)`
- Uses Milvus hybrid_search API (dense vector + BM25 sparse)
- If Milvus Lite doesn't support hybrid, fall back to:
  1. Vector search (dense) → top_k*2 results
  2. Keyword filter (Python-side BM25 or simple token matching) → re-rank
  3. RRF (Reciprocal Rank Fusion) to merge both result sets

### 3. File Watch Trigger
`packages/core/mcp_base.py` must add:
- Watch `~/.codebrain/.sync-trigger` file
- On modification, call a callback (for conventions-mcp auto-reindex)
- Debounce: 2 second window

## Original requirements (keep all)

### packages/core/config.py
- Config class with defaults + env var override
- MILVUS_DB_PATH, EMBEDDING_PROVIDER, EMBEDDING_MODEL, OLLAMA_HOST, OPENAI_API_KEY

### packages/core/milvus_client.py
- init_collections() for conventions, session_memory, git_history
- insert/search methods per collection
- NEW: hybrid_search() with RRF fallback

### packages/core/mcp_base.py  
- BrainMCP wrapping FastMCP
- Auto-init Milvus on startup
- NEW: sync-trigger file watcher

### packages/core/__init__.py
- Export all key classes

### pyproject.toml at root
- Add openai and httpx deps for OpenAI/Ollama embedder support
