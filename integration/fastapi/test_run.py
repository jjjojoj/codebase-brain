#!/usr/bin/env python
"""Integration test: codebase-brain against FastAPI repo"""
import os, sys

os.environ["CODEBRAIN_DB_PATH"] = "/tmp/fastapi-test/.codebrain/codebrain.db"
os.environ["CODEBRAIN_DEFAULT_CONVENTIONS_PATH"] = "/tmp/fastapi-test/.codebrain/conventions"
sys.path.insert(0, "/tmp/codebase-brain-deploy/src")

from codebrain.config import Settings
from codebrain.core.di import init_container
from codebrain.core.repository import Repository
from codebrain.domains.conventions.logic import index_convention_files, search_conventions, list_conventions
from codebrain.domains.brain import local_context, graph_context, context_pack

settings = Settings()
container = init_container(settings)
repo = Repository(container.vector_store, container.embedder)

# 1. Index conventions
result = index_convention_files(repo, path="/tmp/fastapi-test/.codebrain/conventions")
print(f"Indexed: {result['indexed']}, Skipped: {result['skipped']}")

# 2. List
listed = list_conventions(repo)
print(f"Conventions: {len(listed)}")
for c in listed:
    print(f"  [{c['module']}] {c['title']}")

# 3. Semantic search
print("\n=== Search: dependency injection ===")
for r in search_conventions("dependency injection testing", repo, top_k=3):
    print(f"  [{r['module']}] {r['title']} (sim: {r.get('similarity',0):.3f})")

print("\n=== Search: OAuth2 security patterns ===")
for r in search_conventions("OAuth2 security authentication token", repo, top_k=3):
    print(f"  [{r['module']}] {r['title']} (sim: {r.get('similarity',0):.3f})")

# 4. brain_context_for_task
local = local_context.gather_local_context(
    task="add OAuth2 login to items API",
    files=["src/auth/login.py", "src/api/items.py"],
    repo_path="/tmp/fastapi-test",
    top_k=5,
    repository=repo,
)
graph = graph_context.gather_graph_context(
    task="add OAuth2 login to items API",
    symbols=["OAuth2PasswordBearer", "Security"],
    adapter=None,
)
pack = context_pack.assemble_context_pack(
    task="add OAuth2 login to items API", local=local, graph=graph
)

print(f"\n=== Context Pack ===")
print(f"  Status: {pack['status']}")
print(f"  Critical conventions ({len(pack['critical_conventions'])}):")
for c in pack["critical_conventions"]:
    print(f"    - [{c['module']}] {c['title']}")
print(f"  Warnings: {pack['warnings']}")
print(f"  Next steps: {pack['suggested_next_steps']}")

# 5. Empty context (should not crash)
empty = local_context.gather_local_context(task="unknown task", repository=repo)
empty_pack = context_pack.assemble_context_pack(task="unknown", local=empty, graph=None)
print(f"\n=== Empty Pack ===")
print(f"  Status: {empty_pack['status']}")
print(f"  Warnings: {empty_pack['warnings']}")

print("\nALL INTEGRATION TESTS PASSED")
