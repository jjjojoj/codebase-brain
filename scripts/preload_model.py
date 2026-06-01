"""Pre-download the bge-m3 model to avoid timeout on first MCP startup."""
print("Downloading BAAI/bge-m3 model (about 2GB)...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")
print("Done! Model cached. MCP servers will start quickly now.")
