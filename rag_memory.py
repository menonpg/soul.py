"""
soul.py v1.0 — RAG Memory Backend
Replaces full MEMORY.md injection with vector retrieval.
Only relevant memories are injected — handles files with thousands of entries.

Requires: pip install chromadb sentence-transformers
"""
import os
from pathlib import Path
from datetime import datetime

try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


class RAGMemory:
    """
    Drop-in replacement for flat MEMORY.md injection.
    Stores memories as vector embeddings, retrieves top-k relevant chunks.

    Usage:
        memory = RAGMemory("MEMORY.md")
        memory.append("Q: my name is Prahlad\nA: Nice to meet you.")
        context = memory.retrieve("what do you know about me?", k=5)
    """

    def __init__(self, memory_path: str = "MEMORY.md", k: int = 5):
        if not HAS_CHROMA:
            raise ImportError("pip install chromadb sentence-transformers")

        self.memory_path = Path(memory_path)
        self.k = k
        self._db_path = str(self.memory_path.parent / ".soul_vectorstore")

        self._client = chromadb.PersistentClient(path=self._db_path)
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # ~80MB, runs locally, no API key
        )
        self._collection = self._client.get_or_create_collection(
            name="soul_memory",
            embedding_function=self._ef,
        )

        # Index any existing MEMORY.md content on first run
        if self.memory_path.exists():
            self._index_existing()

    def _index_existing(self):
        """Parse and index existing MEMORY.md entries."""
        text = self.memory_path.read_text()
        entries = self._parse_entries(text)
        existing_ids = set(self._collection.get()["ids"])
        new = [(eid, content) for eid, content in entries if eid not in existing_ids]
        if new:
            ids, docs = zip(*new)
            self._collection.add(documents=list(docs), ids=list(ids))

    def _parse_entries(self, text: str) -> list[tuple[str, str]]:
        """Split MEMORY.md into individual timestamped entries."""
        import re
        blocks = re.split(r'\n## ', text)
        entries = []
        for i, block in enumerate(blocks[1:], 1):  # skip header
            entries.append((f"entry_{i}", block.strip()))
        return entries

    def append(self, exchange: str) -> str:
        """Add a new memory entry. Returns the entry id."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"{ts}\n{exchange.strip()}"

        # Write to MEMORY.md
        with open(self.memory_path, "a") as f:
            f.write(f"\n## {entry}\n")

        # Add to vector store
        entry_id = f"entry_{self._collection.count() + 1}"
        self._collection.add(documents=[entry], ids=[entry_id])
        return entry_id

    def retrieve(self, query: str, k: int = None) -> str:
        """Retrieve top-k most relevant memory chunks for a query."""
        k = k or self.k
        count = self._collection.count()
        if count == 0:
            return "# Your Memory\n(No memories yet.)\n"

        results = self._collection.query(
            query_texts=[query],
            n_results=min(k, count),
        )
        docs = results["documents"][0]
        context = "\n\n---\n".join(docs)
        return f"# Relevant Memories (retrieved {len(docs)} of {count} total)\n\n{context}"

    def count(self) -> int:
        return self._collection.count()
